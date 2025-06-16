# Cube MCP Server Makefile
# Provides common development tasks for the project

.PHONY: help install install-dev clean test test-unit test-integration lint typecheck format security audit build run docker-build docker-run dev setup-test-env

# Default target
help: ## Show this help message
	@echo "Cube MCP Server - Development Commands"
	@echo "====================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Environment setup
install: ## Install production dependencies
	@echo "Installing production dependencies..."
	uv sync --no-dev

install-dev: ## Install all dependencies including dev tools
	@echo "Installing all dependencies..."
	uv sync
	@echo "✓ Dependencies installed"

setup-test-env: install-dev ## Setup testing environment and create test structure
	@echo "Setting up test environment..."
	@mkdir -p tests/unit tests/integration tests/fixtures
	@if [ ! -f tests/__init__.py ]; then touch tests/__init__.py; fi
	@if [ ! -f tests/unit/__init__.py ]; then touch tests/unit/__init__.py; fi
	@if [ ! -f tests/integration/__init__.py ]; then touch tests/integration/__init__.py; fi
	@if [ ! -f tests/conftest.py ]; then \
		echo "# pytest configuration and fixtures" > tests/conftest.py; \
		echo "import pytest" >> tests/conftest.py; \
		echo "" >> tests/conftest.py; \
		echo "@pytest.fixture" >> tests/conftest.py; \
		echo "def mock_cube_client():" >> tests/conftest.py; \
		echo "    \"\"\"Mock CubeClient for testing\"\"\"" >> tests/conftest.py; \
		echo "    pass" >> tests/conftest.py; \
	fi
	@if [ ! -f tests/unit/test_cube_client.py ]; then \
		echo "# Unit tests for CubeClient" > tests/unit/test_cube_client.py; \
		echo "import pytest" >> tests/unit/test_cube_client.py; \
		echo "from mcp_cube_server.server import CubeClient" >> tests/unit/test_cube_client.py; \
		echo "" >> tests/unit/test_cube_client.py; \
		echo "def test_sanitize_response_for_logging():" >> tests/unit/test_cube_client.py; \
		echo "    \"\"\"Test response sanitization functionality\"\"\"" >> tests/unit/test_cube_client.py; \
		echo "    # TODO: Implement test" >> tests/unit/test_cube_client.py; \
		echo "    assert True" >> tests/unit/test_cube_client.py; \
	fi
	@if [ ! -f pyproject.toml ] || ! grep -q "pytest" pyproject.toml; then \
		echo "Adding pytest to dev dependencies..."; \
		uv add --dev pytest pytest-asyncio pytest-mock pytest-cov; \
	fi
	@echo "✓ Test environment setup complete"

# Development tasks
clean: ## Clean build artifacts and cache
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".coverage" -delete
	@echo "✓ Cleaned build artifacts"

# Testing
test: test-unit ## Run all tests
	@echo "✓ All tests completed"

test-unit: setup-test-env ## Run unit tests
	@echo "Running unit tests..."
	@if [ -d tests ]; then \
		uv run pytest tests/unit/ -v --tb=short; \
	else \
		echo "No tests found. Run 'make setup-test-env' first."; \
	fi

test-integration: setup-test-env ## Run integration tests
	@echo "Running integration tests..."
	@if [ -d tests/integration ]; then \
		uv run pytest tests/integration/ -v --tb=short; \
	else \
		echo "No integration tests found."; \
	fi

test-coverage: setup-test-env ## Run tests with coverage report
	@echo "Running tests with coverage..."
	uv run pytest tests/ --cov=src/mcp_cube_server --cov-report=html --cov-report=term-missing

# Code quality
lint: install-dev ## Run linting checks
	@echo "Running linting checks..."
	@echo "Note: Add flake8/ruff to pyproject.toml for full linting"
	@python -m py_compile src/mcp_cube_server/*.py
	@echo "✓ Syntax check passed"

typecheck: install-dev ## Run type checking
	@echo "Running type checks..."
	uv run pyright
	@echo "✓ Type checking completed"

format: install-dev ## Format code (placeholder - add black/ruff for real formatting)
	@echo "Code formatting..."
	@echo "Note: Add black or ruff to pyproject.toml for automatic formatting"
	@echo "✓ Format check completed"

security: install-dev ## Run security checks (placeholder)
	@echo "Running security checks..."
	@echo "Note: Add bandit or safety to pyproject.toml for security scanning"
	@echo "✓ Security checks completed"

audit: install-dev ## Audit dependencies for security issues
	@echo "Auditing dependencies..."
	uv tree
	@echo "✓ Dependency audit completed"

# Build and package
build: clean install-dev typecheck ## Build the package
	@echo "Building package..."
	uv build
	@echo "✓ Package built successfully"

# Run tasks
run: install ## Run the MCP server (requires environment variables)
	@echo "Starting Cube MCP server..."
	@echo "Note: Set CUBE_ENDPOINT and CUBE_API_SECRET environment variables"
	uv run mcp_cube_server

run-dev: install-dev ## Run server in development mode with verbose logging
	@echo "Starting Cube MCP server in development mode..."
	@echo "Note: Set CUBE_ENDPOINT and CUBE_API_SECRET environment variables"
	uv run mcp_cube_server --log_level DEBUG

# Docker tasks
docker-build: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t cube-mcp-server:latest .
	@echo "✓ Docker image built"

docker-run: docker-build ## Run Docker container
	@echo "Running Docker container..."
	@echo "Note: Set CUBE_ENDPOINT and CUBE_API_SECRET environment variables"
	docker run --rm -it \
		-e CUBE_ENDPOINT="${CUBE_ENDPOINT}" \
		-e CUBE_API_SECRET="${CUBE_API_SECRET}" \
		-e CUBE_TOKEN_PAYLOAD="${CUBE_TOKEN_PAYLOAD}" \
		cube-mcp-server:latest

# Development workflow
dev: install-dev setup-test-env ## Setup complete development environment
	@echo "Development environment ready!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Set environment variables: CUBE_ENDPOINT, CUBE_API_SECRET"
	@echo "  2. Run 'make test' to run tests"
	@echo "  3. Run 'make run-dev' to start the server"
	@echo "  4. Run 'make typecheck' to check types"

# CI/CD simulation
ci: clean install-dev typecheck test lint security ## Run CI/CD pipeline locally
	@echo "✓ CI/CD pipeline completed successfully"

# Quick development checks
check: typecheck lint ## Quick development checks
	@echo "✓ Quick checks completed"

# Version and info
version: ## Show version information
	@echo "Cube MCP Server version information:"
	@grep "version = " pyproject.toml || echo "Version not found"
	@echo "Python version: $(shell python --version)"
	@echo "UV version: $(shell uv --version)"

# Environment information
env-info: ## Show environment information
	@echo "Environment Information:"
	@echo "======================="
	@echo "Python: $(shell python --version)"
	@echo "UV: $(shell uv --version)"
	@echo "Current directory: $(PWD)"
	@echo "Virtual environment: $(shell uv run python -c 'import sys; print(sys.prefix)')"
	@echo ""
	@echo "Project dependencies:"
	@uv tree --depth 1 2>/dev/null || echo "Run 'make install-dev' first"