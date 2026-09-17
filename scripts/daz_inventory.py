#!/usr/bin/env python3
"""List what a Daz content library holds: figures, bones, morphs and HD morphs.

    scripts/daz_inventory.py "$DAZ_LIBRARY"
    scripts/daz_inventory.py "$DAZ_LIBRARY/data" --brief
    scripts/daz_inventory.py "$DAZ_LIBRARY" --json > output/daz_inventory.json
    scripts/daz_inventory.py --selftest
    scripts/daz_inventory.py --sample /tmp/daz_sample   # no library yet? a synthetic one
    scripts/daz_inventory.py /tmp/daz_sample

$DAZ_LIBRARY is a content directory: the folder holding data/, People/ and
Runtime/ once a product such as Genesis 9 Starter Essentials is unpacked. Any
folder inside one works too. The path must be outside this repository, and so
must every folder the walk would enter: Daz content never goes in the repo, so
a path inside it, or a parent of it, is refused before anything is read.
Symlinks are followed, so a library may link data/ in from another disk, but a
link that resolves into or above the repo is skipped, and a folder reached a
second time (another link to it, or a link loop) is walked once.

WHY: the Daz Genesis research page (docs/reference/daz-genesis.md) quotes
vertex, bone and morph counts from forum posts, Daz's file lists and an
importer's tables. A library on disk can answer those questions itself, with no
Daz Studio, Blender or GPU, because DSON is JSON. Files are decoded with the
standard library's gzip and json modules, and nothing outside the standard
library is imported.

WHAT IT READS. Every .dsf under the directory, per the DSON specification
(docs.daz3d.com/public/dson_spec). A .dsf is plain JSON or gzip; the reader
checks the gzip magic bytes, so both work. It does not decode a raw zlib
stream, which the specification's wording ("zlib compressed") allows but Daz
Studio is reported to write gzip instead (research/claims/daz-genesis.json,
DAZ-070); such a file is reported as unreadable.

- A figure file is a .dsf with a non-empty geometry_library. For each one it
  prints every geometry's vertex and polygon counts (polygons split into quads
  and triangles), and the bones: node_library entries of type "bone", by their
  name (the id when a name is missing; --json gives both).
- Figure files are grouped by the content type their author set: the
  presentation type of the first "figure" node that has one, or else of the
  first node of any type that has one. "Actor" or "Actor/..." is a body;
  "Follower/Attachment..." is an attachment (fitted eyes, mouth, lashes and
  tear, but eyebrows too, which carry the same type); "Follower/Wardrobe...",
  "Follower/Hair..." and "Prop..." are wardrobe, hair and prop; any other type
  is "other", and a file with none is "none". The report lists body and
  attachment figures first, then the other geometry, and tallies every
  content type. Nothing in DSON marks a projection template or an optional
  eyebrow style as such, so a template counts as the wardrobe or hair its type
  says, and an eyebrow style as an attachment.
- Its morphs are the modifiers in the .dsf files under the Morphs folder beside
  the figure file (data/Daz 3D/Genesis 9/Base/Genesis9.dsf owns
  data/Daz 3D/Genesis 9/Base/Morphs/**). Folder names are matched without
  regard to case: on Linux one product unpacked as data/DAZ 3D/... and another
  as data/Daz 3D/... make two folders where Windows has one. Skin bindings are
  left out. A morph whose "parent" URI names a file goes to the figure with
  that asset id: when two figure files share a folder, or when the URI names
  a figure other than the one beside the folder. A morph file outside every
  figure's Morphs folder goes to the figure its parent URI names, when exactly
  one figure in the walk has that asset id; the report counts such morphs as
  "attached by parent URI". Names are grouped by prefix: eCTRLv, facs_ctrl_v,
  facs_bs_, facs_cbs_, facs_jnt_, pJCM, body_cbs_ and other. Controllers with
  no deltas count as morphs, because the visemes are controllers; each group
  says how many hold vertex deltas. A morph is a modifier with a morph block,
  or with no morph block and a channel of type float or int.
- An alias is a modifier whose channel type is "alias": a second name that
  points at another modifier's channel through target_channel. In Genesis 9
  Starter Essentials every alias file is named alias_... and each alias
  carries the name of the modifier it points at, so counting aliases as
  morphs counts those names twice. Aliases are counted and listed apart
  (text: by id; --json: name, id and target_channel), grouped by the name
  they carry, and never counted as morphs.
- Any other modifier (no morph block, and no channel or a channel of another
  type, such as "file") is listed apart as an other modifier, never as a
  morph.
- HD morphs are those with "_div2" in the name or file name, or with an
  hd_url; an alias is never one. For each it says whether the .dsf holds
  base-resolution deltas and an hd_url, only an hd_url, only deltas, or
  neither, and whether the .dhdm the hd_url names is on disk (matched without
  regard to case, because Daz's own URIs mix "DAZ 3D" and "Daz 3D").
- Morph files that reach no figure in the walk are listed at the end, grouped
  by the figure their parent URI names (without regard to case).

A .dsf that decodes to valid JSON but is not DSON (the top level is not an
object, or is an object with no file_version, asset_info, scene or *_library
key) is skipped and counted as "not DSON". It is listed in the report's NOT
DSON section and in --json's "not_dson", with its top-level keys, and is not
an error: the exit status stays 0. Genesis 9 Starter Essentials ships one, a
face group file under Base/Tools/Geometry/Face Groups.

A file that will not decode (bad gzip, truncated gzip, not UTF-8, bad JSON,
a geometry without a counted vertex array, a morph whose deltas are not a
counted array) is counted as unreadable and gets one "skipped <file>:
<reason>" line on stderr, after the report, and an entry of kind "file" in
--json's "errors". A folder that cannot be listed (kind "folder") and a link
into or above the repo (kind "link") get the same line, are counted apart
from the .dsf files, and the walk carries on. File and folder names that are
not valid UTF-8 are printed with \\xNN escapes.

--brief drops the name lists from the text report. --json prints one JSON
object on stdout instead: root, file counts (read: gzip, text, not_dson and
unreadable, which add up to dsf_files), walk skips, geometry_roles and
content_types tallies, figures (content_type and role, geometries, bones with
id, label and parent, morphs with delta counts, hd_url and how each was
attached, morph_groups, hd_morphs, aliases with alias_groups, and
other_modifiers), unattached morphs, aliases and other modifiers, not_dson
and errors.
--selftest writes a small synthetic DSON tree (invented names, gzip and plain)
to a temporary directory, runs the inventory and the command line over it and
checks every count. --sample DIR writes that same tree to DIR, to try the
report without any Daz content. It contains deliberately broken files, so give
it a folder of its own, never the real library's.

Exit status: 0 when every .dsf was read or skipped as not DSON and every
folder was walked; 1 when some .dsf were unreadable, a folder could not be
listed or a link into the repo was skipped (the report is still printed), or
a self-test check failed; 2 for a refused or missing path, or a sample that
could not be written.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent

GROUPS = ("eCTRLv", "facs_ctrl_v", "facs_bs_", "facs_cbs_", "facs_jnt_", "pJCM",
          "body_cbs_")
OTHER = "other"

HD_STATES = {
    "deltas_and_hd_url": "holds {n} base deltas and an hd_url",
    "hd_url_only": "holds only an hd_url, no base deltas",
    "deltas_only": "holds {n} base deltas and no hd_url",
    "neither": "holds neither deltas nor an hd_url",
}
HD_BRIEF = {"deltas_and_hd_url": "base deltas and an hd_url", "hd_url_only": "only an hd_url",
            "deltas_only": "base deltas, no hd_url", "neither": "neither"}

# A figure file's role, from its content type (presentation type), in report order.
# (role, content type prefix); a prefix matches the type itself or the type followed by "/".
ROLE_PREFIXES = (("body", "Actor"), ("attachment", "Follower/Attachment"),
                 ("wardrobe", "Follower/Wardrobe"), ("hair", "Follower/Hair"), ("prop", "Prop"))
ROLES = ("body", "attachment", "wardrobe", "hair", "prop", "other", "none")
FIGURE_ROLES = ("body", "attachment")
DIAL_CHANNELS = ("float", "int")        # a modifier with no morph block and one of these is a morph
DSON_KEYS = "file_version, asset_info, scene or *_library"


class Unreadable(Exception):
    """A .dsf that did not decode, or DSON whose structure is broken."""


class NotDson(Exception):
    """A .dsf that decoded to valid JSON with none of DSON's top-level keys."""

    def __init__(self, reason: str, form: str):
        super().__init__(reason)
        self.form = form


# ---------------------------------------------------------------- guards

