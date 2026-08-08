import re
import time
from collections import deque

# --- attack signatures --------------------------------------------------------
PROBE_PATHS = (
    "/.env", "/.git", "/cgi-bin", "eval-stdin.php", "/vendor/phpunit",
    "wp-admin", "wp-login", "wp-config", "phpmyadmin", "wlwmanifest.xml",
    "/administrator", "/containers/json", "/etc/passwd", "..%2f", "../",
    ".action", "/actuator/env", "/.aws", "/config.json",
)
BAD_UAS = ("sqlmap", "nikto", "masscan", "zgrab", "nmap", "nuclei", "wpscan")
# statuses nginx uses to DENY at the gate (a bad request it refused)
DENIED_STATUSES = {"400", "403", "405", "413", "414", "444"}

# --- defensive nginx-combined parsing ----------------------------------------
_STATUS = re.compile(r'"\s(\d{3})\s')                       # code after the "GET ..." block
_REQ    = re.compile(r'"[A-Z]+\s+(\S+)\s+HTTP')             # the requested path
_UA     = re.compile(r'"([^"]*)"\s*$')                      # last quoted field = user-agent


def parse(line):
    """Pull {ip, status, path, ua} out of an nginx-combined line. Missing fields = None.
    Never raises — an unparseable line just yields Nones."""
    ip = line.split(" ", 1)[0] if line else None
    status = m.group(1) if (m := _STATUS.search(line)) else None
    path = m.group(1) if (m := _REQ.search(line)) else None
    ua = m.group(1) if (m := _UA.search(line)) else None
    return {"ip": ip, "status": status, "path": path, "ua": ua}


class AccessLogDetector:
    """Turns access-log lines into trouble signals. Two kinds:
       1. ATTACK — a probe path / bad UA / denied status, windowed per-IP.
       2. RATE   — a spike of 4xx (security) or 5xx (health) in a rolling window.
    Every detection is windowed, so a scan/outage is ONE signal, not fifty.
    Returns a signal dict when a threshold trips, else None. Never raises."""

    def __init__(self,
                 window_sec=60,
                 attack_threshold=10,   # N probes from one IP in the window → one event
                 rate_4xx_threshold=40, # N 4xx across all IPs in the window → security spike
                 rate_5xx_threshold=15):# N 5xx in the window → app-health spike (outage)
        self.window = window_sec
        self.attack_threshold = attack_threshold
        self.rate_4xx_threshold = rate_4xx_threshold
        self.rate_5xx_threshold = rate_5xx_threshold

        self._attacks = {}                 # ip -> deque[timestamps] of probe hits
        self._4xx = deque()                # timestamps of 4xx
        self._5xx = deque()                # timestamps of 5xx
        self._last_fire = {}               # signal-key -> ts, so we don't re-fire mid-window

    def feed(self, line):
        """Feed one raw access-log line. Returns a signal dict or None."""
        try:
            return self._feed(line)
        except Exception:
            return None                    # detection must never break the watcher

    def _feed(self, line):
        now = time.time()
        p = parse(line)
        status = p["status"]

        # --- 1. attack signature? -------------------------------------------
        if self._is_attack(p):
            ip = p["ip"] or "unknown"
            hits = self._attacks.setdefault(ip, deque())
            hits.append(now)
            self._trim(hits, now)
            if len(hits) >= self.attack_threshold and self._cooldown(f"attack:{ip}", now):
                return {
                    "kind": "attack",
                    "ip": ip,
                    "count": len(hits),
                    "sample": (p["path"] or p["ua"] or "")[:120],
                    "message": f"{len(hits)} suspicious requests from {ip} in {self.window}s "
                               f"(e.g. {p['path'] or p['ua']})",
                }

        # --- 2. rate spikes --------------------------------------------------
        if status and status.startswith("4"):
            self._4xx.append(now)
            self._trim(self._4xx, now)
            if len(self._4xx) >= self.rate_4xx_threshold and self._cooldown("4xx", now):
                return {"kind": "rate_4xx", "count": len(self._4xx),
                        "message": f"{len(self._4xx)} 4xx responses in {self.window}s — "
                                   f"likely scanning/probing"}

        if status and status.startswith("5"):
            self._5xx.append(now)
            self._trim(self._5xx, now)
            if len(self._5xx) >= self.rate_5xx_threshold and self._cooldown("5xx", now):
                return {"kind": "rate_5xx", "count": len(self._5xx),
                        "message": f"{len(self._5xx)} 5xx responses in {self.window}s — "
                                   f"your backend may be down or failing"}

        return None

    # --- helpers -------------------------------------------------------------
    def _is_attack(self, p):
        path = (p["path"] or "").lower()
        ua = (p["ua"] or "").lower()
        if p["status"] in DENIED_STATUSES:
            return True
        if any(sig in path for sig in PROBE_PATHS):
            return True
        if any(bad in ua for bad in BAD_UAS):
            return True
        return False

    def _trim(self, dq, now):
        cutoff = now - self.window
        while dq and dq[0] < cutoff:
            dq.popleft()

    def _cooldown(self, key, now):
        """One signal per window per key — don't re-fire every line once tripped."""
        last = self._last_fire.get(key)
        if last is not None and now - last < self.window:
            return False
        self._last_fire[key] = now
        return True