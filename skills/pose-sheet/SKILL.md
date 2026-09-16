---
name: pose-sheet
description: Render a rigged model to a sprite sheet - camera angles across, animation frames down - for 2 to 4 frame game cycles like idle, walk, attack and hit. Use when the user wants sprite sheets, animation frames, a turnaround, facing sheets, or 2D sprites from a 3D asset. Also use to author or adjust bone poses for a cycle, or to work out which way a unit should face.
---

# Pose sheets: a rigged model to game sprite frames

`scripts/render_sheet.py` drives Blender inside the ComfyUI container. Work in
the asset-engine repo root.

Sheet layout is **angles across, poses down**, which is the order most engines
slice.

## Before you start

```sh
scripts/doctor.py --skip-models
```

This skill needs the container running and `bpy` importable inside it, which are
two separate checks in that output. If `blender` is not ok, nothing here will
work and the failure will look like a broken model rather than a missing
dependency.

If ComfyUI is not running, do not guess your way around it. The doctor prints the
one command to run. On a cold start the container is up before the server is,
so wait rather than restarting.

## Why Blender and not a ComfyUI graph

Worth knowing before trying to simplify this into a workflow. It cannot be done.
Nothing in the install outputs the rigged mesh type that the in graph posing node
consumes, so posing is unreachable headlessly. And the 3D pack's loader reads
only `.obj`, `.ply` and `.glb`, never the `.fbx` that rigging produces. Blender is
the only thing here that reads both and can pose a skeleton.

## 1. Ask which camera the game uses

Do this before rendering anything. It is the single most common source of wrong
sprites, and it is not visible in one frame.

| Game view | Elevation | First azimuth |
|---|---|---|
| 2 to 1 isometric diamonds | 30 (default) | 45 (default) |
| 4 to 3 diamonds | 48.6 | 45 |
| Top down on a square grid | 90 | 0 |
| Side on | 0 to 15 | 0 |

The rule is `elevation = arcsin(tile height / tile width)`. The azimuth starts at
45 for isometric because an isometric camera looks down the diagonal between the
world axes, so a unit facing a world direction is not facing the camera.

Render at 0, 90, 180, 270 for an isometric game and every unit stands square on
while the ground runs diagonally underneath.

## 2. Map the rig's bones to roles

The rigging default emits generic `bone_0` to `bone_N`, and the count and order
differ per asset: five characters from this pipeline came out with 24, 28, 30,
30 and 47 bones. Do not read the map by hand. Work it out:

```sh
scripts/bone_roles.py map output/rigged/<name>.fbx
```

It writes `output/rigged/<name>.roles.json` and prints a table. For
`output/assets/<name>/rig.fbx`, pass `--out output/rigged/<name>.roles.json`, or
every rig called `rig.fbx` writes the same file. Read three things before going
on:

- **`up` and `forward`** name an armature axis each (+Z and -Y on every rig so
  far), with the degrees the raw direction was off it. A vector in brackets
  instead means the facing did not snap. That path has never run on a real rig,
  so say so and check the sheet closely.
- **The `head_end` line** says which bone is the head and why, from skin
  weights. On the 24 and 30 bone rigs the top bone is `head_end`, an end marker,
  and the bone below it is the head.
- **`no role`** lists bones a role file cannot move, such as fingers.

`map` reads `.fbx` and `.glb`. It stops with a message when it cannot find a
pelvis with a spine and two legs, or a chest with an arm to each side. No
non-humanoid skeleton has been tried. If it stops, go to step 3b.

## 3. Compile the poses

`poses/roles/` holds `walk.json` (4 frames), `attack.json` (4), `hit.json` (3)
and `idle.json` (2), written against roles rather than bone names. Compile each
for this rig:

```sh
for p in walk attack hit idle; do
  scripts/bone_roles.py compile poses/roles/$p.json output/rigged/<name>.roles.json
done
```

Each writes `output/poses/<name>_<pose>.json`, the transforms file
`render_sheet.py` reads. Compile exits 1 and names what it dropped, though it
still writes the file:

- `! role not in this rig: spine_2 (frame 2)`: a role this skeleton lacks.
  `spine_2` exists only on the 28 bone rig, which is why the files in
  `poses/roles/` keep to `spine`, `chest`, `neck` and `head`.
