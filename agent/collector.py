import time
from collections import deque


class EventCollector:
    def __init__(self, context_size=10, quiet_seconds=2.0):
        self.buffer = deque(maxlen=context_size)  # last N lines, auto-drops old
        self.active_event = None
        self.last_trouble_time = None
        self.quiet_seconds = quiet_seconds

    def feed_idle(self):
        """Called when no new lines. Close event if quiet period passed."""
        if self.active_event and time.time() - self.last_trouble_time > self.quiet_seconds:
            finished = self.active_event
            self.active_event = None
            return finished
        return None     

    def feed(self, line, trouble):
        """Feed every line in. Returns a finished event dict, or None."""
        finished = None

        if trouble:
            if self.active_event is None:
                # New incident starts — snapshot the context BEFORE it
                self.active_event = {
                    "triggered_by": line,
                    "context_before": list(self.buffer),
                    "lines": [line],
                    "started_at": time.time(),
                }
            else:
                # Still inside the same incident (stack trace continuing)
                self.active_event["lines"].append(line)
            self.last_trouble_time = time.time()

        else:
            if self.active_event is not None:
                # Normal line while an event is open — has the storm passed?
                if time.time() - self.last_trouble_time > self.quiet_seconds:
                    finished = self.active_event
                    self.active_event = None
                else:
                    # Probably still part of the trace (blank/caused-by lines)
                    self.active_event["lines"].append(line)

        self.buffer.append(line)
        return finished