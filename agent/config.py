import os
import uuid

import yaml

DEFAULT_KEY_PATH = "/etc/jarrvis/.jarrvis_key"
LOCAL_KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".jarrvis_key")


def load_config(path=None):
    path = path or os.getenv("JARRVIS_CONFIG", "../jarrvis.yml")

    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    cfg["hub"]["url"] = os.getenv("JARRVIS_HUB_URL") or cfg["hub"]["url"]
    cfg["hub"]["server_name"] = os.getenv("JARRVIS_SERVER_NAME") or cfg["hub"]["server_name"]
    cfg["hub"]["api_key"] = _load_or_create_key()

    return cfg


def _key_path():
    override = os.getenv("JARRVIS_KEY_PATH")
    if override:
        return override

    parent = os.path.dirname(DEFAULT_KEY_PATH)
    if os.access(parent, os.W_OK) or os.access("/etc", os.W_OK):
        return DEFAULT_KEY_PATH

    return LOCAL_KEY_PATH


def _load_or_create_key():
    key_path = _key_path()

    if os.path.exists(key_path):
        with open(key_path, "r") as f:
            return f.read().strip()

    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    key = f"jrv_{uuid.uuid4().hex}"
    with open(key_path, "w") as f:
        f.write(key)
    os.chmod(key_path, 0o600)

    return key