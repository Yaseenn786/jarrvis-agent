import queue

from detector import compile_patterns, is_trouble
from config import load_config
from collector import EventCollector
from shipper import Shipper
from heartbeat import Heartbeat
from logcopy import LogCopy
from watchers import WatcherManager
from poller import CommandPoller

def handle_event(event):
    """Print locally, then ship to hub."""
    print("\n" + "=" * 60)
    print("🚨 JARRVIS EVENT")
    print(f"Trigger : {event['triggered_by']}")
    print(f"Lines   : {len(event['lines'])}")
    print("--- context before ---")
    for l in event["context_before"]:
        print(f"  {l}")
    print("--- incident ---")
    for l in event["lines"]:
        print(f"  {l}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    cfg = load_config()
    shipper = Shipper(cfg["hub"]["url"], cfg["hub"]["server_name"], cfg["hub"]["api_key"])
    compiled = compile_patterns(cfg["patterns"])

    logcopy = None
    if cfg.get("log_copy", {}).get("enabled"):
        lc = cfg["log_copy"]
        logcopy = LogCopy(lc["dir"], lc["max_storage_mb"], lc["retention_days"])

    lines = queue.Queue()
    manager = WatcherManager(lines)

    seed = [{"type": "file", "name": w["path"], "logPath": f"../{w['path']}"}
            for w in cfg.get("watch", [])]
    active = manager.apply(seed)

    hb = Heartbeat(cfg["hub"]["url"], cfg["hub"]["server_name"],
                   api_key=cfg["hub"]["api_key"],
                   interval=30,
                   log_reader=(logcopy.read_recent if logcopy else None))
    hb.start()

    poller = CommandPoller(cfg["hub"]["url"], cfg["hub"]["api_key"],
                           log_reader=(logcopy.read_recent if logcopy else None),
                           on_set_watches=manager.apply)
    poller.start()

    collectors = {}
    print(f"Jarrvis watching {', '.join(active) if active else 'nothing yet'} ...")

    while True:
        try:
            key, line = lines.get(timeout=0.5)
        except queue.Empty:
            for c in list(collectors.values()):
                event = c.feed_idle()
                if event:
                    handle_event(event)
                    shipper.ship(event)
            continue

        if logcopy:
            logcopy.write(line)

        collector = collectors.setdefault(key, EventCollector())
        event = collector.feed(line, is_trouble(line, compiled))
        if event:
            handle_event(event)
            shipper.ship(event)