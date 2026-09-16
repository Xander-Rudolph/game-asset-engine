#!/usr/bin/env python3
"""Check which external command-line tools are installed under tools/, and
fetch the missing ones.

    scripts/fetch_tools.py                    # check every tool in tools.json
    scripts/fetch_tools.py --download         # fetch and unpack what is missing
    scripts/fetch_tools.py --download rhubarb # just one tool
    scripts/fetch_tools.py --licenses         # each tool's licence
    scripts/fetch_tools.py --path rhubarb     # print the binary's path, or exit 1

Standard library only, like fetch_models.py: it runs on the host.

tools.json pins each tool to one release archive by URL, byte size and
sha256. --download writes the archive to tools/_downloads/<file>.part,
resuming a partial one when the server allows, and checks the size and then
the sha256 of the whole file before anything is unpacked. A download that
stops short, whether the connection drops with an error or just closes
early, keeps its .part file and exits 1; the next --download resumes it. A
file larger than pinned, a full-size file whose sha256 does not match, or a
server with nothing past the partial file (HTTP 416) is refused: the .part
file is deleted, nothing is unpacked and it exits 1. Either way a tampered
or truncated archive never reaches tools/.

Only the members named in the entry's "keep" list are unpacked, into a
hidden staging folder that is renamed into place once every member is
written, so an interrupted unpack never looks installed. Each file keeps the
Unix mode stored in the archive, which is how the binary stays executable.
The archive is deleted afterwards. A small .fetched.json in the tool's folder
records the archive's sha256 and every unpacked file's size, and the check
compares against it: a missing or resized file, or a tools.json entry pinned
to a different archive, reads as not installed.

For Rhubarb that means rhubarb, res/ and LICENSE.md only. The Spine extras jar
in the same zip (GPL-2.0 with Classpath Exception, and CDDL parts) is never
unpacked. The tools run from tools/ on the host, so the published image does
not redistribute them.

--path NAME is for other scripts and shell lines. It prints the absolute path
of NAME's binary when the tool is installed and complete, and otherwise
prints why to stderr and exits 1, including when tools.json has no NAME. It
takes no other option or tool name:

    RHUBARB="$(scripts/fetch_tools.py --path rhubarb)" || exit 1

Every entry's dest must be its own folder inside tools/, outside
tools/_downloads, and its binary a file inside dest. Installing replaces dest
whole, so a manifest with any other dest is refused before anything is
checked, fetched or deleted.

Exit codes: 0 everything asked for is installed (or --licenses); 1 something
is missing, a download stopped short, a size or checksum was refused,
--path found nothing usable, or tools.json has a dest or binary outside
tools/; 2 bad arguments, including an unknown tool name without --path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tools.json"
TOOLS = ROOT / "tools"
DOWNLOADS = TOOLS / "_downloads"
MARKER = ".fetched.json"


# ---------------------------------------------------------------------- manifest

def load_manifest() -> list[dict]:
    tools = json.loads(MANIFEST.read_text())["tools"]
    check_dests(tools)
    return tools


def check_dests(tools: list[dict]) -> None:
    """Refuse the manifest unless every dest is its own folder inside tools/.

    unpack() deletes dest before renaming the unpacked copy into place, so a
    dest of "tools", "scripts", "." or "../x" would delete part of the repo or
    write outside it. This runs whenever tools.json is read, so it comes before
    any check, download or delete."""
    tools_dir, downloads = TOOLS.resolve(), DOWNLOADS.resolve()
    seen: dict[Path, str] = {}
    for t in tools:
        name = t.get("name", "?")
        dest = t.get("dest")
        full = (ROOT / dest).resolve() if isinstance(dest, str) and dest else None
        if (full is None or full == tools_dir or not full.is_relative_to(tools_dir)
                or full.is_relative_to(downloads)):
            raise SystemExit(f"{MANIFEST.name}: {name}: dest {dest!r} is not a folder "
                             "inside tools/ (outside tools/_downloads). fetch_tools.py "
                             "replaces dest whole when it installs, so it refuses "
                             "this manifest. Nothing was changed")
        for other, other_name in seen.items():
            if full.is_relative_to(other) or other.is_relative_to(full):
                raise SystemExit(f"{MANIFEST.name}: {name} and {other_name} share a "
                                 "dest folder, or one lies inside the other, so "
                                 "installing one would delete the other. Nothing was "
                                 "changed")
        seen[full] = name
        binary = t.get("binary")
        if not (isinstance(binary, str) and binary
                and (full / binary).resolve().is_relative_to(full)
                and (full / binary).resolve() != full):
            raise SystemExit(f"{MANIFEST.name}: {name}: binary {binary!r} is not a "
                             "file inside its dest. Nothing was changed")


def find(name: str, tools: list[dict] | None = None) -> dict | None:
    for t in tools if tools is not None else load_manifest():
        if t["name"] == name:
            return t
    return None


def dest_dir(tool: dict) -> Path:
    return ROOT / tool["dest"]


def human(n: int | None) -> str:
    if n is None:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024.0
    return ""


# ------------------------------------------------------------------------- check

def problems(tool: dict) -> list[str]:
    """Why this tool does not count as installed; empty when it does."""
    dest = dest_dir(tool)
    marker = dest / MARKER
    if not marker.is_file():
        return [f"not installed: {dest.relative_to(ROOT)} has no {MARKER}"]
    try:
        rec = json.loads(marker.read_text())
    except (OSError, ValueError) as exc:
        return [f"unreadable {MARKER}: {exc}"]
    out = []
    if rec.get("sha256") != tool["sha256"]:
        out.append("installed from a different archive than tools.json pins "
                   f"({str(rec.get('sha256'))[:12]} against {tool['sha256'][:12]})")
    for rel, size in sorted(rec.get("files", {}).items()):
        f = dest / rel
        if not f.is_file():
            out.append(f"missing {rel}")
        elif f.stat().st_size != size:
            out.append(f"{rel} is {f.stat().st_size} bytes, expected {size}")
    binary = dest / tool["binary"]
    if not binary.is_file():
        out.append(f"missing binary {tool['binary']}")
    elif not os.access(binary, os.X_OK):
        out.append(f"{tool['binary']} is not executable")
    return out


def tool_path(name: str) -> Path | None:
    """The binary of an installed, complete tool, or None. For other scripts."""
    tool = find(name)
    if tool is None or problems(tool):
        return None
    return dest_dir(tool) / tool["binary"]


# ---------------------------------------------------------------------- download

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


class ServerFileShorter(Exception):
    """The server has nothing past the bytes already downloaded (HTTP 416)."""


def download(url: str, part: Path, expected: int) -> None:
    """Fetch url into part, resuming a shorter .part when the server allows."""
    part.parent.mkdir(parents=True, exist_ok=True)
    have = part.stat().st_size if part.exists() else 0
    if have > expected:
        part.unlink()
        have = 0
    if have == expected:
        return
    headers = {"User-Agent": "asset-engine-fetch-tools"}
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and have:
            raise ServerFileShorter(f"the server has no bytes past {have}") from exc
        raise
    mode = "ab" if resp.status == 206 and have else "wb"
    got = have if mode == "ab" else 0
    if mode == "ab":
        print(f"    resuming from {human(have)}")
    with resp, open(part, mode) as fh:
        while chunk := resp.read(1 << 20):
            fh.write(chunk)
            got += len(chunk)
            if sys.stdout.isatty():
                pct = 100.0 * got / expected
                print(f"\r    {human(got)} / {human(expected)}  {pct:5.1f}%",
                      end="", flush=True)
    print(f"\r    {human(got)} / {human(expected)}  downloaded")


def safe_member(name: str, strip: str) -> PurePosixPath | None:
    """The member's path below `strip`, or None if it is outside it or unsafe."""
    if not name.startswith(strip):
        return None
    rel = PurePosixPath(name[len(strip):])
    if not rel.parts or rel.is_absolute() or ".." in rel.parts:
        return None
    return rel


