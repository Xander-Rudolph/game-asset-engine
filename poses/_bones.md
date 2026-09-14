# articulationxl skeleton, as produced for a humanoid

UniRig's `articulationxl` template emits generic `bone_N` names, not Mixamo ones.
Dump any rig's own map with:

```sh
docker compose --profile comfy exec -T comfyui python3 -c "
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
| `bone_10`–`bone_12` | +x fingers |
| `bone_13` `bone_14` `bone_15` `bone_16` | -x shoulder, upper arm, forearm, hand |
| `bone_17`–`bone_19` | -x fingers |
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