- `! translate on a connected bone, which Blender ignores: chest (bone_2, frame 2)`:
  only unconnected bones take `translate`, which in practice means the pelvis.
- A roles file from before the `head_end` rule is refused with
  `made by an older bone_roles.py map, before the head_end rule and connected bones; run map again`.

**Never pass a `poses/roles/` file straight to `render_sheet.py`.** It refuses
the `_note` keys with `pose 1: bone '_note' holds a string`.

To write a new role pose, copy the nearest file in `poses/roles/`. `rotate` is
degrees about the **character's own axes**, whatever the bone's roll: **X to its
right, Y forward, Z up**, right-hand rule, applied X then Y then Z.

- **+X** swings a part hanging below its joint forward (thigh, arm) and tips a
  rising part back (spine, neck, head). A knee bend is -X on the shin, an elbow
  bend +X on the forearm, and +X on a foot lifts the toe.
- **+Y** moves a hanging part toward the character's left, so a left arm lifts
  outward, and tips a rising part toward its right.
- **+Z** turns a part to the character's left seen from above; on the chest the
  right shoulder comes forward.
- To mirror a frame, swap `left_` and `right_` and negate Y and Z.
- Each rotation is about those axes as the bone's parent carries them, so a
  shin's rotation adds to its thigh's.
- `@shape_keys` and `@props` are copied through for `render_sheet.py`.
- The axes assume the arms hang at rest, as on every articulationxl rig here.
  On a T-pose rig the arm numbers do not carry over. Say so if the rig is one.

Check a compiled pose's direction without rendering. `probe` prints how far each
role's bone end moved right, forward and up:

```sh
scripts/bone_roles.py probe output/poses/<name>_walk.json output/rigged/<name>.fbx --frame 1
```

Measured on 24, 28, 30 and 47 bone rigs, the four role files move every figure
the same way, and all 20 sheets passed `--check`. The other files in `poses/`
are transforms files for single rigs, and they disagree: `walk.json`,
`rig24_walk.json` and `rig47_walk.json` bend the knee the wrong way on frame 2,
a passing frame. Do not copy them to a new rig.

Rules of thumb that make cycles read at sprite size:

- **Move the spine, not just the limb.** A strike with a still torso looks dead.
  14 to 18 degrees of lean and twist sells it.
- **Counter swing the arms in a walk**, opposite to the legs.
- **Exaggerate.** At 220 pixels a 10 degree rotation is invisible. Walk contact
  poses want about 28 degrees, an attack wind up about 70.
- **Bend the knee about 40 degrees on the passing frame** or the walk glides.

## 3b. Only for what roles do not cover: bone names and the axis probe

Fingers, other bones listed as `no role`, a `jaw` added by
`scripts/face_rig.py add-jaw`, and any rig `map` cannot read are posed by bone
name in a transforms file. There, rotations are XYZ Euler **degrees** in the
**bone's own local space**, and translations are Blender units.

```json
[
  {},
  {"bone_14": {"rotate": [70, 0, 18]}, "bone_2": {"rotate": [-8, 0, -18]}}
]
```

For a rig `map` cannot read, dump the raw hierarchy, and read it from the head
positions: the chain rising from the root is the spine then head, chains
branching sideways at chest height are the arms, and chains going down from the
root are the legs.

```sh
docker exec "$(python3 scripts/_engine.py)" python3 -c "
import bpy; bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='/app/output/rigged/<name>.fbx')
a=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
for b in a.data.bones:
    print(b.name, b.parent.name if b.parent else '-', [round(v,2) for v in b.head_local])"
```

**Probe the axes before authoring by bone name.** The rigger gives each bone
whatever roll its solve landed on, so the local axis that swings a leg can
change between rigs: it was X on one model here and Z on another.
`poses/_axis_probe.json` is a rest frame, then `bone_20` (a thigh) at X 35 and
at Z 35, `bone_14` (an upper arm) at X -60 and `bone_2` at X 25, as
`poses/_bones.md` maps the 28 bone rig. A `bone_N` name means a different bone
on a different rig, so copy it, replace each with the bone you are about to
pose, and render it:

