#!/usr/bin/env python3
"""
UniversalChatbot Auto-Updater Module
Handles version checking and update management
"""
import requests
import json
import os
import hashlib
import logging
from packaging import version
from pathlib import Path
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)

# Repository configuration
REPO_OWNER = "Thexmr"
REPO_NAME = "UniversalChatbot"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

# Version file path
VERSION_FILE = Path(__file__).parent / "VERSION"


class AutoUpdater:
    """Auto-updater class for UniversalChatbot"""
    
    def __init__(self):
        self.current_version = self._load_current_version()
        self.repo_url = f"{GITHUB_API_URL}/releases/latest"
        self._latest_release: Optional[Dict[str, Any]] = None
        
    def _load_current_version(self) -> str:
        """Load current version from VERSION file"""
        try:
            if VERSION_FILE.exists():
                with open(VERSION_FILE, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load version file: {e}")
        return "0.1.0"
    
    def get_current_version(self) -> str:
        """Get current installed version"""
        return self.current_version
    
    def check_for_updates(self) -> Dict[str, Any]:
        """
        Check for updates from GitHub releases
        
        Returns:
            Dict with update info or error status
        """
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'UniversalChatbot-Updater'
            }
            
            response = requests.get(
                self.repo_url, 
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            latest = response.json()
            self._latest_release = latest
            
            latest_version = latest['tag_name'].replace('v', '').replace('V', '')
            
            if version.parse(latest_version) > version.parse(self.current_version):
                return {
                    'available': True,
                    'current_version': self.current_version,
                    'version': latest_version,
                    'url': latest['html_url'],
                    'assets': self._process_assets(latest.get('assets', [])),
                    'release_notes': latest.get('body', ''),
                    'published_at': latest.get('published_at', ''),
                    'prerelease': latest.get('prerelease', False)
                }
            
            return {
                'available': False,
                'current_version': self.current_version,
                'latest_version': latest_version
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Update check failed - network error: {e}")
            return {
                'available': False,
                'error': f'Network error: {str(e)}',
                'current_version': self.current_version
            }
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            return {
                'available': False,
                'error': str(e),
                'current_version': self.current_version
            }
    
    def _process_assets(self, assets: List[Dict]) -> List[Dict]:
        """Process release assets to extract relevant info"""
        processed = []
        for asset in assets:
            processed.append({
                'name': asset.get('name', ''),
                'url': asset.get('browser_download_url', ''),
                'size': asset.get('size', 0),
                'content_type': asset.get('content_type', ''),
                'created_at': asset.get('created_at', '')
            })
        return processed
    
    def get_download_url(self, update_info: Dict[str, Any], 
                         asset_name: Optional[str] = None) -> Optional[str]:
        """
        Get download URL for update
        
        Args:
            update_info: Update info from check_for_updates()
            asset_name: Specific asset name (e.g., 'UniversalChatbot.zip')
        
        Returns:
            Download URL or None
        """
        assets = update_info.get('assets', [])
        
        if asset_name:
            for asset in assets:
                if asset['name'] == asset_name:
                    return asset['url']
        
        # Default: look for zip or tar.gz
        for asset in assets:
            if asset['name'].endswith('.zip') or asset['name'].endswith('.tar.gz'):
                return asset['url']
        
        return None
    
    def verify_checksum(self, file_path: Path, expected_hash: str, 
                        algorithm: str = 'sha256') -> bool:
        """
        Verify file checksum
        
        Args:
            file_path: Path to downloaded file
            expected_hash: Expected hash value
            algorithm: Hash algorithm ('sha256', 'md5', 'sha1')
        
        Returns:
            True if checksum matches
        """
        try:
            hash_func = getattr(hashlib, algorithm.lower())
            hasher = hash_func()
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            
            computed_hash = hasher.hexdigest()
            return computed_hash.lower() == expected_hash.lower()
            
        except Exception as e:
            logger.error(f"Checksum verification failed: {e}")
            return False
    
    def get_release_info(self) -> Optional[Dict[str, Any]]:
        """Get cached release info from last check"""
        return self._latest_release


class UpdateNotifier:
    """Handles update notifications to extension"""
    
    def __init__(self):
        self._pending_update: Optional[Dict[str, Any]] = None
        self._notification_sent = False
    
    def set_pending_update(self, update_info: Dict[str, Any]):
        """Set pending update info"""
        self._pending_update = update_info
        self._notification_sent = False
    
    def has_pending_update(self) -> bool:
        """Check if there's a pending update"""
        return self._pending_update is not None
    
    def get_pending_update(self) -> Optional[Dict[str, Any]]:
        """Get pending update info"""
        return self._pending_update
    
    def clear_pending_update(self):
        """Clear pending update after installation"""
        self._pending_update = None
        self._notification_sent = False
    
    def mark_notification_sent(self):
        """Mark that notification was sent"""
        self._notification_sent = True
    
    def was_notification_sent(self) -> bool:
        """Check if notification was already sent"""
        return self._notification_sent


# Global update notifier instance
update_notifier = UpdateNotifier()


def check_updates_sync() -> Dict[str, Any]:
    """Synchronous update check - for startup"""
    updater = AutoUpdater()
    result = updater.check_for_updates()
    
    if result.get('available'):
        update_notifier.set_pending_update(result)
    
    return result


def get_update_status() -> Dict[str, Any]:
    """Get current update status for UI"""
    updater = AutoUpdater()
    
    status = {
        'current_version': updater.get_current_version(),
        'has_update': update_notifier.has_pending_update(),
        'update_info': update_notifier.get_pending_update()
    }
    
    return status


def format_release_notes(notes: str) -> str:
    """Format release notes for display"""
    if not notes:
        return "No release notes available."
    
    # Remove markdown formatting for popup display
    clean_notes = notes.replace('## ', '').replace('### ', '')
    clean_notes = clean_notes.replace('**', '').replace('*', '')
    
    return clean_notes[:500] + '...' if len(clean_notes) > 500 else clean_notes


if __name__ == '__main__':
    # Test updater
    updater = AutoUpdater()
    print(f"Current version: {updater.get_current_version()}")
    
    result = updater.check_for_updates()
    print(f"Update check result: {json.dumps(result, indent=2)}")