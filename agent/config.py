import yaml


def load_config(path="../jarrvis.yml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)