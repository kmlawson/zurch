# Makefile for zurch project

.PHONY: help install test test-verbose lint lint-fix format clean build dev-install reinstall check-all versionbump

# Default target
help:
	@echo "Available targets:"
	@echo "  help         - Show this help message"
	@echo "  install      - Install zurch using uv"
	@echo "  dev-install  - Install zurch in development mode"
	@echo "  reinstall    - Reinstall zurch (uninstall, clean cache, install)"
	@echo "  test         - Run all tests"
	@echo "  test-verbose - Run tests with verbose output"
	@echo "  lint         - Run ruff linting checks"
	@echo "  lint-fix     - Run ruff linting with auto-fix"
	@echo "  format       - Alias for lint-fix"
	@echo "  check-all    - Run all checks (lint + tests)"
	@echo "  build        - Build the package"
	@echo "  clean        - Clean build artifacts"
	@echo "  install-hooks - Install git pre-commit hooks"
	@echo "  versionbump  - Bump version number in all files (auto-increments patch or use VERSION=x.y.z)"

# Installation targets
install:
	@echo "Installing zurch..."
	uv tool install .

dev-install:
	@echo "Installing zurch in development mode..."
	uv sync

reinstall:
	@echo "Reinstalling zurch..."
	uv tool uninstall zurch || true
	uv cache clean
	uv tool install .

# Testing targets
test:
	@echo "Running tests..."
	uv run pytest tests/

test-verbose:
	@echo "Running tests with verbose output..."
	uv run pytest tests/ -v

# Linting targets
lint:
	@echo "Running ruff linting checks..."
	uv run ruff check .

lint-fix:
	@echo "Running ruff linting with auto-fix..."
	uv run ruff check --fix .

format: lint-fix

# Combined checks
check-all: lint test
	@echo "All checks passed!"

# Build targets
build:
	@echo "Building package..."
	uv build

clean:
	@echo "Cleaning build artifacts..."
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Development shortcuts
dev: dev-install
	@echo "Development environment ready!"

ci: check-all
	@echo "CI checks completed!"

# Package management
sync:
	@echo "Syncing dependencies..."
	uv sync

lock:
	@echo "Updating lock file..."
	uv lock

# Testing with different options
test-fast:
	@echo "Running tests (fast mode)..."
	uv run pytest tests/ -x

test-coverage:
	@echo "Running tests with coverage..."
	uv run pytest tests/ --cov=zurch --cov-report=html

# Specific test targets
test-pydantic:
	@echo "Running Pydantic model tests..."
	uv run pytest tests/test_pydantic_models.py -v

test-database:
	@echo "Running database tests..."
	uv run pytest tests/test_database.py -v

test-handlers:
	@echo "Running handler tests..."
	uv run pytest tests/test_handlers.py -v

# Git hooks
install-hooks:
	@echo "Installing git hooks..."
	@cp scripts/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed successfully."

# Documentation
docs:
	@echo "Available documentation:"
	@echo "  README.md - Main documentation"
	@echo "  CHANGELOG.md - Version history"
	@echo "  DEVELOPMENT.md - Development guide"
	@echo "  TODO.md - Planned features"

# Version management
version:
	@echo "Current version:"
	@uv run python -c "import zurch; print(zurch.__version__)"

# Quick development cycle
dev-cycle: lint-fix test
	@echo "Development cycle complete!"

# Release preparation
release-check: check-all build
	@echo "Release checks passed!"
	@echo "Ready for release!"

# Version management
versionbump:
	@# Get current version from pyproject.toml
	@CURRENT_VERSION=$$(grep 'version = ' pyproject.toml | cut -d'"' -f2); \
	if [ -z "$(VERSION)" ]; then \
		echo "No VERSION specified, auto-incrementing patch version..."; \
		NEW_VERSION=$$(echo $$CURRENT_VERSION | awk -F. '{print $$1"."$$2"."$$3+1}'); \
		echo "Current version: $$CURRENT_VERSION"; \
		echo "New version: $$NEW_VERSION"; \
	else \
		NEW_VERSION="$(VERSION)"; \
		echo "Current version: $$CURRENT_VERSION"; \
		echo "Specified version: $$NEW_VERSION"; \
	fi; \
	echo "Bumping version to $$NEW_VERSION..."; \
	# Get current date in YYYY-MM-DD format \
	TODAY=$$(date +%Y-%m-%d); \
	# Determine which sed to use (gsed on macOS, sed on Linux) \
	if command -v gsed >/dev/null 2>&1; then \
		SED_CMD="gsed"; \
	else \
		SED_CMD="sed"; \
	fi; \
	# Update pyproject.toml \
	$$SED_CMD -i "s/version = \"[^\"]*\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	# Update __init__.py \
	$$SED_CMD -i "s/__version__ = \"[^\"]*\"/__version__ = \"$$NEW_VERSION\"/" zurch/__init__.py; \
	# Update cli.py \
	$$SED_CMD -i "s/__version__ = \"[^\"]*\"/__version__ = \"$$NEW_VERSION\"/" zurch/cli.py; \
	# Update constants.py \
	$$SED_CMD -i "s/zurch\/[^\"]*\"/zurch\/$$NEW_VERSION\"/" zurch/constants.py; \
	# Update README.md badge \
	$$SED_CMD -i "s/PyPI-v[^-]*-blue/PyPI-v$$NEW_VERSION-blue/" README.md; \
	# Update CHANGELOG.md (add new version header) \
	$$SED_CMD -i "1,/^## \[/s/^## \[.*/## [$$NEW_VERSION] - $$TODAY\n\n### Changes\n- TBD\n\n&/" CHANGELOG.md; \
	echo "Version bumped to $$NEW_VERSION in all files"
	@echo "Remember to:"
	@echo "  1. Update CHANGELOG.md with actual changes"
	@echo "  2. Commit changes: git add . && git commit -m 'Bump version to $$NEW_VERSION'"
	@echo "  3. Build and deploy: make clean build && uv run twine upload dist/*"

# Default target when no arguments provided
.DEFAULT_GOAL := help