from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

ChannelName = Literal["telegram", "whatsapp", "email"]
TicketStatus = Literal[
    "received",
    "acked",
    "running",
    "awaiting_approval",
    "approved",
    "rejected",
    "sending",
    "sent",
    "expired",
    "failed",
    "needs_human",
    "archived",
]
Risk = Literal["low", "medium", "high", "critical"]
Intent = Literal["knowledge", "sales", "support", "analytics", "other"]
Specialist = Literal["knowledge", "customer", "sales", "support", "analytics"]


class InboundMessage(BaseModel):
    channel: ChannelName
    external_user_id: str
    display_name: str | None = None
    text: str
    provider_message_id: str
    thread_id: str | None = None
    reply_to: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class ProposedAction(BaseModel):
    type: Literal[
        "draft_quote",
        "create_support_ticket",
        "upsert_contact",
        "trigger_tour",
        "track_kpi",
        "update_inventory",
        "schedule_delivery",
        "escalate_to_human",
        "log_incident",
        "none",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)
    reversible: bool = True


class ProposedResponse(BaseModel):
    customer_reply_ar: str = Field(min_length=2, max_length=4000)
    customer_reply_en: str | None = None
    rationale_ar: str
    risk: Risk = "low"
    specialist: Specialist
    citations: list[str] = Field(default_factory=list)
    actions: list[ProposedAction] = Field(default_factory=list)
    language: Literal["ar"] = "ar"
    lead_score: int | None = None


class ChannelAdapter(Protocol):
    name: str

    async def send_text(self, to: str, text: str, *, reply_to: str | None = None) -> str: ...

    async def send_document(self, to: str, r2_key: str, filename: str) -> str: ...

    async def ack_received(self, to: str, ticket_id: str) -> None: ...


@dataclass
class TicketState:
    ticket_id: str
    tenant_id: str
    channel: ChannelName
    external_user_id: str
    status: TicketStatus = "received"
    intent: Intent = "other"
    risk: Risk = "low"
    specialist: Specialist | None = None
    language: str = "ar"
    retry_count: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)

    def transition(self, new_status: TicketStatus) -> None:
        self.history.append({"from": self.status, "to": new_status})
        self.status = new_status

    def escalate(self, reason: str = "") -> None:
        self.risk = "high"
        self.specialist = "support"
        self.transition("needs_human")
        self.history[-1]["reason"] = reason


@dataclass
class AgentResult:
    success: bool
    response: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    specialist: Specialist | None = None
    risk: Risk = "low"
    citations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_proposed_response(self) -> ProposedResponse:
        return ProposedResponse(
            customer_reply_ar=self.response,
            rationale_ar=self.metadata.get("rationale", ""),
            risk=self.risk,
            specialist=self.specialist or "support",
            citations=self.citations,
            actions=[
                ProposedAction(type=a.get("type", "none"), payload=a.get("payload", {}))
                for a in self.actions
            ],
        )
