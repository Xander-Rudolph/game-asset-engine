# When something breaks

Start here, always:

```sh
scripts/doctor.py
```

Most confusing failures are one of six ordinary things, and the health check
names which one. What follows is for when it says everything is fine and
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
docker logs comfyui 2>&1 | grep -i -A5 'error\|traceback' | head -40
```

## Out of memory during mesh generation

Almost always the staging problem. The texture model stays resident in GPU memory
after it runs, and a request to free memory does not release it. The next shape
run then dies inside its loader.

Restart the container, then run shapes and textures in separate passes:

```sh
docker compose --profile comfy restart comfyui
```

`scripts/asset_to_mesh.sh` does this for you. Do not interleave the two stages in
your own scripts.

## A batch reported every name and produced no files

ComfyUI drops the connection mid-generation and the container restarts itself.
`run_workflow.py` raises on the dead socket, the shell loop carries on to the
next name, and the run *looks* like it worked - the failure is invisible unless
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
this. Smaller batches make it rarer - the crash correlates with how long the
server has been resident, not with any one prompt.

## Every generation fails with "can't convert cuda:0 device type tensor to numpy"

Raised from ComfyUI's quantised-loading path, on **every** generation, while
`nvidia-smi` shows several gigabytes held with an empty queue.

Restart the container. That clears it.

It is worth knowing this one by name because the error says *numpy*, and this
stack documents a genuine numpy dependency chain at length - so the natural
reaction is to go hunting through the pins, which is the wrong tree. The root
cause here was never established; the restart is the answer.

```sh
docker compose --profile packaged restart comfyui
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

## Skinning dies with torch.bfloat16

Set precision to `fp16` rather than `auto`. On automatic it picks bfloat16 on
Ampere and Ada cards, and the sparse convolution library has no bfloat16 kernels.

## Rigging aborts with "Expected 52 bones"

You are using the Mixamo skeleton template. It requires a fixed 52 bone humanoid
and refuses anything else, including most generated characters whose arms hang
against their bodies.

Use `articulationxl` instead.

## The sprite sheet is the rest pose four times

Look for this line in the output:

```
  ! bones not in the rig: bone_41, Spine
```

The bone names in your pose file are not in this rig. Bone names differ per
model. Dump the map and re author. See
[rigging](/guide/rigging#bone-names-are-not-human-readable).

## The model renders as a featureless grey blob

It has no texture yet, and the render tools give untextured meshes a grey clay
material on purpose. Blender's default white against a white world light has no
readable form at all.

If you expected a texture, the texture stage has not run or its output was
overwritten by a later asset.

## Two renders produced sheets containing each other's model

Fixed, but worth knowing if you see it in an old script. Renders used to share one
frame folder, so two running at once interleaved their frames. Each run now gets
its own folder.

## Output files are owned by root

Set `PUID` and `PGID` in `.env` to your own `id -u` and `id -g`, then recreate the
container.

## The docs site loads without styling

The base path does not match where it is served from. GitHub Pages serves a
project site from `/<repo>/`. Set `DOCS_BASE` when building for anywhere else:

```sh
DOCS_BASE=/ npm run docs:build
```

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
field is followed by an extra value the backend never sees. The check reads each
converted graph back the way ComfyUI reads it and compares every value against the
original. It caught five widgets silently dropped across two workflows.
