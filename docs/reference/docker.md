# Docker and versions

Every version in this stack is pinned, and the pins are a chain. Changing one
breaks the next. This page says why, so the chain can be escaped deliberately
rather than by accident.

## The chain

**The host driver decides CUDA.** On a 550 series driver, CUDA cannot go above
12.4, because consumer cards get no forward compatibility.

**CUDA decides Python and torch.** The 3D node pack does not compile its CUDA
extensions. It downloads prebuilt wheels keyed on operating system, Python
version, torch version and CUDA version. The only Linux plus CUDA 12.4 set that
repository publishes is for Python 3.11 and torch 2.6.0.

So: **Python 3.11, torch 2.6.0, CUDA 12.4**, not the 3.12, 2.7.0 and 12.8 that
the pack's own README defaults to. The Dockerfile rewrites that config during the
build.

Change any one of the three and the installer silently falls back to compiling
several large CUDA libraries from source. That is why the base image is a
development image carrying the CUDA compiler, and why the build takes an hour
when it happens.

**Torch decides the ComfyUI version.** ComfyUI is held at v0.30.2, not master. A
dependency declares torch custom operations using builtin generic type hints, and
torch 2.6 rejects those. The server dies on import before a single node loads:

```
ValueError: infer_schema(func): Parameter kernel_size has unsupported type list[int]
```

The last version of that dependency which runs on torch 2.6 is pinned in the
constraints file alongside torch, so nothing can bump it back. v0.30.2 is the
newest ComfyUI release pinning it, and it still ships the API that the rigging
nodes are written against.

## How to escape the pin

In order of likelihood:

1. The wheel repository publishes a Linux CUDA 12.4 set for a newer torch.
2. The host driver reaches 580 or above, the whole stack moves to CUDA 12.8, the
   Python 3.12 and torch 2.7.0 wheel set becomes available, and ComfyUI can track
   master again.

## Profiles

| Profile | For |
|---|---|
| `packaged` | The published image. Mounts no source. |
| `comfy` | Built from source. Node source lives on the host and is bind mounted. |
| `comfy-local` | The same, offline. DNS is blackholed and dependencies are baked in. |

```sh
docker compose --profile packaged up -d
docker compose --profile comfy up -d
docker compose --profile comfy logs -f
```

::: warning A bind mount replaces, it does not merge
Mounting an empty `./custom_nodes` over the baked one is exactly how you get a
server with no nodes in it. The packaged profile therefore mounts no source. The
`comfy` profile's entrypoint seeds an empty mount from the image's own copy and
leaves a non empty one alone, so both a fresh checkout and an edited one work.
:::

## Node packs

`custom_nodes/` is bind mounted under the `comfy` profile, so the image holds
each pack's **compiled dependencies** while the host holds the **source ComfyUI
imports**. Keep the node pack revision in the Dockerfile and in `setup.sh` in
step. Drift between them shows up as an import error with no obvious cause.

The rigging pack installs into an isolated environment with its own bundled
Blender, which is why it is built by `postinstall.sh` inside the **running**
container rather than at image build time. Built during the image build it would
land in a layer that the host mount then hides. Its first run is slow and needs
the network.

## Publishing the image

```sh
scripts/publish_image.sh 0.1.0
scripts/publish_image.sh 0.1.0 --dry
```

Built locally rather than in CI on purpose. The image is 27.5GB and a hosted
runner gives you about 14GB free on the volume Docker's data root lives on, so
the build dies partway through the CUDA layers with no space left.

Log in once first. The token needs package write permission:

```sh
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <you> --password-stdin
```

Two things about that build each cost a round trip to learn:

**BuildKit reads the whole context when the build starts.** Editing a file while
a long build runs does not reach the image, even if the instruction that copies it
is second to last. The first image shipped with a superseded entrypoint for
exactly this reason. Finish editing, then build.

**A named volume is not a bind mount.** Docker copies the image's content into an
empty named volume on first use, so the packaged profile's workflows arrive
whether or not anything seeds them. An empty bind mount gets no such help. It
hides the image's copy, which is what the entrypoint's seeding is for. Test both
paths, because only one of them exercises that code.

## Environment

`.env`, never committed:

| Variable | For |
|---|---|
| `MODELS_DIR` | Where weights live. Resolved relative to the compose file, like any relative bind mount. |
| `PUID`, `PGID` | Your `id -u` and `id -g`. Get these wrong and output lands owned by root. |
| `COMFY_URL` | Where the server answers. Defaults to `http://127.0.0.1:8188`. |
| `HF_TOKEN` | For the gated weight group. |
| `ASSET_ENGINE_FETCH_MODELS` | Set to 1 to have the container fetch missing weights on boot. |
