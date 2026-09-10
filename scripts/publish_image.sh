#!/usr/bin/env bash
# Build the preconfigured image and push it to GHCR.
#
#     scripts/publish_image.sh 0.1.0          # build, tag, push
#     scripts/publish_image.sh 0.1.0 --dry    # build and tag, push nothing
#
# WHY THIS IS NOT A GITHUB ACTION, unlike every other thing this project
# publishes: the image is 26GB. A hosted runner gives you about 14GB free on
# the volume Docker's data root lives on, so the build does not fit -- it dies
# partway through the CUDA layers with no space left on device. The rest of
# the release pipeline (`ci.yml`, `play.yml`, `docs.yml`) runs on hosted
# runners because a Flutter build is small. This one is built where the GPU
# stack already is, and pushed from here.
#
# Log in first, once:
#
#     echo "$GITHUB_TOKEN" | docker login ghcr.io -u <you> --password-stdin
#
# The token needs `write:packages`. A classic PAT works; the `gh` CLI's own
# token does not carry that scope by default.
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="${ASSET_ENGINE_IMAGE_REPO:-ghcr.io/xander-rudolph/game-game-asset-engine-comfy}"
VERSION="${1:-}"
DRY="${2:-}"

if [ -z "$VERSION" ]; then
    echo "usage: $0 <version> [--dry]" >&2
    echo "e.g.:  $0 0.1.0" >&2
    exit 2
fi

mkdir -p logs
LOG="logs/publish-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
echo "logging to $LOG"

echo "== build =="
# BuildKit does not run build steps under the nvidia runtime, so there is no
# GPU here. That is fine and expected: the one step that needs to know about
# CUDA without a device to query is diso, and the Dockerfile sets FORCE_CUDA=1
# and TORCH_CUDA_ARCH_LIST for exactly that.
# The OCI labels are build args, not literals in the Dockerfile, so that
# version/revision/created describe THIS build rather than whenever someone last
# edited the file. An image whose labels lie about its provenance is worse than
# one with no labels, because the lie is machine-readable.
docker build \
    --build-arg IMAGE_VERSION="$VERSION" \
    --build-arg VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)" \
    --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    -t "$IMAGE:$VERSION" -t "$IMAGE:latest" .

echo
echo "== what came out =="
docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' | grep "^$IMAGE" || true

echo
echo "== smoke test =="
# Not a GPU run -- just proof that the thing the image is for is inside it:
# the node packs, their patches, the compiled extension, and the graphs.
docker run --rm --entrypoint bash "$IMAGE:$VERSION" -lc '
set -e
ls /app/custom_nodes | sed "s/^/  node pack: /"
COMFY_CUSTOM_NODES=/app/custom_nodes python3 /opt/asset-engine/scripts/patch_nodes.py --check
ls /app/custom_nodes/ComfyUI-3D-Pack/Gen_3D_Modules/Hunyuan3D_2_1/hy3dpaint/DifferentiableRenderer/mesh_inpaint_processor*.so >/dev/null \
    && echo "  mesh_inpaint_processor: built"
echo "  api graphs:    $(ls /opt/asset-engine/workflows/api/*.json | wc -l)"
echo "  editor graphs: $(ls /app/user/default/workflows/*.json | wc -l)"
echo "  seed:          $(du -sh /opt/asset-engine/seed | cut -f1)"
python3 -c "import torch; assert torch.__version__.startswith(\"2.6.0\"), torch.__version__; print(\"  torch\", torch.__version__)"
'

if [ "$DRY" = "--dry" ]; then
    echo
    echo "built and tagged; --dry, so nothing pushed."
    exit 0
fi

echo
echo "== push =="
echo "26GB or so; this takes a while and resumes badly, so let it finish."
docker push "$IMAGE:$VERSION"
docker push "$IMAGE:latest"

echo
echo "published $IMAGE:$VERSION"
echo "  docker compose --profile packaged up -d"
echo
echo "The package starts PRIVATE. Make it public on the package page if you"
echo "want it pullable without a token:"
echo "  https://github.com/orgs/AthanorGames/packages"
