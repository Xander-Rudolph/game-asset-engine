# The container the MCP server runs in: the host half of the pipeline, and
# nothing else.
#
# READ THIS BEFORE YOU RUN IT. This container is given the host's Docker socket
# (see docker-compose.yml, profile `mcp`), because the Blender tools work by
# running `docker exec` against the ComfyUI container. A process that can talk
# to the Docker socket can start a container that mounts the whole host
# filesystem as root, so socket access is root on the host, whatever uid this
# container runs as. Give this container to code and to clients you would give
# root to, and to no others. It binds its HTTP port to 127.0.0.1 for the same
# reason: nothing outside this machine should be able to reach it.
#
# What is NOT here, deliberately: CUDA, torch, Blender, ComfyUI, the node packs,
# the weights. That is the pipeline image (27.6 GB, built from the Dockerfile at
# the repo root), and it stays where it is. The scripts in scripts/ are host
# scripts: they talk to ComfyUI over HTTP and drive Blender with `docker exec`,
# so all this image owes them is python3, a Docker client, bash, ffmpeg, curl
# and two third-party Python packages. Checked against what the scripts actually import
# and exec (`grep -hoE "^(import|from) [a-z_.]+" scripts/*.py` and a grep for
# "ffmpeg", "ffprobe" and "docker" in scripts/, 2026-09-19): stdlib everywhere,
# plus numpy and PIL in compose_mouths.py, sheet_check.py, make_seamless.py,
# make_loop.py, preview_lipsync.py, cut_icon.py, normalise_mesh.py,
# decimation_report.py and render_sheet.py. The eight scripts/*.sh are all
# `#!/usr/bin/env bash`, and four of them use bashisms busybox ash does not
# have, so bash is not optional here.
#
# The repo is NOT copied in. It is bind-mounted at /asset-engine, so editing a
# script or adding a workflow takes effect on the next call and this image does
# not go stale the moment the repo moves. Nothing in here needs rebuilding
# unless the tool list above changes.

# Pinned by tag AND digest: the tag says which Alpine this is meant to be, the
# digest says which one it actually was. `docker pull alpine:3.21`, 2026-09-19.
ARG ALPINE_TAG=3.21
ARG ALPINE_DIGEST=sha256:ce64758a109eb420d874a118f87920e625e12d3634e03b4a5573fd9f6e5d3507
FROM alpine:${ALPINE_TAG}@${ALPINE_DIGEST}

# One layer, no apk cache, and a reason for each of the seven:
#
#   python3      runs mcp/server.py and every script in scripts/. Alpine 3.21
#                ships 3.12.14 (`python3 -VV` in the image, 2026-09-19).
#   docker-cli   the CLIENT only, no daemon: scripts/_engine.py finds the
#                ComfyUI container with `docker ps` and drives Blender inside it
#                with `docker exec`. The daemon it talks to is the host's,
#                through the mounted socket.
#   ffmpeg       brings ffprobe with it. Lip sync needs both on the host side:
#                lipsync_cues.py, preview_lipsync.py, make_loop.py and
#                generate_music.py all shell out to them, and doctor.py warns
#                when they are missing.
#   py3-numpy    the sprite-sheet, seamless-tile and audio-loop maths.
#   py3-pillow   every script that opens a PNG.
#   bash         every scripts/*.sh asks for it by shebang, and asset_to_mesh.sh,
#                generate_concepts.sh, entrypoint.sh and setup.sh use `[[`,
#                process substitution or `local`, none of which busybox ash has.
#                Under ash they fail as `syntax error: unexpected "("` rather
#                than as anything that names the real cause.
#   curl         asset_to_mesh.sh polls ComfyUI's /queue and /object_info with
#                it before it queues anything.
#
# numpy and Pillow come from apk rather than pip because Alpine is musl: a pip
# install of either compiles from source here unless a musllinux wheel happens
# to exist, and the distro packages are already built.
RUN apk add --no-cache \
        python3 \
        docker-cli \
        ffmpeg \
        py3-numpy \
        py3-pillow \
        bash \
        curl

