"""Unit tests for the command sandbox and its approval gates.

The sandbox decides whether an agent-proposed shell command runs immediately,
waits for a human, or is refused outright. A misclassification here is a remote
code execution bug, so the classifier is tested against each tier explicitly,
including the "unknown command" default that must fail closed to `guard`.

Execution backends (docker/local) are never actually invoked: the tests drive
the decision logic and stub the settings object.
"""

from __future__ import annotations

import pytest

from app.core import sandbox

pytestmark = pytest.mark.unit


class _Settings:
    """Stands in for the runtime settings object the sandbox reads."""

    def __init__(self, **values: str) -> None:
        self._values = values

    def get(self, key: str, default: str) -> str:
        return self._values.get(key, default)


DISABLED = _Settings(sandbox_enabled="0")
NO_BACKEND = _Settings(sandbox_enabled="1", sandbox_mode="local", sandbox_local_allow="0")


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestClassifyBlock:
    @pytest.mark.parametrize(
        "cmd",
        [
            "rm -rf /",
            "mkfs.ext4 /dev/sda1",
            "dd if=/dev/zero of=/dev/sda",
            ":(){:|:&};:",
            "shutdown -h now",
            "reboot",
            "chmod 777 /etc/passwd",
        ],
    )
    def test_destructive_commands_are_blocked(self, cmd: str):
        assert sandbox.classify_command(cmd).tier == "block"

    def test_empty_command_is_blocked(self):
        result = sandbox.classify_command("")
        assert result.tier == "block" and result.reason == "empty command"

    def test_whitespace_only_command_is_blocked(self):
        assert sandbox.classify_command("   ").tier == "block"

    def test_none_is_tolerated_and_blocked(self):
        assert sandbox.classify_command(None).tier == "block"  # type: ignore[arg-type]

    def test_block_beats_safe_when_both_match(self):
        """`echo` is safe, but a fork bomb hidden after it is not."""
        assert sandbox.classify_command("echo hi; :(){:|:&};:").tier == "block"

    def test_classification_is_case_insensitive(self):
        assert sandbox.classify_command("RM -RF /").tier == "block"

    def test_block_reason_names_the_pattern(self):
        assert "mkfs" in sandbox.classify_command("mkfs /dev/sda").reason


class TestClassifyGuard:
    @pytest.mark.parametrize(
        "cmd",
        [
            "pip install requests",
            "apt-get update",
            "rm file.txt",
            "curl https://example.com",
            "wget https://example.com/x",
            "chmod +x script.sh",
            "docker ps",
            "ssh user@host",
        ],
    )
    def test_mutating_commands_require_approval(self, cmd: str):
        assert sandbox.classify_command(cmd).tier == "guard"

    def test_guard_pattern_is_caught_mid_pipeline(self):
        assert sandbox.classify_command("echo x && pip install evil").tier == "guard"

    def test_unknown_commands_fail_closed_to_guard(self):
        result = sandbox.classify_command("some-unknown-binary --flag")
        assert result.tier == "guard"
        assert "unknown" in result.reason


class TestClassifySafe:
    @pytest.mark.parametrize("cmd", ["ls", "pwd", "whoami", "date", "uname -a", "ls -la /tmp"])
    def test_readonly_commands_are_safe(self, cmd: str):
        assert sandbox.classify_command(cmd).tier == "safe"

    def test_a_safe_prefix_inside_a_longer_word_is_not_safe(self):
        """`lsof` must not be treated as `ls`."""
        assert sandbox.classify_command("lsof -i").tier != "safe"

    def test_safe_classification_carries_no_reason(self):
        assert sandbox.classify_command("pwd").reason == ""


class TestCommandClassification:
    def test_holds_tier_and_reason(self):
        c = sandbox.CommandClassification("guard", "because")
        assert c.tier == "guard" and c.reason == "because"

    def test_uses_slots_to_stay_small(self):
        assert not hasattr(sandbox.CommandClassification("safe"), "__dict__")


# ---------------------------------------------------------------------------
# Settings resolution
# ---------------------------------------------------------------------------


class TestSettings:
    def test_missing_config_yields_the_default(self):
        assert sandbox._get_setting(None, "sandbox_mode", "auto") == "auto"

    def test_mapping_style_config_is_read(self):
        assert (
            sandbox._get_setting(_Settings(sandbox_mode="docker"), "sandbox_mode", "auto")
            == "docker"
        )

    def test_attribute_style_config_is_read(self):
        class Attr:
            sandbox_mode = "local"

        assert sandbox._get_setting(Attr(), "sandbox_mode", "auto") == "local"

    def test_a_raising_getter_falls_back_to_the_default(self):
        class Boom:
            def get(self, key, default):
                raise RuntimeError("nope")

        assert sandbox._get_setting(Boom(), "sandbox_mode", "auto") == "auto"

    def test_sandbox_is_enabled_by_default(self):
        assert sandbox._enabled(None) is True

    def test_sandbox_can_be_switched_off(self):
        assert sandbox._enabled(DISABLED) is False