def repo_clash(path: Path) -> str | None:
    """Why `path` may not be walked, or None. Symlinks are resolved first."""
    real = Path(os.path.realpath(path))
    repo = Path(os.path.realpath(ROOT))
    if real == repo or repo in real.parents:
        return (f"refusing {path}: it is inside this repository ({repo}). Daz content "
                "must never enter the repo; keep the library outside it.")
    if real in repo.parents:
        return (f"refusing {path}: this repository ({repo}) is inside it, so the walk "
                "would enter the repo. Point at the content directory itself.")
    return None


def shown(path) -> str:
    """A path as text that always prints: bytes that are not UTF-8 appear as \\xNN."""
    return os.fsencode(path).decode("utf-8", "backslashreplace")


def plural(n: int, word: str, words: str | None = None) -> str:
    return f"{n} {word if n == 1 else words or word + 's'}"


# ---------------------------------------------------------------- decoding

def read_dson(path: Path) -> tuple[dict, str]:
    """Decode one DSON file into (document, "gzip" or "text").

    Raises NotDson for valid JSON that is not DSON, and Unreadable with a
    one-line reason for anything that does not decode; never anything else
    for bad data.
    """
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise Unreadable(f"cannot read: {e.strerror or e}") from None
    if not raw:
        raise Unreadable("empty file (0 bytes)")
    form = "text"
    if raw[:2] == b"\x1f\x8b":
        form = "gzip"
        try:
            raw = gzip.decompress(raw)
        except Exception as e:          # BadGzipFile, EOFError, zlib.error
            raise Unreadable(f"gzip error: {type(e).__name__}: {e}") from None
    elif len(raw) > 1 and raw[0] == 0x78 and (raw[0] << 8 | raw[1]) % 31 == 0:
        raise Unreadable("starts like a raw zlib stream, not gzip; this reader decodes "
                         "gzip and plain JSON only")
    where = " inside the gzip" if form == "gzip" else ""
    if raw[:3] == b"\xef\xbb\xbf":
        encoding = "utf-8-sig"
    elif raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        encoding = "utf-16"
    else:
        encoding = "utf-8"
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError as e:
        raise Unreadable(f"not {encoding} text{where}: {e.reason} at byte {e.start}") from None
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise Unreadable(f"JSON error{where}: {e.msg} at line {e.lineno} "
                         f"column {e.colno}") from None
    except ValueError as e:             # an integer too long to convert, on Python 3.11+
        raise Unreadable(f"JSON error{where}: {e}") from None
    except RecursionError:
        raise Unreadable(f"JSON error{where}: nested too deeply to parse") from None
    if not isinstance(doc, dict):
        kind = {list: "list", str: "string", bool: "boolean", type(None): "null"}.get(
            type(doc), "number")
        raise NotDson(f"not DSON: the top level is a JSON {kind}, not an object", form)
    if not any(k == "file_version" or k == "asset_info" or k == "scene"
               or k.endswith("_library") for k in doc):
        if not doc:
            raise NotDson("not DSON: an empty JSON object", form)
        keys = list(doc)
        more = f" and {len(keys) - 5} more" if len(keys) > 5 else ""
        raise NotDson(f"not DSON: no {DSON_KEYS} key; top-level keys "
                      f"{', '.join(keys[:5])}{more}", form)
    return doc, form


def as_list(obj: dict, key: str) -> list:
    value = obj.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise Unreadable(f"not DSON: {key} is a {type(value).__name__}, not an array")
    return value


def counted(obj, what: str) -> tuple[list, str | None]:
    """The values of a DSON counted array, and a warning if count disagrees."""
    if not isinstance(obj, dict) or not isinstance(obj.get("values"), list):
        raise Unreadable(f"not DSON: {what} is not a counted array with count and values")
    values = obj["values"]
    warning = None
    if obj.get("count") != len(values):
        warning = f"{what}.count is {obj.get('count')!r} but values holds {len(values)}"
    return values, warning


def asset_id(doc: dict) -> str | None:
    info = doc.get("asset_info")
    return info.get("id") if isinstance(info, dict) and isinstance(info.get("id"), str) else None


def uri_file(uri) -> str | None:
    """The file part of a DSON URI, percent-decoded and case-folded, for matching."""
    if not isinstance(uri, str) or not uri.split("#")[0]:
        return None
    return unquote(uri.split("#")[0]).casefold()


# ---------------------------------------------------------------- summaries

def summarise_figure(doc: dict) -> dict:
    warnings = []
    geometries = []
    for g in as_list(doc, "geometry_library"):
        if not isinstance(g, dict):
            raise Unreadable("not DSON: geometry_library holds something other than objects")
        gid = g.get("id", "?")
        verts, w = counted(g.get("vertices"), f"geometry {gid} vertices")
        warnings += [w] if w else []
        polys, w = counted(g.get("polylist"), f"geometry {gid} polylist")
        warnings += [w] if w else []
        sides = {3: 0, 4: 0}
        other = 0
        for p in polys:
            n = len(p) - 2 if isinstance(p, list) else -1
            if n in sides:
                sides[n] += 1
            else:
                other += 1
        if other:
            warnings.append(f"geometry {gid}: {other} polygons are not 3 or 4 vertex "
                            "indices after the two group indices")
        geometries.append({"id": gid, "name": g.get("name"),
                           "type": g.get("type", "polygon_mesh"),
                           "vertices": len(verts), "polygons": len(polys),
                           "quads": sides[4], "triangles": sides[3],
                           "other_polygons": other})
    figure_nodes, bones = [], []
    figure_type, node_type = None, None
    for n in as_list(doc, "node_library"):
        if not isinstance(n, dict):
            raise Unreadable("not DSON: node_library holds something other than objects")
        kind = n.get("type", "node")
        name = n.get("name") or n.get("id")
        entry = {"name": None if name is None else str(name), "id": n.get("id"),
                 "label": n.get("label")}
        presentation = n.get("presentation")
        ctype = presentation.get("type") if isinstance(presentation, dict) else None
        ctype = ctype if isinstance(ctype, str) and ctype else None
        if kind == "bone":
            parent = n.get("parent")
            entry["parent"] = (unquote(parent.split("#")[-1])
                               if isinstance(parent, str) else None)
            bones.append(entry)
        elif kind == "figure":
            figure_nodes.append(entry)
            figure_type = figure_type or ctype
        node_type = node_type or ctype
    content_type = figure_type or node_type
    return {"content_type": content_type, "role": role_of(content_type),
            "geometries": geometries, "figure_nodes": figure_nodes, "bones": bones,
            "warnings": warnings}


def role_of(content_type: str | None) -> str:
    """body, attachment, wardrobe, hair, prop, other or none, from a content type."""
    if content_type is None:
        return "none"
    return next((role for role, prefix in ROLE_PREFIXES
                 if content_type == prefix or content_type.startswith(prefix + "/")), "other")


def summarise_modifiers(doc: dict) -> list[dict]:
    out = []
    for m in as_list(doc, "modifier_library"):
        if not isinstance(m, dict):
            raise Unreadable("not DSON: modifier_library holds something other than objects")
        if "skin" in m:
            continue
        morph = m.get("morph")
        channel = m.get("channel") if isinstance(m.get("channel"), dict) else {}
        channel_type = channel.get("type") if isinstance(channel.get("type"), str) else None
        deltas, hd_url = None, None
        if isinstance(morph, dict):
            if morph.get("deltas") is None:
                deltas = 0
            else:
                values, _ = counted(morph["deltas"], f"modifier {m.get('id')!r} morph deltas")
                deltas = len(values)
            hd_url = morph.get("hd_url") if isinstance(morph.get("hd_url"), str) else None
        elif morph is not None:
            raise Unreadable(f"not DSON: modifier {m.get('id')!r} has a morph that is "
                             "not an object")
        if channel_type == "alias":
            kind = "alias"
        elif morph is not None or channel_type in DIAL_CHANNELS:
            kind = "morph"
        else:
            kind = "other"
        name = m.get("name") or m.get("id")
        target = channel.get("target_channel")
        extra = m.get("extra") if isinstance(m.get("extra"), list) else []
        out.append({"name": name if isinstance(name, str) else None,
                    "id": m.get("id") if isinstance(m.get("id"), str) else None,
                    "kind": kind, "channel_type": channel_type,
                    "target_channel": target if isinstance(target, str) else None,
                    "extra_types": [e["type"] for e in extra
                                    if isinstance(e, dict) and isinstance(e.get("type"), str)],
                    "parent": m.get("parent"), "has_morph": morph is not None,
                    "deltas": deltas, "hd_url": hd_url})
    return out


def group_of(name: str) -> str:
    return next((g for g in GROUPS if name.startswith(g)), OTHER)


def find_casefold(root: Path, parts: list[str], listings: dict | None = None) -> Path | None:
    """root/parts... on disk, matching each component without regard to case.

    Every spelling is followed, not just the first: on Linux data/DAZ 3D and
    data/Daz 3D can both exist, and the file may be under either. `listings`
    caches folder listings across calls.
    """
    listings = {} if listings is None else listings
    frontier = [root]
    for part in (p for p in parts if p not in ("", ".")):
        want, nxt = part.casefold(), []
        for cur in frontier:
            if cur not in listings:
                try:
                    listings[cur] = os.listdir(cur)
                except OSError:
                    listings[cur] = []
            nxt += [cur / n for n in listings[cur] if n.casefold() == want]
        if not nxt:
            return None
        frontier = nxt
    return next((p for p in frontier if p.exists()), None)


