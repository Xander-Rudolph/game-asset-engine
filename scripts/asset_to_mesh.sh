#!/usr/bin/env bash
# concept images -> shapes -> textures -> turntables -> curated assets.
#
#   scripts/asset_to_mesh.sh output/lords/salt.png lord_salt output/lords/sulfur.png lord_sulfur
#
# STAGED, NOT PER-ASSET, and that is the whole design. ComfyUI-3D-Pack holds its
# Hunyuan pipelines in its own node cache, outside ComfyUI's model management, so
# POST /free does not release them and ~5GB stays pinned. With auto_cleanup left
# false (it has to be — see img2mesh_hunyuan3d21.json) a TexGen run leaves TexGen
# resident, and the next asset's ShapeGen then dies with
# `torch.OutOfMemoryError: Allocation on device` in its loader.
#
# So: restart the container once, run EVERY shape (ShapeGen loads once and stays
# hot), restart again, run EVERY texture. Two restarts for a whole batch instead
# of one per asset, and each heavy model is loaded exactly once.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs output/assets output/sheets
LOG="logs/tomesh-$(date +%Y%m%d-%H%M%S).log"
echo "log: $LOG"

restart() {
    docker compose --profile comfy restart comfyui >/dev/null 2>&1
    until curl -s -o /dev/null "${COMFY_URL:-http://127.0.0.1:8188}/object_info"; do sleep 4; done
    sleep 2
}

CONCEPTS=(); NAMES=()
while [ $# -gt 0 ]; do
    CONCEPTS+=("$1"); shift
    if [ $# -gt 0 ] && [[ "$1" != *.png ]]; then NAMES+=("$1"); shift
    else n=$(basename "${CONCEPTS[-1]}"); NAMES+=("${n%.*}"); fi
done

echo "== shapes (${#NAMES[@]}) =="
restart
for i in "${!NAMES[@]}"; do
    printf '  %-16s ' "${NAMES[$i]}"
    python3 scripts/run_workflow.py workflows/api/img2mesh_hunyuan3d21.json \
        --image "${CONCEPTS[$i]}" --set "save_path=mesh/${NAMES[$i]}.glb" >>"$LOG" 2>&1 \
        && echo ok || echo FAILED
done

echo "== textures =="
restart
for i in "${!NAMES[@]}"; do
    [ -f "output/mesh/${NAMES[$i]}.glb" ] || { printf '  %-16s no shape, skipped\n' "${NAMES[$i]}"; continue; }
    printf '  %-16s ' "${NAMES[$i]}"
    if python3 scripts/run_workflow.py workflows/api/mesh_texture_hunyuan3d21.json \
            --image "${CONCEPTS[$i]}" --set "mesh_path=/app/output/mesh/${NAMES[$i]}.glb" \
            --set 'TexGen Pipeline.max_num_view=6' --set 'TexGen Pipeline.resolution=512' >>"$LOG" 2>&1; then
        newest=$(ls -t output/mesh/textured_*.glb 2>/dev/null | head -1)
        [ -n "$newest" ] && mv "$newest" "output/mesh/${NAMES[$i]}_textured.glb"
        # TexGen always writes its maps to the same fixed paths, so copy them out
        # before the next asset overwrites them.
        mkdir -p "output/textures/${NAMES[$i]}"
        cp output/Hun2-1/hunyuan_output*.jpg "output/textures/${NAMES[$i]}/" 2>/dev/null || true
        echo ok
    else
        echo FAILED
    fi
done

echo "== render + curate =="
for i in "${!NAMES[@]}"; do
    name="${NAMES[$i]}"
    model="output/mesh/${name}_textured.glb"; [ -f "$model" ] || model="output/mesh/${name}.glb"
    [ -f "$model" ] || { printf '  %-16s nothing to render\n' "$name"; continue; }
    printf '  %-16s ' "$name"
    python3 scripts/render_sheet.py "$model" --angles 4 --size 340 \
        --out "output/sheets/${name}.png" >>"$LOG" 2>&1 && printf 'render '
    tex=(); for m in "output/textures/${name}"/*.jpg; do [ -f "$m" ] && tex+=("$m"); done
    python3 scripts/cleanup.py keep "$name" --concept "${CONCEPTS[$i]}" --model "$model" \
        --sheets "output/sheets/${name}.png" ${tex[0]+--textures "${tex[@]}"} >>"$LOG" 2>&1 \
        && echo curated || echo "curate FAILED"
done
echo done
