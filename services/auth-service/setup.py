#!/usr/bin/env python3
"""
Setup script for Auth Service development environment
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command: str, cwd: str = None) -> bool:
    """Run a shell command and return success status"""
    try:
        result = subprocess.run(
            command.split(),
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {command}")
        print(f"Error: {e.stderr}")
        return False


def setup_auth_service():
    """Set up the auth service development environment"""
    
    service_dir = Path(__file__).parent
    os.chdir(service_dir)
    
    print("🚀 Setting up Alter8 Auth Service...")
    print(f"📁 Working directory: {service_dir}")
    
    # Check if uv is installed
    if not run_command("uv --version"):
        print("❌ uv is not installed. Please install it first:")
        print("curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False
    
    # Create virtual environment and install dependencies
    print("\n📦 Installing dependencies with uv...")
    if not run_command("uv sync"):
        return False
    
    # Install development dependencies
    print("\n🔧 Installing development dependencies...")
    if not run_command("uv sync --dev"):
        return False
    
    # Set up pre-commit hooks
    print("\n🔗 Setting up pre-commit hooks...")
    run_command("uv run pre-commit install")
    
    # Run code formatting
    print("\n🎨 Formatting code with ruff...")
    run_command("uv run ruff format .")
    
    # Run linting
    print("\n🔍 Running linter...")
    run_command("uv run ruff check . --fix")
    
    # Run type checking
    print("\n🔬 Running type checks...")
    run_command("uv run mypy app")
    
    print("\n✅ Auth Service setup complete!")
    print("\n📝 Next steps:")
    print("1. Copy .env.example to .env and configure your settings")
    print("2. Start the database: docker-compose up postgres redis")
    print("3. Run migrations: uv run alembic upgrade head")
    print("4. Start the service: uv run uvicorn app.main:app --reload")
    
    return True


if __name__ == "__main__":
    success = setup_auth_service()
    sys.exit(0 if success else 1)