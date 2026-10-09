# When something breaks

Start here, always:

```sh
scripts/doctor.py
```

Most confusing failures are something ordinary that the health check looks at:
Docker, the GPU runtime, `.env`, the image, the container, the server, the node
packs, Blender, sparse convolution, the weights and the output folders. It names
the one that is wrong. What follows is for when it says everything is fine and
something still goes wrong.

## The server is up but a workflow fails

**Check the graph against the running server before blaming the graph.**

```sh
scripts/validate_workflows.py            # every graph checked against /object_info
scripts/run_workflow.py --list-nodes Comfy3D    # what the server actually loaded
```

`validate_workflows.py` compares each graph to the node definitions the server
reports, so a renamed input or a removed node is caught before you queue
anything.

## A node pack did not load

The server starts fine with a node pack missing. Its nodes simply are not there,
and a graph using them fails with a message about an unknown node type.

The reason is only ever in the startup log:

```sh
docker logs "$(python3 scripts/_engine.py)" 2>&1 | grep -i -A5 'error\|traceback' | head -40
```

## Out of memory during mesh generation

Almost always a staging problem. The texture model stays resident in GPU memory
after it runs. Requests to free memory don't release it. The next shape run
crashes in its loader.

Restart the container, then run shapes and textures in separate passes:

```sh
docker restart "$(python3 scripts/_engine.py)"
```

**On a shared server, run `curl -s http://127.0.0.1:8188/queue` first.** A
restart ends every running and queued job on it, not only yours. The reply
lists them under `queue_running` and `queue_pending`; restart only when both
hold nothing but your own.

`scripts/asset_to_mesh.sh` does the restart for you, twice per batch. Before
each one it reads `/queue` and stops, naming the jobs, if anything is running or
pending; `ASSET_ENGINE_FORCE_RESTART=1` skips that check, so set it only when
those jobs are yours to lose. Do not interleave the two stages in your own
scripts.

## Out of memory when several jobs share the card

ComfyUI runs one job at a time, so graphs sent by several people or agents
queue rather than collide. Blender is not in that queue. A Cycles render, which
is `render_sheet.py`'s default, uses the same card, and so does anything else
you run in Blender on the GPU.

An edit leaves no room beside it. Sampled with `nvidia-smi` every 200 ms on
2026-10-09: after `run_workflow.py --free` the card had 1,142 MiB of 16,376 in
use, and one `img_edit_qwen.json` job at the graph's defaults, on a 1328 by 1328
image, then peaked at 15,190 MiB and stayed above 15,000 for about 106 of its
131.4 seconds. When the job had finished, 2,738 MiB were still in use.

