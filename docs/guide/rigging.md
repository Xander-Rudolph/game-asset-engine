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

`articulationxl` names every bone `bone_0` through `bone_N`, and the count and
order differ per figure. Five figures from this same pipeline came out with 24,
28, 30, 30 and 47 bones.

So a hand written pose file does not survive being pointed at a second model.
Map the bones to roles before posing anything:

```sh
scripts/bone_roles.py map output/rigged/golem.fbx
```

On the 24 bone `output/rigged/unit_rogue.fbx` it printed, trimmed:

```
  up       +Z  (1.6 deg from the ankles to the top of the spine)
  forward  -Y  (3.0 deg from the way the toes point)
  right    -X  (the character's own right; its left is +X)
  head_end bone_5 carries 0.009 of bone_4's skin weight (13.3 of 1470.7); under 0.25 makes it head_end: yes

  role             bone      head                       skin weight  connected
  pelvis           bone_0    (-0.020, -0.098, +0.051)       6598.7  no
  spine            bone_1    (-0.020, -0.121, +0.215)        313.0  no
  chest            bone_2    (-0.020, -0.105, +0.426)       3036.4  yes
  neck             bone_3    (-0.027, -0.090, +0.684)        196.2  no
  head             bone_4    (-0.027, -0.105, +0.746)       1470.7  yes
  head_end         bone_5    (-0.027, -0.082, +0.863)         13.3  yes
  right_thigh      bone_20   (-0.129, -0.098, +0.043)       2317.2  no
  right_shin       bone_21   (-0.184, -0.066, -0.387)       2789.7  yes

  no role  bone_10  (below left_hand)
  no role  bone_15  (below right_hand)
```