```sh
scripts/render_sheet.py output/rigged/<name>.fbx \
    --poses transforms:poses/<name>_axis_probe.json --angles 4 --size 220 \
    --out output/sheets/<name>_probe.png --check
```

Read which way each row moved. On the rig that was probed, X bent a limb or the
spine forward and back, Z splayed a limb outward and Y twisted along the bone.
Y twists on every rig, because a bone's own axis runs along Y; which of X and Z
swings forward is what changes. The jaw is the exception that needs no probe:
`add-jaw` builds it so a positive X opens it. `--check` passes a jaw row that
changed pixels inside an unchanged silhouette, and prints how many per angle;
that proves something changed, not that it reads as a jaw. Look at the face.

## 4. Render

```sh
scripts/render_sheet.py output/rigged/<name>.fbx \
    --poses transforms:output/poses/<name>_walk.json --angles 4 --size 220 \
    --out output/sheets/<name>_walk.png
```

`--poses` also takes `static`, `frames:1,7,13` and `even:N`.

Other flags: `--angles`, `--azimuth-start`, `--elevation`, `--size`, `--zoom`,
`--persp`, `--span`, `--key`, `--ambient`, `--clay`, `--clay-color`, `--flat`,
`--check`, `--keep-frames` and `--timeout`. The per-cell PNGs under
`output/_sheet_frames/` are deleted once the sheet is composed unless you pass
`--keep-frames`.

## 5. Check what is arithmetic, then look at what is not

```sh
scripts/render_sheet.py output/rigged/<name>.fbx \
    --poses transforms:output/poses/<name>_walk.json --angles 4 --size 220 \
    --out output/sheets/<name>_walk.png --check
```

`--check` computes the faults that are numbers and exits non-zero if it finds
any:

- an empty or near-empty cell, meaning the render failed or the subject rotated
  out of frame
- **a pose row identical to row 0 at every angle**, meaning the pose did nothing
  and you are looking at the rest pose repeated. The missing-bone warning catches
  a typo; this catches a rotation that cancelled, was zero, or went to an axis
  with no effect
- a subject touching its cell border, so the frame is clipping it
- a coverage spread across angles that usually means framing

It also **names the down-and-right facing** rather than asking you to find it,
because the azimuth list is arithmetic and the script already has it.

`scripts/sheet_check.py <sheet> --cell <size>` does the same to a sheet you
already have.

**Then read the sheet yourself for the one thing no check can see: whether the
motion reads as the motion.** A sheet that passes every check above can still be
a confident, well rendered, wrong cycle. Judge it at the size it ships at, not at
340 pixels.

## Rules

- **Orthographic by default.** Keep it. It keeps one asset the same size across
  its own angles and frames, **not across assets**: each model is framed to its
  own bounding box, so a dagger and a golem fill their cells alike. A set drawn
  at one scale needs the same `--span <units>` on every render, on meshes
  given one world size by `scripts/normalise_mesh.py <meshes> --height <units>`
  (`--footprint <units>` for anything tile bound; it overwrites in place unless
  given `--suffix` or `--out-dir`) and confirmed by the same command with
  `--check`. **Never normalise a rigged FBX:** the file it writes has no
  skeleton. Normalising before rigging is undone too: the rigger rescales each
  model so its largest dimension is 2.0 units (four upright figures rigged here
  measured 2.000 tall), so upright figures under one `--span` render the same
  height and a model longer than it is tall comes back shorter. Say so. Use
  `--persp` only if asked.
- **Untextured meshes get grey clay automatically**, because Blender's default
  white against a white world light renders as a featureless blob. Say that
  rather than letting grey read as a bug.
- **A bone name not in the rig is reported, not ignored.** If you see that line,
  the transforms file was written for another rig: compile the role file for
  this one, or re-read the bone map for a bone name pose.
- **Do not hand over a sheet you have not looked at.**
- Sheets go in `output/sheets/` and compiled pose files in `output/poses/`, both
  gitignored. A new role pose goes in `poses/roles/`, and a bone name pose for
  one rig in `poses/`, which is tracked.
- The in graph sprite renderer (`preset_sprites_iso_8.json`) is perspective, so
  it is fine for a turnaround and wrong for sprites that must match in scale. Use
  this script for anything the game loads.
