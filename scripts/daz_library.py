#!/usr/bin/env python3
r"""Install Daz Install Manager packages into a content library outside this repo, and record them.

    scripts/daz_library.py install ~/Downloads/IM00086958-0?_Genesis9StarterEssentials?Of3.zip
    scripts/daz_library.py install ~/Downloads/IM00086958-03_Genesis9StarterEssentials3Of3.zip --dry-run
    scripts/daz_library.py install PACKAGE.zip --overwrite
    scripts/daz_library.py install PACKAGE.zip --eula-read 2026-09-16
    scripts/daz_library.py install PACKAGE.zip --interactive-license   # only once you have bought one
    scripts/daz_library.py list
    scripts/daz_library.py licence 86958
    scripts/daz_library.py licence 86958 --standard-license             # take a mistaken flag back off
    scripts/daz_library.py verify
    scripts/daz_library.py verify 86958 --crc
    scripts/daz_library.py uninstall 86958 --part 03 --dry-run
    scripts/daz_library.py uninstall 86958
    scripts/daz_library.py case-check
    scripts/daz_library.py list --json
    scripts/daz_library.py install PACKAGE.zip --library /other/disk/daz_library
    scripts/daz_library.py selftest

WHERE THE LIBRARY IS. By default MODELS_DIR/daz_library. MODELS_DIR comes from
the environment, else from .env, and a relative value is resolved against the
repo root as docker compose resolves it, the same way scripts/fetch_models.py
reads it. Compose mounts MODELS_DIR at /app/models, so the container sees the
library at /app/models/daz_library. --library names another folder. A library
inside this repository, or one that contains it, is refused before anything is
read or written: Daz content never goes in the repo (CLAUDE.md,
docs/reference/daz-genesis.md). Give scripts/daz_inventory.py, or an importer's
content directory setting, the library folder itself.

WHAT A PACKAGE IS. A Daz Install Manager (DIM) zip, downloaded by hand from your
Daz account. Do not script the Daz website: its Terms of Service forbid
automated access. The file name must match Daz's documented pattern

    ^([A-Z][0-9A-Z]{0,6})(?=\d{8})(\d{8})(-(\d{2}))?_([0-9A-Za-z]+)\.zip$

a store prefix, an eight-digit SKU, an optional two-digit part and a name, as in
IM00086958-01_Genesis9StarterEssentials1Of3.zip. The zip must hold Manifest.dsx
at its root; Supplement.dsx beside it gives the product name. Only the File
elements of Manifest.dsx with TARGET="Content" and ACTION="Install" are
extracted, each to its VALUE with the leading "Content/" removed, so
Content/data/... lands in <library>/data/.... Other File elements, and zip
entries the manifest does not list, are counted and left alone.

Parts of one product share its SKU and the GlobalID in Manifest.dsx, and may be
installed together or one at a time. These are refused as signs of a renamed or
mixed-up zip: a part number that disagrees with the "(N of M)" in
Supplement.dsx's product name, a GlobalID that differs from the one recorded
for the SKU or is recorded under another SKU, two zips for the same part, and a
manifest whose Runtime/Support/DAZ_3D_<number>_ files all name another SKU.
Those two naming habits were read from the three Genesis 9 Starter Essentials
packages (SKU 86958) on 2026-09-16, not from a specification.

SAFETY. Every path of every zip is checked before anything is written, and a
refused path stops the whole run with nothing written. Refused: an absolute
path, a drive letter, a backslash, a NUL, a "..", "." or empty component, a
path into .daz_library/ (where the records live), a name ending in
.daz_library-part (the temporary suffix), a zip entry stored as a symlink, a
name the zip holds twice, a path listed as a file that another listed path, in
the same or another zip of the run, needs as a folder, a file on disk where a
folder is needed, a folder or a symlink already at the path, a symlink or
anything but a regular file at its temporary name, and a path that resolves
outside the library through a symlink already in it. An install takes the
library's lock first (one process at a time), then reads the records and runs
the GlobalID and path checks inside it; when the library has no lock file yet,
the checks also run once before, so a refused run creates nothing. The checks
see the library as it is when they run: another program that changes the
library during an install, without the lock, is not guarded against, except
that the temporary file is created with O_EXCL and O_NOFOLLOW, so it never
follows or reuses anything placed there. Each file is written to that hidden
temporary name beside it and renamed into place only after the zip's CRC-32
check passes, so a corrupt entry never lands. A regular file left at a
temporary name by an interrupted run is removed and written again. A file
already present with identical bytes is skipped. A file with different bytes
is a conflict: the package installs nothing and the conflicts are listed,
unless --overwrite replaces them. A package is also skipped when the free space
is short. --dry-run takes no lock, plans each package against the library as it
is now and writes nothing, so a file shared by two parts shows as a write in
both.

STOPPING. If writing a package fails for any reason, such as a corrupt entry,
an unsupported compression method or an encrypted entry, its temporary file is
removed, that package stops, and the files it had already placed are recorded
with "complete": false; later packages still run, and the exit status is 1.
On the first SIGINT (Ctrl-C), SIGTERM or SIGHUP the install stops after the
chunk it is copying: the temporary file is removed, the files placed so far are
recorded with "complete": false, no further package starts, and the exit
status is 128 plus the signal number (130 for Ctrl-C). A second signal stops at
once, and the files placed so far are still recorded. Signals are held for the
moment a file is renamed into place and listed, and while a record is saved, so
a placed file is never left out of the record. Install again to finish, and
`verify` lists incomplete parts meanwhile.

THE RECORD. <library>/.daz_library/<SKU>.json, the SKU without leading zeros.
It holds the product name (Supplement.dsx, without "(N of M)"), the GlobalID,
the store prefix, and per part: the package file name, the product name as
Supplement.dsx gives it, the zip's sha256 and size, the time it was installed
(kept when the same zip is installed again), the time of the last run, whether
it completed, and the last run's counts. Every installed path is listed with
its size, the CRC-32 the zip gave it and the parts that list it. Files that were already
present with identical bytes are recorded too. The licence held is "Daz
Standard License (EULA)" unless --interactive-license records a bought
Interactive License (this script cannot check a purchase), with the EULA URL
and the date you last read the EULA (--eula-read YYYY-MM-DD, else null). A
later install keeps the recorded licence unless one of those flags changes it.
The rest of the licence block is wording built from those two values: it is
written again whenever the record is saved, and `licence` and `install` print
it as this version of the script words it.

THE LICENCE, as docs/reference/daz-genesis.md reads it ("Licences"; not legal
advice). Renders and sprites made from Daz content may ship in a game without a
purchase, unless the product page says otherwise, as long as nothing shipped
lets the content be extracted; no ruling covers selling standard-licence
renders or sprites as a separate in-game purchase, so ask Daz first. The mesh,
rig, morphs and textures, and FBX or glTF exported from them, may not go into a
build without an Interactive License for that product or a separate agreement
signed by both parties. Even under an Interactive License they may go into a
build only if all of these hold: never in native formats such as .duf or .dsf;
protected against extraction; Daz's written consent before selling the content,
or its 2D or 3D derivatives, as a separate in-game purchase; and Daz's written
consent before delivering it through the cloud or after install when the
individual or business has annual revenue above US$1,000,000. Keep Daz content
out of the AI stages: never give its mesh, textures or UV maps to any model,
and do not feed its renders to Qwen-Image, ControlNet, TRELLIS, Hunyuan3D or
any training until Daz answers in writing. An Interactive License does not lift
that. The EULA carries no version and may change, so re-read it and record the
date.

OTHER COMMANDS.
  list         products recorded: parts, files, bytes, licence
  licence SKU  print the licence held; --interactive-license,
               --standard-license and --eula-read DATE change the record
  verify [SKU] every recorded file is present, a regular file (a symlink
               counts as not a file), at its recorded size; --crc also
               recomputes each CRC-32
  uninstall SKU [--part NN]
               removes the files recorded for that SKU (or that part) that no
               other SKU (or other part of it) records, then the folders that
               end up empty. If a file's size differs from the record, nothing
               is removed unless --force. --dry-run lists what would go.
  case-check   paths that differ only in case, which a case-sensitive file
               system such as Linux's keeps apart: (1) names in one folder of
               the library that differ only in case, and (2) references inside
               the library's .dsf and .duf files (strings such as
               "/data/Daz%203D/..." whose first folder is a top-level folder of
               the library, and whose last component has an extension, which
               leaves out group names such as "/People/Feminine") that match
               a file only when case is ignored. References that match nothing
               are counted as missing; they may belong to products not
               installed, such as Daz Studio's built-in shaders. Counts and
               --examples N of each. How any importer copes with them is not
               tested here.
  selftest     builds synthetic packages with invented names and no Daz
               content in a temporary folder (or --dir DIR, kept) and checks
               install, conflicts, refusals, verify, uninstall and case-check.

--json on any command except selftest prints one JSON object on stdout instead
of the text report; refusals still go to stderr as well.

MEASURED on 2026-09-16 on the host's python3 3.13, with the three Genesis 9
Starter Essentials packages (SKU 86958) downloaded in a browser. The first
block ran before that day's review fixes (the temporary-name checks, the lock
order, recording on any stop); the "after the fixes" lines ran on this version.
  packages  Manifest.dsx listed 4528, 197 and 1780 files, every one TARGET
            "Content" and ACTION "Install", with no zip entry left unlisted.
            Three Runtime/Support/DAZ_3D_86958_* files are listed by all three
            parts with identical bytes. (`install --dry-run --json`)
  install   all three parts into an empty /models/daz_library: 7.59 s wall,
            and 6.90 s the second time (`date` before and after), 6499 files,
            2452887819 bytes, which `du -sb` agreed with; parts 02 and 03
            skipped the three shared files as identical. Nothing is synced to
            disk, so that is the time to the page cache. Installing all three
            over a complete install found every file identical and wrote
            nothing in 6.98 s wall. `uninstall 86958` removed the 6499 files
            and 553 folders in 0.15 s, leaving only .daz_library/.
  verify    0.03 s; with --crc 0.96 s (the command's own timer).
  uninstall --part 03 removed 1777 files and 164 folders that ended up empty
            and kept the three shared files; installing part 03 again took
            0.86 s wall, and verify --crc then passed on all 6499 files.
  corrupt   a copy of part 03 cut to half its size: refused, not a readable
            zip. A copy with one byte flipped inside entry 1088 of 1780: into
            the installed library, the comparison hit "Bad CRC-32" and nothing
            changed; into an empty library, 1087 files landed, the install
            stopped at that entry and recorded complete: false.
  case-check 0 folders held names that differ only in case. All 3847 .dsf
            and .duf files were plain JSON, read in 7.22 s: 24036 references
            to 5185 distinct paths, 5016 exact, 76 matching only when case is
            ignored (52 through "runtime/" for Runtime/, 18 through "DAZ 3D"
            for "Daz 3D", 4 through "Daz" for "DAZ", 2 through a file name)
            and 93 matching nothing, such as Daz Studio's built-in FilaToon
            and PBRSkin shaders. (`case-check --json`)
  after the fixes:
  dry run   all three parts against /models/daz_library: exit 0, every file
            identical (4528, 197, 1780), 6.84 s wall (`date` before and
            after); the record's mtime, size and sha256 were unchanged.
  verify    `verify 86958 --crc` on /models/daz_library: 6499 of 6499, 0.51 to
            0.93 s by its own timer in three runs.
  install   part 03 alone into an empty throwaway library in /tmp: 1780 files,
            241415839 bytes (`du -sb` agreed), written in 0.66 s, 0.89 s wall,
            no temporary file left; verify --crc passed.
  stopping  an invented package, a small file then a 1.5 GB entry, stopped by
            `timeout --preserve-status -s INT|TERM|HUP 0.7`: exit 130, 143 and
            129; each time the small file was recorded, the part incomplete,
            and no temporary file was left.
  selftest  67 checks passed, 4.70 s and 4.80 s wall in two runs
            (`selftest --dir`).

Exit status: 0 done; 1 a conflict, a skipped or partial package, a verify or
case-check finding, or a failed self-test check; 2 a refused path, name,
package, library or argument; 128 plus the signal number for an install
stopped by SIGINT (130), SIGTERM (143) or SIGHUP (129).
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import zipfile
import zlib
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from xml.sax.saxutils import quoteattr

ROOT = Path(__file__).resolve().parent.parent
# Daz's documented pattern text, used with fullmatch and re.ASCII so that a
# trailing newline or a non-ASCII digit does not pass
PACKAGE_RE = re.compile(r"^([A-Z][0-9A-Z]{0,6})(?=\d{8})(\d{8})(-(\d{2}))?_([0-9A-Za-z]+)\.zip$",
                        re.ASCII)
PART_OF = re.compile(r"\s*\((\d+) of (\d+)\)\s*$", re.ASCII)
SUPPORT_SKU = re.compile(r"^Runtime/Support/DAZ_3D_(\d+)_[^/]*$", re.ASCII)
RECORDS = ".daz_library"
RECORD_VERSION = 1
STANDARD = "Daz Standard License (EULA)"
INTERACTIVE = "Daz Standard License (EULA) plus an Interactive License"
EULA_URL = "https://www.daz3d.com/eula"
INTERACTIVE_URL = "https://www.daz3d.com/interactive-license-info"
NOTE = "docs/reference/daz-genesis.md"
CHUNK = 1 << 20
XML_LIMIT = 64 << 20
FREE_MARGIN = 256 << 20
TEMP_SUFFIX = ".daz_library-part"
SINGLE = "single"


class Refused(Exception):
    """A library, package, path or argument this script will not act on (exit 2)."""


# ---------------------------------------------------------------- small helpers

def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def gb(n: int) -> str:
    return f"{n / 1e9:.2f} GB"


def plural(n: int, word: str, words: str | None = None) -> str:
    return f"{n} {word if n == 1 else words or word + 's'}"


def models_dir() -> Path | None:
    """MODELS_DIR from the environment, else from .env, resolved like compose does it."""
    raw = os.environ.get("MODELS_DIR")
    if not raw:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                line = line.strip()
                if line.startswith("MODELS_DIR="):
                    raw = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not raw:
        return None
    return (ROOT / raw).resolve() if not os.path.isabs(raw) else Path(raw)


def repo_clash(path: Path) -> str | None:
    """Why `path` may not hold a library, or None. Symlinks are resolved first."""
    real = Path(os.path.realpath(path))
    repo = Path(os.path.realpath(ROOT))
    if real == repo or repo in real.parents:
        return (f"refusing {path}: it is inside this repository ({repo}). Daz content "
                "must never enter the repo; keep the library outside it.")
    if real in repo.parents:
        return (f"refusing {path}: this repository ({repo}) is inside it. Give the "
                "library a folder of its own outside the repo.")
    return None


def library_path(arg: Path | None) -> Path:
    if arg is None:
        base = models_dir()
        if base is None:
            raise Refused("MODELS_DIR is not set, and .env does not define it; "
                          "pass --library DIR")
        arg = base / "daz_library"
    lib = Path(os.path.abspath(arg))
    why = repo_clash(lib)
    if why:
        raise Refused(why)
    if os.path.lexists(lib) and not lib.is_dir():
        raise Refused(f"refusing {lib}: it exists and is not a folder")
    return lib


def unsafe(path: str) -> str | None:
    """Why a path from a manifest or a record is refused, or None."""
    if not path:
        return "an empty path"
    if "\x00" in path:
        return "a NUL character"
    if "\\" in path:
        return "a backslash, which Windows reads as a folder separator"
    if path.startswith("/"):
        return "an absolute path"
    if re.match(r"^[A-Za-z]:", path):
        return "a drive letter"
    parts = path.split("/")
    if ".." in parts:
        return 'a ".." component'
    if "." in parts or "" in parts:
        return 'an empty or "." component'
    return None


def target_rel(value: str) -> tuple[str | None, str | None]:
    """(library-relative path, None) for a manifest VALUE, or (None, why it is refused)."""
    why = unsafe(value)
    if why:
        return None, why
    if not value.startswith("Content/"):
        return None, 'not under "Content/"'
    rel = value[len("Content/"):]
    why = unsafe(rel)
    if why:
        return None, why
    if rel.split("/")[0].casefold() == RECORDS:
        return None, "inside .daz_library, where the records are kept"
    if rel.endswith(TEMP_SUFFIX):
        return None, f"a name ending in {TEMP_SUFFIX}, which this script uses for temporary files"
    return rel, None


def outside(lib_real: str, dest: Path) -> str | None:
    """Why `dest` escapes the library through a symlink already on disk, or None."""
    real = os.path.realpath(dest)
    base = lib_real.rstrip(os.sep) + os.sep
    if real != lib_real and not real.startswith(base):
        return f"it resolves to {real}, outside the library, through a symlink"
    if os.path.relpath(real, lib_real).split(os.sep)[0].casefold() == RECORDS:
        return "it resolves into .daz_library, where the records are kept, through a symlink"
    return None


def temp_path(dest: Path) -> Path:
    """The hidden name beside `dest` that a file is written to before it is renamed into place."""
    return dest.with_name("." + dest.name + TEMP_SUFFIX)


def blocked(lib: Path, rel: str) -> str | None:
    """Why a file cannot be placed at lib/rel because something else is in the way."""
    parts = rel.split("/")
    cur = lib
    for i, part in enumerate(parts[:-1]):
        cur = cur / part
        if not os.path.lexists(cur):
            return None
        if not os.path.isdir(cur):
            return f"{'/'.join(parts[:i + 1])} is a file where a folder is needed"
    dest = lib / rel
    if os.path.islink(dest):
        return "a symlink already exists at this path"
    if os.path.isdir(dest):
        return "a folder already exists at this path"
    if os.path.lexists(dest) and not os.path.isfile(dest):
        return "something other than a regular file already exists at this path"
    tmp = temp_path(dest)
    if os.path.islink(tmp):
        return f"a symlink is at its temporary name {tmp.name}"
    if os.path.lexists(tmp) and not os.path.isfile(tmp):
        return f"something other than a regular file is at its temporary name {tmp.name}"
    return None


def listed_clashes(plans: list[tuple[dict, list[dict]]]) -> list[dict]:
    """Paths listed as a file that another listed path, in any package of the run, needs as a folder."""
    files = {}
    for pkg, items in plans:
        for item in items:
            files.setdefault(item["rel"], pkg["file"])
    out = []
    for pkg, items in plans:
        for item in items:
            parts = item["rel"].split("/")
            for i in range(1, len(parts)):
                prefix = "/".join(parts[:i])
                if prefix in files:
                    out.append({"package": pkg["file"], "path": f"Content/{item['rel']}",
                                "why": f"it needs {prefix} as a folder, but {files[prefix]} "
                                       "lists that path as a file"})
                    break
    return out


def is_symlink_entry(info: zipfile.ZipInfo) -> bool:
    return info.create_system == 3 and stat.S_ISLNK(info.external_attr >> 16)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def crc32_of(path: Path) -> int:
    crc = 0
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            crc = zlib.crc32(chunk, crc)
    return crc


def same_bytes(zf: zipfile.ZipFile, info: zipfile.ZipInfo, path: Path) -> bool:
    with zf.open(info) as a, open(path, "rb") as b:
        while True:
            x = a.read(CHUNK)
            y = b.read(len(x) or CHUNK)
            if x != y:
                return False
            if not x:
                return True


def valid_date(text: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text, re.ASCII):
        raise argparse.ArgumentTypeError(f"expected a date as YYYY-MM-DD, got {text!r}")
    try:
        day = dt.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a calendar date: {text!r}") from None
    if day > dt.date.today():
        raise argparse.ArgumentTypeError(f"{text} is in the future")
    return text


def valid_sku(text: str) -> str:
    if not re.fullmatch(r"\d{1,8}", text, re.ASCII):
        raise argparse.ArgumentTypeError(f"a SKU is up to eight digits, got {text!r}")
    return str(int(text))


def valid_part(text: str) -> str:
    if not re.fullmatch(r"\d{1,2}", text, re.ASCII):
        raise argparse.ArgumentTypeError(f"a part is one or two digits, got {text!r}")
    return f"{int(text):02d}"


class Lock:
    """An exclusive, non-blocking lock on the library while it is changed."""

    def __init__(self, lib: Path):
        self.lib = lib
        self.fh = None

    def __enter__(self):
        folder = self.lib / RECORDS
        folder.mkdir(parents=True, exist_ok=True)
        self.fh = open(folder / ".lock", "a+")
        try:
            fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.fh.close()
            raise Refused(f"another daz_library.py is changing {self.lib}; "
                          "wait for it to finish") from None
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.fh, fcntl.LOCK_UN)
        self.fh.close()


STOP_SIGNALS = tuple(getattr(signal, n) for n in ("SIGINT", "SIGTERM", "SIGHUP") if hasattr(signal, n))


class Interrupted(BaseException):
    """A second SIGINT, SIGTERM or SIGHUP during an install: stop at once."""

    def __init__(self, signum: int):
        super().__init__(signal.Signals(signum).name)
        self.signum = signum


class StopRequest:
    """While installed, the first SIGINT, SIGTERM or SIGHUP only asks the install to stop at
    the next chunk; a second one raises Interrupted."""

    def __init__(self):
        self.signum: int | None = None
        self.previous: dict = {}

    @property
    def name(self) -> str | None:
        return signal.Signals(self.signum).name if self.signum else None

    def _handler(self, signum, frame):
        if self.signum is not None:
            raise Interrupted(signum)
        self.signum = signum
        print(f"{signal.Signals(signum).name} received: stopping at the current file and "
              "recording what is placed; send it again to stop at once", file=sys.stderr,
              flush=True)

    def install(self) -> None:
        for s in STOP_SIGNALS:
            self.previous[s] = signal.signal(s, self._handler)

    def restore(self) -> None:
        for s, handler in self.previous.items():
            signal.signal(s, handler)
        self.previous.clear()


@contextlib.contextmanager
def held_signals():
    """Hold SIGINT, SIGTERM and SIGHUP until the block ends, so it is never cut in two."""
    old = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)


# ---------------------------------------------------------------- records

def load_records(lib: Path) -> dict[str, dict]:
    out = {}
    folder = lib / RECORDS
    if not folder.is_dir():
        return out
    for p in sorted(folder.glob("*.json")):
        try:
            rec = json.loads(p.read_text())
        except (OSError, ValueError) as e:
            raise Refused(f"cannot read the record {p}: {e}") from None
        if not isinstance(rec, dict) or rec.get("sku") != p.stem \
                or not isinstance(rec.get("files"), dict) \
                or not isinstance(rec.get("packages"), dict):
            raise Refused(f"{p} is not a daz_library.py record for SKU {p.stem}")
        out[p.stem] = rec
    return out


def save_record(lib: Path, rec: dict) -> None:
    folder = lib / RECORDS
    folder.mkdir(parents=True, exist_ok=True)
    rec["files"] = dict(sorted(rec["files"].items()))
    rec["packages"] = dict(sorted(rec["packages"].items()))
    path = folder / f"{rec['sku']}.json"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(rec, indent=1) + "\n")
    os.replace(tmp, path)


# docs/reference/daz-genesis.md, "Shipping 3D data: the Interactive License" and "What not to do"
RENDERS = ("may ship in a game without a purchase, unless the product page says otherwise, as "
           "long as nothing shipped lets the content be extracted")
RENDERS_SOLD_STANDARD = ("no ruling covers selling standard-licence renders or sprites as a "
                         "separate in-game purchase; ask Daz first")
RENDERS_SOLD_INTERACTIVE = ("needs Daz's written consent: under the Interactive License that "
                            "covers the content's 2D derivatives too")
CONDITIONS_3D = [
    "never in native formats such as .duf or .dsf",
    "protected against extraction, by technology, asset protection, encryption or other means",
    "sold as a separate in-game purchase, itself or its 2D or 3D derivatives, only with Daz's "
    "written consent",
    "delivered through the cloud or after install only with Daz's written consent when the "
    "individual or business has annual revenue above US$1,000,000",
]
AI_STAGES = ("excluded: never give the mesh, textures or UV maps to any model, and do not feed "
             "renders to Qwen-Image, ControlNet, TRELLIS, Hunyuan3D or any training until Daz "
             "answers in writing; an Interactive License does not lift this")


def licence_block(interactive: bool, eula_read: str | None) -> dict:
    """The record's licence block. Only `interactive_license` and `eula_read` are inputs."""
    if interactive:
        mesh = ("an Interactive License is recorded (this script cannot check a purchase); the "
                "mesh, rig, morphs and textures, and FBX or glTF exported from them, may go into "
                "a build only on every condition in mesh_rig_morphs_textures_conditions")
    else:
        mesh = ("may not go into a build: that needs an Interactive License for this product, "
                "under which every condition in mesh_rig_morphs_textures_conditions applies, or a "
                "separate agreement signed by both parties")
    return {
        "held": INTERACTIVE if interactive else STANDARD,
        "interactive_license": interactive,
        "renders_and_sprites": RENDERS,
        "renders_and_sprites_sold_separately": (RENDERS_SOLD_INTERACTIVE if interactive
                                                else RENDERS_SOLD_STANDARD),
        "mesh_rig_morphs_textures": mesh,
        "mesh_rig_morphs_textures_conditions": list(CONDITIONS_3D),
        "ai_stages": AI_STAGES,
        "eula_url": EULA_URL,
        "interactive_license_url": INTERACTIVE_URL,
        "eula_read": eula_read,
        "see": f"{NOTE}, Licences",
    }


