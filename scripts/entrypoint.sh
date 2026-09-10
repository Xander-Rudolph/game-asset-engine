#!/usr/bin/env bash
# What the packaged image does before it hands over to ComfyUI.
#
# Three jobs, in order:
#
#   1. Seed any bind mount that arrived empty. The image carries a pristine
#      copy of the node source, the workflows, the poses and the prompts at
#      /opt/athanor/seed. A bind mount HIDES whatever the image had at that
#      path, so a fresh checkout with empty custom_nodes/ and workflows/
#      would otherwise start a server with no nodes and no graphs -- the
#      exact "missing workflows" this image exists to prevent. Seeding is
#      skipped the moment a directory has anything in it, so a host copy the
#      user has edited is never overwritten.
#
#   2. Say what weights are missing, by name, before the server starts.
#      Models are the one thing too large to bake (the set is ~200GB), so
#      the next best thing is refusing to be quiet about it: a missing
#      checkpoint otherwise shows up as a red node an hour later.
#
#   3. exec the command, so ComfyUI is PID 1 and signals reach it.
#
# Nothing here is fatal. A missing model is worth saying loudly and worth
# starting anyway: most of the graphs do not need most of the weights.
set -euo pipefail

SEED=/opt/athanor/seed
say() { printf '\033[36m[athanor]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[athanor]\033[0m %s\n' "$*" >&2; }

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
# prompts stay at /opt/athanor, where the scripts read them from: copying
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

# --- 2. report on the weights ---------------------------------------------

if [ "${ATHANOR_CHECK_MODELS:-1}" = "1" ] && [ -x /opt/athanor/scripts/fetch_models.py ]; then
    if [ "${ATHANOR_FETCH_MODELS:-0}" = "1" ]; then
        say "fetching any missing models (ATHANOR_FETCH_MODELS=1)"
        python3 /opt/athanor/scripts/fetch_models.py --download || \
            warn "model fetch failed; starting anyway"
    else
        python3 /opt/athanor/scripts/fetch_models.py || true
        say "set ATHANOR_FETCH_MODELS=1 to download the missing ones on boot"
    fi
fi

# --- 3. over to ComfyUI ----------------------------------------------------

say "ComfyUI on :8188"
exec "$@"
