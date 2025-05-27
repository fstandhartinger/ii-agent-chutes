#!/usr/bin/env python3
"""
Install Playwright browsers to persistent storage on Render.com
This ensures browsers persist across deployments.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_playwright_to_persistent_storage():
    """Install Playwright browsers to /var/data if available, otherwise use default location."""
    
    # Check if we're on Render with persistent storage
    persistent_base = Path("/var/data")
    if persistent_base.exists() and persistent_base.is_dir():
        print("Detected persistent storage at /var/data")
        
        # Create playwright directory in persistent storage
        playwright_dir = persistent_base / "playwright"
        playwright_dir.mkdir(exist_ok=True)
        
        # Set environment variable to use persistent storage
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(playwright_dir)
        print(f"Set PLAYWRIGHT_BROWSERS_PATH to {playwright_dir}")
        
        # Check if browsers are already installed
        chromium_path = playwright_dir / "chromium-*"
        if any(playwright_dir.glob("chromium-*")):
            print("Playwright browsers already installed in persistent storage")
            return True
    else:
        print("No persistent storage detected, using default location")
    
    # Install Playwright browsers
    try:
        print("Installing Playwright chromium browser...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("Successfully installed Playwright chromium browser")
        
        # Try to install dependencies (may fail on some platforms)
        try:
            print("Attempting to install system dependencies...")
            subprocess.run([sys.executable, "-m", "playwright", "install-deps", "chromium"], check=True)
            print("Successfully installed system dependencies")
        except subprocess.CalledProcessError:
            print("Warning: Could not install system dependencies (this is expected on some platforms)")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error installing Playwright: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = install_playwright_to_persistent_storage()
    sys.exit(0 if success else 1) 