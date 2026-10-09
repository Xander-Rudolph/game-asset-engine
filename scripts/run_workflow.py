#!/usr/bin/env python3
"""Run a ComfyUI API-format workflow from the command line.

    scripts/run_workflow.py workflows/api/txt2img_sdxl.json \\
        --set 'prompt=a mossy stone golem, game asset, neutral grey background'

    scripts/run_workflow.py workflows/api/preset_ground_texture.json \\
        --subject 'moss and fallen pine needles'   # fills the preset's SUBJECT slot

    scripts/run_workflow.py workflows/api/img2mesh_trellis.json \\
        --image concept.png --set target=12000

    scripts/run_workflow.py --list-nodes 3D          # what the server loaded
    scripts/run_workflow.py --free                   # unload ComfyUI's models
    scripts/run_workflow.py --interrupt PROMPT_ID    # stop your own running job

--set takes either a title-addressed override, `NodeTitle.widget=value`, or a
bare `name=value` that matches any node input named `name`.  Values are parsed
as JSON when they parse, otherwise kept as strings, so `steps=20` is an int and
`prompt=20 golems` is a string.

--prompt replaces the whole Positive text.  The concept and ground texture
presets (preset_concept_*.json and preset_ground_texture.json) carry the house
technique in that text around a `<<< SUBJECT: ... >>>` slot, so on those use
--subject, which fills the slot and keeps the technique.

When the job ends, the files it wrote are listed by path under output/: first
the ones the server's /history names, then, each with its size, the ones that
nodes such as Comfy3D's Save 3D Mesh write without naming them there, found
from each node's own save path among the files written while the job ran.  A
file another job or script wrote meanwhile is not listed.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")

# The body ComfyUI's POST /free reads: unload every model it manages, then
# reset the executor's cache and free what that held.
FREE_BODY = {"unload_models": True, "free_memory": True}


def api(path: str, payload=None, method=None):
    url = f"{SERVER.rstrip('/')}/{path.lstrip('/')}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method or ("POST" if data else "GET"),
        headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"{e.code} from {url}\n{body[:4000]}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Cannot reach ComfyUI at {SERVER}: {e.reason}\n"
                         "Is it up?  docker compose --profile packaged up -d  (published image)\n"
                         "       or  docker compose --profile comfy up -d     (source build)")
    # /free, /interrupt and POST /queue answer 200 with an empty body.
    return json.loads(raw) if raw.strip() else {}


def _wait_for_server(timeout: float = 180.0) -> bool:
    """Is ComfyUI answering again? Waits up to [timeout] for it to come back.

    Used only by the retry path. A container that restarted itself takes
    the better part of a minute to reload the node packs, and asking
    during that window is what turns one dropped connection into a whole
    batch of them.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            url = f"{SERVER.rstrip('/')}/object_info"
            with urllib.request.urlopen(url, timeout=10):
                return True
        except Exception:
            time.sleep(4)
    return False


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


# ------------------------------------------------------------ queue control

def queue_ids() -> tuple[list[str], list[str]]:
    """(running, pending) prompt ids, read from GET /queue.

    Each queue item is (number, prompt_id, prompt, extra_data, outputs), so
    the id is the second field."""
    q = api("/queue")

    def ids(items):
        return [str(i[1]) for i in items or [] if isinstance(i, list) and len(i) > 1]
    return ids(q.get("queue_running")), ids(q.get("queue_pending"))


def cmd_interrupt(prompt_id: str, dry_run: bool) -> int:
    # POST /interrupt with no body stops WHATEVER is running, and on a shared
    # server that is usually someone else's job. Newer servers also honour a
    # prompt_id in the body, but an older one ignores it, so check first.
    running, pending = queue_ids()
    if prompt_id not in running:
        if prompt_id in pending:
            why = "is still pending, not running. Remove it with --delete instead"
        else:
            now = ", ".join(running) if running else "nothing"
            why = f"is not running (running now: {now})"
        raise SystemExit(f"--interrupt: {prompt_id} {why}. Nothing was interrupted.")
    if dry_run:
        print(f"  dry run: would POST /interrupt {{'prompt_id': {prompt_id!r}}}",
              file=sys.stderr)
        return 0
    api("/interrupt", {"prompt_id": prompt_id})
    print(f"  interrupted {prompt_id}")
    return 0


