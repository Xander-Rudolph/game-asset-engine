#!/usr/bin/env python3
r"""Probe MPFB2, MakeHuman's Blender add-on, in the container's headless bpy.

Builds a default MakeHuman body from CC0 assets only, loads the 15
Meta/Oculus-style visemes as shape keys, saves a .blend and a .glb under
output/mpfb/, and renders one viseme per row so you can judge by eye whether
the mouth shapes read at sprite sizes.

    scripts/mpfb_probe.py fetch        # pinned downloads, checked, into input/_devtools/mpfb2
    scripts/mpfb_probe.py build        # output/mpfb/human_visemes.blend, .glb, _build.json
    scripts/mpfb_probe.py render       # output/mpfb/human_visemes_sheet_{128,220,340}.png, _render.json

    # MPFB's own export-copy cleanup, which deletes every helper, so no eyes,
    # teeth or tongue are left
    scripts/mpfb_probe.py build --helpers none --name human_no_helpers

    # add one of MPFB's built-in rigs before the helpers go, under another name
    scripts/mpfb_probe.py build --rig game_engine --name human_game_engine

    # the no-helpers variant, one size and one framing, 16 EEVEE samples,
    # keeping the per-cell PNGs under output/mpfb/_frames/
    scripts/mpfb_probe.py render --name human_no_helpers --sizes 128 --columns face \
        --samples 16 --keep-frames

    # the same rows through render_sheet.py, whole figure only, from the
    # poses file that `build` writes
    scripts/render_sheet.py output/mpfb/human_visemes.blend \
        --poses transforms:output/mpfb/human_visemes_poses.json --angles 1 --size 128 \
        --out output/mpfb/human_visemes_render_sheet_128.png

WHAT IS DOWNLOADED. `fetch` pins four archives by URL, byte size and sha256,
writes each to input/_devtools/mpfb2/downloads/<file>.part, and renames it
into place only when both match. On a mismatch it deletes the .part file and
exits 1. MPFB 2.0.17 comes from extensions.blender.org, whose index publishes
that sha256. The three face packs come from files.makehumancommunity.org,
which publishes no checksum, so their pins are the bytes downloaded on
2026-09-16, which matched on both mirrors. The add-on zip is unpacked into
input/_devtools/mpfb2/ext/mpfb. The face packs stay zipped: `build` installs
them with MPFB's own "Load pack from zip file" operator.

Licences (read 2026-09-16):
  MPFB 2.0.17   code GPL-3.0-or-later (blender_manifest.toml); bundled base
                mesh, targets and rigs CC0 1.0 (LICENSE.md in the GitHub repo
                at tag v2.0.17; the extension zip carries no licence file)
  visemes01     CC0 ("Functional asset packs ... The assets are shared under
  visemes02     CC0" on static.makehumancommunity.org/assets/assetpacks.html;
  faceunits01   every entry in each pack's packs/*.json says "license": "CC0")
None of it is copied into the repo: input/ is gitignored.

HOW MPFB RUNS WITHOUT A UI. Nothing is installed into the image or into
Blender's user config (/app/.home/.config/blender):
  1. BLENDER_USER_RESOURCES is set before `import bpy`, pointing at
     input/_devtools/mpfb2/blender_user. MPFB's logs, config and installed
     packs land there.
  2. input/_devtools/mpfb2/ext is added as a local extension repository with
     preferences.extensions.repos.new(module="mpfb_probe", custom_directory=...)
     and the add-on is enabled as bl_ext.mpfb_probe.mpfb.
  3. The services come from MPFB_CONTEXTUAL_INFORMATION["SERVICES"]:
     HumanService.create_human(), TargetService.bake_targets(),
     FaceService.load_targets(load_meta_visemes=True), the same order as
     MPFB's Export Copy panel.

TRAPS, each seen for real:
  * A plain sys.path import of the package fails in register() with
      ValueError: The "package" does not name an extension
    because LocationService calls bpy.utils.extension_path_user(__package__).
    It has to be enabled as an extension.
  * Once MPFB has been enabled, the bpy process does not exit when the
    script ends. It prints "Error: Not freed memory blocks" and was still
    hanging when `timeout 60` killed it, with or without
    addon_utils.disable() first. The build script therefore flushes and
    calls os._exit(0) after printing its result. `render` opens the saved
    .blend without MPFB and has exited normally that way, but it ends with
    os._exit(0) as well, as render_sheet.py does after a hang at exit there.
  * create_human() leaves helper geometry in the mesh, hidden only by a
    Mask modifier named "Hide helpers". Of its 19158 vertices, 5778 are
    helpers: 4778 in the HelperGeometry group (eyes, eyelashes, teeth,
    tongue, tights, skirt, hair and genitals) and 1000 in JointCubes.
    Exported with the modifier in place, the .glb carried all of it (21833
    glTF vertices). With export_apply=True it lost every morph target, and
    bpy.ops.object.modifier_apply refuses with
      RuntimeError: Error: Modifier cannot be applied to a mesh with shape keys
    So the helper vertices are deleted after the visemes load. By default
    the eye, teeth and tongue helpers (506 vertices) are kept and the other
    5272 deleted, because eight of the visemes move the lower teeth and
    tongue. _build.json lists every helper group's vertex count.
  * A timeout on the host only stops the docker exec client, and the Blender
    process in the container would carry on. So both Blender scripts call
    signal.alarm(--timeout) with SIGALRM left at its default action, which
    ends the process even inside a render or the exit hang, as
    scripts/_engine.py does for every Blender tool, and the host waits 30 s
    longer than that.
  * FaceService.load_targets() does not raise when a pack is missing. It
    logs "Did not find matching target for viseme_aa" and so on, and
    returns having added no shape keys, so `build` checks that all 15
    arrived.

`build` also writes <name>_poses.json: one render_sheet.py transforms pose per
viseme, each setting that key to 1 with "@shape_keys". render_sheet.py gained
.blend input and "@shape_keys" while this probe was being written, and the
render_sheet.py example above works: its cells frame the figure like the body
column below (the same bounding box in the viseme_sil cell) and change 0 to 7
pixels against viseme_sil where the body column changes 0 to 8. It frames the
whole subject only, though, so `render` keeps its own renderer for the face
framings. That renderer uses render_sheet.py's default clay, sun and world
light, with three columns per row:
  body     the whole figure, orthographic, the view render_sheet.py's first
           facing gives (azimuth 45, elevation 30)
  face     front on; the band from the crown down to the lowest point
           viseme_aa moves (on the neck, below the chin) fills three quarters
           of the cell height
  face34   the same framing, 35 degrees round towards the key light and
           10 degrees up
<name>_render.json holds, per size and column, how many pixels each viseme
changes against viseme_sil, the neutral mouth.

MEASURED on 2026-09-16 in comfyui-packaged (bpy 4.5.9 LTS), default options
unless one is named:
  build    1.6 to 1.8 s wall for each of the four builds shown above.
           13886 vertices (the 13380-vertex body plus the 506 kept eye,
           teeth and tongue helper vertices), 16 shape keys: Basis and the
           15 visemes. The .glb has 15066 glTF vertices and 15 morph
           targets with their names in extras.targetNames, and re-imports
           with all 15 keys. --rig game_engine gave 53 bones with no jaw,
           eye or tongue bone; --rig default gave 163, including jaw, eye.L,
           eye.R and eleven tongue bones (tongue00 to tongue04, then
           tongue05 to tongue07 as .L and .R pairs).
  render   135 cells in 896 s and then 861 s wall at EEVEE's default 64
           samples, each time while other Blender renders shared the
           container; both runs gave the same pixel counts. EEVEE here draws
           through llvmpipe (Mesa software OpenGL, reported by
           gpu.platform.renderer_get()), not the GPU. The no-helpers render
           example above (15 cells of 128 px, --samples 16) took 43 s and
           then 31.5 s, and the render_sheet.py example (15 cells of 128 px,
           64 samples) 88.6 s.
  visible  Pixels changed against viseme_sil (threshold 8), fewest to most
           over the other 14 visemes:
                    128 px      220 px      340 px
           body     0 to 8      1 to 18     4 to 46
           face     38 to 244   127 to 722  311 to 1654
           face34   58 to 273   190 to 738  464 to 1629
           By eye, in the body framing no viseme reads at 128 px; at 220 px
           only viseme_aa shows, and at 340 px aa, E and O, each as a dark
           mark a few pixels across. In the face framing viseme_aa reads
           clearly at all three sizes. At 128 px the others are small
           changes around the lip line, easier to see side by side than
           alone. At 340 px aa, O, CH, PP, I, E and U can be told apart side
           by side, while DD, kk, nn, SS, RR, TH and FF look like one
           slightly open mouth.

Before each Blender job this waits, polling every 30 s, while ComfyUI's
queue has a running job, because both share the container's RAM. --no-wait
skips that.

Exit codes: 0 done; 1 a download, checksum, Blender step or check failed, or
Blender ran past --timeout; 2 bad arguments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import ALARM_GRACE, container, exec_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEV = ROOT / "input" / "_devtools" / "mpfb2"
DEV_C = "/app/input/_devtools/mpfb2"
DOWNLOADS = DEV / "downloads"
EXT = DEV / "ext"
OUT = ROOT / "output" / "mpfb"
OUT_C = "/app/output/mpfb"
REPO_MODULE = "mpfb_probe"
COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")

PINS = [
    {
        "name": "mpfb",
        "version": "2.0.17",
        "file": "add-on-mpfb-v2.0.17.zip",
        "urls": ["https://extensions.blender.org/download/sha256:"
                 "4f0a879d64a39bf646fbf5f53601ac678855da329d650617dca5737548239a87"
                 "/add-on-mpfb-v2.0.17.zip"],
        "size": 45031536,
        "sha256": "4f0a879d64a39bf646fbf5f53601ac678855da329d650617dca5737548239a87",
        "licence": "code GPL-3.0-or-later; bundled assets CC0 1.0",
        "licence_source": "blender_manifest.toml in the zip; "
                          "https://raw.githubusercontent.com/makehumancommunity/mpfb2/v2.0.17/LICENSE.md",
    },
    {
        "name": "visemes01",
        "description": "Microsoft-style visemes, 22 targets",
        "file": "visemes01.zip",
        "urls": ["https://files.makehumancommunity.org/functional/visemes01.zip",
                 "https://files2.makehumancommunity.org/functional/visemes01.zip"],
        "size": 179683,
        "sha256": "f61f4f36bb4fe43486efa2a644eea9d6760e510bde10eecc97a4ddf28424e4d3",
        "licence": "CC0",
        "licence_source": "https://static.makehumancommunity.org/assets/assetpacks.html "
                          "(Functional asset packs); packs/visemes01.json",
    },
    {
        "name": "visemes02",
        "description": "Meta/Oculus-style visemes, 15 targets",
        "file": "visemes02.zip",
        "urls": ["https://files.makehumancommunity.org/functional/visemes02.zip",
                 "https://files2.makehumancommunity.org/functional/visemes02.zip"],
        "size": 130733,
        "sha256": "a69ab6fb95ddd5f56f70acc7e859f5f9c6ae613c527d577ea1571eff2183d29e",
        "licence": "CC0",
        "licence_source": "https://static.makehumancommunity.org/assets/assetpacks.html "
                          "(Functional asset packs); packs/visemes02.json",
    },
    {
        "name": "faceunits01",
        "description": "ARKit-style face units, 52 targets",
        "file": "faceunits01.zip",
        "urls": ["https://files.makehumancommunity.org/functional/faceunits01.zip",
                 "https://files2.makehumancommunity.org/functional/faceunits01.zip"],
        "size": 257821,
        "sha256": "d113107bd7eb59f3af4df6fc0ec29bfcc593f496d0b336aec14f086a80ce7146",
        "licence": "CC0",
        "licence_source": "https://static.makehumancommunity.org/assets/assetpacks.html "
                          "(Functional asset packs); packs/faceunits01.json",
    },
]

# Rows in the order of VISEMES02_TO_LIPSYNC in MPFB's faceservice.py.
VISEMES = ["viseme_sil", "viseme_PP", "viseme_FF", "viseme_TH", "viseme_DD",
           "viseme_kk", "viseme_CH", "viseme_SS", "viseme_nn", "viseme_RR",
           "viseme_aa", "viseme_E", "viseme_I", "viseme_O", "viseme_U"]

DEFAULT_HELPERS = "helper-l-eye,helper-r-eye,helper-upper-teeth,helper-lower-teeth,helper-tongue"

# The framings `render` knows, in the order they appear across a sheet.
COLUMNS = ("body", "face", "face34")

# How much longer the host waits than the in-container alarm, so the process
# ends itself first and the host can say so. _engine.exec_python adds it.
TIMEOUT_GRACE = ALARM_GRACE


# ------------------------------------------------------------------ fetch

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(pin: dict) -> bool:
    dest = DOWNLOADS / pin["file"]
    if dest.exists() and dest.stat().st_size == pin["size"] and sha256_of(dest) == pin["sha256"]:
        print(f"  have     {dest.relative_to(ROOT)}")
        return True
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    for url in pin["urls"]:
        print(f"  get      {url}")
        h = hashlib.sha256()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "asset-engine mpfb_probe"})
            with urllib.request.urlopen(req, timeout=120) as r, part.open("wb") as f:
                for chunk in iter(lambda: r.read(1 << 20), b""):
                    f.write(chunk)
                    h.update(chunk)
        except (urllib.error.URLError, OSError) as exc:
            print(f"  ! {url}: {exc}")
            part.unlink(missing_ok=True)
            continue
        size = part.stat().st_size
        if size != pin["size"] or h.hexdigest() != pin["sha256"]:
            print(f"  ! {pin['file']}: got {size} bytes, sha256 {h.hexdigest()}; "
                  f"pinned {pin['size']} bytes, sha256 {pin['sha256']}. Deleted.")
            part.unlink(missing_ok=True)
            continue
        part.replace(dest)
        print(f"  ok       {dest.relative_to(ROOT)}  {size} bytes  sha256 {pin['sha256']}")
        return True
    return False


def unpack_addon(pin: dict) -> bool:
    target = EXT / "mpfb"
    marker = target / ".fetched.json"
    try:
        if json.loads(marker.read_text())["sha256"] == pin["sha256"]:
            print(f"  have     {target.relative_to(ROOT)}")
            return True
    except (OSError, ValueError, KeyError):
        pass
    staging = EXT / ".mpfb.staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    with zipfile.ZipFile(DOWNLOADS / pin["file"]) as zf:
        names = zf.namelist()
        for n in names:
            p = PurePosixPath(n)
            if p.is_absolute() or ".." in p.parts:
                shutil.rmtree(staging, ignore_errors=True)
                print(f"  ! refusing {pin['file']}: member {n!r} leaves the folder")
                return False
        if "blender_manifest.toml" not in names:
            shutil.rmtree(staging, ignore_errors=True)
            print(f"  ! {pin['file']} has no blender_manifest.toml at its root")
            return False
        zf.extractall(staging)
    (staging / ".fetched.json").write_text(json.dumps(
        {"file": pin["file"], "sha256": pin["sha256"], "members": len(names)}, indent=2) + "\n")
    shutil.rmtree(target, ignore_errors=True)
    staging.replace(target)
    print(f"  unpacked {target.relative_to(ROOT)}  ({len(names)} members)")
    return True


def cmd_fetch(args) -> int:
    ok = all([download(p) for p in PINS])
    if not ok:
        return 1
    return 0 if unpack_addon(PINS[0]) else 1


# ------------------------------------------------------------------ Blender side

BUILD_SCRIPT = r'''
import json, os, signal, sys, time, traceback
cfg = json.loads(sys.argv[-1])
# The host's timeout only stops docker exec. SIGALRM's default action ends this
# process even inside C code or the exit hang; see --help.
signal.signal(signal.SIGALRM, signal.SIG_DFL)
signal.alarm(cfg["timeout"])
# Before bpy loads: every user-level path (extension user dirs, MPFB's logs,
# config and installed packs) goes under the dev folder, never the image's
# ~/.config/blender.
os.environ["BLENDER_USER_RESOURCES"] = cfg["user_resources"]
import bpy, addon_utils

result = {"steps": [], "stopped_at": None}


class Stop(Exception):
    pass


def step(name, fn):
    t = time.time()
    try:
        value = fn()
    except Exception as exc:
        result["steps"].append({
            "step": name, "ok": False, "seconds": round(time.time() - t, 2),
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc()[-2500:]})
        result["stopped_at"] = name
        raise Stop(name)
    result["steps"].append({"step": name, "ok": True, "seconds": round(time.time() - t, 2)})
    return value


def reraise(exc):
    raise exc


def helper_groups(ob):
    """Vertex counts of the body, the two helper umbrella groups and each helper-* group."""
    names = {g.index: g.name for g in ob.vertex_groups}
    counts, helpers = {}, 0
    umbrella = {g.index for g in ob.vertex_groups if g.name in ("HelperGeometry", "JointCubes")}
    for v in ob.data.vertices:
        mine = [g.group for g in v.groups if g.weight > 0]
        helpers += any(i in umbrella for i in mine)
        for i in mine:
            n = names[i]
            if n in ("body", "HelperGeometry", "JointCubes") or n.startswith("helper-"):
                counts[n] = counts.get(n, 0) + 1
    return helpers, dict(sorted(counts.items()))


def delete_helpers(ob, keep):
    idx = {g.name: g.index for g in ob.vertex_groups}
    missing = [n for n in keep if n not in idx]
    if missing:
        raise ValueError(f"no vertex group {missing}")
    drop = {idx[n] for n in ("HelperGeometry", "JointCubes") if n in idx}
    kept = {idx[n] for n in keep}
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    doomed = 0
    for v in ob.data.vertices:
        groups = {g.group for g in v.groups if g.weight > 0}
        v.select = bool(groups & drop) and not (groups & kept)
        doomed += v.select
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for md in list(ob.modifiers):
        if md.type == "MASK" and md.vertex_group == "body" and not md.invert_vertex_group:
            ob.modifiers.remove(md)
    for g in list(ob.vertex_groups):
        if g.name in keep:
            continue
        if g.name.startswith(("helper-", "joint-")) or g.name in ("HelperGeometry", "JointCubes"):
            ob.vertex_groups.remove(g)
    return doomed


try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    pkg = "bl_ext." + cfg["repo_module"] + ".mpfb"

    def add_repo():
        bpy.context.preferences.extensions.repos.new(
            name=cfg["repo_module"], module=cfg["repo_module"],
            custom_directory=cfg["repo_dir"], source="USER")
        addon_utils.extensions_refresh(ensure_wheels=False)

    step("add local extension repository", add_repo)

    def enable():
        mod = addon_utils.enable(pkg, default_set=True, handle_error=reraise)
        if mod is None:
            raise RuntimeError(f"addon_utils.enable({pkg!r}) returned None")

    step(f"enable {pkg}", enable)
    mpfb = sys.modules[pkg]
    services = mpfb.MPFB_CONTEXTUAL_INFORMATION["SERVICES"]
    Loc = services["LocationService"]
    Asset = services["AssetService"]
    Human = services["HumanService"]
    Face = services["FaceService"]
    Target = services["TargetService"]
    result["mpfb_version"] = list(mpfb.VERSION)
    result["mpfb_user_data"] = Loc.get_user_data()

    packs = {}
    for z in cfg["packs"]:
        stem = os.path.splitext(os.path.basename(z))[0]

        def install(z=z):
            problem = Asset.check_asset_pack_zip(z)
            if problem is not None:
                raise RuntimeError(f"AssetService.check_asset_pack_zip: {problem}")
            ret = bpy.ops.mpfb.load_pack(filepath=z)
            if "FINISHED" not in ret:
                raise RuntimeError(f"bpy.ops.mpfb.load_pack returned {sorted(ret)}")

        step(f"install pack {stem} with mpfb.load_pack", install)
        meta = json.load(open(os.path.join(Loc.get_user_data(), "packs", stem + ".json")))
        packs[stem] = {
            "entries": len(meta),
            "licences": sorted({str(v.get("license")) for v in meta.values()}),
            "authors": sorted({str(v.get("author")) for v in meta.values()}),
        }
    result["installed_packs"] = packs

    human = step("HumanService.create_human()", lambda: Human.create_human())
    result["create_human_shape_keys"] = [k.name for k in human.data.shape_keys.key_blocks] \
        if human.data.shape_keys else []
    if cfg["rig"]:
        step(f"HumanService.add_builtin_rig({cfg['rig']!r})",
             lambda: Human.add_builtin_rig(human, cfg["rig"]))
    step("TargetService.bake_targets()", lambda: Target.bake_targets(human))
    step("FaceService.load_targets(load_meta_visemes=True)",
         lambda: Face.load_targets(human, load_microsoft_visemes=False, load_meta_visemes=True))

    def check_visemes():
        have = {k.name for k in human.data.shape_keys.key_blocks} if human.data.shape_keys else set()
        missing = [v for v in cfg["visemes"] if v not in have]
        if missing:
            raise RuntimeError(f"visemes missing after load_targets: {missing}")

    step("all 15 visemes present", check_visemes)
    result["vertices_before_cleanup"] = len(human.data.vertices)
    result["mask_modifiers"] = [[m.name, m.vertex_group, m.invert_vertex_group]
                                for m in human.modifiers if m.type == "MASK"]
    result["helper_vertices"], result["vertex_groups_before_cleanup"] = helper_groups(human)
    result["helper_vertices_deleted"] = step(
        "delete helper geometry", lambda: delete_helpers(human, cfg["keep_helpers"]))
    result["kept_helpers"] = cfg["keep_helpers"]

    me = human.data
    basis = me.shape_keys.key_blocks[0]
    shifts = {}
    for kb in me.shape_keys.key_blocks[1:]:
        best, moved = 0.0, 0
        for a, b in zip(basis.data, kb.data):
            d = (a.co - b.co).length
            if d > 1e-5:
                moved += 1
                best = max(best, d)
        shifts[kb.name] = {"max_shift_m": round(best, 5), "vertices_moved": moved}
    result["shape_keys"] = [k.name for k in me.shape_keys.key_blocks]
    result["shape_key_shifts"] = shifts
    result["vertices"] = len(me.vertices)
    result["faces"] = len(me.polygons)
    result["height_m"] = round(human.dimensions.z, 4)
    result["objects"] = [[o.name, o.type] for o in bpy.data.objects]
    result["modifiers"] = [[m.name, m.type] for m in human.modifiers]
    result["materials"] = [s.material.name for s in human.material_slots if s.material]
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    result["bones"] = len(arm.data.bones) if arm else 0
    result["bone_names"] = [b.name for b in arm.data.bones] if arm else []

    os.makedirs(os.path.dirname(cfg["blend"]), exist_ok=True)
    # Otherwise a rebuild leaves the previous file beside it as .blend1.
    bpy.context.preferences.filepaths.save_version = 0
    step("save .blend", lambda: bpy.ops.wm.save_as_mainfile(filepath=cfg["blend"], check_existing=False))
    step("export .glb", lambda: bpy.ops.export_scene.gltf(
        filepath=cfg["glb"], export_format="GLB", export_morph=True, export_apply=False))
except Stop:
    pass
except Exception:
    result["stopped_at"] = result["stopped_at"] or "outside a step"
    result["fatal"] = traceback.format_exc()[-2500:]

print("MPFB_BUILD " + json.dumps(result), flush=True)
sys.stderr.flush()
# Once MPFB is enabled the process hangs at exit instead of ending; see --help.
os._exit(0)
'''

RENDER_SCRIPT = r'''
import json, os, signal, sys, time
cfg = json.loads(sys.argv[-1])
# As in the build script: end this process at the timeout, mid-render or not.
signal.signal(signal.SIGALRM, signal.SIG_DFL)
signal.alarm(cfg["timeout"])
import bpy, math
from mathutils import Vector, Euler

t0 = time.time()
os.makedirs(cfg["frames_dir"], exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=cfg["blend"])
enabled = [a.module for a in bpy.context.preferences.addons if "mpfb" in a.module]

meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys
          and any(k.name.startswith("viseme_") for k in o.data.shape_keys.key_blocks)]
if not meshes:
    raise SystemExit("no mesh with viseme_ shape keys in " + cfg["blend"])
ob = meshes[0]
keys = ob.data.shape_keys.key_blocks
order = [v for v in cfg["visemes"] if v in keys]
missing = [v for v in cfg["visemes"] if v not in keys]

clay = bpy.data.materials.new("clay")
clay.use_nodes = True
bsdf = clay.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = tuple(cfg["clay_color"]) + (1.0,)
bsdf.inputs["Roughness"].default_value = 0.65
if "Specular IOR Level" in bsdf.inputs:
    bsdf.inputs["Specular IOR Level"].default_value = 0.3
for o in bpy.data.objects:
    if o.type == "MESH":
        o.data.materials.clear()
        o.data.materials.append(clay)

mw = ob.matrix_world
basis = keys[0].data
pts = [mw @ v.co for v in basis]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
# The face framing runs from the mesh top down to the lowest rest point that
# the widest viseme moves, which lands below the chin, on the neck. The camera
# aims at the middle of every vertex inside that height band.
wide = keys[cfg["frame_key"]].data
moved = [mw @ a.co for a, b in zip(basis, wide) if (a.co - b.co).length > 1e-4]
chin = min(p.z for p in moved)
head_h = hi.z - chin
band = [p for p in pts if p.z >= chin]
head_centre = Vector(((min(p.x for p in band) + max(p.x for p in band)) / 2.0,
                      (min(p.y for p in band) + max(p.y for p in band)) / 2.0,
                      (hi.z + chin) / 2.0))
extent = max((hi - lo)[i] for i in range(3))

scene = bpy.context.scene
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.clip_start = 0.01
cam_data.clip_end = 100.0
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = cfg["ambient"]
scene.world = world
sun = bpy.data.lights.new("key", "SUN")
sun.energy = cfg["key"]
sun_ob = bpy.data.objects.new("key", sun)
scene.collection.objects.link(sun_ob)
sun_ob.rotation_euler = Euler((math.radians(55), 0, math.radians(30)), "XYZ")
sun_ob.parent = cam

scene.render.engine = "BLENDER_EEVEE_NEXT"
if cfg["samples"]:
    scene.eevee.taa_render_samples = cfg["samples"]
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"

centre = (lo + hi) / 2.0
columns = {
    "body": {"target": centre, "scale": extent * 1.15, "az": -45.0, "el": 30.0, "dist": extent * 3.0},
    "face": {"target": head_centre, "scale": head_h / 0.75, "az": 0.0, "el": 0.0, "dist": 2.0},
    # Turned to the side the camera-parented sun lights; at +35 the face sat in shadow.
    "face34": {"target": head_centre, "scale": head_h / 0.75, "az": -35.0, "el": 10.0, "dist": 2.0},
}
names = [c for c in cfg["columns"] if c in columns]
if names != cfg["columns"]:
    raise SystemExit(f"unknown framing in {cfg['columns']}; known: {sorted(columns)}")


def place(col):
    c = columns[col]
    az, el = math.radians(c["az"]), math.radians(c["el"])
    offset = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * c["dist"]
    cam.location = c["target"] + offset
    cam.rotation_euler = Euler((math.radians(90.0) - el, 0.0, az), "XYZ")
    cam_data.ortho_scale = c["scale"]


frames = []
for size in cfg["sizes"]:
    scene.render.resolution_x = scene.render.resolution_y = size
    for ri, name in enumerate(order):
        for k in keys[1:]:
            k.value = 0.0
        keys[name].value = 1.0
        bpy.context.view_layer.update()
        for ci, col in enumerate(names):
            place(col)
            f = os.path.join(cfg["frames_dir"], f"s{size}_r{ri:02d}_c{ci}.png")
            scene.render.filepath = f
            bpy.ops.render.render(write_still=True)
            frames.append(f)

print("MPFB_RENDER " + json.dumps({
    "frames": frames, "order": order, "missing": missing, "columns": names,
    "mpfb_addons_enabled": enabled, "mesh": ob.name, "shape_keys": [k.name for k in keys],
    "head_height_m": round(head_h, 4), "figure_height_m": round(hi.z - lo.z, 4),
    "eevee_samples": scene.eevee.taa_render_samples,
    "seconds": round(time.time() - t0, 1)}), flush=True)
sys.stderr.flush()
os._exit(0)
'''


# ------------------------------------------------------------------ host side

def wait_for_idle(skip: bool) -> None:
    """Wait while ComfyUI runs a job: Blender shares the container's RAM with it."""
    if skip:
        return
    while True:
        try:
            with urllib.request.urlopen(COMFY + "/queue", timeout=10) as r:
                running = json.load(r).get("queue_running", [])
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print(f"  (could not read {COMFY}/queue: {exc}; not waiting)")
            return
        if not running:
            return
        print(f"  ComfyUI is running a job; checking again in 30 s ({time.strftime('%H:%M:%S')})")
        time.sleep(30)


