#!/usr/bin/env bash
# concept images -> shapes -> textures -> turntables -> curated assets.
#
#   scripts/asset_to_mesh.sh output/concept/golem.png golem output/concept/chimera.png chimera
#
# STAGED, NOT PER-ASSET, and that is the whole design. ComfyUI-3D-Pack holds its
# Hunyuan pipelines in its own node cache, outside ComfyUI's model management, so
# POST /free does not release them and ~5GB stays pinned. With auto_cleanup left
# false (it has to be, see img2mesh_hunyuan3d21.json) a TexGen run leaves TexGen
# resident, and the next asset's ShapeGen then dies with
# `torch.OutOfMemoryError: Allocation on device` in its loader.
#
# So: restart the container once, run EVERY shape (ShapeGen loads once and stays
# hot), restart again, run EVERY texture. Two restarts for a whole batch instead
# of one per asset, and each heavy model is loaded exactly once.
#
# The server is SHARED, and a restart kills whatever it is running or holding in
# its queue. So each restart first reads GET /queue and refuses, naming the jobs,
# when anything is there. Set ASSET_ENGINE_FORCE_RESTART=1 to restart anyway,
# and only when those jobs are yours to lose.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs output/assets output/sheets
LOG="logs/tomesh-$(date +%Y%m%d-%H%M%S).log"
echo "log: $LOG"

COMFY="${COMFY_URL:-http://127.0.0.1:8188}"

# Exits the script when the server holds any job, running or pending, because a
# restart would kill it. Prints nothing when the queue is empty.
require_empty_queue() {
    if [ "${ASSET_ENGINE_FORCE_RESTART:-0}" = "1" ]; then
        echo "ASSET_ENGINE_FORCE_RESTART=1: restarting without checking $COMFY/queue" >&2
        return 0
    fi
    local queue busy
    if ! queue=$(curl -sf -m 30 "$COMFY/queue"); then
        echo "asset_to_mesh.sh: could not read $COMFY/queue, so it cannot tell whether a" \
             "restart would kill other jobs on the shared server. Not restarting." \
             "Set ASSET_ENGINE_FORCE_RESTART=1 to restart anyway." >&2
        exit 1
    fi
    if ! busy=$(printf '%s' "$queue" | python3 -c '
import json, sys
try:
    q = json.load(sys.stdin)
except ValueError:
    sys.exit(1)          # the shell prints the one-line reason
if not isinstance(q, dict) or not all(
        isinstance(q.get(k) or [], list) for k in ("queue_running", "queue_pending")):
    sys.exit(1)
def ids(key):
    return [str(i[1]) if isinstance(i, list) and len(i) > 1 else "?" for i in q.get(key) or []]
run, pend = ids("queue_running"), ids("queue_pending")
if run or pend:
    print("%d running (%s), %d pending (%s)" % (
        len(run), ", ".join(run) or "none", len(pend), ", ".join(pend) or "none"))
'); then
        echo "asset_to_mesh.sh: $COMFY/queue did not answer with a queue. Not restarting." >&2
        exit 1
    fi
    if [ -n "$busy" ]; then
        echo "asset_to_mesh.sh: not restarting. The ComfyUI server at $COMFY is shared and" \
             "holds $busy. Restarting would kill other jobs on the shared server." \
             "Wait for them to finish, or set ASSET_ENGINE_FORCE_RESTART=1 if they are yours to lose." >&2
        exit 1
    fi
}

restart() {
    require_empty_queue
    # The container is comfyui-packaged for the published image and comfyui for a
    # source build, so ask the same resolver the other scripts use.
    docker restart "$(python3 scripts/_engine.py)" >/dev/null 2>&1
    until curl -s -o /dev/null "$COMFY/object_info"; do sleep 4; done
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
    # No --engine, so this takes render_sheet.py's default, Cycles on the card
    # since 2026-09-18. It waits for a free card before each sheet, which here
    # means after the texture stage has drained the queue. Sheets drawn before
    # that switch came from EEVEE and will not match these, so re-render a set
    # whole rather than adding to it; --engine eevee matches the older ones.
    python3 scripts/render_sheet.py "$model" --angles 4 --size 340 \
        --out "output/sheets/${name}.png" >>"$LOG" 2>&1 && printf 'render '
    tex=(); for m in "output/textures/${name}"/*.jpg; do [ -f "$m" ] && tex+=("$m"); done
    python3 scripts/cleanup.py keep "$name" --concept "${CONCEPTS[$i]}" --model "$model" \
        --sheets "output/sheets/${name}.png" ${tex[0]+--textures "${tex[@]}"} >>"$LOG" 2>&1 \
        && echo curated || echo "curate FAILED"
done
echo done
