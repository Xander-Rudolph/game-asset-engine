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
  [  ok  ] image        ghcr.io/xander-rudolph/game-asset-engine-comfy:latest
  [  ok  ] container    comfyui-packaged is up 3 hours
  [  ok  ] server       http://127.0.0.1:8188 answering, 944 node types loaded
  [  ok  ] node packs   3D-Pack and UniRig both loaded
  [  ok  ] blender      bpy 4.5.9 LTS in the container
  [  ok  ] spconv       sparse convolution imports
  [  ok  ] weights      5/5 complete; 0 incomplete (0B outstanding)
  [  ok  ] folders      output, input and logs are writable

  Ready. Nothing to fix.
```

Add `--fix` and it will do the safe parts itself: write your `.env`, start the
container, and wait for the server to finish loading.

```sh
scripts/doctor.py --fix
```

::: tip Run this before blaming a workflow
Most confusing failures in this pipeline come from a short list of ordinary
problems, and the health check looks for all of them: Docker, the GPU runtime,
`.env`, the image, the container, the server, the node packs, Blender, sparse
convolution, the weights and the output folders. Each one shows up much later as
something that looks like a broken graph. Checking first removes the
guessing.
:::

## The prebuilt image

Everything except the weights, already built. This is the short version;
[running the image](/guide/running-the-image) has the pull, the authentication,
the plain `docker run` equivalent and what each flag is for.

```sh
cp .env.example .env       # then set MODELS_DIR to where weights should live
docker compose --profile packaged up -d
```

That is the whole install. The image carries ComfyUI, all four node packs at
pinned commits with their compatibility patches applied, the Hunyuan texture
extension compiled, and every workflow already in the editor sidebar.

Open <http://localhost:8188> when it is up.

While the package is still private, the pull needs you to log in first. See
[running the image](/guide/running-the-image#authenticating).

### Weights are not in the image

The weight set is around 200GB, so it stays on your disk under `MODELS_DIR`. The
container reads `models.json` on boot and names anything missing before the
server starts, rather than letting it turn up as a red node an hour later.

To have the container fetch the core group itself on boot (about 20GB):

```sh
ASSET_ENGINE_FETCH_MODELS=1 docker compose --profile packaged up -d
```

Or fetch them yourself, in groups:

```sh
scripts/fetch_models.py                    # check core; no weights, but seeds MODELS_DIR
scripts/fetch_models.py --download         # fetch the missing core models
scripts/fetch_models.py --download --group qwen   # the concept graphs need it, about 48GB
scripts/fetch_models.py --list-groups      # what groups exist and their sizes
```

The [first asset walkthrough](/guide/first-asset#fetch-the-weights-once) also
uses the `trellis` and `hunyuan` groups and fetches them in its first step.

A file counts as present only when its size matches what the hub reports. A
half finished download gets fetched again rather than silently loaded and
crashed on. Downloads resume.

::: warning The packaged image mounts no source
Mounting a host folder replaces what the image has at that path. It doesn't add
to it. If you mount an empty `./custom_nodes` folder, the nodes baked into the
image are hidden. Use the `comfy` profile below when you want to edit node
source code.
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
scripts/publish_image.sh 0.1.2
```

It builds locally rather than in CI on purpose. The image is 27.6GB and a hosted
runner has nothing like the disk for it.

Two things about that build are worth knowing:

- **Finish editing before you build.** The build reads all your files when it
  starts. An edit made while the build runs doesn't reach the image, even if the
  step that copies that file is near the end. The first published image shipped
  with an outdated start-up script for exactly this reason.
- **A named volume is not a mounted host folder.** Docker fills an empty named
  volume from the image on first use, so the packaged profile's workflows arrive
  even if the start-up script's seeding is broken. An empty host folder under
  the `comfy` profile gets no such help. It hides the image's copy, and only the
  seeding fills it. Test both, because only the empty host folder case runs the
  seeding.
