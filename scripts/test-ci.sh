#!/bin/bash
# Local CI Test Script
# Mimics the GitHub Actions workflow for local testing

set -e  # Exit on any error

echo "🧪 Running Local CI Test Pipeline"
echo "=================================="

echo ""
echo "📦 Installing dependencies..."
uv sync --dev

echo ""
echo "🔍 Running linting checks..."
uv run ruff check src/ tests/ --diff
uv run ruff format src/ tests/ --check

echo ""
echo "🚀 Running unit and component tests..."
uv run pytest tests/ -m "not integration" -v --tb=short

echo ""
echo "🔄 Running integration tests with timeout protection..."
timeout 45 uv run pytest tests/ -m integration -v --tb=short

echo ""
echo "📊 Running coverage analysis..."
uv run pytest tests/ -m "not integration" --cov=src --cov-report=term-missing --cov-report=html

echo ""
echo "✅ All CI checks passed!"
echo "======================="
echo "Your code is ready for CI/CD pipeline."
echo ""
echo "Coverage report available at: htmlcov/index.html"
echo "Log files available at: /tmp/mcp_chain_integration/" 