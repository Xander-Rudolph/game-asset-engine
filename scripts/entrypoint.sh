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
#      carry, because its licence forbids distributing part of it (1b below).
#
#   3. Say what weights are missing, by name, before the server starts.
#      Models are the one thing too large to bake (the set is ~274GB), so
#      the next best thing is refusing to be quiet about it: a missing
#      checkpoint otherwise shows up as a red node an hour later.
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

# --- 2. report on the weights ---------------------------------------------

if [ "${ASSET_ENGINE_CHECK_MODELS:-1}" = "1" ] && [ -x /opt/asset-engine/scripts/fetch_models.py ]; then
    if [ "${ASSET_ENGINE_FETCH_MODELS:-0}" = "1" ]; then
        say "fetching any missing models (ASSET_ENGINE_FETCH_MODELS=1)"
        python3 /opt/asset-engine/scripts/fetch_models.py --download || \
            warn "model fetch failed; starting anyway"
    else
        python3 /opt/asset-engine/scripts/fetch_models.py || true
        say "set ASSET_ENGINE_FETCH_MODELS=1 to download the missing ones on boot"
    fi
fi

# --- 3. over to ComfyUI ----------------------------------------------------

say "ComfyUI on :8188"
exec "$@"
