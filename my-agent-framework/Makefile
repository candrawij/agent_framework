.PHONY: dev test lint format install clean docker-up docker-down

# Development
dev:
	uvicorn framework.api.server:app --reload --host 0.0.0.0 --port 8000

# Testing
test:
	pytest tests/ -v --cov=framework --cov=model_layer --cov-report=term-missing

test-fast:
	pytest tests/ -v -m "not slow"

# Code quality
lint:
	ruff check framework/ model_layer/ tests/
	mypy framework/ model_layer/

format:
	black framework/ model_layer/ tests/ shared/
	ruff check --fix framework/ model_layer/ tests/

# Install
install:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all,dev]"

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build

# Setup JWT secret
gen-secret:
	python scripts/gen_jwt_secret.py
