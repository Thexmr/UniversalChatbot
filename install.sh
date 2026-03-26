#!/bin/bash
set -e

echo "============================================"
echo "  UniversalChatbot Native Host Installer"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
echo "[1/4] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 not found!${NC}"
    echo "Please install Python 3.11+ from your package manager"
    exit 1
fi

echo -e "${GREEN}[OK] Python version:${NC}"
python3 --version
echo ""

# Install Python dependencies
echo "[2/4] Installing Python dependencies..."
cd backend
if [ -f "requirements.txt" ]; then
    if ! pip3 install -r requirements.txt; then
        echo -e "${RED}[ERROR] Failed to install dependencies${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}[WARNING] requirements.txt not found, skipping pip install${NC}"
fi
echo ""

# Return to script directory
cd "$SCRIPT_DIR"

# Setup Native Messaging Host
echo "[3/4] Registering Native Messaging Host..."
python3 setup_unix.py
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Failed to register Native Messaging Host${NC}"
    exit 1
fi
echo ""

# Create desktop entry
echo "[4/4] Creating desktop entry..."
DESKTOP_FILE="$HOME/.local/share/applications/universalchatbot.desktop"
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=UniversalChatbot
Comment=AI Chat Assistant for your browser
Exec=python3 $SCRIPT_DIR/backend/main.py
Icon=$SCRIPT_DIR/icons/icon48.png
Type=Application
Terminal=true
Categories=Network;WebBrowser;
EOF

chmod +x "$DESKTOP_FILE"
echo -e "${GREEN}[OK] Desktop entry created: $DESKTOP_FILE${NC}"
echo ""

# Summary
echo "============================================"
echo "  Installation Complete!"
echo "============================================"
echo ""
echo -e "${GREEN}Native Host registered:${NC} com.universalchatbot.bridge"
echo "Manifest location: ~/.config/google-chrome/NativeMessagingHosts/"
echo "Desktop entry: $DESKTOP_FILE"
echo ""
echo "Supported browsers: Google Chrome, Chromium, Microsoft Edge"
echo ""
echo "Run verification:"
echo "  python3 verify_setup.py"
echo ""
echo "Quick start:"
echo "  ./start.sh"
echo ""

# Detect OS for browser-specific paths
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}Note (macOS):${NC} The manifest is also registered at:"
    echo "  ~/Library/Application Support/Google/Chrome/NativeMessagingHosts/"
fi
echo ""
