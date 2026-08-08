import json
import os
import threading
from datetime import datetime, timezone, timedelta

ACTIVITY_PATH = "/var/lib/jarrvis/activity.jsonl"
RETENTION_DAYS = 60


class Activity:
    """Append-only trace of what the agent does on this server — the black box.
    JSON-lines, one action per line, survives restarts. Bounded to RETENTION_DAYS.
    Thread-safe. Never raises — tracing must never break the agent."""

    def __init__(self, path=ACTIVITY_PATH, retention_days=RETENTION_DAYS):
        self.path = path
        self.retention_days = retention_days
        self._lock = threading.Lock()
        self._writes = 0
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except OSError:
            pass
        self._trim()   # prune old entries on startup

    def record(self, type, detail=""):
        """Append one action. e.g. record('WATCH_SET', 'postgres, app')."""
        entry = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "type": type,
            "detail": detail,
        }
        try:
            with self._lock:
                with open(self.path, "a") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                self._writes += 1
            if self._writes % 200 == 0:   # keep it bounded even on long-running agents
                self._trim()
        except OSError:
            pass

    def _trim(self):
        """Drop entries older than retention_days. Cheap — the file is tiny."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        try:
            with self._lock:
                if not os.path.exists(self.path):
                    return
                with open(self.path) as f:
                    lines = f.readlines()
                kept = []
                for line in lines:
                    try:
                        at = datetime.fromisoformat(json.loads(line)["at"])
                        if at >= cutoff:
                            kept.append(line)
                    except (ValueError, KeyError, TypeError):
                        kept.append(line)   # unparseable → keep, never lose data
                if len(kept) != len(lines):
                    with open(self.path, "w") as f:
                        f.writelines(kept)
        except OSError:
            pass