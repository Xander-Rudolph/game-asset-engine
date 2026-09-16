# articulationxl skeleton, as produced for a humanoid

UniRig's `articulationxl` template emits generic `bone_N` names, not Mixamo ones.
Dump any rig's own map with:

```sh
docker exec "$(python3 scripts/_engine.py)" python3 -c "
import bpy; bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='/app/output/<rigged>.fbx')
a=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
for b in a.data.bones: print(b.name, b.parent.name if b.parent else '-', list(round(v,2) for v in b.head_local))"
```

This map is for one 28-bone humanoid, the rig that `walk.json`, `attack.json`,
`hit.json` and `idle.json` were written for. +x is one side, -x the other:

| bones | part |
|---|---|
| `bone_0` | root / pelvis |
| `bone_1` `bone_2` `bone_3` | spine, lower to chest |
| `bone_4` `bone_5` | neck, head |
| `bone_6` `bone_7` `bone_8` `bone_9` | +x shoulder, upper arm, forearm, hand |
| `bone_10` to `bone_12` | +x fingers |
| `bone_13` `bone_14` `bone_15` `bone_16` | -x shoulder, upper arm, forearm, hand |
| `bone_17` to `bone_19` | -x fingers |
| `bone_20` `bone_21` `bone_22` `bone_23` | +x thigh, shin, foot, toe |
| `bone_24` `bone_25` `bone_26` `bone_27` | -x thigh, shin, foot, toe |

Rotations are XYZ Euler **degrees** in the bone's local space; a bone's own
axis runs along Y, so bending a limb is usually X. Translations are Blender
units along the bone's axes.

## rig24 and rig47 poses

A pose file only fits the skeleton it was written for, because the bone count
and order differ per figure. `rig24_*.json` and `rig47_*.json` hold the same
walk, attack and hit cycles, derived for two other skeletons from their limb
chains:

| files | bones | spine | arm swing, +x and -x | thigh and shin, +x | thigh and shin, -x |
|---|---|---|---|---|---|
| `rig24_*.json` | 24 | `bone_2` | `bone_7`, `bone_12` | `bone_16` `bone_17` | `bone_20` `bone_21` |
| `rig47_*.json` | 47 | `bone_2` | `bone_6`, `bone_21` | `bone_35` `bone_36` | `bone_41` `bone_42` |

The derivation picked the same bones on two 30-bone rigs, which only add two
short chains off the root, so `rig24_*.json` applies to those too. Check a
rig's own map against this table before using either set.

## Roles: one pose file for every rig

`scripts/bone_roles.py` works out what each `bone_N` is from the skeleton's
geometry, and the files in `poses/roles/` are written against those role names
in the character's own axes. Compiling a role file for a rig gives an ordinary
transforms file, so one `walk.json` drives every skeleton in this note.

```sh
scripts/bone_roles.py map output/rigged/unit_warrior.fbx
scripts/bone_roles.py compile poses/roles/walk.json output/rigged/unit_warrior.roles.json \
    --out output/poses/unit_warrior_walk.json
scripts/render_sheet.py output/rigged/unit_warrior.fbx \
    --poses transforms:output/poses/unit_warrior_walk.json --angles 4 --size 220 --check
```

`map` writes `output/rigged/<stem>.roles.json` unless `--out` says otherwise;
give a rig called `rig.fbx` its own `--out`, or every such rig writes the same
file. `compile` also takes the FBX itself, and `probe TRANSFORMS RIG` prints how
far each role's bone end moved along the character's axes, which is the quick
way to check a new pose's direction. `compile` refuses a roles file written by
an earlier `map`, from before the `head_end` rule, so run `map` again on such a
rig. `scripts/bone_roles.py --help` has the rules in full.

### How the roles are found

Bone heads, tails and parents are read, and skin weights for one call only, the
head (below). The root has no parent, and the pelvis is the first bone from the
root down with three or more children. The legs are
the two pelvis chains reaching furthest; on each, the thigh and shin are the
consecutive pair with the greatest combined length, and the foot is the shin's
child reaching furthest horizontally. The spine is the other pelvis chain
pointing most nearly away from the legs, followed through the straightest
child; the chest is the first spine bone with chains leaving it to both sides,
which are the arms. Up runs from the midpoint of the ankles to the top of the
spine chain.

**Facing comes from the feet.** Forward is the sum of both feet's ankle to toe
tip vectors with the up component removed, and right is forward crossed with
up. Every test rig faces -Y, so the `+x` side in the tables above is the
character's own left:

