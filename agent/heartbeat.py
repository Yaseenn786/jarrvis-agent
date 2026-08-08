import threading
import time

import psutil
import requests

import discover
import frontdoor


class Heartbeat:
    def __init__(self, hub_url, server_name, api_key=None, interval=30,
                 log_reader=None, discover_every=20, watch_health=None):
        self.hub_url = hub_url
        self.endpoint = f"{hub_url}/api/heartbeat"
        self.server_name = server_name
        self.api_key = api_key
        self.interval = interval
        self.log_reader = log_reader
        self.discover_every = discover_every
        self.watch_health = watch_health   # callable → watchdog.snapshot()
        self.beat_count = 0

    def _collect(self):
        payload = {
            "serverName": self.server_name,
            "apiKey": self.api_key,
            "cpuPercent": psutil.cpu_percent(interval=1),
            "memoryPercent": psutil.virtual_memory().percent,
            "diskPercent": psutil.disk_usage("/").percent,
            "recentLogs": self.log_reader(50) if self.log_reader else "",
        }

        # ship live watcher health every beat — what's watched + is it healthy
        if self.watch_health:
            try:
                health = self.watch_health()   # {key: {"healthy": bool, "reason": str}}
                payload["watching"] = [
                    {"source": key, "healthy": h["healthy"], "reason": h["reason"]}
                    for key, h in health.items()
                ]
                payload["watchCount"] = len(health)
            except Exception:
                payload["watching"] = []
                payload["watchCount"] = 0

        if self.beat_count % self.discover_every == 0:
            payload["discovered"] = discover.discover()
            payload["frontDoor"] = frontdoor.refresh_frontdoor()

        self.beat_count += 1
        return payload

    def _loop(self):
        while True:
            try:
                requests.post(self.endpoint, json=self._collect(), timeout=10)
            except (requests.RequestException, ValueError):
                pass
            time.sleep(self.interval)

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()