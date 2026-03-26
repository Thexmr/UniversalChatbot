#!/bin/bash
# UniversalChatbot Quick Start Script (Linux/Mac)
# Starts the backend with virtual environment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}"
echo "  _   _ _   _ ___  ___     _   _      _   _   _ _____ _   _ "
echo "  | | | | | | ||  \/  |    | | | |    | | | | | |_   _| | | |"
echo "  | | | | | | || .  . | ___| |_| | ___| |_| | | | | | | |_| |"
echo "  | | | | | | || |\/| |/ _ \ __| |/ _ \  _  | | | | |  _  |"
echo "  | |_| | |_| || |  | |  __/ |_| |  __/ | | | |_| | | | | |"
echo "   \___/ \___/ \_|  |_/\___|\__|_|\___|_| |_|\___/  \_/ |_|_|"
echo -e "${NC}"
echo ""

# Check if backend exists
if [ ! -d "backend" ]; then
    echo -e "${RED}[ERROR] backend directory not found!${NC}"
    exit 1
fi

# Setup virtual environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[1/3] Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}    ✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}[1/3] Virtual environment exists${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}[2/3] Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Install/update dependencies
echo -e "${YELLOW}[3/3] Checking dependencies...${NC}"
cd backend
pip install -q -r requirements.txt
echo -e "${GREEN}    ✓ Dependencies ready${NC}"

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}"
        echo "  [Note] .env file missing!"
        echo "  Copy .env.example to .env and configure your API keys"
        echo -e "${NC}"
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ UniversalChatbot is starting...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  ${BLUE}Backend:${NC} http://localhost:5000"
echo -e "  ${BLUE}WebSocket:${NC} ws://localhost:5000"
echo -e "  ${BLUE}Backend dir:${NC} $(pwd)"
echo ""
echo -e "  ${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Start the backend
python main.py
