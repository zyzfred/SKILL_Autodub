#!/usr/bin/env python3

import os
from pathlib import Path


def _candidate_dirs(extra_roots=None):
    seen = set()
    roots = [Path.cwd(), Path(__file__).resolve().parent]
    if extra_roots:
        roots.extend(Path(root).resolve() for root in extra_roots)

    for root in roots:
        current = root
        while True:
            if current not in seen:
                seen.add(current)
                yield current
            if current.parent == current:
                break
            current = current.parent


def _parse_env_line(line):
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None, None
    if stripped.startswith("export "):
        stripped = stripped[7:].strip()
    if "=" not in stripped:
        return None, None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None, None
    if value and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_dotenv(extra_roots=None, override=False):
    for directory in _candidate_dirs(extra_roots=extra_roots):
        env_path = directory / ".env"
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            key, value = _parse_env_line(line)
            if not key:
                continue
            if override or key not in os.environ:
                os.environ[key] = value
        return env_path
    return None

