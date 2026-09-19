# The MCP server

Every capability in this repo is a command-line script, so driving the pipeline
has always needed a shell. `mcp/server.py` wraps the scripts that are safe to
expose as Model Context Protocol tools, so a client that has no shell, or that
is not on this machine, can check the engine, look at what is on disk, queue a
graph, render a sprite sheet and cut lip sync cues without ever being handed a
command line.

It is one Python file, standard library only. It speaks MCP over stdin and
stdout by default, and serves the same 23 tools over HTTP when you ask it to.

::: danger The Docker socket it needs is root on this host
The Blender tools work by running `docker exec` against the ComfyUI container,
and `scripts/_engine.py` finds that container with `docker ps`. Both go through
`/var/run/docker.sock`.

Anything that can talk to that socket can start a container that mounts the
whole host filesystem as root. So socket access is root on the host, and the
non-root uid the container runs as bounds nothing at all. Give this server, and
every client that can call it, the trust you would give root on this machine.
Not less.

That is also why the HTTP port stays on the loopback address. The compose entry
publishes `127.0.0.1:8765:8765`, so only this host can reach it. The server has
no authentication of its own, so publishing it on `0.0.0.0` would hand the host
to everything on the network.

Running the server straight from a shell, as the registration commands below
do, inherits your own Docker access rather than adding any. The socket is still
what the Blender tools use, and it is still root on this host.
:::

## Check it runs before you register it

From the repo root:

```sh
python3 mcp/server.py --list-tools     # the tools, one line each
python3 mcp/selftest.py                # the protocol, over both transports
```

The selftest starts a copy of the server on a pipe, speaks MCP to it, calls
read-only tools, checks that a path outside the allowed folders and a badly
typed argument come back as messages rather than tracebacks, then does the same
over HTTP on a free port. It queues no generation job and runs no Blender job,
so it is safe to run while somebody else is using the graphics card.

24 checks, 19 over stdio and 5 over HTTP, all passing in 7.6 seconds on the
reference machine (`time python3 mcp/selftest.py`, 2026-09-19). Exit 0 when
everything passed.

## What it serves

23 tools in four groups, each one wrapping a script in this repo
(`python3 mcp/server.py --list-tools`, 2026-09-19). The one-line description of
each lives in the server rather than on this page, so `--list-tools` is the
list that cannot go stale.

| Group | Tools | What a call costs |
| --- | --- | --- |
| Read-only | `engine_health`, `list_graphs`, `validate_graphs`, `list_models`, `list_animation_clips`, `list_prompt_folders`, `list_assets`, `inspect_sprite_sheet`, `inspect_daz_library`, `daz_library_list` | Seconds. Reads files on disk, or asks the running ComfyUI what it loaded. |
| Queue | `run_graph`, `queue_status`, `interrupt_job`, `free_models` | `run_graph` queues a graph on the shared ComfyUI server and waits for it, so it costs minutes and the graphics card. The other three are immediate. |
| Blender | `render_sprite_sheet`, `bone_roles_map`, `bone_roles_compile`, `face_rig_add_jaw`, `decimation_report`, `normalise_mesh` | Minutes, inside the ComfyUI container, through the Docker socket. |
| Lip sync | `lipsync_cues`, `compose_mouths`, `preview_lipsync` | Seconds to a few minutes on the CPU. `lipsync_cues` and `preview_lipsync` need ffmpeg. |

A client that calls `engine_health` first gets the same report every skill in
this repo starts with, which is the point: almost every confusing failure here
is Docker, the GPU runtime, the container, the server, the node packs, Blender
or the output folders, and the health check looks at all of them.

Two runs through the server on 2026-09-19, on the reference machine:

- `render_sprite_sheet` on `output/assets/alchemist_warrior/model.glb`, 2 angles
  at 96 px, 16 samples, Cycles on the card, finished in 0.9 seconds.
- `engine_health` called from inside the container, which is what proves the
  Docker socket route works at all: the full health check ran, and reported
  ComfyUI answering with 944 node types and bpy 4.5.9 LTS in the container. The
  same two numbers came back from the host on the same day
  (`scripts/doctor.py --skip-models`).

### What is deliberately absent

Nothing here deletes, uninstalls or publishes:

- no `cleanup.py sweep` and no `cleanup.py keep`, because the sweep removes
  files and curating decides what a finished asset is, which is a person's call
- no `daz_library.py install` or `uninstall`
- no `fetch_models.py --download`, which writes tens of gigabytes and would
  accept, on your behalf, licences a person has to accept
