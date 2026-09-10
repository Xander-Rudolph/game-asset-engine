#!/usr/bin/env python3
"""List the animation clips the installed node packs can apply to a mesh.

Two separate libraries, on two separate skeletons — see the README:

  mesh2motion  bundled .glb clip libraries, one per rig family, bound to
               mesh2motion's own rigs.  Read straight out of the glTF JSON
               chunk, so this stays true as the pack updates.
  UniRig       whatever .fbx / .npz sits in the node's animation_templates,
               applied to a Mixamo-named skeleton.  Add your own there.

    scripts/list_animations.py
    scripts/list_animations.py human        # filter by rig or clip name
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M2M = ROOT / "custom_nodes/ComfyUI-mesh2motion/mesh2motion-ui/animations"
UNIRIG = ROOT / "custom_nodes/ComfyUI-UniRig/assets/animation_templates"
# prestartup_script.py copies the pack's templates here, and this is the folder
# the UniRigApplyAnimation combo actually reads — drop Mixamo downloads in it.
LIVE = ROOT / "input/animation_templates"


def glb_animations(path: Path) -> list[str]:
    """Clip names from a .glb, by parsing the glTF JSON chunk. No deps."""
    b = path.read_bytes()
    if b[:4] != b"glTF":
        return []
    off = 12
    while off + 8 <= len(b):
        length, ctype = struct.unpack_from("<II", b, off)
        if ctype == 0x4E4F534A:                                   # 'JSON'
            doc = json.loads(b[off + 8: off + 8 + length].decode().rstrip("\x00 "))
            return [a.get("name", "?") for a in doc.get("animations", [])]
        off += 8 + length
    return []


def main() -> int:
    needle = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    total = 0

    print(f"mesh2motion  ({M2M})")
    if not M2M.is_dir():
        print("  not installed — scripts/setup.sh clones it")
    for glb in sorted(M2M.glob("*.glb")):
        rig = glb.stem.replace("-animations", "")
        clips = [c for c in glb_animations(glb)
                 if not needle or needle in c.lower() or needle in rig.lower()]
        if not clips:
            continue
        total += len(clips)
        print(f"\n  {rig}  ({len(clips)} clips)")
        for i in range(0, len(clips), 4):
            print("    " + "  ".join(f"{c:<28}" for c in clips[i:i + 4]).rstrip())
    extra = M2M / "CarnegieMellonAnimations"
    if extra.is_dir():
        n = sorted(p.name for p in extra.glob("*.fbx"))
        print(f"\n  CMU mocap ({len(n)} fbx): {', '.join(n)}")

    for label, root in (("UniRig (pack)", UNIRIG), ("UniRig (live, editable)", LIVE)):
        print(f"\n{label}  ({root})")
        if not root.is_dir():
            print("  not present yet — appears after the container's first start")
            continue
        for sub in sorted(p for p in root.iterdir() if p.is_dir()):
            files = sorted(p.name for p in sub.iterdir() if p.is_file())
            files = [f for f in files if not needle or needle in f.lower()]
            if files:
                total += len(files)
                print(f"  {sub.name}: {', '.join(files)}")

    suffix = f" matching {needle!r}" if needle else ""
    print(f"\n{total} clip(s){suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
