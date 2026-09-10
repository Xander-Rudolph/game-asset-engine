# ComfyUI + ComfyUI-3D-Pack
#
# Version lock, and why it is what it is:
#
#   Host driver is 550.x (CUDA <= 12.4). GeForce cards can't use CUDA
#   forward-compat, so the whole stack stays on CUDA 12.4 until the driver
#   is >= 580.
#
#   ComfyUI-3D-Pack does not build its CUDA extensions here — it downloads
#   pre-built wheels from MrForExample/Comfy3D_Pre_Builds, keyed on
#   "<os>_<py>_<torch>_<cuda>".  The ONLY Linux + cu124 combination that
#   repo publishes is:
#
#       _Wheels_linux_py311_torch2.6.0_cu124
#
#   Hence Python 3.11 and torch 2.6.0, not the 3.12/2.7.0/cu128 the pack's
#   README and build_config.yaml default to.  Change any one of those three
#   and install.py falls back to compiling pytorch3d/nvdiffrast/spconv from
#   source, which is why this image is a -devel base with nvcc in it.
ARG CUDA_TAG=12.4.1-cudnn-devel-ubuntu22.04
FROM nvidia/cuda:${CUDA_TAG}

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PIP_CONSTRAINT=/etc/pip-constraints.txt \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYOPENGL_PLATFORM=egl \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics \
    TORCH_CUDA_ARCH_LIST=8.9+PTX

# nvdiffrast renders through EGL, pymeshlab/open3d want the GL + X stubs,
# and the source fallback needs build-essential + ninja + nvcc.
# PIP_CONSTRAINT is set above and pip errors out if the file is absent, so it has
# to exist before the very first pip invocation; the torch layer fills it in.
RUN touch /etc/pip-constraints.txt && \
    apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common gnupg ca-certificates && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-dev python3.11-venv python3.11-distutils \
        build-essential ninja-build cmake git wget curl ffmpeg \
        libgl1 libgl1-mesa-dev libgl1-mesa-glx libglib2.0-0 \
        libegl1 libegl1-mesa-dev libgles2 libgles2-mesa-dev \
        libglvnd0 libglvnd-dev libglx0 libsm6 libxext6 libxrender1 \
        libxi6 libxxf86vm1 libassimp-dev && \
    rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11 && \
    python3.11 -m pip install --upgrade pip setuptools wheel

WORKDIR /app

# ---- torch first, pinned, so nothing downstream can drag it forward -------
ARG TORCH_VERSION=2.6.0
ARG TORCHVISION_VERSION=0.21.0
ARG TORCHAUDIO_VERSION=2.6.0
ARG XFORMERS_VERSION=0.0.29.post3
# PIP_CONSTRAINT (set above) points here, so no later `pip install` — however
# deep in a custom node's dependency tree — can resolve torch, or comfy-kitchen,
# to something else.
# Without it, one transitive requirement pulls torch from PyPI's default index
# and the whole stack silently lands on cu13 wheels the 550 driver cannot run.
RUN printf '%s\n' \
        "torch==${TORCH_VERSION}" \
        "torchvision==${TORCHVISION_VERSION}" \
        "torchaudio==${TORCHAUDIO_VERSION}" \
        "xformers==${XFORMERS_VERSION}" \
        "comfy-kitchen==0.2.26" \
        "gpytoolbox==0.3.7" \
        "transformers==4.57.6" \
        "diffusers==0.38.0" > /etc/pip-constraints.txt && \
    pip install --no-cache-dir \
        torch==${TORCH_VERSION} torchvision==${TORCHVISION_VERSION} \
        torchaudio==${TORCHAUDIO_VERSION} xformers==${XFORMERS_VERSION} \
        --index-url https://download.pytorch.org/whl/cu124

# apt's python3-blinker lands in /usr/lib/python3/dist-packages, which
# deadsnakes' 3.11 still has on sys.path, and pip refuses to uninstall a
# distutils-installed package.  rembg pulls flask, which wants a newer blinker,
# and the build dies there.  Note --ignore-installed is NOT the fix: it takes no
# argument, so `--ignore-installed blinker` silently applies to every package
# and re-resolves torch from scratch.
RUN rm -rf /usr/lib/python3/dist-packages/blinker*