- no `publish_image.sh`
- no container start, stop or restart
- no arbitrary file read or write

A client that needs one of those uses a shell, where a person can see what it is
about to do.

### The safety rules it enforces

Read from `mcp/server.py` on 2026-09-19, and exercised by the selftest:

- Every path argument is resolved, symlinks and all, and refused unless it lies
  under `output/`, `input/` or the models directory. Anything written is refused
  unless it lies under `output/`.
- A graph is named, not pathed. `run_graph` takes `txt2img_sdxl` and resolves it
  inside `workflows/api/`, so a path cannot escape through it. Role pose files
  and prompt folders work the same way.
- No subprocess is ever run through a shell. Every command is an argument list,
  so nothing a caller sends is parsed as shell syntax.
- Every tool has a timeout and takes its own `timeout` argument in seconds.
- One result is capped at 40,000 characters (`ASSET_ENGINE_MCP_MAX_CHARS`).
- A tool reports the files it wrote by path and size. It never returns their
  bytes.

## Register it with Claude Code

One command, using the config published with this site:

```sh
claude mcp add-json asset-engine "$(curl -fsSL https://xander-rudolph.github.io/game-asset-engine/mcp/asset-engine.json)"
```

From a checkout, the same bytes without the network:

```sh
claude mcp add-json asset-engine "$(cat docs/public/mcp/asset-engine.json)"
```

Either way, check it and then look at what it offers:

```sh
claude mcp list          # asset-engine: ... - ✔ Connected
claude mcp get asset-engine
claude mcp remove asset-engine
```

`claude mcp list` health-checks each configured server by starting it and
completing the handshake, so a ✔ Connected means the server really ran.

