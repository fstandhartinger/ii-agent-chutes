#!/usr/bin/env python3
"""
Script to install and configure code-server for VS Code web interface.
This provides a web-based VS Code editor accessible via browser.
"""

import subprocess
import sys
import logging
import os
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_code_server():
    """Install code-server using the official installation script."""
    try:
        logger.info("Installing code-server...")
        
        # Download and run the installation script
        result = subprocess.run([
            "curl", "-fsSL", "https://code-server.dev/install.sh"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Pipe the script to sh
            install_result = subprocess.run([
                "sh"
            ], input=result.stdout, text=True, timeout=300)
            
            if install_result.returncode == 0:
                logger.info("Successfully installed code-server")
                return True
            else:
                logger.error(f"Failed to install code-server: {install_result.stderr}")
                return False
        else:
            logger.error(f"Failed to download code-server installer: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Code-server installation timed out")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during code-server installation: {e}")
        return False

def configure_code_server():
    """Configure code-server with appropriate settings."""
    try:
        logger.info("Configuring code-server...")
        
        # Create config directory
        config_dir = os.path.expanduser("~/.config/code-server")
        os.makedirs(config_dir, exist_ok=True)
        
        # Create configuration
        config = {
            'bind-addr': '0.0.0.0:8080',
            'auth': 'none',
            'password': '',
            'cert': False
        }
        
        config_path = os.path.join(config_dir, "config.yaml")
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        logger.info(f"Code-server configuration written to {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error configuring code-server: {e}")
        return False

def create_startup_script():
    """Create a startup script for code-server."""
    try:
        logger.info("Creating code-server startup script...")
        
        script_content = '''#!/bin/bash
# Start code-server in the background
export PATH="$HOME/.local/bin:$PATH"
cd /opt/render/project/src/workspace
code-server --bind-addr 0.0.0.0:8080 --auth none &
echo "Code-server started on port 8080"
'''
        
        script_path = "/opt/render/project/start-code-server.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        logger.info(f"Startup script created at {script_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating startup script: {e}")
        return False

def check_code_server_installation():
    """Check if code-server is installed and working."""
    try:
        result = subprocess.run([
            "code-server", "--version"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Code-server version: {result.stdout.strip()}")
            return True
        else:
            logger.error("Code-server is not installed or not working")
            return False
            
    except Exception as e:
        logger.error(f"Error checking code-server installation: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting code-server installation and configuration...")
    
    # Install code-server
    if not install_code_server():
        logger.error("Code-server installation failed")
        sys.exit(1)
    
    # Configure code-server
    if not configure_code_server():
        logger.error("Code-server configuration failed")
        sys.exit(1)
    
    # Create startup script
    if not create_startup_script():
        logger.error("Startup script creation failed")
        sys.exit(1)
    
    # Verify installation
    if check_code_server_installation():
        logger.info("Code-server installation and configuration completed successfully")
        sys.exit(0)
    else:
        logger.error("Code-server installation verification failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 