# ---- ComfyUI --------------------------------------------------------------
# NOT master.  ComfyUI's `comfy-kitchen` dependency declares torch custom ops with
# PEP 585 builtin generics (`kernel_size: list[int]`), which torch 2.6's
# infer_schema rejects — the server dies on import before any node loads.  Support
# for those annotations arrives in torch 2.7, which 3D-Pack's cu124 wheels rule
# out.  comfy-kitchen <= 0.2.26 is the last line that works on torch 2.6, and
# v0.30.2 is the newest ComfyUI release pinning it.  It still ships
# comfy_api.latest, which ComfyUI-UniRig's nodes are written against.
#
# To move past this: either the wheel repo publishes a Linux cu124 set for a newer
# torch, or the host driver reaches >= 580 and the whole stack can go to cu128.
ARG COMFYUI_REF=v0.30.2
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /app && \
    git -C /app checkout ${COMFYUI_REF}
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install -U --pre comfyui-manager

RUN pip install --no-cache-dir \
        platformdirs gitpython opencv-python-headless imageio-ffmpeg \
        onnxruntime-gpu insightface albumentations segment_anything ultralytics \
        huggingface_hub[hf_transfer]

# ---- ComfyUI-3D-Pack ------------------------------------------------------
# The source tree is KEPT, not thrown away.  It used to be a throwaway clone
# on the theory that the real copy arrives on the ./custom_nodes bind mount --
# which meant the image held the pack's compiled dependencies while the host
# held the source they were built against, and nothing kept the two in step.
# `setup.sh` had to be told to clone the same ref, and drift between them is
# an ImportError with no obvious cause.  One ref, in one place, baked.
#
# Pinned to a commit rather than a branch for the same reason: `main` is a
# moving target, and an image that builds differently on Tuesday is not a
# package.  This is the commit the whole stack was actually brought up on.
ARG COMFY3D_REF=9e8096e50c5bcf35e1f3e34c6ae06216101f8a11
RUN git clone https://github.com/MrForExample/ComfyUI-3D-Pack.git \
        /app/custom_nodes/ComfyUI-3D-Pack && \
    git -C /app/custom_nodes/ComfyUI-3D-Pack checkout ${COMFY3D_REF}

WORKDIR /app/custom_nodes/ComfyUI-3D-Pack
# Two rewrites of the pack's own requirements, and the second one is not
# cosmetic.  The pack pins `cumm==0.7.11` -- the CPU build -- while spconv-cu124
# requires `cumm-cu124`.  Install the file as-is and you get BOTH: they share one
# dist-packages/cumm/ directory, so whichever lands last wins and the CPU
# core_cc.so shadows the CUDA one.  spconv then fails to import AT ALL, with a
# pybind error that names none of this:
#
#   could not convert default argument 'workspace: tv::Tensor' in method
#   'GemmTunerSimple.run_with_tuned_result' into a Python object
#   (type not registered yet?)
#
# That takes down every sparse-convolution algorithm in the pack, Stable3DGen's
# TRELLIS among them.  The published 0.1.0 image shipped with it broken; the
# runtime remedy is in docs/guide/troubleshooting.md and doctor.py names it.
#
# Point the pack's wheel lookup at the combination that actually exists for
# Linux (see the header): cu124 + torch 2.6.0.  Left as 12.8/2.7.0 it asks
# for _Wheels_linux_py311_torch2.7.0_cu124, 404s, and compiles for an hour.
RUN sed -i \
        -e 's/^cuda_version: .*/cuda_version: "12.4"/' \
        -e 's/version: "2\.7\.0"/version: "2.6.0"/' \
        -e 's/version: "0\.22\.0"/version: "0.21.0"/' \
        -e 's/version: "0\.0\.30"/version: "0.0.29.post3"/' \
        _Pre_Builds/_Build_Scripts/build_config.yaml && \
    sed -i 's/^spconv-cu126$/spconv-cu124/' requirements.txt && \
    sed -i 's/^cumm==/cumm-cu124==/' requirements.txt && \
    grep -E 'cuda_version|version:' _Pre_Builds/_Build_Scripts/build_config.yaml

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir ninja "rembg[gpu]" open_clip_torch

