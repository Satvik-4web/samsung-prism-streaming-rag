.PHONY: up down test lint typecheck

up:
	docker compose up --build -d

down:
	docker compose down

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy backend
