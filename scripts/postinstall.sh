#!/usr/bin/env bash
# Node installs that have to happen inside the running container rather than at
# image build time, because they write into the bind-mounted custom_nodes/.
#
# ComfyUI-UniRig is the reason this exists: it uses `comfy-env`, which builds an
# isolated pixi environment (bundled Blender, flash-attn, torch-scatter …) in the
# node's own directory.  Built during `docker build` it would land in a layer the
# ./custom_nodes mount then hides; built here it lands on the host and survives
# every later rebuild.  First run takes a while and needs the network.
set -euo pipefail
cd "$(dirname "$0")/.."

# Everything this script prints also lands in logs/, so a long run can be read
# back after the fact without scrolling a terminal. Logs are gitignored and are
# swept by scripts/cleanup.py.
mkdir -p logs
LOG="logs/postinstall-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
echo "logging to $LOG"

SVC="${SVC:-comfyui}"
if ! docker compose --profile comfy ps --services --filter status=running | grep -qx "$SVC"; then
    echo "$SVC is not running — start it with 'docker compose --profile comfy up -d' first." >&2
    exit 1
fi

run() { docker compose --profile comfy exec -T "$SVC" bash -lc "$*"; }

if [ -d custom_nodes/ComfyUI-UniRig ] && [ ! -d custom_nodes/ComfyUI-UniRig/.pixi ]; then
    echo "== ComfyUI-UniRig: building isolated env (slow, one time) =="
    run 'cd /app/custom_nodes/ComfyUI-UniRig && \
         pip install -q -r requirements.txt --upgrade && \
         python install.py'
else
    echo "== ComfyUI-UniRig: env already present, skipping =="
fi

# comfy-env's pixi environment resolves comfy-kitchen to latest, which needs
# torch >= 2.7 for its PEP 585 custom-op annotations — the same wall the main
# environment hit.  The pixi env correctly inherits torch 2.6, so the two
# disagree and UniRig registers ZERO nodes (silently: it logs the ValueError and
# carries on).  0.2.26 is the last release that runs on torch 2.6.
UNIRIG_ENV=/app/.home/.ce/envs/unirig-nodes/.pixi/envs/default
if [ -d .comfy-env/envs/unirig-nodes/.pixi/envs/default ]; then
    echo "== ComfyUI-UniRig: pinning comfy-kitchen in the isolated env =="
    run "$UNIRIG_ENV/bin/python -m pip install -q --no-cache-dir 'comfy-kitchen==0.2.26' && \
         $UNIRIG_ENV/bin/python -c \"import comfy_kitchen, torch; print('env torch', torch.__version__, 'comfy_kitchen OK')\""
fi

# Hunyuan3D-2.1's TexGen needs a pybind11 extension that ships as SOURCE ONLY.
# Without it MeshRender.py's bare `except` swallows the ImportError, prints a
# warning, and leaves meshVerticeInpaint undefined — so texturing dies 40s in
# with `NameError: name 'meshVerticeInpaint' is not defined`.  It has to be built
# here rather than in the Dockerfile: it belongs inside the node tree, which the
# ./custom_nodes bind mount replaces at runtime.
INPAINT=custom_nodes/ComfyUI-3D-Pack/Gen_3D_Modules/Hunyuan3D_2_1/hy3dpaint/DifferentiableRenderer
if [ -d "$INPAINT" ] && ! ls "$INPAINT"/mesh_inpaint_processor*.so >/dev/null 2>&1; then
    echo "== building mesh_inpaint_processor (Hunyuan3D TexGen) =="
    run 'D=/app/'"$INPAINT"'; cd "$D" && \
         SUF=$(python3 -c "import sysconfig; print(sysconfig.get_config_var(\"EXT_SUFFIX\"))") && \
         c++ -O3 -Wall -shared -std=c++17 -fPIC $(python3 -m pybind11 --includes) \
             mesh_inpaint_processor.cpp -o "mesh_inpaint_processor$SUF" && \
         echo built "mesh_inpaint_processor$SUF"'
else
    echo "== mesh_inpaint_processor: already built =="
fi

echo "== restarting so the new nodes register =="
docker compose --profile comfy restart "$SVC"
