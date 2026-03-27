# ─── Algo Trading — Developer Makefile ───────────────────────────────────────
.PHONY: help up down logs db-shell redis-shell install test lint

help:
	@echo "  make up          — Start full Docker stack"
	@echo "  make down        — Stop Docker stack"
	@echo "  make logs        — Follow all container logs"
	@echo "  make db-shell    — Open psql shell"
	@echo "  make redis-shell — Open redis-cli shell"
	@echo "  make install     — Install Python dependencies"
	@echo "  make test        — Run test suite"
	@echo "  make lint        — Run ruff linter"
	@echo "  make migrate     — Run DB schema (first-time setup)"
	@echo "  make news-fetch  — Manually trigger news ingestion"
	@echo "  make symbol-sync — Manually trigger symbol master sync"

up:
	docker compose up -d
	@echo "✅  Stack started. MLflow: http://localhost:5000 | Grafana: http://localhost:3001"

down:
	docker compose down

logs:
	docker compose logs -f

db-shell:
	docker exec -it algo_timescaledb psql -U $${POSTGRES_USER:-algo} -d $${POSTGRES_DB:-algotrading}

redis-shell:
	docker exec -it algo_redis redis-cli -a $${REDIS_PASSWORD:-redis_secret}

migrate:
	docker exec -i algo_timescaledb psql -U $${POSTGRES_USER:-algo} -d $${POSTGRES_DB:-algotrading} \
		< infra/db/init/001_init_schema.sql
	@echo "✅  Schema applied"

install:
	pip install poetry
	poetry install

test:
	poetry run pytest tests/ -v --cov=data --cov-report=term-missing

lint:
	poetry run ruff check data/ --fix
	poetry run black data/

news-fetch:
	poetry run python -c "import asyncio; from data.ingestion.news import fetch_and_store_news; asyncio.run(fetch_and_store_news())"

symbol-sync:
	poetry run python -c "import asyncio; from data.symbol_master.sync import sync_nse_equity_symbols; asyncio.run(sync_nse_equity_symbols())"