# gpytoolbox 0.3.0 — what the unpinned requirement resolves to — still calls
# np.Inf, removed in NumPy 2.0, and 3D-Pack imports it transitively through
# StableFast3D.  That one AttributeError fails the import of the ENTIRE node
# pack, every algorithm in it, not just SF3D.  0.3.7 is fixed, but installing it
# with deps drags numpy back to 2.2 and breaks rembg's requirements, so take it
# --no-deps and add the one dependency it actually needs.
RUN pip install --no-cache-dir --no-deps gpytoolbox==0.3.7 && \
    pip install --no-cache-dir scs

# diso is built here rather than left to install.py, which swallows the failure —
# and the image then looks fine until TripoSG's unconditional `import diso` takes
# the whole node pack down at runtime.
#
# FORCE_CUDA=1 is the load-bearing part.  BuildKit does not run build steps under
# the daemon's default (nvidia) runtime, so there is no GPU during `docker build`;
# diso's setup.py gates on `torch.cuda.is_available()`, falls back to a CppExtension
# with the .cu sources dropped, and the compile fails with "No CUDA runtime is
# found".  Its setup.py checks FORCE_CUDA as an explicit override, and
# TORCH_CUDA_ARCH_LIST (set at the top) tells nvcc what to target without a device
# to query.  This is also why upstream's DOCKER_INSTRUCTIONS.md says to build with
# DOCKER_BUILDKIT=0 — the override is the tidier half of that fix.
#
# MAX_JOBS caps nvcc parallelism: unbounded it is 28 jobs on this box, and CUDA
# template instantiation is memory-hungry enough for that to matter at 31GB.
ENV MAX_JOBS=8
RUN python install.py
RUN FORCE_CUDA=1 pip install --no-cache-dir --no-build-isolation \
        "git+https://github.com/SarahWeiii/diso.git#egg=diso" && \
    python -c "import diso; print('diso OK')"

# A coherent transformers/diffusers/hub set.  Left to resolve freely, pip installs
# transformers 5.x, which calls a safetensors API that exists in no release
# (`safe_open(..., backend=)`) and dies loading any diffusers pipeline; and
# diffusers 0.40, which needs huggingface-hub >= 1.23 while transformers 4.x caps
# it below 1.0.  These three versions agree with each other and with ComfyUI
# v0.30.2's own `transformers>=4.50.3`.
RUN pip install --no-cache-dir \
        "transformers==4.57.6" "diffusers==0.38.0" "huggingface-hub>=0.36,<1.0"

# Blender, for scripts/render_sheet.py.  bpy 4.5.9 is the last line with a cp311
# wheel — which is exactly the Python the 3D-Pack wheels already pin us to.
RUN pip install --no-cache-dir "bpy==4.5.9" && \
    python -c "import bpy; print('bpy', bpy.app.version_string)"

# realesrgan pulls an old basicsr that imports a torchvision module removed
# in 0.17; without this the whole node pack fails to import.
RUN python - <<'PY'
import os, glob
for f in glob.glob('/usr/local/lib/python3.11/dist-packages/basicsr/**/*.py', recursive=True):
    s = open(f).read()
    if 'torchvision.transforms.functional_tensor' in s:
        open(f, 'w').write(s.replace('torchvision.transforms.functional_tensor',
                                     'torchvision.transforms.functional'))
        print('patched', f)
PY

# ---- the rest of the node packs, pinned and baked -------------------------
# These were cloned at runtime by scripts/setup.sh, at whatever their default
# branch happened to be that day.  That is the other half of "missing nodes":
# a fresh checkout needs the network, four clones and a matching set of
# patches before the server has anything to offer.  Now the image carries
# them, at the commits this stack was actually brought up on.
ARG UNIRIG_REF=69ee59dc459d2da7cb0291930c1f944886c31d7c
ARG CAMERAPACK_REF=a58268fe5261d07ffeb93de26cc0d2558a5c0110
ARG MESH2MOTION_REF=11fe6b7aaa5eac60afa3d726389cd9dd870ed1f6
RUN set -eux; \
    for spec in \
        "https://github.com/PozzettiAndrea/ComfyUI-UniRig.git|ComfyUI-UniRig|${UNIRIG_REF}" \
        "https://github.com/PozzettiAndrea/ComfyUI-CameraPack.git|ComfyUI-CameraPack|${CAMERAPACK_REF}" \
        "https://github.com/jtydhr88/ComfyUI-mesh2motion.git|ComfyUI-mesh2motion|${MESH2MOTION_REF}" \
    ; do \
        url="${spec%%|*}"; rest="${spec#*|}"; dir="${rest%%|*}"; ref="${rest#*|}"; \
        git clone "$url" "/app/custom_nodes/$dir"; \
        git -C "/app/custom_nodes/$dir" checkout "$ref"; \
    done

