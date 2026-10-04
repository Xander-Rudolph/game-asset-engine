#!/usr/bin/env python3
"""Pack a Baldur's Gate 3 file-override mod and drop it in the game's Mods folder.

    scripts/bg3_pack.py --name NimbleHalflings \\
        --replace HFL_F_NKD_Body_A.GR2=output/bg3/halfling_f_v9.gr2 \\
        --replace HFL_M_NKD_Body_A.GR2=output/bg3/halfling_m_v8.gr2 --install

A pak is a folder tree with a `Mods/<Name>/meta.lsx` in it, and the game reads
a file from the highest-priority pak that carries its path.  So a body made by
`bg3_project.py` goes in at the very path the vanilla body has inside
`Models.pak`, and every character built on that body wears the new shape, with
no Toolkit session, no new resources and no character-creation tables.  That
is the quickest way to see a projected body in the game; it is not a shippable
mod (see below).

What the script does:

1. `--replace NAME=FILE` looks NAME up in the game's `Models.pak` listing
   (`output/bg3/models_pak_list.txt`, written by Divine's `list-package`; the
   script runs that itself when the file is missing) and stages FILE at that
   virtual path.  `--file VIRTUALPATH=FILE` stages a file at a path you give,
   for textures and anything else.
2. Writes `Mods/<Name>/meta.lsx` with a UUID derived from the name, so
   repacking keeps the game's mod entry, and a Version64 from `--version`.
3. Packs the staging folder with Divine (`create-package`, lz4) into
   `output/bg3/<Name>.pak` and lists the result back.
4. With `--install`, copies the pak into the game's Mods folder, which for a
   Steam Play install is inside the game's Proton prefix:
   `steamapps/compatdata/1086940/pfx/drive_c/users/steamuser/AppData/Local/Larian Studios/Baldur's Gate 3/Mods`.
   Enable it in the in-game Mod Manager.  Pass `--mods-dir` for any other
   layout.

Divine runs the way `docs/reference/bg3-toolkit.md` describes: LSLib's
`Divine.dll` from `tools/lslib/` under Wine with the Windows .NET 8 runtime in
`tools/dotnet-win/runtime/` (its native build fails on Unix paths), with the
prefix `~/.wine-lslib` or `$LSLIB_WINEPREFIX`.

Everything this writes is derived from Larian's content, so it stays under
`output/bg3/` (which `cleanup.py keep` refuses) and is never committed; and a
body whose shape came through Hunyuan3D is for your own machine, since that
licence's territory clause does not fit a worldwide mod (BG3-012, BG3-013).
The override mechanism is the modding community's practice; whether this pak
loads and shows the body was not yet seen in the game when this was written.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "bg3"
MODELS_PAK_LIST = OUT / "models_pak_list.txt"
GAME_APP_ID = "1086940"
STEAM_ROOTS = ["~/.steam/steam", "~/.steam/debian-installation", "~/.local/share/Steam"]
MODS_IN_PREFIX = Path("pfx/drive_c/users/steamuser/AppData/Local/Larian Studios/Baldur's Gate 3/Mods")


# ---- Divine under Wine --------------------------------------------------------
def find_divine() -> tuple[Path, Path, str]:
    dlls = sorted((ROOT / "tools" / "lslib").glob("*/Packed/Tools/Divine.dll"))
    dotnet = ROOT / "tools" / "dotnet-win" / "runtime" / "dotnet.exe"
    prefix = os.path.expanduser(os.environ.get("LSLIB_WINEPREFIX", "~/.wine-lslib"))
    missing = []
    if not dlls:
        missing.append("tools/lslib/<version>/Packed/Tools/Divine.dll (scripts/fetch_tools.py lslib)")
    if not dotnet.exists():
        missing.append("tools/dotnet-win/runtime/dotnet.exe (Microsoft's Windows x64 .NET 8 runtime zip, "
                       "unpacked, with granny2.dll from LSLib's release zip copied beside dotnet.exe)")
    if not Path(prefix).is_dir():
        missing.append(f"the Wine prefix {prefix} (set LSLIB_WINEPREFIX, or run Divine once under wine)")
    if shutil.which("wine") is None:
        missing.append("wine on the PATH")
    if missing:
        sys.exit("Divine cannot run here. Missing:\n  " + "\n  ".join(missing)
                 + "\nSee docs/reference/bg3-toolkit.md, step 1.")
    return dlls[-1], dotnet, prefix


def winpath(p: Path) -> str:
    return "Z:" + str(p.resolve()).replace("/", "\\")


def divine(args: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    dll, dotnet, prefix = find_divine()
    env = dict(os.environ, WINEPREFIX=prefix, WINEDEBUG="-all")
    cmd = ["wine", str(dotnet), winpath(dll), "-g", "bg3", "-l", "info"] + args
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    r.stdout = r.stdout.replace("\r", "")
    r.stderr = r.stderr.replace("\r", "")
    return r


def fail_on(r: subprocess.CompletedProcess, what: str) -> None:
    text = r.stdout + r.stderr
    if r.returncode != 0 or "[FATAL]" in text or "[ERROR]" in text:
        tail = "\n".join(text.strip().splitlines()[-12:])
        sys.exit(f"Divine {what} failed:\n{tail}")


# ---- the game's files ----------------------------------------------------------
def steam_root() -> Path | None:
    for cand in STEAM_ROOTS:
        p = Path(cand).expanduser()
        if (p / "steamapps").is_dir():
            return p
    return None


def models_pak() -> Path | None:
    root = steam_root()
    if root is None:
        return None
    p = root / "steamapps/common/Baldurs Gate 3/Data/Models.pak"
    return p if p.exists() else None


def pak_listing() -> dict[str, str]:
    """{file name (lower): virtual path} for Models.pak, from the cached listing
    or from a fresh `list-package`."""
    if not MODELS_PAK_LIST.exists():
        pak = models_pak()
        if pak is None:
            sys.exit(f"{MODELS_PAK_LIST} is missing and the game's Models.pak was not found under "
                     f"{', '.join(STEAM_ROOTS)}; pass --models-pak-list or --file with full virtual paths.")
        print(f"  listing    {pak} with Divine (once; cached at {MODELS_PAK_LIST.relative_to(ROOT)})")
        r = divine(["-a", "list-package", "-s", winpath(pak)], timeout=3600)
        fail_on(r, "list-package")
        OUT.mkdir(parents=True, exist_ok=True)
        MODELS_PAK_LIST.write_text("\n".join(l for l in r.stdout.splitlines() if "\t" in l) + "\n")
    table: dict[str, str] = {}
    for line in MODELS_PAK_LIST.read_text().splitlines():
        path = line.split("\t", 1)[0].strip()
        if path:
            table.setdefault(Path(path).name.lower(), path)
    return table


# ---- meta.lsx ------------------------------------------------------------------
def version64(text: str) -> int:
    parts = [int(x) for x in text.split(".")]
    while len(parts) < 4:
        parts.append(0)
    major, minor, revision, build = parts[:4]
    return (major << 55) | (minor << 47) | (revision << 31) | build


def meta_lsx(name: str, author: str, description: str, mod_uuid: str, ver: int) -> str:
    def attr(i, t, v):
        v = str(v).replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
        return f'              <attribute id="{i}" type="{t}" value="{v}"/>'
    rows = [
        attr("Author", "LSString", author),
        attr("CharacterCreationLevelName", "FixedString", ""),
        attr("Description", "LSString", description),
        attr("Folder", "LSString", name),
        attr("LobbyLevelName", "FixedString", ""),
        attr("MD5", "LSString", ""),
        attr("MainMenuBackgroundVideo", "FixedString", ""),
        attr("MenuLevelName", "FixedString", ""),
        attr("Name", "LSString", name),
        attr("NumPlayers", "uint8", 4),
        attr("PhotoBooth", "FixedString", ""),
        attr("StartupLevelName", "FixedString", ""),
        attr("Tags", "LSString", ""),
        attr("Type", "FixedString", "Add-on"),
        attr("UUID", "FixedString", mod_uuid),
        attr("Version64", "int64", ver),
    ]
    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<save>",
        '  <version major="4" minor="7" revision="1" build="3"/>',
        '  <region id="Config">',
        '    <node id="root">',
        "      <children>",
        '        <node id="Dependencies"/>',
        '        <node id="ModuleInfo">',
        *rows,
        "          <children>",
        '            <node id="PublishVersion">',
        f'              <attribute id="Version64" type="int64" value="{ver}"/>',
        "            </node>",
        '            <node id="TargetModes">',
        "              <children>",
        '                <node id="Target">',
        '                  <attribute id="Object" type="FixedString" value="Story"/>',
        "                </node>",
        "              </children>",
        "            </node>",
        "          </children>",
        "        </node>",
        "      </children>",
        "    </node>",
        "  </region>",
        "</save>",
        "",
    ])


# ---- main ----------------------------------------------------------------------
def mods_dir() -> Path | None:
    root = steam_root()
    if root is None:
        return None
    return root / "steamapps/compatdata" / GAME_APP_ID / MODS_IN_PREFIX


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="mod name; also its folder and the pak's file name")
    ap.add_argument("--replace", action="append", default=[], metavar="NAME=FILE",
                    help="put FILE at the virtual path of NAME in Models.pak (e.g. "
                         "HFL_F_NKD_Body_A.GR2=output/bg3/halfling_f_v9.gr2); repeatable")
    ap.add_argument("--file", action="append", default=[], metavar="VIRTUALPATH=FILE",
                    help="put FILE at this virtual path; repeatable")
    ap.add_argument("--author", default="", help="meta.lsx Author")
    ap.add_argument("--description", default="", help="meta.lsx Description")
    ap.add_argument("--version", default="1.0.0.0", help="major.minor.revision.build (default 1.0.0.0)")
    ap.add_argument("--out", help="the pak to write (default output/bg3/<name>.pak)")
    ap.add_argument("--models-pak-list", help="a Divine list-package listing of Models.pak "
                                              "(default output/bg3/models_pak_list.txt)")
    ap.add_argument("--install", action="store_true", help="copy the pak into the game's Mods folder")
    ap.add_argument("--mods-dir", help="the Mods folder --install copies to (default: the game's Proton prefix)")
    args = ap.parse_args()

    if args.models_pak_list:
        global MODELS_PAK_LIST
        MODELS_PAK_LIST = Path(args.models_pak_list)
    if not args.replace and not args.file:
        ap.error("nothing to pack: give --replace and/or --file")

    staged: list[tuple[str, Path]] = []
    table = pak_listing() if args.replace else {}
    for spec in args.replace:
        name, _, file = spec.partition("=")
        vpath = table.get(name.strip().lower())
        if vpath is None:
            sys.exit(f"{name} is not in the Models.pak listing; give its virtual path with --file")
        staged.append((vpath, Path(file)))
    for spec in args.file:
        vpath, _, file = spec.partition("=")
        staged.append((vpath.strip().strip("/"), Path(file)))
    for vpath, file in staged:
        if not file.exists():
            sys.exit(f"{file} does not exist")

    name = args.name
    stage = OUT / f"{name}_pak"
    out = Path(args.out) if args.out else OUT / f"{name}.pak"
    if stage.exists():
        shutil.rmtree(stage)
    for vpath, file in staged:
        dst = stage / vpath
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, dst)
        print(f"  staged     {vpath}  <- {file}  ({file.stat().st_size:,} bytes)")
    mod_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"game-asset-engine/bg3/{name}"))
    ver = version64(args.version)
    meta = stage / "Mods" / name / "meta.lsx"
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(meta_lsx(name, args.author, args.description, mod_uuid, ver))
    print(f"  meta       Mods/{name}/meta.lsx  UUID {mod_uuid}  Version64 {ver} ({args.version})")

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    r = divine(["-a", "create-package", "-s", winpath(stage), "-d", winpath(out), "-c", "lz4"])
    fail_on(r, "create-package")
    r = divine(["-a", "list-package", "-s", winpath(out)])
    fail_on(r, "list-package")
    entries = [l.split("\t")[0] for l in r.stdout.splitlines() if "\t" in l]
    print(f"  wrote      {out}  ({out.stat().st_size:,} bytes, {len(entries)} files)")
    for e in entries:
        print(f"             {e}")
    want = {v for v, _ in staged} | {f"Mods/{name}/meta.lsx"}
    missing = want - set(entries)
    if missing:
        sys.exit(f"the pak lacks {sorted(missing)}")

    record = {"name": name, "uuid": mod_uuid, "version": args.version, "version64": ver,
              "pak": str(out), "files": [{"path": v, "from": str(f)} for v, f in staged]}
    if args.install:
        target = Path(args.mods_dir).expanduser() if args.mods_dir else mods_dir()
        if target is None:
            sys.exit("no Steam install found for --install; pass --mods-dir")
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out, target / out.name)
        record["installed"] = str(target / out.name)
        print(f"  installed  {target / out.name}")
        print("             enable it in the game's Mod Manager (main menu); if the game has never run on "
              "this machine the folder was just created and the first launch may rebuild its prefix")
    (OUT / f"{name}_pak.json").write_text(json.dumps(record, indent=1))
    print(f"  record     {OUT / f'{name}_pak.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