def kept(rel: PurePosixPath, keep: list[str]) -> bool:
    s = rel.as_posix()
    for k in keep:
        if k.endswith("/"):
            if s.startswith(k):
                return True
        elif s == k:
            return True
    return False


def unpack(tool: dict, archive: Path) -> dict[str, int]:
    """Unpack only the keep-list into dest via a staging folder; return sizes."""
    if tool.get("archive") != "zip":
        raise SystemExit(f"  {tool['name']}: archive type {tool.get('archive')!r} "
                         "is not supported")
    dest = dest_dir(tool)
    stage = dest.parent / f".{dest.name}.staging"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    files: dict[str, int] = {}
    matched = {k: False for k in tool["keep"]}
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            rel = safe_member(info.filename, tool["strip"])
            if rel is None or info.is_dir() or not kept(rel, tool["keep"]):
                continue
            for k in matched:
                if kept(rel, [k]):
                    matched[k] = True
            target = stage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out, 1 << 20)
            mode = (info.external_attr >> 16) & 0o7777
            if info.create_system == 3 and mode:
                # Keep the stored permission bits, but never write group or
                # other write access, whatever the archive says.
                os.chmod(target, mode & ~(stat.S_IWGRP | stat.S_IWOTH))
            files[rel.as_posix()] = info.file_size
    missing = [k for k, hit in matched.items() if not hit]
    if missing:
        shutil.rmtree(stage)
        raise SystemExit(f"  {tool['name']}: the archive holds nothing for keep "
                         f"entries {missing}; tools.json no longer matches it")
    (stage / MARKER).write_text(json.dumps({
        "name": tool["name"], "version": tool["version"], "url": tool["url"],
        "sha256": tool["sha256"], "size": tool["size"], "keep": tool["keep"],
        "files": files}, indent=1) + "\n")
    if dest.exists():
        shutil.rmtree(dest)
    stage.rename(dest)
    return files


