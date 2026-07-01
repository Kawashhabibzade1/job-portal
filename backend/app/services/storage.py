import json
import os
from pathlib import Path
from threading import Lock
from typing import Any


DATA_DIR = Path(os.getenv("CAREER_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))


class JsonStore:
    def __init__(self, filename: str, default: Any):
        self.path = DATA_DIR / filename
        self.default = default
        self._lock = Lock()

    def read(self) -> Any:
        with self._lock:
            if not self.path.exists():
                return self.default
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return self.default

    def write(self, data: Any) -> Any:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return data
