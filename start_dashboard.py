#!/usr/bin/env python3
"""
UniversalChatbot - Dashboard Starter
Simple script to start the web dashboard
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from dashboard.app import start_dashboard

if __name__ == "__main__":
    print("=" * 50)
    print("UniversalChatbot Dashboard")
    print("=" * 50)
    print("Starting server on http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        start_dashboard(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
        sys.exit(0)
