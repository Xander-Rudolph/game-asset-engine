#!/usr/bin/env bash
# What the packaged image does before it hands over to ComfyUI.
#
# Four jobs, in order:
#
#   1. Seed any bind mount that arrived empty. The image carries a pristine
#      copy of the node source, the workflows, the poses and the prompts at
#      /opt/asset-engine/seed. A bind mount HIDES whatever the image had at that
#      path, so a fresh checkout with empty custom_nodes/ and workflows/
#      would otherwise start a server with no nodes and no graphs -- the
#      exact "missing workflows" this image exists to prevent. Seeding is
#      skipped the moment a directory has anything in it, so a host copy the
#      user has edited is never overwritten.
#
#   2. Fetch comfyui_controlnet_aux, the one node pack the image must not
#      carry, because its licence forbids distributing part of it (1b below),
#      and build UniRig's own environment if it is missing or broken (1c).
#
#   3. Say what weights are missing, by name, before the server starts, and
#      fetch them when asked (2 below). Models are the one thing too large to
#      bake (the set is ~274GB), so the next best thing is refusing to be
#      quiet about it: a missing checkpoint otherwise shows up as a red node
#      an hour later.
#
#   4. exec the command, so ComfyUI is PID 1 and signals reach it.
#
# Nothing here is fatal. A missing model is worth saying loudly and worth
# starting anyway: most of the graphs do not need most of the weights.
set -euo pipefail

SEED=/opt/asset-engine/seed
say() { printf '\033[36m[asset-engine]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[asset-engine]\033[0m %s\n' "$*" >&2; }

# --- 1. seed the mounts ----------------------------------------------------

# `find -print -quit` is the emptiness test rather than `ls`, because a
# directory holding only dotfiles is not empty and `ls` would say it was.
#
# Nothing in here may stop the server coming up. Docker creates a missing
# bind-mount source as a ROOT-owned directory, and this container runs as the
# host user, so a fresh checkout that skipped `mkdir` gives an unwritable
# mount -- and under `set -e` a failed copy would turn that into a container
# that refuses to start, which is a far worse failure than a missing node.
seed_if_empty() {
    local from="$1" to="$2" what="$3"
    [ -d "$from" ] || return 0
    mkdir -p "$to" 2>/dev/null || true
    [ -d "$to" ] || { warn "$to is not a directory; skipping $what"; return 0; }
    if [ -n "$(find "$to" -maxdepth 1 ! -path "$to" -print -quit 2>/dev/null)" ]; then
        return 0                        # the host has its own copy; leave it
    fi
    say "seeding $what into $to"
    if ! cp -a "$from/." "$to/" 2>/dev/null; then
        warn "could not write $to (owned by $(stat -c '%U:%G' "$to" 2>/dev/null || echo '?'))"
        warn "  $what will be missing. Fix with: sudo chown -R $(id -u):$(id -g) $to"
    fi
}

# Only the two paths a bind mount can plausibly cover. The poses and the
# prompts stay at /opt/asset-engine, where the scripts read them from: copying
# them under /app bought nothing and needed a root-owned directory the
# container has no business writing to.
seed_if_empty "$SEED/custom_nodes" /app/custom_nodes "node packs"
seed_if_empty "$SEED/user" /app/user "workflows"

