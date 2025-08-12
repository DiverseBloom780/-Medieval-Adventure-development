# persistence.py
from __future__ import annotations
import json
import os
from typing import Any

_FILE = "highscore.json"

def load_high_score(default: int = 0) -> int:
    try:
        if not os.path.exists(_FILE):
            return default
        with open(_FILE, "r", encoding="utf-8") as f:
            data: Any = json.load(f)
        return int(data.get("high_score", default))
    except Exception:
        return default

def save_high_score(score: int) -> None:
    try:
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump({"high_score": int(score)}, f)
    except Exception:
        # Silently ignore; high score persistence is non-critical.
        pass