def current_licence(rec: dict) -> dict:
    """The record's licence block as this version words it, from its two inputs."""
    lic = rec.get("licence") or {}
    return licence_block(bool(lic.get("interactive_license")), lic.get("eula_read"))


def licence_lines(rec: dict) -> list[str]:
    lic = current_licence(rec)
    name = rec.get("product_name") or "product name not recorded"

    def para(text: str, indent: str = "  ", later: str | None = None) -> list[str]:
        return textwrap.wrap(text, 96, initial_indent=indent,
                             subsequent_indent=later if later is not None else indent)

    out = [f"Licence for SKU {rec['sku']} ({name}): {lic['held']}"]
    if lic["interactive_license"]:
        out += para(f"Renders and sprites made from this content {RENDERS}. Selling them as a "
                    "separate in-game purchase needs Daz's written consent (condition 3).")
        out += para("An Interactive License is recorded for this product (this script cannot "
                    "check a purchase). Under it, the mesh, rig, morphs and textures, and FBX or "
                    "glTF exported from them, may go into a build only on all of these "
                    "conditions:")
    else:
        out += para(f"Renders and sprites made from this content {RENDERS}. No ruling covers "
                    "selling standard-licence renders or sprites as a separate in-game purchase; "
                    "ask Daz first.")
        out += para("The mesh, rig, morphs and textures, and FBX or glTF exported from them, may "
                    "NOT go into a build without an Interactive License for this product or a "
                    "separate agreement signed by both parties. Under an Interactive License "
                    "they may go into a build only on all of these conditions:")
    for i, cond in enumerate(CONDITIONS_3D, 1):
        out += para(f"{cond[0].upper()}{cond[1:]}.", f"    {i}. ", "       ")
    out += para("Keep Daz content out of the AI stages: never give its mesh, textures or UV maps "
                "to any model, and do not feed its renders to Qwen-Image, ControlNet, TRELLIS, "
                "Hunyuan3D or any training until Daz answers in writing. An Interactive License "
                "does not lift that.")
    out += [f"  EULA {lic['eula_url']}, last read: "
            + (lic["eula_read"] or "not recorded (pass --eula-read YYYY-MM-DD after reading it)"),
            f"  Interactive License {lic['interactive_license_url']}",
            f"  From {NOTE}, \"Licences\"; not legal advice."]
    return out


