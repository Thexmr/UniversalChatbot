#!/usr/bin/env python3
"""
Windows Native Messaging Host Setup for UniversalChatbot
Registers the native host with Chrome/Edge
"""
import json
import winreg
import os
import sys

HOST_NAME = "com.universalchatbot.bridge"


def get_backend_path():
    """Get the absolute path to main.py"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_path = os.path.join(script_dir, "backend", "main.py")
    return os.path.abspath(backend_path)


def register_native_host():
    """Register the native messaging host in Windows Registry"""
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
    
    # Write manifest to home directory
    manifest_dir = os.path.expanduser("~/.universalchatbot")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, "native-host.json")
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(MANIFEST, f, indent=2)
    
    print(f"[OK] Manifest written to: {manifest_path}")
    
    # Register in Windows Registry
    # Support both Chrome and Edge
    browsers = [
        ("Chrome", "Software\\Google\\Chrome\\NativeMessagingHosts\\" + HOST_NAME),
        ("Edge", "Software\\Microsoft\\Edge\\NativeMessagingHosts\\" + HOST_NAME),
    ]
    
    for browser_name, key_path in browsers:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValue(key, "", winreg.REG_SZ, manifest_path)
            print(f"[OK] Registered for {browser_name}")
        except Exception as e:
            print(f"[WARNING] Failed to register for {browser_name}: {e}")
    
    print(f"\n[✓] Successfully registered: {HOST_NAME}")
    print(f"    Main script: {main_py_path}")
    
    return manifest_path


def verify_registration():
    """Verify the registration was successful"""
    try:
        key_path = f"Software\\Google\\Chrome\\NativeMessagingHosts\\{HOST_NAME}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            manifest_path = winreg.QueryValue(key, "")
            print(f"\n[Verification] Registry entry found:")
            print(f"    Manifest path: {manifest_path}")
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                print(f"    Main script exists: {os.path.exists(manifest.get('path', ''))}")
                return True
    except FileNotFoundError:
        print("\n[ERROR] Registry entry not found!")
        return False
    return False


if __name__ == "__main__":
    print("=" * 50)
    print("UniversalChatbot Native Host Setup (Windows)")
    print("=" * 50)
    print()
    
    manifest = register_native_host()
    verify_registration()