def glb_summary(path: Path) -> dict:
    """Read the glTF JSON chunk with the standard library: morph targets, skins, vertices."""
    data = path.read_bytes()
    magic, _version, _length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError(f"{path} is not a binary glTF file")
    chunk_len, chunk_type = struct.unpack_from("<I4s", data, 12)
    if chunk_type != b"JSON":
        raise ValueError(f"{path}: first chunk is {chunk_type!r}, not JSON")
    doc = json.loads(data[20:20 + chunk_len])
    acc = doc.get("accessors", [])
    meshes = []
    for m in doc.get("meshes", []):
        prims = m.get("primitives", [])
        meshes.append({
            "name": m.get("name"),
            "primitives": len(prims),
            "vertices": sum(acc[p["attributes"]["POSITION"]]["count"] for p in prims),
            "morph_targets": max((len(p.get("targets", [])) for p in prims), default=0),
            "target_names": (m.get("extras") or {}).get("targetNames", []),
        })
    skins = doc.get("skins", [])
    return {"bytes": len(data), "meshes": meshes, "skins": len(skins),
            "joints": sum(len(s.get("joints", [])) for s in skins),
            "materials": len(doc.get("materials", []))}


def no_result(wall: float, timeout: int) -> None:
    """Say why exec_json came back empty: a Blender error, or which timeout ended it."""
    if wall >= timeout + TIMEOUT_GRACE:
        print(f"  ! Blender was still running {TIMEOUT_GRACE} s after its --timeout {timeout} s "
              f"alarm; look for it with `docker top {container()}`")
    elif wall >= timeout:
        print(f"  ! Blender ran past --timeout {timeout} s and its SIGALRM ended it "
              f"({wall} s wall)")
    else:
        print("  ! Blender printed no result (traceback above)")