# ---------------------------------------------------------------- packages

def read_xml(zf: zipfile.ZipFile, name: str, where: Path) -> ET.Element:
    info = zf.getinfo(name)
    if info.file_size > XML_LIMIT:
        raise Refused(f"refusing {where}: {name} is {info.file_size} bytes, over the "
                      f"{XML_LIMIT} byte limit")
    try:
        data = zf.read(info)
    except (zipfile.BadZipFile, zlib.error, EOFError, OSError, ValueError) as e:
        raise Refused(f"refusing {where}: cannot read {name} from the zip ({e})") from None
    try:
        return ET.fromstring(data)
    except ET.ParseError as e:
        raise Refused(f"refusing {where}: {name} is not well-formed XML ({e})") from None


def open_package(path: Path) -> dict:
    """Read a package's name, Manifest.dsx and Supplement.dsx. Raises Refused."""
    m = PACKAGE_RE.fullmatch(path.name)
    if not m:
        raise Refused(f"refusing {path}: the name does not match Daz's package pattern "
                      "<prefix><8-digit SKU>[-<2-digit part>]_<Name>.zip")
    if not path.is_file():
        raise Refused(f"refusing {path}: not a file")
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError, ValueError, EOFError) as e:
        raise Refused(f"refusing {path}: not a readable zip ({e})") from None
    try:
        infos = zf.infolist()
        by_name: dict[str, list[zipfile.ZipInfo]] = {}
        for info in infos:
            by_name.setdefault(info.filename, []).append(info)
            if not info.flag_bits & 0x800 and not info.filename.isascii():
                try:     # a name zipfile read as cp437 may be UTF-8 without the flag
                    alt = info.filename.encode("cp437").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    alt = None
                if alt and alt != info.filename:
                    by_name.setdefault(alt, []).append(info)
        if "Manifest.dsx" not in by_name:
            raise Refused(f"refusing {path}: no Manifest.dsx at the root of the zip")
        root = read_xml(zf, "Manifest.dsx", path)
        if root.tag != "DAZInstallManifest":
            raise Refused(f"refusing {path}: Manifest.dsx's root element is <{root.tag}>, "
                          "not <DAZInstallManifest>")
        gid_el = root.find("GlobalID")
        gid = gid_el.get("VALUE") if gid_el is not None else None
        if not gid:
            raise Refused(f"refusing {path}: Manifest.dsx has no GlobalID VALUE")
        values, others, twice = [], {}, 0
        seen = set()
        for el in root.findall("File"):
            target, action, value = el.get("TARGET"), el.get("ACTION"), el.get("VALUE")
            if target == "Content" and action == "Install" and value is not None:
                if value in seen:
                    twice += 1
                    continue
                seen.add(value)
                values.append(value)
            else:
                key = f"TARGET={target!r} ACTION={action!r}"
                others[key] = others.get(key, 0) + 1
        product = None
        if "Supplement.dsx" in by_name:
            sup = read_xml(zf, "Supplement.dsx", path)
            el = sup.find("ProductName")
            product = el.get("VALUE") if el is not None else None
        part = m.group(4)
        of = PART_OF.search(product or "")
        if part and of and int(of.group(1)) != int(part):
            raise Refused(f"refusing {path}: the name gives part {part} but Supplement.dsx "
                          f"says {product!r}; was the zip renamed?")
        sku = str(int(m.group(2)))
        named = {str(int(s.group(1))) for v in values
                 if (s := SUPPORT_SKU.match(v[len("Content/"):] if v.startswith("Content/")
                                            else v))}
        if named and sku not in named:
            raise Refused(f"refusing {path}: the name gives SKU {sku} but Manifest.dsx lists "
                          f"Runtime/Support/DAZ_3D_{sorted(named)[0]}_... files; was the zip "
                          "renamed?")
        listed = set(values)
        unlisted = sum(1 for i in infos if not i.is_dir()
                       and i.filename not in ("Manifest.dsx", "Supplement.dsx")
                       and i.filename not in listed)
    except Refused:
        zf.close()
        raise
    except (zipfile.BadZipFile, zlib.error, EOFError, OSError, ValueError) as e:
        zf.close()
        raise Refused(f"refusing {path}: not a readable zip ({e})") from None
    return {"path": path, "file": path.name, "zip": zf, "entries": by_name,
            "prefix": m.group(1), "sku": sku, "sku8": m.group(2),
            "part": part or SINGLE, "global_id": gid, "product": product,
            "product_base": PART_OF.sub("", product) if product else None,
            "parts_total": int(of.group(2)) if of else None,
            "values": values, "listed_twice": twice, "other_files": others,
            "unlisted_entries": unlisted}


def safety_plan(pkg: dict, lib: Path) -> tuple[list[dict], list[dict]]:
    """(items, refusals) for one package, from names and the disk, reading no file data."""
    lib_real = os.path.realpath(lib)
    items, refusals = [], []
    for value in pkg["values"]:
        rel, why = target_rel(value)
        info = None
        if not why:
            found = pkg["entries"].get(value, [])
            if not found:
                why = "listed in Manifest.dsx but not in the zip"
            elif len(found) > 1:
                why = "the zip holds this name more than once"
            else:
                info = found[0]
                if info.is_dir():
                    why = "a folder entry in the zip, not a file"
                elif is_symlink_entry(info):
                    why = "stored in the zip as a symlink"
        if not why:
            why = outside(lib_real, lib / rel) or blocked(lib, rel)
        if why:
            refusals.append({"package": pkg["file"], "path": value, "why": why})
        else:
            items.append({"rel": rel, "info": info})
    return items, refusals


def case_twins(lib: Path, rels: list[str], limit: int = 5) -> tuple[int, list[list[str]]]:
    """New paths that differ only in case from each other or from what is on disk."""
    listings: dict[Path, list[str]] = {}
    spelled: dict[str, str] = {}
    found: set[tuple[str, str]] = set()
    for rel in rels:
        parts = rel.split("/")
        cur, on_disk = lib, True
        for i, part in enumerate(parts):
            prefix = "/".join(parts[:i + 1])
            first = spelled.setdefault(prefix.casefold(), prefix)
            if first != prefix:
                found.add(tuple(sorted((first, prefix))))
            if on_disk:
                if cur not in listings:
                    try:
                        listings[cur] = os.listdir(cur)
                    except OSError:
                        listings[cur] = []
                names = listings[cur]
                if part in names:
                    cur = cur / part
                    continue
                twin = next((n for n in names if n.casefold() == part.casefold()), None)
                if twin is not None:
                    found.add(tuple(sorted(("/".join(parts[:i] + [twin]), prefix))))
                on_disk = False
    # a clash at data/DAZ 3D makes every path below it clash too; keep the topmost
    top = sorted(found, key=lambda p: (p[0].count("/"), p))
    kept: list[tuple[str, str]] = []
    for a, b in top:
        if not any(a.casefold().startswith(k[0].casefold() + "/") for k in kept):
            kept.append((a, b))
    return len(kept), [list(k) for k in kept[:limit]]


def compare(pkg: dict, items: list[dict], lib: Path) -> None:
    """Set each item's action: write, identical or conflict. Reads files of equal size."""
    zf = pkg["zip"]
    for item in items:
        dest = lib / item["rel"]
        if not os.path.lexists(dest):
            item["action"] = "write"
        elif os.path.getsize(dest) == item["info"].file_size \
                and same_bytes(zf, item["info"], dest):
            item["action"] = "identical"
        else:
            item["action"] = "conflict"


def open_temp(tmp: Path) -> int:
    """Create `tmp` for writing, never following or reusing what is there. A regular file left
    by an interrupted run is removed first; anything else raises FileExistsError."""
    try:
        st = os.lstat(tmp)
    except FileNotFoundError:
        st = None
    if st is not None:
        if not stat.S_ISREG(st.st_mode):
            raise FileExistsError(f"something other than a regular file is at the temporary "
                                  f"name {tmp.name}")
        os.unlink(tmp)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    return os.open(tmp, flags, 0o666)


def install_items(pkg: dict, items: list[dict], lib: Path, placed: list[dict],
                  stop: StopRequest) -> str | None:
    """Write every write or conflict item, appending each one to `placed` as it lands.

    Returns None, or why the package stopped: any Exception while writing, or a stop request
    from the first signal. Interrupted (a second signal) removes the temporary file and is
    raised; the caller still records `placed`."""
    zf = pkg["zip"]
    for item in items:
        if item["action"] == "identical":
            continue
        if stop.signum:
            return f"{stop.name} received before {item['rel']}"
        dest = lib / item["rel"]
        tmp = temp_path(dest)
        created = False
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            fd = open_temp(tmp)
            created = True
            with os.fdopen(fd, "wb") as out, zf.open(item["info"]) as src:
                while chunk := src.read(CHUNK):
                    out.write(chunk)
                    if stop.signum:
                        break
            if stop.signum:
                os.unlink(tmp)
                created = False
                return (f"{stop.name} received while writing {item['rel']}; its temporary file "
                        "was removed")
            with held_signals():
                os.replace(tmp, dest)
                created = False
                placed.append(item)
        except BaseException as e:
            if created:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            if not isinstance(e, Exception):
                raise
            return f"stopped at {item['rel']}: {type(e).__name__}: {e}"
    return None


def merge_record(rec: dict | None, pkg: dict, items: list[dict], placed: list[dict],
                 complete: bool, counts: dict, sha: str, size: int, args) -> dict:
    stamp = now()
    if rec is None:
        rec = {"record_version": RECORD_VERSION, "sku": pkg["sku"], "store_prefix": pkg["prefix"],
               "product_name": pkg["product_base"], "global_id": pkg["global_id"],
               "parts_total": pkg["parts_total"], "created_at": stamp, "updated_at": stamp,
               "packages": {}, "files": {},
               "licence": licence_block(bool(args.interactive_license), args.eula_read),
               "written_by": "scripts/daz_library.py"}
    else:
        held = rec.get("licence") or {}
        rec["licence"] = licence_block(bool(args.interactive_license
                                            or held.get("interactive_license")),
                                       args.eula_read or held.get("eula_read"))
        rec["product_name"] = rec.get("product_name") or pkg["product_base"]
        rec["parts_total"] = rec.get("parts_total") or pkg["parts_total"]
        rec["updated_at"] = stamp
    placed_ids = {id(i) for i in placed}
    recorded = [i for i in items if i["action"] == "identical" or id(i) in placed_ids]
    for item in recorded:
        info = item["info"]
        entry = rec["files"].setdefault(item["rel"], {"size": info.file_size, "parts": []})
        entry["size"] = info.file_size
        entry["crc32"] = f"{info.CRC:08x}"
        if pkg["part"] not in entry["parts"]:
            entry["parts"] = sorted(entry["parts"] + [pkg["part"]])
    prev = rec["packages"].get(pkg["part"]) or {}
    same = prev.get("sha256") == sha and prev.get("complete") and complete
    rec["packages"][pkg["part"]] = {
        "file": pkg["file"], "product_name": pkg["product"], "sha256": sha, "size": size,
        "installed_at": prev.get("installed_at", stamp) if same else stamp,
        "last_run_at": stamp, "complete": complete, "listed": len(items),
        "recorded": len(recorded), "last_run": counts,
        "bytes_listed": sum(i["info"].file_size for i in items),
        "unlisted_zip_entries": pkg["unlisted_entries"],
        "other_manifest_files": pkg["other_files"]}
    return rec


