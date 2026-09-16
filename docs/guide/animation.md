# Animation cycles

Two ways to get a rigged model moving. Use a library clip, or pose the bones
yourself.

## Library clips

`scripts/list_animations.py` prints what is actually installed. It reads clip
names out of the files rather than from a list someone typed, so it stays true as
packs update.

```sh
scripts/list_animations.py
scripts/list_animations.py human
```

### mesh2motion: 176 clips, 8 skeletons

This is the one with real game cycles, and the only one covering non humanoids.

| Skeleton | Clips | Includes |
|---|---|---|
| human base | 87 | idle, walk, jog, sprint, crouch, jump, roll, swim, sword attack and block, spell casting, hit reactions, death |
| human addon | 37 | fighting idle, defend, power up, levitate, meditate, victory, crawl, dances |
| fox | 14 | idle, alert idle, walk, run, sneak, jump, bite, bark, howl, sit, death |
| kaiju | 10 | idle, walk, swim, attack, tail attack, roar, hit, death |
| spider | 10 | idle, walk, jump, attack, bite, eating, hit, two deaths |
| snake | 8 | idle, coiled, side winding, bite, hit, death |
| dragon | 5 | idle, walk, flap, glide |
| bird | 5 | idle, walk, flap, glide |

Clips ending `_RM` carry root motion, meaning the character moves through the
world. The rest loop in place, which is usually what a game engine wants.

### UniRig: 5 clips and a folder to fill

It ships almost nothing. What it gives you instead is a Mixamo compatible
skeleton, so anything from Mixamo retargets onto it. Download the cycles you
want as FBX for Unity, drop them in `input/animation_templates/mixamo/`, and they
appear in the animation dropdown on the next node refresh.

## Posing bones yourself

For short game cycles, two to four frames of idle, walk, attack and hit,
authoring poses directly is faster than finding and retargeting clips.

What `render_sheet.py` reads is a transforms file: a JSON list, one entry per
frame, each entry mapping bone names to transforms.

```json
[
  {},
  {"bone_14": {"rotate": [70, 0, 18]}, "bone_2": {"rotate": [-8, 0, -18]}}
]
```

Rotations are XYZ Euler degrees. Translations are Blender units. An empty object
is the rest pose.

