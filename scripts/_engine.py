"""Shared helpers for talking to whichever ComfyUI container is actually running.

The compose file defines three services and each names its container
differently: `comfyui` for the from-source profile, `comfyui-packaged` for the
published image, `comfyui-local` for the offline one.  A script that hardcodes
one of those works for whoever wrote it and fails for everyone else, and the
failure looks like a broken pipeline rather than a wrong name.

So: ask Docker which one is up.

    from _engine import container, exec_python
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

# In preference order. The from-source profile wins when several are up, because
# someone running that profile is editing node source and means to test it.
CANDIDATES = ("comfyui", "comfyui-packaged", "comfyui-local")


def container() -> str:
    """The name of the running ComfyUI container.

    Falls back to the first candidate so callers still produce a sensible error
    message when nothing is running, rather than a confusing empty string.
    """
    override = os.environ.get("ASSET_ENGINE_CONTAINER")
    if override:
        return override
    try:
        out = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=30).stdout.split()
    except Exception:
        return CANDIDATES[0]
    for name in CANDIDATES:
        if name in out:
            return name
    return CANDIDATES[0]


def exec_python(script: str, payload: str, timeout: int = 3600):
    """Run a Python snippet inside the container with one JSON argument.

    Every Blender-driven tool here works this way: the whole configuration
    arrives as a single JSON blob on argv, so there is no shell quoting to get
    wrong.

    The timeout is the point of routing everything through here. A Blender call
    that hangs hangs forever otherwise, and a tool that loops inherits one
    chance to hang per iteration.
    """
    return subprocess.run(
        ["docker", "exec", "-i", container(), "python3", "-c", script, payload],
        capture_output=True, text=True, timeout=timeout)


def exec_json(script: str, cfg: dict, sentinel: str, timeout: int = 3600):
    """Run a Blender snippet and return the dict it printed after `sentinel`.

    The snippet prints one line of `<SENTINEL> {json}` when it succeeds. That
    convention exists because Blender writes a great deal to stdout that nobody
    asked for, so the result has to be findable rather than parsed from the tail.

    Returns None and reports to stderr when the sentinel never appears, which
    covers a Blender traceback, a timeout, and a container that is not running.
    Callers treat None as failure and say so in their own words.
    """
    try:
        r = exec_python(script, json.dumps(cfg), timeout=timeout)
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            f"  timed out after {timeout}s inside {container()}\n"
            "  Blender was still running. Nothing was written.\n")
        return None
    line = next((l for l in r.stdout.splitlines() if l.startswith(sentinel)), None)
    if line is None:
        sys.stderr.write(r.stdout[-3000:] + "\n" + r.stderr[-4000:] + "\n")
        return None
    return json.loads(line[len(sentinel):])