# ---------------------------------------------------------------- commands

def emit(args, obj: dict, lines: list[str]) -> None:
    if args.json:
        print(json.dumps(obj, indent=1))
    elif lines:
        print("\n".join(lines))


def plan_install(pkgs: list[dict], lib: Path) -> tuple[dict, list, list[dict], list[str]]:
    """(records, plans, refused paths, refusal messages) for a run, from the library as it is."""
    records = load_records(lib) if lib.is_dir() else {}
    messages: list[str] = []
    by_part: dict[tuple[str, str], list[dict]] = {}
    for p in pkgs:
        by_part.setdefault((p["sku"], p["part"]), []).append(p)
    for (sku, part), group in by_part.items():
        if len(group) > 1:
            messages.append(f"refusing {', '.join(p['file'] for p in group)}: two zips for "
                            f"SKU {sku} part {part}")
    for sku in sorted({p["sku"] for p in pkgs}):
        gids = {p["global_id"] for p in pkgs if p["sku"] == sku}
        if len(gids) > 1:
            messages.append(f"refusing the SKU {sku} zips: they carry different GlobalIDs "
                            f"({', '.join(sorted(gids))})")
        rec = records.get(sku)
        if rec and rec.get("global_id") not in gids:
            messages.append(f"refusing the SKU {sku} zips: GlobalID {sorted(gids)[0]} differs "
                            f"from the {rec.get('global_id')} recorded for SKU {sku}")
        for other, orec in records.items():
            if other != sku and orec.get("global_id") in gids:
                messages.append(f"refusing the SKU {sku} zips: GlobalID "
                                f"{orec.get('global_id')} is recorded for SKU {other}")
    plans, refusals = [], []
    for p in pkgs:
        items, refused = safety_plan(p, lib)
        refusals += refused
        plans.append((p, items))
    refusals += listed_clashes(plans)
    messages += [f"refusing {r['package']}: {r['path']}: {r['why']}" for r in refusals]
    return records, plans, refusals, messages


def record_run(lib: Path, records: dict, pkg: dict, items: list[dict], placed: list[dict],
               complete: bool, identical: int, sha: str, size: int, args) -> dict:
    """Merge one package's run into its SKU's record and save it, with signals held."""
    done = {"written": sum(1 for i in placed if i["action"] == "write"),
            "replaced": sum(1 for i in placed if i["action"] == "conflict"),
            "identical": identical}
    with held_signals():
        rec = merge_record(records.get(pkg["sku"]), pkg, items, list(placed), complete, done,
                           sha, size, args)
        save_record(lib, rec)
        records[pkg["sku"]] = rec
    return done


def cmd_install(args, lib: Path) -> int:
    pkgs, opened = [], []
    for z in args.zips:
        try:
            pkgs.append(open_package(Path(z)))
        except Refused as e:
            opened.append(str(e))

    def refuse(messages: list[str], refusals: list[dict]) -> int:
        for p in pkgs:
            p["zip"].close()
        for msg in messages:
            print(msg, file=sys.stderr)
        print("nothing was installed", file=sys.stderr)
        if args.json:
            print(json.dumps({"library": str(lib), "installed": False, "errors": messages,
                              "refused_paths": refusals}, indent=1))
        return 2

    # Plan before the lock only when refusing now spares creating the library or its lock
    # file, or when a package is refused already; an install plans again inside the lock.
    records, plans, refusals, messages = {}, [], [], []
    if args.dry_run or opened or not (lib / RECORDS / ".lock").is_file():
        try:
            records, plans, refusals, messages = plan_install(pkgs, lib)
        except BaseException:
            for p in pkgs:
                p["zip"].close()
            raise
        if opened or messages:
            return refuse(opened + messages, refusals)

    results, lines, status = [], [], 0
    touched: list[str] = []
    stop = StopRequest()

    def flush():
        if not args.json and lines:
            print("\n".join(lines), flush=True)
            lines.clear()

    lock = None
    try:
        if not args.dry_run:
            lib.mkdir(parents=True, exist_ok=True)
            lock = Lock(lib)
            lock.__enter__()
            records, plans, refusals, messages = plan_install(pkgs, lib)
            if messages:
                return refuse(messages, refusals)
            stop.install()
        for pkg, items in sorted(plans, key=lambda t: (t[0]["sku"], t[0]["part"])):
            flush()
            res = {"file": pkg["file"], "sku": pkg["sku"], "part": pkg["part"],
                   "product_name": pkg["product"], "global_id": pkg["global_id"],
                   "listed": len(items), "listed_twice": pkg["listed_twice"],
                   "other_manifest_files": pkg["other_files"],
                   "unlisted_zip_entries": pkg["unlisted_entries"]}
            head = (f"{pkg['file']}  (SKU {pkg['sku']}, part {pkg['part']}, "
                    f"{pkg['product'] or 'no Supplement.dsx product name'})")
            lines.append(head)
            if stop.signum:
                res["status"] = "not_started"
                lines.append(f"  not started: {stop.name} was received")
                results.append(res)
                continue
            started = time.monotonic()
            size = pkg["path"].stat().st_size
            sha = sha256_of(pkg["path"])
            res.update(sha256=sha, size=size, sha256_seconds=round(time.monotonic() - started, 2))
            lines.append(f"  zip {size} bytes, sha256 {sha} ({res['sha256_seconds']:.2f} s)")
            flush()
            try:
                t0 = time.monotonic()
                compare(pkg, items, lib)
                res["compare_seconds"] = round(time.monotonic() - t0, 2)
            except Exception as e:
                res["status"] = "unreadable"
                res["error"] = f"{type(e).__name__}: {e}"
                lines.append(f"  not installed: comparing with the library failed ({res['error']})")
                status = max(status, 1)
                results.append(res)
                continue
            counts = {a: sum(1 for i in items if i["action"] == a)
                      for a in ("write", "identical", "conflict")}
            conflicts = [i["rel"] for i in items if i["action"] == "conflict"]
            n_twins, twins = case_twins(lib, [i["rel"] for i in items if i["action"] == "write"])
            res.update(to_write=counts["write"], identical=counts["identical"],
                       conflicts=counts["conflict"], conflict_examples=conflicts[:args.examples],
                       case_twins=n_twins, case_twin_examples=twins)
            need = sum(i["info"].file_size for i in items if i["action"] != "identical")
            lines.append(f"  {len(items)} files for Content ({gb(sum(i['info'].file_size for i in items))}): "
                         f"{counts['write']} new, {counts['identical']} identical, "
                         f"{counts['conflict']} differing")
            if pkg["other_files"] or pkg["unlisted_entries"] or pkg["listed_twice"]:
                lines.append(f"  left alone: {pkg['unlisted_entries']} zip entries the manifest "
                             f"does not list, {sum(pkg['other_files'].values())} File elements "
                             f"with another TARGET or ACTION, {pkg['listed_twice']} listed twice")
            if n_twins:
                lines.append(f"  warning: {plural(n_twins, 'new path')} differ only in case from "
                             "another path; run case-check. For example:")
                lines += [f"    {a}  |  {b}" for a, b in twins]
            if conflicts:
                verb = "will be replaced" if args.overwrite else "blocks the install"
                lines.append(f"  {plural(len(conflicts), 'file')} already in the library "
                             f"with different bytes; each {verb}:")
                owners = {r: [s for s, rec in records.items() if r in rec["files"]]
                          for r in conflicts[:args.examples]}
                lines += [f"    {r}" + (f"  (recorded for SKU {', '.join(owners[r])})"
                                        if owners[r] else "") for r in conflicts[:args.examples]]
                if len(conflicts) > args.examples:
                    lines.append(f"    ... and {len(conflicts) - args.examples} more")
            if args.dry_run:
                res["status"] = "planned"
                lines.append(f"  dry run: {counts['write'] + (counts['conflict'] if args.overwrite else 0)}"
                             f" files would be written ({gb(need)})")
                if conflicts and not args.overwrite:
                    status = max(status, 1)
                results.append(res)
                continue
            if conflicts and not args.overwrite:
                res["status"] = "conflicts"
                lines.append("  not installed: nothing from this package was written; "
                             "pass --overwrite to replace the differing files")
                status = max(status, 1)
                results.append(res)
                continue
            free = shutil.disk_usage(lib).free
            if need + FREE_MARGIN > free:
                res["status"] = "no_space"
                lines.append(f"  not installed: it needs {gb(need)} and {lib} has {gb(free)} "
                             f"free, less a {gb(FREE_MARGIN)} margin")
                status = max(status, 1)
                results.append(res)
                continue
            if stop.signum:
                res["status"] = "not_started"
                lines.append(f"  not installed: {stop.name} was received before writing")
                results.append(res)
                continue
            flush()
            placed: list[dict] = []
            started = time.monotonic()
            try:
                error = install_items(pkg, items, lib, placed, stop)
            except BaseException as e:
                record_run(lib, records, pkg, items, placed, False, counts["identical"], sha,
                           size, args)
                flush()
                print(f"{pkg['file']}: stopped at once ({type(e).__name__}: {e}); the "
                      f"{plural(len(placed), 'file')} placed are recorded with complete: false in "
                      f"{lib / RECORDS / (pkg['sku'] + '.json')}", file=sys.stderr, flush=True)
                raise
            seconds = time.monotonic() - started
            done = record_run(lib, records, pkg, items, placed, error is None,
                              counts["identical"], sha, size, args)
            if pkg["sku"] not in touched:
                touched.append(pkg["sku"])
            written_bytes = sum(i["info"].file_size for i in placed)
            state = "installed" if error is None else "interrupted" if stop.signum else "partial"
            res.update(done, bytes_written=written_bytes, install_seconds=round(seconds, 2),
                       status=state, error=error)
            lines.append(f"  installed: {done['written']} written, {done['replaced']} replaced, "
                         f"{done['identical']} identical skipped; {gb(written_bytes)} in "
                         f"{seconds:.2f} s")
            if error:
                lines.append(f"  {state.upper()}: {error}")
                lines.append(f"  the {plural(len(placed), 'file')} placed before it are recorded "
                             "with complete: false; "
                             + ("install it again to finish" if stop.signum else
                                "fix or download the zip again and reinstall"))
                status = max(status, 1)
            results.append(res)
    finally:
        stop.restore()
        for p in pkgs:
            p["zip"].close()
        if lock and lock.fh is not None and not lock.fh.closed:
            lock.__exit__(None, None, None)
    if stop.signum:
        status = 128 + stop.signum
        lines.append(f"stopped by {stop.name}: install again to finish")
    flush()
    if touched:
        lines.append(f"record: {lib / RECORDS}")
        for sku in touched:
            lines += [""] + licence_lines(records[sku])
    obj = {"library": str(lib), "dry_run": args.dry_run, "packages": results,
           "licences": {s: current_licence(records[s]) for s in touched}}
    if stop.signum:
        obj["stopped_by"] = stop.name
    emit(args, obj, lines)
    return status


def product_summary(rec: dict) -> dict:
    parts = sorted(rec["packages"])
    return {"sku": rec["sku"], "product_name": rec.get("product_name"),
            "global_id": rec.get("global_id"), "parts": parts,
            "parts_total": rec.get("parts_total"),
            "incomplete_parts": [p for p in parts if not rec["packages"][p].get("complete")],
            "files": len(rec["files"]), "bytes": sum(f["size"] for f in rec["files"].values()),
            "licence": rec["licence"]["held"], "eula_read": rec["licence"].get("eula_read"),
            "created_at": rec.get("created_at"), "updated_at": rec.get("updated_at")}


