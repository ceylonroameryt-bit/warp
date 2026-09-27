.PHONY: help dev stop build migrate seed test lint fmt clean

# Default target
help: ## Show this help message
	@echo "Warp Ladger — Development Commands"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ─── Environment ─────────────────────────────────────────────
.env:
	@echo "Creating .env from .env.example..."
	@cp .env.example .env
	@echo "⚠ Please edit .env and set your SECRET_KEY and passwords."

# ─── Docker ──────────────────────────────────────────────────
dev: .env ## Start the full local development stack
	docker-compose up --build -d
	@echo ""
	@echo "✅ Warp Ladger is running:"
	@echo "   Frontend:  http://localhost:3000"
	@echo "   API:       http://localhost:8000"
	@echo "   API Docs:  http://localhost:8000/api/docs"
	@echo "   MailHog:   http://localhost:8025"
	@echo "   MinIO UI:  http://localhost:9001"

stop: ## Stop all services
	docker-compose down

build: ## Rebuild Docker images without cache
	docker-compose build --no-cache

logs: ## Tail all service logs
	docker-compose logs -f

logs-backend: ## Tail backend logs
	docker-compose logs -f backend

logs-web: ## Tail frontend logs
	docker-compose logs -f web

# ─── Database ─────────────────────────────────────────────────
migrate: ## Run Alembic database migrations
	docker-compose exec backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create name=add_something)
	docker-compose exec backend alembic revision --autogenerate -m "$(name)"

migrate-down: ## Rollback the last migration
	docker-compose exec backend alembic downgrade -1

seed: ## Seed the database with system roles, permissions and super-admin
	docker-compose exec backend python -m infrastructure.scripts.seed

# ─── Testing ──────────────────────────────────────────────────
test: ## Run all backend tests
	docker-compose exec backend pytest tests/ -v --cov=app --cov-report=term-missing

test-fast: ## Run tests without coverage
	docker-compose exec backend pytest tests/ -v -x

test-frontend: ## Run frontend type check and lint
	docker-compose exec web npm run type-check
	docker-compose exec web npm run lint

# ─── Code Quality ─────────────────────────────────────────────
lint: ## Lint backend (ruff) and frontend (eslint)
	docker-compose exec backend ruff check app tests
	docker-compose exec web npm run lint

fmt: ## Format backend code
	docker-compose exec backend ruff format app tests
	docker-compose exec backend ruff check --fix app tests

# ─── Utilities ────────────────────────────────────────────────
shell-backend: ## Open a shell in the backend container
	docker-compose exec backend bash

shell-db: ## Open a PostgreSQL shell
	docker-compose exec postgres psql -U warpladger -d warpladger

clean: ## Remove all containers and volumes (DESTRUCTIVE)
	@echo "⚠  This will delete all local data. Press Ctrl+C to cancel..."
	@sleep 3
	docker-compose down -v --remove-orphans
