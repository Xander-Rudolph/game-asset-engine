#!/usr/bin/env python3
"""Apply compatibility patches to the cloned node-pack sources.

These have to live here rather than in the Dockerfile: `custom_nodes/` is a bind
mount, so the host copy is the one ComfyUI actually imports and anything the
image did to its own copy is hidden. `setup.sh` runs this after every clone or
pull, and it is idempotent — re-running is a no-op.

Each entry says what upstream breakage it works around, so they can be dropped
when the node pack catches up.

    scripts/patch_nodes.py            # apply
    scripts/patch_nodes.py --check    # report only, exit 1 if any are unapplied
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Where the node packs live. Normally `custom_nodes/` beside this script, but
#: the image bakes the packs at /app/custom_nodes and runs this from
#: /opt/asset-engine, so it has to be told. Set COMFY_CUSTOM_NODES to override.
NODES = Path(os.environ.get("COMFY_CUSTOM_NODES", ROOT / "custom_nodes"))

# (file, find, replace, why)
PATCHES: list[tuple[str, str, str, str]] = [
    (
        "ComfyUI-3D-Pack/Gen_3D_Modules/Era3D/mvdiffusion/pipelines/pipeline_mvdiffusion_unclip.py",
        "CLIPFeatureExtractor",
        "CLIPImageProcessor",
        "transformers 5.x removed the deprecated CLIPFeatureExtractor alias for "
        "CLIPImageProcessor. Era3D still imports the old name, and that single "
        "ImportError fails the import of the ENTIRE 3D-Pack — every algorithm in "
        "it, not just Era3D. The two classes are the same thing.",
    ),
    (
        "ComfyUI-3D-Pack/Gen_3D_Modules/Stable3DGen/stablex/controlnetvae.py",
        "from diffusers.models.controlnet import ControlNetOutput",
        "from diffusers.models.controlnets.controlnet import ControlNetOutput",
        "diffusers moved ControlNetOutput to diffusers.models.controlnets.controlnet "
        "and dropped the old path. Same class, new home — and again one bad import "
        "here takes the whole node pack down.",
    ),
    (
        "ComfyUI-3D-Pack/nodes.py",
        "decimate_mesh(mesh.v.detach().cpu().numpy(), mesh.f.detach().cpu().numpy(), target, remesh, optimalplacement)",
        "decimate_mesh(mesh.v.detach().cpu().numpy(), mesh.f.detach().cpu().numpy(), "
        "target=target, remesh=remesh, optimalplacement=optimalplacement)",
        "Decimate Mesh passes its widgets POSITIONALLY into "
        "decimate_mesh(verts, faces, target, backend, remesh, optimalplacement) — so "
        "the node's `remesh` lands in `backend` and its `optimalplacement` lands in "
        "`remesh`. The visible symptom is that the face target is silently ignored: "
        "quadric decimation hits the target, then the mis-bound `remesh` triggers "
        "isotropic remeshing at targetlen=1% which puts the faces straight back. "
        "Asking for 18000 gave 48491. Binding by keyword fixes it.",
    ),
    (
        "ComfyUI-3D-Pack/Gen_3D_Modules/Hunyuan3D_2_1/hy3dpaint/utils/multiview_utils.py",
        "custom_pipeline=custom_pipeline, \n            torch_dtype=torch.float16",
        "custom_pipeline=custom_pipeline,\n            trust_remote_code=True,\n            torch_dtype=torch.float16",
        "Hunyuan3D-2.1 TexGen loads its paint pipeline from custom code in the node "
        "tree (hy3dpaint/hunyuanpaintpbr/pipeline.py). Current diffusers refuses to "
        "execute that without an explicit opt-in and raises ValueError: '... contains "
        "custom code in pipeline.py which must be executed'. The code is the node "
        "pack's own, already on disk, so trust_remote_code=True is the intended path.",
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report only, do not write")
    args = ap.parse_args()

    applied = pending = missing = 0
    for rel, find, repl, why in PATCHES:
        path = NODES / rel
        if not path.exists():
            print(f"  --   {rel}\n       not present (node pack not cloned?)")
            missing += 1
            continue
        text = path.read_text()
        if find not in text:
            print(f"  ok   {rel}")
            applied += 1
            continue
        if args.check:
            print(f"  TODO {rel}\n       {why}")
            pending += 1
            continue
        path.write_text(text.replace(find, repl))
        print(f"  ->   {rel}: {find} -> {repl}")
        print(f"       {why}")
        applied += 1

    print(f"\n{applied} patch(es) in place, {pending} pending, {missing} skipped")
    return 1 if pending or missing else 0


if __name__ == "__main__":
    sys.exit(main())
