# Install and first run

There are two ways in. Use the prebuilt image unless you need to change node
source code.

## Check what you have first

Before installing anything, run the health check. It works even when nothing is
set up yet, and it tells you the one thing to do next rather than listing
everything at once.

```sh
scripts/doctor.py
```

Output looks like this when everything is ready:

```
  [  ok  ] docker       engine 27.5.1
  [  ok  ] gpu runtime  nvidia runtime registered with docker
  [  ok  ] .env         MODELS_DIR=/models
  [  ok  ] image        ghcr.io/athanorgames/athanor-comfy:latest
  [  ok  ] container    comfyui is up 3 hours
  [  ok  ] server       http://127.0.0.1:8188 answering, 943 node types loaded
  [  ok  ] node packs   3D-Pack and UniRig both loaded
  [  ok  ] blender      bpy 4.5.9 LTS in the container
  [  ok  ] folders      output, input and logs are writable

  Ready. Nothing to fix.
```

Add `--fix` and it will do the safe parts itself: write your `.env`, start the
container, and wait for the server to finish loading.

```sh
scripts/doctor.py --fix
```

::: tip Run this before blaming a workflow
Most confusing failures in this pipeline are one of six ordinary things: no
Docker, no GPU runtime, no `.env`, no image, container stopped, or weights
missing. All six show up much later as something that looks like a broken
graph. Two seconds of checking removes the guessing.
:::

## The prebuilt image

Everything except the weights, already built.

```sh
cp .env.example .env       # then set MODELS_DIR to where weights should live
docker compose --profile packaged up -d
```

That is the whole install. The image carries ComfyUI, all four node packs at
pinned commits with their compatibility patches applied, the Hunyuan texture
extension compiled, and every workflow already in the editor sidebar.

Open <http://localhost:8188> when it is up.

### Weights are not in the image

The weight set is around 200GB, so it stays on your disk under `MODELS_DIR`. The
container reads `models.json` on boot and names anything missing before the
server starts, rather than letting it turn up as a red node an hour later.

To have it fetch them itself:

```sh
ATHANOR_FETCH_MODELS=1 docker compose --profile packaged up -d
```

Or fetch them yourself, in groups:

```sh
scripts/fetch_models.py                    # report on the core group
scripts/fetch_models.py --download         # fetch the missing core models
scripts/fetch_models.py --list-groups      # what groups exist and their sizes
```

A file counts as present only when its size matches what the hub reports. A
half finished download gets fetched again rather than silently loaded and
crashed on. Downloads resume.

::: warning The packaged image mounts no source
A bind mount replaces a path rather than merging with it. Mounting an empty
`./custom_nodes` over the baked one is exactly how you get a server with no
nodes in it. Use the `comfy` profile below when you want to edit node source.
:::

## Building from source

Use this when you need to change node source code on the host.

```sh
scripts/setup.sh --all      # nodes, models, image, container, post-install
```

That script is safe to re-run at any time. To do the steps by hand:

```sh
docker compose --profile comfy up -d        # connected, can download
docker compose --profile comfy down
docker compose --profile comfy-local up -d  # offline, DNS blackholed
docker compose --profile comfy logs -f
```

The `comfy` profile seeds an empty `custom_nodes` mount from the image's own
copy and leaves a non-empty one alone, so both a fresh checkout and an edited
one work.

## Set your user id

In `.env`:

```
PUID=1000
PGID=1000
```

Use your own `id -u` and `id -g`. Get this wrong and every generated mesh,
sprite and sheet lands in `output/` owned by root, and you cannot move it into
your game without `sudo`.

## Where things live

```
.env                  your settings, never committed
models.json           the weight manifest
docker-compose.yml    the profiles
Dockerfile            CUDA 12.4, Python 3.11, torch 2.6.0, the node packs
scripts/              one script per stage
workflows/api/        the graphs, in the format the server accepts
prompts/              prompt libraries by subject type
poses/                hand authored animation poses
input/ output/        uploads in, images and models out
```

`output/` and `input/` are not tracked in git. Neither is `.env`.

## Publishing a new image

```sh
scripts/publish_image.sh 0.1.0
```

It builds locally rather than in CI on purpose. The image is 27.5GB and a hosted
runner has nothing like the disk for it.

Two things about that build each cost a round trip to learn:

- BuildKit reads the whole build context when the build starts. Editing a file
  while a long build runs does not reach the image, even if the `COPY` that
  takes it is the second to last instruction. The first image shipped with an
  out of date entrypoint for exactly this reason. Finish editing, then build.
- A named volume is not a bind mount. Docker copies the image's content into an
  empty named volume on first use, so the packaged profile's workflows arrive
  whether or not anything seeds them. An empty bind mount gets no such help. It
  hides the image's copy, which is what the entrypoint seeding is for. Test both,
  because only one of them exercises that code.
