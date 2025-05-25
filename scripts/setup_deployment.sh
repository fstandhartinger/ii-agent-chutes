#!/bin/bash
# Setup script for deployment environments
# This script should be run during the build/deployment process

set -e  # Exit on any error

echo "Setting up deployment environment..."

# Install Playwright browsers
echo "Installing Playwright browsers..."
python -m playwright install chromium

# Install system dependencies (may fail in some environments, that's ok)
echo "Installing system dependencies..."
python -m playwright install-deps chromium || echo "Warning: Could not install system dependencies (this may be expected in some environments)"

# Verify installation
echo "Verifying Playwright installation..."
python -m playwright --version

echo "Deployment setup completed successfully!" 