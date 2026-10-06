#!/usr/bin/env python3
"""Print the prompt a ComfyUI image was made from.

ComfyUI writes the whole graph it ran into every image it saves: a `prompt`
text chunk in a PNG from SaveImage, and an EXIF `prompt:` field in a WebP from
SaveAnimatedWEBP.  This reads that graph back and prints the text of each text
encoder in it, marked positive or negative by the sampler input it reaches.  A
prompt typed into a separate string node, as the editor graphs do, is followed
back to that node.

    scripts/image_prompt.py output/concept_00012_.png
    scripts/image_prompt.py output/*.png
    scripts/image_prompt.py --json output/concept_00012_.png > graph.json

--json prints the whole embedded graph instead, in the API format that
scripts/run_workflow.py takes.

An image that was edited, converted or screenshotted has usually lost the graph,
and so has one from a server started with --disable-metadata.  Standard library
only, on the host.  Exits 1 when a file has no ComfyUI prompt in it.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# The inputs that hold the text itself.  A text encoder's other string inputs,
# such as the instruction an image edit encoder wraps round the prompt, are
# settings rather than the prompt.
TEXT_KEYS = ("text", "text_g", "text_l", "prompt", "tags", "lyrics")
# Where a string node keeps its text, when a prompt is wired in from one.
SOURCE_KEYS = ("value", "text", "string", "prompt")
# A node whose output is empty conditioning, whatever went in.  A negative made
# by zeroing the positive has no text of its own.
ZEROING = ("ConditioningZeroOut",)


def png_texts(data: bytes) -> dict[str, str]:
    """The text chunks of a PNG: tEXt, zTXt, iTXt, and the `comf` chunks an
    animated PNG from ComfyUI carries."""
    texts: dict[str, str] = {}
    off = len(PNG_SIGNATURE)
    while off + 8 <= len(data):
        length, ctype = struct.unpack_from(">I4s", data, off)
        body = data[off + 8: off + 8 + length]
        off += 12 + length
        if ctype not in (b"tEXt", b"zTXt", b"iTXt", b"comf"):
            continue
        key, _, rest = body.partition(b"\0")
        try:
            if ctype in (b"tEXt", b"comf"):
                value = rest.decode("latin-1")
            elif ctype == b"zTXt":
                value = zlib.decompress(rest[1:]).decode("latin-1")
            else:
                compressed, rest = rest[0], rest[2:]
                _language, _, rest = rest.partition(b"\0")
                _translated, _, rest = rest.partition(b"\0")
                value = (zlib.decompress(rest) if compressed else rest).decode("utf-8")
        except (zlib.error, UnicodeDecodeError, IndexError):
            continue
        texts.setdefault(key.decode("latin-1"), value)
    return texts


def embedded_prompt(path: Path) -> dict | None:
    """The API-format graph ComfyUI saved in the image, or None."""
    data = path.read_bytes()
    if data.startswith(PNG_SIGNATURE):
        raw = png_texts(data).get("prompt")
        if raw is None:
            return None
        try:
            graph = json.loads(raw)
        except ValueError:
            return None
        return graph if isinstance(graph, dict) else None
    # A WebP keeps it in EXIF as `prompt:{...}`.  json.dumps writes ASCII, so a
    # byte search finds it without parsing the EXIF block.
    text = data.decode("latin-1")
    start = text.find("prompt:{")
    while start >= 0:
        try:
            graph, _ = json.JSONDecoder().raw_decode(text, start + len("prompt:"))
            if isinstance(graph, dict):
                return graph
        except ValueError:
            pass
        start = text.find("prompt:{", start + 1)
    return None


def is_link(value) -> bool:
    return (isinstance(value, list) and len(value) == 2
            and isinstance(value[0], (str, int)) and isinstance(value[1], int))


def resolve_text(graph: dict, value, seen: set[str]) -> tuple[str | None, list[str]]:
    """The string an input holds, following links back through string nodes.
    Returns the text, or None, and the node ids it came through."""
    if isinstance(value, str):
        return value, []
    if not is_link(value):
        return None, []
    nid = str(value[0])
    node = graph.get(nid)
    if nid in seen or not isinstance(node, dict):
        return None, [nid]
    seen.add(nid)
    inputs = node.get("inputs", {})
    for key in SOURCE_KEYS:
        if key in inputs:
            text, via = resolve_text(graph, inputs[key], seen)
            if text is not None:
                return text, [nid] + via
    return None, [nid]


def roles(graph: dict) -> dict[str, set[str]]:
    """Which of positive and negative each node's conditioning reaches."""
    found: dict[str, set[str]] = {}

    def mark(nid: str, role: str, seen: set[str]) -> None:
        node = graph.get(nid)
        if nid in seen or not isinstance(node, dict):
            return
        seen.add(nid)
        if node.get("class_type") in ZEROING:
            return
        found.setdefault(nid, set()).add(role)
        for key, value in node.get("inputs", {}).items():
            if is_link(value) and "conditioning" in key:
                mark(str(value[0]), role, seen)

    for node in graph.values():
        if not isinstance(node, dict):
            continue
        for key, value in node.get("inputs", {}).items():
            if key in ("positive", "negative") and is_link(value):
                mark(str(value[0]), key, set())
    return found


def prompts(graph: dict) -> list[tuple[str, str, list[str]]]:
    """(role, text, where) for every text a text encoder in the graph was given."""
    reached = roles(graph)
    rows: dict[tuple[str, str], list[str]] = {}
    for nid, node in graph.items():
        if not isinstance(node, dict) or "TextEncode" not in str(node.get("class_type")):
            continue
        r = reached.get(nid, set())
        role = ("positive and negative" if len(r) == 2
                else next(iter(r)) if r else "prompt")
        for key in TEXT_KEYS:
            if key not in node.get("inputs", {}):
                continue
            text, via = resolve_text(graph, node["inputs"][key], set())
            if text is None:
                continue
            where = f"node {nid} {node['class_type']}.{key}"
            if via:
                src = graph.get(via[-1], {}).get("class_type", "?")
                where += f", from node {via[-1]} {src}"
            label = role if key in ("text", "text_g", "prompt") else f"{role} {key}"
            rows.setdefault((label, text), []).append(where)
    order = {"positive": 0, "positive and negative": 1, "negative": 2}
    return sorted(((label, text, where) for (label, text), where in rows.items()),
                  key=lambda row: (order.get(row[0].split(" ")[0], 3), row[0]))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", type=Path, help="PNG or WebP files ComfyUI saved")
    ap.add_argument("--json", action="store_true",
                    help="print the whole embedded graph rather than its prompts")
    args = ap.parse_args()

    status, printed = 0, False
    for path in args.images:
        try:
            graph = embedded_prompt(path)
        except OSError as e:
            print(f"{path}: {e.strerror or e}", file=sys.stderr)
            status = 1
            continue
        if graph is None:
            print(f"{path}: no ComfyUI prompt in it", file=sys.stderr)
            status = 1
            continue
        if args.json:
            print(json.dumps(graph, indent=2, ensure_ascii=False))
            continue
        found = prompts(graph)
        if not found:
            print(f"{path}: a ComfyUI graph, but no text encoder in it has a prompt",
                  file=sys.stderr)
            status = 1
            continue
        blocks = [f"{label}  ({'; '.join(where)})\n" + (text if text.strip() else "(empty)")
                  for label, text, where in found]
        if len(args.images) > 1:
            blocks.insert(0, f"== {path}")
        print(("\n" if printed else "") + "\n\n".join(blocks))
        printed = True
    return status


if __name__ == "__main__":
    sys.exit(main())