It writes `output/rigged/unit_rogue.roles.json`, which `bone_roles.py compile`
reads to turn one role pose file into a pose for this rig. That is covered in
[deriving cycles automatically](/guide/animation#deriving-cycles-automatically).

`map` reads the skeleton's geometry, and skin weights for the head, but never
its names:

- **Root and pelvis.** The root is the bone with no parent. The pelvis is the
  root, or the first bone below it, with three or more children.
- **Legs.** The two chains off the pelvis that reach furthest from it. On each,
  the thigh and shin are the consecutive pair with the greatest combined length,
  and the foot is the shin's child whose chain reaches furthest sideways from
  the ankle.
- **Spine.** The remaining pelvis chain pointing most nearly away from the legs,
  followed at each bone through the child that continues most nearly straight.
- **Chest and arms.** The chest is the first spine bone with chains leaving it
  to both sides, and those chains are the arms. On each, the upper arm and
  forearm are the longest consecutive pair.
- **Facing.** Forward is the way the feet point, and right is forward crossed
  with up. Every rig mapped here faces -Y, so the character's own left is +X.
- **Head.** Skin weights settle this one call, because on some rigs the top bone
  is an end marker the mesh hardly follows. See
  [which bone is the head](/guide/animation#which-bone-is-the-head).

`map` reads `.fbx` and `.glb`. On 2026-09-16 it ran on the five articulationxl
figures, `input/3d/mixamo.fbx` and `output/mpfb/human_game_engine.glb`. No
non-humanoid skeleton has been tried.

For the 28 bone humanoid, `output/assets/alchemist_warrior/rig.fbx`, the map
agrees bone for bone with the one worked out by hand in `poses/_bones.md`:

| Bones | Part |
|---|---|
| `bone_0` | root and pelvis |
| `bone_1` to `bone_3` | spine, spine_2 and chest |
| `bone_4`, `bone_5` | neck, head |
| `bone_6` to `bone_9` | left shoulder, upper arm, forearm, hand |
| `bone_10` to `bone_12` | that hand's fingers |
| `bone_13` to `bone_16` | right shoulder, upper arm, forearm, hand |
| `bone_17` to `bone_19` | that hand's fingers |
| `bone_20` to `bone_23` | left thigh, shin, foot, toe |
| `bone_24` to `bone_27` | right thigh, shin, foot, toe |

It disagrees with `poses/_bones.md` in one place. The table there for the
`rig24_*.json` and `rig47_*.json` pose files puts `bone_2` in its spine column.
`map` makes `bone_2` the chest on the 24, both 30 and the 47 bone rigs, because
the arms leave it, and `bone_1` the one spine bone below it. The arm, thigh and
shin bones in that table agree.

For bones `map` gives no role, such as fingers, or a skeleton it cannot read,
dump the raw hierarchy:

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

## Faces

Neither rigger makes a face. A UniRig figure measured for the lip sync research
had no jaw, eye or mouth bones and no shape keys, and mesh2motion's human rig
stops at the head ([lip sync](/reference/lip-sync#the-riggers-give-you-no-face)).
How Valve built faces for the Source engine out of muscle shapes, and which of
its ideas carry over, is in [Source Filmmaker](/reference/source-filmmaker#how-valve-s-facial-system-is-built).
Human bases that do ship a face rig, and what their licences let a game do, are
compared in [DAZ Genesis](/reference/daz-genesis#other-character-bases-compared).

### A jaw by rule

`scripts/face_rig.py add-jaw` adds a weighted `jaw` bone under the head of a
rigged `.fbx`, `.glb` or `.blend`, and writes a `.blend` or an `.fbx`. Turn the
jaw about its own X axis; a positive angle opens it.

```sh
scripts/face_rig.py add-jaw output/rigged/golem.fbx --out output/face_rig/golem_jaw.blend
scripts/render_sheet.py output/face_rig/golem_jaw.blend \
    --poses transforms:output/face_rig/jaw20.json --size 220 --flat \
    --out output/sheets/golem_jaw.png
```

`output/face_rig/jaw20.json` is a file you write, holding
`[{}, {"jaw": {"rotate": [20, 0, 0]}}]`: the rest pose, then the jaw open 20
degrees. The jaw has no role, so it is posed by its bone name in a transforms
file, not from `poses/roles/`.

**Check the head it picked.** `add-jaw` prints the chain it climbed and the bone
it took for the head. The top bone is not always the head: on three of the five
articulationxl rigs tried, it is the heaviest weight on 5 vertices or fewer. So
the head is the bone, from the top down, that is the heaviest weight on the most
of the highest 2% of the vertices the chain moves. Pass `--head` when the pick
is wrong. Run on 2026-09-16, it picked the same bone that `bone_roles.py map`
calls the head on all five rigs:

| Rig | Head | Vertices given jaw weight | Moved by a 20 degree turn |
|---|---|---|---|
| `unit_rogue`, 24 bones | `bone_4` | 297 | 264 |
| `alchemist_warrior`, 28 bones | `bone_5` | 194 | 191 |
| `unit_alchemist`, 30 bones | `bone_4` | 534 | 493 |
| `unit_beastmaster`, 30 bones | `bone_4` | 336 | 323 |
| `unit_warrior`, 47 bones | `bone_4` | 196 | 185 |

Before writing, `add-jaw` turns the jaw 20 degrees. If no vertex moves more than
0.5% of the head's height, or the ones that move rise on average, it prints the
numbers, writes nothing and exits 1. Only the first case has been triggered, on
a test head weighted 0.001, where it printed
`! nothing moved when the jaw turned: the weights did not take`.

**At sprite size the change is small.** On `unit_alchemist`, the jaw at 0 and
at 20 degrees, counted per cell with a row diff on 2026-09-16. A second
`add-jaw` and render the same day gave the same per-cell counts.

| Render | Cells | Pixels changed per cell |
|---|---|---|
| 220 px, `--flat` | azimuths 0, 90, 180, 270 | 251, 145, 29, 172 |
| 128 px, `--flat` | azimuths 0, 90, 180, 270 | 99, 65, 21, 65 |
| 220 px, isometric | azimuths 45, 135, 225, 315 | 249, 54, 70, 241 |
| 128 px, isometric | azimuths 45, 135, 225, 315 | 89, 25, 34, 91 |

In the 220 px front cell the change fits a 28 by 17 px box, 34 of its pixels
change by 16 levels or more, and no silhouette pixel changes. At 128 px it fits
16 by 11 px, with 12 pixels changing by 16 levels or more.

A generated mesh has no parted lips, so the jaw stretches the lower face down
rather than opening a mouth. `--check` passes a jaw row but cannot judge it.
A row that keeps row 0's silhouette is compared pixel by pixel, and on
2026-09-16 `scripts/sheet_check.py` passed both the 220 px flat and the 128 px
isometric jaw sheets with `pose row 1 keeps row 0's silhouette at every angle,
but 63/64/11/74 px inside it changed by 8 levels or more` (25/9/10/29 px at
128 px). Whether that change reads as a jaw is still for a face sheet to show.

Not tried: `--front` other than `-y`, `--name`, and Mixamo, mesh2motion or
Genesis rigs.

### Shape keys

`render_sheet.py` sets shape keys per row with `@shape_keys` in a transforms
file, and rig properties with `@props`; `scripts/render_sheet.py --help` covers
both. `scripts/face_rig.py transfer-shapes` copies shape keys from a template
head onto a model with Blender's Surface Deform modifier, but nothing places the
template: it must already sit on the model's surface. `scripts/face_rig.py
spheres` writes test spheres to try it on, and a transfer onto them moved 261 of
642 vertices, by 0.3044 units at most. `scripts/face_rig.py --help` has the
details, and [lip sync](/reference/lip-sync#faces-on-generated-meshes) has the
heads worth borrowing shapes from and their licences.

## Checking a rig

Render it. A rig that solved badly is obvious in one sheet and invisible in a log:

```sh
scripts/bone_roles.py compile poses/roles/walk.json output/rigged/golem.fbx \
    --out output/poses/golem_walk.json
scripts/render_sheet.py output/rigged/golem.fbx --poses transforms:output/poses/golem_walk.json \
    --angles 4 --size 220 --out output/sheets/golem_walk.png --check
```

`compile` maps the rig first when given the FBX itself. `--check` exits non-zero
on a fault it can measure, such as an empty or clipped cell, or a pose row
identical to the first row at every angle. It cannot tell a good walk from a bad
one.

Then open the image and look at it. A mis solved shoulder produces a confident,
well rendered, wrong walk cycle.
