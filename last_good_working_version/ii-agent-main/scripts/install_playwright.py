#!/usr/bin/env python3
"""
Script to install Playwright browsers for deployment environments.
This should be run during the deployment process to ensure browsers are available.
"""

import subprocess
import sys
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_playwright_browsers():
    """Install Playwright browsers."""
    try:
        logger.info("Installing Playwright browsers...")
        
        # Install chromium browser
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("Successfully installed Playwright chromium browser")
            logger.info(f"Output: {result.stdout}")
        else:
            logger.error(f"Failed to install Playwright browsers: {result.stderr}")
            return False
            
        # Install system dependencies
        logger.info("Installing system dependencies...")
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install-deps", "chromium"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("Successfully installed system dependencies")
            logger.info(f"Output: {result.stdout}")
        else:
            logger.warning(f"Failed to install system dependencies (this might be expected in some environments): {result.stderr}")
            
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Playwright installation timed out")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during Playwright installation: {e}")
        return False

def check_playwright_installation():
    """Check if Playwright browsers are installed."""
    try:
        result = subprocess.run([
            sys.executable, "-m", "playwright", "--version"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Playwright version: {result.stdout.strip()}")
            return True
        else:
            logger.error("Playwright is not installed")
            return False
            
    except Exception as e:
        logger.error(f"Error checking Playwright installation: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting Playwright browser installation...")
    
    # Check if Playwright is available
    if not check_playwright_installation():
        logger.error("Playwright is not available. Please install it first with: pip install playwright")
        sys.exit(1)
    
    # Install browsers
    if install_playwright_browsers():
        logger.info("Playwright browser installation completed successfully")
        sys.exit(0)
    else:
        logger.error("Playwright browser installation failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 