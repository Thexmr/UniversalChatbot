#!/usr/bin/env python3
"""
Unix/Linux/macOS Native Messaging Host Setup for UniversalChatbot
Registers the native host with Chrome/Edge/Chromium
"""
import json
import os
import sys
import platform

HOST_NAME = "com.universalchatbot.bridge"


def get_backend_path():
    """Get the absolute path to main.py"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_path = os.path.join(script_dir, "backend", "main.py")
    return os.path.abspath(backend_path)


def get_config_dirs():
    """Get browser config directories based on OS"""
    home = os.path.expanduser("~")
    system = platform.system()
    
    config_dirs = []
    
    if system == "Darwin":  # macOS
        config_dirs = [
            os.path.join(home, "Library/Application Support/Google/Chrome/NativeMessagingHosts"),
            os.path.join(home, "Library/Application Support/Microsoft Edge/NativeMessagingHosts"),
            os.path.join(home, "Library/Application Support/Chromium/NativeMessagingHosts"),
        ]
    else:  # Linux and other Unix
        config_dirs = [
            os.path.join(home, ".config/google-chrome/NativeMessagingHosts"),
            os.path.join(home, ".config/chromium/NativeMessagingHosts"),
            os.path.join(home, ".config/microsoft-edge/NativeMessagingHosts"),
            os.path.join(home, ".config/BraveSoftware/Brave-Browser/NativeMessagingHosts"),
        ]
    
    return config_dirs


def register_native_host():
    """Register the native messaging host"""
    main_py_path = get_backend_path()
    
    if not os.path.exists(main_py_path):
        print(f"[ERROR] main.py not found at: {main_py_path}")
        print("Make sure you're running this from the project root directory.")
        sys.exit(1)
    
    MANIFEST = {
        "name": HOST_NAME,
        "description": "UniversalChatbot Native Host",
        "path": main_py_path,
        "type": "stdio",
        "allowed_origins": [
            "chrome-extension://*/",
            "chrome-extension://*/"
        ]
    }
    
    config_dirs = get_config_dirs()
    created_manifests = []
    
    for config_dir in config_dirs:
        try:
            os.makedirs(config_dir, exist_ok=True)
            manifest_path = os.path.join(config_dir, f"{HOST_NAME}.json")
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(MANIFEST, f, indent=2)
            
            created_manifests.append((config_dir, manifest_path))
            print(f"[OK] Manifest created: {manifest_path}")
            
        except PermissionError as e:
            print(f"[WARNING] Permission denied for {config_dir}: {e}")
        except Exception as e:
            print(f"[WARNING] Failed to create manifest in {config_dir}: {e}")
    
    if not created_manifests:
        print("[ERROR] Failed to create any manifest files!")
        sys.exit(1)
    
    print(f"\n[✓] Successfully registered: {HOST_NAME}")
    print(f"    Main script: {main_py_path}")
    
    return created_manifests


def verify_registration(created_manifests):
    """Verify the registration was successful"""
    print("\n[Verification]")
    all_ok = True
    
    for config_dir, manifest_path in created_manifests:
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                main_script = manifest.get('path', '')
                script_exists = os.path.exists(main_script)
                
                print(f"  ✓ {config_dir}")
                print(f"    Manifest: OK")
                print(f"    Script exists: {'Yes' if script_exists else 'No'}")
                
                if not script_exists:
                    all_ok = False
                    
            except json.JSONDecodeError:
                print(f"  ✗ {config_dir}")
                print(f"    Manifest: Invalid JSON")
                all_ok = False
        else:
            print(f"  ✗ {config_dir}")
            print(f"    Manifest: Not found")
            all_ok = False
    
    return all_ok


def check_browser_running():
    """Check if Chrome/Chromium is running"""
    import subprocess
    
    browsers = ["chrome", "chromium", "brave", "edge", "Google Chrome"]
    running = []
    
    for browser in browsers:
        try:
            result = subprocess.run(
                ["pgrep", "-i", browser],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                running.append(browser)
        except:
            pass
    
    if running:
        print(f"\n[Note] Detected running browsers: {', '.join(running)}")
        print("       You may need to restart them for changes to take effect.")


if __name__ == "__main__":
    print("=" * 50)
    if platform.system() == "Darwin":
        print("UniversalChatbot Native Host Setup (macOS)")
    else:
        print("UniversalChatbot Native Host Setup (Linux/Unix)")
    print("=" * 50)
    print()
    
    created_manifests = register_native_host()
    verify_registration(created_manifests)
    check_browser_running()
