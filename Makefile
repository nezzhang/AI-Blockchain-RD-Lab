.PHONY: install dev lint format typecheck test test-cov clean

# Install runtime dependencies (uv if available, else pip)
install:
	@if command -v uv >/dev/null 2>&1; then uv sync --all-extras; \
	else pip install -e ".[analytics,dev]"; fi

dev: install lint typecheck test

lint:
	ruff check src tests scripts

format:
	ruff check --fix src tests scripts
	ruff format src tests scripts

typecheck:
	mypy

test:
	pytest

test-cov:
	pytest --cov=blockchain_rd_lab --cov-report=term-missing

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