| rig | bones | up, off +Z | toes, off -Y |
|---|---|---|---|
| `output/rigged/unit_rogue.fbx` | 24 | 1.6 degrees | 3.0 degrees |
| `output/assets/alchemist_warrior/rig.fbx` | 28 | 1.8 degrees | 0.0 degrees |
| `output/rigged/unit_alchemist.fbx` | 30 | 5.0 degrees | 4.3 degrees |
| `output/rigged/unit_beastmaster.fbx` | 30 | 3.6 degrees | 5.4 degrees |
| `output/rigged/unit_warrior.fbx` | 47 | 1.1 degrees | 3.0 degrees |

Both directions are snapped to the nearest armature axis when within 20
degrees.

### The role map on the test rigs

| role | 24 bones | 28 bones | 30 bones (both) | 47 bones |
|---|---|---|---|---|
| root and pelvis | `bone_0` | `bone_0` | `bone_0` | `bone_0` |
| spine | `bone_1` | `bone_1` | `bone_1` | `bone_1` |
| spine_2 | none | `bone_2` | none | none |
| chest | `bone_2` | `bone_3` | `bone_2` | `bone_2` |
| neck | `bone_3` | `bone_4` | `bone_3` | `bone_3` |
| head | `bone_4` | `bone_5` | `bone_4` | `bone_4` |
| head_end | `bone_5` | none | `bone_5` | none |
| left shoulder, upper_arm, forearm, hand | `bone_6` to `bone_9` | `bone_6` to `bone_9` | `bone_6` to `bone_9` | `bone_5` to `bone_8` |
| right shoulder, upper_arm, forearm, hand | `bone_11` to `bone_14` | `bone_13` to `bone_16` | `bone_11` to `bone_14` | `bone_20` to `bone_23` |
| left thigh, shin, foot, toe | `bone_16` to `bone_19` | `bone_20` to `bone_23` | `bone_16` to `bone_19` | `bone_35` to `bone_38` |
| right thigh, shin, foot, toe | `bone_20` to `bone_23` | `bone_24` to `bone_27` | `bone_20` to `bone_23` | `bone_41` to `bone_44` |
| no role | `bone_10`, `bone_15` below the hands | `bone_10` to `bone_12`, `bone_17` to `bone_19` below the hands | as 24, plus `bone_24` to `bone_29`, two midline chains off the pelvis | the finger chains, and `bone_39`, `bone_40`, `bone_45`, `bone_46`, a second short chain off each shin |

Checked against the tables above: the 28-bone map agrees bone for bone, all 23
roles and the six finger bones. The rig24 arm swing, thigh and shin bones agree
on the 24-bone and both 30-bone rigs, and the rig47 ones on the 47-bone rig.
Their spine column, `bone_2`, is the chest in role terms, because the arms leave
it; the 28-bone files lean `bone_2` too, which is `spine_2` there.

**The head is settled by skin weights.** The 28 and 47-bone rigs have two bones
above the chest, and the 24 and 30-bone rigs three. On the three-bone rigs the
last one is an end marker that the mesh hardly follows. `map` compares skin
weights: the last bone above the chest is `head_end` when it carries less than
a quarter of the weight of the bone before it, and otherwise it is the head.
When the bone before it carries no weight, or the rig has none, the count
decides instead: three or more bones make the last one `head_end`. Both rules
give the same map on all seven rigs checked, but the count is only a guess at
how the rigger laid out the neck, while the weights say which bone the mesh
follows:

| rig | last bone above the chest | its skin weight, against the bone before it | role |
|---|---|---|---|
| 24 | `bone_5` | 13.3 of 1470.7 (0.009) | head_end |
| 28 | `bone_5` | 680.3 of 1113.2 (0.611) | head |
| 30, unit_alchemist | `bone_5` | 251.9 of 1439.8 (0.175) | head_end |
| 30, unit_beastmaster | `bone_5` | 116.4 of 1457.6 (0.080) | head_end |
| 47 | `bone_4` | 1436.1 of 306.5 (4.685) | head |
| `input/3d/mixamo.fbx` | `mixamorig:HeadTop_End` | 0.0 of 523.0 (0.000) | head_end |
| `output/mpfb/human_game_engine.glb` | `head` | 4777.3 of 246.8 (19.361) | head |

Posed in Blender, turning the head role +18 X moves the highest head vertex
back by 0.070 to 0.083 units on all five test rigs. The same turn on `head_end`,
which an earlier version of this tool called the head, moved no vertex more
than 0.004 (24 bones), 0.017 (unit_alchemist) or 0.009 (unit_beastmaster).

### Character axes

`rotate` in a role file is degrees about the character's own axes, whatever the
bone's roll: X to its right, Y forward, Z up. Positive angles follow the
right-hand rule, applied X, then Y, then Z, like Blender's XYZ Euler. Each
rotation is about those axes as the bone's parent carries them, so a shin's
rotation adds to its thigh's.

