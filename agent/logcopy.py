import gzip
import os
import shutil
import time
from datetime import date


class LogCopy:
    def __init__(self, store_dir, max_storage_mb=100, retention_days=1,
                 flush_every=50):
        self.dir = store_dir
        self.max_bytes = max_storage_mb * 1024 * 1024
        self.retention_days = retention_days
        self.flush_every = flush_every
        self.last_flush = time.time()

        os.makedirs(self.dir, exist_ok=True)
        self.current_day = date.today()
        self.file = open(self._path_for(self.current_day), "a")
        self.lines_since_flush = 0

    def read_recent(self, max_lines=300):
        """Return the last N lines of today's copy."""
        self.file.flush()
        with open(self._path_for(self.current_day), "r") as f:
            return "".join(f.readlines()[-max_lines:])    

    def _path_for(self, d):
        return os.path.join(self.dir, f"{d.isoformat()}.log")

    def write(self, line):
        today = date.today()
        if today != self.current_day:
            self._roll(today)

        self.file.write(line + "\n")
        self.lines_since_flush += 1
        now = time.time()
        if self.lines_since_flush >= self.flush_every or now - self.last_flush > 5:
            self.file.flush()
            self.lines_since_flush = 0
            self.last_flush = now
            self._enforce_cap()

    def _roll(self, today):
        """Midnight: close + gzip yesterday, open today, clean old."""
        self.file.close()
        old_path = self._path_for(self.current_day)
        if os.path.exists(old_path):
            with open(old_path, "rb") as src, gzip.open(old_path + ".gz", "wb") as dst:
                shutil.copyfileobj(src, dst)
            os.remove(old_path)

        self.current_day = today
        self.file = open(self._path_for(today), "a")
        self._cleanup_old()

    def _cleanup_old(self):
        """Delete files older than retention_days."""
        cutoff = time.time() - (self.retention_days * 86400)
        for name in os.listdir(self.dir):
            path = os.path.join(self.dir, name)
            if os.path.getmtime(path) < cutoff:
                os.remove(path)

    def _enforce_cap(self):
        """If folder exceeds max size, delete oldest files first."""
        files = [
            (os.path.getmtime(os.path.join(self.dir, n)), os.path.join(self.dir, n))
            for n in os.listdir(self.dir)
        ]
        total = sum(os.path.getsize(p) for _, p in files)
        for _, path in sorted(files):                 # oldest first
            if total <= self.max_bytes:
                break
            if path == self.file.name:               # never delete the live file
                continue
            total -= os.path.getsize(path)
            os.remove(path)