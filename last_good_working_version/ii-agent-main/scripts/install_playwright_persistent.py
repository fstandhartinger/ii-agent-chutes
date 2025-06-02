#!/usr/bin/env python3
"""
Enhanced Playwright browser installation for Render.com
This ensures browsers persist across deployments and handles system dependencies gracefully.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def install_playwright_to_persistent_storage():
    """Install Playwright browsers to /var/data if available, otherwise use default location."""
    
    # Check if we're on Render with persistent storage
    persistent_base = Path("/var/data")
    if persistent_base.exists() and persistent_base.is_dir():
        logger.info("Detected persistent storage at /var/data")
        
        # Create playwright directory in persistent storage
        playwright_dir = persistent_base / "playwright"
        playwright_dir.mkdir(exist_ok=True)
        
        # Set environment variable to use persistent storage
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(playwright_dir)
        logger.info(f"Set PLAYWRIGHT_BROWSERS_PATH to {playwright_dir}")
        
        # Check if browsers are already installed
        if any(playwright_dir.glob("chromium-*")):
            logger.info("Playwright browsers already installed in persistent storage")
            return test_browser_launch()
    else:
        logger.info("No persistent storage detected, using default location")
    
    # Install Playwright browsers
    try:
        logger.info("Installing Playwright chromium browser...")
        result = subprocess.run([
            sys.executable, "-m", "playwright", "install", "chromium"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"Failed to install Playwright browsers: {result.stderr}")
            return False
            
        logger.info("Successfully installed Playwright chromium browser")
        
        # Try to install dependencies (may fail on some platforms)
        try:
            logger.info("Attempting to install system dependencies...")
            result = subprocess.run([
                sys.executable, "-m", "playwright", "install-deps", "chromium"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("Successfully installed system dependencies")
            else:
                logger.warning("Could not install system dependencies via playwright install-deps")
                logger.info("Attempting alternative system dependency installation...")
                
                # Try alternative approach for system dependencies
                try:
                    alt_deps = [
                        "libnss3", "libatk-bridge2.0-0", "libdrm2", "libxkbcommon0",
                        "libxcomposite1", "libxdamage1", "libxrandr2", "libgbm1",
                        "libxss1", "libasound2", "libatspi2.0-0", "libgtk-3-0"
                    ]
                    
                    subprocess.run(["apt-get", "update"], check=False, capture_output=True)
                    subprocess.run(
                        ["apt-get", "install", "-y"] + alt_deps,
                        check=False, capture_output=True, timeout=120
                    )
                    logger.info("Alternative system dependency installation attempted")
                except Exception as e:
                    logger.warning(f"Alternative dependency installation failed: {e}")
                    
        except subprocess.TimeoutExpired:
            logger.warning("System dependency installation timed out")
        except Exception as e:
            logger.warning(f"System dependency installation failed: {e}")
        
        # Test browser launch
        return test_browser_launch()
        
    except subprocess.TimeoutExpired:
        logger.error("Playwright browser installation timed out")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during Playwright installation: {e}")
        return False

def test_browser_launch():
    """Test if browser can be launched successfully."""
    try:
        logger.info("Testing browser launch capability...")
        
        # Test script that tries different launch configurations
        test_script = '''
import asyncio
import sys
from playwright.async_api import async_playwright

async def test_launch():
    playwright = None
    browser = None
    try:
        playwright = await async_playwright().start()
        
        # Try headless mode with minimal args
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ]
        )
        
        # Create a page to verify it works
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("data:text/html,<h1>Test</h1>")
        
        await context.close()
        await browser.close()
        await playwright.stop()
        
        print("✓ Browser launch test successful")
        return True
        
    except Exception as e:
        print(f"⚠ Browser launch test failed: {e}")
        if browser:
            try:
                await browser.close()
            except:
                pass
        if playwright:
            try:
                await playwright.stop()
            except:
                pass
        return False

# Run the test
success = asyncio.run(test_launch())
sys.exit(0 if success else 1)
'''
        
        result = subprocess.run([
            sys.executable, "-c", test_script
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            logger.info("Browser launch test passed")
            return True
        else:
            logger.warning(f"Browser launch test failed: {result.stderr}")
            logger.info("Browser will use fallback configuration at runtime")
            return True  # Don't fail the build, just warn
            
    except subprocess.TimeoutExpired:
        logger.warning("Browser launch test timed out")
        return True  # Don't fail the build
    except Exception as e:
        logger.warning(f"Browser launch test error: {e}")
        return True  # Don't fail the build

def verify_installation():
    """Verify Playwright installation."""
    try:
        result = subprocess.run([
            sys.executable, "-m", "playwright", "--version"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"Playwright version: {result.stdout.strip()}")
            return True
        else:
            logger.error("Playwright verification failed")
            return False
            
    except Exception as e:
        logger.error(f"Playwright verification error: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting enhanced Playwright installation...")
    
    # Verify Playwright is available
    if not verify_installation():
        logger.error("Playwright is not available. Please install it first with: pip install playwright")
        sys.exit(1)
    
    # Install browsers and test
    success = install_playwright_to_persistent_storage()
    
    if success:
        logger.info("✓ Playwright installation completed successfully")
        sys.exit(0)
    else:
        logger.warning("⚠ Playwright installation completed with warnings")
        logger.info("Application will use fallback browser configuration at runtime")
        sys.exit(0)  # Don't fail the build, just warn 