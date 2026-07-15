import re


def compile_patterns(patterns):
    return [re.compile(p) for p in patterns]


def is_trouble(line, compiled):
    return any(p.search(line) for p in compiled)