# The editor's workflow folder is seeded even when the user dir already has
# a database in it: ComfyUI writes comfyui.db there on first run, so the
# directory is non-empty from then on and the graphs would never arrive.
if [ -d "$SEED/user/default/workflows" ]; then
    mkdir -p /app/user/default/workflows 2>/dev/null || true
    for f in "$SEED"/user/default/workflows/*.json; do
        [ -e "$f" ] || continue
        [ -e "/app/user/default/workflows/$(basename "$f")" ] && continue
        cp -a "$f" /app/user/default/workflows/ 2>/dev/null &&
            say "added workflow $(basename "$f" .json)" || true
    done
fi

# --- 1b. fetch the pack the image may not carry ----------------------------

# comfyui_controlnet_aux is not in the image (the owner's decision, 2026-09-30):
# its dwpose/ and open_pose/ folders carry CMU's OpenPose licence, which
# forbids distributing them, and a published image would. So each container
# fetches it for itself from GitHub, at the commit the Dockerfile pins, the
# first time it starts. The container's own layer holds it, so a
# --force-recreate fetches it again: 87MB, 2.5s on the reference machine
# (2026-09-30).
#
# Downloading it is accepting CMU's terms, which is why this says so, and why
# ASSET_ENGINE_CONTROLNET_AUX=0 skips it. Without it, complete_workflow.json's
# Pose Transfer flow has no preprocessor; nothing else here uses the pack.
#
# Cloned into /app/temp and moved into place only once complete, so a fetch
# cut short never leaves a half pack for ComfyUI to import. A source build's
# ./custom_nodes mount usually has it already, from scripts/setup.sh, and an
# existing copy is always left alone.
fetch_controlnet_aux() {
    local url="${ASSET_ENGINE_CONTROLNET_AUX_URL:-}" ref="${ASSET_ENGINE_CONTROLNET_AUX_REF:-}"
    local dest=/app/custom_nodes/comfyui_controlnet_aux tmp
    [ -n "$url" ] && [ -n "$ref" ] || return 0      # an image from before this
    [ "${ASSET_ENGINE_CONTROLNET_AUX:-1}" = "1" ] || {
        say "skipping comfyui_controlnet_aux (ASSET_ENGINE_CONTROLNET_AUX=${ASSET_ENGINE_CONTROLNET_AUX})"
        return 0
    }
    [ -e "$dest" ] && return 0
    say "fetching comfyui_controlnet_aux at ${ref:0:7}, which the image does not carry"
    say "  its dwpose/ and open_pose/ code is CMU's OpenPose licence: noncommercial"
    say "  research use only. Set ASSET_ENGINE_CONTROLNET_AUX=0 to skip it."
    tmp="$(mktemp -d /app/temp/controlnet_aux.XXXXXX 2>/dev/null)" || {
        warn "no writable /app/temp; comfyui_controlnet_aux not fetched"; return 0; }
    if git init -q "$tmp" &&
        git -C "$tmp" fetch -q --depth 1 "$url" "$ref" &&
        git -C "$tmp" checkout -q FETCH_HEAD &&
        mv "$tmp" "$dest" 2>/dev/null; then
        say "  comfyui_controlnet_aux ready at $(git -C "$dest" rev-parse --short HEAD)"
    else
        rm -rf "$tmp"
        warn "could not fetch comfyui_controlnet_aux; Pose Transfer will be missing its node"
    fi
}
fetch_controlnet_aux

# --- 1c. build UniRig's environment ----------------------------------------

# UniRig runs its nodes in its own pixi environment, under $HOME/.ce, which the
# packaged service keeps in the unirig-home volume. Nothing else builds it:
# without it the nodes load in the main environment, where Apply Animation died
# loading Blender ("undefined symbol: rtcGetSceneTraversable", 2026-09-30).
#
# Built with UniRig's own install.py, not comfy-env's COMFY_ENV_AUTO_INSTALL.
# The auto-install writes a manifest without the [cuda] wheels, so the
# environment loads and Auto Rig then dies on "No module named
# 'torch_cluster'" (2026-09-30); install.py adds torch-scatter, torch-cluster,
# spconv, cumm and flash-attn. Its comfy-kitchen comes from UniRig's
# comfy-env.toml, which scripts/patch_nodes.py pins to 0.2.26.
#
# install.py's spconv and cumm are swapped for the pair the main image uses.
# comfy-env's wheel index has only cumm 0.8.2 for cu124, torch 2.6 and Python
# 3.11, beside spconv 2.3.8, which requires cumm<0.8.0; Auto Rig then died in
# cumm's runtime CUDA compile ("nvrtc compile failed", 2026-09-30). With
# spconv-cu124 and cumm-cu124 at the main image's versions, pip check was clean
# and Auto Rig rigged a mesh in 45 s. The versions are read from the main image
# at start-up, so the two cannot drift apart.
#
# The test imports what broke: comfy_kitchen, which a version torch 2.6 rejects
# fails to import, and the CUDA wheels; and it checks that cumm-cu124, not the
# index's cumm, is installed. It takes about 5 s. An environment that fails it
# is removed and rebuilt, so a half-built one, or one an older image built,
# heals itself. ASSET_ENGINE_UNIRIG_ENV=0 skips all of it, and UniRig with it.
UNIRIG_ENV_TEST='
import comfy_kitchen, torch_cluster, torch_scatter, spconv.pytorch
from importlib.metadata import version, PackageNotFoundError
version("cumm-cu124")
try:
    version("cumm")
except PackageNotFoundError:
    pass
else:
    raise SystemExit("the index cumm is installed")
'
build_unirig_env() {
    local node=/app/custom_nodes/ComfyUI-UniRig
    local env="${HOME:-/app/.home}/.ce/envs/unirig-nodes"
    local py="$env/.pixi/envs/default/bin/python"
    local log="${HOME:-/app/.home}/.ce/unirig-install.log"
    local pair
    [ -f "$node/install.py" ] || return 0
    [ "${ASSET_ENGINE_UNIRIG_ENV:-1}" = "1" ] || {
        say "skipping UniRig's environment (ASSET_ENGINE_UNIRIG_ENV=${ASSET_ENGINE_UNIRIG_ENV})"
        return 0
    }
    if [ -x "$py" ] && "$py" -c "$UNIRIG_ENV_TEST" >/dev/null 2>&1; then
        return 0
    fi
    if [ -e "$env" ]; then
        warn "UniRig's environment is incomplete or stale; rebuilding it"
        rm -rf "$env"
    fi
    say "building UniRig's environment, once (about 10GB under ${HOME:-/app/.home}/.ce)"
    mkdir -p "$(dirname "$log")" 2>/dev/null || true
    pair="$(python3 -c 'from importlib.metadata import version as v
print("spconv-cu124==" + v("spconv-cu124"), "cumm-cu124==" + v("cumm-cu124"))' 2>/dev/null)"
    if (cd "$node" && python3 install.py) >"$log" 2>&1 &&
        [ -n "$pair" ] &&
        "$py" -m pip uninstall -y spconv cumm >>"$log" 2>&1 &&
        "$py" -m pip install $pair >>"$log" 2>&1 &&
        "$py" -c "$UNIRIG_ENV_TEST" >>"$log" 2>&1; then
        say "  UniRig's environment is ready ($pair)"
    else
        warn "could not build UniRig's environment; its nodes will fail. Log: $log"
    fi
}
build_unirig_env

# --- 2. report on the weights ---------------------------------------------

# ASSET_ENGINE_FETCH_GROUPS names the models.json groups to check, and with
# ASSET_ENGINE_FETCH_MODELS=1 to download: "core" when unset. Nothing beyond
# core arrives unless it is named, because a group is up to tens of GB and
# each model's licence binds you from the moment it downloads; the Krea 2
# Community License says so in its first paragraph. So
# ASSET_ENGINE_FETCH_GROUPS="core krea2" with ASSET_ENGINE_FETCH_MODELS=1 is
# an explicit choice to take Krea 2 on its terms. The weights land in the
# MODELS_DIR mount, so they are fetched once, not on every start. A model
# whose licence forbids commercial use is still refused, as on the host.
#
# The weights are not baked into the image instead: compose mounts MODELS_DIR
# over /app/models, which would hide a baked copy, and an image carrying Krea
# 2 would be a distribution of it, under section 3 of its licence.
if [ "${ASSET_ENGINE_CHECK_MODELS:-1}" = "1" ] && [ -x /opt/asset-engine/scripts/fetch_models.py ]; then
    fetch_groups="${ASSET_ENGINE_FETCH_GROUPS:-core}"
    group_args=()
    for g in ${fetch_groups//,/ }; do group_args+=(--group "$g"); done
    [ ${#group_args[@]} -gt 0 ] || group_args=(--group core)
    if [ "${ASSET_ENGINE_FETCH_MODELS:-0}" = "1" ]; then
        say "fetching any missing models in: $fetch_groups (ASSET_ENGINE_FETCH_MODELS=1)"
        say "  each model's licence binds you from download; fetch_models.py --licenses lists them"
        python3 /opt/asset-engine/scripts/fetch_models.py --download "${group_args[@]}" || \
            warn "model fetch failed; starting anyway"
    else
        python3 /opt/asset-engine/scripts/fetch_models.py "${group_args[@]}" || true
        say "set ASSET_ENGINE_FETCH_MODELS=1 to download the missing ones on boot"
    fi
fi

# --- 3. over to ComfyUI ----------------------------------------------------

say "ComfyUI on :8188"
exec "$@"