def cmd_build(args) -> int:
    missing = [p["file"] for p in PINS if not (DOWNLOADS / p["file"]).exists()]
    if missing or not (EXT / "mpfb" / "blender_manifest.toml").exists():
        print("  ! run `scripts/mpfb_probe.py fetch` first")
        return 1
    keep = [] if args.helpers.strip().lower() == "none" else \
        [h.strip() for h in args.helpers.split(",") if h.strip()]
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = {
        "user_resources": f"{DEV_C}/blender_user",
        "repo_module": REPO_MODULE,
        "repo_dir": f"{DEV_C}/ext",
        "packs": [f"{DEV_C}/downloads/{p['file']}" for p in PINS[1:]],
        "rig": args.rig,
        "keep_helpers": keep,
        "visemes": VISEMES,
        "blend": f"{OUT_C}/{args.name}.blend",
        "glb": f"{OUT_C}/{args.name}.glb",
        "timeout": args.timeout,
    }
    print(f"  container {container()}")
    print(f"  mpfb      {cfg['repo_dir']}/mpfb as bl_ext.{REPO_MODULE}.mpfb")
    print(f"  helpers   {', '.join(keep) if keep else 'none kept'}")
    wait_for_idle(args.no_wait)
    t = time.time()
    res = exec_json(BUILD_SCRIPT, cfg, "MPFB_BUILD ", timeout=args.timeout)
    wall = round(time.time() - t, 1)
    if res is None:
        no_result(wall, args.timeout)
        return 1
    for s in res["steps"]:
        mark = "ok" if s["ok"] else "FAILED"
        print(f"  {mark:6s} {s['seconds']:6.2f} s  {s['step']}")
        if not s["ok"]:
            print(f"         {s['error']}")
    report = {
        "date": time.strftime("%Y-%m-%d"),
        "container": container(),
        "wall_seconds": wall,
        "downloads": [{k: p[k] for k in p if k != "urls"} | {"url": p["urls"][0]} for p in PINS],
        "blender": res,
    }
    rc = 0
    if res.get("stopped_at") or res.get("fatal"):
        print(f"  ! stopped at: {res.get('stopped_at')}")
        if res.get("fatal"):
            print(res["fatal"])
        rc = 1
    else:
        glb = OUT / f"{args.name}.glb"
        report["glb"] = glb_summary(glb)
        visemes = [k for k in res["shape_keys"] if k.startswith("viseme_")]
        groups = res["vertex_groups_before_cleanup"]
        print(f"  helpers   {res['helper_vertices']} of {res['vertices_before_cleanup']} vertices "
              f"(HelperGeometry {groups.get('HelperGeometry', 0)}, "
              f"JointCubes {groups.get('JointCubes', 0)}); "
              f"{res['helper_vertices_deleted']} deleted, "
              f"{res['helper_vertices'] - res['helper_vertices_deleted']} kept")
        print(f"  mesh      {res['vertices']} vertices, {res['faces']} faces, "
              f"{res['height_m']} m tall")
        print(f"  keys      {len(res['shape_keys'])} shape keys: {', '.join(res['shape_keys'])}")
        if res["bones"]:
            print(f"  rig       {res['bones']} bones")
        for m in report["glb"]["meshes"]:
            print(f"  glb       {m['name']}: {m['vertices']} vertices, {m['morph_targets']} morph targets")
        print(f"  wrote     {(OUT / (args.name + '.blend')).relative_to(ROOT)}, {glb.relative_to(ROOT)}")
        if len(visemes) != len(VISEMES):
            print(f"  ! expected {len(VISEMES)} visemes, got {len(visemes)}")
            rc = 1
        if not any(m["morph_targets"] >= len(VISEMES) for m in report["glb"]["meshes"]):
            print("  ! the .glb lost its morph targets")
            rc = 1
        # One pose per viseme in render_sheet.py's transforms format, so that
        # tool can render the same rows for the whole figure.
        poses = OUT / f"{args.name}_poses.json"
        poses.write_text(json.dumps([{"@shape_keys": {v: 1.0}} for v in VISEMES], indent=1) + "\n")
        print(f"  poses     {poses.relative_to(ROOT)}  (render_sheet.py --poses transforms:)")
    report_path = OUT / f"{args.name}_build.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"  report    {report_path.relative_to(ROOT)}  ({wall} s wall)")
    return rc


