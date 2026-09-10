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

import os
import subprocess

# In preference order. The from-source profile wins when several are up, because
# someone running that profile is editing node source and means to test it.
CANDIDATES = ("comfyui", "comfyui-packaged", "comfyui-local")


def container() -> str:
    """The name of the running ComfyUI container.

    Falls back to the first candidate so callers still produce a sensible error
    message when nothing is running, rather than a confusing empty string.
    """
    override = os.environ.get("ATHANOR_CONTAINER")
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
    """
    return subprocess.run(
        ["docker", "exec", "-i", container(), "python3", "-c", script, payload],
        capture_output=True, text=True, timeout=timeout)
