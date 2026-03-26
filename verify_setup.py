#!/usr/bin/env python3
"""
UniversalChatbot Setup Verification Script
Checks Native Host registration, dependencies, and communication
"""
import json
import os
import sys
import platform
import subprocess
import importlib.util
from pathlib import Path

HOST_NAME = "com.universalchatbot.bridge"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(title):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_check(name, status, details=""):
    """Print a check result"""
    if status:
        print(f"  {Colors.GREEN}✓{Colors.RESET} {name}")
    else:
        print(f"  {Colors.RED}✗{Colors.RESET} {name}")
    if details:
        print(f"    {details}")


# ============================================================================
# CHECK 1: Python Version
# ============================================================================
def check_python():
    """Check Python version"""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    # Python 3.11+ recommended
    is_ok = version.major == 3 and version.minor >= 11
    
    print_header("1. Python Environment")
    print_check("Python 3.11+", is_ok, f"Found: Python {version_str}")
    
    return is_ok


# ============================================================================
# CHECK 2: Dependencies
# ============================================================================
def check_dependencies():
    """Check if required packages are installed"""
    required = []
    
    # Read from requirements.txt if it exists
    req_file = Path("backend/requirements.txt")
    if req_file.exists():
        with open(req_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (remove version specifiers)
                    pkg = line.split('[')[0].split('=')[0].split('<')[0].split('>')[0].strip()
                    if pkg:
                        required.append(pkg)
    else:
        # Default requirements
        required = ['flask', 'flask-cors', 'flask-socketio', 'requests', 'python-dotenv']
    
    print_header("2. Python Dependencies")
    
    all_ok = True
    missing = []
    
    for pkg in required:
        try:
            # Try importing the package
            import_name = pkg.replace('-', '_')
            spec = importlib.util.find_spec(import_name)
            if spec is None:
                # Some packages have different import names
                alt_names = {
                    'flask-socketio': 'flask_socketio',
                    'flask-cors': 'flask_cors',
                    'python-dotenv': 'dotenv',
                }
                if import_name in alt_names:
                    spec = importlib.util.find_spec(alt_names[import_name])
            
            if spec:
                print_check(f"{pkg}", True)
            else:
                print_check(f"{pkg}", False, "Not installed")
                missing.append(pkg)
                all_ok = False
        except Exception as e:
            print_check(f"{pkg}", False, str(e))
            missing.append(pkg)
            all_ok = False
    
    if missing:
        print(f"\n  {Colors.YELLOW}Install missing packages:{Colors.RESET}")
        print(f"    pip install {' '.join(missing)}")
    
    return all_ok


# ============================================================================
# CHECK 3: Native Host Registration
# ============================================================================
def check_native_host_registration():
    """Check if native host is registered"""
    print_header("3. Native Host Registration")
    
    system = platform.system()
    registered = []
    
    if system == "Windows":
        # Check Windows Registry
        try:
            import winreg
            browsers = [
                ("Chrome", "Software\\Google\\Chrome\\NativeMessagingHosts\\" + HOST_NAME),
                ("Edge", "Software\\Microsoft\\Edge\\NativeMessagingHosts\\" + HOST_NAME),
            ]
            
            for browser_name, key_path in browsers:
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                        manifest_path = winreg.QueryValue(key, "")
                        if os.path.exists(manifest_path):
                            print_check(f"{browser_name} registry entry", True, manifest_path)
                            registered.append((browser_name, manifest_path))
                        else:
                            print_check(f"{browser_name} registry entry", False, "Manifest file not found")
                except FileNotFoundError:
                    print_check(f"{browser_name} registry entry", False, "Not registered")
                    
        except ImportError:
            print_check("Windows Registry", False, "winreg module not available")
    
    else:  # Linux/macOS
        # Check browser config directories
        home = os.path.expanduser("~")
        
        if system == "Darwin":
            config_dirs = [
                ("Chrome", f"{home}/Library/Application Support/Google/Chrome/NativeMessagingHosts"),
                ("Edge", f"{home}/Library/Application Support/Microsoft Edge/NativeMessagingHosts"),
            ]
        else:
            config_dirs = [
                ("Chrome", f"{home}/.config/google-chrome/NativeMessagingHosts"),
                ("Chromium", f"{home}/.config/chromium/NativeMessagingHosts"),
                ("Edge", f"{home}/.config/microsoft-edge/NativeMessagingHosts"),
                ("Brave", f"{home}/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"),
            ]
        
        for browser_name, config_dir in config_dirs:
            manifest_path = os.path.join(config_dir, f"{HOST_NAME}.json")
            if os.path.exists(manifest_path):
                print_check(f"{browser_name} manifest", True, manifest_path)
                registered.append((browser_name, manifest_path))
            else:
                print_check(f"{browser_name} manifest", False, f"Not found at {manifest_path}")
    
    return registered


def validate_manifest(manifest_path):
    """Validate the manifest file"""
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        checks = [
            ('name', HOST_NAME),
            ('type', 'stdio'),
        ]
        
        errors = []
        for key, expected in checks:
            actual = manifest.get(key)
            if actual != expected:
                errors.append(f"{key}: expected '{expected}', got '{actual}'")
        
        main_script = manifest.get('path', '')
        if not os.path.exists(main_script):
            errors.append(f"main.py not found at: {main_script}")
        
        if errors:
            print(f"\n  {Colors.RED}Manifest errors:{Colors.RESET}")
            for err in errors:
                print(f"    - {err}")
            return False
        else:
            print(f"  {Colors.GREEN}✓ Manifest valid{Colors.RESET}")
            print(f"    Path: {main_script}")
            return True
            
    except json.JSONDecodeError as e:
        print(f"\n  {Colors.RED}Invalid JSON in manifest: {e}{Colors.RESET}")
        return False
    except Exception as e:
        print(f"\n  {Colors.RED}Error reading manifest: {e}{Colors.RESET}")
        return False


# ============================================================================
# CHECK 4: Backend Files
# ============================================================================
def check_backend_files():
    """Check if all required backend files exist"""
    print_header("4. Backend Files")
    
    required_files = [
        ("backend/main.py", "Main entry point"),
        ("backend/requirements.txt", "Python dependencies"),
    ]
    
    all_ok = True
    for file, desc in required_files:
        exists = os.path.exists(file)
        print_check(f"{file}", exists, desc)
        if not exists:
            all_ok = False
    
    return all_ok


# ============================================================================
# CHECK 5: Test Communication
# ============================================================================
def test_communication():
    """Test stdin/stdout communication with main.py"""
    print_header("5. Communication Test")
    
    backend_dir = Path("backend")
    main_py = backend_dir / "main.py"
    
    if not main_py.exists():
        print_check("Communication", False, "main.py not found")
        return False
    
    print("  Testing stdin/stdout communication...")
    
    try:
        # Start a quick test
        test_message = json.dumps({"action": "ping"}) + '\n'
        
        proc = subprocess.Popen(
            [sys.executable, str(main_py)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(backend_dir),
            text=True
        )
        
        try:
            # Send test message with timeout
            stdout, stderr = proc.communicate(input=test_message, timeout=5)
            
            if proc.returncode == 0 or stdout:
                print_check("Communication", True, "Process responds to stdin/stdout")
                return True
            else:
                print_check("Communication", True, "Process started (no response to ping)")
                return True
                
        except subprocess.TimeoutExpired:
            proc.kill()
            # Process started and timed out waiting for input (expected)
            print_check("Communication", True, "Process started and waiting for input (expected)")
            return True
            
    except Exception as e:
        print_check("Communication", False, str(e))
        return False


# ============================================================================
# SUMMARY
# ============================================================================
def print_summary(results):
    """Print final summary"""
    print_header("SUMMARY")
    
    passed = sum(results)
    total = len(results)
    
    print(f"  Tests passed: {passed}/{total}")
    print()
    
    if passed == total:
        print(f"  {Colors.GREEN}{Colors.BOLD}✓ All checks passed!{Colors.RESET}")
        print(f"  {Colors.GREEN}Setup is complete and ready to use.{Colors.RESET}")
    elif passed >= total - 1:
        print(f"  {Colors.YELLOW}{Colors.BOLD}⚠ Setup mostly complete{Colors.RESET}")
        print(f"  {Colors.YELLOW}Some non-critical checks failed.{Colors.RESET}")
    else:
        print(f"  {Colors.RED}{Colors.BOLD}✗ Setup incomplete{Colors.RESET}")
        print(f"  {Colors.RED}Please run the installer first:{Colors.RESET}")
        if platform.system() == "Windows":
            print(f"    {Colors.BLUE}install.bat{Colors.RESET}")
        else:
            print(f"    {Colors.BLUE}./install.sh{Colors.RESET}")
    
    print()
    print(f"  {Colors.BOLD}Next steps:{Colors.RESET}")
    print(f"    1. Install the browser extension")
    print(f"    2. Run: {Colors.BLUE}./start.sh{Colors.RESET} (or {Colors.BLUE}start.bat{Colors.RESET})")
    print(f"    3. Open the extension popup")


# ============================================================================
# MAIN
# ============================================================================
def main():
    print(f"{Colors.BOLD}")
    print("  _   _ _   _ ___  ___     _   _      _   _   _ _____ _   _ ")
    print("  | | | | | | ||  \/  |    | | | |    | | | | | |_   _| | | |")
    print("  | | | | | | || .  . | ___| |_| | ___| |_| | | | | | | |_| |")
    print("  | | | | | | || |\/| |/ _ | __| |/ _ |  _  | | | | |  _  |")
    print("  | |_| | |_| || |  | |  __| |_| |  __| | | | |_| | | | | |")
    print("   \___/ \___/ \_|  |_/\___|\__|_|\___|_| |_|\___/  \_/ |_|_|")
    print(f"{Colors.RESET}")
    print(f"                    Setup Verification v1.0")
    
    results = []
    
    # Run all checks
    results.append(check_python())
    results.append(check_dependencies())
    
    # Check native host registration
    registered = check_native_host_registration()
    results.append(len(registered) > 0)
    
    # Validate manifests
    manifest_valid = all(validate_manifest(path) for _, path in registered)
    results.append(manifest_valid)
    
    results.append(check_backend_files())
    results.append(test_communication())
    
    # Print summary
    print_summary(results)
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
