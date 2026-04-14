.PHONY: sync format lint ty tests coverage check build-docs serve-docs help

help:
	@echo "Available commands:"
	@echo "  make sync          - Install/sync all dependencies"
	@echo "  make format        - Format code with ruff"
	@echo "  make lint          - Run linter (ruff check)"
	@echo "  make ty            - Run type checker"
	@echo "  make tests         - Run tests (without coverage)"
	@echo "  make coverage      - Run tests with coverage report"
	@echo "  make check         - Run all checks (format, lint, ty, tests)"
	@echo "  make build-docs    - Build documentation"
	@echo "  make serve-docs    - Serve documentation locally"
	@echo "  make help          - Show this help message"

.PHONY: sync
sync:
	uv sync --all-extras

.PHONY: format
format:
	uv run ruff format cortex_agents/ examples/ tests/
	uv run ruff check --fix cortex_agents/ examples/ tests/

.PHONY: lint
lint:
	uv run ruff check cortex_agents/ examples/ tests/

.PHONY: ty
ty:
	uv run ty check cortex_agents/

.PHONY: tests
tests:
	uv run pytest

.PHONY: coverage
coverage:
	uv run coverage run -m pytest
	uv run coverage xml -o coverage.xml
	uv run coverage report -m --fail-under=80
	uv run coverage html

.PHONY: check
check: format lint ty tests

.PHONY: build-docs
build-docs:
	uv run mkdocs build

.PHONY: serve-docs
serve-docs:
	uv run mkdocs serve
