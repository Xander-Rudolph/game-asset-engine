# The MCP server's container

How to build and run the image that `mcp/server.py` runs in. What the server
itself serves is not this file's business.

## Read this first: the Docker socket is root on the host

This container is given `/var/run/docker.sock`. It has to be: the Blender tools
drive Blender by running `docker exec` against the ComfyUI container, and
`scripts/_engine.py` finds that container with `docker ps`. Both go through the
socket.

Anything that can talk to the Docker socket can start a container that mounts
the whole host filesystem as root. So socket access is root on the host, and the
non-root uid inside this container bounds nothing at all. Two consequences worth
stating plainly:

- Give this container, and the clients that can call it, the trust you would
  give root on this machine. Not less.
- Keep the HTTP port on the loopback address. The compose entry publishes
  `127.0.0.1:8765:8765`, so only this host can reach it. Publishing it on
  `0.0.0.0` instead would hand the host to everything on the network, and the
  server has no authentication of its own to stop that.

If you want the server without that, drop the socket mount: the tools that only
talk to ComfyUI over HTTP keep working and the Blender ones stop.

## Build

    docker build -f mcp/Dockerfile -t asset-engine-mcp:dev mcp

Or, through compose, which tags it the same way:

    docker compose --profile mcp build

The build context is `mcp/`, not the repo, and `mcp/.dockerignore` excludes
everything in it. The image copies no repo file: the repo arrives as a bind
mount, so a script you edit takes effect on the next call rather than the next
build, and the image does not go stale when the repo moves.

Measured on the reference machine (`docker build --no-cache`, then
`docker images asset-engine-mcp:dev`, 2026-09-19): 6 seconds, 275 MB. The
pipeline image at the repo root is 27.6 GB and this is not a smaller version of
it: there is no CUDA, no torch, no Blender and no ComfyUI here. Seven packages
on Alpine 3.21, pinned by tag and digest: python3 (3.12.14), docker-cli (27.3.1,
the client alone, never a daemon), ffmpeg (6.1.2, which brings ffprobe), bash
(5.2.37, because every `scripts/*.sh` asks for it by shebang and several use
bashisms busybox ash does not have), curl (8.14.1, which `asset_to_mesh.sh`
polls ComfyUI with), py3-numpy (2.1.3) and py3-pillow (11.0.0).

## Run it over stdio, for a client on this machine

The default. The server speaks MCP over stdin and stdout, the client starts it,
and nothing listens on a port. `-i` is required, because without it the client's
stdin never reaches the server; `--rm` because one of these exists per client
session.

    docker run --rm -i \
      --user "$(id -u):$(id -g)" \
      --group-add "$(stat -c '%g' /var/run/docker.sock)" \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v "$PWD":/asset-engine \
      -v /models:/models \
      --add-host host.docker.internal:host-gateway \
      -e ASSET_ENGINE_ROOT=/asset-engine \
      -e MODELS_DIR=/models \
      -e COMFY_URL=http://host.docker.internal:8188 \
      asset-engine-mcp:dev

Run that from the repo root, and give `-v /models:/models` whatever `MODELS_DIR`
in `.env` actually points at. That is the whole command a client's MCP config
has to hold: the image name is the last argument, and anything after it is
appended to the server's own arguments.

## Run it over HTTP, for a client that connects to it

For a client that cannot start a process, or for several clients sharing one
server. Compose owns this one:

    docker compose --profile mcp up -d
    docker compose --profile mcp logs -f

It serves the same tools on `http://127.0.0.1:8765`. POST the JSON-RPC frames
there; GET answers 405. The `mcp` profile is its own: `docker compose --profile
packaged up -d` and the two `comfy` profiles do not start it, and it does not
start them.

Two arguments in that service entry look wrong and are not:

- `--host 0.0.0.0`. The server binds `127.0.0.1` by default, which inside a
  container is the container's own loopback and not an address a published port
  can reach. With the default, a POST to `127.0.0.1:8765` on the host is refused
  while the container's log cheerfully says `http on 127.0.0.1:8765`. What keeps
  the server private is the `ports` entry, which publishes on `127.0.0.1` alone.
  The server prints a warning about binding off-loopback; inside a container it
  means "this host's loopback, and containers on this compose network".
- `COMFY_URL=http://host.docker.internal:8188`. Every script here falls back to
  `http://127.0.0.1:8188`, which in a container is the container. Without this
  the failure reads as `nothing answering at http://127.0.0.1:8188`, as though
  ComfyUI were down. `extra_hosts` is what makes that name resolve to the host
  on Linux.

`--profile mcp up` builds the image if it is not built yet. Stop it with
`docker rm -f asset-engine-mcp`, which is the one container this profile
started.

## The mounts, and why each one is there

| Mount | Why |
| --- | --- |
| `.:/asset-engine` | The repo, read-write. The server runs the scripts in `scripts/`, and those write into `output/`. Mounted at the same absolute path the repo has on the host, so a path in a tool call means the same thing on both sides of the socket. |
| `${MODELS_DIR}:/models` | The weights, and the Daz content library under `daz_library/`. The scripts read `MODELS_DIR` from the environment, or from `.env` when it is unset. `/models` is what `MODELS_DIR=../../models/` in `.env` resolves to from the repo root anyway, so the two agree. |
| `/var/run/docker.sock` | How `scripts/_engine.py` finds the ComfyUI container and runs Blender inside it. Root on the host. See the top of this file. |

## The environment it reads

| Variable | Set to | Meaning |
| --- | --- | --- |
| `ASSET_ENGINE_ROOT` | `/asset-engine` | Where the repo is mounted. Also the image's default. |
| `MODELS_DIR` | `/models` | Where the weights are mounted. |
| `ASSET_ENGINE_CONTAINER` | unset | Which ComfyUI container to drive. Left unset, `scripts/_engine.py` asks `docker ps` and takes the first of `comfyui`, `comfyui-packaged`, `comfyui-local` that is up. Set it when several are running and you mean a particular one. |
| `COMFY_URL` | `http://host.docker.internal:8188` | Where ComfyUI answers, seen from inside the container. Not optional: the fallback every script shares is `http://127.0.0.1:8188`, which in a container is the container. |

## When the Docker socket does not work

    permission denied while trying to connect to the Docker daemon socket at
    unix:///var/run/docker.sock: Get "http://%2Fvar%2Frun%2Fdocker.sock/v1.47/
    containers/json": dial unix /var/run/docker.sock: connect: permission denied

(One line really, wrapped here. Measured by running the image's `docker ps` as
uid 1000 with no supplementary group, 2026-09-19.)

The socket is `root:docker` mode 0660, and the container runs as your uid, which
is not in that group inside the container. Both commands above add docker's gid
as a supplementary group, but the compose entry has to guess it: it defaults to
126, which is this host's (`stat -c '%g' /var/run/docker.sock`, 2026-09-19). If
yours differs, put it in `.env`:

    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)

Do not answer this by running the container as root. It would not make the
container safer, and it would make every file the pipeline writes into `output/`
root-owned, which is the thing `PUID`/`PGID` exist to prevent.
