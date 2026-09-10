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

For the alchemist warrior (28 bones), +x is one side, -x the other:

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