def content_root(path: Path, aid: str | None) -> Path | None:
    """The content directory a file sits in, from its asset_info id, or None.

    The id is the file's own path from the content root ("/data/Daz%203D/..."),
    so stripping it off the real path gives the root, if the file has not moved.
    """
    if not aid:
        return None
    parts = [p for p in unquote(aid).split("/") if p]
    if not parts or len(parts) >= len(path.parts):
        return None
    tail = path.parts[-len(parts):]
    if [p.casefold() for p in tail] != [p.casefold() for p in parts]:
        return None
    return Path(*path.parts[:-len(parts)])


def beside_figures(path: Path, by_dir: dict[str, list[dict]]) -> list[dict]:
    """The figures whose folder holds the nearest Morphs folder above `path`, ignoring case."""
    for above in path.parents:
        if above.name.casefold() == "morphs":
            hit = by_dir.get(str(above.parent).casefold())
            if hit:
                return hit
    return []


# ---------------------------------------------------------------- the walk

def inventory(top: Path) -> dict:
    started = time.monotonic()
    top = top.resolve()
    figures, morph_files, errors = [], [], []

    def note(path, kind, message):
        try:
            rel = Path(path).relative_to(top)
        except ValueError:
            rel = Path(path)
        errors.append({"file": shown(rel.as_posix()), "kind": kind, "error": message})

    # Symlinks are followed, because a library may link data/ in from another
    # disk, but never into the repo, and a folder reached twice (a second link
    # to it, or a link loop) is walked once.
    paths, seen, twice = [], set(), 0
    for dirpath, dirnames, filenames in os.walk(
            top, followlinks=True,
            onerror=lambda e: note(e.filename or top, "folder",
                                   f"cannot list directory: {e.strerror}")):
        real = os.path.realpath(dirpath)
        if repo_clash(Path(real)):      # a safety net: such links are pruned below
            note(dirpath, "link",
                 f"not walked: it resolves to {shown(real)}, in or above this repository")
            dirnames[:] = []
            continue
        if real in seen:
            twice += 1
            dirnames[:] = []
            continue
        seen.add(real)
        keep = []
        for d in sorted(dirnames):
            full = os.path.join(dirpath, d)
            target = os.path.realpath(full) if os.path.islink(full) else None
            if target is not None and repo_clash(Path(target)):
                note(full, "link", f"not walked: it resolves to {shown(target)}, "
                                   "in or above this repository")
            else:
                keep.append(d)
        dirnames[:] = keep
        for f in sorted(filenames):
            if not f.lower().endswith(".dsf"):
                continue
            path = Path(dirpath, f)
            if path.is_symlink() and repo_clash(Path(os.path.realpath(path))):
                note(path, "link", "not read: it links into this repository")
                continue
            paths.append(path)

    forms = {"gzip": 0, "text": 0, "not_dson": 0, "unreadable": 0}
    not_dson = []
    for path in paths:
        rel = shown(path.relative_to(top).as_posix())
        try:
            doc, form = read_dson(path)
            aid = asset_id(doc)
            if doc.get("geometry_library"):
                fig = summarise_figure(doc)
                fig.update({"file": rel, "form": form, "asset_id": aid,
                            "_path": path, "_morphs": []})
                figures.append(fig)
            else:
                mods = summarise_modifiers(doc)
                if mods:
                    morph_files.append({"file": rel, "path": path, "asset_id": aid,
                                        "modifiers": mods})
        except NotDson as e:
            not_dson.append({"file": rel, "form": e.form, "reason": str(e)})
            forms["not_dson"] += 1
            continue
        except Unreadable as e:
            errors.append({"file": rel, "kind": "file", "error": str(e)})
            forms["unreadable"] += 1
            continue
        forms[form] += 1
    figures.sort(key=lambda f: (ROLES.index(f["role"]), f["file"]))

    by_dir: dict[str, list[dict]] = {}
    by_id: dict[str, list[dict]] = {}
    for fig in figures:
        by_dir.setdefault(str(fig["_path"].parent).casefold(), []).append(fig)
        if uri_file(fig["asset_id"]):
            by_id.setdefault(uri_file(fig["asset_id"]), []).append(fig)

    unattached: dict[str, dict] = {}
    listings: dict[Path, list[str]] = {}
    for mf in morph_files:
        candidates = beside_figures(mf["path"], by_dir)
        root = content_root(mf["path"], mf["asset_id"])
        stem = mf["path"].stem
        for mod in mf["modifiers"]:
            name = mod["name"] or stem
            record = {"name": name, "id": mod["id"], "kind": mod["kind"], "file": mf["file"],
                      "group": group_of(name), "deltas": mod["deltas"],
                      "hd_url": mod["hd_url"], "channel_type": mod["channel_type"],
                      "target_channel": mod["target_channel"],
                      "extra_types": mod["extra_types"]}
            if mod["kind"] == "morph" and ("_div2" in name or "_div2" in stem
                                           or mod["hd_url"]):
                record["hd"] = hd_record(record, root, listings)
            target = uri_file(mod["parent"])
            owner, via = None, None
            if target is None:
                if len(candidates) == 1:
                    owner = candidates[0]
            else:
                owner = next((f for f in candidates if uri_file(f["asset_id"]) == target),
                             None)
                if owner is None and len(candidates) == 1 and not candidates[0]["asset_id"]:
                    owner = candidates[0]
            if owner is not None:
                via = "morphs_folder"
            elif target is not None and len(by_id.get(target, [])) == 1:
                owner, via = by_id[target][0], "parent_uri"
            record["via"] = via
            record["morphs_folder_of"] = ([] if via == "morphs_folder"
                                          else [f["file"] for f in candidates])
            if owner is not None:
                owner["_morphs"].append(record)
            else:
                label = (unquote(mod["parent"].split("#")[0])
                         if isinstance(mod["parent"], str) else "") or "(no parent URI)"
                slot = unattached.setdefault(label.casefold(), {"spellings": set(),
                                                                "records": []})
                slot["spellings"].add(label)
                slot["records"].append(record)

    unattached_blocks = []
    for key in sorted(unattached):
        slot = unattached[key]
        spellings = sorted(slot["spellings"])
        unattached_blocks.append(dict(target=spellings[0], also_spelled=spellings[1:],
                                      **morph_block(slot["records"])))
    roles = {r: sum(f["role"] == r for f in figures) for r in ROLES}
    content_types: dict[str, int] = {}
    for fig in figures:
        if fig["content_type"] is not None:
            content_types[fig["content_type"]] = content_types.get(fig["content_type"], 0) + 1
    return {
        "root": shown(top),
        "dsf_files": len(paths),
        "read": forms,
        "folders_reached_twice": twice,
        "walk_skips": {"folders_not_listed": sum(e["kind"] == "folder" for e in errors),
                       "links_into_repo": sum(e["kind"] == "link" for e in errors)},
        "seconds": round(time.monotonic() - started, 3),
        "geometry_roles": roles,
        "content_types": dict(sorted(content_types.items(),
                                     key=lambda kv: (ROLES.index(role_of(kv[0])), kv[0]))),
        "figures": [finish_figure(f) for f in figures],
        "unattached": unattached_blocks,
        "not_dson": not_dson,
        "errors": errors,
    }


def hd_record(record: dict, root: Path | None, listings: dict) -> dict:
    n, url = record["deltas"] or 0, record["hd_url"]
    state = ("deltas_and_hd_url" if n and url else "hd_url_only" if url
             else "deltas_only" if n else "neither")
    found = None
    if url and root is not None:
        found = find_casefold(root, unquote(url.split("#")[0]).split("/"),
                              listings) is not None
    return {"state": state, "dhdm_found": found}


def morph_block(records: list[dict]) -> dict:
    records = sorted(records, key=lambda r: (r["name"].casefold(), r["file"]))
    morphs = [r for r in records if r["kind"] == "morph"]
    aliases = [r for r in records if r["kind"] == "alias"]
    others = [r for r in records if r["kind"] == "other"]
    groups = {g: [] for g in (*GROUPS, OTHER)}
    for r in morphs:
        groups[r["group"]].append(r["name"])
    alias_groups = {g: [] for g in (*GROUPS, OTHER)}
    for r in aliases:
        alias_groups[r["group"]].append(r["id"] or r["name"])
    hd = [{"name": r["name"], "file": r["file"], "deltas": r["deltas"],
           "hd_url": r["hd_url"], **r["hd"]} for r in morphs if "hd" in r]

    def pick(rs, *keys):
        return [{k: r[k] for k in (*keys, "via", "morphs_folder_of")} for r in rs]

    return {"morph_count": len(morphs),
            "morph_files": len({r["file"] for r in morphs}),
            "morph_groups": groups,
            "morphs": pick(morphs, "name", "file", "group", "deltas", "hd_url"),
            "hd_morphs": hd,
            "alias_count": len(aliases),
            "alias_groups": alias_groups,
            "aliases": pick(aliases, "name", "id", "file", "group", "target_channel"),
            "other_modifier_count": len(others),
            "other_modifiers": pick(others, "name", "id", "file", "channel_type",
                                    "extra_types")}


