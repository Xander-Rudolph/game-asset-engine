#!/usr/bin/env bash
# Rig figures through UniRig, one at a time.
#
#   scripts/rig_units.sh unit_warrior unit_rogue
#
# UniRigLoadMesh offers a COMBO of files, and comfy-env's isolated worker
# snapshots that list when the node is scanned — a mesh dropped into
# input/3d/ afterwards is rejected with "value_not_in_list", and a
# container restart does not refresh it. So each figure is copied over a
# slot that IS in the list and loaded through that; the node reads the
# file at run time, so no restart is needed between figures.
#
# fbx_name is set per figure for two reasons: it names the output, and it
# is the only input that changes between runs. Every figure is loaded
# through the same slot path, so without it ComfyUI sees identical node
# inputs, serves the cached result ("done in 0s") and hands back the
# previous figure's rig.
#
# Two settings are load-bearing, both found by failing on a real asset:
#   articulationxl, not mixamo — mixamo demands a fixed 52-bone humanoid
#     and aborts ("Expected 52 bones ... got 22") on any figure whose arms
#     hang against its body, which is most of ours.
#   fp16, not auto — auto picks bf16 on Ampere/Ada and spconv 2.3.8 has no
#     bfloat16 kernels, so skinning dies with a bare "WorkerError:
#     torch.bfloat16".
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs output/rigged
LOG="logs/rig-$(date +%Y%m%d-%H%M%S).log"
SLOT=input/3d/realistic_male_character.glb
[ -f "$SLOT.orig" ] || cp "$SLOT" "$SLOT.orig"
echo "log: $LOG"
for name in "$@"; do
    src="input/3d/${name}.glb"
    [ -f "$src" ] || { printf '%-18s no mesh at %s\n' "$name" "$src"; continue; }
    printf '%-18s ' "$name"
    cp "$src" "$SLOT"
    stamp=$(mktemp); : > "$stamp"     # anything newer than this is ours
    if python3 scripts/run_workflow.py workflows/api/mesh_rig_unirig.json \
            --set 'source_folder=input' \
            --set 'file_path=3d/realistic_male_character.glb' \
            --set 'skeleton_template=articulationxl' \
            --set 'precision=fp16' \
            --set "fbx_name=$name" >>"$LOG" 2>&1; then
        # By mtime, not by counting: UniRig names its output off the mesh,
        # so a rerun can overwrite rather than add and a count never moves.
        newest=$(find output -maxdepth 1 -name '*.fbx' -newer "$stamp" -print -quit)
        rm -f "$stamp"
        if [ -n "$newest" ]; then
            mv "$newest" "output/rigged/${name}.fbx"
            echo "ok -> output/rigged/${name}.fbx"
        else
            echo "ran but produced no fbx"
        fi
    else
        echo "FAILED (see $LOG)"
    fi
done
cp "$SLOT.orig" "$SLOT"
echo done
