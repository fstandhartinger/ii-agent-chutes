#!/bin/bash
# Safe Render.com build script that handles Playwright installation gracefully
# This script handles the case where system dependencies cannot be installed

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

# Try to install system dependencies, but don't fail if it doesn't work
echo "Attempting to install Playwright system dependencies..."
python -m playwright install-deps chromium 2>/dev/null || {
    echo "Warning: Could not install system dependencies. This is expected on some hosting platforms."
    echo "The application will attempt to run in headless mode with fallback options."
}

# Verify Playwright installation
echo "Verifying Playwright installation..."
python -m playwright --version

echo "Build process completed successfully!"
echo "Note: If browser launch fails at runtime, the application will automatically fall back to headless mode." 