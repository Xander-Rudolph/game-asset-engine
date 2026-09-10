#!/usr/bin/env bash
# One-shot bring-up: custom nodes -> checkpoint skeleton -> models -> image ->
# run -> per-node post-install.  Safe to re-run; every step is idempotent.
#
#   scripts/setup.sh                 # core models only
#   scripts/setup.sh --all           # every model group except 'gated'
#   scripts/setup.sh --no-download   # wire everything up, fetch nothing
set -euo pipefail
cd "$(dirname "$0")/.."

# Everything this script prints also lands in logs/, so a long run can be read
# back after the fact without scrolling a terminal. Logs are gitignored and are
# swept by scripts/cleanup.py.
mkdir -p logs
LOG="logs/setup-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
echo "logging to $LOG"

# Keep COMFY3D_REF in step with the Dockerfile ARG of the same name: the image
# holds the pack's compiled deps, this clone holds the source ComfyUI actually
# imports, and drift between them is an ImportError with no obvious cause.
COMFY3D_REF="${COMFY3D_REF:-main}"

# repo -> directory under custom_nodes/
NODES=(
  "https://github.com/MrForExample/ComfyUI-3D-Pack.git|ComfyUI-3D-Pack"
  "https://github.com/PozzettiAndrea/ComfyUI-UniRig.git|ComfyUI-UniRig"
  "https://github.com/PozzettiAndrea/ComfyUI-CameraPack.git|ComfyUI-CameraPack"
  "https://github.com/jtydhr88/ComfyUI-mesh2motion.git|ComfyUI-mesh2motion"
)

GROUPS=()
DOWNLOAD=--download
SKIP_BUILD=""
for a in "$@"; do
    case "$a" in
        --no-download) DOWNLOAD="" ;;
        --no-build)    SKIP_BUILD=1 ;;
        *)             GROUPS+=("$a") ;;
    esac
done

echo "== custom nodes =="
mkdir -p custom_nodes output input workflows
for spec in "${NODES[@]}"; do
    url="${spec%%|*}"; dir="custom_nodes/${spec##*|}"
    if [ -d "$dir/.git" ]; then
        git -C "$dir" pull --ff-only --quiet || echo "  (could not fast-forward $dir, leaving as is)"
    else
        git clone --depth 1 "$url" "$dir"
    fi
    printf '  %-24s %s\n' "${spec##*|}" "$(git -C "$dir" log -1 --format='%h %s')"
done

echo
echo "== node source patches =="
# custom_nodes/ is a bind mount, so upstream-compatibility fixes have to be
# applied to the host clone, not baked into the image.  Re-run after every pull.
python3 scripts/patch_nodes.py

echo
echo "== models =="
python3 scripts/fetch_models.py $DOWNLOAD ${GROUPS[@]+"${GROUPS[@]}"}

if [ -z "$SKIP_BUILD" ]; then
    echo
    echo "== image =="
    docker compose --profile comfy build
fi

echo
echo "== up =="
docker compose --profile comfy up -d

echo
echo "== post-install =="
scripts/postinstall.sh

echo
echo "ComfyUI on http://localhost:8188"
echo "  logs:   docker compose --profile comfy logs -f"
echo "  models: scripts/fetch_models.py --all"