# Their Python deps, so the offline profile has everything it needs.  Failures
# are tolerated one pack at a time: a node that cannot install its extras is a
# missing node category, not a broken image.
RUN for req in /app/custom_nodes/*/requirements.txt; do \
        [ -f "$req" ] || continue; \
        case "$req" in */ComfyUI-3D-Pack/*) continue;; esac; \
        pip install --no-cache-dir -r "$req" || true; \
    done

# The compatibility patches, applied to the source that ships.  They lived in
# scripts/patch_nodes.py precisely because the bind mount hid whatever the
# image did to its own copy; with the source baked, the right time to apply
# them is here, once, where an unapplied patch fails the build.
COPY scripts/patch_nodes.py /opt/asset-engine/scripts/patch_nodes.py
ENV COMFY_CUSTOM_NODES=/app/custom_nodes
RUN python3 /opt/asset-engine/scripts/patch_nodes.py && \
    python3 /opt/asset-engine/scripts/patch_nodes.py --check

# Hunyuan3D-2.1's TexGen needs a pybind11 extension that ships as SOURCE ONLY.
# Without it MeshRender.py's bare `except` swallows the ImportError and leaves
# meshVerticeInpaint undefined, so texturing dies forty seconds in with a
# NameError.  It was built by postinstall.sh inside the running container
# because it belongs inside the node tree that the bind mount replaced; the
# tree is baked now, so it is built here and is simply present.
RUN pip install --no-cache-dir pybind11 && \
    D=/app/custom_nodes/ComfyUI-3D-Pack/Gen_3D_Modules/Hunyuan3D_2_1/hy3dpaint/DifferentiableRenderer && \
    cd "$D" && \
    SUF=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))") && \
    c++ -O3 -Wall -shared -std=c++17 -fPIC $(python3 -m pybind11 --includes) \
        mesh_inpaint_processor.cpp -o "mesh_inpaint_processor$SUF" && \
    python3 -c "import sys; sys.path.insert(0, '$D'); \
import mesh_inpaint_processor; print('mesh_inpaint_processor OK')"

# install.py's wheels win: nothing above may quietly re-resolve torch.
RUN python -c "import torch, torchvision; print('torch', torch.__version__, 'tv', torchvision.__version__); \
assert torch.__version__.startswith('2.6.0'), torch.__version__"
# Import the fragile end of the node pack here, where a failure is a red build
# rather than a silently missing node category in the browser hours later.
# StableFast3D is the canary: it is imported unconditionally by 3D-Pack's
# nodes.py and drags in gpytoolbox, so if it loads, the pack loads.  (The whole
# nodes.py cannot be imported at build time — it wants ComfyUI's folder_paths,
# which only exists once the server is running.)
RUN cd /app/custom_nodes/ComfyUI-3D-Pack && \
    python -c "import sys; sys.path.insert(0, 'Gen_3D_Modules'); \
import gpytoolbox, numpy; \
from StableFast3D.sf3d.system import SF3D; \
print('3D-Pack canary OK — numpy', numpy.__version__, '+ gpytoolbox + StableFast3D')"

# ---- the recipe: scripts, graphs, poses, prompts ---------------------------
# Everything a fresh machine needed from the repo, carried by the image so a
# `docker run` is the whole install.  models.json comes along so the container
# can say which weights are missing by name, which is the one part of the set
# too large to bake (~200GB of checkpoints).
COPY scripts /opt/asset-engine/scripts
COPY poses /opt/asset-engine/poses
COPY prompts /opt/asset-engine/prompts
COPY models.json /opt/asset-engine/models.json
COPY workflows/api /opt/asset-engine/workflows/api

# The editor's own graphs, where ComfyUI looks for user workflows.
COPY workflows/default/workflows /app/user/default/workflows

# A pristine copy of everything a bind mount can hide.
#
# A bind mount does not merge with the image, it REPLACES the path: mount an
# empty ./custom_nodes over a baked one and the server starts with no nodes at
# all, which is precisely the failure this image is meant to end.  The
# entrypoint seeds an empty mount from here and leaves a non-empty one alone,
# so the packaged case works with no mounts and the development case still
# gets a host copy it can edit.
RUN mkdir -p /opt/asset-engine/seed && \
    cp -a /app/custom_nodes /opt/asset-engine/seed/custom_nodes && \
    cp -a /app/user /opt/asset-engine/seed/user && \
    du -sh /opt/asset-engine/seed

COPY scripts/entrypoint.sh /usr/local/bin/asset-engine-entrypoint
RUN chmod +x /usr/local/bin/asset-engine-entrypoint /opt/asset-engine/scripts/*.py \
        /opt/asset-engine/scripts/*.sh 2>/dev/null || true

# Where fetch_models.py looks, and where the compose file mounts the weights.
ENV MODELS_DIR=/app/models \
    ASSET_ENGINE_HOME=/opt/asset-engine

# Run as the host user (compose passes PUID/PGID from .env), so generated meshes
# and sprites are owned by whoever has to move them into the game — not root.
# These are the paths ComfyUI writes to that are NOT bind mounts, plus a HOME the
# non-root user can actually use: comfy-env builds UniRig's pixi environment under
# $HOME, and /root is unreadable to uid 1000.
RUN mkdir -p /app/temp /app/.home && chmod -R 0777 /app/temp /app/.home /app/output /app/input /app/user 2>/dev/null || true
ENV HOME=/app/.home

WORKDIR /app
EXPOSE 8188
ENTRYPOINT ["/usr/local/bin/asset-engine-entrypoint"]
CMD ["python3", "main.py", "--listen", "0.0.0.0", "--enable-manager"]

# Labels, so the package page on GHCR says what this is and where it came from.
#
# Passed in by scripts/publish_image.sh rather than hardcoded, because a version
# or revision baked as a literal is wrong the moment anything moves.  Defaults
# are deliberately obvious placeholders so an unlabelled image is visible as one.
ARG IMAGE_VERSION=dev
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
# CUDA_TAG is declared above the FROM, which scopes it to the FROM alone.
# Re-declare it here or the base.name label expands to an empty string.
ARG CUDA_TAG=12.4.1-cudnn-devel-ubuntu22.04
#
# On the licence label: the previous value was "MIT", which was wrong in a way
# worth naming.  This image is not one work under one licence.  It bundles this
# repo's Apache-2.0 scripts, GPL-3.0-only ComfyUI and UniRig, GPL-2.0-or-later
# Blender, MIT node-pack code, and Tencent community licences that carry a
# territorial exclusion and have no SPDX identifier -- hence the LicenseRef.
# An SPDX expression is the honest form here; a single permissive id is not.
# See docs/guide/redistributing.md before publishing this anywhere.
# maintainer and ref.name are inherited from the NVIDIA/Ubuntu base and are
# actively misleading if left: they say NVIDIA owns this and that it is "ubuntu".
LABEL maintainer="Xanderu" \
      org.opencontainers.image.ref.name="asset-engine-comfy" \
      org.opencontainers.image.title="Asset Engine ComfyUI" \
      org.opencontainers.image.description="ComfyUI with 3D-Pack, UniRig, CameraPack and mesh2motion pinned and built, plus the Asset Engine pipeline workflows and scripts. Model weights are NOT included; the container names the missing ones on boot." \
      org.opencontainers.image.source="https://github.com/Xander-Rudolph/asset-engine" \
      org.opencontainers.image.url="https://xander-rudolph.github.io/asset-engine/" \
      org.opencontainers.image.documentation="https://xander-rudolph.github.io/asset-engine/guide/install" \
      org.opencontainers.image.vendor="Xanderu" \
      org.opencontainers.image.licenses="Apache-2.0 AND GPL-3.0-only AND GPL-2.0-or-later AND MIT AND LicenseRef-Tencent-Hunyuan-Community" \
      org.opencontainers.image.base.name="nvidia/cuda:${CUDA_TAG}" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" 
