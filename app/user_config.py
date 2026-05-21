"""Persistent user configuration (last CSV, recent files)."""
import json
import os
from typing import List, Optional


class UserConfig:
    MAX_RECENT = 10

    def __init__(self):
        home_dir = os.path.expanduser("~")
        self.config_path = os.path.join(home_dir, ".visim", "config.json")
        self.last_csv_path: Optional[str] = None
        self.recent_csv_paths: List[str] = []
        self._load()

    def _load(self):
        try:
            if not os.path.exists(self.config_path):
                return
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            last = data.get("last_csv_path")
            if isinstance(last, str) and os.path.isfile(last):
                self.last_csv_path = os.path.abspath(last)
            recent = data.get("recent_csv_paths", [])
            if isinstance(recent, list):
                seen = set()
                cleaned = []
                for p in recent:
                    if isinstance(p, str) and os.path.isfile(p) and p not in seen:
                        seen.add(p)
                        cleaned.append(p)
                self.recent_csv_paths = cleaned[: self.MAX_RECENT]
        except Exception:
            pass

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            payload = {
                "last_csv_path": self.last_csv_path,
                "recent_csv_paths": self.recent_csv_paths,
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def set_last_csv_path(self, path: str):
        if not path:
            return
        self.last_csv_path = os.path.abspath(path)
        self._save()

    def add_recent(self, path: str):
        if not path:
            return
        abs_path = os.path.abspath(path)
        if not os.path.isfile(abs_path):
            return
        self.recent_csv_paths = [p for p in self.recent_csv_paths if p != abs_path]
        self.recent_csv_paths.insert(0, abs_path)
        self.recent_csv_paths = self.recent_csv_paths[: self.MAX_RECENT]
        self._save()

    def remove_recent(self, path: str):
        self.recent_csv_paths = [p for p in self.recent_csv_paths if p != path]
        self._save()

    def clear_recent(self):
        self.recent_csv_paths = []
        self._save()