def cmd_list(args, lib: Path) -> int:
    records = load_records(lib)
    rows = [product_summary(r) for r in records.values()]
    lines = [f"Daz library {lib}"]
    if not rows:
        lines.append("  no products recorded" + ("" if lib.is_dir() else " (the folder does not exist)"))
    for r in rows:
        of = f" of {r['parts_total']}" if r["parts_total"] else ""
        lines += [f"SKU {r['sku']}  {r['product_name'] or '(no product name)'}",
                  f"  parts {', '.join(r['parts'])}{of}"
                  + (f"; incomplete: {', '.join(r['incomplete_parts'])}" if r["incomplete_parts"] else ""),
                  f"  {r['files']} files, {r['bytes']} bytes ({gb(r['bytes'])})",
                  f"  licence: {r['licence']}; EULA last read: {r['eula_read'] or 'not recorded'}",
                  f"  installed {r['created_at']}, updated {r['updated_at']}"]
    if rows:
        lines += ["Renders and sprites may ship on conditions. The mesh, rig, morphs and textures need an",
                  "Interactive License, and conditions still apply under it. Keep Daz content out of the",
                  f"AI stages. `licence SKU` gives the conditions ({NOTE})."]
    emit(args, {"library": str(lib), "products": rows}, lines)
    return 0


def cmd_licence(args, lib: Path) -> int:
    changing = args.interactive_license or args.standard_license or args.eula_read
    if changing:
        if not (lib / RECORDS).is_dir():
            raise Refused(f"no record for SKU {args.sku} in {lib}")
        with Lock(lib):
            records = load_records(lib)
            rec = records.get(args.sku)
            if rec is None:
                raise Refused(f"no record for SKU {args.sku} in {lib}")
            interactive = rec["licence"]["interactive_license"]
            if args.interactive_license:
                interactive = True
            if args.standard_license:
                interactive = False
            read = args.eula_read or rec["licence"].get("eula_read")
            rec["licence"] = licence_block(interactive, read)
            rec["updated_at"] = now()
            save_record(lib, rec)
    else:
        rec = load_records(lib).get(args.sku)
        if rec is None:
            raise Refused(f"no record for SKU {args.sku} in {lib}")
    emit(args, {"sku": rec["sku"], "licence": current_licence(rec)}, licence_lines(rec))
    return 0


def cmd_verify(args, lib: Path) -> int:
    records = load_records(lib)
    if args.sku and args.sku not in records:
        raise Refused(f"no record for SKU {args.sku} in {lib}")
    skus = [args.sku] if args.sku else sorted(records)
    out, lines, status = [], [f"Verify {lib}"], 0
    started = time.monotonic()
    for sku in skus:
        rec = records[sku]
        problems = {"missing": [], "not_a_file": [], "wrong_size": [], "wrong_crc": [],
                    "unsafe_path": []}
        for rel, f in rec["files"].items():
            why = unsafe(rel)
            if why:
                problems["unsafe_path"].append(rel)
                continue
            path = lib / rel
            try:
                st = os.lstat(path)     # a symlink is not a file this script placed
            except FileNotFoundError:
                problems["missing"].append(rel)
                continue
            except OSError:
                problems["not_a_file"].append(rel)
                continue
            if not stat.S_ISREG(st.st_mode):
                problems["not_a_file"].append(rel)
            elif st.st_size != f["size"]:
                problems["wrong_size"].append(rel)
            elif args.crc and f.get("crc32") and f"{crc32_of(path):08x}" != f["crc32"]:
                problems["wrong_crc"].append(rel)
        bad = sum(len(v) for v in problems.values())
        status = 1 if bad else status
        incomplete = [p for p, pk in rec["packages"].items() if not pk.get("complete")]
        if incomplete:
            status = 1
        out.append({"sku": sku, "files": len(rec["files"]), "ok": len(rec["files"]) - bad,
                    "crc_checked": bool(args.crc), "incomplete_parts": incomplete,
                    **{k: len(v) for k, v in problems.items()},
                    "examples": {k: v[:args.examples] for k, v in problems.items() if v}})
        lines.append(f"SKU {sku}: {len(rec['files']) - bad} of {len(rec['files'])} files present "
                     f"at their recorded size{' and CRC-32' if args.crc else ''}")
        for k, v in problems.items():
            if v:
                lines.append(f"  {k.replace('_', ' ')}: {len(v)}")
                lines += [f"    {r}" for r in v[:args.examples]]
        if incomplete:
            lines.append(f"  incomplete parts, recorded after a stopped install: {', '.join(incomplete)}")
    seconds = round(time.monotonic() - started, 2)
    lines.append(f"{seconds:.2f} s")
    if not skus:
        lines.insert(1, "  no products recorded")
    emit(args, {"library": str(lib), "products": out, "seconds": seconds}, lines)
    return status


def cmd_uninstall(args, lib: Path) -> int:
    if not (lib / RECORDS).is_dir():
        raise Refused(f"no record for SKU {args.sku} in {lib}")
    with Lock(lib):
        records = load_records(lib)
        rec = records.get(args.sku)
        if rec is None:
            raise Refused(f"no record for SKU {args.sku} in {lib}")
        if args.part and args.part not in rec["packages"]:
            raise Refused(f"SKU {args.sku} has no recorded part {args.part}; recorded: "
                          f"{', '.join(sorted(rec['packages']))}")
        lib_real = os.path.realpath(lib)
        others = {rel for s, r in records.items() if s != args.sku for rel in r["files"]}
        remove, kept_other_sku, kept_other_part, missing, changed = [], [], [], [], []
        for rel, f in rec["files"].items():
            if args.part:
                if args.part not in f["parts"]:
                    continue
                if len(f["parts"]) > 1:
                    kept_other_part.append(rel)
                    continue
            if rel in others:
                kept_other_sku.append(rel)
                continue
            why = unsafe(rel) or outside(lib_real, lib / rel)
            if why:
                raise Refused(f"refusing to uninstall: the record lists {rel!r}: {why}")
            path = lib / rel
            if not os.path.lexists(path):
                missing.append(rel)
            elif os.path.islink(path) or not os.path.isfile(path) \
                    or os.path.getsize(path) != f["size"]:
                changed.append(rel)
                remove.append(rel)
            else:
                remove.append(rel)
        res = {"library": str(lib), "sku": args.sku, "part": args.part, "dry_run": args.dry_run,
               "remove": len(remove), "kept_recorded_by_another_sku": len(kept_other_sku),
               "kept_recorded_by_another_part": len(kept_other_part),
               "already_missing": len(missing), "changed_since_install": len(changed),
               "examples": {"kept_recorded_by_another_sku": kept_other_sku[:args.examples],
                            "kept_recorded_by_another_part": kept_other_part[:args.examples],
                            "changed_since_install": changed[:args.examples]}}
        what = f"SKU {args.sku}" + (f" part {args.part}" if args.part else "")
        lines = [f"Uninstall {what} from {lib}",
                 f"  {len(remove)} files to remove, {len(missing)} already missing",
                 f"  kept: {len(kept_other_part)} also recorded by another part, "
                 f"{len(kept_other_sku)} also recorded by another SKU"]
        lines += [f"    {r}" for r in (kept_other_part + kept_other_sku)[:args.examples]]
        if changed and not args.force:
            lines.append(f"  {plural(len(changed), 'file')} no longer match the recorded size or "
                         "are not regular files, so nothing was removed; run verify, then "
                         "uninstall --force to remove them anyway:")
            lines += [f"    {r}" for r in changed[:args.examples]]
            res["removed"] = 0
            emit(args, res, lines)
            return 1
        if args.dry_run:
            lines.append("  dry run: nothing removed")
            lines += [f"    would remove {r}" for r in remove[:args.examples]]
            emit(args, res, lines)
            return 0
        started = time.monotonic()
        folders, removed, failed, failed_rels = set(), 0, [], set()
        for rel in remove:
            try:
                os.unlink(lib / rel)
                removed += 1
            except FileNotFoundError:
                pass
            except OSError as e:
                failed.append(f"{rel}: {e.strerror or e}")
                failed_rels.add(rel)
                continue
            folders.add((lib / rel).parent)
        pruned = 0
        for folder in sorted(folders, key=lambda p: len(p.parts), reverse=True):
            cur = folder
            while cur != lib and lib in cur.parents and cur.name != RECORDS:
                try:
                    os.rmdir(cur)
                    pruned += 1
                except OSError:
                    break
                cur = cur.parent
        gone = (set(remove) - failed_rels) | set(missing)
        for rel in list(rec["files"]):
            f = rec["files"][rel]
            if rel in failed_rels:
                continue
            if args.part:
                if args.part in f["parts"]:
                    f["parts"].remove(args.part)
                if not f["parts"]:
                    del rec["files"][rel]
            elif rel in gone or rel in kept_other_sku:
                del rec["files"][rel]
        leftover = [r for r in rec["files"] if not args.part]
        if args.part:
            del rec["packages"][args.part]
        else:
            rec["packages"] = {}
        record_path = lib / RECORDS / f"{args.sku}.json"
        if not rec["packages"] and not leftover and not failed:
            record_path.unlink()
            lines.append(f"  record {record_path} removed")
        else:
            rec["updated_at"] = now()
            save_record(lib, rec)
            lines.append(f"  record {record_path} updated")
        seconds = round(time.monotonic() - started, 2)
        res.update(removed=removed, folders_removed=pruned, failed=failed, seconds=seconds)
        lines.insert(len(lines) - 1, f"  removed {removed} files and {pruned} folders that ended "
                                     f"up empty in {seconds:.2f} s")
        lines += [f"  could not remove {f}" for f in failed[:args.examples]]
        emit(args, res, lines)
        return 1 if failed else 0


def read_json_doc(path: Path):
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8-sig"))


def find_casefold(root: Path, parts: list[str], listings: dict) -> str | None:
    """The on-disk spelling of root/parts matched without regard to case, or None."""
    frontier = [(root, [])]
    for part in parts:
        want, nxt = part.casefold(), []
        for cur, spelled in frontier:
            if cur not in listings:
                try:
                    listings[cur] = os.listdir(cur)
                except OSError:
                    listings[cur] = []
            nxt += [(cur / n, spelled + [n]) for n in listings[cur] if n.casefold() == want]
        if not nxt:
            return None
        frontier = nxt
    return "/".join(frontier[0][1])


