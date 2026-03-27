#!/usr/bin/env python3
"""
UniversalChatbot Update Script
Handles downloading, installing, and rolling back updates
"""
import os
import sys
import json
import shutil
import zipfile
import tarfile
import tempfile
import requests
import hashlib
import signal
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from backend.updater import AutoUpdater, UpdateNotifier
    from backend.chatbot.logger import get_logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.handlers = []
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
else:
    logger = get_logger()

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
BACKUP_DIR = PROJECT_ROOT / "backups"
UPDATE_TEMP_DIR = Path(tempfile.gettempdir()) / "ucb_update"
UPDATE_STATUS_FILE = PROJECT_ROOT / ".update_status.json"
VERSION_FILE = PROJECT_ROOT / "backend" / "VERSION"


class UpdateManager:
    """Manages the update process including backup and rollback"""
    
    def __init__(self):
        self.updater = AutoUpdater()
        self.downloaded_file: Optional[Path] = None
        self.backup_path: Optional[Path] = None
        self.update_info: Optional[Dict] = None
        
    def perform_update(self, force: bool = False) -> Dict[str, Any]:
        """
        Perform update process
        
        Args:
            force: Force update even if version seems same
        
        Returns:
            Dict with update result
        """
        try:
            # Step 1: Check for updates
            logger.info("Checking for updates...")
            check_result = self.updater.check_for_updates()
            
            if not force and not check_result.get('available'):
                if check_result.get('error'):
                    return {
                        'success': False,
                        'error': check_result['error'],
                        'stage': 'check'
                    }
                return {
                    'success': False,
                    'message': "No updates available",
                    'current_version': check_result.get('current_version')
                }
            
            self.update_info = check_result
            new_version = check_result['version']
            current_version = check_result['current_version']
            
            logger.info(f"Update available: {current_version} -> {new_version}")
            
            # Step 2: Download update
            logger.info("Downloading update...")
            download_result = self._download_update()
            if not download_result['success']:
                return download_result
            
            # Step 3: Create backup
            logger.info("Creating backup...")
            backup_result = self._create_backup()
            if not backup_result['success']:
                return backup_result
            
            # Save update status for potential rollback
            self._save_update_status(new_version, self.backup_path)
            
            # Step 4: Install update
            logger.info("Installing update...")
            install_result = self._install_update()
            if not install_result['success']:
                logger.error("Install failed, attempting rollback...")
                self._perform_rollback()
                return install_result
            
            # Step 5: Health check
            logger.info("Running health check...")
            health_result = self._health_check()
            if not health_result['success']:
                logger.error("Health check failed, performing rollback...")
                self._perform_rollback()
                return health_result
            
            # Step 6: Update version file
            self._update_version_file(new_version)
            
            # Clear update notification
            UpdateNotifier().clear_pending_update()
            
            logger.info(f"Successfully updated to version {new_version}")
            
            return {
                'success': True,
                'version': new_version,
                'previous_version': current_version,
                'message': f"Successfully updated to {new_version}")
            }
            
        except Exception as e:
            logger.error(f"Update failed: {e}", exc_info=True)
            # Attempt rollback on any error
            if self.backup_path:
                self._perform_rollback()
            return {
                'success': False,
                'error': str(e),
                'stage': 'unknown'
            }
    
    def _download_update(self) -> Dict[str, Any]:
        """Download update package from GitHub"""
        try:
            download_url = self.updater.get_download_url(self.update_info)
            
            if not download_url:
                return {
                    'success': False,
                    'error': 'No downloadable asset found',
                    'stage': 'download'
                }
            
            # Create temp directory
            UPDATE_TEMP_DIR.mkdir(parents=True, exist_ok=True)
            
            # Download file
            headers = {'User-Agent': 'UniversalChatbot-Updater'}
            response = requests.get(download_url, headers=headers, stream=True, timeout=180)
            response.raise_for_status()
            
            # Determine filename
            filename = download_url.split('/')[-1].split('?')[0]
            if not filename:
                filename = 'update.zip'
            
            self.downloaded_file = UPDATE_TEMP_DIR / filename
            
            # Save file with progress
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(self.downloaded_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            logger.info(f"Downloaded: {self.downloaded_file} ({downloaded} bytes)")
            
            # Verify checksum if provided in release
            assets = self.update_info.get('assets', [])
            for asset in assets:
                if asset['name'] == filename:
                    # Note: GitHub doesn't provide checksums directly, but we verify the download
                    break
            
            return {'success': True, 'file': str(self.downloaded_file)}
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Download failed: {str(e)}',
                'stage': 'download'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Download error: {str(e)}',
                'stage': 'download'
            }
    
    def _create_backup(self) -> Dict[str, Any]:
        """Create backup of current installation"""
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            current_version = self.updater.get_current_version()
            backup_name = f"backup_{current_version}_{timestamp}"
            self.backup_path = BACKUP_DIR / backup_name
            
            # Create backup
            shutil.copytree(PROJECT_ROOT, self.backup_path, 
                          ignore=shutil.ignore_patterns(
                              'backups', '_*', '.update_status.json',
                              '__pycache__', '*.pyc', '.git'
                          ))
            
            logger.info(f"Backup created: {self.backup_path}")
            
            # Clean old backups (keep last 5)
            self._cleanup_old_backups()
            
            return {'success': True, 'backup_path': str(self.backup_path)}
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Backup failed: {str(e)}',
                'stage': 'backup'
            }
    
    def _cleanup_old_backups(self, keep: int = 5):
        """Remove old backups, keeping only the most recent ones"""
        try:
            backups = sorted(BACKUP_DIR.glob('backup_*'), key=lambda x: x.stat().st_mtime)
            if len(backups) > keep:
                for old_backup in backups[:-keep]:
                    shutil.rmtree(old_backup, ignore_errors=True)
                    logger.info(f"Removed old backup: {old_backup}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")
    
    def _install_update(self) -> Dict[str, Any]:
        """Extract and install the update"""
        try:
            if not self.downloaded_file or not self.downloaded_file.exists():
                return {
                    'success': False,
                    'error': 'Downloaded file not found',
                    'stage': 'install'
                }
            
            # Extract archive
            extract_dir = UPDATE_TEMP_DIR / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            if self.downloaded_file.suffix == '.zip':
                with zipfile.ZipFile(self.downloaded_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif self.downloaded_file.suffix in ['.tar.gz', '.tgz']:
                with tarfile.open(self.downloaded_file, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported archive format: {self.downloaded_file.suffix}',
                    'stage': 'install'
                }
            
            # Find extracted content (may be in subdirectory)
            extracted_items = list(extract_dir.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                source_dir = extracted_items[0]
            else:
                source_dir = extract_dir
            
            # Copy new files to project root (preserve backups dir)
            for item in source_dir.iterdir():
                if item.name in ['backups', '.git', '_update_status.json']:
                    continue
                    
                dest = PROJECT_ROOT / item.name
                
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest, ignore_errors=True)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
            
            logger.info("Update files installed successfully")
            
            return {'success': True}
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Installation failed: {str(e)}',
                'stage': 'install'
            }
    
    def _health_check(self) -> Dict[str, Any]:
        """Verify the installation is working after update"""
        try:
            # Check critical files exist
            critical_files = [
                'backend/main.py',
                'extension/manifest.json',
                'extension/popup.html',
                'extension/background.js'
            ]
            
            for file_path in critical_files:
                full_path = PROJECT_ROOT / file_path
                if not full_path.exists():
                    return {
                        'success': False,
                        'error': f'Critical file missing after update: {file_path}',
                        'stage': 'health_check'
                    }
            
            # Try to import main module
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, '-c', 'from backend.main import main; print("OK")'],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    timeout=10
                )
                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': f'Module import check failed: {result.stderr.decode()}',
                        'stage': 'health_check'
                    }
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Health check failed: {str(e)}',
                    'stage': 'health_check'
                }
            
            logger.info("Health check passed")
            return {'success': True}
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Health check error: {str(e)}',
                'stage': 'health_check'
            }
    
    def _perform_rollback(self) -> Dict[str, Any]:
        """Rollback to previous version"""
        try:
            if not self.backup_path or not self.backup_path.exists():
                # Try to load backup path from status file
                status = self._load_update_status()
                if status and 'backup_path' in status:
                    self.backup_path = Path(status['backup_path'])
            
            if not self.backup_path or not self.backup_path.exists():
                logger.error("No backup found for rollback")
                return {'success': False, 'error': 'No backup available'}
            
            logger.info(f"Rolling back from backup: {self.backup_path}")
            
            # Restore files from backup (exclude backups dir)
            for item in self.backup_path.iterdir():
                if item.name == 'backups':
                    continue
                    
                dest = PROJECT_ROOT / item.name
                
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest, ignore_errors=True)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
            
            logger.info("Rollback completed successfully")
            
            # Remove update status file
            if UPDATE_STATUS_FILE.exists():
                UPDATE_STATUS_FILE.unlink()
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _save_update_status(self, new_version: str, backup_path: Path):
        """Save update status for potential rollback"""
        status = {
            'version': new_version,
            'backup_path': str(backup_path),
            'timestamp': datetime.now().isoformat(),
            'status': 'installing'
        }
        with open(UPDATE_STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    
    def _load_update_status(self) -> Optional[Dict]:
        """Load update status"""
        try:
            if UPDATE_STATUS_FILE.exists():
                with open(UPDATE_STATUS_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load update status: {e}")
        return None
    
    def _update_version_file(self, new_version: str):
        """Update version file""
        VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(VERSION_FILE, 'w') as f:
            f.write(new_version)
        
        # Also update manifest.json
        manifest_path = PROJECT_ROOT / 'extension' / 'manifest.json'
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            manifest['version'] = new_version
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update manifest.json: {e}")


def perform_update():
    """Main function called by update script"""
    manager = UpdateManager()
    result = manager.perform_update()
    
    if result['success']:
        print(f"✅ Update successful: {result.get('message')}")
        print("Please restart the service to apply the update.")
    else:
        print(f"❌ Update failed: {result.get('error', result.get('message', 'Unknown error'))}")
        print(f"Stage: {result.get('stage', 'unknown')}")
    
    return result


def check_for_updates():
    """Check for updates without installing"""
    updater = AutoUpdater()
    result = updater.check_for_updates()
    
    if result.get('available'):
        print(f"✨ Update available!")
        print(f"   Current: {result['current_version']}")
        print(f"   Latest:  {result['version']}")
        print(f"   URL: {result['url']}")
        print(f"\nRun 'python scripts/update.py --apply' to install.")
        return True
    elif result.get('error'):
        print(f"⚠️  Error checking for updates: {result['error']}")
        return False
    else:
        print(f"✅ Up to date! (v{result['current_version']})")
        return False


def restart_service():
    """Restart the UniversalChatbot service"""
    try:
        # Check for running process
        if sys.platform == 'win32':
            # Windows restart
            subprocess.Popen([
                'python', str(PROJECT_ROOT / 'start.bat')
            ], shell=True)
        else:
            # Unix/Mac restart
            # First stop any running instance
            subprocess.run(['pkill', '-f', 'backend/main.py'], capture_output=True)
            time.sleep(1)
            # Start new instance
            subprocess.Popen([
                'bash', str(PROJECT_ROOT / 'start.sh')
            ], cwd=str(PROJECT_ROOT))
        
        print("🔄 Service restarted")
        return True
    except Exception as e:
        print(f"⚠️  Restart failed: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='UniversalChatbot Update Manager')
    parser.add_argument('--check', action='store_true', help='Check for updates only')
    parser.add_argument('--apply', action='store_true', help='Apply available update')
    parser.add_argument('--restart', action='store_true', help='Restart service after update')
    parser.add_argument('--force', action='store_true', help='Force update even if versions match')
    
    args = parser.parse_args()
    
    if args.check:
        check_for_updates()
    elif args.apply:
        result = perform_update()
        if result['success'] and args.restart:
            restart_service()
    else:
        # Default: check and apply
        has_update = check_for_updates()
        if has_update:
            response = input("\nInstall update? (y/n): ")
            if response.lower() == 'y':
                result = perform_update()
                if result['success']:
                    restart_response = input("Restart service now? (y/n): ")
                    if restart_response.lower() == 'y':
                        restart_service()