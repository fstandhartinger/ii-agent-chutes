#!/bin/bash
# Render.com build script with VS Code server support
# This script handles the complete build process including code-server for VS Code integration

set -e  # Exit on any error

echo "Starting Render.com build process with VS Code support..."

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

# Install code-server for VS Code web interface
echo "Installing code-server..."
curl -fsSL https://code-server.dev/install.sh | sh

# Create code-server config directory
mkdir -p ~/.config/code-server

# Create code-server configuration
cat > ~/.config/code-server/config.yaml << EOF
bind-addr: 0.0.0.0:8080
auth: none
password: 
cert: false
EOF

echo "Creating code-server startup script..."
cat > /opt/render/project/start-code-server.sh << 'EOF'
#!/bin/bash
# Start code-server in the background
export PATH="$HOME/.local/bin:$PATH"
cd /opt/render/project/src/workspace
code-server --bind-addr 0.0.0.0:8080 --auth none &
echo "Code-server started on port 8080"
EOF

chmod +x /opt/render/project/start-code-server.sh

# Verify installations
echo "Verifying Playwright installation..."
python -m playwright --version

echo "Verifying code-server installation..."
code-server --version || echo "Code-server installation may need to be verified at runtime"

echo "Build process completed successfully!"
echo "Playwright browsers are ready for use."
echo "Code-server is configured and ready to start." 