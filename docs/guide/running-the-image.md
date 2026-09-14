# Running the published image

The image is the whole install. It carries ComfyUI, the four node packs at pinned
commits with their compatibility patches applied, the Hunyuan texture extension
compiled, Blender as a Python module, and every workflow already in the editor
sidebar.

It is about 27.6GB and does **not** contain model weights.

```
ghcr.io/xander-rudolph/game-asset-engine-comfy:0.1.1
ghcr.io/xander-rudolph/game-asset-engine-comfy:latest
```

## Authenticating

A pull needs a GitHub token only while the package is private. While it is, log
in with a personal access token that has `read:packages` permission:

```sh
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <your-github-username> --password-stdin
```

::: warning Permission errors look like missing images
If the package is private and you're not logged in, `docker pull` reports
`denied` or `manifest unknown`, not a permission error. That looks like a wrong
tag. Check you're logged in before chasing the tag.
:::

## With compose, which is the short way

```sh
cp .env.example .env       # set MODELS_DIR, PUID and PGID
docker compose --profile packaged up -d
```

Then <http://localhost:8188>.

`scripts/doctor.py --fix` does the same thing and waits for the server to finish
loading, which takes a minute or two on a cold start.

## Without compose

Useful when you are running it somewhere the repo is not checked out. This is the
compose `packaged` profile written out in full:

```sh
docker run -d \
  --name comfyui-packaged \
  --gpus all \
  -p 8188:8188 \
  --shm-size 16g \
  --user "$(id -u):$(id -g)" \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -e PYOPENGL_PLATFORM=egl \
  -e HF_HOME=/app/models/.hf \
  -v /path/to/models:/app/models \
  -v /path/to/models/3d_checkpoints:/app/custom_nodes/ComfyUI-3D-Pack/Checkpoints \
  -v "$PWD/output:/app/output" \
  -v "$PWD/input:/app/input" \
  -v unirig-home:/app/.home \
  -v comfy-user:/app/user \
  ghcr.io/xander-rudolph/game-asset-engine-comfy:latest
```

Each flag solves a specific problem:

| Flag | Why |
|---|---|
| `--gpus all` | Required for generation |
| `--shm-size 16g` | The default 64MB is too small for the dataloaders, and the worker crash you get doesn't say why |
| `--user $(id -u):$(id -g)` | Without it, every mesh, sprite and sheet is owned by root, and you can't move it into your game without `sudo` |
| `PYOPENGL_PLATFORM=egl` | Enables headless rendering |
| `HF_HOME` inside the models mount | Keeps the Hugging Face cache with the weights. Otherwise it sits inside the container, and recreating the container loses it |
| `3d_checkpoints` mount | The 3D pack only looks for checkpoints inside its own node folder, so the ones in your models folder are mounted there |
| `unirig-home` volume | The rigging pack builds an environment of about 11GB on first use. A named volume keeps it through `down` and `--force-recreate` |
| `comfy-user` volume | Graphs you save in the editor live here. Without it, `down` or `--force-recreate` deletes them |

::: danger Don't mount an empty folder over custom_nodes
A mounted host folder replaces what the image has at that path. It doesn't add
to it. An empty `./custom_nodes` hides all the baked-in nodes. The packaged
profile doesn't mount source for this reason.
:::

## Weights are separate

The weight set is around 200GB and stays on your disk under `MODELS_DIR`. The
container reads `models.json` on boot and names anything missing **before** the
server starts, rather than letting it turn up as a red node an hour later.

```sh
scripts/fetch_models.py                    # check core; no weights, but seeds MODELS_DIR
scripts/fetch_models.py --download         # fetch the missing core models
scripts/fetch_models.py --download --group qwen   # the concept graphs need it, about 48GB
scripts/fetch_models.py --list-groups      # what groups exist, and their sizes
```

The [first asset walkthrough](/guide/first-asset#fetch-the-weights-once) also
uses the `trellis` and `hunyuan` groups and fetches them in its first step.

Or have the container fetch the core group itself on boot (about 20GB):

```sh
ASSET_ENGINE_FETCH_MODELS=1 docker compose --profile packaged up -d
```

## Checking it actually works

```sh
scripts/doctor.py
```

Eleven checks, including two that are easy to miss and expensive to discover late:
whether Blender is importable inside the container, and whether sparse
convolution imports. See [when something breaks](/guide/troubleshooting).

To look inside by hand:

```sh
docker exec comfyui-packaged python3 -c "import bpy; print(bpy.app.version_string)"
docker exec comfyui-packaged python3 -c "import spconv.pytorch; print('ok')"
curl -s localhost:8188/object_info | python3 -c "import json,sys; print(len(json.load(sys.stdin)), 'node types')"
```

A healthy server reports around 944 node types.

## Updating

```sh
docker compose --profile packaged pull
docker compose --profile packaged up -d
```

::: warning `docker image prune -a` is expensive here
It removes anything not used by a *running* container, which includes this image
when it is stopped. Getting it back is a 17GB download that unpacks to 27.6GB, or an hour of CUDA layers
if you rebuild. Prune by repository rather than with `-a` when clearing build
clutter.
:::

## Building it yourself

```sh
scripts/publish_image.sh 0.1.2
```

It builds locally rather than in CI on purpose: a hosted runner gives about 14GB
free on the volume Docker's data root lives on, so the build dies partway through
the CUDA layers. See [Docker and versions](/reference/docker) for the version
pins and why each one is what it is.

## Before you publish an image of your own

Publishing a container built from this repo redistributes the GPL software inside
it, and this repo's Apache-2.0 licence does not discharge those obligations on
your behalf. There are two separate duties and one of them is easy to miss.

[Read this first](/guide/redistributing).
