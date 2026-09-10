#!/usr/bin/env python3
"""Run a ComfyUI API-format workflow from the command line.

    scripts/run_workflow.py workflows/api/txt2img_sdxl.json \
        --set 'prompt=a mossy stone golem, game asset, neutral grey background'

    scripts/run_workflow.py workflows/api/img2mesh_triposr.json \
        --image concept.png --set faces=18000

    scripts/run_workflow.py --list-nodes 3D          # what the server loaded

--set takes either a title-addressed override, `NodeTitle.widget=value`, or a
bare `name=value` that matches any node input named `name`.  Values are parsed
as JSON when they parse, otherwise kept as strings, so `steps=20` is an int and
`prompt=20 golems` is a string.

Outputs (images and meshes alike) are reported by path under output/.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")


def api(path: str, payload=None, method=None):
    url = f"{SERVER.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method or ("POST" if data else "GET"),
        headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"{e.code} from {url}\n{body[:4000]}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Cannot reach ComfyUI at {SERVER}: {e.reason}\n"
                         "Is it up?  docker compose --profile comfy up -d")


def upload_image(path: Path) -> str:
    """Multipart POST to /upload/image; returns the server-side filename."""
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = b"".join([
        f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
        f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode(),
        path.read_bytes(), b"\r\n",
        f'--{boundary}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n'.encode(),
        f"--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        f"{SERVER.rstrip('/')}/upload/image", data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        info = json.load(r)
    name = info["name"]
    if info.get("subfolder"):
        name = f"{info['subfolder']}/{name}"
    return name


# ------------------------------------------------------------------ overrides

def parse_value(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def apply_override(graph: dict, spec: str, allow_many: bool = False) -> None:
    key, _, raw = spec.partition("=")
    if not _:
        raise SystemExit(f"--set wants key=value, got {spec!r}")
    val = parse_value(raw)
    title, _, widget = key.rpartition(".")

    hits = []
    for nid, node in graph.items():
        if not isinstance(node, dict) or "class_type" not in node:
            continue                                  # "_comment" and friends
        if title and node.get("_meta", {}).get("title") != title:
            continue
        if widget in node.get("inputs", {}):
            hits.append((nid, node))
    if not hits:
        where = f"in node titled {title!r}" if title else "in any node"
        raise SystemExit(f"--set {spec}: no input named {widget!r} {where}")
    if len(hits) > 1 and not title and not allow_many:
        # Silently writing to every match is how a bare `--set text=...` used to
        # overwrite the NEGATIVE prompt with the positive one — the run succeeded
        # and quietly produced a worse image.  Make the caller choose.
        names = [n.get("_meta", {}).get("title", n["class_type"]) for _, n in hits]
        raise SystemExit(
            f"--set {spec}: {widget!r} exists on {len(hits)} nodes ({', '.join(names)}).\n"
            f"  Address one:  --set '{names[0]}.{widget}={raw}'\n"
            f"  Or all:       --set-all '{spec}'")
    for nid, node in hits:
        node["inputs"][widget] = val
        print(f"  set {node['_meta'].get('title', node['class_type'])}.{widget} = {val!r}")


# ----------------------------------------------------------------------- main

def wait_for(prompt_id: str, poll=1.0) -> dict:
    spinner, i, t0 = "|/-\\", 0, time.time()
    while True:
        hist = api(f"/history/{prompt_id}")
        if prompt_id in hist:
            entry = hist[prompt_id]
            st = entry.get("status", {})
            if st.get("completed") or st.get("status_str") in ("success", "error"):
                print(f"\r  done in {time.time()-t0:.0f}s" + " " * 20)
                return entry
        if sys.stdout.isatty():
            print(f"\r  {spinner[i % 4]} {time.time()-t0:5.0f}s", end="", flush=True)
        i += 1
        time.sleep(poll)


def report(entry: dict, since: float = 0.0) -> int:
    st = entry.get("status", {})
    if st.get("status_str") == "error":
        for kind, *rest in st.get("messages", []):
            if kind == "execution_error":
                d = rest[0]
                print(f"\nERROR in {d.get('node_type')} ({d.get('node_id')}): "
                      f"{d.get('exception_type')}: {d.get('exception_message')}")
                for line in (d.get("traceback") or [])[-12:]:
                    print("   ", line.rstrip())
                return 1
        print(f"\nERROR: {json.dumps(st)[:2000]}")
        return 1

    found, reported = 0, []
    for nid, out in entry.get("outputs", {}).items():
        for key, items in out.items():
            if not isinstance(items, list):
                continue
            for it in items:
                if isinstance(it, dict) and "filename" in it:
                    sub = it.get("subfolder") or ""
                    print(f"  output/{sub + '/' if sub else ''}{it['filename']}")
                    reported.append(it["filename"])
                    found += 1
                elif isinstance(it, str) and ("/" in it or "." in it):
                    print(f"  {it}")
                    found += 1
    # Comfy3D's Save 3D Mesh is an OUTPUT_NODE but records nothing in history —
    # it returns the path as a STRING and never populates `ui`.  So the meshes
    # land on disk and the API says nothing about them.  Sweep for what appeared.
    out_dir = ROOT / "output"
    if out_dir.is_dir():
        fresh = sorted((f for f in out_dir.rglob("*")
                        if f.is_file() and f.stat().st_mtime >= since - 1),
                       key=lambda f: f.stat().st_mtime)
        for f in fresh:
            rel = f.relative_to(ROOT)
            if not any(str(rel).endswith(seen) for seen in reported):
                print(f"  {rel}  ({f.stat().st_size / 1024:.0f} KB)")
                found += 1
    if not found:
        print("  (workflow produced no file outputs)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workflow", nargs="?", type=Path)
    ap.add_argument("--set", action="append", default=[], metavar="K=V",
                    help="override a widget; repeatable. Refuses an ambiguous bare key")
    ap.add_argument("--set-all", action="append", default=[], metavar="K=V",
                    help="override a widget on EVERY node that has it")
    ap.add_argument("--prompt", metavar="TEXT",
                    help="shorthand for --set 'Positive.text=TEXT'")
    ap.add_argument("--negative", metavar="TEXT",
                    help="shorthand for --set 'Negative.text=TEXT'")
    ap.add_argument("--image", type=Path,
                    help="upload this file and point every LoadImage at it")
    ap.add_argument("--list-nodes", nargs="?", const="", metavar="SUBSTR",
                    help="list node types the server has loaded, filtered")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the resolved graph instead of queueing it")
    args = ap.parse_args()

    if args.list_nodes is not None:
        info = api("/object_info")
        names = sorted(n for n in info if args.list_nodes.lower() in n.lower())
        for n in names:
            print(f"  {n}")
        print(f"\n{len(names)} of {len(info)} node types")
        return 0

    if not args.workflow:
        ap.error("a workflow file is required (or use --list-nodes)")
    graph = json.loads(args.workflow.read_text())

    if args.image:
        name = upload_image(args.image)
        print(f"  uploaded {args.image} as {name}")
        for node in graph.values():
            if not isinstance(node, dict) or "class_type" not in node:
                continue
            if node["class_type"] in ("LoadImage", "LoadImageMask"):
                node["inputs"]["image"] = name

    if args.prompt is not None:
        apply_override(graph, f"Positive.text={args.prompt}")
    if args.negative is not None:
        apply_override(graph, f"Negative.text={args.negative}")
    for spec in args.set:
        apply_override(graph, spec)
    for spec in args.set_all:
        apply_override(graph, spec, allow_many=True)

    if args.dry_run:
        print(json.dumps(graph, indent=2))
        return 0

    graph = {k: v for k, v in graph.items()
             if isinstance(v, dict) and "class_type" in v}
    started = time.time()
    res = api("/prompt", {"prompt": graph, "client_id": uuid.uuid4().hex})
    if res.get("node_errors"):
        print(json.dumps(res["node_errors"], indent=2))
        return 1
    pid = res["prompt_id"]
    print(f"  queued {pid}")
    return report(wait_for(pid), since=started)


if __name__ == "__main__":
    sys.exit(main())
