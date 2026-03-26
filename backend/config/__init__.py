"""
Config Package - Konfigurationsmanagement für UniversalChatbot.
"""

from pathlib import Path
import yaml


def load_settings(config_path: str = None) -> dict:
    """
    Lädt die Konfiguration aus settings.yaml.
    
    Args:
        config_path: Optionaler Pfad zur Config-Datei
    
    Returns:
        Konfiguration als Dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent / "settings.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


__all__ = ["load_settings"]