Or write the command out by hand. The `--` is required: without it Claude Code
tries to parse the server's own flags as its own
([Claude Code MCP documentation](https://code.claude.com/docs/en/mcp), read
2026-09-19).

```sh
claude mcp add --transport stdio asset-engine -- /usr/bin/python3 /asset-engine/mcp/server.py
```

That plain form passes no environment, so the server falls back to its own
defaults: `ASSET_ENGINE_ROOT=/asset-engine`, `MODELS_DIR` read from the repo's
`.env`, and `COMFY_URL=http://127.0.0.1:8188`. Use the published config instead
if any of those is wrong for you.

### Which paths you must change

The published config defaults to this machine's layout. Two things to check
before you register it anywhere else:

- **`/asset-engine` is the repo root here.** If your checkout is somewhere
  else, export `ASSET_ENGINE_ROOT` before registering.
- **`/usr/bin/python3` is the system Python.** The repo's scripts want it, not
  `.venv`, which is the notebook kernel and has no numpy. Export
  `ASSET_ENGINE_PYTHON` if yours is elsewhere.

A wrong root is not silent, and the message names the variable. Measured by
calling `list_graphs` with `ASSET_ENGINE_ROOT=/tmp/not-the-repo` on 2026-09-19:

```
list_graphs could not run: no graphs found under /tmp/not-the-repo/workflows/api. Is ASSET_ENGINE_ROOT right? It is currently /tmp/not-the-repo.
```

### The variables the config reads

Each one is `${VAR:-default}`, so exporting it in the shell you run
`claude mcp add-json` from is what overrides it. Claude Code expands `${VAR}`
and `${VAR:-default}` in a server's `command`, `args` and `env`
([Claude Code MCP documentation](https://code.claude.com/docs/en/mcp), read
2026-09-19).

| Variable | Default in the config | Export it when |
| --- | --- | --- |
| `ASSET_ENGINE_ROOT` | `/asset-engine` | Your checkout is somewhere else. |
| `ASSET_ENGINE_PYTHON` | `/usr/bin/python3` | Your system Python is somewhere else. It is passed on to the scripts as well as used to start the server, so a virtualenv Python does not get picked up by accident. |
| `MODELS_DIR` | empty | You want to override `.env`. Empty is deliberate: the server then reads `MODELS_DIR` out of the repo's `.env` and resolves a relative value against the repo root, exactly as `scripts/fetch_models.py` and compose do. |
| `COMFY_URL` | `http://127.0.0.1:8188` | ComfyUI is on another host or port. |
| `ASSET_ENGINE_CONTAINER` | empty | Several ComfyUI containers are up and you mean a particular one. Empty means `scripts/_engine.py` asks `docker ps`. |

### Which scope to register it in

Read from the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp)
on 2026-09-19:

| Scope | Loads in | Stored in | Approval |
| --- | --- | --- | --- |
| `local`, the default | this project only, private to you | `~/.claude.json` | none |
| `project` | this project, shared through version control | `.mcp.json` in the repo root | every user is prompted before it is used; `claude mcp reset-project-choices` resets those answers |
| `user` | all your projects | `~/.claude.json` | none |

```sh
claude mcp add-json asset-engine "$(cat docs/public/mcp/asset-engine.json)" --scope user
```

`user` is the scope to want if you drive several game repos from one machine,
because the server is a property of the machine rather than of a project.

::: warning Do not put this one in .mcp.json
`.mcp.json` at the plugin root ships to everyone who installs this repo as a
plugin, and it would hand each of them a server that wants the Docker socket.
`.mcp.json` here is for [Meshy](/reference/skills#mcp-servers), a hosted service
that needs an API key and nothing local.
:::

### Timeouts worth knowing about

Claude Code's own limits, not the server's, read from the
[Claude Code MCP documentation](https://code.claude.com/docs/en/mcp) on
2026-09-19:

- `MCP_TIMEOUT` is the startup timeout, in milliseconds, set on the client:
  `MCP_TIMEOUT=10000 claude`.
- A tool call that sends no response and no progress notification for the idle
  window is aborted. That window defaults to 30 minutes for a stdio server and
  five minutes for an HTTP one, and
  `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` changes it, in milliseconds. It matters
  here because `run_graph` and the Blender tools return one result at the end
  and say nothing while they work: a long render over the HTTP route wants a
  larger window.

The server's own per-tool timeouts are separate, and every tool takes a
`timeout` argument in seconds that overrides its default.

## Run it in the container instead

The image is Alpine 3.21 pinned by tag and digest, seven packages, non-root,
275 MB (`docker images asset-engine-mcp:dev`, 2026-09-19). It carries no CUDA,
no torch, no Blender and no ComfyUI: those are the pipeline image, and this one
reaches them over HTTP and through the Docker socket. The repo is not copied
in, it is bind-mounted, so a script you edit takes effect on the next call.

```sh
docker compose --profile mcp build
```

`mcp` is its own compose profile, so it starts with none of the pipeline
profiles and they start without it. `mcp/README.md` has the full build and run
detail, including the `docker run --rm -i` form for a client that starts the
server itself, and what to do when the socket says `permission denied`.

One thing the compose entry needs from you. The socket is `root:docker` mode
0660, and the container runs as your uid, which is not in that group inside the
container, so compose adds docker's gid as a supplementary group. That gid is
host-specific and the entry has to guess it, defaulting to 126, which is this
host's (`stat -c '%g' /var/run/docker.sock`, 2026-09-19). If yours differs, put
it in `.env`:

```sh
DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
```

## The HTTP route, and its limits

For a client that cannot start a process, or for several clients sharing one
server. Compose owns it:

```sh
docker compose --profile mcp up -d
```

That serves the same 23 tools on `http://127.0.0.1:8765`. Without compose, on
the host:

```sh
python3 mcp/server.py --http --port 8765
```

What it is and is not, measured on 2026-09-19 by posting to it with `curl` and
by `python3 mcp/selftest.py`:

- **It answers POST only.** One JSON-RPC message in, one JSON response out. A
  GET returns 405.
- **No server-sent events, no resumable streams, no session identifiers.** A
  client that requires the streamable HTTP transport's full shape will not be
  happy with it.
- **No authentication of its own.** None at all. The loopback bind is the whole
  access control.
- **It binds `127.0.0.1` by default.** Inside a container that is the
  container's own loopback, which a published port cannot reach, so the compose
  entry passes `--host 0.0.0.0` and publishes `127.0.0.1:8765:8765`. The
  published address is what keeps it private, not the bind address.
- **Anything other than the loopback needs a TLS reverse proxy in front of it,
  doing the authorisation.** The MCP specification requires https for a remote
  transport except on localhost, and this server speaks plain HTTP
  (`mcp/server.py`, read 2026-09-19).

## Why this is not shipped in the plugin

A Claude Code plugin can carry MCP servers, and then they start for everyone
who enables the plugin, with no per-server opt out
([Claude Code MCP documentation](https://code.claude.com/docs/en/mcp), read
2026-09-19). A server that wants the Docker socket is not something an
installer should acquire as a side effect of installing a plugin, so this one is
registered by hand.

There is no one-click install for a bare MCP server, no URL scheme, no deep link
and no registry the CLI reads. A published config file and one
`claude mcp add-json` command is the shortest honest route there is, which is
what the command at the top of this page is.

The plugin itself, and the nine skills that drive the same pipeline from a
shell, are in [installing it for Claude](/guide/claude).