def fetch(tool: dict) -> bool:
    name = tool["name"]
    part = DOWNLOADS / (Path(tool["url"]).name + ".part")
    print(f"\n==> {tool.get('title', name)} {tool['version']}  ({human(tool['size'])})")
    print(f"    {tool['url']}")
    try:
        download(tool["url"], part, tool["size"])
    except ServerFileShorter as exc:
        print(f"  REFUSED: {exc}, so its file is smaller than the {tool['size']} bytes "
              "tools.json pins. The partial download was deleted.")
        part.unlink()
        return False
    except (urllib.error.URLError, OSError) as exc:
        print(f"  FAILED: {exc}")
        print(f"  the partial download stays at {part.relative_to(ROOT)}; "
              "--download resumes it")
        return False
    size = part.stat().st_size if part.exists() else 0
    if size < tool["size"]:
        # http.client returns a short body without raising when the server
        # closes early, so this is the usual sign of a dropped connection.
        print(f"  INCOMPLETE: {part.name} is {size} of {tool['size']} bytes; the server "
              "stopped early")
        print(f"  the partial download stays at {part.relative_to(ROOT)}; "
              "--download resumes it")
        return False
    if size > tool["size"]:
        print(f"  REFUSED: {part.name} is {size} bytes, tools.json pins {tool['size']}")
        part.unlink()
        return False
    digest = sha256_of(part)
    if digest != tool["sha256"]:
        print(f"  REFUSED: sha256 {digest}\n"
              f"           expected {tool['sha256']}\n"
              "  Nothing was unpacked and the download was deleted.")
        part.unlink()
        return False
    print("    size and sha256 match")
    try:
        files = unpack(tool, part)
    except SystemExit as exc:
        print(exc)
        return False
    part.unlink()
    try:
        DOWNLOADS.rmdir()
    except OSError:
        pass
    total = sum(files.values())
    print(f"    unpacked {len(files)} files, {human(total)} ({total} bytes), "
          f"into {tool['dest']}/")
    return True


# -------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", metavar="NAME",
                    help="tools to act on (default: every tool in tools.json)")
    ap.add_argument("--download", action="store_true",
                    help="fetch, verify and unpack what is missing")
    ap.add_argument("--licenses", action="store_true",
                    help="print each tool's licence and whether commercial use is allowed")
    ap.add_argument("--path", metavar="NAME",
                    help="print the binary path of an installed tool, or exit 1")
    args = ap.parse_args()
    if args.path is not None and (args.download or args.licenses or args.names):
        ap.error("--path takes one tool name and no other option or name")

    tools = load_manifest()
    known = {t["name"] for t in tools}
    if args.path is not None:
        tool = find(args.path, tools)
        if tool is None:
            print(f"unknown tool {args.path!r}; tools.json has: {', '.join(sorted(known))}",
                  file=sys.stderr)
            return 1
        why = problems(tool)
        if why:
            for w in why:
                print(f"{args.path}: {w}", file=sys.stderr)
            print(f"run: scripts/fetch_tools.py --download {args.path}", file=sys.stderr)
            return 1
        print(dest_dir(tool) / tool["binary"])
        return 0

    for n in args.names:
        if n not in known:
            print(f"unknown tool {n!r}; tools.json has: {', '.join(sorted(known))}",
                  file=sys.stderr)
            return 2

    chosen = [t for t in tools if not args.names or t["name"] in args.names]

    if args.licenses:
        width = max(len(f"{t['name']} {t['version']}") for t in chosen)
        for t in chosen:
            label = f"{t['name']} {t['version']}"
            print(f"{label:<{width}}  {t['license']}")
            print(f"{'':<{width}}  commercial: {t['commercial']}")
            print(f"{'':<{width}}  {t['license_url']}")
            print(f"{'':<{width}}  unpacked: {', '.join(t['keep'])}")
        print("\nThese are the licences on the tools themselves. They run from tools/ "
              "on the host and are not copied into the image.")
        return 0

    todo = []
    for t in chosen:
        why = problems(t)
        label = f"{t['name']} {t['version']}"
        if why:
            print(f"  MISS {label:<24} {human(t['size'])} to fetch")
            for w in why[:5]:
                print(f"       {w}")
            if len(why) > 5:
                print(f"       and {len(why) - 5} more")
            todo.append(t)
        else:
            print(f"  ok   {label:<24} {dest_dir(t) / t['binary']}")
    print(f"\n{len(chosen) - len(todo)}/{len(chosen)} installed")
    if not todo:
        return 0
    if not args.download:
        print("re-run with --download to fetch them.")
        return 1

    failed = [t["name"] for t in todo if not fetch(t)]
    if failed:
        print(f"\nIncomplete: {', '.join(failed)}")
        return 1
    print("\nAll requested tools installed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
