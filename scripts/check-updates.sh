#!/bin/bash
#
# UniversalChatbot Update Checker Script
# Run this periodically to check for and install updates
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "==================================="
echo "UniversalChatbot Update Checker"
echo "==================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed"
    exit 1
fi

# Check for updates
echo "🔍 Checking for updates..."
python3 scripts/update.py --check

# If update is available and --auto flag is set
if [[ "$1" == "--auto" ]]; then
    echo ""
    echo "📦 Auto-installing update..."
    python3 scripts/update.py --apply --restart
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ Auto-update completed successfully"
        exit 0
    else
        echo "❌ Auto-update failed"
        exit 1
    fi
fi

# Interactive mode with auto-apply option
if [[ "$1" == "--auto-apply" ]]; then
    echo ""
    echo "📦 Installing update..."
    python3 scripts/update.py --apply --restart
fi

echo ""
echo "To install any available update, run: ./scripts/check-updates.sh --auto-apply"