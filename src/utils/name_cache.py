import json
import os
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class NameCache:
    def __init__(self, cache_file: str = "name_cache.json"):
        self.cache_file = cache_file
        self.name_map = {}
        self._load_cache()

    def _load_cache(self):
        """Load name mappings from cache file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.name_map = json.load(f)
                logger.info(f"Loaded {len(self.name_map)} name mappings from cache")
        except Exception as e:
            logger.error(f"Error loading name cache: {e}")
            self.name_map = {}

    def save_cache(self):
        """Save current name mappings to cache file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.name_map, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.name_map)} name mappings to cache")
        except Exception as e:
            logger.error(f"Error saving name cache: {e}")

    def update_mapping(self, username: str, display_name: str):
        """Update mapping for a single user"""
        self.name_map[username] = display_name

    def get_display_name(self, username: str) -> str:
        """Get display name for a username, return username if not found"""
        return self.name_map.get(username, username)

    def clear_cache(self):
        """Clear all cached mappings"""
        self.name_map.clear()
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)