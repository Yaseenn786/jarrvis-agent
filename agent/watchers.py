import subprocess
import threading
import time

from tailer import tail


class Watcher:
    """Runs one source in its own thread, pushing (key, line) into a shared queue."""

    def __init__(self, key, out_queue):
        self.key = key
        self.out = out_queue
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._stop.set()

    def _emit(self, line):
        if line is not None:
            self.out.put((self.key, line))


class FileWatcher(Watcher):
    def __init__(self, key, path, out_queue):
        super().__init__(key, out_queue)
        self.path = path

    def _run(self):
        while not self._stop.is_set():
            try:
                for line in tail(self.path):
                    if self._stop.is_set():
                        return
                    self._emit(line)
            except OSError:
                time.sleep(5)


class DockerWatcher(Watcher):
    def __init__(self, key, container, out_queue):
        super().__init__(key, out_queue)
        self.container = container

    def _run(self):
        while not self._stop.is_set():
            proc = None
            try:
                proc = subprocess.Popen(
                    ["docker", "logs", "-f", "--tail", "0", self.container],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1,
                )
                for line in proc.stdout:
                    if self._stop.is_set():
                        break
                    self._emit(line.rstrip("\n"))
            except OSError:
                pass
            finally:
                if proc:
                    proc.terminate()

            if not self._stop.is_set():
                time.sleep(5)


class WatcherManager:
    """Starts/stops watchers so the running set matches what the hub asked for."""

    def __init__(self, out_queue):
        self.out = out_queue
        self.active = {}

    def apply(self, targets):
        wanted = {f"{t['type']}:{t['name']}": t for t in targets}

        for key in list(self.active):
            if key not in wanted:
                self.active.pop(key).stop()

        for key, t in wanted.items():
            if key in self.active:
                continue
            w = self._build(key, t)
            if w:
                w.start()
                self.active[key] = w

        return sorted(self.active)

    def _build(self, key, t):
        if t["type"] == "docker":
            return DockerWatcher(key, t["name"], self.out)

        path = t.get("logPath")
        if path:
            return FileWatcher(key, path, self.out)

        return None