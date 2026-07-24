import json
import threading
import time

import psutil
import requests

import discover


class Heartbeat:
    def __init__(self, hub_url, server_name, api_key=None, interval=30, log_reader=None,
                 discover_every=20, on_set_watches=None):
        self.hub_url = hub_url
        self.endpoint = f"{hub_url}/api/heartbeat"
        self.server_name = server_name
        self.api_key = api_key
        self.interval = interval
        self.log_reader = log_reader
        self.discover_every = discover_every
        self.on_set_watches = on_set_watches
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

        if self.beat_count % self.discover_every == 0:
            payload["discovered"] = discover.discover()

        self.beat_count += 1
        return payload

    def _loop(self):
        while True:
            try:
                r = requests.post(self.endpoint, json=self._collect(), timeout=10)
                for cmd in r.json().get("commands", []):
                    self._handle(cmd)
            except (requests.RequestException, ValueError):
                pass
            time.sleep(self.interval)

    def _handle(self, cmd):
        if cmd["type"] == "FETCH_LOGS":
            result = self.log_reader() if self.log_reader else "log copy not enabled"
            self._report(cmd["id"], result)

        elif cmd["type"] == "SET_WATCHES":
            if not self.on_set_watches:
                return
            try:
                params = json.loads(cmd.get("paramsJson") or "{}")
            except ValueError:
                return
            active = self.on_set_watches(params.get("targets", []))
            self._report(cmd["id"], f"watching: {', '.join(active) if active else 'nothing'}")

    def _report(self, cmd_id, result):
        try:
            requests.post(
                f"{self.hub_url}/api/commands/{cmd_id}/result",
                json={"result": result, "apiKey": self.api_key},
                timeout=30,
            )
        except requests.RequestException:
            pass

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()