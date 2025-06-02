#!/bin/bash
# Render.com build script
# This script handles the complete build process for Render.com deployment

set -e  # Exit on any error

echo "Starting Render.com build process..."

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install the application
echo "Installing application dependencies..."
pip install .

# Install Playwright browsers
echo "Installing Playwright browsers..."
python -m playwright install chromium

# Install system dependencies (may fail in some environments, that's ok)
echo "Installing Playwright system dependencies..."
python -m playwright install-deps chromium || echo "Warning: Could not install system dependencies (this may be expected in some environments)"

# Verify Playwright installation
echo "Verifying Playwright installation..."
python -m playwright --version

echo "Build process completed successfully!"
echo "Playwright browsers are ready for use." 