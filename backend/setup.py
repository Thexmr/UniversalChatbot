#!/usr/bin/env python3
"""
Setup-Skript für UniversalChatbot Native Messaging Host.
Registriert den Host für Chrome Extension.
"""

import os
import sys
import json
import argparse
from pathlib import Path


def get_windows_registry_script(extension_id: str, host_name: str, manifest_path: str) -> str:
    """
    Erstellt Windows Registry Script für Native Messaging.
    
    Args:
        extension_id: Die Chrome Extension ID
        host_name: Name des Hosts
        manifest_path: Absoluter Pfad zur Manifest-Datei
    
    Returns:
        Registry-Script als String
    """
    key_path = f"SOFTWARE\\Google\\Chrome\\NativeMessagingHosts\\{host_name}"
    
    script = f"""Windows Registry Editor Version 5.00

[{key_path}]
@="{manifest_path.replace('\\\\', '\\\\\\\\')}"
"""
    return script


def create_manifest(
    host_path: str,
    host_name: str = "com.universalchatbot.nativehost",
    extension_ids: list = None
) -> dict:
    """
    Erstellt das Native Messaging Manifest.
    
    Args:
        host_path: Absoluter Pfad zum Python-Skript
        host_name: Name für den Host
        extension_ids: Liste erlaubter Extension-IDs
    
    Returns:
        Manifest als Dictionary
    """
    manifest = {
        "name": host_name,
        "description": "UniversalChatbot Native Messaging Host",
        "path": host_path,
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{ext_id}/"
            for ext_id in (extension_ids or ["*"])  # Platzhalter für Entwicklung
        ]
    }
    return manifest


def install_windows(extension_id: str = None, host_name: str = "com.universalchatbot.nativehost"):
    """
    Installiert den Native Host auf Windows.
    
    Args:
        extension_id: Optional die echte Extension ID
        host_name: Name des Hosts
    """
    print("=== Windows Native Host Installation ===\n")
    
    # Pfade ermitteln
    backend_dir = Path(__file__).parent.resolve()
    python_exe = sys.executable
    main_script = backend_dir / "main.py"
    
    # Host-Wrapper erstellen (BAT für Windows)
    bat_path = backend_dir / "native_host.bat"
    with open(bat_path, "w") as f:
        f.write(f'@echo off\n')
        f.write(f'"{python_exe}" "{main_script}" %*\n')
    
    # Manifest erstellen
    manifest = create_manifest(
        host_path=str(bat_path),
        host_name=host_name,
        extension_ids=[extension_id] if extension_id else ["*"]
    )
    
    manifest_path = backend_dir / "native_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Manifest erstellt: {manifest_path}")
    print(f"Host-Skript: {bat_path}")
    
    # Registry-Script erstellen
    reg_script = get_windows_registry_script(
        extension_id or "*",
        host_name,
        str(manifest_path)
    )
    
    reg_path = backend_dir / "install_host.reg"
    with open(reg_path, "w") as f:
        f.write(reg_script)
    
    print(f"Registry-Script erstellt: {reg_path}")
    print("\n=== Installation abschließen ===")
    print("1. Doppelklicke 'install_host.reg' um die Registry zu aktualisieren")
    print("2. Chrome muss ggf. neu gestartet werden")
    print(f"3. Extension ID: {extension_id or '[DEINE_EXTENSION_ID]'}")
    
    return True


def install_linux(extension_id: str = None, host_name: str = "com.universalchatbot.nativehost"):
    """
    Installiert den Native Host auf Linux.
    
    Args:
        extension_id: Optional die echte Extension ID
        host_name: Name des Hosts
    """
    print("=== Linux Native Host Installation ===\n")
    
    # Pfade ermitteln
    backend_dir = Path(__file__).parent.resolve()
    home_dir = Path.home()
    
    # Installationsziel
    config_dir = home_dir / ".config" / "google-chrome" / "NativeMessagingHosts"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Host-Wrapper erstellen
    host_script = backend_dir / "main.py"
    
    manifest = create_manifest(
        host_path=str(host_script),
        host_name=host_name,
        extension_ids=[extension_id] if extension_id else ["*"]
    )
    
    manifest_path = config_dir / f"{host_name}.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Host ausführbar machen
    manifest_path.chmod(0o644)
    
    print(f"Manifest installiert: {manifest_path}")
    print(f"Host-Skript: {host_script}")
    print("\n=== Installation abgeschlossen ===")
    print(f"Extension ID: {extension_id or '[DEINE_EXTENSION_ID]'}")
    
    return True


def install_macos(extension_id: str = None, host_name: str = "com.universalchatbot.nativehost"):
    """
    Installiert den Native Host auf macOS.
    
    Args:
        extension_id: Optional die echte Extension ID
        host_name: Name des Hosts
    """
    print("=== macOS Native Host Installation ===\n")
    
    # Pfade ermitteln
    backend_dir = Path(__file__).parent.resolve()
    home_dir = Path.home()
    
    # Installationsziel (Chrome)
    config_dir = home_dir / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Host-Skript
    host_script = backend_dir / "main.py"
    
    manifest = create_manifest(
        host_path=str(host_script),
        host_name=host_name,
        extension_ids=[extension_id] if extension_id else ["*"]
    )
    
    manifest_path = config_dir / f"{host_name}.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Manifest installiert: {manifest_path}")
    print(f"Host-Skript: {host_script}")
    print("\n=== Installation abgeschlossen ===")
    print(f"Extension ID: {extension_id or '[DEINE_EXTENSION_ID]'}")
    
    return True


def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(
        description="UniversalChatbot Native Host Setup"
    )
    parser.add_argument(
        "--extension-id",
        help="Chrome Extension ID (optional, '*' für Entwicklung)"
    )
    parser.add_argument(
        "--host-name",
        default="com.universalchatbot.nativehost",
        help="Name für den Native Host"
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Deinstalliert den Native Host"
    )
    
    args = parser.parse_args()
    
    if args.uninstall:
        print("Deinstallation wird noch nicht unterstützt.")
        return
    
    # Plattform-spezifische Installation
    if sys.platform == "win32":
        install_windows(args.extension_id, args.host_name)
    elif sys.platform == "darwin":
        install_macos(args.extension_id, args.host_name)
    else:
        install_linux(args.extension_id, args.host_name)


if __name__ == "__main__":
    main()