def cmd_delete(prompt_ids: list[str], dry_run: bool) -> int:
    running, pending = queue_ids()
    for pid in prompt_ids:
        if pid in running:
            raise SystemExit(f"--delete: {pid} is running, and a delete only removes "
                             "pending jobs. Stop it with --interrupt instead.")
        if pid not in pending:
            raise SystemExit(f"--delete: {pid} is not in the queue. Nothing was deleted.")
    if dry_run:
        print(f"  dry run: would POST /queue {{'delete': {prompt_ids!r}}}", file=sys.stderr)
        return 0
    api("/queue", {"delete": prompt_ids})
    for pid in prompt_ids:
        print(f"  deleted {pid}")
    return 0


def cmd_free(dry_run: bool) -> int:
    if dry_run:
        print(f"  dry run: would POST /free {FREE_BODY}", file=sys.stderr)
        return 0
    api("/free", FREE_BODY)
    print("  asked ComfyUI to unload its models and free memory (POST /free)")
    return 0


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
        # overwrite the NEGATIVE prompt with the positive one: the run succeeded
        # and quietly produced a worse image.  Make the caller choose.
        names = [n.get("_meta", {}).get("title", n["class_type"]) for _, n in hits]
        raise SystemExit(
            f"--set {spec}: {widget!r} exists on {len(hits)} nodes ({', '.join(names)}).\n"
            f"  Address one:  --set '{names[0]}.{widget}={raw}'\n"
            f"  Or all:       --set-all '{spec}'")
    for nid, node in hits:
        node["inputs"][widget] = val
        print(f"  set {node['_meta'].get('title', node['class_type'])}.{widget} = {val!r}")


# A fill-in slot in a prompt, as the presets and the prompt library write them:
# `<<< NAME: what to put here >>>`. The non-greedy match lets one span lines.
SLOT = re.compile(r"<<<(.*?)>>>", re.S)
SUBJECT_SLOT = re.compile(r"<<<\s*SUBJECT\b.*?>>>", re.S)


def positive_texts(graph: dict) -> list[dict]:
    """The nodes titled Positive whose `text` input is a string."""
    return [n for n in graph.values()
            if isinstance(n, dict) and "class_type" in n
            and n.get("_meta", {}).get("title") == "Positive"
            and isinstance(n.get("inputs", {}).get("text"), str)]


def apply_subject(graph: dict, subject: str, source: Path) -> None:
    """Put [subject] where the Positive text's SUBJECT slot is, and nothing else.

    A prefix strip would be wrong: preset_ground_texture.json puts the slot in
    the middle of a sentence."""
    nodes = positive_texts(graph)
    filled = 0
    for node in nodes:
        # A function, not a string, so a backslash in the subject stays literal.
        text, n = SUBJECT_SLOT.subn(lambda _m: subject, node["inputs"]["text"])
        if n:
            node["inputs"]["text"] = text
            filled += n
    if not filled:
        if nodes:
            raise SystemExit(f"--subject: {source} has no <<< SUBJECT: ... >>> slot in "
                             "its Positive text. Use --prompt to replace the whole "
                             "Positive text instead.")
        raise SystemExit(f"--subject: {source} has no node titled 'Positive' with a "
                         "text input, so no <<< SUBJECT: ... >>> slot. Address the "
                         "prompt widget with --set 'NodeTitle.widget=...' instead.")
    print(f"  set Positive.text SUBJECT slot = {subject!r}")


def warn_unfilled_slots(graph: dict, source: Path) -> None:
    names = []
    for node in positive_texts(graph):
        for inner in SLOT.findall(node["inputs"]["text"]):
            name = " ".join(inner.split(":", 1)[0].split()) or "..."
            if name not in names:
                names.append(name)
    if names:
        slots = ", ".join(f"<<< {n} >>>" for n in names)
        noun = "an unfilled slot" if len(names) == 1 else "unfilled slots"
        print(f"warning: the Positive text of {source} still has {noun} "
              f"({slots}); it reaches the model as literal text.", file=sys.stderr)


# ------------------------------------------------- files /history never names
#
# /history names a file only when the node that wrote it hands it back in its
# `ui` result.  The nodes in SAVERS write files without doing that: Comfy3D's
# Save 3D Mesh is an OUTPUT_NODE that returns its path as a STRING, so a mesh
# graph's history has no outputs at all.  So each one's file is predicted from
# the node's own inputs, as a pattern under output/.  The rules were read from
# the node source in the packaged image on 2026-10-08: ComfyUI-3D-Pack's
# nodes.py and parse_save_filename in its shared_utils/common_utils.py, and
# ComfyUI-UniRig's nodes/skinning.py, nodes/animation.py and nodes/mesh_io.py.
#
# This used to be a sweep of output/ for every file newer than the moment the
# job was queued, which also claimed what anything else wrote in that window:
# the job queued ahead of this one, or a Blender run's .blend.  Now a file is
# listed only when one of this graph's nodes would have written it, and it was
# written while this job ran.  ComfyUI runs one job at a time, so only a host
# script writing a matching name in those minutes could still be mistaken for
# this job's.  An output node that SAVERS does not know and that names nothing
# in /history is reported as such: where it writes cannot be predicted here.