# Non-root, and the same uid/gid convention the pipeline services use: compose
# passes `user: "${PUID:-1000}:${PGID:-1000}"` so that everything written into
# output/ is owned by whoever has to move it into the game. The user baked here
# is that default, 1000:1000, so the image is already non-root when it is run
# without compose. HOME is 0777 for the same reason the pipeline image makes its
# HOME 0777: a host with a different PUID gets a uid that owns nothing, and a
# Python that cannot write $HOME is a Python that fails in odd places.
RUN addgroup -g 1000 engine && \
    adduser -D -u 1000 -G engine -h /home/engine engine && \
    chmod 0777 /home/engine
USER 1000:1000

ENV HOME=/home/engine \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ASSET_ENGINE_ROOT=/asset-engine

# Where the repo is mounted, so a relative path in a tool call means what the
# caller thinks it means.
WORKDIR /asset-engine

# Only meaningful in HTTP mode (`--http --port 8765`). In the default stdio mode
# the server speaks MCP over stdin and stdout and listens on nothing. Compose
# publishes this on 127.0.0.1 only; see the note at the top.
EXPOSE 8765

# ENTRYPOINT not CMD, so flags append: `docker run ... asset-engine-mcp
# --http --port 8765` serves the same tools over HTTP, and no argument at all
# speaks MCP over stdin and stdout.
ENTRYPOINT ["python3", "/asset-engine/mcp/server.py"]

# Labels, in the same style as the pipeline image at the repo root: version,
# revision and date are passed in at build time rather than baked, and their
# defaults are obvious placeholders so an unlabelled image is visible as one.
ARG IMAGE_VERSION=dev
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
# ALPINE_TAG is declared above the FROM, which scopes it to the FROM alone.
# Re-declare it here or the base.name label expands to an empty string.
ARG ALPINE_TAG=3.21
#
# On the licence label: this image carries no code from this repo, because the
# repo is mounted rather than copied. What it does carry is its seven packages
# and the base, and their licences are what apk reports for them
# (`apk info --license python3 py3-numpy py3-pillow docker-cli ffmpeg bash curl
# alpine-baselayout`, 2026-09-19): PSF-2.0, BSD-3-Clause, custom:PIL,
# Apache-2.0, "GPL-2.0-or-later AND LGPL-2.1-or-later", GPL-3.0-or-later, curl
# and GPL-2.0-only. custom:PIL is the HPND-derived Pillow licence, which SPDX
# now calls MIT-CMU; "curl" is curl's own SPDX identifier.
# The repo's own Apache-2.0 scripts are NOT covered by this expression: they
# arrive over a bind mount and keep their own licence.
LABEL maintainer="Xanderu" \
      org.opencontainers.image.ref.name="game-asset-engine-mcp" \
      org.opencontainers.image.title="Game Asset Engine MCP server" \
      org.opencontainers.image.description="Runs mcp/server.py, which serves this repo's pipeline to MCP clients. Carries python3, the Docker CLI, ffmpeg, bash, curl, numpy and Pillow only: the repo, the weights and the GPU work all live outside it." \
      org.opencontainers.image.source="https://github.com/Xander-Rudolph/game-asset-engine" \
      org.opencontainers.image.url="https://xander-rudolph.github.io/game-asset-engine/" \
      org.opencontainers.image.documentation="https://github.com/Xander-Rudolph/game-asset-engine/blob/main/mcp/README.md" \
      org.opencontainers.image.vendor="Xanderu" \
      org.opencontainers.image.licenses="Apache-2.0 AND PSF-2.0 AND BSD-3-Clause AND MIT-CMU AND GPL-2.0-or-later AND LGPL-2.1-or-later AND GPL-3.0-or-later AND GPL-2.0-only AND curl" \
      org.opencontainers.image.base.name="alpine:${ALPINE_TAG}" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}"
