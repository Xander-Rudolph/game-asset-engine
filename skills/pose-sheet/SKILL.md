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

## 2. Get the rig's bone names

The rigging default emits generic `bone_0` to `bone_N`, so the map differs per
asset and **must be read before authoring poses**. Two characters from this same
pipeline came out with 47 and 28 bones.

```sh
docker exec comfyui python3 -c "
import bpy; bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='/app/output/rigged/<name>.fbx')
a=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
for b in a.data.bones:
    print(b.name, b.parent.name if b.parent else '-', [round(v,2) for v in b.head_local])"
```

Read the hierarchy from the head positions. The chain rising from the root is the
spine then head. Chains branching at chest height going sideways are the arms.
Chains from the root going down are the legs. `poses/_bones.md` records a worked
example.

## 3. Author the poses

A pose file is a JSON **list**, one entry per frame, each a map of bone name to
transform. Rotations are XYZ Euler **degrees** in the bone's local space.
Translations are Blender units.

```json
[
  {},
  {"bone_14": {"rotate": [70, 0, 18]}, "bone_2": {"rotate": [-8, 0, -18]}}
]
```

**Axis convention, established by probing a real rig. Do not guess.**

- **X bends a limb or the spine forward and back.** The swing axis, and it does
  most of the work in every cycle.
- **Z splays a limb outward** from the body.
- **Y twists** along the bone.

Working examples in `poses/`: `idle.json` (2 frames), `walk.json` (4),
`attack.json` (4), `hit.json` (3). Copy the nearest and adjust.

Rules of thumb that make cycles read at sprite size:

- **Move the spine, not just the limb.** A strike with a still torso looks dead.
  14 to 18 degrees of lean and twist sells it.
- **Counter swing the arms in a walk**, opposite to the legs.
- **Exaggerate.** At 220 pixels a 10 degree rotation is invisible. Walk contact
  poses want about 28 degrees, an attack wind up about 70.
- **Bend the knee about 40 degrees on the passing frame** or the walk glides.

## 4. Render

```sh
scripts/render_sheet.py output/rigged/<name>.fbx \
    --poses transforms:poses/walk.json --angles 4 --size 220 \
    --out output/sheets/<name>_walk.png
```

`--poses` also takes `static`, `frames:1,7,13` and `even:N`.

Other flags: `--angles`, `--azimuth-start`, `--elevation`, `--size`, `--zoom`,
`--persp`, `--key`, `--ambient`, `--clay-color`, `--flat`.

## 5. Look at it, then say what you see

**Read the sheet** and judge it before handing it over. A mis signed rotation
produces a confident, wrong, perfectly rendered cycle.

Check in this order:

1. Did any bone name miss? The script prints `! bones not in the rig: ...`. If so
   the pose did nothing and you are looking at the rest pose repeated.
2. Do the facings match the game's camera? Pick the cell where the figure faces
   down and to the right on screen, and say which cell index that is. That is the
   first facing, and the engine's mapping starts there.
3. Does the motion read at the size it will ship at? If you rendered at 340 and
   the game uses 128, render again at 128 before approving.

## Rules

- **Orthographic by default.** Keep it. It is what makes two assets rendered on
  different days share a scale. Use `--persp` only if asked.
- **Untextured meshes get grey clay automatically**, because Blender's default
  white against a white world light renders as a featureless blob. Say that
  rather than letting grey read as a bug.
- **A bone name not in the rig is reported, not ignored.** If you see that line,
  re-read the bone map.
- **Do not hand over a sheet you have not looked at.**
- Sheets go in `output/sheets/`, pose files in `poses/`. `output/` is gitignored,
  `poses/` is not.
- The in graph sprite renderer (`preset_sprites_iso_8.json`) is perspective, so
  it is fine for a turnaround and wrong for sprites that must match in scale. Use
  this script for anything the game loads.
