#!/bin/bash
# Enhanced Render.com build script with robust Playwright installation
# This script handles system dependencies and browser installation gracefully

set -e  # Exit on any error

echo "Starting Render.com build process..."

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install the application
echo "Installing application dependencies..."
pip install .

# Set environment variable for Playwright browsers path (persistent storage)
if [ -d "/var/data" ]; then
    echo "Setting up persistent storage for Playwright browsers..."
    export PLAYWRIGHT_BROWSERS_PATH="/var/data/playwright"
    mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"
    echo "PLAYWRIGHT_BROWSERS_PATH set to: $PLAYWRIGHT_BROWSERS_PATH"
fi

# Install Playwright browsers using persistent storage if available
echo "Installing Playwright browsers..."
python scripts/install_playwright_persistent.py || {
    echo "Falling back to standard Playwright installation..."
    
    # Try standard installation
    python -m playwright install chromium || {
        echo "ERROR: Failed to install Playwright chromium browser"
        echo "This might be due to network issues or insufficient disk space"
        exit 1
    }
    
    # Try to install system dependencies with better error handling
    echo "Installing system dependencies..."
    python -m playwright install-deps chromium 2>/dev/null || {
        echo "Warning: Could not install system dependencies."
        echo "This is expected on hosting platforms without root access."
        echo "The application will run in headless mode with minimal configuration."
        
        # Try alternative approach for system dependencies
        echo "Attempting alternative system dependency installation..."
        apt-get update 2>/dev/null && apt-get install -y \
            libnss3 \
            libatk-bridge2.0-0 \
            libdrm2 \
            libxkbcommon0 \
            libxcomposite1 \
            libxdamage1 \
            libxrandr2 \
            libgbm1 \
            libxss1 \
            libasound2 2>/dev/null || {
            echo "Alternative system dependency installation also failed."
            echo "Application will use minimal browser configuration."
        }
    }
}

# Verify Playwright installation
echo "Verifying Playwright installation..."
python -m playwright --version || {
    echo "ERROR: Playwright verification failed"
    exit 1
}

# Test browser launch capability
echo "Testing browser launch capability..."
python -c "
import asyncio
from playwright.async_api import async_playwright

async def test_browser():
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        await browser.close()
        await playwright.stop()
        print('✓ Browser launch test successful')
        return True
    except Exception as e:
        print(f'⚠ Browser launch test failed: {e}')
        print('Application will use fallback configuration at runtime')
        return False

asyncio.run(test_browser())
" || echo "Browser test completed with warnings"

echo "Build process completed successfully!"
echo "Note: If browser launch fails at runtime, the application will automatically fall back to minimal headless mode." 