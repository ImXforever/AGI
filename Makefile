# =============================================================================
# PetroAgent Platform — Makefile
# =============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

APP_NAME := petroagent
DOCKER_COMPOSE := docker compose
PYTHON := python3
PYTEST := $(PYTHON) -m pytest
RUFF := ruff
MYPY := mypy

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install dependencies
	pip install -e ".[dev]"

.PHONY: dev
dev: ## Run development server with auto-reload
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

.PHONY: dev-docker
dev-docker: ## Run full stack via Docker Compose
	$(DOCKER_COMPOSE) up --build

.PHONY: down
down: ## Stop Docker Compose services
	$(DOCKER_COMPOSE) down

.PHONY: logs
logs: ## Tail Docker Compose logs
	$(DOCKER_COMPOSE) logs -f

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

.PHONY: lint
lint: ## Run linter (ruff)
	$(RUFF) check app/ tests/ tools/ provision/

.PHONY: format
format: ## Auto-format code
	$(RUFF) format app/ tests/ tools/ provision/

.PHONY: typecheck
typecheck: ## Run type checker (mypy)
	$(MYPY) app/

.PHONY: security
security: ## Run security scan (bandit + secret_scan)
	bandit -r app/ -c pyproject.toml
	$(PYTHON) tools/secret_scan.py

.PHONY: config-lint
config-lint: ## Validate configuration
	$(PYTHON) tools/config_lint.py

.PHONY: check: lint typecheck ## Run all quality checks
check: lint typecheck security config-lint

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

.PHONY: test
test: ## Run unit tests
	$(PYTEST) tests/unit/ -v --tb=short

.PHONY: test-integration
test-integration: ## Run integration tests
	$(PYTEST) tests/integration/ -v --tb=short

.PHONY: test-e2e
test-e2e: ## Run end-to-end tests
	$(PYTHON) tests/e2e/run_e2e.py

.PHONY: test-eval
test-eval: ## Run evaluation suite
	$(PYTHON) tests/eval/run_eval.py

.PHONY: test-all
test-all: ## Run all tests
	$(PYTEST) tests/ -v --tb=short

.PHONY: coverage
coverage: ## Run tests with coverage report
	$(PYTEST) tests/ --cov=app --cov-report=term-missing --cov-report=html:htmlcov

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

.PHONY: db-migrate
db-migrate: ## Run database migrations
	$(PYTHON) -c "import asyncio; from app.storage.pg import connect_pg, run_migrations; asyncio.run(run_migrations(None))"

.PHONY: db-seed
db-seed: ## Seed database with initial data
	$(PYTHON) -c "import asyncio; from app.storage.seed import load_seeds; print('run via app startup')"

.PHONY: db-reset
db-reset: ## Reset database (DANGEROUS — drops all tables)
	$(PYTHON) -c "import psycopg2; conn = psycopg2.connect('postgresql://petroagent:petroagent@localhost:5432/petroagent'); cur = conn.cursor(); cur.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public'); conn.commit(); print('database reset')"

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

.PHONY: build
build: ## Build Docker image
	docker build -t $(APP_NAME):latest .

.PHONY: build-hermes
build-hermes: ## Build Hermes bridge image
	docker build -f Dockerfile.hermes -t $(APP_NAME)-hermes:latest .

.PHONY: push
push: ## Push Docker image to registry
	docker push $(APP_NAME):latest

# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------

.PHONY: deploy-railway
deploy-railway: ## Deploy to Railway
	railway up

.PHONY: package
package: ## Create deployment package
	$(PYTHON) tools/package.py

# ---------------------------------------------------------------------------
# Provisioning
# ---------------------------------------------------------------------------

.PHONY: provision
provision: ## Provision a new tenant
	$(PYTHON) provision/tenant.py --config provision/tenant.example.yaml

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .mypy_cache .pytest_cache htmlcov .ruff_cache dist build *.egg-info
