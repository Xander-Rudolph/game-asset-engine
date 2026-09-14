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

## Two critical settings

Both were discovered after failing on real assets, and both are set in
`rig_units.sh`.

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

If your mesh has more faces than the rigger's budget, the rigger decimates it
first (cuts its face count down) and solves the skeleton against that lighter
copy. This is how high-resolution models get rigged at all, but there's a side
effect that catches people out.

**What it does:** Before solving anything, the rigger joins separate pieces,
applies transformations and triangulates. If the triangulated mesh has more
faces than `target_face_count`, it is decimated to that count using collapse
decimation, which merges neighbouring vertices to remove faces. The skeleton and
skin weights are solved against this decimated mesh.

**Why it's useful:** The skeleton solver is a neural network that can only take
so much. Given 600,000 faces it doesn't just run slowly, it can't run at all.
Decimating first means you can point it at a high-resolution scan or sculpt and
get a usable skeleton in a few minutes, without manual preparation.

**The important part:** The FBX it gives you contains the decimated mesh, not
yours. The output uses the vertices and faces from the decimated version.

::: warning Above the budget, your original model gets replaced
If your mesh has 642,000 faces but the budget is 48,000, you get back a 48,000
face model with a skeleton. The skeleton is fine, but the original detail is
gone. Nothing warns you about this.
:::

**The budget is a maximum, not a goal.** If your mesh is smaller than the
budget, it passes through untouched. A 39,996 face mesh rigged with a 48,000
face budget comes back with 39,996 faces and 47 bones, unchanged. This is the
normal case here, since meshes are saved at 18,000 faces and the budget is much
higher.

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

Two details make this work. Get either one wrong and the rig looks broken:

- **Align the meshes first.** The rigger normalises its output by scaling and
  centring into a unit box, so the original mesh rarely lines up with it. The
  script matches their bounding boxes before transferring. Skip this step and
  every weight gets read from the wrong part of the body.
- **Use face-based interpolation, not vertex-based.** The proxy has far fewer
  vertices than the original, so snapping to the nearest one quantises the
  weights (they jump in steps) and you see bands at the joints. Both meshes
  describe the same surface, so a point on the original almost always lands
  inside a face of the proxy, and the script blends the weights across that
  face.

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
docker exec "$(python3 scripts/_engine.py)" python3 -c "
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

Or let a script work it out from the skeleton's own geometry. None ships here
yet, but the rules are short: the root is the bone with no parent, the legs are
the two chains descending furthest below it, the spine is the chain that rises,
and the arms are the two chains branching off near the top. See
[deriving cycles automatically](/guide/animation#deriving-cycles-automatically).

## Batch rigging quirks

All three are handled in `rig_units.sh`, and each took real time to find.

**The file list is fixed when the nodes load.** The mesh loader offers a
dropdown of files, and the rigger's isolated worker process snapshots that list
when it first scans the node. A mesh you add to `input/3d/` after that is
rejected with `value_not_in_list`. Restarting the container doesn't help either.
The script works around this by copying each mesh over a file that was already
in the list. The node reads the actual file when it runs, so you don't need to
restart between figures.

**Change the output name for each figure, or you get the previous one.** Every
figure is loaded through the same input slot, so ComfyUI sees identical inputs
and serves its cached result. It reports done in 0s and hands back the previous
figure's rig. Changing `fbx_name` per figure both names the output and breaks
the cache.

**Track output by timestamp, not by file count.** The rigger writes its `.fbx`
into `output/`, named from `fbx_name`. A file of that name can already be there
from an earlier run that was never moved, such as one run by hand, and then
neither a file count nor a name check can tell the new result from the old one.
The script creates an empty timestamp file before each run, takes the `.fbx` in
`output/` that is newer than it, and moves that to `output/rigged/`.

## Checking a rig

Render it. A rig that solved badly is obvious in one sheet and invisible in a log:

```sh
scripts/render_sheet.py output/rigged/golem.fbx --poses transforms:poses/walk.json \
    --angles 4 --size 220 --out output/sheets/golem_walk.png --check
```

`--check` exits non-zero on a fault it can measure, such as an empty or clipped
cell, or a pose row identical to the first row at every angle. It cannot tell a
good walk from a bad one.

Then open the image and look at it. A mis solved shoulder produces a confident,
well rendered, wrong walk cycle.
