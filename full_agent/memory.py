import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class MemoryRecord:
    content: str
    scope: str = "global"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None


class MemoryStore:
    def __init__(self, path):
        self.path = Path(path)

    def add(self, record):
        data = self._normalize(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        return data

    def search(self, query, scope=None, limit=5):
        query = (query or "").lower()
        matches = []
        for record in self.list(scope=scope):
            haystack = json.dumps(record, ensure_ascii=False).lower()
            if not query or query in haystack:
                matches.append(record)
            if len(matches) >= limit:
                break
        return matches

    def list(self, scope=None):
        if not self.path.exists():
            return []
        records = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if scope is None or record.get("scope") == scope:
                    records.append(record)
        return records

    def _normalize(self, record):
        if isinstance(record, MemoryRecord):
            data = asdict(record)
        elif isinstance(record, dict):
            data = dict(record)
        else:
            raise TypeError("memory record must be a dict or MemoryRecord")

        content = data.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("memory record requires non-empty content")

        data.setdefault("scope", "global")
        data.setdefault("metadata", {})
        data.setdefault(
            "created_at",
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        )
        return data