You rarely need to write one of these by hand. `poses/roles/` holds a walk (4
frames), an attack (4), a hit (3) and an idle (2), written once against bone
roles rather than bone names, and `scripts/bone_roles.py` compiles each into a
transforms file for your rig. That route is
[below](#deriving-cycles-automatically), with what it was measured on. The other
files in `poses/` are transforms files for particular rigs, and they fit only
those rigs.

Render a compiled file:

```sh
scripts/render_sheet.py output/rigged/golem.fbx \
    --poses transforms:output/poses/golem_walk.json --angles 4 --size 220 --check
```

`--check` exits non-zero if the sheet has a fault it can measure, such as an
empty cell or a pose that did nothing. More on that
[below](#a-typo-costs-you-the-whole-sheet).

`--poses` also takes `static` for one pose, `frames:1,7,13` to sample a baked
animation, and `even:4` to spread frames across a clip's range.

::: danger Transforms files are in each bone's own space
This causes confusion, so read it carefully.

`render_sheet.py` rotates bones in their **own local coordinate space**. It
sets each pose bone's Euler rotation directly.

That is simple for a single model, but a transforms file does not carry over to
another rig. The automatic rigger gives each bone whatever roll (twist along its
length) the solve landed on, so the axis that swings a leg forward changes from
rig to rig. It was X on one model here and Z on another.

`scripts/bone_roles.py compile` does the conversion for you. A role pose file is
written about the **character's own axes**, X to its right, Y forward and Z up,
and compile turns each rotation into the bone's own axes for one rig. Those axes
are the character's as the bone's parent carries them, not fixed world axes, so
a shin's rotation adds to its thigh's.

If a transforms file that looked right on one figure sprawls on another, a
different bone roll is the likely reason. Write the pose as a role file and
compile it for each figure instead.
:::

## Which axis does what

This is for a transforms file written by bone name, such as a pose for a finger
or a jaw, which have no role. A role pose file uses the character's axes
[instead](#character-axes).

Established by probing a real rig with `render_sheet.py`, not guessed. So these
are local space axes, and they hold for that rig:

- **X bends a limb or the spine forward and back.** This is the swing axis and it
  does most of the work in every cycle.
- **Z splays a limb outward** from the body.
- **Y twists** along the bone.

A bone's own axis runs along Y, so Y twists on every rig. X and Z are the two
bending axes, and which one swings forward depends on the bone's roll. That is
the part that changed between rigs, as the box above says. On a new rig, turn
one thigh about X in a test pose and see which way it moves before you write a
whole cycle.

## Exaggerate more than feels right

At sprite size, subtlety is invisible. Numbers that work:

| Motion | Amount |
|---|---|
| Walk, leg at contact | about 28 degrees |
| Walk, knee bend on the passing frame | about 40 degrees |
| Attack wind up | about 70 degrees |
| Spine lean and twist on a strike | 14 to 18 degrees |
| Anything below | about 10 degrees is invisible at 220 px |

Three rules that make a cycle read:

1. **Move the spine, not just the limb.** A strike with a still torso looks dead.
2. **Counter swing the arms in a walk**, opposite to the legs.
3. **Bend the knee on the passing frame** or the walk reads as a glide.

## A typo costs you the whole sheet

Bone names that are not in the rig are reported, not ignored:

```
  ! bones not in the rig: bone_41, Spine
```

If you see that line, the pose did nothing and the sheet you just rendered is the
rest pose four times. Re read the bone map. Bone names differ per model, which is
covered in [rigging](/guide/rigging#bone-names-are-not-human-readable).

Compile catches the same mistake one step earlier. A role the rig lacks is
dropped and named, and compile exits 1, though it still writes the file:

```
  ! role not in this rig: spine_2 (frame 2)
  ! those parts of the pose were dropped
```

Both only catch a wrong name. Render with `--check` as well. It flags a
pose row identical to the first row at every angle and exits non-zero, which
catches a pose that did nothing even when every bone name was right: a rotation
that cancelled out, was zero, or went to an axis with no visible effect.

## Deriving cycles automatically

Because bone names differ per model, a hand written transforms file does not
survive being pointed at a second one. `scripts/bone_roles.py` gets round that in
two steps. `map` works out what each `bone_N` is from the skeleton, and
`compile` turns one pose file written against those roles into the transforms
file for that rig.

```sh
scripts/bone_roles.py map output/rigged/golem.fbx
scripts/bone_roles.py compile poses/roles/walk.json output/rigged/golem.roles.json \
    --out output/poses/golem_walk.json
scripts/render_sheet.py output/rigged/golem.fbx \
    --poses transforms:output/poses/golem_walk.json --angles 4 --size 220 --check
```

`map` prints a table of role, bone, skin weight and whether the bone is
connected to its parent, and writes `output/rigged/<stem>.roles.json`. A rig file
called `rig.fbx`, such as `output/assets/<name>/rig.fbx`, needs its own `--out`,
or every such rig writes the same roles file. `compile` also takes the FBX in
place of the roles file, and without `--out` it writes
`output/poses/<rig>_<pose>.json`.

Pass the files in `poses/roles/` to `compile`, never straight to
`render_sheet.py`. They carry `_note` keys, which compile skips and
`render_sheet.py` refuses, naming the file and then
`pose 1: bone '_note' holds a string. Expected an object such as {"rotate": [x, y, z]}`.

### Roles

`root`, `pelvis`, `spine` (then `spine_2` and on, if there are more), `chest`,
`neck` (then `neck_2`), `head` and `head_end`, and for each side `left_` and
`right_` versions of `hip`, `shoulder`, `upper_arm`, `forearm`, `hand`, `thigh`,
`shin`, `foot` and `toe`. On articulationxl rigs `root` and `pelvis` are the same
bone. Fingers, and any short chain the rules do not place, get no role, and `map`
lists them under `no role`.

The roles come from bone heads, tails and parents, and from skin weights for one
decision, the head. The rules are in
[rigging](/guide/rigging#bone-names-are-not-human-readable), and in full in
`scripts/bone_roles.py --help`.

Only `spine`, `chest`, `neck` and `head` among the middle roles exist on every
test rig, so the files in `poses/roles/` keep to those. `spine_2` exists only on
the 28-bone rig, and a file naming it fails to compile on the others.

### Character axes

`rotate` in a role file is degrees about the character's own axes, whatever the
bone's roll: **X to its right, Y forward, Z up**. Positive angles follow the
right-hand rule, applied X, then Y, then Z, like Blender's XYZ Euler.

| rotate | a part hanging below its joint | a part rising above it |
|---|---|---|
| +X | swings forward | tips back |
| +Y | moves toward the character's left: a left arm lifts outward, a right arm swings across the body | tips toward the character's right |
| +Z | turns to the character's left seen from above; on the chest, the right shoulder comes forward | the same |

So a knee bend is -X on the shin, an elbow bend +X on the forearm, and +X on a
foot lifts the toe. To mirror a frame, swap `left_` and `right_` and negate Y
and Z. `@shape_keys` and `@props` are copied into the compiled frame unchanged
for `render_sheet.py`.

`translate` is in rig units along the same axes, and moves only a bone that is
not connected to its parent, because Blender pins a connected bone's head to its
parent's tail. `map` says per bone. In practice, translate the pelvis. Compile
drops a translate on a connected bone and exits 1:

```
  ! translate on a connected bone, which Blender ignores: chest (bone_2, frame 2)
```

The axes assume a rest pose with the arms hanging at the sides, as every
articulationxl rig here has. On a T-pose rig the arm numbers do not carry over:
compiled for `input/3d/mixamo.fbx`, a T-pose, frame 1 of the walk moved the right
hand forward by 0.051 of the figure's height, against 0.153 on the 47-bone
`unit_warrior`.

To see which way a compiled pose moves each part without rendering, `probe`
prints how far each role's bone end moved along right, forward and up:

```sh
scripts/bone_roles.py probe output/poses/golem_walk.json output/rigged/golem.fbx --frame 1
```

### Measured on five rigs

Measured on 2026-09-16 on five articulationxl figures: `output/rigged/unit_rogue.fbx`
(24 bones), `output/assets/alchemist_warrior/rig.fbx` (28),
`output/rigged/unit_alchemist.fbx` and `output/rigged/unit_beastmaster.fbx` (30
each) and `output/rigged/unit_warrior.fbx` (47). The figures measure 1.84 to 2.11
units between their lowest and highest bone ends.

- **Facing.** `map` found every one facing -Y with up +Z. Before snapping to
  those axes, up was 1.1 to 5.0 degrees off and the toes 0.0 to 5.4 degrees.
- **Compile.** Posed in Blender, every test rotation on a bone whose parent
  stayed at rest matched the intended orientation to within 1.44e-05 per matrix
  element, and a thigh then shin, or upper arm then forearm, to within 1.35e-05.
- **Walk.** Each compiled `poses/roles/` file was posed in Blender and its bone ends measured
  along the character's axes, which is what `probe` reports. On frame 1, the
  contact with the left foot leading, in rig units:

  | rig | left toe forward | right hand forward | right toe | left hand |
  |---|---|---|---|---|
  | 24 | +0.466 | +0.317 | -0.767 | -0.222 |
  | 28 | +0.434 | +0.308 | -0.733 | -0.226 |
  | 30, unit_alchemist | +0.470 | +0.317 | -0.777 | -0.220 |
  | 30, unit_beastmaster | +0.469 | +0.313 | -0.787 | -0.219 |
  | 47 | +0.469 | +0.304 | -0.759 | -0.218 |

  Frame 3 mirrors it with the same signs, and on the passing frames the swinging
  knee bends 42 degrees the natural way, the foot going back, on all five.
- **Attack.** The right hand moves back by 0.533 to 0.593 units on the wind up
  and forward by 0.577 to 0.646 on the strike, on every rig. It is a swing, not
  an overhead strike: on the wind up the hand stays 0.31 to 0.39 units below the
  shoulder joint.
- **Hit and idle.** On frame 2 of `poses/roles/hit.json` the head tips back 18
  degrees against the chest, and on frame 2 of `poses/roles/idle.json` it dips 10
  degrees forward, on all five.
- **Sheets.** All 20, walk, attack, hit and idle on all five rigs, rendered with
  `--check` at 220 px and 4 angles and passed, taking 73 to 177 s each while other
  jobs shared the container. Read side by side, each pose moves every figure the
  same way in the same phase.

The per-rig transforms files in `poses/` do not agree with each other, measured
the same way. On frame 2, `poses/walk.json` on the 28-bone rig, `rig24_walk.json`
on the 24-bone rig and `rig47_walk.json` on the 47-bone rig bend the knee the wrong way,
the shin swinging forward of the thigh by 41.9, 45.6 and 45.0 degrees.
`rig24_attack.json` and `rig47_attack.json` swing the left arm where `attack.json`
swings the right.

### Which bone is the head

The 28 and 47-bone rigs have two bones above the chest, and the 24 and 30-bone
rigs three. An earlier `map` took the last one for the head. On the three-bone
rigs that bone is an end marker the mesh hardly follows, so the head turns in
`poses/roles/hit.json` and `idle.json` did almost nothing there: turning it +18 X moved no
vertex more than 0.004 units on the 24-bone rig, 0.017 on unit_alchemist and
0.009 on unit_beastmaster.

`map` now compares skin weights. The last bone above the chest is `head_end` when
it carries less than a quarter of the skin weight of the bone before it, and the
bone before it is the head; otherwise the last bone is the head. When the bone
before it carries no weight, or the rig has none, the count decides: three or
more bones above the chest make the last one `head_end`. Both rules give the same
map on the five test rigs, `input/3d/mixamo.fbx` and
`output/mpfb/human_game_engine.glb`. The `head_end` line of the `map` table shows
the numbers, such as `bone_5 carries 0.009 of bone_4's skin weight (13.3 of 1470.7)`
on the 24-bone rig.

With the fix, turning the head role +18 X moves the highest head vertex back by
0.070 to 0.083 units on all five rigs, and the head tips back on the 24 and
30-bone hit sheets. `compile` refuses a roles file written before the fix with
`<file>: made by an older bone_roles.py map, before the head_end rule and connected bones; run map again`.

### Not tested yet

- Rigs whose last bone above the chest carries between 0.175 and 0.611 of the
  weight of the bone before it. The quarter threshold sits in a gap seen on seven
  rigs only.
- A real rig with no skin weights. The count rule ran only on real skeletons with
  their weights zeroed.
- A rig not facing an armature axis. Every rig mapped so far snapped, so that path
  has never run.
- The `hip` role. No rig here has a bone between the pelvis and the thigh.
- `translate` on hands, feet and toes, where connection varies by rig. It was
  measured only on the pelvis, the neck and the chest.
- A compiled file carrying `@shape_keys` or `@props` rendered as a sheet. Only
  the compile output was checked.
- Mixamo and MPFB rigs were mapped but not rendered, and no non-humanoid skeleton
  was tried.
- Keeping the feet on the floor. Nothing does: on the walk's contact frames the
  lowest foot or toe bone end sits 0.026 to 0.100 units above where it rests.
- Using the compiled poses in a game engine.

## Frames as models, not as a sheet

If your game renders 3D at runtime, consider exporting each pose as its own model
instead of as a sprite sheet.

A sheet of pre rendered frames has to be re cut for every camera direction, and it
cannot survive the camera rotating to an angle you did not bake. Posed models go
through the same rendering path as the resting figure and come out correct at any
angle.

They can share the resting figure's texture, because posing moves vertices and
does not touch UVs. So only the geometry is written per frame.

## Faces and lip sync

The riggers give a figure no face. `scripts/face_rig.py add-jaw` adds a jaw bone
you can turn per sheet row, and a transforms file can set shape keys per row with
`@shape_keys`; both are in [rigging](/guide/rigging#faces). How to turn a voice
line into mouth shapes, and why a talking face belongs on a portrait rather than
on a sprite sheet, is researched in [lip sync](/reference/lip-sync), and
[talking portraits](/guide/talking-portraits) builds one.

## Licensing, briefly

All three animation sources are clear for a commercial game:

- mesh2motion's 176 clips are CC0. No conditions at all.
- Its 7 motion capture clips are free for commercial use.
- Mixamo is royalty free with no attribution.

The one shared restriction is that you may not redistribute the animation files
themselves as animation files. Baking a clip onto your own model and shipping that
inside a game is the permitted use. [Full detail](/guide/licensing).
