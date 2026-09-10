#!/usr/bin/env python3
"""Check which model dependencies are present under MODELS_DIR, and fetch the
missing ones.

Stdlib only, on purpose: this runs on the host before the image exists, so it
cannot lean on huggingface_hub.  It talks to the HF tree API directly.

    scripts/fetch_models.py                      # report on the 'core' group
    scripts/fetch_models.py --all                # report on everything
    scripts/fetch_models.py --download           # fetch missing 'core' models
    scripts/fetch_models.py --download --group hunyuan --group trellis
    scripts/fetch_models.py --download --all
    scripts/fetch_models.py --seed-only          # just lay down the 3D-Pack
                                                 # Checkpoints config skeleton

A file counts as present when it exists and its size matches what the hub
reports; a short file is a resumed-download casualty and gets re-fetched.
Set HF_TOKEN for gated repos.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "models.json"
HF = "https://huggingface.co"
#: The pack's own Checkpoints tree, which carries the per-model config files
#: the 3D nodes read. Beside this script in a checkout; at /app/custom_nodes
#: inside the image, where the packs are baked. COMFY_CUSTOM_NODES says which.
SKELETON_SRC = (
    Path(os.environ.get("COMFY_CUSTOM_NODES", ROOT / "custom_nodes"))
    / "ComfyUI-3D-Pack"
    / "Checkpoints"
)
SKELETON_DST = "3d_checkpoints"


# --------------------------------------------------------------------------- env

def models_dir() -> Path:
    """MODELS_DIR from the environment, else from .env, resolved like compose
    does it — relative to the directory holding the compose file."""
    raw = os.environ.get("MODELS_DIR")
    if not raw:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                line = line.strip()
                if line.startswith("MODELS_DIR="):
                    raw = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not raw:
        sys.exit("MODELS_DIR is not set, and .env does not define it.")
    return (ROOT / raw).resolve() if not os.path.isabs(raw) else Path(raw)


def auth_headers() -> dict:
    tok = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    return {"Authorization": f"Bearer {tok}"} if tok else {}


# ----------------------------------------------------------------------- hub api

def _get_json(url: str):
    req = urllib.request.Request(url, headers=auth_headers())
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def repo_tree(repo: str, repo_type: str = "model") -> list[dict]:
    """Every file in a repo as {path, size}, following pagination."""
    prefix = {"model": "models", "dataset": "datasets", "space": "spaces"}[repo_type]
    url = f"{HF}/api/{prefix}/{repo}/tree/main?recursive=1&expand=1"
    out, seen = [], set()
    while url:
        req = urllib.request.Request(url, headers=auth_headers())
        with urllib.request.urlopen(req, timeout=60) as r:
            page = json.load(r)
            link = r.headers.get("Link", "")
        for e in page:
            if e.get("type") == "file" and e["path"] not in seen:
                seen.add(e["path"])
                size = e.get("size")
                lfs = e.get("lfs") or {}
                out.append({"path": e["path"], "size": lfs.get("size", size)})
        url = ""
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.split(";")[0].strip().strip("<>")
    return out


def resolve_url(repo: str, path: str, repo_type: str = "model") -> str:
    prefix = {"model": "", "dataset": "datasets/", "space": "spaces/"}[repo_type]
    return f"{HF}/{prefix}{repo}/resolve/main/{path}"


# --------------------------------------------------------------------- downloads

def human(n: int | None) -> str:
    if n is None:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024.0
    return ""


def download(url: str, dest: Path, expected: int | None) -> None:
    """Fetch url to dest, resuming a partial .part file when the server allows."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0

    headers = auth_headers()
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        if e.code == 416 and expected and have >= expected:      # already whole
            part.rename(dest)
            return
        if e.code in (401, 403):
            raise SystemExit(
                f"  {e.code} on {url}\n"
                "  Gated or private repo — accept the licence on HF and export HF_TOKEN."
            )
        raise

    mode = "ab" if resp.status == 206 and have else "wb"
    if mode == "wb":
        have = 0
    total = expected or (int(resp.headers.get("Content-Length", 0)) + have) or None

    got = have
    with resp, open(part, mode) as fh:
        while chunk := resp.read(1 << 20):
            fh.write(chunk)
            got += len(chunk)
            if total and sys.stdout.isatty():
                pct = 100.0 * got / total
                print(f"\r    {human(got)} / {human(total)}  {pct:5.1f}%", end="", flush=True)
    # Redirected to a log: one line at the end, not 100k carriage returns.
    print(f"\r    {human(got)} / {human(total)}  done")
    part.rename(dest)


