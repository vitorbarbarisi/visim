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
        # Sash positions are stored as fractions of window width (0.0-1.0) so the
        # layout proportions stay consistent across window sizes and resolutions.
        self.sash_left: Optional[float] = None
        self.sash_right: Optional[float] = None
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
            # Only accept fractions in (0, 1). Legacy absolute-pixel values
            # (saved by older versions) are ignored so defaults apply instead.
            sl = data.get("sash_left")
            if isinstance(sl, (int, float)) and 0 < sl < 1:
                self.sash_left = float(sl)
            sr = data.get("sash_right")
            if isinstance(sr, (int, float)) and 0 < sr < 1:
                self.sash_right = float(sr)
        except Exception:
            pass

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            payload = {
                "last_csv_path": self.last_csv_path,
                "recent_csv_paths": self.recent_csv_paths,
                "sash_left": self.sash_left,
                "sash_right": self.sash_right,
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

    def set_sash(self, key: str, fraction: float):
        """Store a sash position as a fraction of window width (0.0-1.0)."""
        if not (0 < fraction < 1):
            return
        if key == "left":
            self.sash_left = fraction
        elif key == "right":
            self.sash_right = fraction
        self._save()

    def remove_recent(self, path: str):
        self.recent_csv_paths = [p for p in self.recent_csv_paths if p != path]
        self._save()

    def clear_recent(self):
        self.recent_csv_paths = []
        self._save()
