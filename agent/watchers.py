import os
import subprocess
import threading
import time

from tailer import tail


class Watcher:
    """Runs one source in its own thread, pushing (key, line) into a shared queue.
    Designed to be UNKILLABLE — no exception can silently end the thread."""

    def __init__(self, key, out_queue):
        self.key = key
        self.out = out_queue
        self._stop = threading.Event()
        self.last_tick = time.time()   # bumped every loop cycle (incl. idle) — proves liveness
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._safe_run, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop.set()

    def is_alive(self):
        return self.thread is not None and self.thread.is_alive()

    def _tick(self):
        self.last_tick = time.time()

    def _emit(self, line):
        if line is not None:
            self.out.put((self.key, line))

    def _safe_run(self):
        """Wraps _run so ANY error → log, back off, retry. The Aug-3 fix:
        the thread loops forever instead of dying on a non-OSError."""
        while not self._stop.is_set():
            try:
                self._run()
                # _run returned (source stream ended) — re-establish unless stopping
                if not self._stop.is_set():
                    self._tick()
                    time.sleep(3)
            except Exception as e:   # noqa: BLE001 — deliberately broad; a watcher must never die
                print(f"⚠️  watcher {self.key} crashed: {e} — restarting read in 5s")
                self._tick()          # still looping = still alive
                time.sleep(5)

    def _run(self):
        raise NotImplementedError

    def health(self):
        """(healthy, reason). Base check: thread alive. Overridden per source type."""
        if not self.is_alive():
            return False, "thread dead"
        return True, "ok"


class FileWatcher(Watcher):
    def __init__(self, key, path, out_queue):
        super().__init__(key, out_queue)
        self.path = path

    def _run(self):
        for line in tail(self.path):        # yields the line, or None every ~0.2s when idle
            if self._stop.is_set():
                return
            self._tick()                    # every cycle — proves the read loop is turning
            self._emit(line)

    def health(self):
        if not self.is_alive():
            return False, "thread dead"
        if not os.path.exists(self.path):
            return False, "log file missing"
        # file watcher ticks every ~0.2s when healthy; a stale tick = the read is stuck
        if time.time() - self.last_tick > 60:
            return False, "read stalled"
        return True, "ok"


class DockerWatcher(Watcher):
    def __init__(self, key, container, out_queue):
        super().__init__(key, out_queue)
        self.container = container
        self.proc = None

    def _run(self):
        self.proc = subprocess.Popen(
            ["docker", "logs", "-f", "--tail", "0", self.container],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        try:
            for line in self.proc.stdout:
                if self._stop.is_set():
                    break
                self._tick()
                self._emit(line.rstrip("\n"))
        finally:
            if self.proc:
                self.proc.terminate()
                self.proc = None
        # returns when the stream ends (container stopped/restarted) → _safe_run reconnects

    def health(self):
        if not self.is_alive():
            return False, "thread dead"
        # docker blocks on a quiet container (no tick), so we check the PLUMBING instead:
        if self.proc is None or self.proc.poll() is not None:
            return False, "log stream not running"
        if not _container_running(self.container):
            return False, "container not running"
        return True, "ok"


def _container_running(name):
    """Is this container in `docker ps`? Fails safe (returns True) if we can't check."""
    try:
        out = subprocess.run(
            ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5,
        )
        return name in out.stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return True   # can't check → don't false-alarm


class WatcherManager:
    """Starts/stops watchers so the running set matches what the hub asked for."""

    def __init__(self, out_queue):
        self.out = out_queue
        self.active = {}
        self.targets = {}   # remember each watcher's target dict, so we can rebuild it

    def apply(self, targets):
        wanted = {f"{t['type']}:{t['name']}": t for t in targets}
        self.targets = wanted

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

    def restart(self, key):
        """Stop and rebuild one watcher from its stored target. True on success."""
        t = self.targets.get(key)
        if t is None:
            return False
        old = self.active.pop(key, None)
        if old:
            old.stop()
        w = self._build(key, t)
        if not w:
            return False
        w.start()
        self.active[key] = w
        return True

    def health(self):
        """Snapshot of every watcher's health — read by the watchdog + heartbeat."""
        return {key: w.health() for key, w in self.active.items()}

    def _build(self, key, t):
        if t["type"] == "docker":
            return DockerWatcher(key, t["name"], self.out)
        path = t.get("logPath")
        if path:
            return FileWatcher(key, path, self.out)
        return None