CONTAINER_OUTPUT = "/app/output/"
# parse_save_filename replaces these in the file name, not the folder, with
# the time of the save.
DATE_CODES = {"%Y": r"\d{4}", "%m": r"\d{2}", "%d": r"\d{2}", "%H": r"\d{2}",
              "%M": r"\d{2}", "%S": r"\d{2}", "%f": r"\d{6}"}
ANY = r"[^/]+"   # a name that comes down a link, so is not known here


def _literal(node: dict, name: str, default: str) -> str | None:
    """A node's widget value, its default when absent, or None when linked."""
    value = node.get("inputs", {}).get(name, default)
    return None if isinstance(value, list) else str(value)


def _under_output(path: str | None) -> str | None:
    """A path a node saves to, relative to output/, or None when it is
    linked or lies outside output/."""
    if path is None:
        return None
    if path.startswith(CONTAINER_OUTPUT):
        path = path[len(CONTAINER_OUTPUT):]
    elif os.path.isabs(path):
        return None
    return os.path.normpath(path)


def _comfy3d_save(default: str):
    """[Comfy3D] Save 3D Mesh and Save 3DGS: save_path, with its date codes."""
    def rule(node: dict) -> str | None:
        rel = _under_output(_literal(node, "save_path", default))
        if rel is None:
            return None
        folder, name = os.path.split(rel)
        stem, ext = os.path.splitext(name)
        rx = re.escape(stem)
        for code, digits in DATE_CODES.items():
            rx = rx.replace(code, digits)
        return (re.escape(folder) + "/" if folder else "") + rx + re.escape(ext)
    return rule


def _unirig_skinning(node: dict) -> str:
    """UniRigAutoRig and UniRigApplySkinningMLNew: <fbx_name>_<template>.fbx,
    or rigged_<unix time>_<template>.fbx with no name, in output/ itself."""
    name = _literal(node, "fbx_name", "")
    if name is None:
        base = ANY
    elif name.strip():
        base = name.strip()
        if base.lower().endswith(".fbx"):
            base = base[:-4]
        base = re.escape(base)
    else:
        base = r"rigged_\d+"
    return base + r"_[^/]+\.fbx"


def _unirig_animation(node: dict) -> str:
    """UniRigApplyAnimation: output_name, with .fbx added when it has none,
    or else <model stem>_<animation stem>.fbx, in output/ itself."""
    out = _literal(node, "output_name", "")
    if out is None:
        return ANY + r"\.(?i:fbx)"
    if out.strip():
        name = out.strip()
        return re.escape(name if name.lower().endswith(".fbx") else name + ".fbx")
    model = _literal(node, "model_fbx_path", "")
    anim = _literal(node, "animation_file", "Breakdance.fbx")
    m = ANY if model is None else re.escape(os.path.splitext(os.path.basename(model))[0])
    a = ANY if anim is None else re.escape(os.path.splitext(anim)[0])
    return f"{m}_{a}" + r"\.fbx"


def _unirig_save_mesh(node: dict) -> str | None:
    """UniRigSaveMesh: file_path, under output/ unless it is absolute."""
    rel = _under_output(_literal(node, "file_path", "output.obj"))
    return None if rel is None else re.escape(rel)


# class_type -> rule(node) giving a regex for the path under output/, or None
# when the node's inputs do not say where it writes.
SAVERS = {
    "[Comfy3D] Save 3D Mesh": _comfy3d_save("Mesh_%Y-%m-%d-%M-%S-%f.glb"),
    "[Comfy3D] Save 3DGS": _comfy3d_save("3DGS_%Y-%m-%d-%M-%S-%f.ply"),
    # Its input image and the textured mesh's every file, at fixed names.
    "[Comfy3D] Hunyuan3D 21 TexGen": lambda node: r"Hun2-1/hunyuan_[^/]+",
    "UniRigAutoRig": _unirig_skinning,
    "UniRigApplySkinningMLNew": _unirig_skinning,
    "UniRigApplyAnimation": _unirig_animation,
    "UniRigSaveMesh": _unirig_save_mesh,
}