def finish_figure(fig: dict) -> dict:
    out = {k: fig[k] for k in ("file", "form", "asset_id", "content_type", "role",
                               "figure_nodes", "geometries")}
    out["bone_count"] = len(fig["bones"])
    out["bones"] = fig["bones"]
    out.update(morph_block(fig["_morphs"]))
    out["warnings"] = fig["warnings"]
    return out


# ---------------------------------------------------------------- text report

def columns(names: list[str], indent: int, width: int = 100) -> list[str]:
    if not names:
        return []
    w = min(max(len(n) for n in names) + 2, width - indent)
    per = max(1, (width - indent) // w)
    return [" " * indent + "".join(f"{n:<{w}}" for n in names[i:i + per]).rstrip()
            for i in range(0, len(names), per)]


def morph_lines(block: dict, brief: bool) -> list[str]:
    if not block["morph_count"]:
        lines = ["  morphs: none"]
    else:
        lines = [f"  morphs: {block['morph_count']} in {block['morph_files']} files"]
        lines += morph_detail(block, brief)
    if block["alias_count"]:
        lines.append(f"  aliases, not counted as morphs: {block['alias_count']} "
                     "(channel type alias, a second name for another modifier's channel)")
        tally = [f"{g} {len(ids)}" for g, ids in block["alias_groups"].items() if ids]
        lines.append(f"    by the name they carry: {', '.join(tally)}")
        if not brief:
            lines += columns([i for ids in block["alias_groups"].values() for i in ids], 6)
    if block["other_modifier_count"]:
        kinds: dict[str, int] = {}
        for m in block["other_modifiers"]:
            what = (f"channel type {m['channel_type']}" if m["channel_type"]
                    else "no channel")
            kinds[what] = kinds.get(what, 0) + 1
        lines.append(f"  other modifiers, not counted as morphs: {block['other_modifier_count']} "
                     f"(no morph block and no float or int channel: "
                     f"{', '.join(f'{c} {w}' for w, c in sorted(kinds.items()))})")
        if not brief:
            lines += columns([m["name"] for m in block["other_modifiers"]], 6)
    return lines


def morph_detail(block: dict, brief: bool) -> list[str]:
    lines = []
    by_uri = sum(1 for m in block["morphs"] if m["via"] == "parent_uri")
    if by_uri:
        lines.append("    attached by parent URI, from outside this figure's Morphs folder: "
                     f"{by_uri}")
    elsewhere = [m for m in block["morphs"] if m["morphs_folder_of"]]
    if elsewhere:
        folders = sorted({f for m in elsewhere for f in m["morphs_folder_of"]})
        lines.append(f"    in a Morphs folder beside {', '.join(folders)}, with a parent URI "
                     f"naming a different figure: {len(elsewhere)}")
    with_deltas = {}
    for m in block["morphs"]:
        with_deltas[m["group"]] = with_deltas.get(m["group"], 0) + bool(m["deltas"])
    for g, names in block["morph_groups"].items():
        lines.append(f"    {g:<12} {len(names):>5}  ({with_deltas.get(g, 0)} with deltas)")
        if not brief:
            lines += columns(names, 6)
    hd = block["hd_morphs"]
    if hd:
        lines.append(f"  HD morphs (_div2 or an hd_url): {len(hd)}")
        if brief:
            tally = {}
            for h in hd:
                tally[h["state"]] = tally.get(h["state"], 0) + 1
            lines += [f"    {HD_BRIEF[s]}: {c}" for s, c in tally.items()]
        else:
            w = max(len(h["name"]) for h in hd) + 2
            for h in hd:
                disk = {True: "; .dhdm on disk", False: "; .dhdm not found",
                        None: "; .dhdm not checked, as the .dsf is not at the path "
                              "its asset id gives"}[h["dhdm_found"]] if h["hd_url"] else ""
                lines.append(f"    {h['name']:<{w}}{HD_STATES[h['state']].format(n=h['deltas'])}"
                             f"{disk}")
    return lines


def report(inv: dict, brief: bool) -> str:
    read, skips, roles = inv["read"], inv["walk_skips"], inv["geometry_roles"]
    out = [f"Daz inventory of {inv['root']}",
           f"{inv['dsf_files']} .dsf files: {read['gzip']} gzip, {read['text']} plain, "
           f"{read['not_dson']} not DSON (skipped), {read['unreadable']} unreadable; "
           f"{inv['seconds']:.2f} s"]
    if inv["folders_reached_twice"]:
        out[-1] += (f"; {plural(inv['folders_reached_twice'], 'folder')} reached again "
                    "through links walked once")
    if skips["folders_not_listed"]:
        out[-1] += f"; {plural(skips['folders_not_listed'], 'folder')} could not be listed"
    if skips["links_into_repo"]:
        out[-1] += f"; {plural(skips['links_into_repo'], 'link')} into the repo skipped"
    main = sum(roles[r] for r in FIGURE_ROLES)
    rest = [f"{roles[r]} {'with no content type' if r == 'none' else r}"
            for r in ROLES if r not in FIGURE_ROLES and roles[r]]
    out.append(f"{plural(len(inv['figures']), 'figure file')}, by content type: "
               f"{main} body or attachment ({roles['body']} body, "
               f"{roles['attachment']} attachment); "
               f"{len(inv['figures']) - main} other geometry"
               + (f" ({', '.join(rest)})" if rest else ""))
    if inv["content_types"]:
        w = max(len(t) for t in inv["content_types"]) + 2
        out.append("content types:")
        out += [f"  {t:<{w}}{n:>5}  {role_of(t)}" for t, n in inv["content_types"].items()]
    section = None
    for fig in inv["figures"]:
        now = "main" if fig["role"] in FIGURE_ROLES else "rest"
        if now != section:
            section = now
            out += ["", "BODY AND ATTACHMENT FIGURES (content type Actor or Follower/Attachment)"
                    if now == "main" else
                    "OTHER GEOMETRY (wardrobe, hair, prop, any other content type or none)"]
        nodes = ", ".join(n["name"] or "?" for n in fig["figure_nodes"]) or "none"
        out += ["", f"FIGURE {fig['file']}  ({fig['form']})",
                f"  asset id {fig['asset_id']}",
                f"  content type {fig['content_type'] or 'none'} ({fig['role']})",
                f"  figure node {nodes}"]
        for g in fig["geometries"]:
            split = f"{g['quads']} quads, {g['triangles']} triangles"
            if g["other_polygons"]:
                split += f", {g['other_polygons']} other"
            out.append(f"  geometry {g['id']} ({g['type']}): {g['vertices']} vertices, "
                       f"{g['polygons']} polygons ({split})")
        out.append(f"  bones: {fig['bone_count']}")
        if not brief:
            out += columns([b["name"] or "?" for b in fig["bones"]], 4)
        if fig["morph_count"] or fig["alias_count"] or fig["other_modifier_count"]:
            out += morph_lines(fig, brief)
        else:
            out.append("  morphs: none (no readable morph beside the figure file names it, "
                       "and none elsewhere does)")
        out += [f"  warning: {w}" for w in fig["warnings"]]
    if inv["unattached"]:
        out += ["", "MORPH FILES UNDER NO FIGURE IN THIS WALK, "
                "by the figure their parent URI names"]
        for block in inv["unattached"]:
            out += ["", f"TARGET {block['target']}"]
            if block["also_spelled"]:
                out.append(f"  also spelled {', '.join(block['also_spelled'])}")
            out += morph_lines(block, brief)
    if inv["not_dson"]:
        out += ["", "NOT DSON, SKIPPED: valid JSON, but not an object with a "
                f"{DSON_KEYS} key; not an error"]
        out += [f"  {n['file']}  ({n['form']}): {n['reason']}" for n in inv["not_dson"]]
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

def _asset(rel: str, kind: str) -> dict:
    return {"file_version": "0.6.0.0",
            "asset_info": {"id": "/" + quote(rel), "type": kind,
                           "contributor": {"author": "daz_inventory selftest"},
                           "revision": "1.0"}}


def _figure(rel, geom, fig, vertices, polygons, bones, content_type=None, decoy=None):
    """A figure file. `content_type` goes on the figure node; `decoy`, on a plain node
    listed before it, which must not win."""
    doc = _asset(rel, "figure")
    doc["geometry_library"] = [{
        "id": geom, "name": geom, "type": "polygon_mesh",
        "vertices": {"count": len(vertices), "values": vertices},
        "polygon_groups": {"count": 1, "values": ["Body"]},
        "polygon_material_groups": {"count": 1, "values": ["Skin"]},
        "polylist": {"count": len(polygons), "values": [[0, 0, *p] for p in polygons]}}]
    nodes = [{"id": fig, "name": fig, "type": "figure", "label": fig}]
    if content_type:
        nodes[0]["presentation"] = {"type": content_type, "label": fig}
    parent = fig
    for bone_id, bone_name in bones:
        nodes.append({"id": bone_id, "name": bone_name, "type": "bone",
                      "label": bone_name.title(), "parent": "#" + parent})
        parent = bone_id
    prop = {"id": "prop_node", "name": "prop_node", "type": "node", "label": "Prop"}
    if decoy:
        prop["presentation"] = {"type": decoy}
        nodes.insert(0, prop)
    else:
        nodes.append(prop)
    doc["node_library"] = nodes
    doc["modifier_library"] = [{"id": "SkinBinding", "name": "SkinBinding",
                                "parent": "#" + geom,
                                "skin": {"node": "#" + fig, "geometry": "#" + geom,
                                         "vertex_count": len(vertices), "joints": []}}]
    return doc


def _modifier(rel, name, parent, deltas=None, hd_url=None, deltas_key=True,
              channel_type="float", extra_type=None):
    doc = _asset(rel, "modifier")
    mod = {"id": name, "name": name, "parent": parent, "group": "/Selftest"}
    if channel_type:
        mod["channel"] = {"id": "value", "type": channel_type, "name": "Value",
                          "value": 0.0, "min": 0.0, "max": 1.0}
    if extra_type:
        mod["extra"] = [{"type": extra_type}]
    if deltas is not None or hd_url:
        morph = {"vertex_count": 8}
        if deltas_key:
            morph["deltas"] = {"count": len(deltas or []), "values": deltas or []}
        if hd_url:
            morph["hd_url"] = hd_url
        mod["morph"] = morph
    doc["modifier_library"] = [mod]
    doc["scene"] = {"modifiers": [{"id": name + "-1", "url": "#" + name}]}
    return doc


def _alias(rel, alias_id, name, parent, target):
    """An alias modifier: its own id, the name of the modifier it points at, no morph."""
    doc = _asset(rel, "modifier")
    doc["modifier_library"] = [{
        "id": alias_id, "name": name, "parent": parent, "group": "/Selftest",
        "channel": {"id": alias_id, "type": "alias", "name": name, "label": name,
                    "target_channel": target}}]
    doc["scene"] = {"modifiers": [{"id": alias_id + "-1", "url": "#" + alias_id}]}
    return doc


def build_sample(root: Path) -> None:
    """Write the synthetic library. Every name in it is invented for the test."""
    def put(rel, payload, gz=False):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        data = payload if isinstance(payload, bytes) else json.dumps(payload, indent=1).encode()
        p.write_bytes(gzip.compress(data) if gz else data)

    v = "data/Selftest Vendor"
    one, two, pair = f"{v}/Figure One", f"{v}/Figure Two", f"{v}/Pair"
    cube = [[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)]
    put(f"{one}/FigureOne.dsf", _figure(
        f"{one}/FigureOne.dsf", "FigureOneGeom", "FigureOne", cube,
        [[0, 1, 3, 2], [4, 5, 7, 6], [0, 1, 5, 4], [2, 3, 7, 6], [0, 2, 6, 4],
         [1, 3, 7], [1, 7, 5]],
        [("hip_t", "hip_t"), ("spine_id", "spine_t"), ("head_t", "head_t")],
        content_type="Actor"), gz=True)
    parent_one = "/" + quote(f"{one}/FigureOne.dsf") + "#FigureOneGeom"
    a, b = f"{one}/Morphs/Selftest Vendor/Set A", f"{one}/Morphs/Selftest Vendor/Set B"
    d = [[0, 0.1, 0.0, 0.0], [3, 0.0, 0.2, 0.0], [5, 0.0, 0.0, 0.3], [7, 0.1, 0.1, 0.1]]
    for rel, name, kw, gz in (
            (a, "eCTRLvTest", {}, False),
            (a, "facs_ctrl_vTest", {}, True),
            (a, "facs_bs_TestOpen", {"deltas": d[:3]}, True),
            (a, "facs_bs_TestWide_div2", {"deltas": d[:2], "hd_url": "/" + quote(
                "data/SELFTEST VENDOR/figure one/Morphs/Selftest Vendor/Set A/"
                "facs_bs_TestWide_div2.dhdm")}, False),
            (a, "facs_cbs_TestFix_div2", {"hd_url": "/" + quote(
                f"{a}/facs_cbs_TestFix_div2.dhdm"), "deltas_key": False}, True),
            (a, "facs_jnt_TestTurn", {}, False),
            (b, "pJCMTestBend_90_L", {"deltas": d}, True),
            (b, "body_cbs_TestBulge", {"deltas": d[:1]}, False),
            (b, "TestOther", {"deltas": []}, False)):
        put(f"{rel}/{name}.dsf", _modifier(f"{rel}/{name}.dsf", name, parent_one, **kw), gz)
    put(f"{a}/facs_bs_TestWide_div2.dhdm", b"invented bytes, not a real dhdm")
    # Aliases carry the name of the modifier they point at, so they must not be counted
    # as morphs (the visemes would count twice), and an alias to a _div2 is no HD morph.
    c = f"{one}/Morphs/Selftest Vendor/Set C"
    put(f"{c}/facs_ctrl_vTestB.dsf", _modifier(f"{c}/facs_ctrl_vTestB.dsf", "facs_ctrl_vTestB",
                                               parent_one))
    for alias_id, name, gz in (("alias_selftest_facs_ctrl_vTest", "facs_ctrl_vTest", False),
                               ("alias_selftest_facs_ctrl_vTestB", "facs_ctrl_vTestB", True),
                               ("alias_selftest_facs_bs_TestWide_div2", "facs_bs_TestWide_div2",
                                False)):
        put(f"{c}/{alias_id}.dsf", _alias(f"{c}/{alias_id}.dsf", alias_id, name, parent_one,
                                          parent_one.split("#")[0] + f"#{name}?value"), gz)
    # Neither morphs nor aliases: a channel of type file, and a modifier held only in extra.
    put(f"{c}/SelftestLauncher.dsf", _modifier(f"{c}/SelftestLauncher.dsf", "SelftestLauncher",
                                               parent_one, channel_type="file"))
    put(f"{c}/SelftestPush.dsf", _modifier(f"{c}/SelftestPush.dsf", "SelftestPush", parent_one,
                                           channel_type=None,
                                           extra_type="selftest/modifier/push"))
    # Valid JSON that is not DSON: skipped and listed, never an error.
    groups = f"{v}/Tools/Face Groups"
    put(f"{groups}/Selftest Groups.dsf", {"selftest_group_list": [{"id": "g1", "faces": [0]}]})
    put(f"{groups}/Selftest Many Keys.dsf", {f"key{i}": i for i in range(1, 8)}, gz=True)
    put(f"{one}/UV Sets/Selftest/Base.dsf",
        dict(_asset(f"{one}/UV Sets/Selftest/Base.dsf", "uv_set"),
             uv_set_library=[{"id": "Base", "vertex_count": 8,
                              "uvs": {"count": 0, "values": []}}]))
    put(f"{one}/Readme.duf", b"not walked: only .dsf files are read")

    broken = f"{one}/Morphs/Broken"
    put(f"{broken}/bad_gzip.dsf", b"\x1f\x8bgarbage after the gzip magic")
    put(f"{broken}/truncated_gzip.dsf",
        gzip.compress(json.dumps(_asset(broken, "modifier")).encode())[:30])
    put(f"{broken}/bad_json.dsf", b'{"file_version": "0.6.0.0", ')
    put(f"{broken}/gzip_bad_json.dsf", b'{"asset_info": ]', gz=True)
    put(f"{broken}/empty.dsf", b"")
    put(f"{broken}/top_list.dsf", b"[]")                # valid JSON, not DSON: not an error
    put(f"{broken}/empty_object.dsf", b"{}")            # the same
    put(f"{broken}/zlib_stream.dsf", b"\x78\x9c\x03\x00\x00\x00\x00\x01")
    put(f"{broken}/not_utf8.dsf", b'{"file_version": "\xff"}')
    rel = f"{broken}/deltas_not_counted.dsf"
    doc = _modifier(rel, "facs_bs_TestBare_div2", parent_one, deltas=d[:1])
    doc["modifier_library"][0]["morph"]["deltas"] = d[:1]
    put(rel, doc)
    put(f"{v}/Bad Figure/BadFigure.dsf",
        dict(_asset(f"{v}/Bad Figure/BadFigure.dsf", "figure"),
             geometry_library=[{"id": "NoVertices"}]))

    put(f"{two}/FigureTwo.dsf", _figure(
        f"{two}/FigureTwo.dsf", "FigureTwoGeom", "FigureTwo", cube[:4], [[0, 1, 3, 2]],
        [("root_t", "root_t"), ("tail_t", "tail_t")],
        content_type="Follower/Attachment/Head/Face/Selftest", decoy="Prop/Selftest Decoy"))
    parent_two = "/" + quote(f"{two}/FigureTwo.dsf") + "#FigureTwoGeom"
    missing = "/" + quote(f"{v}/Missing/Missing.dsf") + "#MissingGeom"
    for rel, name, parent, gz in (
            # beside the figure file
            (f"{two}/Morphs/Selftest Vendor", "facs_bs_TestTwo", parent_two, False),
            # the same Morphs folder in another capitalisation
            ("data/SELFTEST VENDOR/Figure Two/Morphs/Selftest Vendor", "facs_bs_TestCase",
             parent_two, True),
            # in no Morphs folder; the parent URI, in lower case, names Figure Two
            (f"{v}/Extras", "facs_jnt_TestElsewhere", parent_two.lower(), False),
            # beside Figure Two, but naming Figure One, then a figure not in the walk
            (f"{two}/Morphs/Selftest Vendor", "TestMisplaced", parent_one, False),
            (f"{two}/Morphs/Selftest Vendor", "facs_bs_TestStray",
             missing.replace("Selftest%20Vendor", "SELFTEST%20VENDOR"), False)):
        put(f"{rel}/{name}.dsf", _modifier(f"{rel}/{name}.dsf", name, parent, deltas=d[:2]),
            gz)

    for letter, gz, ctype in (("A", False, "Follower/Wardrobe/Selftest"), ("B", True, None)):
        put(f"{pair}/Pair{letter}.dsf", _figure(
            f"{pair}/Pair{letter}.dsf", f"Pair{letter}Geom", f"Pair{letter}", cube[:3],
            [[0, 1, 2]], [(f"pair_{letter.lower()}_root", f"pair_{letter.lower()}_root")],
            content_type=ctype), gz)
    # One geometry file per remaining role: hair, prop (a plain node, no figure node), other.
    for folder, ctype in (("Hair", "Follower/Hair"), ("Prop", None), ("Graft", "Follower")):
        rel = f"{v}/{folder}/Selftest{folder}.dsf"
        doc = _figure(rel, f"{folder}Geom", f"Selftest{folder}", cube[:3], [[0, 1, 2]],
                      [(f"{folder.lower()}_root", f"{folder.lower()}_root")], content_type=ctype)
        if folder == "Prop":
            doc["node_library"] = [{"id": "SelftestProp", "name": "SelftestProp", "type": "node",
                                    "presentation": {"type": "Prop/Selftest"}}]
        put(rel, doc)
    for name, target, fragment in (("facs_bs_PairA", "PairA.dsf", "PairAGeom"),
                                   ("eCTRLvPairB", "PairB.dsf", "PairB"),
                                   ("TestNobody", "Nobody.dsf", "NobodyGeom")):
        rel = f"{pair}/Morphs/{name}.dsf"
        put(rel, _modifier(rel, name, "/" + quote(f"{pair}/{target}") + "#" + fragment,
                           deltas=d[:1]))
    rel = f"{v}/Loose/Morphs/facs_bs_Loose_div2.dsf"
    put(rel, _modifier(rel, "facs_bs_Loose_div2", missing,
                       deltas=[], hd_url="/" + quote(f"{v}/Loose/Morphs/gone.dhdm")))
    rel = f"{v}/Loose/Morphs/alias_selftest_facs_bs_Loose_div2.dsf"
    put(rel, _alias(rel, "alias_selftest_facs_bs_Loose_div2", "facs_bs_Loose_div2", missing,
                    missing.split("#")[0] + "#facs_bs_Loose_div2?value"))


def selftest() -> int:
    failures = []

    def check(label, got, want):
        ok = got == want
        print(f"  {'ok  ' if ok else 'FAIL'} {label}"
              + ("" if ok else f": got {got!r}, want {want!r}"))
        if not ok:
            failures.append(label)

    def run(*argv):
        return subprocess.run([sys.executable, str(Path(__file__).resolve()), *map(str, argv)],
                              capture_output=True, text=True, timeout=120)

    with tempfile.TemporaryDirectory(prefix="daz_inventory_selftest_") as tmp:
        root, edge = Path(tmp, "library"), Path(tmp, "edge")
        print(f"self-test in {tmp}")
        check("temp dir is outside the repo", repo_clash(Path(tmp)), None)
        build_sample(root)
        inv = inventory(root)
        v = "data/Selftest Vendor"
        figs = {f["file"]: f for f in inv["figures"]}

        check(".dsf files walked", inv["dsf_files"], 46)
        check("read as gzip / plain / not DSON / unreadable", inv["read"],
              {"gzip": 8, "text": 25, "not_dson": 4, "unreadable": 9})
        check("unreadable files", sorted(e["file"].rsplit("/", 1)[-1] for e in inv["errors"]),
              sorted(["bad_gzip.dsf", "truncated_gzip.dsf", "bad_json.dsf",
                      "gzip_bad_json.dsf", "empty.dsf",
                      "zlib_stream.dsf", "not_utf8.dsf", "deltas_not_counted.dsf",
                      "BadFigure.dsf"]))
        messages = {e["file"].rsplit("/", 1)[-1]: e["error"] for e in inv["errors"]}
        for fname, start in (("bad_gzip.dsf", "gzip error: BadGzipFile"),
                             ("truncated_gzip.dsf", "gzip error: EOFError"),
                             ("bad_json.dsf", "JSON error: "),
                             ("gzip_bad_json.dsf", "JSON error inside the gzip: "),
                             ("empty.dsf", "empty file"),
                             ("zlib_stream.dsf", "starts like a raw zlib stream"),
                             ("not_utf8.dsf", "not utf-8 text"),
                             ("deltas_not_counted.dsf", "not DSON: modifier "
                              "'facs_bs_TestBare_div2' morph deltas is not a counted array"),
                             ("BadFigure.dsf", "not DSON: geometry NoVertices vertices")):
            check(f"message for {fname} starts {start!r}",
                  messages.get(fname, "").startswith(start), True)
        check("valid JSON that is not DSON: skipped with its form and reason, not an error",
              [(n["file"].rsplit("/", 1)[-1], n["form"], n["reason"]) for n in inv["not_dson"]],
              [("empty_object.dsf", "text", "not DSON: an empty JSON object"),
               ("top_list.dsf", "text", "not DSON: the top level is a JSON list, not an object"),
               ("Selftest Groups.dsf", "text", "not DSON: no file_version, asset_info, scene "
                "or *_library key; top-level keys selftest_group_list"),
               ("Selftest Many Keys.dsf", "gzip", "not DSON: no file_version, asset_info, "
                "scene or *_library key; top-level keys key1, key2, key3, key4, key5 "
                "and 2 more")])
        check("figure files, body and attachment first, then by file", list(figs), [
            f"{v}/Figure One/FigureOne.dsf", f"{v}/Figure Two/FigureTwo.dsf",
            f"{v}/Pair/PairA.dsf", f"{v}/Hair/SelftestHair.dsf", f"{v}/Prop/SelftestProp.dsf",
            f"{v}/Graft/SelftestGraft.dsf", f"{v}/Pair/PairB.dsf"])
        check("figure roles, from the figure node's content type before any other node's",
              [(f["role"], f["content_type"]) for f in inv["figures"]],
              [("body", "Actor"), ("attachment", "Follower/Attachment/Head/Face/Selftest"),
               ("wardrobe", "Follower/Wardrobe/Selftest"), ("hair", "Follower/Hair"),
               ("prop", "Prop/Selftest"), ("other", "Follower"), ("none", None)])
        check("geometry roles and content types tallied", (inv["geometry_roles"],
                                                           list(inv["content_types"].items())),
              ({"body": 1, "attachment": 1, "wardrobe": 1, "hair": 1, "prop": 1, "other": 1,
                "none": 1},
               [("Actor", 1), ("Follower/Attachment/Head/Face/Selftest", 1),
                ("Follower/Wardrobe/Selftest", 1), ("Follower/Hair", 1), ("Prop/Selftest", 1),
                ("Follower", 1)]))
        check("a content type matches a role only whole or before a slash",
              [role_of(t) for t in ("Actor/Character", "Actors", "Follower/AttachmentX",
                                    "Follower/Attachment/Lower-Body", "Follower/Hair",
                                    "Props/Selftest", "Prop", "Set", None)],
              ["body", "other", "other", "attachment", "hair", "other", "prop", "other",
               "none"])

        one = figs.get(f"{v}/Figure One/FigureOne.dsf", {})
        g = (one.get("geometries") or [{}])[0]
        check("figure one vertices", g.get("vertices"), 8)
        check("figure one polygons, quads, triangles",
              (g.get("polygons"), g.get("quads"), g.get("triangles")), (7, 5, 2))
        check("figure one form", one.get("form"), "gzip")
        check("figure one bones by name, not id",
              [b["name"] for b in one.get("bones", [])], ["hip_t", "spine_t", "head_t"])
        check("figure one bone parents",
              [b["parent"] for b in one.get("bones", [])], ["FigureOne", "hip_t", "spine_id"])
        check("figure one morph count, without aliases or other modifiers",
              one.get("morph_count"), 11)
        check("figure one groups: 2 visemes, not 4 with their aliases",
              {k: len(n) for k, n in one.get("morph_groups", {}).items()},
              {"eCTRLv": 1, "facs_ctrl_v": 2, "facs_bs_": 2, "facs_cbs_": 1,
               "facs_jnt_": 1, "pJCM": 1, "body_cbs_": 1, "other": 2})
        check("figure one aliases, grouped by the name they carry",
              (one.get("alias_count"),
               {k: ids for k, ids in one.get("alias_groups", {}).items() if ids}),
              (3, {"facs_ctrl_v": ["alias_selftest_facs_ctrl_vTest",
                                   "alias_selftest_facs_ctrl_vTestB"],
                   "facs_bs_": ["alias_selftest_facs_bs_TestWide_div2"]}))
        check("figure one alias names, targets and files",
              [(a["name"], a["target_channel"].rsplit("#", 1)[-1], a["file"].rsplit("/", 1)[-1])
               for a in one.get("aliases", [])],
              [("facs_bs_TestWide_div2", "facs_bs_TestWide_div2?value",
                "alias_selftest_facs_bs_TestWide_div2.dsf"),
               ("facs_ctrl_vTest", "facs_ctrl_vTest?value", "alias_selftest_facs_ctrl_vTest.dsf"),
               ("facs_ctrl_vTestB", "facs_ctrl_vTestB?value",
                "alias_selftest_facs_ctrl_vTestB.dsf")])
        check("figure one other modifiers: a file channel and an extra-only modifier",
              [(m["name"], m["channel_type"], m["extra_types"])
               for m in one.get("other_modifiers", [])],
              [("SelftestLauncher", "file", []),
               ("SelftestPush", None, ["selftest/modifier/push"])])
        check("figure one morphs with deltas",
              sorted(m["name"] for m in one.get("morphs", []) if m["deltas"]),
              ["TestMisplaced", "body_cbs_TestBulge", "facs_bs_TestOpen",
               "facs_bs_TestWide_div2", "pJCMTestBend_90_L"])
        check("figure one: a morph beside another figure goes to the figure it names",
              [(m["name"], m["via"], m["morphs_folder_of"]) for m in one.get("morphs", [])
               if m["via"] != "morphs_folder"],
              [("TestMisplaced", "parent_uri", [f"{v}/Figure Two/FigureTwo.dsf"])])
        hd = {h["name"]: (h["state"], h["deltas"], h["dhdm_found"])
              for h in one.get("hd_morphs", [])}
        check("figure one HD morphs, and no alias among them", hd, {
            "facs_bs_TestWide_div2": ("deltas_and_hd_url", 2, True),
            "facs_cbs_TestFix_div2": ("hd_url_only", 0, False)})
        check("figure one: no count warnings", one.get("warnings"), [])

        two = figs.get(f"{v}/Figure Two/FigureTwo.dsf", {})
        g = (two.get("geometries") or [{}])[0]
        check("figure two vertices, quads, bones",
              (g.get("vertices"), g.get("quads"), two.get("bone_count")), (4, 1, 2))
        check("figure two morphs and how each was attached",
              [(m["name"], m["via"]) for m in two.get("morphs", [])],
              [("facs_bs_TestCase", "morphs_folder"), ("facs_bs_TestTwo", "morphs_folder"),
               ("facs_jnt_TestElsewhere", "parent_uri")])
        for letter, name in (("A", "facs_bs_PairA"), ("B", "eCTRLvPairB")):
            pf = figs.get(f"{v}/Pair/Pair{letter}.dsf", {})
            check(f"shared folder: Pair{letter} gets only its own morph",
                  [m["name"] for m in pf.get("morphs", [])], [name])
        un = {u["target"]: [m["name"] for m in u["morphs"]] for u in inv["unattached"]}
        check("unattached morphs by target, one block per target whatever its case", un, {
            "/data/SELFTEST VENDOR/Missing/Missing.dsf": ["facs_bs_Loose_div2",
                                                         "facs_bs_TestStray"],
            f"/{v}/Pair/Nobody.dsf": ["TestNobody"]})
        check("unattached: the other spelling is kept",
              [u["also_spelled"] for u in inv["unattached"]],
              [[f"/{v}/Missing/Missing.dsf"], []])
        loose = [h for u in inv["unattached"] for h in u["hd_morphs"]]
        check("unattached _div2 with an empty delta array, and not its alias",
              [(h["state"], h["deltas"], h["dhdm_found"]) for h in loose],
              [("hd_url_only", 0, False)])
        check("unattached aliases are listed apart from the morphs",
              [(u["morph_count"], [a["id"] for a in u["aliases"]]) for u in inv["unattached"]],
              [(2, ["alias_selftest_facs_bs_Loose_div2"]), (1, [])])

        r = run(root)
        check("command line: exit 1 when files are unreadable", r.returncode, 1)
        check("command line: one stderr line per unreadable file, none for not DSON",
              sorted(line.split(":")[0].rsplit("/", 1)[-1] for line in r.stderr.splitlines()
                     if line.startswith("skipped ")),
              sorted(e["file"].rsplit("/", 1)[-1] for e in inv["errors"]))
        check("command line: no traceback", "Traceback" in r.stdout + r.stderr, False)
        check("command line: report names the HD state",
              "holds 2 base deltas and an hd_url; .dhdm on disk" in r.stdout, True)
        check("command line: summary lines", (
            "\n46 .dsf files: 8 gzip, 25 plain, 4 not DSON (skipped), 9 unreadable; "
            in r.stdout,
            "\n7 figure files, by content type: 2 body or attachment (1 body, 1 attachment); "
            "5 other geometry (1 wardrobe, 1 hair, 1 prop, 1 other, 1 with no content type)\n"
            in r.stdout), (True, True))
        at = [r.stdout.find(s) for s in (
            "\nBODY AND ATTACHMENT FIGURES", f"\nFIGURE {v}/Figure Two/FigureTwo.dsf",
            "\nOTHER GEOMETRY", f"\nFIGURE {v}/Pair/PairA.dsf", "\nNOT DSON, SKIPPED")]
        check("command line: body and attachment section, then other geometry, then not DSON",
              (-1 not in at, at == sorted(at)), (True, True))
        check("command line: aliases and other modifiers have their own lines", (
            "    facs_ctrl_v      2  (0 with deltas)" in r.stdout,
            "  aliases, not counted as morphs: 3 " in r.stdout,
            "    by the name they carry: facs_ctrl_v 2, facs_bs_ 1\n" in r.stdout,
            "  other modifiers, not counted as morphs: 2 (no morph block and no float or int "
            "channel: 1 channel type file, 1 no channel)" in r.stdout), (True, True, True, True))
        r = run(root, "--json")
        try:
            parsed = json.loads(r.stdout)
        except ValueError:
            parsed = {}
        check("command line: --json is one JSON object with 7 figures and 4 not DSON",
              (len(parsed.get("figures", [])), len(parsed.get("not_dson", []))), (7, 4))
        check("command line: --brief omits bone names",
              "spine_t" in run(root, "--brief").stdout, False)
        for label, target in (("the repo itself", ROOT), ("a folder inside the repo",
                                                          ROOT / "output"),
                              ("a parent of the repo", ROOT.parent)):
            r = run(target)
            check(f"refuses {label}", (r.returncode, r.stderr.startswith("refusing ")),
                  (2, True))
        for label, target, start in (
                ("a non-empty folder", root, f"{root} already exists and is not empty"),
                ("a file", root / v / "Figure Two/FigureTwo.dsf", "not a directory: "),
                ("a path under a file", root / v / "Figure Two/FigureTwo.dsf/sample",
                 "cannot write the sample to ")):
            r = run("--sample", target)
            check(f"--sample refuses {label}", (r.returncode, r.stderr.startswith(start),
                                                "Traceback" in r.stderr), (2, True, False))

        # Links and a folder that cannot be listed: all counted apart from the .dsf files.
        (root / "link_into_repo").symlink_to(ROOT / "scripts", target_is_directory=True)
        (root / "link_file_into_repo.dsf").symlink_to(ROOT / "scripts" / "daz_inventory.py")
        (root / "link_loop").symlink_to(root, target_is_directory=True)
        locked = root / "locked"
        locked.mkdir()
        can_lock = os.geteuid() != 0 if hasattr(os, "geteuid") else False
        if can_lock:
            locked.chmod(0)
        try:
            inv = inventory(root)
            r = run(root, "--brief")
        finally:
            locked.chmod(0o755)
        tail = "; 1 folder could not be listed" if can_lock else ""
        check("command line: the summary counts links and folders apart from the .dsf files",
              "46 .dsf files: 8 gzip, 25 plain, 4 not DSON (skipped), 9 unreadable; " in r.stdout
              and f"through links walked once{tail}; 2 links into the repo skipped" in r.stdout,
              True)
        kinds = {e["file"]: (e["kind"], e["error"].split(":")[0]) for e in inv["errors"]
                 if e["kind"] != "file"}
        want = {"link_into_repo": ("link", "not walked"),
                "link_file_into_repo.dsf": ("link", "not read")}
        if can_lock:
            want["locked"] = ("folder", "cannot list directory")
        else:
            print("  skip the unlistable folder: running as root, which can list it anyway")
        check("links into the repo and an unlistable folder are reported by kind", kinds, want)
        check("a link loop is walked once and adds no files",
              (inv["dsf_files"], inv["folders_reached_twice"]), (46, 1))
        check("gzip + plain + not DSON + unreadable adds up to the .dsf files",
              sum(inv["read"].values()), inv["dsf_files"])
        check("walk skips are counted apart", inv["walk_skips"],
              {"folders_not_listed": 1 if can_lock else 0, "links_into_repo": 2})

        # A clean library holding a file that is valid JSON but not DSON exits 0.
        clean = Path(tmp, "clean")
        build = f"{v}/Clean"
        cube = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        for rel, doc in (
                (f"{build}/CleanFigure.dsf", _figure(
                    f"{build}/CleanFigure.dsf", "CleanGeom", "CleanFigure", cube, [[0, 1, 2]],
                    [("clean_root", "clean_root")], content_type="Actor")),
                (f"{build}/Morphs/facs_ctrl_vClean.dsf", _modifier(
                    f"{build}/Morphs/facs_ctrl_vClean.dsf", "facs_ctrl_vClean",
                    "#CleanGeom")),
                (f"{build}/Morphs/alias_selftest_facs_ctrl_vClean.dsf", _alias(
                    f"{build}/Morphs/alias_selftest_facs_ctrl_vClean.dsf",
                    "alias_selftest_facs_ctrl_vClean", "facs_ctrl_vClean", "#CleanGeom",
                    "#facs_ctrl_vClean?value")),
                (f"{build}/Tools/Face Groups/Clean Groups.dsf",
                 {"selftest_group_list": []})):
            (clean / rel).parent.mkdir(parents=True, exist_ok=True)
            (clean / rel).write_text(json.dumps(doc))
        r = run(clean, "--brief")
        check("clean library with a not-DSON file: exit 0, nothing on stderr",
              (r.returncode, r.stderr), (0, ""))
        check("clean library: the summary and the NOT DSON section name it", (
            "\n4 .dsf files: 0 gzip, 3 plain, 1 not DSON (skipped), 0 unreadable; " in r.stdout,
            f"\n  {build}/Tools/Face Groups/Clean Groups.dsf  (text): not DSON: " in r.stdout,
            "    facs_ctrl_v      1  (0 with deltas)" in r.stdout,
            "  aliases, not counted as morphs: 1 " in r.stdout), (True, True, True, True))
        r = run(clean, "--json")
        try:
            parsed = json.loads(r.stdout)
        except ValueError:
            parsed = {}
        check("clean library --json: exit 0, no errors, one not_dson, one morph and one alias",
              (r.returncode, parsed.get("errors"), len(parsed.get("not_dson", [])),
               [(f["morph_count"], f["alias_count"]) for f in parsed.get("figures", [])]),
              (0, [], 1, [(1, 1)]))

        # A folder name that is not UTF-8, as a Windows zip unpacked on Linux can leave.
        odd = os.fsdecode(b"Caf\xe9")
        try:
            (edge / "data" / odd / "Morphs").mkdir(parents=True)
        except (OSError, UnicodeError) as e:
            print(f"  skip the non-UTF-8 folder name: this filesystem refuses it ({e})")
        else:
            rel = f"data/{odd}/OddFigure.dsf"
            (edge / rel).write_text(json.dumps(_figure(
                rel.replace(odd, "Cafe"), "OddGeom", "Odd", [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                [[0, 1, 2]],
                [("odd_root", "odd_root")])))
            (edge / "data" / odd / "Morphs" / "facs_bs_Odd.dsf").write_text(json.dumps(
                _modifier("x", "facs_bs_Odd", "#OddGeom", deltas=[[0, 1.0, 0.0, 0.0]])))
            r = run(edge)
            check("non-UTF-8 folder: text report exits 0 with no traceback",
                  (r.returncode, "Traceback" in r.stdout + r.stderr), (0, False))
            check("non-UTF-8 folder: the byte is shown as \\xe9, with its morph",
                  ("FIGURE data/Caf\\xe9/OddFigure.dsf" in r.stdout,
                   "morphs: 1 in 1 files" in r.stdout), (True, True))
            r = run(edge, "--json")
            try:
                parsed = json.loads(r.stdout)
            except ValueError:
                parsed = {}
            check("non-UTF-8 folder: --json names the file the same way",
                  [f["file"] for f in parsed.get("figures", [])],
                  ["data/Caf\\xe9/OddFigure.dsf"])

        # An integer literal too long for Python 3.11+ to convert is a plain ValueError.
        if hasattr(sys, "set_int_max_str_digits"):
            edge.mkdir(exist_ok=True)
            (edge / "long_integer.dsf").write_text(
                '{"file_version": "0.6.0.0", "n": ' + "1" * 5000 + "}")
            limit = sys.get_int_max_str_digits()
            sys.set_int_max_str_digits(4300)
            try:
                got = [(e["file"], e["kind"], e["error"].startswith("JSON error: Exceeds"))
                       for e in inventory(edge)["errors"]]
            except Exception as e:          # the failure this check exists to catch
                got = f"{type(e).__name__}: {e}"[:120]
            finally:
                sys.set_int_max_str_digits(limit)
            check("an over-long integer is one unreadable file, not a traceback",
                  got, [("long_integer.dsf", "file", True)])
        else:
            print("  skip the over-long integer: this Python has no integer string limit")

    print(f"self-test {'passed' if not failures else 'FAILED'}: "
          f"{len(failures)} failing check(s)")
    return 1 if failures else 0


# ---------------------------------------------------------------- main

def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):      # a name from JSON may hold a lone surrogate
            stream.reconfigure(errors="backslashreplace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("directory", nargs="?", type=Path,
                    help="a Daz content directory, or any folder inside one, outside the repo")
    ap.add_argument("--json", action="store_true", help="print one JSON object instead")
    ap.add_argument("--brief", action="store_true",
                    help="counts only: no bone or morph name lists (text report)")
    ap.add_argument("--selftest", action="store_true",
                    help="build a synthetic DSON tree in a temp dir and check the counts")
    ap.add_argument("--sample", type=Path, metavar="DIR",
                    help="write the self-test's synthetic library to DIR and exit; "
                         "never the real library's folder")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.sample:
        if repo_clash(args.sample):
            print(f"refusing {args.sample}: the inventory will not walk it there, because it "
                  "is in or above this repository; write the sample outside it.",
                  file=sys.stderr)
            return 2
        try:
            if args.sample.exists() and not args.sample.is_dir():
                print(f"not a directory: {args.sample}", file=sys.stderr)
                return 2
            if args.sample.is_dir() and any(args.sample.iterdir()):
                print(f"{args.sample} already exists and is not empty", file=sys.stderr)
                return 2
            build_sample(args.sample)
        except OSError as e:
            print(f"cannot write the sample to {args.sample}: {e.strerror or e}",
                  file=sys.stderr)
            return 2
        print(f"wrote a synthetic library to {args.sample}; run: "
              f"{sys.argv[0]} {args.sample}")
        return 0
    if args.directory is None:
        ap.error("give a content directory, --selftest or --sample DIR")

    why = repo_clash(args.directory)
    if why:
        print(why, file=sys.stderr)
        return 2
    if not args.directory.is_dir():
        print(f"not a directory: {args.directory}", file=sys.stderr)
        return 2

    inv = inventory(args.directory)
    if args.json:
        print(json.dumps(inv, indent=1))
    else:
        print(report(inv, args.brief))
        if not inv["dsf_files"]:
            print("no .dsf files found; is this a Daz content directory?")
    sys.stdout.flush()
    for e in inv["errors"]:
        print(f"skipped {e['file']}: {e['error']}", file=sys.stderr)
    return 1 if inv["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
