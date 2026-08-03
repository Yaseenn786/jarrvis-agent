import json
import threading
import time
import subprocess
import requests
import os
import re

import frontdoor

class CommandPoller:
    """
    Owns ALL command handling. Holds one long-poll open to the hub; hub answers
    the instant a command exists (~1s) or 'nothing' after ~25s, then we re-open.
    Runs in its own daemon thread. Heartbeat no longer touches commands.
    """

    def __init__(self, hub_url, api_key, log_reader=None, on_set_watches=None, wait_timeout=30):
        self.hub_url = hub_url
        self.endpoint = f"{hub_url}/api/commands/poll"
        self.api_key = api_key
        self.log_reader = log_reader
        self.on_set_watches = on_set_watches
        # MUST exceed the hub's ~25s hold, or the client hangs up before the hub replies
        self.wait_timeout = wait_timeout

    def _loop(self):
        while True:
            try:
                r = requests.get(
                    self.endpoint,
                    params={"apiKey": self.api_key},
                    timeout=self.wait_timeout,
                )
                for cmd in r.json().get("commands", []):
                    self._handle(cmd)
            except requests.RequestException:
                time.sleep(2)   # hub/network hiccup → brief backoff
            except ValueError:
                pass            # empty/garbage body → treat as a miss, re-open

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
        elif cmd["type"] == "DOCKER_STATS":
            self._report(cmd["id"], self._docker_stats())     
        elif cmd["type"] == "FETCH_ACCESS_LOG":
            try:
                params = json.loads(cmd.get("paramsJson") or "{}")
            except ValueError:
                params = {}
            self._report(cmd["id"], self._fetch_access_log(params))    

    def _report(self, cmd_id, result):
        try:
            requests.post(
                f"{self.hub_url}/api/commands/{cmd_id}/result",
                json={"result": result, "apiKey": self.api_key},
                timeout=30,
            )
        except requests.RequestException:
            pass

    def _docker_stats(self):
        try:
            ps = subprocess.run(
                ["docker", "ps", "-a", "--format",
                 "table {{.Names}}\t{{.Status}}\t{{.State}}\t{{.Image}}"],
                capture_output=True, text=True, timeout=15,
            )
            if ps.returncode != 0:
                return f"docker ps failed: {ps.stderr.strip() or 'is docker running?'}"

            stats = subprocess.run(
                ["docker", "stats", "--no-stream", "--format",
                 "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"],
                capture_output=True, text=True, timeout=15,
            )
            live = stats.stdout.strip() if stats.returncode == 0 else "(stats unavailable)"

            return (
                "=== all containers (running + stopped) ===\n"
                f"{ps.stdout.strip() or 'no containers'}\n\n"
                "=== live stats (running only) ===\n"
                f"{live or 'no running containers'}"
            )
        except FileNotFoundError:
            return "docker not installed on this server"
        except subprocess.TimeoutExpired:
            return "docker stats timed out"
        except Exception as e:
            return f"docker stats error: {e}"
        
        
    def _fetch_access_log(self, params):
        fd = frontdoor.get_frontdoor()          # cached — no detection at request time
        path = fd.get("accessLog")
        if not path:
            return f"No access log on this server ({fd.get('detail', 'unknown front door')})."
        if not os.path.exists(path):
            return f"Access log path {path} not found on this server."

        ip = (params.get("ip") or "").strip()
        contains = (params.get("contains") or "").strip()
        status = (params.get("status") or "").strip()      # "404" or a class "4xx"/"5xx"
        try:
            max_lines = int(params.get("max_lines") or 300)
        except (ValueError, TypeError):
            max_lines = 300
        max_lines = max(1, min(max_lines, 1000))            # hard cap

        matches = []
        try:
            with open(path, "r", errors="replace") as f:
                for line in f:                               # stream — never load whole file
                    if ip and ip not in line:
                        continue
                    if contains and contains not in line:
                        continue
                    if status and not self._status_matches(line, status):
                        continue
                    matches.append(line.rstrip("\n"))
        except OSError as e:
            return f"Could not read access log: {e}"

        if not matches:
            return "No matching access-log lines found for that query."

        trimmed = matches[-max_lines:]
        header = f"{len(matches)} matching line(s)"
        if len(trimmed) < len(matches):
            header += f" (showing last {len(trimmed)})"
        return header + ":\n" + "\n".join(trimmed)

    @staticmethod
    def _status_matches(line, status):
        m = re.search(r'"\s(\d{3})\s', line)                # the code right after the "GET ..." request
        if not m:
            return False
        code = m.group(1)
        s = status.lower()
        if s in ("2xx", "3xx", "4xx", "5xx"):
            return code[0] == s[0]
        return code == status    

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()