`render_sheet.py` waits before a Cycles render until ComfyUI's queue is empty
and no other Blender job is running
([two render engines](/guide/render-engines#which-to-use)). It checks before it
starts, not while it renders: a graph queued a moment later loads its model
beside the render, and two renders that both find the card free start together.
That is read from the script, not provoked.

When more than one person or agent drives the card, give every GPU job the same
lock:

```sh
flock -w 7200 /tmp/gpu.lock scripts/run_workflow.py workflows/api/img_edit_qwen.json --image in.png
flock -w 7200 /tmp/gpu.lock scripts/render_sheet.py output/rigged/golem.fbx --angles 4 --check
```

`flock` takes an exclusive lock on the file, runs the command and lets go when
the command exits. With `-w` it gives up after that many seconds and exits 1
(flock(1) from util-linux 2.41.3, read 2026-10-09). The lock is advisory: it
orders only the jobs that take it, so everyone sharing the card has to use the
same file. Work that never touches the card, such as a Blender build rendering
with Cycles on the CPU, can stay outside it.

A queued job outlives its client. `run_workflow.py` does not cancel its job when
it is stopped, by Ctrl-C or by a `timeout`, so the job carries on in ComfyUI
after the lock is free (read from the script). Check `/queue` before the next
job starts.

The cost is waiting. A 2.5D isometric game made with the engine had three
agents share one card through one lock on 2026-10-09, and a render waited up to
24 minutes for it (the game's notes).

## A batch reported every name and produced no files

ComfyUI drops the connection mid-generation and the container restarts itself.
`run_workflow.py` raises on the dead socket, the shell loop carries on to the
next name, and the run *looks* like it worked. The failure is invisible unless
you count the files afterwards. On one icon batch this cost eleven images before
anyone noticed.

The symptom in the log is `RemoteDisconnected` or a connection reset, sometimes
with the container's own restart line just after it.

```sh
# Count what you actually got, before believing the log.
ls output/icons/*.png | wc -l
```

What fixes it: check the server is answering before each item, restart it when
it is not, and retry a few times. `scripts/run_workflow.py --retries 3` does
this. Smaller batches make it rarer: the crash correlates with how long the
server has been resident, not with any one prompt.

## Every generation fails with "can't convert cuda:0 device type tensor to numpy"

Raised from ComfyUI's quantised-loading path (`layer_conf.numpy()` in
`comfy/ops.py`) when a node loads a model stored in the fp8 "scaled" layout,
while `nvidia-smi` shows several gigabytes held with an empty queue. In the
asset workflow it shows up at the Qwen text encoder's `CLIPLoader` in a run with
the Texture stage on as well as a Qwen stage, and Concept, fast is on when the
graph opens.

The texture stage causes it. Hunyuan3D-2.1's texture loader hands its paint
pipeline to mmgp, a memory manager, and mmgp 3.7.14 finishes by setting torch's
default device to CUDA for the whole server process. From then on ComfyUI builds
each fp8 "scaled" model's quantisation settings on the GPU and cannot read them
back. Five models in the weight set are stored that way: the Qwen and Wan text
encoders, `qwen_image_2512_4steps_merged` and both Wan 2.2 image-to-video models
(read from their file headers, 2026-10-06). So after one texture run, every Qwen
and Wan stage fails, in the same run or any later one, until the server restarts.

`scripts/patch_nodes.py` puts the default device back once mmgp is done.
Image 0.1.10 is the first with that patch: pull it and recreate the container.
The published images up to 0.1.9 do not have it. On those:

- Run the texture stage on its own, then restart the container before any Qwen
  or Wan stage. A restart clears it until the next texture run.
- On the development profile, run `scripts/patch_nodes.py` and restart instead.

With the patch, a Qwen job queued straight after a texture run gets past its
text encoder, but on a 16 GB card it can then run out of GPU memory in its
sampler, with `torch.OutOfMemoryError: Allocation on device`. On 0.1.10 on the
reference machine, with Blender holding 365 MiB of the card, `txt2img_qwen_fast.json`
did that twice in two tries straight after `mesh_texture_hunyuan3d21.json`, ran
when queued again, and ran first time after `scripts/run_workflow.py --free`
between the two (2026-10-06). So free memory after a texture run, or queue the
failed job again: ComfyUI frees the same memory itself when it runs out.

It is worth knowing this one by name because the error says *numpy*, and this
stack documents a genuine numpy dependency chain at length, so the natural
reaction is to go hunting through the pins, which is the wrong tree.

```sh
docker restart "$(python3 scripts/_engine.py)"
```

If the server is shared, run `curl -s http://127.0.0.1:8188/queue` before that
restart: it ends every running and queued job, not only yours. Then wait for
the server to answer again:

```sh
until curl -s -o /dev/null http://127.0.0.1:8188/object_info; do sleep 4; done
```

## The rig came back as the previous model

ComfyUI caches by node inputs. If every figure is loaded through the same file
path and nothing else changes, the second run returns the first run's result,
reports done in 0s, and hands you the wrong rig.

Set a different output name per figure. That both names the output and breaks the
cache.

## A new mesh is rejected with value_not_in_list

The mesh loader offers a dropdown of files, and the worker process snapshots that
list when the node is first scanned. A file dropped in afterwards is not on the
list, and restarting the container does not refresh it.

Copy your mesh over a filename that is already on the list and load through that.
The node reads the file at run time, so the contents are yours even though the
name is not.

Or wire the path in. A `file_path` fed by another node, such as a string
primitive holding `/app/output/mesh/name.glb`, is not checked against the list,
and the node takes an absolute container path as it is. The Rig stage of
[the pipeline graph](/guide/asset-workflow) works that way (run 2026-10-02).

## Anything using sparse convolution dies with "type not registered yet"

The full error names nothing you could usefully search for:

```
could not convert default argument 'workspace: tv::Tensor' in method
'GemmTunerSimple.run_with_tuned_result' into a Python object
(type not registered yet?)
```

`spconv` cannot import at all, so every sparse-convolution node fails, TRELLIS
included. `scripts/doctor.py` reports it as a failed `spconv` check.

The cause is two `cumm` builds installed at once. The node pack pins the CPU
`cumm`, while `spconv-cu124` requires `cumm-cu124`. Both install into the same
`dist-packages/cumm/` directory, so whichever lands last wins, and the CPU
build's `core_cc.so` shadows the CUDA one that registers the types spconv needs.

The published 0.1.0 image shipped this way. The runtime remedy:

```sh
docker exec -u 0 "$(python3 scripts/_engine.py)" pip uninstall -y cumm
docker exec -u 0 "$(python3 scripts/_engine.py)" pip install --force-reinstall --no-deps cumm-cu124==0.7.11
docker restart "$(python3 scripts/_engine.py)"
```

If the server is shared, run `curl -s http://127.0.0.1:8188/queue` before that
restart: it ends every running and queued job, not only yours.

An image built from the current Dockerfile does not need this, because the
requirements rewrite that fixes `spconv-cu126` now fixes `cumm` alongside it.

::: warning A second, different error means the process is already poisoned
If you see `generic_type: cannot initialize type "ExternalAllocator": an object
with that name is already defined` instead, a failed import has already left
partial state behind. Restart the container and read the first error, not this
one. On a shared server, check `curl -s http://127.0.0.1:8188/queue` before
restarting: a restart ends every running and queued job.
:::

## Skinning dies with torch.bfloat16

Set precision to `fp16` rather than `auto`. On automatic it picks bfloat16 on
Ampere and Ada cards, and the sparse convolution library has no bfloat16 kernels.

## Rigging aborts with "Expected 52 bones"

You are using the Mixamo skeleton template. It requires a fixed 52 bone humanoid
and refuses anything else, including most generated characters whose arms hang
against their bodies.

Use `articulationxl` instead.

## UniRig dies with rtcGetSceneTraversable, or has no nodes at all

Both mean UniRig's own environment is missing or broken. UniRig runs its nodes in
an isolated pixi environment under `/app/.home/.ce`, which the packaged service
keeps in the `unirig-home` volume. From 0.1.4, `scripts/entrypoint.sh` builds it
before ComfyUI starts, checks it on every start (about 5 s), and rebuilds it if it
fails the check; the log says `building UniRig's environment` and then `UniRig's
environment is ready`. If it says `could not build`, read
`/app/.home/.ce/unirig-install.log`. `ASSET_ENGINE_UNIRIG_ENV=0` skips it.

Up to 0.1.3 nothing built it, and building it by hand ran into three faults in
turn, all found on 2026-09-30. The entrypoint now handles each:

- **No environment.** ComfyUI's log says `pixi has not materialized unirig-nodes;
  using in-process import`. The nodes load in the main environment, and Apply
  Animation died loading Blender with `undefined symbol: rtcGetSceneTraversable`,
  the Embree mismatch between the image's bpy 4.5.9 and UniRig's that the compose
  file names.
- **No nodes.** Built as it comes, UniRig registered 0 nodes, and the log's
  metadata scan ended in `infer_schema(func): Parameter stride has unsupported type
  list[int]`. UniRig's `nodes/comfy-env.toml` asks for `comfy-kitchen = "*"`,
  which resolved to 0.2.36, and nothing past 0.2.26 works on this image's torch 2.6.
  `scripts/patch_nodes.py` pins it to 0.2.26.
- **Auto Rig dies in `nvrtc compile failed`**, with errors in cumm's tensorview
  headers. comfy-env's wheel index has only cumm 0.8.2 for this stack, beside
  spconv 2.3.8, which requires cumm below 0.8. The entrypoint swaps in
  spconv-cu124 and cumm-cu124 at the main image's versions, 2.3.8 and 0.7.11.
  comfy-env's own `COMFY_ENV_AUTO_INSTALL` is left off, because its manifest leaves
  out the CUDA wheels altogether, and Auto Rig then died on `No module named
  'torch_cluster'`.

Built this way from an empty volume, UniRig registered all 16 nodes, and
`scripts/rig_units.sh` rigged a TRELLIS mesh in 36 s. Inside the environment the
nodes do not run from `/app`, so give them absolute container paths, such as
`/app/output/rigged/name.fbx`: a relative one is not found.

On an image before 0.1.4, delete the environment and let a 0.1.4 container build
it, or build it by hand with UniRig's installer and then make the same two fixes
inside it:

```sh
docker exec comfyui-packaged bash -c 'cd /app/custom_nodes/ComfyUI-UniRig && python3 install.py'
docker exec comfyui-packaged bash -c 'P=/app/.home/.ce/envs/unirig-nodes/.pixi/envs/default/bin/python; $P -m pip install --no-deps "comfy-kitchen==0.2.26" && $P -m pip uninstall -y spconv cumm && $P -m pip install "spconv-cu124==2.3.8" "cumm-cu124==0.7.11"'
docker restart comfyui-packaged     # once /queue is empty
```

## UniRig's preview panel is empty

UniRig's Preview Rigged Mesh node runs but draws nothing, and ComfyUI's start-up
log says `Failed to execute startup-script: .../ComfyUI-UniRig/prestartup_script.py
/ [Errno 13] Permission denied`, with UniRig listed as `PRESTARTUP FAILED`. The
server runs as your user and could not write UniRig's viewers into its own pack
folder, so the script stopped there, before it copies UniRig's sample FBX files
into `input/`.

- **Packaged image, up to 0.1.8.** The packs in the image belong to root. From
  0.1.9 the image makes `ComfyUI-UniRig/web` writable; pull it and recreate the
  container. On 0.1.9 the panel drew UniRig's sample character with its
  skeleton (2026-10-05).
- **Development profile.** `./custom_nodes` is a bind mount, and files in it that
  a container run as root wrote belong to root; here UniRig's `web/` folder did
  (2026-10-05). `sudo chown -R "$(id -u):$(id -g)" custom_nodes` hands them back.

## The sprite sheet is the rest pose four times

Look for this line in the output:

```
  ! bones not in the rig: bone_41, Spine
```

The bone names in your pose file are not in this rig. Bone names differ per
model, so a transforms file written for one rig, such as `poses/walk.json`,
does not fit another. Compile a role pose for this rig and render that:

```sh
scripts/bone_roles.py compile poses/roles/walk.json output/rigged/golem.fbx
scripts/render_sheet.py output/rigged/golem.fbx \
    --poses transforms:output/poses/golem_walk.json --angles 4 --size 220 --check
```

See [animation](/guide/animation#deriving-cycles-automatically). For a bone no
role covers, or a rig `bone_roles.py map` cannot read, dump the map and pose by
bone name ([rigging](/guide/rigging#bone-names-are-not-human-readable)).

A pose can also do nothing when every bone name is right, for example when a
rotation cancels out or goes to an axis with no effect. Then no line is printed.
Render with `--check`: it flags a pose row identical to the first row at every
angle, and exits non-zero.

## The model renders as a featureless grey blob

It has no texture yet, and the render tools give untextured meshes a grey clay
material on purpose. Blender's default white against a white world light has no
readable form at all.

If you expected a texture, the texture stage has not run or its output was
overwritten by a later asset.

## The same prompt and seed gave a different file

Expected. Nothing is wrong.

Three fresh runs of the same graph, same seed, same input image, produced three
different checksums: identical size, identical face count, different bytes. The
variation is GPU nondeterminism in the sparse-convolution and attention kernels,
and it applies to every generator here, not just one.

So **compare renders, not hashes.** A checksum diff between two runs tells you
nothing about whether a change you made had an effect.

Two things that confuse this further:

- **A repeat with identical node inputs does not re-execute.** ComfyUI serves the
  cached result and returns in about a second. If you are trying to test whether
  some change matters, that cache will happily show you an identical result for
  the wrong reason. Change an input or restart the container to force a real run.
  On a shared server, change an input: a restart ends every running and queued
  job, so check `curl -s http://127.0.0.1:8188/queue` before one.
- **Face counts are not evidence either** when a `Decimate` node is in the graph,
  because it clamps to its target. Two runs both reporting 48,000 faces may have
  produced quite different geometry.

## Two renders produced sheets containing each other's model

Fixed, but worth knowing if you see it in an old script. Renders used to share one
frame folder, so two running at once interleaved their frames. Each run now gets
its own folder, and it is deleted once the sheet is put together. Pass
`--keep-frames` to keep it.

## Output files are owned by root

Set `PUID` and `PGID` in `.env` to your own `id -u` and `id -g`, then recreate the
container.

## The docs site loads without styling

The base path does not match where it is served from. GitHub Pages serves a
project site from `/<repo>/`. Set `DOCS_BASE` when building for anywhere else:

```sh
DOCS_BASE=/ npm run docs:build
```

## The docs site is public although the repo is private

GitHub Pages publishes to the open internet whatever the repository's
visibility. Read in GitHub's documentation on 2026-10-09: "GitHub Pages sites
are publicly available on the internet, even if the repository for the site is
private (if your plan or organization allows it)", and "If the account that owns
the repository uses GitHub Free or GitHub Free for organizations, the repository
must be public." A paid plan lets Pages publish from a private repository, and
the site is still public. The exception is an organisation's plan: "To publish
a GitHub Pages site privately, your organization must use GitHub Enterprise
Cloud." ([Creating a Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site),
[changing its visibility](https://docs.github.com/en/pages/getting-started-with-github-pages/changing-the-visibility-of-your-github-pages-site).)

`.github/workflows/docs.yml` deploys this repository's docs, which are public
on purpose. If you copy it into a private project, such as a game's own docs,
make it build without deploying: delete the `deploy` job, the two Pages steps
and the `pages` and `id-token` permissions, keep `npm install` and
`npm run docs:build` so a broken page still fails the run, and read the site on
your own machine with `npm run docs:dev`.

## A workflow edited in the editor behaves differently from the file

The graphs in `workflows/api/` are in the format the server accepts, which the web
editor cannot open. The editor versions are generated from them:

```sh
scripts/api_to_ui.py --check      # convert all, and verify every value survived
```

Edit the API file and regenerate. The converted graphs are generated files.

That `--check` is not decoration. Node values are stored as a positional array in
the editor format, and the position depends on the order the node declares its
inputs, which is only knowable from the running server. Two things shift that
array and produce a graph that looks perfect and runs with the steps in the
guidance box: an input that is wired takes no slot in the array, and every seed
field is followed by an extra value the backend never sees, whether or not its node
asks for one. The check reads each converted graph back and compares every value
against the original. It caught five widgets silently dropped across two
workflows, but it reads the array with the converter's own idea of its order, so a
wrong idea passes it: on 2026-09-30 the TRELLIS, Hunyuan3D and TripoSG graphs
passed while the editor sent their values one place early
([Workflows](/reference/workflows#editing-graphs-in-the-comfyui-editor)).