def cmd_case_check(args, lib: Path) -> int:
    if not lib.is_dir():
        raise Refused(f"no library at {lib}")
    started = time.monotonic()
    # (1) names in one folder that differ only in case
    folders_with_twins, twin_examples, twin_names = 0, [], 0
    doc_files = []
    for dirpath, dirnames, filenames in os.walk(lib):
        here = Path(dirpath)
        if here == lib:
            dirnames[:] = [d for d in dirnames if d != RECORDS]
        groups: dict[str, list[str]] = {}
        for n in dirnames + filenames:
            groups.setdefault(n.casefold(), []).append(n)
        clashes = [sorted(g) for g in groups.values() if len(g) > 1]
        if clashes:
            folders_with_twins += 1
            twin_names += sum(len(c) for c in clashes)
            rel = here.relative_to(lib).as_posix()
            for c in clashes:
                if len(twin_examples) < args.examples:
                    twin_examples.append({"folder": "" if rel == "." else rel, "names": c})
        doc_files += [here / f for f in sorted(filenames)
                      if f.lower().endswith((".dsf", ".duf"))]
    disk_seconds = round(time.monotonic() - started, 2)

    # (2) references inside .dsf and .duf files
    tops = {n.casefold() for n in os.listdir(lib) if n != RECORDS and (lib / n).is_dir()}
    listings: dict[Path, list[str]] = {}
    resolved: dict[str, tuple[str, str | None]] = {}
    refs_total, unreadable, unreadable_examples = 0, 0, []
    per_target: dict[str, dict] = {}
    t0 = time.monotonic()
    for path in doc_files:
        try:
            doc = read_json_doc(path)
        except (OSError, ValueError, EOFError, UnicodeDecodeError, RecursionError,
                zlib.error, gzip.BadGzipFile) as e:
            unreadable += 1
            if len(unreadable_examples) < args.examples:
                unreadable_examples.append(f"{path.relative_to(lib).as_posix()}: "
                                           f"{type(e).__name__}")
            continue
        seen_here = set()
        stack = [doc]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                stack.extend(v for v in x.values() if isinstance(v, (dict, list, str)))
            elif isinstance(x, list):
                stack.extend(v for v in x if isinstance(v, (dict, list, str)))
            elif x[:1] == "/":
                target = unquote(x.split("#", 1)[0].split("?", 1)[0])[1:]
                if not target or target.split("/", 1)[0].casefold() not in tops \
                        or "." not in target.rsplit("/", 1)[-1]:
                    continue
                refs_total += 1
                if target not in resolved:
                    parts = target.split("/")
                    if "\x00" in target or any(p in ("", ".", "..") for p in parts):
                        resolved[target] = ("missing", None)
                    elif os.path.exists(lib / target):
                        resolved[target] = ("exact", target)
                    else:
                        spelled = find_casefold(lib, parts, listings)
                        resolved[target] = ("case_only", spelled) if spelled else ("missing", None)
                slot = per_target.setdefault(target, {"files": 0, "example_file": None})
                if target not in seen_here:
                    seen_here.add(target)
                    slot["files"] += 1
                    slot["example_file"] = slot["example_file"] or path.relative_to(lib).as_posix()
    ref_seconds = round(time.monotonic() - t0, 2)
    kinds = {"exact": [], "case_only": [], "missing": []}
    for target, (kind, spelled) in sorted(resolved.items()):
        kinds[kind].append({"reference": target, "on_disk": spelled, **per_target[target]})
    for k in kinds:
        kinds[k].sort(key=lambda r: (-r["files"], r["reference"]))
    # which differing folder spellings explain the case-only references
    spellings: dict[tuple[str, str], int] = {}
    for r in kinds["case_only"]:
        for a, b in zip(r["reference"].split("/"), r["on_disk"].split("/")):
            if a != b:
                spellings[(a, b)] = spellings.get((a, b), 0) + 1
                break
    res = {
        "library": str(lib),
        "disk": {"folders_with_names_differing_only_in_case": folders_with_twins,
                 "names_involved": twin_names, "examples": twin_examples,
                 "seconds": disk_seconds},
        "references": {"files_scanned": len(doc_files) - unreadable, "unreadable": unreadable,
                       "unreadable_examples": unreadable_examples,
                       "top_level_folders": sorted(tops), "references": refs_total,
                       "distinct_targets": len(resolved),
                       "exact": len(kinds["exact"]), "case_only": len(kinds["case_only"]),
                       "missing": len(kinds["missing"]),
                       "case_only_first_difference": [
                           {"referenced": a, "on_disk": b, "targets": n}
                           for (a, b), n in sorted(spellings.items(), key=lambda t: -t[1])],
                       "case_only_examples": kinds["case_only"][:args.examples],
                       "missing_examples": kinds["missing"][:args.examples],
                       "seconds": ref_seconds}}
    r = res["references"]
    lines = [f"Case check of {lib}",
             f"On disk: {folders_with_twins} folders hold names that differ only in case "
             f"({twin_names} names); walked in {disk_seconds:.2f} s"]
    lines += [f"  {e['folder'] or '.'}: {' | '.join(e['names'])}" for e in twin_examples]
    lines += [f"References in {r['files_scanned']} .dsf and .duf files ({unreadable} unreadable), "
              f"to paths under {', '.join(sorted(tops)) or 'no folder'}: {refs_total} references "
              f"to {len(resolved)} distinct paths, read in {ref_seconds:.2f} s",
              f"  {r['exact']} match a path exactly",
              f"  {r['case_only']} match a path only when case is ignored"]
    for d in r["case_only_first_difference"][:args.examples]:
        lines.append(f"    first difference {d['referenced']!r} where the disk has "
                     f"{d['on_disk']!r}: {d['targets']} paths")
    for e in r["case_only_examples"]:
        lines.append(f"    {e['reference']}  (on disk {e['on_disk']}; from {e['files']} files, "
                     f"such as {e['example_file']})")
    lines.append(f"  {r['missing']} match nothing in this library; they may belong to products "
                 "not installed")
    for e in r["missing_examples"]:
        lines.append(f"    {e['reference']}  (from {e['files']} files, such as {e['example_file']})")
    lines += [f"  unreadable: {u}" for u in unreadable_examples]
    emit(args, res, lines)
    return 1 if folders_with_twins or r["case_only"] else 0


# ---------------------------------------------------------------- self-test

def _package(path: Path, files: dict[str, bytes], gid: str | None = "11111111-2222-3333-4444-555555555555",
             product: str | None = "Selftest Product (1 of 2)", extra_values: list[str] = (),
             extra_entries: dict[str, bytes] | None = None, symlinks: dict[str, str] | None = None,
             other_targets: int = 0, manifest: bool = True, stored: bool = True) -> Path:
    """Write a synthetic DIM-style package. Every name and byte in it is invented."""
    path.parent.mkdir(parents=True, exist_ok=True)
    comp = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(path, "w", comp) as z:
        if manifest:
            xml = ['<DAZInstallManifest VERSION="0.1">']
            if gid:
                xml.append(f" <GlobalID VALUE={quoteattr(gid)}/>")
            for v in [f"Content/{r}" for r in files] + list(extra_values) + list(symlinks or {}):
                xml.append(f' <File TARGET="Content" ACTION="Install" VALUE={quoteattr(v)}/>')
            for i in range(other_targets):
                xml.append(f' <File TARGET="Application" ACTION="Install" '
                           f'VALUE="Application/tool{i}.txt"/>')
            xml.append("</DAZInstallManifest>")
            z.writestr("Manifest.dsx", "\n".join(xml) + "\n")
        if product:
            z.writestr("Supplement.dsx", '<ProductSupplement VERSION="0.1">\n'
                       f" <ProductName VALUE={quoteattr(product)}/>\n</ProductSupplement>\n")
        for rel, data in files.items():
            z.writestr(f"Content/{rel}", data)
        for name, data in (extra_entries or {}).items():
            z.writestr(name, data)
        for name, target in (symlinks or {}).items():
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, target)
    return path


def _patch_central(path: Path, name: str, offset: int, value: int) -> None:
    """Set a two-byte field of `name`'s central directory entry, such as the compression
    method (offset 10) or the flag bits (offset 8), to make a zip this script cannot read."""
    data = bytearray(path.read_bytes())
    i = data.find(b"PK\x01\x02")
    while i >= 0:
        n = int.from_bytes(data[i + 28:i + 30], "little")
        if data[i + 46:i + 46 + n] == name.encode():
            data[i + offset:i + offset + 2] = value.to_bytes(2, "little")
            path.write_bytes(bytes(data))
            return
        i = data.find(b"PK\x01\x02", i + 4)
    raise ValueError(f"{name} is not in {path}")