def ran_between(entry: dict, since: float) -> tuple[float, float]:
    """When the job started and stopped running, in seconds, from the
    timestamps on its /history status messages, a second wider each way for
    file times; from `since` to now when there are none."""
    stamps = [m[1]["timestamp"] / 1000.0
              for m in entry.get("status", {}).get("messages", [])
              if isinstance(m, list) and len(m) > 1 and isinstance(m[1], dict)
              and isinstance(m[1].get("timestamp"), (int, float))]
    if stamps:
        return min(stamps) - 1, max(stamps) + 1
    return since - 1, time.time() + 1


def unreported_files(graph: dict, entry: dict, out_dir: Path,
                     t0: float, t1: float) -> tuple[list[Path], list[tuple]]:
    """The files this graph's nodes wrote without naming them in /history.

    Returns (files, notes).  files are under out_dir, written between t0 and
    t1, and match the pattern a SAVERS rule gives for one of this graph's
    nodes, oldest first.  notes are (node id, class, why) for each node whose
    files cannot be predicted."""
    patterns, notes = [], []
    outputs = entry.get("outputs", {})
    prompt = entry.get("prompt")
    # ComfyUI keeps the ids of the graph's output nodes in the prompt's fifth field.
    output_ids = ({str(i) for i in prompt[4]}
                  if isinstance(prompt, list) and len(prompt) > 4
                  and isinstance(prompt[4], list) else set())
    for nid, node in graph.items():
        if not isinstance(node, dict):
            continue
        cls = node.get("class_type")
        if cls in SAVERS:
            rx = SAVERS[cls](node)
            if rx is None:
                notes.append((nid, cls, "its path comes down a link or lies "
                              "outside output/, so its file is not listed"))
            else:
                patterns.append(re.compile(rx))
        elif str(nid) in output_ids and not outputs.get(str(nid)):
            notes.append((nid, cls, "an output node that named no files in "
                          "/history, and this script does not know where it "
                          "writes, so look in output/ for anything it made"))
    files = []
    if patterns and out_dir.is_dir():
        for f in out_dir.rglob("*"):
            try:
                if not f.is_file() or not t0 <= f.stat().st_mtime <= t1:
                    continue
            except OSError:
                continue
            rel = f.relative_to(out_dir).as_posix()
            if any(p.fullmatch(rel) for p in patterns):
                files.append(f)
    files.sort(key=lambda f: f.stat().st_mtime)
    return files, notes


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


