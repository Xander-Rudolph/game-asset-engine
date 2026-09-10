#!/usr/bin/env python3
"""Check every workflow in workflows/api against a running ComfyUI's /object_info.

Catches the three ways a hand-written API graph goes wrong before you queue it
and wait ninety seconds for the same news:

  * a class_type the server never loaded (node pack missing, or import failed)
  * a widget name that does not exist on that node
  * a required input left unwired

    scripts/validate_workflows.py
    scripts/validate_workflows.py workflows/api/img2mesh_triposg.json
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")


def object_info() -> dict:
    try:
        with urllib.request.urlopen(f"{SERVER}/object_info", timeout=120) as r:
            return json.load(r)
    except Exception as e:
        sys.exit(f"Cannot reach ComfyUI at {SERVER}: {e}\n"
                 "  docker compose --profile comfy up -d")


def check(path: Path, info: dict) -> list[str]:
    graph = json.loads(path.read_text())
    problems = []
    for nid, node in graph.items():
        if not isinstance(node, dict) or "class_type" not in node:
            continue                                    # "_comment" and friends
        ct = node["class_type"]
        spec = info.get(ct)
        if spec is None:
            near = [n for n in info if ct.split()[-1].lower() in n.lower()][:3]
            problems.append(f"  [{nid}] unknown node {ct!r}"
                            + (f" — did you mean {near}?" if near else ""))
            continue
        req = spec["input"].get("required", {})
        opt = spec["input"].get("optional", {})
        known = set(req) | set(opt)
        for name in node.get("inputs", {}):
            if name not in known:
                problems.append(f"  [{nid}] {ct}: no input {name!r} "
                                f"(has {sorted(known)})")
        for name in req:
            if name not in node.get("inputs", {}):
                problems.append(f"  [{nid}] {ct}: required input {name!r} not set")
        for name, val in node.get("inputs", {}).items():
            if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str):
                if val[0] not in graph:
                    problems.append(f"  [{nid}] {ct}.{name} wired to missing node {val[0]}")
    return problems


def main() -> int:
    targets = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "workflows/api").glob("*.json"))
    info = object_info()
    print(f"{len(info)} node types on {SERVER}\n")
    bad = 0
    for p in targets:
        problems = check(p, info)
        try:
            shown = p.resolve().relative_to(ROOT)
        except ValueError:
            shown = p
        print(f"{'FAIL' if problems else 'ok  '} {shown}")
        for line in problems:
            print(line)
        bad += bool(problems)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
