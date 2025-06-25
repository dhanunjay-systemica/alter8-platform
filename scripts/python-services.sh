#!/bin/bash

# Python FastAPI Services Management Script

PYTHON_SERVICES=(
    "auth-service"
    "property-service"
    "document-service"
    "tenant-service"
    "lease-service"
    "agent-service"
    "verification-service"
    "payment-service"
    "analytics-service"
)

case "$1" in
    "install")
        echo "Installing Python service dependencies..."
        for service in "${PYTHON_SERVICES[@]}"; do
            if [ -d "services/$service" ]; then
                echo "Installing dependencies for $service..."
                cd "services/$service"
                if [ -f "requirements.txt" ]; then
                    pip install -r requirements.txt
                elif [ -f "pyproject.toml" ]; then
                    pip install -e .
                fi
                cd ../..
            fi
        done
        ;;
    "dev")
        echo "Starting Python services in development mode..."
        for service in "${PYTHON_SERVICES[@]}"; do
            if [ -d "services/$service" ]; then
                echo "Starting $service..."
                cd "services/$service"
                if [ -f "main.py" ]; then
                    uvicorn main:app --reload --port $(( 8000 + $(echo $service | wc -c) )) &
                fi
                cd ../..
            fi
        done
        ;;
    "test")
        echo "Running tests for Python services..."
        for service in "${PYTHON_SERVICES[@]}"; do
            if [ -d "services/$service" ]; then
                echo "Testing $service..."
                cd "services/$service"
                if [ -f "pytest.ini" ] || [ -d "tests" ]; then
                    pytest
                fi
                cd ../..
            fi
        done
        ;;
    "lint")
        echo "Linting Python services..."
        for service in "${PYTHON_SERVICES[@]}"; do
            if [ -d "services/$service" ]; then
                echo "Linting $service..."
                cd "services/$service"
                if command -v ruff &> /dev/null; then
                    ruff check .
                elif command -v flake8 &> /dev/null; then
                    flake8 .
                fi
                cd ../..
            fi
        done
        ;;
    *)
        echo "Usage: $0 {install|dev|test|lint}"
        echo "  install - Install dependencies for all Python services"
        echo "  dev     - Start all Python services in development mode"
        echo "  test    - Run tests for all Python services"
        echo "  lint    - Lint all Python services"
        exit 1
        ;;
esac