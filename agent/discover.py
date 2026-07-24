import json
import os
import subprocess

import psutil

HINTS = {
    "postgres": "PostgreSQL database",
    "mysql": "MySQL database",
    "mariadb": "MariaDB database",
    "redis": "Redis cache",
    "mongo": "MongoDB database",
    "nginx": "Nginx web server",
    "rabbitmq": "RabbitMQ broker",
}


def discover():
    """Everything on this box worth watching. Never raises."""
    return _docker() + _processes()


def _docker():
    try:
        out = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    

    if out.returncode != 0:
        return []

    found = []
    for line in out.stdout.strip().splitlines():
        try:
            c = json.loads(line)
        except ValueError:
            continue

        found.append({
            "type": "docker",
            "name": c.get("Names", ""),
            "identifier": c.get("ID", ""),
            "hint": _image_hint(c.get("Image", "")),
            "logPath": None
        })

    return found


DEV_NOISE = (
    "vscode", "vscode-server", ".vscode", "code helper",
    "jetbrains", "intellij", "language-server", "-ls.jar",
    "copilot", "sonarlint", "eslintserver", "typescript-language",
)


def _processes():
    found = []

    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            pid = p.info["pid"]
            cmdline = " ".join(p.info.get("cmdline") or [])

            if not cmdline or _in_container(pid):
                continue
            if _is_dev_noise(cmdline):
                continue

            label = _process_label(cmdline)
            if not label:
                continue

            ports = _listening_ports(pid)
            if not ports:
                continue

            paths = _log_paths(pid)

            found.append({
                "type": "process",
                "name": label[0],
                "identifier": str(pid),
                "hint": f"{label[1]} on port {ports[0]}",
                "logPath": paths[0] if paths else None,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return found


def _is_dev_noise(cmdline):
    lowered = cmdline.lower()
    return any(marker in lowered for marker in DEV_NOISE)


def _listening_ports(pid):
    try:
        conns = psutil.Process(pid).net_connections(kind="inet")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []

    return sorted({
        c.laddr.port for c in conns
        if c.status == psutil.CONN_LISTEN and c.laddr
    })


def _in_container(pid):
    """Containerised processes show up on the host too — skip the duplicate."""
    try:
        with open(f"/proc/{pid}/cgroup") as f:
            content = f.read()
        return "docker" in content or "containerd" in content
    except OSError:
        return False


def _process_label(cmdline):
    parts = cmdline.split()

    if "java" in cmdline and "-jar" in cmdline:
        jar = next((p for p in parts if p.endswith(".jar")), "app.jar")
        return os.path.basename(jar), "Java application"

    if "gunicorn" in cmdline or "uvicorn" in cmdline:
        target = next((p for p in parts if ":" in p and "/" not in p), "python-web-app")
        return target, "Python web application"

    if "node" in cmdline and "npm" not in cmdline:
        script = next(
            (os.path.basename(p) for p in parts if p.endswith((".js", ".mjs", ".cjs"))),
            "node-app",
        )
        return script, "Node.js application"

    return None


def _image_hint(image):
    image = image.lower()
    for fragment, label in HINTS.items():
        if fragment in image:
            return label
    return "Application container"

def _log_paths(pid):
    """Files this process has open that look like logs. Linux only."""
    fd_dir = f"/proc/{pid}/fd"
    found = []

    try:
        fds = os.listdir(fd_dir)
    except OSError:
        return []

    for fd in fds:
        try:
            target = os.readlink(os.path.join(fd_dir, fd))
        except OSError:
            continue

        if not target.startswith("/"):
            continue
        if "(deleted)" in target:
            continue
        if target.endswith((".log", ".out")) or "/log" in target:
            found.append(target)

    return sorted(set(found))