# ---------------------------------------------------------------------- manifest

def matches(path: str, patterns: list[str]) -> bool:
    """Prefix or glob match — 'subdir/' catches a whole folder."""
    from fnmatch import fnmatch
    return any(path.startswith(p) or fnmatch(path, p) for p in patterns)


def plan(entry: dict, mdir: Path) -> list[tuple[str, Path, int | None]]:
    """(url, destination, expected size) for every file this entry wants."""
    kind = entry["kind"]
    dest = mdir / entry["dest"]

    if kind == "url":
        return [(entry["url"], dest, None)]

    rtype = entry.get("repo_type", "model")
    if kind == "file":
        size = None
        try:
            for f in repo_tree(entry["repo"], rtype):
                if f["path"] == entry["file"]:
                    size = f["size"]
                    break
        except Exception:
            pass
        return [(resolve_url(entry["repo"], entry["file"], rtype), dest, size)]

    if kind == "snapshot":
        files = repo_tree(entry["repo"], rtype)
        inc, exc = entry.get("include"), entry.get("exclude", [])
        # .gitattributes and READMEs are noise; the pack ships its own configs.
        exc = list(exc) + [".gitattributes", "README.md", "*.md"]
        out = []
        for f in files:
            if inc and not matches(f["path"], inc):
                continue
            if matches(f["path"], exc):
                continue
            out.append((resolve_url(entry["repo"], f["path"], rtype),
                        dest / f["path"], f["size"]))
        return out

    raise ValueError(f"unknown kind {kind!r} in entry {entry['name']!r}")


def status(items) -> tuple[list, int, int]:
    """Split into missing/present; return (missing, bytes_present, bytes_total)."""
    missing, have_b, all_b = [], 0, 0
    for url, dest, size in items:
        all_b += size or 0
        if dest.exists() and (size is None or dest.stat().st_size == size):
            have_b += size or dest.stat().st_size
        else:
            missing.append((url, dest, size))
    return missing, have_b, all_b


# ---------------------------------------------------------------------- skeleton

def seed_skeleton(mdir: Path) -> None:
    """Copy ComfyUI-3D-Pack's Checkpoints tree (configs, model_index.json, the
    'put the model here' markers) into MODELS_DIR/3d_checkpoints.

    The compose file mounts that folder over the pack's own, which would
    otherwise hide the configs the loaders read — the pack downloads weights
    only and expects the json/yaml to already be on disk."""
    if not SKELETON_SRC.is_dir():
        print(f"! {SKELETON_SRC} not found — run scripts/setup.sh first to clone "
              f"ComfyUI-3D-Pack, or the 3D checkpoint configs will be missing.")
        return
    dst = mdir / SKELETON_DST
    copied = 0
    for src in SKELETON_SRC.rglob("*"):
        if src.is_dir() or ".git" in src.parts:
            continue
        target = dst / src.relative_to(SKELETON_SRC)
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied += 1
    print(f"skeleton: {copied} config file(s) copied into {dst}")


