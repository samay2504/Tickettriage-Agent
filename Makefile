.PHONY: help install install-dev test test-cov lint format clean run docker-build docker-up docker-down

help:
	@echo "Ticket Triage Agent - Available targets:"
	@echo "  install          Install dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  test             Run tests"
	@echo "  test-cov         Run tests with coverage report"
	@echo "  lint             Run linting (ruff + mypy)"
	@echo "  format           Format code (black)"
	@echo "  format-check     Check formatting without changes"
	@echo "  clean            Clean temporary files"
	@echo "  run              Run development server"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-up        Start Docker containers"
	@echo "  docker-down      Stop Docker containers"

install:
	pip install --upgrade pip
	pip install -e .
	pip install -r requirements.txt

install-dev: install
	pip install black ruff mypy pytest pytest-cov pytest-mock httpx

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=app --cov=agent --cov=kb --cov=cache --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	ruff check .
	mypy app agent kb cache config

format:
	black .

format-check:
	black --check .
	ruff check --select I .

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '.pytest_cache' -delete
	find . -type d -name '.mypy_cache' -delete
	find . -type d -name '.ruff_cache' -delete
	find . -type d -name 'htmlcov' -delete
	find . -type f -name '.coverage' -delete
	rm -rf build/ dist/ *.egg-info/

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker-compose -f docker/docker-compose.yml build

docker-up:
	docker-compose -f docker/docker-compose.yml up -d

docker-down:
	docker-compose -f docker/docker-compose.yml down

docker-logs:
	docker-compose -f docker/docker-compose.yml logs -f app