| rotate | a part hanging below its joint | a part rising above it |
|---|---|---|
| +X | swings forward | tips back |
| +Y | moves toward the character's left: a left arm lifts outward, a right arm swings across the body | tips toward the character's right |
| +Z | turns to the character's left seen from above; on the chest, the right shoulder comes forward | the same |

So a knee bend is -X on the shin, an elbow bend +X on the forearm, and +X on a
foot lifts the toe. To mirror a frame, swap `left_` and `right_` and negate Y
and Z. Keys starting with `_` are notes and compile skips them; `@shape_keys`
and `@props` are copied into the compiled frame for `render_sheet.py`.

The axes assume a rest pose with the arms hanging at the sides, as every
articulationxl rig here has. On a T-pose rig an X rotation that swings a hanging
arm forward mostly twists an arm held out level, so the arm numbers do not carry
over. Compiled for `input/3d/mixamo.fbx`, a T-pose, frame 1 of the walk moved the
right hand forward by 0.051 of the figure's height against 0.153 on
`unit_warrior`, while the leading toe still moved 0.192 against 0.235.

`translate` is also accepted, in rig units along the same axes, but only moves
a bone that is not connected to its parent: Blender pins a connected bone's
head to its parent's tail and ignores its location. On the five test rigs the
chest, head, shins, upper arms and forearms are always connected, the pelvis,
spine, neck, thighs and shoulders never are, and hands, feet and toes vary from
rig to rig; `map` lists it per bone. `compile` drops a translate on a connected
bone, names it and exits 1. In practice, translate the pelvis. Measured in
Blender on all five rigs: a location set straight onto the connected chest moved
it by 0, a pelvis translate of +0.05 along Y moved the head forward by 0.05 to
within 5.6e-06, and a translate on the unconnected neck under a spine turned 30
degrees landed within 5.3e-06 of where the parent-carried axes put it. The test
rigs measure 1.84 to 2.11 units between their lowest and highest bone ends, so a
translation is only roughly the same share of each figure.

`compile` maps each rotation into armature axes and conjugates it by the bone's
rest orientation, which is what a pose bone's own Euler rotation means. Posed in
Blender on all five rigs, every test rotation on a bone whose parent stayed at
rest matched the intended armature-space orientation to within 1.44e-05 per
matrix element, and a thigh then shin, or upper arm then forearm, matched the
product of the two rotations to within 1.35e-05.

### Measured on the test rigs

Each compiled file was posed in Blender and its bone ends measured along the
character's axes (`probe` reports the same displacements). On frame 1 of
`poses/roles/walk.json`, the contact with the left foot leading:

| rig | left toe forward | right hand forward | right toe | left hand |
|---|---|---|---|---|
| 24 | +0.466 | +0.317 | -0.767 | -0.222 |
| 28 | +0.434 | +0.308 | -0.733 | -0.226 |
| 30, unit_alchemist | +0.470 | +0.317 | -0.777 | -0.220 |
| 30, unit_beastmaster | +0.469 | +0.313 | -0.787 | -0.219 |
| 47 | +0.469 | +0.304 | -0.759 | -0.218 |

Frame 3 mirrors it with the same signs, and on the passing frames the swinging
knee bends 42 degrees the natural way, the foot going back, on all five. In
`poses/roles/attack.json` the right hand moves back by 0.533 to 0.593 units on
the wind up and forward by 0.577 to 0.646 on the strike, on every rig. It is a
swing, not an overhead strike: on the wind up the hand stays 0.31 to 0.39 units
below the shoulder joint. On frame 2 of `poses/roles/hit.json` the head tips
back 18 degrees against the chest, and on frame 2 of `poses/roles/idle.json` it
dips 10 degrees, on all five rigs.

The per-rig local files do not agree with each other. Measured the same way,
the passing frames of `walk.json` on the 28-bone rig, `rig24_walk.json` on the
24-bone rig and `rig47_walk.json` on the 47-bone rig bend the knee the other
way, the shin swinging forward of the thigh by 41.9, 45.6 and 45.0 degrees on
frame 2. `rig24_attack.json` and `rig47_attack.json` swing the left arm where
`attack.json` swings the right.

All 20 sheets, walk, attack, hit and idle on all five rigs, rendered with
`--check` at 220 px and 4 angles and passed, taking 73 to 177 s each. Read side
by side, each pose moves every figure the same way in the same phase, and on the
hit sheets the head now tips back on the 24 and 30-bone figures too. The long
coat on the 24, 30 and 47-bone figures swings out with the legs on the walk's
stride, and thin stretched strands show near the arms in some cells; both are
the mesh and its skinning, so look past them when judging the pose.
