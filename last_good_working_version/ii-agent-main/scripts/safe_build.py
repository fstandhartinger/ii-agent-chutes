#!/usr/bin/env python3
"""
Safe build script for deployment environments.
This script handles Playwright installation gracefully when system dependencies cannot be installed.
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(command, description, allow_failure=False):
    """Run a command and handle errors appropriately."""
    logger.info(f"{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        if allow_failure:
            logger.warning(f"⚠ {description} failed (this may be expected): {e.stderr}")
            return False
        else:
            logger.error(f"✗ {description} failed: {e.stderr}")
            sys.exit(1)

def main():
    """Main build process."""
    logger.info("Starting safe build process...")
    
    # Upgrade pip
    run_command("pip install --upgrade pip", "Upgrading pip")
    
    # Install the application
    run_command("pip install .", "Installing application dependencies")
    
    # Install Playwright browsers
    run_command("python -m playwright install chromium", "Installing Playwright browsers")
    
    # Try to install system dependencies (allow failure)
    success = run_command(
        "python -m playwright install-deps chromium", 
        "Installing Playwright system dependencies",
        allow_failure=True
    )
    
    if not success:
        logger.info("System dependencies could not be installed. This is expected on some hosting platforms.")
        logger.info("The application will automatically fall back to headless mode with minimal configuration.")
    
    # Verify Playwright installation
    run_command("python -m playwright --version", "Verifying Playwright installation")
    
    logger.info("✓ Build process completed successfully!")
    logger.info("Note: If browser launch fails at runtime, the application will automatically use fallback options.")

if __name__ == "__main__":
    main() 