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

A pose file is a JSON list. One entry per frame. Each entry maps bone names to
transforms.

```json
[
  {},
  {"bone_14": {"rotate": [70, 0, 18]}, "bone_2": {"rotate": [-8, 0, -18]}}
]
```

Rotations are XYZ Euler degrees. Translations are Blender units. An empty object
is the rest pose.

Worked examples live in `poses/`: `idle.json` with 2 frames, `walk.json` with 4,
`attack.json` with 4, `hit.json` with 3. Copy the nearest one and adjust.

Render it:

```sh
scripts/render_sheet.py output/rigged/golem.fbx \
    --poses transforms:poses/walk.json --angles 4 --size 220
```

`--poses` also takes `static` for one pose, `frames:1,7,13` to sample a baked
animation, and `even:4` to spread frames across a clip's range.

::: danger Two tools, two rotation conventions
This has caused real confusion, so read it twice.

`render_sheet.py` applies rotations in the **bone's own local space**. It sets
the pose bone's Euler rotation directly.

`pose_frames.py`, the tool that bakes frames out as models, applies them in
**world space**, converting per bone.

They are both right for what they do, and a pose file written for one is not
correct for the other. Local space is simpler for a single model. World space
exists because the automatic rigger gives each bone whatever roll the solve
landed on, so the axis that swings a leg forward differs between rigs. It was X
on one model here and Z on another. Authoring in world space means one pose file
works on every skeleton.

If a pose file produces a sensible cycle in one tool and sprawling nonsense in
the other, this is why.
:::

## Which axis does what

Established by probing a real rig, not guessed:

- **X bends a limb or the spine forward and back.** This is the swing axis and it
  does most of the work in every cycle.
- **Z splays a limb outward** from the body.
- **Y twists** along the bone.

A bone's own axis runs along Y, which is why bending is X.

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

## Deriving cycles automatically

Because bone names differ per model, a hand written pose file does not survive
being pointed at a second one. The game repo's `tool/make_cycles.py` reads the
skeleton's geometry and works out which chains are legs, spine and arms, then
writes walk, attack and hit files for that specific rig.

That is the approach to copy if you are rigging many characters. Derive the
limbs, then apply a cycle expressed in terms of limbs rather than bone names.

## Frames as models, not as a sheet

If your game renders 3D at runtime, consider exporting each pose as its own model
instead of as a sprite sheet.

A sheet of pre rendered frames has to be re cut for every camera direction, and it
cannot survive the camera rotating to an angle you did not bake. Posed models go
through the same rendering path as the resting figure and come out correct at any
angle.

They can share the resting figure's texture, because posing moves vertices and
does not touch UVs. So only the geometry is written per frame.

## Licensing, briefly

All three animation sources are clear for a commercial game:

- mesh2motion's 176 clips are CC0. No conditions at all.
- Its 7 motion capture clips are free for commercial use.
- Mixamo is royalty free with no attribution.

The one shared restriction is that you may not redistribute the animation files
themselves as animation files. Baking a clip onto your own model and shipping that
inside a game is the permitted use. [Full detail](/guide/licensing).
