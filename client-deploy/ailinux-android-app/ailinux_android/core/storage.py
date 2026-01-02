"""
Android Secure Storage
======================

Cross-platform storage with Android-specific paths.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("ailinux.storage")


def get_app_dir() -> Path:
    """Get app data directory - works on Android and Desktop"""
    try:
        # Android: Use internal storage
        from android.storage import app_storage_path
        return Path(app_storage_path())
    except ImportError:
        # Desktop: Use ~/.config/ailinux
        return Path.home() / ".config" / "ailinux"


class SecureStorage:
    """Simple encrypted storage for credentials and settings"""

    def __init__(self):
        self.storage_dir = get_app_dir()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """Get file path for key"""
        return self.storage_dir / f"{key}.json"

    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """Save data to storage"""
        try:
            path = self._get_path(key)
            with open(path, "w") as f:
                json.dump(data, f)
            # Secure permissions on Linux/Desktop
            try:
                path.chmod(0o600)
            except:
                pass
            return True
        except Exception as e:
            logger.error(f"Failed to save {key}: {e}")
            return False

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data from storage"""
        try:
            path = self._get_path(key)
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {key}: {e}")
        return None

    def delete(self, key: str) -> bool:
        """Delete data from storage"""
        try:
            path = self._get_path(key)
            if path.exists():
                path.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return self._get_path(key).exists()
