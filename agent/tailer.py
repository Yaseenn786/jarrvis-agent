import time
import os


def tail(filepath):
    """Follow a log file line by line, like `tail -f`."""
    with open(filepath, "r") as f:
        # Jump to the end of the file — we only care about NEW lines
        f.seek(0, os.SEEK_END)

        while True:
            line = f.readline()
            if line:
                yield line.rstrip("\n")
            else:
                # No new line yet — nap briefly, don't burn CPU
                time.sleep(0.2)
                yield None  