def selftest(keep: Path | None) -> int:
    failures = []

    def check(label, got, want):
        ok = got == want
        print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f": got {got!r}, want {want!r}"))
        if not ok:
            failures.append(label)

    script = str(Path(__file__).resolve())

    def parse(text):
        try:
            return json.loads(text)
        except ValueError:
            return {}

    def run(*argv, json_out=False):
        r = subprocess.run([sys.executable, script, *map(str, argv)],
                           capture_output=True, text=True, timeout=300)
        return r, (parse(r.stdout) if json_out else None)

    def patched_cmd(patch: str, *argv) -> list[str]:
        """This script's main() in a child whose modules `patch` changes first, to stop or
        slow an install at a chosen point."""
        code = "\n".join(["import os, signal, sys, time, runpy, zipfile",
                          f"g = runpy.run_path({script!r}, run_name='daz_library_selftest_child')",
                          patch, f"sys.argv = [{script!r}] + {[str(a) for a in argv]!r}",
                          "sys.exit(g['main']())"])
        return [sys.executable, "-c", code]

    def run_patched(patch: str, *argv):
        r = subprocess.run(patched_cmd(patch, *argv), capture_output=True, text=True, timeout=300)
        return r, parse(r.stdout)

    def signal_at(entry: str, *signals: str) -> str:
        """A patch that sends `signals` to the child as it opens the zip entry `entry`."""
        sends = "".join(f"        os.kill(os.getpid(), signal.{name}); time.sleep(0.05)\n"
                        for name in signals)
        return ("real_open = zipfile.ZipFile.open\n"
                "def patched_open(self, name, *a, **k):\n"
                "    if getattr(name, 'filename', name) == " + repr(entry) + ":\n"
                + sends + "    return real_open(self, name, *a, **k)\n"
                "zipfile.ZipFile.open = patched_open")

    def temp_files(folder: Path) -> list[str]:
        return sorted(p.name for p in folder.rglob("*" + TEMP_SUFFIX)) if folder.exists() else []

    def flat(text: str) -> str:
        return " ".join(text.split())

    if keep is not None:
        if repo_clash(keep):
            print(repo_clash(keep), file=sys.stderr)
            return 2
        if keep.exists() and any(keep.iterdir()):
            print(f"{keep} already exists and is not empty", file=sys.stderr)
            return 2
        keep.mkdir(parents=True, exist_ok=True)
        ctx = None
        base = keep
    else:
        ctx = tempfile.TemporaryDirectory(prefix="daz_library_selftest_")
        base = Path(ctx.name)
    try:
        print(f"self-test in {base}")
        pk, lib, outside_dir = base / "packages", base / "library", base / "outside"
        outside_dir.mkdir(parents=True, exist_ok=True)
        L = ("--library", lib)
        v = "data/Selftest Vendor/Figure"
        p1_files = {f"{v}/One.dsf": b'{"file_version": "0.6.0.0"}\n',
                    f"{v}/Morphs/a.dsf": b"a" * 3000,
                    "Runtime/Support/DAZ_3D_99990001_Selftest.dsx": b"shared support file"}
        p2_files = {f"{v}/Morphs/Deep/b.dsf": b"b" * 5000,
                    "Runtime/Support/DAZ_3D_99990001_Selftest.dsx": b"shared support file",
                    "People/Selftest/Two Only/c.duf": json.dumps(
                        {"asset_info": {"id": "/People/Selftest/Two%20Only/c.duf"},
                         "scene": {"nodes": [{"url": "/data/selftest%20vendor/Figure/One.dsf#One"},
                                             {"url": "/data/Selftest%20Vendor/Figure/One.dsf#One"},
                                             {"url": "/data/Selftest%20Vendor/Gone.dsf#x"},
                                             {"group": "/Pose Controls/Head"}]}}).encode()}
        one = _package(pk / "IM99990001-01_SelftestProduct1Of2.zip", p1_files, other_targets=2,
                       extra_entries={"Content/unlisted.txt": b"not in the manifest"})
        two = _package(pk / "IM99990001-02_SelftestProduct2Of2.zip", p2_files,
                       product="Selftest Product (2 of 2)")

        r, j = run("install", one, two, *L, "--eula-read", "2026-09-16", "--json", json_out=True)
        check("install two parts: exit 0", r.returncode, 0)
        got = {p["part"]: (p.get("written"), p.get("identical"), p.get("status"))
               for p in j.get("packages", [])}
        check("part 01 writes 3, part 02 writes 2 and skips the identical shared file",
              got, {"01": (3, 0, "installed"), "02": (2, 1, "installed")})
        check("unlisted zip entries and other TARGETs are left alone",
              ([p.get("unlisted_zip_entries") for p in j.get("packages", [])],
               (lib / "unlisted.txt").exists()), ([1, 0], False))
        rec = json.loads((lib / RECORDS / "99990001.json").read_text())
        check("record: files and the parts that list them",
              {k: f["parts"] for k, f in rec["files"].items()},
              {**{k: ["01"] for k in p1_files}, **{k: ["02"] for k in p2_files},
               "Runtime/Support/DAZ_3D_99990001_Selftest.dsx": ["01", "02"]})
        check("record: product name without (N of M), parts total, GlobalID",
              (rec["product_name"], rec["parts_total"], rec["global_id"]),
              ("Selftest Product", 2, "11111111-2222-3333-4444-555555555555"))
        check("record: sha256 and size of each zip",
              {p: (k["sha256"], k["size"]) for p, k in rec["packages"].items()},
              {"01": (sha256_of(one), one.stat().st_size), "02": (sha256_of(two), two.stat().st_size)})
        check("record: licence defaults to the standard EULA, with the read date",
              (rec["licence"]["held"], rec["licence"]["interactive_license"],
               rec["licence"]["eula_read"], rec["licence"]["eula_url"]),
              (STANDARD, False, "2026-09-16", EULA_URL))
        r, _ = run("licence", "99990001", *L)
        check("licence text says what may and may not ship",
              all(s in flat(r.stdout) for s in (
                  "Renders and sprites made from this content may ship",
                  "No ruling covers selling standard-licence renders or sprites",
                  "may NOT go into a build without an Interactive License",
                  "Never in native formats", "Protected against extraction",
                  "only with Daz's written consent",
                  "annual revenue above US$1,000,000", "out of the AI stages", NOTE)), True)

        r, j = run("install", one, *L, "--json", json_out=True)
        check("reinstall part 01: all identical, nothing written",
              [(p.get("written"), p.get("identical")) for p in j.get("packages", [])], [(0, 3)])

        victim = lib / v / "Morphs/a.dsf"
        victim.write_bytes(b"c" * 3000)
        r, j = run("install", one, *L, "--json", json_out=True)
        check("a differing file is a conflict: exit 1, nothing written",
              (r.returncode, [p.get("status") for p in j.get("packages", [])],
               victim.read_bytes()[:1]), (1, ["conflicts"], b"c"))
        r, _ = run("verify", *L)
        check("verify passes when only the bytes changed at the same size", r.returncode, 0)
        r, _ = run("verify", *L, "--crc")
        check("verify --crc catches the changed bytes", (r.returncode, "wrong crc: 1" in r.stdout),
              (1, True))
        r, j = run("install", one, *L, "--overwrite", "--json", json_out=True)
        check("--overwrite replaces it", ([(p.get("replaced"), p.get("status"))
                                          for p in j.get("packages", [])],
                                         victim.read_bytes()[:1]), ([(1, "installed")], b"a"))
        victim.write_bytes(b"short")
        r, j = run("verify", "99990001", *L, "--json", json_out=True)
        check("verify catches a wrong size", (r.returncode, j.get("products", [{}])[0].get("wrong_size")),
              (1, 1))
        run("install", one, *L, "--overwrite")

        # a second SKU that shares one path with the first
        other = _package(pk / "IM99990002_OtherProduct.zip",
                         {f"{v}/Morphs/Deep/b.dsf": b"b" * 5000, "data/Other/own.dsf": b"own"},
                         gid="99999999-0000-0000-0000-000000000002", product="Other Product")
        r, j = run("install", other, *L, "--interactive-license", "--json", json_out=True)
        check("a second SKU installs, sharing an identical file",
              (r.returncode, [(p.get("written"), p.get("identical")) for p in j.get("packages", [])]),
              (0, [(1, 1)]))
        r, j = run("licence", "99990002", *L, "--json", json_out=True)
        lic = j.get("licence", {})
        r2, _ = run("licence", "99990002", *L)
        check("an Interactive License is worded with every condition, and no field says plainly "
              "that 3D data may ship",
              (lic.get("interactive_license"), len(lic.get("mesh_rig_morphs_textures_conditions", [])),
               any("may_ship" in k for k in lic),
               lic.get("mesh_rig_morphs_textures", "").count("only on every condition"),
               all(s in flat(r2.stdout) for s in (
                   "may go into a build only on all of these conditions",
                   "Never in native formats", "Protected against extraction",
                   "Sold as a separate in-game purchase, itself or its 2D or 3D derivatives, only "
                   "with Daz's written consent",
                   "after install only with Daz's written consent when the individual or business "
                   "has annual revenue above US$1,000,000",
                   "Selling them as a separate in-game purchase needs Daz's written consent",
                   "cannot check a purchase"))),
              (True, 4, False, 1, True))
        r, j = run("list", *L, "--json", json_out=True)
        check("list: two products, parts and licences",
              [(p["sku"], p["parts"], p["licence"]) for p in j.get("products", [])],
              [("99990001", ["01", "02"], STANDARD), ("99990002", [SINGLE], INTERACTIVE)])

        r, j = run("uninstall", "99990001", "--part", "02", *L, "--json", json_out=True)
        check("uninstall part 02: exit 0, keeps the file part 01 and SKU 99990002 also record",
              (r.returncode, j.get("removed"), j.get("kept_recorded_by_another_part"),
               j.get("kept_recorded_by_another_sku")), (0, 1, 1, 1))
        check("uninstall part 02: shared files stay, its own file and empty folders go",
              ((lib / "Runtime/Support/DAZ_3D_99990001_Selftest.dsx").exists(),
               (lib / v / "Morphs/Deep/b.dsf").exists(), (lib / "People").exists()),
              (True, True, False))
        rec = json.loads((lib / RECORDS / "99990001.json").read_text())
        check("record after uninstalling part 02", (sorted(rec["packages"]), len(rec["files"])),
              (["01"], 3))
        r, j = run("install", two, *L, "--json", json_out=True)
        check("reinstall part 02", [(p.get("written"), p.get("identical"))
                                    for p in j.get("packages", [])], [(1, 2)])
        r, _ = run("verify", *L, "--crc")
        check("verify --crc after reinstall", r.returncode, 0)

        # refusals: nothing may be written anywhere
        before = sorted(p.relative_to(base).as_posix() for p in base.rglob("*"))
        slips = {
            "dotdot": _package(pk / "IM99990003-01_SlipDotDot.zip", {"data/ok.dsf": b"x"},
                               gid="33333333-0000-0000-0000-000000000001", product="Slip",
                               extra_values=["Content/../outside/escaped.txt"],
                               extra_entries={"Content/../outside/escaped.txt": b"x"}),
            "absolute": _package(pk / "IM99990004-01_SlipAbsolute.zip", {"data/ok.dsf": b"x"},
                                 gid="33333333-0000-0000-0000-000000000002", product="Slip",
                                 extra_values=[f"{outside_dir}/abs.txt"],
                                 extra_entries={f"{outside_dir}/abs.txt": b"x"}),
            "backslash": _package(pk / "IM99990005-01_SlipBackslash.zip", {"data/ok.dsf": b"x"},
                                  gid="33333333-0000-0000-0000-000000000003", product="Slip",
                                  extra_values=["Content/data\\..\\..\\outside\\bs.txt"],
                                  extra_entries={"Content/data\\..\\..\\outside\\bs.txt": b"x"}),
            "symlink entry": _package(pk / "IM99990006-01_SlipSymlink.zip", {"data/ok.dsf": b"x"},
                                      gid="33333333-0000-0000-0000-000000000004", product="Slip",
                                      symlinks={"Content/data/link": str(outside_dir)}),
            "record folder": _package(pk / "IM99990007-01_SlipRecords.zip",
                                      {".daz_library/99990001.json": b"{}"},
                                      gid="33333333-0000-0000-0000-000000000005", product="Slip"),
            "not listed in zip": _package(pk / "IM99990008-01_SlipMissing.zip", {"data/ok.dsf": b"x"},
                                          gid="33333333-0000-0000-0000-000000000006", product="Slip",
                                          extra_values=["Content/data/not_in_zip.dsf"]),
        }
        for label, zpath in slips.items():
            r, _ = run("install", zpath, *L)
            check(f"zip-slip {label}: exit 2 with a refusal and nothing installed",
                  (r.returncode, "refusing " in r.stderr, "nothing was installed" in r.stderr),
                  (2, True, True))
        (lib / "data/escape_link").symlink_to(outside_dir, target_is_directory=True)
        via_link = _package(pk / "IM99990009-01_SlipViaLink.zip",
                            {"data/escape_link/through.txt": b"x"},
                            gid="33333333-0000-0000-0000-000000000007", product="Slip")
        r, _ = run("install", via_link, *L)
        check("a symlink in the library that leads outside: exit 2",
              (r.returncode, "outside the library, through a symlink" in r.stderr), (2, True))
        (lib / "data/escape_link").unlink()
        def not_packages(names):
            return [n for n in names if n != "packages" and not n.startswith("packages/")]
        after = sorted(p.relative_to(base).as_posix() for p in base.rglob("*"))
        check("the refusals wrote nothing inside or outside the library",
              not_packages(after), not_packages(before))

        bad_name = pk / "Selftest Renamed.zip"
        shutil.copy(one, bad_name)
        r, _ = run("install", bad_name, *L)
        check("a renamed zip that breaks Daz's pattern: exit 2",
              (r.returncode, "does not match Daz's package pattern" in r.stderr), (2, True))
        wrong_part = pk / "IM99990001-03_SelftestProduct1Of2.zip"
        shutil.copy(one, wrong_part)
        r, _ = run("install", wrong_part, *L)
        check("a zip renamed to another part: exit 2", (r.returncode, "was the zip renamed?" in r.stderr),
              (2, True))
        wrong_sku = pk / "IM99990077-01_SelftestProduct1Of2.zip"
        shutil.copy(one, wrong_sku)
        r, _ = run("install", wrong_sku, *L)
        check("a zip renamed to another SKU: exit 2",
              (r.returncode, "Runtime/Support/DAZ_3D_99990001_" in r.stderr), (2, True))
        not_zip = pk / "IM99990010-01_NotAZip.zip"
        not_zip.write_bytes(b"this is not a zip archive")
        r, _ = run("install", not_zip, *L)
        check("not a zip: exit 2", (r.returncode, "not a readable zip" in r.stderr), (2, True))
        truncated = pk / "IM99990001-01_Truncated.zip"
        truncated.write_bytes(one.read_bytes()[: one.stat().st_size // 2])
        r, _ = run("install", truncated, *L)
        check("a truncated zip: exit 2", (r.returncode, "not a readable zip" in r.stderr), (2, True))
        no_manifest = _package(pk / "IM99990011-01_NoManifest.zip", {"data/x.dsf": b"x"}, manifest=False)
        r, _ = run("install", no_manifest, *L)
        check("no Manifest.dsx: exit 2", (r.returncode, "no Manifest.dsx" in r.stderr), (2, True))
        other_gid = _package(pk / "IM99990001-02_OtherGlobalId.zip", p2_files,
                             gid="00000000-0000-0000-0000-00000000dead",
                             product="Selftest Product (2 of 2)")
        r, _ = run("install", other_gid, *L)
        check("a GlobalID that differs from the record: exit 2",
              (r.returncode, "differs from the" in r.stderr), (2, True))
        r, _ = run("install", one, *L, "--library", ROOT / "output" / "daz_library_selftest")
        check("a library inside the repo: exit 2, nothing created",
              (r.returncode, "inside this repository" in r.stderr,
               (ROOT / "output" / "daz_library_selftest").exists()), (2, True, False))
        r, _ = run("list", "--library", ROOT.parent)
        check("a library that contains the repo: exit 2", (r.returncode, r.stderr.startswith("refusing ")),
              (2, True))

        # a corrupt entry: the CRC check stops the install before the bad file lands
        payload = b"corrupt me " * 400
        bad = _package(pk / "IM99990012-01_CorruptEntry.zip",
                       {"data/Corrupt/aaa_good.dsf": b"good", "data/Corrupt/bbb_bad.dsf": payload},
                       gid="44444444-0000-0000-0000-000000000001", product="Corrupt")
        data = bytearray(bad.read_bytes())
        at = data.find(payload) + 100
        data[at] ^= 0xFF
        bad.write_bytes(bytes(data))
        r, j = run("install", bad, *L, "--json", json_out=True)
        check("a corrupt entry: exit 1, status partial, the good file recorded, the bad one absent",
              (r.returncode, [p.get("status") for p in j.get("packages", [])],
               (lib / "data/Corrupt/aaa_good.dsf").exists(),
               (lib / "data/Corrupt/bbb_bad.dsf").exists(),
               list((lib / "data/Corrupt").glob("*" + TEMP_SUFFIX))),
              (1, ["partial"], True, False, []))
        r, _ = run("verify", "99990012", *L)
        check("verify flags the incomplete part", (r.returncode, "incomplete parts" in r.stdout), (1, True))
        r, _ = run("uninstall", "99990012", *L)
        check("uninstall the partial product: exit 0, its folder goes",
              (r.returncode, (lib / "data/Corrupt").exists()), (0, False))

        # names: Daz's pattern with fullmatch and ASCII digits only
        arabic = "\u0660\u0661"
        try:
            valid_sku(arabic)
            sku_refused = False
        except argparse.ArgumentTypeError:
            sku_refused = True
        check("a package name with a trailing newline or non-ASCII digits does not match; "
              "nor does a SKU argument in non-ASCII digits",
              ([bool(PACKAGE_RE.fullmatch(n)) for n in (
                  "IM99990001-01_SelftestProduct1Of2.zip",
                  "IM99990001-01_SelftestProduct1Of2.zip\n",
                  "IM\u0660\u0660\u066090001-01_SelftestProduct1Of2.zip")], sku_refused),
              ([True, False, False], True))

        # a symlink or a stale file at a temporary name, and a symlink at the path itself
        escaped = outside_dir / "escaped.dsf"
        tl = _package(pk / "IM99990014_TempLink.zip", {"data/TempLink/f.dsf": b"payload"},
                      gid="66666666-0000-0000-0000-000000000001", product="Temp Link")
        victim = outside_dir / "victim.dsf"
        victim.write_bytes(b"outside the library")
        (lib / "data/TempLink").mkdir(parents=True)
        planted = lib / "data/TempLink" / ("." + "f.dsf" + TEMP_SUFFIX)
        for label, target in (("a dangling symlink", escaped), ("a symlink to a file", victim)):
            planted.symlink_to(target)
            r, _ = run("install", tl, *L, "--dry-run")
            r2, _ = run("install", tl, *L)
            check(f"{label} at the temporary name: exit 2 (dry run too), nothing written anywhere",
                  (r.returncode, r2.returncode, "temporary name" in r2.stderr, escaped.exists(),
                   victim.read_bytes(), (lib / "data/TempLink/f.dsf").exists(),
                   planted.is_symlink()),
                  (2, 2, True, False, b"outside the library", False, True))
            planted.unlink()
        planted.write_bytes(b"left by an interrupted run")
        r, _ = run("install", tl, *L)
        check("a regular file left at the temporary name is removed and the file is written",
              (r.returncode, (lib / "data/TempLink/f.dsf").read_bytes(), temp_files(lib)),
              (0, b"payload", []))
        same = outside_dir / "same.dsf"
        same.write_bytes(b"payload")
        (lib / "data/TempLink/f.dsf").unlink()
        (lib / "data/TempLink/f.dsf").symlink_to(same)
        r, j = run("verify", "99990014", *L, "--crc", "--json", json_out=True)
        check("verify counts a symlink at a recorded path as not a file, even with the same bytes",
              (r.returncode, j.get("products", [{}])[0].get("not_a_file")), (1, 1))
        inside = lib / "data/TempLink/inside.dsf"
        inside.write_bytes(b"payload")
        (lib / "data/TempLink/f.dsf").unlink()
        (lib / "data/TempLink/f.dsf").symlink_to(inside)
        r, _ = run("install", tl, *L)
        check("a symlink at the path itself, even one that stays inside the library: exit 2",
              (r.returncode, "a symlink already exists at this path" in r.stderr), (2, True))
        (lib / "data/TempLink/f.dsf").unlink()
        inside.unlink()
        (lib / "data/TempLink/f.dsf").write_bytes(b"payload")
        r, _ = run("uninstall", "99990014", *L)
        check("uninstall 99990014: exit 0", r.returncode, 0)

        # a path listed as a file that another listed path needs as a folder
        clash = _package(pk / "IM99990015_Clash.zip",
                         {"data/Clash/x": b"file", "data/Clash/x/y.dsf": b"y"},
                         gid="66666666-0000-0000-0000-000000000002", product="Clash")
        cl1 = _package(pk / "IM99990016-01_ClashParts1Of2.zip", {"data/Clash2/x": b"file"},
                       gid="66666666-0000-0000-0000-000000000003", product="Clash Parts (1 of 2)")
        cl2 = _package(pk / "IM99990016-02_ClashParts2Of2.zip", {"data/Clash2/x/y.dsf": b"y"},
                       gid="66666666-0000-0000-0000-000000000003", product="Clash Parts (2 of 2)")
        r, _ = run("install", clash, *L)
        r2, _ = run("install", cl1, cl2, *L)
        check("a file and a folder at one path, in one zip or across two: exit 2, nothing written",
              (r.returncode, r2.returncode, "lists that path as a file" in r.stderr,
               "lists that path as a file" in r2.stderr, (lib / "data/Clash").exists(),
               (lib / "data/Clash2").exists()), (2, 2, True, True, False, False))

        # any exception while writing: an unsupported compression method, an encrypted entry
        for label, sku, offset, value in (("an unsupported compression method", "99990017", 10, 99),
                                          ("an encrypted entry", "99990018", 8, 1)):
            broken = _package(pk / f"IM{sku}_Unreadable.zip",
                              {"data/Unreadable/aaa.dsf": b"a", "data/Unreadable/bbb.dsf": b"b"},
                              gid=f"66666666-0000-0000-0000-0000{sku}", product="Unreadable")
            _patch_central(broken, "Content/data/Unreadable/bbb.dsf", offset, value)
            r, j = run("install", broken, *L, "--json", json_out=True)
            r2, j2 = run("list", *L, "--json", json_out=True)
            rows = {p["sku"]: p for p in j2.get("products", [])}
            check(f"{label}: exit 1, partial, the placed file recorded as incomplete, no temporary file",
                  (r.returncode, [p.get("status") for p in j.get("packages", [])],
                   rows.get(sku, {}).get("files"), rows.get(sku, {}).get("incomplete_parts"),
                   (lib / "data/Unreadable/aaa.dsf").exists(),
                   (lib / "data/Unreadable/bbb.dsf").exists(), temp_files(lib)),
                  (1, ["partial"], 1, [SINGLE], True, False, []))
            r, _ = run("uninstall", sku, *L)
            check(f"{label}: uninstall finds the recorded file", (r.returncode,
                  (lib / "data/Unreadable").exists()), (0, False))

        # signals: the first stops at the current file, a second stops at once
        s1 = _package(pk / "IM99990019-01_Stopped1Of2.zip",
                      {"data/Stopped/aaa.dsf": b"a" * 5000, "data/Stopped/bbb.dsf": b"b" * 5000},
                      gid="66666666-0000-0000-0000-000000000019", product="Stopped (1 of 2)")
        s2 = _package(pk / "IM99990019-02_Stopped2Of2.zip", {"data/Stopped/ccc.dsf": b"c"},
                      gid="66666666-0000-0000-0000-000000000019", product="Stopped (2 of 2)")
        r, j = run_patched(signal_at("Content/data/Stopped/bbb.dsf", "SIGINT"),
                           "install", s1, s2, *L, "--json")
        rec = json.loads((lib / RECORDS / "99990019.json").read_text()) \
            if (lib / RECORDS / "99990019.json").exists() else {"files": {}, "packages": {}}
        check("the first SIGINT: exit 130, the file before it recorded, part 01 incomplete, "
              "part 02 not started, no temporary file",
              (r.returncode, j.get("stopped_by"), [p.get("status") for p in j.get("packages", [])],
               sorted(rec["files"]), {k: v.get("complete") for k, v in rec["packages"].items()},
               (lib / "data/Stopped/bbb.dsf").exists(), temp_files(lib)),
              (130, "SIGINT", ["interrupted", "not_started"], ["data/Stopped/aaa.dsf"],
               {"01": False}, False, []))
        r, _ = run("install", s1, s2, *L)
        r2, _ = run("verify", "99990019", *L, "--crc")
        check("installing again after a stop finishes it", (r.returncode, r2.returncode), (0, 0))
        run("uninstall", "99990019", *L)
        r, j = run_patched(signal_at("Content/data/Stopped/bbb.dsf", "SIGINT", "SIGTERM"),
                           "install", s1, s2, *L, "--json")
        rec = json.loads((lib / RECORDS / "99990019.json").read_text()) \
            if (lib / RECORDS / "99990019.json").exists() else {"files": {}, "packages": {}}
        check("a second signal stops at once: exit 143, the placed file still recorded, "
              "no temporary file",
              (r.returncode, j.get("error"), sorted(rec["files"]),
               {k: v.get("complete") for k, v in rec["packages"].items()}, temp_files(lib)),
              (143, "stopped at once by SIGTERM", ["data/Stopped/aaa.dsf"], {"01": False}, []))
        r, _ = run("uninstall", "99990019", *L)
        check("uninstall after a stop at once: exit 0, its folder goes",
              (r.returncode, (lib / "data/Stopped").exists()), (0, False))

        # the records are read inside the lock: a run that waits for it sees the other's record
        race_lib = base / "library_race"
        r1 = _package(pk / "IM99990020-01_Race1Of2.zip",
                      {"data/Race/one.dsf": b"1", "Runtime/Support/DAZ_3D_99990020_Race.dsx": b"s"},
                      gid="66666666-0000-0000-0000-000000000020", product="Race (1 of 2)")
        r2p = _package(pk / "IM99990020-02_Race2Of2.zip",
                       {"data/Race/two.dsf": b"2", "Runtime/Support/DAZ_3D_99990020_Race.dsx": b"s"},
                       gid="66666666-0000-0000-0000-000000000020", product="Race (2 of 2)")
        slow = ("real_enter = g['Lock'].__enter__\n"
                "def slow_enter(self):\n"
                "    time.sleep(1.5)\n"
                "    return real_enter(self)\n"
                "g['Lock'].__enter__ = slow_enter")
        waiting = subprocess.Popen(patched_cmd(slow, "install", r2p, "--library", race_lib),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(0.4)
        first, _ = run("install", r1, "--library", race_lib)
        waited_out, waited_err = waiting.communicate(timeout=300)
        rec = json.loads((race_lib / RECORDS / "99990020.json").read_text()) \
            if (race_lib / RECORDS / "99990020.json").exists() else {"files": {}, "packages": {}}
        check("two installs of one product at once: both exit 0 and the record keeps both parts",
              (first.returncode, waiting.returncode, sorted(rec["packages"]),
               rec["files"].get("Runtime/Support/DAZ_3D_99990020_Race.dsx", {}).get("parts")),
              (0, 0, ["01", "02"], ["01", "02"]))
        r, _ = run("uninstall", "99990020", "--library", race_lib)
        check("uninstall after the race removes every file",
              (r.returncode, sorted(p.relative_to(race_lib).as_posix() for p in race_lib.rglob("*"))),
              (0, [RECORDS, f"{RECORDS}/.lock"]))

        # case-check
        r, j = run("case-check", *L, "--json", json_out=True)
        refs = j.get("references", {})
        check("case-check: a reference that matches only when case is ignored, and a missing one",
              (r.returncode, refs.get("case_only"), refs.get("missing"),
               j.get("disk", {}).get("folders_with_names_differing_only_in_case")), (1, 1, 1, 0))
        twin = _package(pk / "IM99990013_CaseTwin.zip", {"data/SELFTEST VENDOR/Twin/t.dsf": b"t"},
                        gid="55555555-0000-0000-0000-000000000001", product="Case Twin")
        r, j = run("install", twin, *L, "--json", json_out=True)
        check("install warns about a path that differs only in case",
              [p.get("case_twins") for p in j.get("packages", [])], [1])
        r, j = run("case-check", *L, "--json", json_out=True)
        check("case-check: the twin folder on disk",
              (j.get("disk", {}).get("folders_with_names_differing_only_in_case"),
               j.get("disk", {}).get("examples", [{}])[0].get("names")),
              (1, ["SELFTEST VENDOR", "Selftest Vendor"]))
        for sku in ("99990001", "99990002", "99990013"):
            r, _ = run("uninstall", sku, *L)
            check(f"uninstall {sku}: exit 0", r.returncode, 0)
        left = sorted(p.relative_to(lib).as_posix() for p in lib.rglob("*"))
        check("after uninstalling everything only the record folder and its lock remain",
              left, [RECORDS, f"{RECORDS}/.lock"])
    finally:
        if ctx is not None:
            ctx.cleanup()
    print(f"self-test {'passed' if not failures else 'FAILED'}: {len(failures)} failing check(s)")
    return 1 if failures else 0


# ---------------------------------------------------------------- main

def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--library", type=Path, metavar="DIR",
                        help="the content library (default MODELS_DIR/daz_library, outside the repo)")
    common.add_argument("--json", action="store_true", help="print one JSON object instead")
    common.add_argument("--examples", type=int, default=5, metavar="N",
                        help="how many example paths to show (default 5)")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("install", parents=[common], help="extract DIM zips into the library")
    p.add_argument("zips", nargs="+", type=Path, metavar="ZIP")
    p.add_argument("--overwrite", action="store_true", help="replace files whose bytes differ")
    p.add_argument("--dry-run", action="store_true", help="plan and compare, write nothing")
    p.add_argument("--interactive-license", action="store_true",
                   help="record a bought Interactive License for this product")
    p.add_argument("--eula-read", type=valid_date, metavar="YYYY-MM-DD",
                   help="the date you last read the Daz EULA")
    sub.add_parser("list", parents=[common], help="products recorded in the library")
    p = sub.add_parser("licence", parents=[common], help="print or change the licence held")
    p.add_argument("sku", type=valid_sku)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--interactive-license", action="store_true")
    g.add_argument("--standard-license", action="store_true")
    p.add_argument("--eula-read", type=valid_date, metavar="YYYY-MM-DD")
    p = sub.add_parser("verify", parents=[common], help="recorded files present at their size")
    p.add_argument("sku", nargs="?", type=valid_sku)
    p.add_argument("--crc", action="store_true", help="also recompute each file's CRC-32")
    p = sub.add_parser("uninstall", parents=[common], help="remove a product's recorded files")
    p.add_argument("sku", type=valid_sku)
    p.add_argument("--part", type=valid_part, help="only this part, such as 03")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true",
                   help="also remove files whose size no longer matches the record")
    sub.add_parser("case-check", parents=[common], help="paths that differ only in case")
    p = sub.add_parser("selftest", help="synthetic packages, no Daz content")
    p.add_argument("--dir", type=Path, help="build in DIR and keep it (empty, outside the repo)")
    args = ap.parse_args()

    if args.cmd == "selftest":
        return selftest(args.dir)
    try:
        lib = library_path(args.library)
        return {"install": cmd_install, "list": cmd_list, "licence": cmd_licence,
                "verify": cmd_verify, "uninstall": cmd_uninstall,
                "case-check": cmd_case_check}[args.cmd](args, lib)
    except Refused as e:
        print(e, file=sys.stderr)
        if getattr(args, "json", False):
            print(json.dumps({"error": str(e)}, indent=1))
        return 2
    except (Interrupted, KeyboardInterrupt) as e:
        signum = e.signum if isinstance(e, Interrupted) else signal.SIGINT
        msg = f"stopped at once by {signal.Signals(signum).name}"
        print(msg, file=sys.stderr)
        if getattr(args, "json", False):
            print(json.dumps({"error": msg}, indent=1))
        return 128 + signum


if __name__ == "__main__":
    sys.exit(main())
