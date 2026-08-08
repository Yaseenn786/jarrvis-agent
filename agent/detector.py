import re


def compile_patterns(patterns):
    return [re.compile(p) for p in patterns]


def is_trouble(line, compiled):
    if line.startswith("[JARRVIS-ACCESSLOG]"):   # access-log watcher already decided it's trouble
        return True
    return any(p.search(line) for p in compiled)