def report(entry: dict, since: float = 0.0, graph: dict | None = None) -> int:
    """Print how the job ended and the files it wrote; 1 if it failed.

    `graph` is the graph that was queued.  Without it, the copy /history keeps
    is used."""
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

    found, reported = 0, set()
    for nid, out in entry.get("outputs", {}).items():
        for key, items in out.items():
            if not isinstance(items, list):
                continue
            for it in items:
                if isinstance(it, dict) and "filename" in it:
                    sub = it.get("subfolder") or ""
                    rel = f"{sub}/{it['filename']}" if sub else it["filename"]
                    print(f"  output/{rel}")
                    reported.add(rel)
                    found += 1
                elif isinstance(it, str) and ("/" in it or "." in it):
                    # A path a node hands back as text, such as the FBX that
                    # UniRig's preview names, inside the container.
                    if it.startswith(CONTAINER_OUTPUT):
                        reported.add(it[len(CONTAINER_OUTPUT):])
                        it = "output/" + it[len(CONTAINER_OUTPUT):]
                    else:
                        reported.add(it)
                    print(f"  {it}")
                    found += 1

    if graph is None:
        prompt = entry.get("prompt")
        graph = prompt[2] if isinstance(prompt, list) and len(prompt) > 2 else {}
    t0, t1 = ran_between(entry, since)
    files, notes = unreported_files(graph, entry, ROOT / "output", t0, t1)
    for f in files:
        rel = f.relative_to(ROOT / "output").as_posix()
        if rel not in reported:
            print(f"  output/{rel}  ({f.stat().st_size / 1024:.0f} KB)")
            found += 1
    for nid, cls, why in notes:
        print(f"  (node {nid}, {cls}: {why})")
    if not found and not notes:
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
                    help="replace the WHOLE Positive text (shorthand for --set "
                         "'Positive.text=TEXT'). On preset_concept_*.json and "
                         "preset_ground_texture.json that drops the house technique "
                         "too; use --subject there")
    ap.add_argument("--subject", metavar="TEXT",
                    help="fill only the <<< SUBJECT: ... >>> slot in the Positive "
                         "text and keep the rest of it. Refused with --prompt, and "
                         "on a graph whose Positive text has no SUBJECT slot")
    ap.add_argument("--negative", metavar="TEXT",
                    help="shorthand for --set 'Negative.text=TEXT'")
    ap.add_argument("--image", type=Path,
                    help="upload this file and point every LoadImage at it")
    ap.add_argument("--list-nodes", nargs="?", const="", metavar="SUBSTR",
                    help="list node types the server has loaded, filtered")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the resolved graph instead of queueing it. With "
                         "--free, --interrupt or --delete, check but send nothing")
    ap.add_argument("--retries", type=int, default=0, metavar="N",
                    help="on a dropped connection, wait for the server to come "
                         "back and try again, up to N times. Use in batches")
    ap.add_argument("--free", action="store_true",
                    help="POST /free to unload the models ComfyUI manages and free "
                         "memory, then exit, or queue the workflow if one is given. "
                         "The server acts on it once the running job, if any, ends. "
                         "It does NOT release ComfyUI-3D-Pack's Hunyuan pipelines, "
                         "which the pack caches itself; only a container restart does")
    ap.add_argument("--interrupt", metavar="PROMPT_ID",
                    help="stop PROMPT_ID, only if it is the job running now. "
                         "/interrupt stops whatever is running, so this reads /queue "
                         "first and refuses any other id. Stop only jobs you started")
    ap.add_argument("--delete", action="append", default=[], metavar="PROMPT_ID",
                    help="remove a pending job from the queue; repeatable. Refuses "
                         "an id that is running or not queued")
    args = ap.parse_args()

    if args.subject is not None and args.prompt is not None:
        ap.error("--subject and --prompt cannot be combined: --prompt replaces the "
                 "whole Positive text, --subject fills only its SUBJECT slot")

    controlled = False
    if args.interrupt:
        controlled = True
        cmd_interrupt(args.interrupt, args.dry_run)
    if args.delete:
        controlled = True
        cmd_delete(args.delete, args.dry_run)
    if args.free:
        controlled = True
        cmd_free(args.dry_run)

    if args.list_nodes is not None:
        info = api("/object_info")
        names = sorted(n for n in info if args.list_nodes.lower() in n.lower())
        for n in names:
            print(f"  {n}")
        print(f"\n{len(names)} of {len(info)} node types")
        return 0

    if not args.workflow:
        if controlled:
            return 0
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
    if args.subject is not None:
        apply_subject(graph, args.subject, args.workflow)
    if args.negative is not None:
        apply_override(graph, f"Negative.text={args.negative}")
    for spec in args.set:
        apply_override(graph, spec)
    for spec in args.set_all:
        apply_override(graph, spec, allow_many=True)
    warn_unfilled_slots(graph, args.workflow)

    if args.dry_run:
        print(json.dumps(graph, indent=2))
        return 0

    graph = {k: v for k, v in graph.items()
             if isinstance(v, dict) and "class_type" in v}

    # Retried, because the failure this guards is INVISIBLE.
    #
    # ComfyUI drops the connection mid-generation and the container
    # restarts itself. Without a retry this raises, the shell loop around
    # it moves on to the next name, and the batch reports every item while
    # writing files for only some -- eleven icons went missing that way
    # before anyone thought to count the output. So a batch should pass
    # --retries: waiting for the server to answer again and trying once
    # more turns a silent hole into a pause.
    attempts = max(1, args.retries + 1)
    for attempt in range(1, attempts + 1):
        started = time.time()
        try:
            res = api("/prompt", {"prompt": graph,
                                  "client_id": uuid.uuid4().hex})
            if res.get("node_errors"):
                print(json.dumps(res["node_errors"], indent=2))
                return 1
            pid = res["prompt_id"]
            print(f"  queued {pid}")
            return report(wait_for(pid), since=started, graph=graph)
        except SystemExit:
            # A graph the server rejects will be rejected again; only a
            # dropped connection is worth another go, and `api` turns both
            # into SystemExit. Tell them apart by asking whether the server
            # is there at all.
            if attempt == attempts or not _wait_for_server():
                raise
            print(f"  lost the server; retrying ({attempt}/{args.retries})")


if __name__ == "__main__":
    sys.exit(main())
