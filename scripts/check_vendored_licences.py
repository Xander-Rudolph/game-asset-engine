#!/usr/bin/env python3
"""Fail if a tracked file outside docs/ and research/ looks like copied, licence-restricted content.

    scripts/check_vendored_licences.py
    scripts/check_vendored_licences.py --untracked   # also files git does not track yet
    scripts/check_vendored_licences.py --markers     # what it looks for, and why

WHY: the repo is Apache-2.0, and NOTICE says the third-party software it drives
is not vendored here.  The research notes read proprietary SDK code, a store
EULA, GPL projects and share-alike pages precisely so that none of it has to be
copied.  docs/ and research/ are where those sources are named, quoted and
linked.  Anywhere else, a maker's name or the body of a restrictive licence is
the cheapest sign that something was pasted in, and a paste is far easier to
catch before a commit than after a release.

It prints path:line:marker for each hit, followed by the matched text, and exits
1 if there is any hit that the allowlist below does not cover.  Standard library
only; it reads the files `git ls-files` lists and never touches the network.

WHAT IT WILL NOT TELL YOU: whether code was copied.  A pasted function with its
header stripped matches nothing here, and a hit is only a reason to look.  It
also cannot see into binaries, and it skips its own file, which has to name every
marker.  NOTICE, CREDITS.md and the Dockerfile name GPL licences by their SPDX
ids, which is licence metadata rather than licence text, so they match nothing.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve().relative_to(ROOT).as_posix()

# Where sources are meant to be named, quoted and cited.
SKIP_PREFIXES = ("docs/", "research/")

# ------------------------------------------------------------------ allowlist
# (path, marker, reason).  A legitimate mention outside docs/ and research/.
# Covers every line in that file that hits that marker, so give a reason that
# would still hold if the file grew another mention.
ALLOW = [
    ("CLAUDE.md", "Valve",
     "the maintainer rules file, forbidding that maker's content in the repo"),
    ("CLAUDE.md", "Daz",
     "the maintainer rules file, forbidding that maker's content in the repo"),
    (".claude/skills/research-note/SKILL.md", "Daz",
     "names docs/reference/daz-genesis.md as a note to copy the shape from, and DAZ claim "
     "ids as an example of how a page cites its register"),
    ("scripts/lipsync_cues.py", "Valve",
     "credits the 0.08 s window of Valve's phoneme filter as the source of the share "
     "frame rule, a number read in docs/reference/source-filmmaker.md, not SDK code"),
    ("scripts/daz_inventory.py", "Daz",
     "reads a user's own Daz content library from outside the repo and refuses a path "
     "inside it, so it names the maker, its folders and its spec; its test library is "
     "invented"),
    ("scripts/daz_inventory.py", "Genesis",
     "names Genesis 9 Starter Essentials and its data/ folders as the library a user "
     "unpacks and points it at; no Genesis data is in the file"),
]

# Separator between the words of a multi-word marker: whitespace, or a comment
# leader when the text has been wrapped inside a source comment.
SEP = r"(?:[\s#*/;]|--)+"


def words(*ws: str) -> str:
    return SEP.join(ws)


# (marker, pattern, flags, why).  Case rules are per marker: a maker's name is
# matched as a whole word so it is not found inside unrelated words, and a GPL
# title block is matched in capitals so an SPDX name or a sentence about the GPL
# does not trip it.  The reasons point at the page that settled each rule.
SFM = "docs/reference/source-filmmaker.md, Licences"
DAZ = "docs/reference/daz-genesis.md, Licences"
OWN = "docs/guide/licensing.md, This repository's own licence"
MARKERS = [
    ("Valve", r"\bValve\b", 0,
     f"Source SDK code and Valve content: learn from, never vendor ({SFM})"),
    ("LIPSinc", r"\bLIPSinc\b", re.I,
     f"the TalkBack files in the Source SDK are proprietary: never use, vendor or ship ({SFM})"),
    ("Source 1 SDK", r"\b" + words("Source", "1", "SDK") + r"\b", re.I,
     f"the SDK licence reaches only a Source 1 Valve game mod ({SFM})"),
    ("GPL licence text",
     r"\bGNU" + SEP + r"(?:(?:AFFERO|LESSER|LIBRARY)" + SEP + r")?"
     + words("GENERAL", "PUBLIC", "LICENSE", "Version") + r"\b", 0,
     f"the title block of a GPL, LGPL or AGPL body; none of that code is vendored ({OWN})"),
    ("GPL notice",
     r"\bThis" + SEP + r"(?:program|library)" + SEP
     + words("is", "free", r"software\s*[;:]?", "you", "can", "redistribute", "it"), re.I,
     f"the per-file notice a GPL or LGPL source file carries ({OWN})"),
    # The short name, the URL and the long name, as a licence footer or the
    # title of the legal code spells it, with or without NonCommercial.
    ("CC BY-SA",
     r"\bCC[\s-]BY(?:-NC)?-SA\b"
     r"|creativecommons\.org/licenses/by(?:-nc)?-sa\b"
     r"|\bAttribution[\s-]+(?:Non[\s-]?Commercial[\s-]+)?Share[\s-]?Alike\b",
     re.I, f"CC BY-SA 3.0 work such as Crowbar cannot be relicensed as Apache-2.0 "
           f"({SFM}, Crowbar); the BY-NC-SA variants add a NonCommercial condition"),
    ("Daz", r"\bDaz(?:\s?3D)?\b", re.I,
     f"under the standard Daz EULA, nothing Daz Content can be extracted from may be "
     f"distributed ({DAZ})"),
    ("Genesis", r"\bGenesis\s+[89](?:\.\d)?\b", 0,
     f"the Genesis 8 and 9 figures are Daz store products (Starter Essentials), under "
     f"the same Daz EULA as paid content ({DAZ})"),
]
COMPILED = [(name, re.compile(pat, flags)) for name, pat, flags, _ in MARKERS]


def git_files(untracked: bool) -> list[str]:
    cmds = [["ls-files", "-z"]]
    if untracked:
        cmds.append(["ls-files", "-z", "--others", "--exclude-standard"])
    out: set[str] = set()
    for cmd in cmds:
        try:
            res = subprocess.run(["git", "-C", str(ROOT), *cmd],
                                 capture_output=True, check=True)
        except (OSError, subprocess.CalledProcessError) as e:
            err = getattr(e, "stderr", b"") or b""
            sys.exit(f"check_vendored_licences: git ls-files failed, run this from a "
                     f"git checkout: {err.decode(errors='replace').strip() or e}")
        out.update(p for p in res.stdout.decode().split("\0") if p)
    return sorted(out)


def scan(rel: str):
    """Yield (line, marker, matched text) for every marker hit in one file."""
    path = ROOT / rel
    try:
        data = path.read_bytes()
    except OSError:
        return                      # listed by git but deleted in the working tree
    if b"\0" in data[:8192]:
        return                      # binary
    text = data.decode("utf-8", errors="replace")
    found = [(m.start(), name, " ".join(m.group(0).split()))
             for name, rx in COMPILED for m in rx.finditer(text)]
    for pos, name, snippet in sorted(found):
        yield text.count("\n", 0, pos) + 1, name, snippet


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--untracked", action="store_true",
                    help="scan files git does not track yet too (ignored files stay ignored)")
    ap.add_argument("--markers", action="store_true",
                    help="list the markers and why each one is here, then exit")
    args = ap.parse_args()

    if args.markers:
        for name, _, _, why in MARKERS:
            print(f"{name:<18} {why}")
        return 0

    known = {name for name, *_ in MARKERS}
    for path, marker, _ in ALLOW:
        if marker not in known:
            sys.exit(f"check_vendored_licences: allowlist entry for {path} names "
                     f"unknown marker {marker!r}")
    allowed = {(path, marker) for path, marker, _ in ALLOW}

    hits = used = 0
    matched: set[tuple[str, str]] = set()
    scanned: set[str] = set()
    for rel in git_files(args.untracked):
        if rel == SELF or rel.startswith(SKIP_PREFIXES):
            continue
        scanned.add(rel)
        for line, marker, snippet in scan(rel):
            if (rel, marker) in allowed:
                matched.add((rel, marker))
                used += 1
                continue
            print(f"{rel}:{line}:{marker}  {snippet!r}")
            hits += 1

    sys.stdout.flush()
    for path, marker, _ in ALLOW:
        if path in scanned and (path, marker) not in matched:
            print(f"note: allowlist entry ({path}, {marker}) matched nothing; "
                  f"remove it if the mention is gone", file=sys.stderr)
    if hits:
        print(f"{hits} hit(s) outside docs/ and research/. Remove the copied content, "
              f"or add (path, marker, reason) to ALLOW in {SELF} if the mention is "
              f"legitimate.", file=sys.stderr)
        return 1
    print(f"no restricted-content markers outside docs/ and research/"
          f"{f' ({used} allowlisted)' if used else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
