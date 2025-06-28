#!/bin/bash
# Test runner script for Docker environment
set -e

echo "🧪 Running ML Pipeline Tests in Docker Environment"
echo "=================================================="

# Ensure we're in the ml_pipeline directory
cd /app/ml_pipeline

# Install test dependencies if not already installed
echo "📦 Installing test dependencies..."
python -m pip install pytest pytest-cov pytest-mock pytest-asyncio pytest-xdist seaborn tabulate

# Run different types of tests based on argument
case "${1:-all}" in
    "unit")
        echo "🔧 Running Unit Tests..."
        python -m pytest tests/unit/ -v --tb=short -m "not slow"
        ;;
    "integration") 
        echo "🔗 Running Integration Tests..."
        python -m pytest tests/integration/ -v --tb=short -m "integration"
        ;;
    "quick")
        echo "⚡ Running Quick Tests (no coverage)..."
        python -m pytest tests/ -v --tb=short -m "not slow" --no-cov
        ;;
    "coverage")
        echo "📊 Running Tests with Coverage..."
        python -m pytest tests/ --cov=src/ml_pipeline --cov-report=term-missing --cov-report=html:htmlcov --cov-fail-under=70
        ;;
    "simple")
        echo "🔄 Running Simple Setup Tests..."
        python -m pytest tests/test_simple_example.py -v --no-cov
        ;;
    "all"|*)
        echo "🚀 Running All Tests..."
        python -m pytest tests/ -v --tb=short --no-cov
        ;;
esac

echo "✅ Tests completed!"