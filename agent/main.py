import time

from tailer import tail
from detector import compile_patterns, is_trouble
from config import load_config
from collector import EventCollector


def handle_event(event):
    """For now: print. Later: ship to hub."""
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
    compiled = compile_patterns(cfg["patterns"])
    logfile = cfg["watch"][0]["path"]
    collector = EventCollector()

    print(f"Jarrvis watching {logfile} ...")

    for line in tail(f"../{logfile}"):
        if line is None:
            event = collector.feed_idle()
            if event:
                handle_event(event)
            continue

        event = collector.feed(line, is_trouble(line, compiled))
        if event:
            handle_event(event)