# Docker and versions

Every version here is pinned, and they depend on each other. Change one and the
next breaks. This page explains the chain so you can make deliberate changes
instead of accidental ones.

## The dependency chain

**The host driver determines CUDA.** A 550-series driver caps out at CUDA 12.4,
because consumer cards get no forward compatibility.

**CUDA determines Python and PyTorch.** The 3D node pack doesn't compile its
CUDA extensions. It downloads prebuilt wheels from a separate wheel repository,
picking the set that matches your operating system, Python, torch and CUDA
version. The only set for Linux and CUDA 12.4 in that repository is for
Python 3.11 and torch 2.6.0.

So we use **Python 3.11, torch 2.6.0, CUDA 12.4**, not the torch 2.7.0 and
CUDA 12.8 that the pack's build config asks for by default. Those need a newer
driver, so the Dockerfile rewrites that config during the build.

If you change any of these three, the installer silently falls back to
compiling several large CUDA libraries from source, which takes an hour. That's
why the base image is a development image with the CUDA compiler in it.

**PyTorch determines the ComfyUI version.** We use ComfyUI v0.30.2, not the
latest. A dependency (`comfy-kitchen`) uses type hints that torch 2.6 rejects,
so the server dies on start-up before a single node loads:

```
ValueError: infer_schema(func): Parameter kernel_size has unsupported type list[int]
```

The last `comfy-kitchen` release that runs on torch 2.6 is 0.2.26. It is pinned
in the constraints file next to torch, so no later `pip install` can move it.
v0.30.2 is the newest ComfyUI release that pins that version, and it still has
the API the rigging nodes need.

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

::: warning A mounted host folder hides what the image has
Mounting an empty `./custom_nodes` folder hides the nodes baked into the image.
The packaged profile doesn't mount source at all. Under the `comfy` profile, the
start-up script copies the baked nodes in only when the folder is empty, so a
fresh checkout works and your edits are never overwritten.
:::

## Node packs

Under the `comfy` profile, `custom_nodes/` is mounted from the host. The image
holds each pack's **compiled dependencies**, and the host holds the **source
code** ComfyUI imports. Keep the node pack commits in the Dockerfile and
`setup.sh` the same. If they drift, you get import errors that don't point to
the real problem.

The rigging pack has its own bundled Blender in an isolated environment. That's
why it's installed by `postinstall.sh` in the **running container**, not during
image build. If it were built at image time, the host mount would hide it. Its
first run is slow and needs network access.

## Publishing the image

```sh
scripts/publish_image.sh 0.1.2
scripts/publish_image.sh 0.1.2 --dry
```

We build locally, not in CI. The image is 27.6GB. A hosted runner has only
about 14GB free on the disk Docker stores images on, so the build dies partway
through the CUDA layers with `no space left on device`.

Log in once first. The token needs package write permission:

```sh
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <you> --password-stdin
```

Two things to know about the build:

**Finish editing before you build.** The build reads all files when it starts.
Changes made during the build don't make it in, even if the copy instruction is
near the end. The first shipped image had an outdated start-up script for exactly
this reason.

**A named volume is not a mounted host folder.** Docker fills an empty named
volume from the image on first use, so the packaged profile's workflows arrive
even if the start-up script's seeding is broken. An empty host folder gets no
such help. It hides the image's copy, and only the seeding fills it. Test both,
because only the empty host folder case runs the seeding.

## Environment

`.env`, never committed:

| Variable | For |
|---|---|
| `MODELS_DIR` | Where weights live. Resolved relative to the compose file, like any relative bind mount. |
| `PUID`, `PGID` | Your `id -u` and `id -g`. Get these wrong and output lands owned by root. |
| `COMFY_URL` | Where the server answers. Defaults to `http://127.0.0.1:8188`. |
| `HF_TOKEN` | For the gated weight group. |
| `ASSET_ENGINE_FETCH_MODELS` | Set to 1 to have the container fetch missing weights on boot. |
