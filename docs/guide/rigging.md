# Rigging

Rigging puts a skeleton inside a mesh and works out how much each bone moves
each vertex. Here it is automatic. You do not paint weights.

```sh
cp output/mesh/golem_textured.glb input/3d/golem.glb
scripts/rig_units.sh golem
```

Out comes `output/rigged/golem.fbx`.

## Two riggers, and they do not mix

| | UniRig | mesh2motion |
|---|---|---|
| Skeleton | Mixamo compatible or generic | Its own, one per creature family |
| Animations | Anything from Mixamo | 176 clips built in |
| Non humanoids | Poorly | Fox, spider, snake, dragon, bird, kaiju |
| How you drive it | Command line | Interactive, in the browser |

Pick one per asset:

- **A non humanoid creature** goes to mesh2motion. Nothing else here has those
  skeletons.
- **A humanoid you want in a game engine** goes to UniRig with the Mixamo
  template, then the Mixamo animation library.
- **A look, quickly** goes to mesh2motion's human base, 87 clips with no
  downloads.

They do not compose. mesh2motion rigs onto its own skeleton and plays its own
clips. UniRig produces a different skeleton and plays Mixamo clips. There is no
path from one to the other.

## Two settings that are load bearing

Both were found by failing on real assets. Both are set in `rig_units.sh`.

### Use articulationxl, not mixamo

The Mixamo template demands a fixed 52 bone humanoid and refuses anything else:

```
Expected 52 bones ... got 22
```

It aborts on any figure whose arms hang against its body, which is most
generated characters. `articulationxl` works out the skeleton from the mesh
instead, so it takes whatever shape you give it.