# -------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--download", action="store_true",
                    help="actually fetch what is missing (default: report only)")
    ap.add_argument("--group", action="append", default=[],
                    help="group to include; repeatable (default: core)")
    ap.add_argument("--all", action="store_true", help="every group except 'gated'")
    ap.add_argument("--gated", action="store_true", help="include the 'gated' group too")
    ap.add_argument("--seed-only", action="store_true",
                    help="only lay down the 3D-Pack Checkpoints skeleton")
    ap.add_argument("--list-groups", action="store_true")
    ap.add_argument("--licenses", action="store_true",
                    help="print each model's licence and whether it permits commercial use")
    ap.add_argument("--accept-noncommercial", action="store_true",
                    help="allow downloading models whose licence forbids commercial use")
    args = ap.parse_args()

    man = json.loads(MANIFEST.read_text())
    if args.licenses:
        width = max(len(e["name"]) for e in man["models"])
        for e in sorted(man["models"], key=lambda x: (x["commercial"].startswith("yes"),
                                                      x["group"], x["name"])):
            flag = {"y": "  ", "c": "! ", "N": "!!"}[
                "y" if e["commercial"].startswith("yes")
                else "N" if e["commercial"].startswith("NO") else "c"]
            print(f"{flag}{e['name']:<{width}}  {e['license']}")
            if not e["commercial"].startswith("yes"):
                print(f"  {'':<{width}}  commercial: {e['commercial']}")
                print(f"  {'':<{width}}  {e['license_url']}")
        print("\n!! forbids commercial use   ! commercial use with conditions")
        print("These are the licences on the MODEL WEIGHTS.  What they say about the "
              "meshes and images you generate with them is a separate question the "
              "licence text answers — read it before shipping an asset.")
        return 0
    if args.list_groups:
        for g, desc in man["groups"].items():
            print(f"  {g:<12} {desc}")
        return 0

    mdir = models_dir()
    mdir.mkdir(parents=True, exist_ok=True)
    print(f"MODELS_DIR = {mdir}")

    seed_skeleton(mdir)
    if args.seed_only:
        return 0

    groups = set(args.group) or ({g for g in man["groups"]} if args.all else {"core"})
    if args.all:
        # --all means "everything you can just use": opt in to the two groups
        # with strings attached rather than have them arrive by default.
        groups.discard("noncommercial")
        if not args.gated:
            groups.discard("gated")
    if args.gated:
        groups.add("gated")
    print(f"groups     = {', '.join(sorted(groups))}\n")

    entries = [e for e in man["models"] if e["group"] in groups]
    blocked = [e for e in entries
               if e["commercial"].startswith("NO") and not args.accept_noncommercial]
    if blocked:
        for e in blocked:
            print(f"  SKIP {e['name']:<48} {e['license']} — {e['commercial']}")
        print("       pass --accept-noncommercial to fetch these anyway\n")
        entries = [e for e in entries if e not in blocked]
    todo, ok, failed = [], 0, []

    for e in entries:
        try:
            items = plan(e, mdir)
        except Exception as exc:
            print(f"  ??  {e['name']:<48} could not list repo: {exc}")
            failed.append(e["name"])
            continue
        missing, have_b, all_b = status(items)
        mark = "ok " if not missing else "MISS"
        detail = human(all_b) if not missing else f"{human(all_b - have_b)} to fetch"
        print(f"  {mark} {e['name']:<48} {detail}")
        if e.get("note") and missing:
            print(f"       {e['note']}")
        if missing:
            todo.append((e, missing))
        else:
            ok += 1

    total = sum(s or 0 for _, ms in todo for _, _, s in ms)
    print(f"\n{ok}/{len(entries)} complete; {len(todo)} incomplete ({human(total)} outstanding)")
    if failed:
        print(f"could not check: {', '.join(failed)}")

    if not todo:
        return 0
    if not args.download:
        print("\nre-run with --download to fetch them.")
        return 1

    free = shutil.disk_usage(mdir).free
    if total > free:
        sys.exit(f"\nNeed {human(total)} but only {human(free)} free on {mdir}.")

    for e, missing in todo:
        print(f"\n==> {e['name']}  ({len(missing)} file(s))")
        for url, dest, size in missing:
            print(f"  {dest.relative_to(mdir)}  {human(size)}")
            try:
                download(url, dest, size)
            except SystemExit as exc:
                # Gated/forbidden applies to the whole repo, so stop this entry.
                print(exc)
                failed.append(e["name"])
                break
            except Exception as exc:
                # One flaky file should not skip the other sixteen; note it and
                # carry on, and the next --download run retries just the gaps.
                print(f"  FAILED: {exc}")
                failed.append(e["name"])
                continue

    if failed:
        print(f"\nIncomplete: {', '.join(sorted(set(failed)))}")
        return 1
    print("\nAll requested models present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
