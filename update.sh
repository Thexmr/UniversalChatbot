#!/bin/bash
# UniversalChatbot Update Script
# Pulls latest changes and updates dependencies

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}"
echo "  _   _ _   _ ___  ___ ___________ _   _ "
echo "  | | | | | | ||  \/  ||  _  | ___ \ | | |"
echo "  | | | | | | || .  . || | | | |_/ / | | |"
echo "  | | | | | | || |\/| || | | |    /| | | |"
echo "  | |_| | |_| || |  | |\ \_/ / |\ \\ |_|_|"
echo "   \___/ \___/ \_|  |_/ \___/\_| \_|_____|"
echo -e "${NC}"
echo ""

# Check if it's a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}[ERROR] Not a git repository!${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/5] Checking git status...${NC}"
BRANCH=$(git branch --show-current)
REMOTE=$(git config --get remote.origin.url)
echo -e "    Branch: ${GREEN}$BRANCH${NC}"
echo -e "    Remote: ${GREEN}$REMOTE${NC}"
echo ""

echo -e "${YELLOW}[2/5] Stashing local changes (if any)...${NC}"
if git diff-index --quiet HEAD --; then
    echo -e "    ${GREEN}No local changes to stash${NC}"
else
    git stash push -m "Auto-stash before update $(date)"
    echo -e "    ${GREEN}Changes stashed${NC}"
fi
echo ""

echo -e "${YELLOW}[3/5] Fetching updates...${NC}"
git fetch origin
if [ $? -eq 0 ]; then
    echo -e "    ${GREEN}✓ Fetch successful${NC}"
else
    echo -e "    ${RED}✗ Fetch failed${NC}"
    exit 1
fi
echo ""

# Check if there are updates
echo -e "${YELLOW}[4/5] Checking for updates...${NC}"
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})
BASE=$(git merge-base @ @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "    ${GREEN}Already up to date!${NC}"
elif [ "$LOCAL" = "$BASE" ]; then
    echo -e "    ${YELLOW}Updates available!${NC}"
    git log --oneline HEAD..origin/$BRANCH | head -5
    echo ""
    
    echo -e "${YELLOW}Merging updates...${NC}"
    git merge origin/$BRANCH
    echo -e "    ${GREEN}✓ Merge successful${NC}"
elif [ "$REMOTE" = "$BASE" ]; then
    echo -e "    ${YELLOW}Local commits need push${NC}"
else
    echo -e "    ${RED}Diverged from remote! Manual fix required.${NC}"
    exit 1
fi
echo ""

# Update dependencies
echo -e "${YELLOW}[5/5] Updating Python dependencies...${NC}"
if [ -d ".venv" ]; then
    source ".venv/bin/activate"
    cd backend
    pip install -r requirements.txt --upgrade --quiet
    echo -e "    ${GREEN}✓ Dependencies updated${NC}"
else
    echo -e "    ${YELLOW}No venv found. Run setup first.${NC}"
fi
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Update complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  ${BLUE}Restart UniversalChatbot:${NC}"
echo -e "    ./start.sh"
echo ""
