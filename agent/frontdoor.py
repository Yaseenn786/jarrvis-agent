import json
import os
import re
import subprocess
import urllib.request

import psutil

CACHE_PATH = "/etc/jarrvis/frontdoor.json"

NGINX_DEFAULTS = ["/var/log/nginx/access.log"]
APACHE_DEFAULTS = [
    "/var/log/apache2/access.log",   # debian/ubuntu
    "/var/log/httpd/access_log",     # rhel/amazon linux
]


def refresh_frontdoor():
    """Detect the front door, write it to the local cache, and return it.
    Called on the discovery cadence. This is the SLOW path (does real detection)."""
    result = detect_frontdoor()
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(result, f)
    except OSError:
        pass   # cache write failed — not fatal, still return the live result
    return result


def get_frontdoor():
    """Read the cached front door — the FAST path used at fetch time (no detection).
    Falls back to a live detect if the cache doesn't exist yet."""
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return refresh_frontdoor()


def detect_frontdoor():
    """
    Figure out how traffic reaches this box's backend. Never raises.
    Returns: {"type": "nginx"|"apache"|"loadbalancer"|"none",
              "accessLog": "/path" or None, "detail": "..."}
    """
    if _process_running("nginx"):
        path = _nginx_log_path() or _first_existing(NGINX_DEFAULTS)
        return _result("nginx", path, "nginx reverse proxy detected")

    if _process_running("apache2") or _process_running("httpd"):
        path = _first_existing(APACHE_DEFAULTS)
        return _result("apache", path, "apache reverse proxy detected")

    lb = _looks_like_load_balancer()
    if lb:
        return _result("loadbalancer", None,
                       f"likely behind a load balancer ({lb}) — access logs live in the "
                       "cloud (e.g. S3), not on this server")

    return _result("none", None, "no local reverse proxy — access log not on this server")


def _result(kind, path, detail):
    return {"type": kind, "accessLog": path, "detail": detail}


def _process_running(name):
    for p in psutil.process_iter(["name"]):
        try:
            if (p.info["name"] or "").lower() == name.lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def _first_existing(paths):
    return next((p for p in paths if os.path.exists(p)), None)


def _nginx_log_path():
    """Ask nginx to dump its resolved config (nginx -T), pull the first real access_log path."""
    try:
        out = subprocess.run(["nginx", "-T"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    for m in re.finditer(r"^\s*access_log\s+(\S+)", out.stdout, re.MULTILINE):
        if m.group(1) != "off":
            return m.group(1)
    return None


def _looks_like_load_balancer():
    """Best-effort: is this a cloud box likely fronted by an LB? Cheap, never raises."""
    try:
        token = urllib.request.urlopen(
            urllib.request.Request(
                "http://169.254.169.254/latest/api/token",
                method="PUT",
                headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
            ),
            timeout=1,
        ).read().decode()
        req = urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/instance-id",
            headers={"X-aws-ec2-metadata-token": token},
        )
        if urllib.request.urlopen(req, timeout=1).status == 200:
            return "AWS EC2 instance"
    except Exception:
        pass
    return None