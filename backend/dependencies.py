"""Dependencies for FastAPI — DB sessions, auth, pagination, and shared resources."""

from __future__ import annotations
from typing import Annotated, Any
import json
import os
from pathlib import Path


# ── Data Directory ─────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def get_data_dir() -> str:
    """Return the data directory path."""
    return DATA_DIR


# ── JSON Data Loader ──────────────────────────────────────────────────────

class JSONDataLoader:
    """Loads and caches JSON data files."""
    
    def __init__(self, data_dir: str):
        self._data_dir = data_dir
        self._cache: dict[str, Any] = {}
    
    def load(self, filename: str, use_cache: bool = True) -> Any:
        """Load JSON file with optional caching."""
        if use_cache and filename in self._cache:
            return self._cache[filename]
        
        path = os.path.join(self._data_dir, filename)
        if not os.path.isfile(path):
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if use_cache:
                    self._cache[filename] = data
                return data
        except Exception:
            return None
    
    def reload(self, filename: str) -> Any:
        """Force reload a specific file, bypassing cache."""
        self._cache.pop(filename, None)
        return self.load(filename, use_cache=True)
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()


# ── Singleton Instance ─────────────────────────────────────────────────────

_data_loader: JSONDataLoader | None = None


def get_data_loader() -> JSONDataLoader:
    """Get or create the singleton JSON data loader."""
    global _data_loader
    if _data_loader is None:
        _data_loader = JSONDataLoader(DATA_DIR)
    return _data_loader


# ── Type Aliases ─────────────────────────────────────────────────────────

DataLoader = Annotated[JSONDataLoader, Depends(get_data_loader)]


# Import for type annotation
from typing import Depends
