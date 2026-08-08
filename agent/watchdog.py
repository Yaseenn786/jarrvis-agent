import threading
import time


class Watchdog:
    """Supervises the watchers — a mini process-supervisor inside the agent.
    Wakes every `interval`s, checks each watcher's health, restarts the broken
    ones, and records it to the black box. Its own thread; never dies."""

    def __init__(self, manager, activity=None, interval=60):
        self.manager = manager
        self.activity = activity
        self.interval = interval
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            time.sleep(self.interval)
            try:
                self._check()
            except Exception as e:   # the watchdog itself must never die
                print(f"⚠️  watchdog error: {e}")

    def _check(self):
        for key, (healthy, reason) in self.manager.health().items():
            if healthy:
                continue
            print(f"⚠️  watcher {key} unhealthy ({reason}) — restarting")
            ok = self.manager.restart(key)
            if self.activity:
                detail = f"{key} — {reason}" + ("" if ok else " (restart FAILED)")
                self.activity.record("WATCHER_RESTARTED", detail)

    def snapshot(self):
        """Health of every watcher, for the heartbeat to ship to the hub."""
        return {
            key: {"healthy": healthy, "reason": reason}
            for key, (healthy, reason) in self.manager.health().items()
        }