The cost is bone names. See [bone names are not human readable](#bone-names-are-not-human-readable) below.

### Use fp16, not auto

On automatic, it picks bfloat16 on Ampere and Ada cards. The sparse convolution
library in this stack has no bfloat16 kernels, so skinning dies with a bare:

```
WorkerError: torch.bfloat16
```

Nothing in that message points at precision. Set `fp16` and it works.

## The decimate then rig shortcut

This is how high resolution models get rigged at all, and it has a consequence
that catches people out.

**What happens.** Before solving anything, the rigger joins the mesh objects,
applies transforms, triangulates, and then decimates to `target_face_count`
using collapse decimation. The skeleton and the skin weights are solved against
that decimated mesh.

**Why it helps.** The solver is a neural network with a fixed appetite. Handing
it 600,000 faces is not slow, it is impossible. Decimating first means you can
point it at a photogrammetry scan or a sculpt and get a usable skeleton in a few
minutes, without preparing anything by hand.

**The catch.** The FBX it hands back contains the decimated mesh. Not your mesh.
The skinning stage takes the vertices and faces recorded by the skeleton stage,
which are the decimated ones, and writes those into the output.

::: warning Above the budget, your model is replaced by the proxy
Feed a 642,000 face model in with the budget at 48,000, and you get a 48,000
face model with a skeleton in it. The skeleton is good. The detail is gone, and
nothing warns you.
:::

**The budget is a ceiling, not a target.** Below it, nothing happens at all. A
39,996 face mesh rigged with the budget at 48,000 comes back as 39,996 faces
with 47 bones, untouched. That is the normal case for this pipeline, because
meshes are saved at 18,000 faces and the budget is well above it.

So there are only two situations:

| Your mesh | What comes back |
|---|---|
| Under the budget | The same mesh, now with a skeleton |
| Over the budget | A decimated copy, with a skeleton |

### Keeping the detail as well as the rig

When the detail was the point, transfer the weights back onto the original mesh:

```sh
scripts/transfer_weights.py output/rigged/hero.fbx input/3d/hero_full.glb \
    --out output/rigged/hero_full.fbx
```

Measured on a real pair: a 47 bone skeleton solved on a 39,996 face proxy,
transferred onto a 642,547 face mesh with 394,992 vertices. Zero vertices left
unweighted.

```
  proxy      39,996 faces, 47 bones, 47 weight groups
  original   642,547 faces, 394,992 verts
  unweighted 0 verts (0.00%)
```

Two details make it work, and getting either wrong produces a mess that looks
like a bad rig:

- **The meshes have to be aligned first.** The rigger normalises its output,
  centring and scaling the model into a unit box, so the original almost never
  sits on top of it. The script matches bounding boxes before transferring. Skip
  that and every weight is read from the wrong part of the body.
- **Interpolate across the nearest face, not the nearest vertex.** Snapping to
  the proxy's much sparser vertices quantises the weights and gives visible
  banding at the joints. The proxy and the original describe the same surface,
  so a point on one lands inside a face on the other.

The script reports how many vertices ended up with no weight at all. Anything
above 1% means the alignment failed, not that the transfer is imprecise. A
vertex with no weight does not move, which shows up as a piece of the model
staying behind mid stride.

**When not to bother.** If the asset is only ever seen as a sprite, the proxy is
better than the original in every way that matters. It is smaller, it renders
faster, and at 128 pixels it is identical. See
[decimation](/guide/decimation) for what a face budget actually costs.

## Bone names are not human readable

`articulationxl` names every bone `bone_0` through `bone_N`, and the count
differs per figure. Two characters from this same pipeline came out with 47
bones and 28 bones.

So a hand written pose file does not survive being pointed at a second model.
Dump the map before authoring anything:

```sh
docker exec comfyui python3 -c "
import bpy; bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='/app/output/rigged/golem.fbx')
a=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
for b in a.data.bones:
    print(b.name, b.parent.name if b.parent else '-', [round(v,2) for v in b.head_local])"
```

Read the hierarchy from the head positions. The chain rising from the root is the
spine and then the head. Chains branching at chest height going sideways are the
arms. Chains going down from the root are the legs.

For a 28 bone humanoid from this pipeline the map came out as:

| Bones | Part |
|---|---|
| `bone_0` | root and pelvis |
| `bone_1` to `bone_3` | spine, lower to chest |
| `bone_4`, `bone_5` | neck, head |
| `bone_6` to `bone_9` | one shoulder, upper arm, forearm, hand |
| `bone_10` to `bone_12` | that hand's fingers |
| `bone_13` to `bone_16` | the other shoulder, upper arm, forearm, hand |
| `bone_17` to `bone_19` | that hand's fingers |
| `bone_20` to `bone_23` | one thigh, shin, foot, toe |
| `bone_24` to `bone_27` | the other thigh, shin, foot, toe |

Or let a script work it out from the skeleton's own geometry, which is what
`tool/make_cycles.py` in the game repo does: the root is the bone with no
parent, the legs are the two chains descending furthest below it, the spine is
the chain that rises, and the arms are the two chains branching off near the top.

## Two batch scripting traps

Both of these come from `rig_units.sh` and both cost real time to find.

**The file list is snapshotted.** The mesh loader offers a dropdown of files,
and the isolated worker process snapshots that list when the node is first
scanned. A mesh dropped into `input/3d/` afterwards is rejected with
`value_not_in_list`, and restarting the container does not refresh it. The
script works around this by copying each figure over a file that is already in
the list and loading through that. The node reads the file at run time, so no
restart is needed between figures.

**Set a different output name per figure or you get the previous one.** Every
figure is loaded through the same slot path, so without changing something,
ComfyUI sees identical node inputs, serves the cached result, reports done in 0s
and hands back the previous figure's rig. Setting `fbx_name` per figure both
names the output and breaks the cache.

**Find the output by time, not by counting.** The rigger names its output after
the mesh, so a rerun overwrites rather than adds, and a file count never moves.
The script touches a timestamp file before the run and takes whatever is newer.

## Checking a rig

Render it. A rig that solved badly is obvious in one sheet and invisible in a log:

```sh
scripts/render_sheet.py output/rigged/golem.fbx --poses transforms:poses/walk.json \
    --angles 4 --size 220 --out output/sheets/golem_walk.png
```

Then open the image and look at it. A mis solved shoulder produces a confident,
well rendered, wrong walk cycle.