def cmd_render(args) -> int:
    blend = OUT / f"{args.name}.blend"
    if not blend.exists():
        print(f"  ! no {blend.relative_to(ROOT)}; run `scripts/mpfb_probe.py build` first")
        return 1
    sizes, columns = args.sizes, args.columns
    run_id = f"{os.getpid()}_{int(time.time())}"
    cfg = {
        "blend": f"{OUT_C}/{args.name}.blend",
        "frames_dir": f"{OUT_C}/_frames/{run_id}",
        "visemes": VISEMES,
        "frame_key": "viseme_aa",
        "sizes": sizes,
        "columns": columns,
        "clay_color": [0.55, 0.54, 0.52],
        "key": 1.6,
        "ambient": 0.22,
        "samples": args.samples,
        "timeout": args.timeout,
    }
    frames = OUT / "_frames" / run_id
    wait_for_idle(args.no_wait)
    try:
        return compose_render(args, cfg, blend, frames)
    finally:
        # Also after a failure, so a Blender error or timeout leaves no
        # half-filled frames folder behind.
        if not args.keep_frames:
            shutil.rmtree(frames, ignore_errors=True)
            try:
                frames.parent.rmdir()
            except OSError:
                pass


def compose_render(args, cfg: dict, blend: Path, frames: Path) -> int:
    from PIL import Image, ImageChops, ImageDraw

    sizes = cfg["sizes"]
    t = time.time()
    info = exec_json(RENDER_SCRIPT, cfg, "MPFB_RENDER ", timeout=args.timeout)
    wall = round(time.time() - t, 1)
    if info is None:
        no_result(wall, args.timeout)
        return 1
    if info["missing"]:
        print(f"  ! not in the .blend: {', '.join(info['missing'])}")
    print(f"  opened    {blend.relative_to(ROOT)} with MPFB add-ons enabled: "
          f"{info['mpfb_addons_enabled'] or 'none'}")
    order, cols = info["order"], info["columns"]
    report = {"date": time.strftime("%Y-%m-%d"), "wall_seconds": wall,
              "blender_seconds": info["seconds"], "renders": len(info["frames"]),
              "eevee_samples": info["eevee_samples"],
              "head_height_m": info["head_height_m"], "figure_height_m": info["figure_height_m"],
              "threshold": args.threshold, "sizes": {}}
    for size in sizes:
        sheet = Image.new("RGBA", (len(cols) * size, len(order) * size), (0, 0, 0, 0))
        cells = {}
        for ri in range(len(order)):
            for ci in range(len(cols)):
                im = Image.open(frames / f"s{size}_r{ri:02d}_c{ci}.png").convert("RGBA")
                cells[(ri, ci)] = im
                sheet.paste(im, (ci * size, ri * size))
        out = OUT / f"{args.name}_sheet_{size}.png"
        sheet.save(out)
        # Pixels that differ from the neutral row by more than the threshold in
        # any channel, per column: the number that says whether a shape shows.
        neutral = order.index("viseme_sil") if "viseme_sil" in order else 0
        per = {}
        for ci, col in enumerate(cols):
            base = cells[(neutral, ci)]
            figure = sum(base.getchannel("A").histogram()[1:])
            rows = {}
            for ri, name in enumerate(order):
                diff = ImageChops.difference(cells[(ri, ci)], base)
                bands = [b.point(lambda v: 255 if v > args.threshold else 0) for b in diff.split()]
                mask = bands[0]
                for b in bands[1:]:
                    mask = ImageChops.lighter(mask, b)
                box = mask.getbbox()
                rows[name] = {"changed_px": mask.histogram()[255],
                              "box": [box[2] - box[0], box[3] - box[1]] if box else [0, 0]}
            per[col] = {"figure_px": figure, "visemes": rows}
        report["sizes"][str(size)] = per
        # A labelled copy for looking at; the unlabelled sheet is the asset.
        gutter = 90
        lab = Image.new("RGBA", (gutter + sheet.width, 16 + sheet.height), (255, 255, 255, 255))
        lab.alpha_composite(sheet, (gutter, 16))
        d = ImageDraw.Draw(lab)
        for ci, col in enumerate(cols):
            d.text((gutter + ci * size + 4, 2), col, fill=(0, 0, 0, 255))
        for ri, name in enumerate(order):
            d.text((4, 16 + ri * size + size // 2 - 5), name, fill=(0, 0, 0, 255))
        lab.save(OUT / f"{args.name}_sheet_{size}_labelled.png")
        print(f"  sheet     {out.relative_to(ROOT)}  ({len(cols)}x{len(order)} cells of {size}px)")
        for col in cols:
            counts = [per[col]["visemes"][n]["changed_px"] for n in order if n != "viseme_sil"]
            print(f"            {col:7s} changed px vs viseme_sil: min {min(counts)}, "
                  f"max {max(counts)}, figure {per[col]['figure_px']} px")
    report_path = OUT / f"{args.name}_render.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"  report    {report_path.relative_to(ROOT)}  "
          f"({len(info['frames'])} renders, {wall} s wall)")
    if args.keep_frames:
        print(f"  frames    {frames.relative_to(ROOT)}")
    return 1 if info["missing"] else 0


def csv_sizes(text: str) -> list[int]:
    """--sizes: whole numbers from 16 to 2048, comma separated, repeats dropped."""
    try:
        sizes = [int(s) for s in text.split(",") if s.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected whole numbers separated by commas, such as 128,220, got {text!r}") from None
    if not sizes:
        raise argparse.ArgumentTypeError("name at least one cell size, such as 128")
    if any(not 16 <= s <= 2048 for s in sizes):
        raise argparse.ArgumentTypeError(f"cell sizes must be 16 to 2048 px, got {text!r}")
    return list(dict.fromkeys(sizes))


def csv_columns(text: str) -> list[str]:
    """--columns: names from COLUMNS, comma separated, repeats dropped."""
    cols = [c.strip() for c in text.split(",") if c.strip()]
    bad = [c for c in cols if c not in COLUMNS]
    if bad:
        raise argparse.ArgumentTypeError(
            f"unknown framing {', '.join(repr(c) for c in bad)}; choose from {', '.join(COLUMNS)}")
    if not cols:
        raise argparse.ArgumentTypeError(f"name at least one of {', '.join(COLUMNS)}")
    return list(dict.fromkeys(cols))


def bounded(lo: int, hi: int | None):
    """An int argument type that refuses values outside lo..hi (hi None: no upper bound)."""
    def parse(text: str) -> int:
        try:
            v = int(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected a whole number, got {text!r}") from None
        if v < lo or (hi is not None and v > hi):
            span = f"{lo} to {hi}" if hi is not None else f"{lo} or more"
            raise argparse.ArgumentTypeError(f"expected {span}, got {v}")
        return v
    return parse


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download, check and unpack the pinned archives")

    def common(p, timeout):
        p.add_argument("--name", default="human_visemes",
                       help="base name of the .blend and .glb under output/mpfb/")
        p.add_argument("--timeout", type=bounded(1, None), default=timeout,
                       help=f"seconds before Blender ends itself inside the container "
                            f"(default {timeout}); the host waits {TIMEOUT_GRACE} s more")
        p.add_argument("--no-wait", action="store_true",
                       help="do not wait for a running ComfyUI job to finish first")

    b = sub.add_parser("build", help="human with visemes: .blend, .glb, _build.json")
    common(b, 600)
    b.add_argument("--helpers", default=DEFAULT_HELPERS,
                   help="helper vertex groups to keep, comma separated, or none "
                        f"(default {DEFAULT_HELPERS})")
    b.add_argument("--rig", default="",
                   help="a built-in MPFB rig to add first, such as default or game_engine")

    r = sub.add_parser("render", help="one viseme per row: _sheet_<size>.png, _render.json")
    common(r, 1800)
    r.add_argument("--sizes", type=csv_sizes, default=[128, 220, 340],
                   help="cell sizes, 16 to 2048 px, comma separated (default 128,220,340)")
    r.add_argument("--columns", type=csv_columns, default=list(COLUMNS),
                   help=f"framings, comma separated, from {', '.join(COLUMNS)} (default all three)")
    r.add_argument("--threshold", type=bounded(0, 254), default=8,
                   help="0 to 254 channel difference that counts as a changed pixel (default 8)")
    r.add_argument("--samples", type=bounded(0, None), default=0,
                   help="EEVEE render samples; 0 keeps Blender's default, which "
                        "render_sheet.py also leaves alone")
    r.add_argument("--keep-frames", action="store_true",
                   help="keep the per-cell PNGs under output/mpfb/_frames/")
    args = ap.parse_args()

    if args.cmd == "fetch":
        return cmd_fetch(args)
    if args.cmd == "build":
        return cmd_build(args)
    return cmd_render(args)


if __name__ == "__main__":
    sys.exit(main())
