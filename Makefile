# TriForce AI Backend — Development Commands
# =============================================

VENV    := .venv
PYTHON  := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
PYTEST  := $(VENV)/bin/pytest
UVICORN := $(VENV)/bin/uvicorn

.PHONY: help install dev test test-v test-cov lint check run clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install dependencies
	python3 -m venv $(VENV)
	$(PIP) install -q -r requirements.txt

dev: ## Run development server with hot-reload
	$(UVICORN) app.main:app --host 0.0.0.0 --port 9100 --reload

run: ## Run production server
	$(UVICORN) app.main:app --host 0.0.0.0 --port 9100 --workers 4

test: ## Run all tests
	$(PYTEST) tests/

test-v: ## Run all tests (verbose)
	$(PYTEST) tests/ -v

test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ --cov=app --cov-report=term-missing

lint: ## Syntax-check all Python files
	$(PYTHON) -c "import ast, pathlib; \
	  files = list(pathlib.Path('app').rglob('*.py')); \
	  [ast.parse(f.read_text()) for f in files]; \
	  print(f'✓ {len(files)} files OK')"

check: lint test ## Run lint + tests

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/