# ---------------------------------------------------------------------------
# run_python
# ---------------------------------------------------------------------------


class TestRunPython:
    async def test_empty_code_is_refused(self):
        assert "⚠️" in await sandbox.run_python("")

    async def test_oversized_code_is_refused(self):
        assert "⚠️" in await sandbox.run_python("x" * (sandbox.MAX_CODE_CHARS + 1))

    async def test_disabled_sandbox_refuses_to_run(self):
        assert "🔒" in await sandbox.run_python("print(1)", config=DISABLED)

    async def test_no_available_backend_is_reported(self, monkeypatch: pytest.MonkeyPatch):
        """Local execution is only permitted outside production; with docker
        absent and APP_ENV=production the sandbox must refuse rather than run."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setattr(sandbox, "_docker_ok", lambda: False)
        assert "🔒" in await sandbox.run_python("print(1)", config=NO_BACKEND)

    async def test_local_execution_is_refused_in_production(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("APP_ENV", "production")
        assert sandbox._local_allowed() is False

    @pytest.mark.parametrize("env", ["dev", "test", "local"])
    async def test_local_execution_is_permitted_outside_production(
        self, monkeypatch: pytest.MonkeyPatch, env: str
    ):
        monkeypatch.setenv("APP_ENV", env)
        assert sandbox._local_allowed() is True


# ---------------------------------------------------------------------------
# run_shell — the approval gate
# ---------------------------------------------------------------------------


class TestRunShell:
    async def test_empty_command_is_refused(self):
        assert "⚠️" in await sandbox.run_shell("")

    async def test_disabled_sandbox_refuses_to_run(self):
        assert "🔒" in await sandbox.run_shell("ls", config=DISABLED)

    async def test_blocked_command_never_executes(self):
        out = await sandbox.run_shell("rm -rf /", config=_Settings(sandbox_enabled="1"))
        assert "🚫" in out

    async def test_guarded_command_waits_for_approval(self):
        out = await sandbox.run_shell("pip install requests", config=_Settings(sandbox_enabled="1"))
        assert "⏳" in out
        assert "sandbox:" in out

    async def test_the_approval_callback_receives_the_command_and_id(self):
        seen: list[tuple[str, str]] = []

        async def callback(command: str, approval_id: str) -> None:
            seen.append((command, approval_id))

        await sandbox.run_shell(
            "pip install requests",
            config=_Settings(sandbox_enabled="1"),
            approval_callback=callback,
        )
        assert len(seen) == 1
        assert seen[0][0] == "pip install requests"
        assert seen[0][1].startswith("sandbox:")

    async def test_allow_all_mode_skips_the_approval_prompt(self):
        cfg = _Settings(
            sandbox_enabled="1",
            approval_mode="allow-all",
            sandbox_mode="local",
            sandbox_local_allow="0",
        )
        out = await sandbox.run_shell("pip install requests", config=cfg)
        assert "⏳" not in out

    async def test_yolo_mode_skips_the_approval_prompt(self):
        cfg = _Settings(
            sandbox_enabled="1", yolo_mode="1", sandbox_mode="local", sandbox_local_allow="0"
        )
        out = await sandbox.run_shell("pip install requests", config=cfg)
        assert "⏳" not in out

    async def test_yolo_mode_still_cannot_run_a_blocked_command(self):
        """No configuration may unblock a destructive command."""
        cfg = _Settings(sandbox_enabled="1", yolo_mode="1", approval_mode="allow-all")
        assert "🚫" in await sandbox.run_shell("rm -rf /", config=cfg)

    async def test_safe_command_needs_no_approval(self):
        out = await sandbox.run_shell("ls", config=NO_BACKEND)
        assert "⏳" not in out

    async def test_approval_ids_are_stable_per_command(self):
        cfg = _Settings(sandbox_enabled="1")
        first = await sandbox.run_shell("pip install a", config=cfg)
        second = await sandbox.run_shell("pip install a", config=cfg)
        assert first == second


# ---------------------------------------------------------------------------
# check_approval
# ---------------------------------------------------------------------------


class TestCheckApproval:
    async def test_without_a_database_nothing_is_approved(self):
        assert await sandbox.check_approval("sandbox:abc") is False

    async def test_an_approved_row_grants_permission(self):
        class Pg:
            async def fetchrow(self, *_a):
                return {"status": "approved"}

        assert await sandbox.check_approval("id", pg=Pg()) is True

    async def test_a_pending_row_does_not_grant_permission(self):
        class Pg:
            async def fetchrow(self, *_a):
                return {"status": "pending"}

        assert await sandbox.check_approval("id", pg=Pg()) is False

    async def test_a_missing_row_does_not_grant_permission(self):
        class Pg:
            async def fetchrow(self, *_a):
                return None

        assert await sandbox.check_approval("id", pg=Pg()) is False
