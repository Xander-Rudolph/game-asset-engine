# What Source Filmmaker knows about faces and rigs

::: tip Status: researched on 2026-09-15, partly built on 2026-09-16
Three of the seven [What to build](#what-to-build) items now exist, and a fourth in part; that list says what each measured and what is still untested. [`scripts/bone_roles.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/bone_roles.py) and the role poses in `poses/roles/` are item 1, [`scripts/check_vendored_licences.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/check_vendored_licences.py) is item 2, and the Source engine line under [researched, not shipped](/guide/licensing#researched-not-shipped) in licensing is item 7. Item 4 became the `share` frame rule in [`scripts/lipsync_cues.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/lipsync_cues.py), which the [talking portraits](/guide/talking-portraits) guide uses. No SFM, Valve or Source SDK file was added. Statements measured on 2026-09-16 while building carry no claim id; each says which script produced it, or sits in a passage that does.

The research itself: in this repository's container, Blender Source Tools exported a DMX through `bpy` 4.5.9, and its Compile QCs call was run against a stand-in `studiomdl.exe` and a wrapper script; the add-on was loaded for that test only and is not in the image. Everything else was read, not run, from Valve's Source SDK 2013 code, the Valve Developer Community wiki, licence texts, community tools and forum threads (marked as such), and Valve's sample files were counted from copies in third-party mirrors. The verified claims behind this page are in [`research/claims/source-filmmaker.json`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/claims/source-filmmaker.json) on GitHub.
:::

Source Filmmaker (SFM) is Valve's movie tool on the Source engine. <!-- SFM-079 --> It runs only on Windows, so it cannot run in this pipeline. <!-- SFM-079, SFM-088 --> Neither Valve's SDK code nor its game assets may be copied into a pipeline whose output is sold ([licences](#licences-copy-learn-from-never-vendor), checked 2026-09-15). <!-- SFM-008, SFM-110 --> It is still worth reading about, because Valve solved two problems this repository has not: a skeleton whose bone names every Source tool keys on, and a face that can lip-sync from a recording plus a typed transcript on models with phoneme presets. <!-- SFM-001, SFM-017, SFM-055 -->

This pipeline's side of the comparison: UniRig's `articulationxl` names bones `bone_0` to `bone_N`, makes no face bones and no blendshapes, and sprites come out at around 128 to 220 px ([rigging](/guide/rigging), [facings](/guide/facings)). So what transfers is design, not files. Phoneme tools and faces on generated meshes are in [lip sync](/reference/lip-sync), and other character bases in [DAZ Genesis](/reference/daz-genesis).

## Source Filmmaker, and where it runs

SFM is Steam app 1840, a Windows-only application on the Alien Swarm branch of Source. <!-- SFM-079, SFM-095 --> Its last update was version 0.9.8.15, announced on 2015-01-12, and the public Steam build, 489744, has not changed since. <!-- SFM-095 --> Valve rates that build Playable on Steam Deck under Proton. Source 2 Filmmaker is a separate program that ships inside the Workshop Tools of Valve's Source 2 games; it was not researched.

It cannot load a model straight from FBX, SMD or DMX. <!-- SFM-079 --> Models are compiled from SMD or DMX meshes plus a `.qc` file into MDL with studiomdl, then placed in a folder SFM searches through `gameinfo.txt`, usually `game/usermod`. <!-- SFM-079 --> A DMX animation, for example from Blender Source Tools, can still be imported onto a model already in the scene. <!-- SFM-079 -->

Scripting is embedded Python 2.7.5, a Windows build compiled with Visual Studio 2010, which the Valve Developer Community (VDC) wiki calls "a work in progress and experimental". <!-- SFM-067 --> The `sfm` object exists only while a script runs from an Animation Set Editor menu. <!-- SFM-067 -->

VDC's command-line page lists `-sfm_loadsession`, `-sfm_autolayoff`, `-sfm_layoffframerange`, `-sfm_layoffshotlist`, `-sfm_layoffshotrange`, `-sfm_startup_script`, `-sfmscripting` and `-nostartwizard`, but describes only `-sfm_loadsession`, `-sfm_autolayoff` and `-nostartwizard`. <!-- SFM-095 --> Valve's 0.9.8.3 release note (2013-12-17) says `-sfm_startup_script` runs a Python script at startup. <!-- SFM-095 --> These switches are the nearest thing to a batch render, and nothing read shows them working without a window.

SFM is a place to learn from, not a pipeline stage.

## How Source rigs a character

### The skeleton and the control rig are separate

The VDC page "Skeletons and Rigging" (last edited 2024-07-12) describes ValveBiped as the standard human rig developed in XSI (Softimage) for Half-Life 2. <!-- SFM-054 --> It is two hierarchies: the skeleton deforms the mesh and is exported into the game, and the control rig only animates that skeleton inside XSI, through constraints, and is never exported. <!-- SFM-054 -->

This pipeline has the first half only. The rigger's skeleton deforms the mesh, and a pose is a table of per-bone Euler rotations ([animation](/guide/animation#posing-bones-yourself)). Nothing animates the skeleton through constraints as a control rig does; since 2026-09-16, `scripts/bone_roles.py` sits between a pose and the skeleton only as a compiler, turning a pose written against roles into those per-bone rotations ([what to build](#what-to-build), item 1).

### Bone names are the join key

studiomdl matches bones across SMD files by name, because bone IDs are internal to each file, and animation on a misnamed bone is not applied at compile time. <!-- SFM-055 -->

`$includemodel` pulls another MDL's sequences into a model at run time. <!-- SFM-056 --> The VDC `$includemodel` page (revision 485589, 2025-07-18) says the included MDL may order its bones differently but must have the same hierarchy and `ikchain` declarations, and that nothing checks this at run time. <!-- SFM-056 --> Valve's `virtualmodel_t::AppendBonemap` in `src/public/studio_virtualmodel.cpp` does a partial check. <!-- SFM-056 --> It matches bones by name, ignoring case, and logs `missmatched parent bones` when a parent differs, but never refuses, so a model with a different hierarchy loads and animates wrongly. <!-- SFM-056 --> Weapons attach the same way, by carrying a bone with the identical name, according to the wiki (not checked). <!-- SFM-057 -->

That is the failure this repository already has: `articulationxl` gave two figures 47 and 28 bones, so a pose file written for one does not survive the other ([bone names are not human readable](/guide/rigging#bone-names-are-not-human-readable)). The repository worked around it with a pose set per rig (`poses/rig24_*.json`, `poses/rig47_*.json`). Since 2026-09-16, [`scripts/bone_roles.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/bone_roles.py) works out which bone plays which role and compiles one role pose, such as `poses/roles/walk.json`, into a transforms file for each rig ([what to build](#what-to-build), item 1).

### ValveBiped, as Valve's rig script reads it

No wiki page listing every ValveBiped bone turned up. The list that survives is in `rig_biped_simple.py`, the rig script Valve ships with SFM at `game/platform/scripts/sfm/animset/`, read from a copy in a [third-party mod repository](https://github.com/OverflowExceptionError/Mini_Portal2/blob/main/platform/scripts/sfm/animset/rig_biped_simple.py). <!-- SFM-053 -->

It finds each bone with `sfmUtils.FindFirstDag` and a list of candidate names. <!-- SFM-053 --> For the pelvis, spine 0 to 2 and, on each side, the thigh, calf, foot, toe, clavicle, upper arm, forearm and hand, the list holds three names in this order: `ValveBiped.Bip01_*`, `Bip01_*`, then `bip_*`. <!-- SFM-053 --> The right thigh is `ValveBiped.Bip01_R_Thigh`, `Bip01_R_Thigh`, then `bip_hip_R`, so the third family uses its own part names. <!-- SFM-053 --> Spine 3, the neck and the head carry extra fallbacks (four, five and four names), and the root role uses only `RootTransform`. <!-- SFM-053 -->

The lesson is not these strings. One script serves three skeleton families because each role has a short list of names, assuming `FindFirstDag` returns the first name that exists; `sfmUtils.py` was not read. <!-- SFM-053 -->

### QC commands that shape a skeleton

The first three rows were checked against the wiki and Valve's code where it exists. The `$lod` row is the wiki's description, not checked.

| Command | What it does |
|---|---|
| `$definebone` | Declares a bone outside any SMD, so studiomdl keeps it with no geometry, which animation-only MDLs need. Placed before any model reference, the lines set bone order, though parents still move ahead of children. `studiomdl -definebones` prints them and exits. <!-- SFM-058 --> |
| `$bonemerge`, `$collapsebones` | Culling depends on the studiomdl build and the wiki's pages disagree: `$bonemerge` "typically" keeps a bone, Garry's Mod's studiomdl ignores it, and bones can still collapse after `$definebone`. `$collapsebones` removes bones not connected to vertices, attachment points or IK rules, or that do not animate. Check the compiled model. <!-- SFM-059 --> |
| `$ikchain` | Always three bones: you name the end bone and studiomdl climbs two parents, or stops with `too close to root`. `ikrule` takes `footstep`, `touch`, `release`, `unlatch` and `attachment`. <!-- SFM-060 --> |
| `$lod` | Can collapse a bone subtree or switch facial animation off. <!-- SFM-065 --> |

The per-model bone limit, `MAXSTUDIOBONES`, is 128 in Source 2013 games such as Half-Life 2 and Team Fortress 2, and in Left 4 Dead and Left 4 Dead 2, and 256 in SFM, Garry's Mod and CS:GO. <!-- SFM-066 --> studiomdl refuses a model whose bone count reaches the limit, which the wiki (revision 499359, 2026-02-24) puts down to an implicit root bone, so a model can hold at most 127 or 255 bones of its own. <!-- SFM-066 -->

### SFM rig scripts

Rig scripts are Python files in `game/platform/scripts/sfm/animset/` that appear under an animation set's right-click Rig menu, and each builds its rig between `sfm.BeginRig(rigName)` and `sfm.EndRig()`. <!-- SFM-093 --> Valve's `rig_biped_simple.py` works in this order, which is one script's pattern rather than a rule: <!-- SFM-068 -->

1. Reset everything to the reference pose in pass-through mode. <!-- SFM-068 -->
2. Create handles constrained to the bones, plus knee and elbow pole handles. <!-- SFM-068 -->
3. Bake the handles with `sfm.GenerateSamples()` and remove those constraints. <!-- SFM-068 -->
4. Reparent the handles into a hierarchy and record their default transforms. <!-- SFM-068 -->
5. Build reverse-foot controls. <!-- SFM-068 -->
6. Constrain the bones back to the handles with point and orient constraints and `sfmUtils.BuildArmLeg`, which adds two-bone IK with a pole-vector target and an orient constraint on the end bone. <!-- SFM-068 -->

The VDC page "SFM/Python script commands" (last edited 2023-07-19) documents the IK constraint only as a two-bone solver: `slaveEnd` must be the grandson of `slaveRoot`. <!-- SFM-069 --> The bend plane comes from a fixed world vector (`poleVector`, default `[0, 1, 0]`) or a DAG node passed as `pvTarget`, which overrides it. <!-- SFM-069 --> It decides the knee's direction only while the target is closer than the two bones' combined length. <!-- SFM-069 -->

The foot roll needs `pvt_heel_L` and `pvt_heel_R` attachments. <!-- SFM-070 --> Without one, the script prints `Could not create foot control rig_footRoll, model is missing heel attachment point: pvt_heel_<side>` and falls back to plain leg IK on that side, and the rest of the rig still builds. <!-- SFM-070 -->

For a custom model, the wiki's "SFM/Making custom rigs" (last edited 2024-01-21, essentially unchanged since 2012) copies `rig_biped_simple.py`, edits its `FindFirstDag` name lists and its rig objects in four places, and names the root, pelvis, upper leg, lower leg, foot, collar, elbow and hand as the most important bones. <!-- SFM-071 -->

The idiom worth keeping: a pose is targets on handles, and a solver turns them into bone rotations. A foot target survives a change of skeleton that a rotation table does not.

Three QC conventions also transfer, as the wiki describes them (not checked): `$attachment`, a named point on a bone; `$weightlist`, per-bone weights so a sequence animates only part of the skeleton; and `$boneflexdriver`, where a bone's translation drives a flex controller. <!-- SFM-049, SFM-063, SFM-064 --> The last would let one animation file carry face state through a renderer that poses bones only, as `render_sheet.py` did until 2026-09-16, when it gained per-pose shape keys and rig properties ([lip sync](/reference/lip-sync#faces-on-generated-meshes)).

### From Blender to Source, and which steps run on Linux

Versions and licences checked 2026-09-15; each licence text is linked in [the licence table](#licences-copy-learn-from-never-vendor).

| Step | Tool, version and licence | On Linux | Headless |
|---|---|---|---|
| Export SMD, VTA, DMX, QC | [Blender Source Tools](https://github.com/Artfunkel/BlenderSourceTools) 3.4.3 (master `3d5fd9b`, 2025-11-01), Blender 4.1 or later. Add-on code GPL-2.0-or-later; `datamodel.py` MIT <!-- SFM-048, SFM-084 --> | Yes, run in this repository's container | Yes, exported through the `bpy` 4.5.9 module |
| DMX without Blender | `datamodel.py`: binary 1 to 5 and 9, keyvalues2 1 to 4, binary_proto 2, standard library only. [srctools](https://github.com/TeamSpen210/srctools) 2.7.0, Python 3.9 or newer, reads and writes DMX, reads only some parts of MDL; MIT (code), except bundled `libsquish/` under its own MIT-style licence <!-- SFM-084, SFM-087 --> | Yes. `datamodel.py` is pure Python; srctools installs from Linux wheels <!-- SFM-084, SFM-087 --> | Yes, both are libraries <!-- SFM-084, SFM-087 --> |
| Compile QC to MDL | `studiomdl.exe`, a Windows command-line tool in the `bin` folder of Source games that include the SDK tools; source survives only in community archives of the 2004 and 2006 SDKs. Steam Subscriber Agreement section 2.C (the tool and what it makes): non-commercial unless a tool's own Subscription Terms say otherwise <!-- SFM-073, SFM-109 --> | Only through Wine or Proton <!-- SFM-072, SFM-075 --> | A command-line tool; not tried under Wine <!-- SFM-073 --> |
| Run studiomdl on Linux | [StudioMDL-helper](https://github.com/LoveRenamon/StudioMDL-helper), MIT (code), and [SourceOps](https://github.com/bonjorno7/SourceOps), GPL-3.0 (code), both call it through Wine <!-- SFM-075 --> | Yes; neither run here <!-- SFM-075 --> | Not tried |
| Decompile MDL | [Crowbar](https://github.com/ZeqMacaw/Crowbar) 0.74, VB.NET Windows Forms, .NET Framework 4.0, x86. CC BY-SA 3.0 Unported (Crowbar's own code and binaries) <!-- SFM-076 --> | No native build <!-- SFM-076 --> | No, a GUI program <!-- SFM-076 --> |
| Import MDL into Blender | [SourceIO](https://github.com/REDxEYE/SourceIO) 5.5.4, Blender 4.2.0 or later, imports Source 1 and 2 formats, exports only VTF. MIT (its own code) <!-- SFM-077 --> | Yes, not run here | An add-on; headless use not tried <!-- SFM-077 --> |
| Load and animate | Source Filmmaker. [SFM Subscription Terms](https://www.sourcefilmmaker.com/sfm_subscription_agreement/): the tool may make commercial or non-commercial movies; Valve's game assets only for personal, non-commercial use <!-- SFM-110 --> | No native build <!-- SFM-079 -->; Playable under Proton on Steam Deck | No page shows a render without a window |

studiomdl reads SMD, DMX, OBJ and VRM (Valve's abandoned multi-LOD format, not VRoid's) for meshes, and VTA and DMX for flexes. <!-- SFM-073, SFM-074 --> FBX input arrived in the CS:GO branch for static meshes only, and no page says SFM's Alien Swarm studiomdl reads it. <!-- SFM-074 --> According to the VDC page, only the third-party fork NekoMDL reads FBX or glTF animation and flexes. <!-- SFM-074 -->

With Engine Path left blank and Binary 5 and Model 18 picked by hand, which is what SFM needs, Blender Source Tools exported a DMX in this repository's container whose header named encoding `binary 5` and format `model 18`. <!-- SFM-072 --> Left alone, the selectors keep the add-on's defaults, Binary 2 and Model 1 (`default='2'` and `default='1'` in `__init__.py`), so a headless export must set both versions explicitly. <!-- SFM-072 --> The field is labelled Engine Path in 3.4.3; the VDC help page still calls it SDK Path. <!-- SFM-072 -->

::: warning The Compile QCs button fails on plain Linux without a wrapper
Blender Source Tools starts `<Engine Path>/studiomdl.exe` with `subprocess.Popen`, with no Wine wrapper and no platform check. <!-- SFM-072 --> On plain Linux that fails with `OSError [Errno 8] Exec format error`, or `Permission denied` if the file is not executable; both were reproduced in the container against a stand-in `studiomdl.exe`. <!-- SFM-072 --> An executable wrapper script saved as `studiomdl.exe` ran in the container; Wine registered through binfmt_misc may also work, but was not tested. <!-- SFM-072 --> The panel appears only when Engine Path is a recognised Source 1 branch and Game Path holds a `gameinfo.txt`, `addoninfo.txt` or `gameinfo.gi`. <!-- SFM-072 -->
:::

## How Valve's facial system is built

### Muscles, not expressions

Computer Graphics World's (CGW) March 2004 article "Larger than Half-Life" (Martin McEachern, Vol. 27, Issue 3) says Valve selected 25 of the 40 "keyframes of expression" in Paul Ekman's facial lexicon, modelled 34 blend shapes per character in XSI and controlled them with its Faceposer tool. <!-- SFM-031 --> The targets were built "below the level of actual expressions", as individual facial muscles in their flexed state. <!-- SFM-031 -->

The VDC page "Flex animation" (last edited 2026-05-31) says "Half-Life 2 characters are based on the FACS, Facial Action Coding System", and that Valve's `standardflex_xsi.qci` and `facerules_xsi.qci` "implement" it. <!-- SFM-090 --> The scripts name flexes after numbered action units such as AU1 (inner brow raiser), AU12 (lip corner puller) and AU26 (jaw drop), and Faceposer's mouth controls (part, puckerer, funneler, stretcher, jaw_drop) are worked out from them. <!-- SFM-090 -->

The VDC sheet "Character Facial Animation Shapekey Set" (created 2005-04-11, revision 429610) numbers 34 slots after the reference frame: 5 for the lids, 4 for the brows, 10 for cheeks and mouth corners, 9 for the lips and 5 for the jaw, with slot 29 blank and slots 10 and 11 sharing a label. <!-- SFM-030 --> Every shape starts from a neutral pose with lips slightly parted and the jaw open 1/16 to 1/4 inch, at "marked" intensity except the "Extreme" 33 and 34. <!-- SFM-030 --> The page never calls this the Half-Life 2 face or a standard; that link is inferred. <!-- SFM-030 -->

### Flex shapes and their limits

A flex shape moves each vertex in a straight line from the base position, scaled by its weight; above 1.0 it pushes past the sculpt and a negative weight inverts it. <!-- SFM-089 --> The non-linearity lives in the layer above, where flex rules, domination rules and corrective shapes combine controller values. <!-- SFM-089 --> That is where CGW's unattributed phrase that the engine can "combine the 34 blend shapes non-linearly" fits. <!-- SFM-031, SFM-089 -->

The public Source 1 headers cap a compiled model at 10,000 flexed vertices per mesh on PC, 1,024 flex shapes and 96 flex controllers. <!-- SFM-034, SFM-041, SFM-089 --> The headers checked were SDK 2013's `studio.h` and the TF2, L4D2, Alien Swarm, Portal 2 and CS:GO branches. <!-- SFM-041, SFM-089 --> SFM's own `vs` module reports 128 controllers and 65,536 flexed vertices, according to a 2018 `help()` dump in a community guide. <!-- SFM-034 --> The wiki's "DMX supports 128 flex controllers" has no source, so plan for 96 in a compiled Source 1 model. <!-- SFM-041, SFM-089 --> The community-written wiki puts TF2's hardware-morph (HWM) faces at 50 shapes, 35 controllers and about 100 corrective shapes; the numbers came with "might vary" in 2012, and Valve never published them. <!-- SFM-041 -->

Shapes are sparse. <!-- SFM-043 --> A VTA file is plain text in which frame 0 lists every triangle corner of the reference SMD and each later frame lists only the corners whose position or normal changed. <!-- SFM-043 --> In Valve's `male_06_expressions.vta`, SDK sample content counted from a [third-party mirror](https://github.com/megakarlach/HL2reUpdate), frame 0 has 14,112 lines and frames 1, 2 and 3 have 396, 464 and 557. <!-- SFM-043 -->

### Controllers and flex rules

Animators work on controllers, not on the raw shapes. <!-- SFM-040 --> Valve's `facerules_xsi.qci` from the SDK sample content, read from the same mirror, declares 44 flex controllers: 16 right and left stereo pairs and 12 mono controls such as `blink`, `jaw_drop`, `smile`, `bite` and `presser`. <!-- SFM-032 --> Its 63 rules write 38 FACS-named flexes (`%AU1R` to `%AU38`), 12 eyelid outputs, 12 local variables and a mouth shader value. <!-- SFM-032 -->

A rule is `%flexname = expression` inside `$model`. <!-- SFM-033 --> The language has `+`, `-`, `*`, `/`, parentheses, unary minus, `min`, `max`, constants, controller names, and `%name` references to another flex or a `localvar` temporary; division returns 0 when the divisor is 0.0001 or less. <!-- SFM-033 --> There is no suppression operator. <!-- SFM-033 --> You multiply by `(1 - other)` yourself: <!-- SFM-033 -->

```
%upper_right_raiser = right_lid_raiser * (1 - right_lid_droop * 0.8) * (1 - right_lid_closer) * (1 - blink)
```

A compiled model stores each rule as a small stack program that `CStudioHdr::RunFlexRules` runs at runtime, with opcodes for constants, fetches, arithmetic, `MIN`, `MAX`, `2WAY`, `NWAY`, `COMBO` and `DOMINATE`. <!-- SFM-034 -->

### Stereo controllers

Left and right come from one sculpt. <!-- SFM-038 --> `flexpair <name> <split> frame <n>` makes `<name>R` and `<name>L` from a single VTA frame, blending with a smoothstep from `-split` to `+split` across X = 0 in the VTA file's coordinates, although the wiki calls it the "Y origin". <!-- SFM-038 --> Faceposer and SFM merge two controllers into one stereo slider only when they are named `right_<x>` and `left_<x>` with right declared first. <!-- SFM-038 -->

In DMX the split is a per-vertex `balance` array, which the VDC "DMX model" page says runs from 0 = 100% right to 1 = 100% left. <!-- SFM-045 --> Blender Source Tools builds it for controllers flagged stereo, across an axis (X by default) or from a vertex group (0 = left, 1 = right). <!-- SFM-048 --> The two sources state opposite conventions, so test one export before trusting either. <!-- SFM-045, SFM-048 -->

### Dominators and corrective shapes

In DMX, a `DmeCombinationDominationRule` lists `dominators` and `suppressed` raw shape names; when the dominators are active the suppressed shapes fade out, for example "open jaw" dominating "puff cheeks". <!-- SFM-040 --> It compiles to the same maths as a `(1 - x)` term. <!-- SFM-033 -->

A shape named by joining other shape names with underscores, such as `a_b`, is a corrective that fades in additively when all the shapes it names are active; `a`, `b` and `c` together apply `a_b`, `a_c`, `b_c` and `a_b_c`. <!-- SFM-040 --> A corrective can repeat a name: `s_s` responds quadratically, and more repeats give cubic or quartic curves. <!-- SFM-040 --> So underscores stay out of names animators should see. <!-- SFM-040 -->

A DMX model holds all of it in one file: shapes as `DmeVertexDeltaData`, controls in a `DmeCombinationOperator`, and expression rules in a `DmeFlexRules` element placed in that operator's `targets[]`, not in the operator itself. <!-- SFM-045 -->

### Visemes are rows of weights

There is no sculpt per phoneme. <!-- SFM-013, SFM-015 --> In a `phonemes.txt` expression class, line 1 is `$keys` and the controller names, line 2 is `$hasweighting`, and each further line is a quoted phoneme name, a quoted code, a setting and weight pair per key, and a quoted description. <!-- SFM-015 --> Valve's Dota 2 `expressions/heroes/phonemes.txt`, counted from a [community mirror](https://github.com/spirit-bear-productions/dota_vpk_updates), has 48 phoneme rows over 31 controllers. <!-- SFM-015 -->

At playback, `C_BaseFlex::ProcessVisemes` looks up each phoneme code in the required `phonemes` class and the optional `phonemes_weak` and `phonemes_strong`; a code missing from `phonemes.vfe` is skipped. <!-- SFM-013 --> Each row's weights are matched to controllers by name and added before the flex rules run, as `g_flexweight[j] += amount * scale * weight`. <!-- SFM-013 -->

`scale` is a box filter: the share of the window from `t` to `t + dt` that the phoneme covers, with `dt` set by `phonemefilter`, default 0.08 s. <!-- SFM-013, SFM-035 --> With crossfade on, `dt` is widened for the current phoneme toward the next one only, never beyond the current phoneme's length. <!-- SFM-035 --> Crossfade depends on `phonemesnap` (default 2): on at LOD0 and LOD1, off at LOD2 and coarser, unless the model was compiled with `$forcephonemecrossfade`. <!-- SFM-035 -->

The wiki page for that command (last edited 2025-07-16) says every model uses "an exaggerated crispness to the lip sync" by default, which looks better when the lips are only a couple of pixels high and unnatural up close. <!-- SFM-036 --> The code shows the crispness is not a snap: it is the plain 0.08 s blend at LOD2 and below, while LOD0 and LOD1 already stretch the blend into the next phoneme. <!-- SFM-036 -->

In the Source SDK 2013 headers, `CDmePhonemeMapping` declares two attributes of its own, `preset` and `weight`. <!-- SFM-119 --> It inherits `name`, which `FindMapping` appears to use as the raw phoneme, and `CDmeAnimationSet` keeps these mappings in its `phonememap` array. <!-- SFM-119 --> The implementation is not public. <!-- SFM-119 -->

### Weak, normal and strong

The emphasis track sets an intensity from 0 to 1, with 0.5 as neutral, and `amount` is twice that. <!-- SFM-013, SFM-014 --> Above 0.60 the normal class crossfades into `phonemes_strong`, full at 1.0; below 0.40 into `phonemes_weak`, full at 0.0; between the two it only scales the normal class. <!-- SFM-014 --> A phoneme with no strong or weak version caps the normal class at 1.2 or 0.8. <!-- SFM-014 --> The wiki says Valve did not use the strong and weak classes in the shipped Half-Life 2, "but in theory, it should work." <!-- SFM-014 -->

### What transfers to this pipeline

These lessons apply to authored mouth frames or a separately made head, since this pipeline's meshes have no face bones or blendshapes. [Lip sync](/reference/lip-sync) covers [faces on generated meshes](/reference/lip-sync#faces-on-generated-meshes) and [mouth-shape sets](/reference/lip-sync#mouth-shape-sets) in depth.

1. **Visemes belong in a table.** Valve's visemes are rows of weights over controllers. <!-- SFM-013, SFM-015 --> Here a row per Rhubarb letter, or per phone from an aligner, can name mouth frames, so a sound costs a line of text, not a render.
2. **Suppression is multiplication.** A `(1 - x)` term or a domination rule keeps shapes from fighting. <!-- SFM-033, SFM-040 --> A closed-lip viseme should zero the open-mouth frames, not average with them.
3. **One sculpt, two sides.** Stereo is a weight across one shape. <!-- SFM-038, SFM-045 --> It matters only once a head has shape keys.
4. **Emphasis is one scalar.** Weak, normal and strong are three variants of each viseme, crossfaded by one authored emphasis value. <!-- SFM-014 --> A loudness envelope could supply that value here; that is a proposal, not something Valve did.
5. **Close-ups want the crossfade.** Valve keeps the plain 0.08 s blend for low-detail LODs, which the wiki says suits lips a couple of pixels high, and crossfades into the next phoneme up close. <!-- SFM-035, SFM-036 --> This repository puts no faces on sprite sheets ([lip sync](/reference/lip-sync#faces-only-read-on-a-portrait)), and a portrait of 340 px or more ([facings](/guide/facings#sizes)) is the close-up case, so the crossfade is the rule to test.
6. **Timing travels with the audio.** Source stores it inside the WAV. <!-- SFM-009 --> This repository writes its music as MP3 ([music](/guide/music#making-it-loop)), and the lip sync note's example voice line is an Ogg file; neither format carries RIFF chunks, so the equivalent here is a text sidecar such as the [timeline file](/reference/lip-sync#the-timeline-file) that note describes and `scripts/lipsync_cues.py` writes. A community mirror of Vampire: The Masquerade, Bloodlines is reported to hold a similar block, marked VERSION 1.2, as standalone `.lip` files; this was not checked. <!-- SFM-026 -->

## How SFM extracts phonemes

### Two extractors, both Windows DLLs

Faceposer's automatic extraction has exactly two back ends, both Windows DLLs in `bin/phonemeextractors`. <!-- SFM-005, SFM-047 --> Their source is in `src/utils/phonemeextractor` of Valve's Source SDK 2013 repository. <!-- SFM-005, SFM-024 --> Faceposer's own source is not in the repository. <!-- SFM-024 -->

- **"MS SAPI 5.1"** uses Microsoft's in-process recogniser with a grammar built from the sentence's words, so it needs a transcript. <!-- SFM-001, SFM-047 --> The wiki says it is broken on Windows Vista and later. <!-- SFM-047 -->
- **"IMS (LipSinc)"** wraps the LIPSinc TalkBack 1.1 library through `ims_helper.dll` and needs a `lipsinc_data` folder. <!-- SFM-006, SFM-047 --> It has a textless mode: with an empty sentence or a single `[Textless]` word, it passes an empty string to `TalkBackGetAnalysis()`. <!-- SFM-006 -->

Both include `<windows.h>`, and the project files link `sapi.lib` from a `sapi51` directory that is not in the repository. <!-- SFM-005 -->

### The SAPI extractor needs a transcript

Checked against `phonemeextractor.cpp` on master, commit `b8cfb12`. <!-- SFM-091 --> It splits the typed text on spaces, drops anything inside `[ ]`, and builds a SAPI grammar with one top-level rule, `Root`, in which each word is a state linked to the next in transcript order. <!-- SFM-001 --> It activates that grammar under the comment "Activate the CFG ( rather than using dictation )" and never loads dictation. <!-- SFM-001 -->

This is looser than strict forced alignment. <!-- SFM-001 --> `MAX_WORD_SKIP` is 1, and with more than one word, empty arcs make every word after the first optional. <!-- SFM-001, SFM-091 --> Skipped words are put back with no phonemes and spread evenly across the gaps. <!-- SFM-001, SFM-003, SFM-091 --> Without text it stops: `SAPI_ExtractPhonemes` prints `Input sentence is empty!`, `ExtractPhonemes` prints `Error:  no rule / text specified`, and text with no usable words fails with `contained no usable words`. <!-- SFM-001 -->

Inside a word nothing is aligned. <!-- SFM-003 --> The only timing taken from SAPI is each recognised word's start and end. <!-- SFM-003 --> The word's span is then split in proportion to fixed per-phoneme weights: 0.6 for `c` and `k`, 0.7 for `y`, 0.8 for most stops, fricatives, `l` and `n`, 1.0 for most vowels and approximants, and 1.2 for `er`, `er2`, `ow`, `uw`, `ao`, `aw` and `oy`, with 1.0 for an unknown phoneme. <!-- SFM-003 --> A `FIXME` above the code says phonemes are spread evenly; the code contradicts it. <!-- SFM-003, SFM-091 -->

Language is not hard-coded, but the output is English-centric. <!-- SFM-004 --> The phone converter is created for the UI language or a `-languageid` switch, and falls back to English, 0x409, only if that fails. <!-- SFM-004 --> Source's phoneme table knows only SAPI's American English symbols, and anything else logs `Unrecognized phoneme` and becomes silence. <!-- SFM-004 -->

### The phoneme set and the VDAT chunk

The table in `src/public/phonemeconverter.cpp` has 54 entries: 47 lowercase ARPAbet-style phonemes, 6 aliases (`h`, `k`, `ay`, `ng`, `aw`, `oy`) that reuse standard codes, and `<sil>`. <!-- SFM-011 --> Each code is a Unicode code point, the matching IPA letter for a real phoneme (593 = U+0251 for `aa`, 952 = U+03B8 for `th`) and 95, `_`, for silence. <!-- SFM-011 -->

Timing lives inside the WAV, in a RIFF chunk with id `VDAT`, a 4-byte little-endian length that does not count the 8 id and length bytes, and a whitespace-separated text block. <!-- SFM-009 --> Its shape, as `CSentence::SaveToBuffer` writes it: <!-- SFM-010 -->

```
VERSION 1.0
PLAINTEXT { <sentence text> }
WORDS { WORD <word> <start> <end> { <code> <name> <start> <end> 1 ... } ... }
EMPHASIS { <time> <value> ... }
OPTIONS { voice_duck <0|1> [checksum <n>] }
```

The trailing `1` on each phoneme is a fixed volume, the reader parses only version 1.0, and an old `CLOSECAPTION` section is still skipped. <!-- SFM-010 --> The engine's runtime form keeps only phoneme codes and times, the emphasis samples and `voice_duck`, so visemes are driven by timing plus emphasis. <!-- SFM-012 --> The SDK repository also carries VDAT reading and writing code in `soundcombiner.cpp`, which comes from Faceposer's code, is built by no project and will not compile as shipped. <!-- SFM-024 --> Like the rest of the SDK, it is under the [SOURCE 1 SDK LICENSE](https://github.com/ValveSoftware/source-sdk-2013/blob/master/LICENSE) (checked 2026-09-15). <!-- SFM-008, SFM-024 -->

### From phoneme to face in SFM

SFM's Extract Phonemes makes lip sync only on a model with phoneme presets for its face controls; the VDC page (last edited 2012-09-17) says it "will only work on the HWM TF2 classes, and HL2 FACS-compliant models". <!-- SFM-017 --> HWM TF2 models ship with presets, HL2 FACS-compliant models get them from "Create Phoneme Presets based on HL2 FACS controls" in the Element Viewer, and any other model needs a preset table built by hand on top of facial controls it already has. <!-- SFM-017 -->

Faceposer's wiki page says the extractor has a hard time with long sentences (not checked). <!-- SFM-019 --> Tutorials advise typing the transcript exactly as spoken without punctuation, cutting long lines into short clips between words, and expecting to hand-fix (community reports, not checked). <!-- SFM-020 --> Several SFM forum regulars call the extractor unreliable and animate mouths by hand. <!-- SFM-021 -->

### What any of it is worth on Linux

| Piece | Runs on Linux | May this repository reuse it |
|---|---|---|
| SAPI extractor | No: `windows.h`, COM, ATL, SAPI 5.1 <!-- SFM-001, SFM-005 --> | No. SOURCE 1 SDK LICENSE (code); read it for the method <!-- SFM-008 --> |
| IMS extractor and TalkBack | No: Windows DLLs and libraries <!-- SFM-005, SFM-006, SFM-107 --> | No. TalkBack is LIPSinc copyright, all rights reserved (code, binaries, manual); the wrapper source is under the SOURCE 1 SDK LICENSE <!-- SFM-007, SFM-024, SFM-107 --> |
| `sentence.cpp`, `c_baseflex.cpp`, the phoneme table | Would need porting | No. SOURCE 1 SDK LICENSE (code); the design can be reimplemented <!-- SFM-008 --> |
| VDAT chunk reader (`riff.h`) and DMX loader | Prebuilt `linux64/tier2.a` (contains `riff.o`) and `linux64/dmxloader.a` exist, with no source <!-- SFM-024, SFM-119 --> | No. SOURCE 1 SDK LICENSE, Valve copyright; only in a free Source 1 mod <!-- SFM-008, SFM-119 --> |
| ValveResourceFormat's `.vfe` reader | Yes, .NET; reads compiled `.vfe` version 0 and dumps text, cannot write `.vfe` <!-- SFM-016 --> | Run it. MIT (contributors' code, not `Tests/Files`; no rights over Valve's `.vfe` content; keep the notice) <!-- SFM-016 --> |

Licences checked 2026-09-15; the texts are linked in [the licence table](#licences-copy-learn-from-never-vendor).

The open replacements for the extractor, Rhubarb Lip Sync and forced aligners such as Montreal Forced Aligner, are compared, measured and licensed in [lip sync](/reference/lip-sync#speech-to-mouth-shapes).

## Learning material worth the time

The VDC wiki is the canonical documentation. It now sits behind a bot check that blocks scripted fetches, so read it in a browser or through Wayback captures. The first five entries under [Sources worth reading](#sources-worth-reading) are a reading order; stop when the question is answered.

Skip the rest unless you will run SFM on Windows. Valve's official tutorial playlist, lip-sync and rigging videos included, teaches the GUI. <!-- SFM-096 --> The Steam scripting guides are Python 2.7 notes and `help()` dumps. <!-- SFM-099 --> The 2026 Faceposer forks, Faceposer++ and Scenemaker, are Windows tools. <!-- SFM-098 --> No Valve talk or paper on the facial system was found. <!-- SFM-101 -->

## Licences: copy, learn from, never vendor

Checked 2026-09-15 against the linked texts. "Copy" means the file may enter this repository's tree with its notice, and "vendor" means keeping such a copy here. "Run" means using it as a separate program, and "learn" means reading it and writing your own. A verdict marked (practice) is this repository's choice, not a licence limit.

| Item | Licence or terms, and what they cover | Verdict |
|---|---|---|
| [Source SDK 2013](https://github.com/ValveSoftware/source-sdk-2013/blob/master/LICENSE): extractors, `sentence.cpp`, `phonemeconverter.cpp`, `c_baseflex.cpp`, `studio.h`, DMX headers and prebuilt libraries | SOURCE 1 SDK LICENSE, for the whole SDK including code: use, copy and modify only to develop a modified Valve game on Source 1, distributed only if free and within the Steam Subscriber Agreement's terms of use for Valve games; redistribute only free of charge with `LICENSE`, `thirdpartylegalnotices.txt`, Valve's copyright notice and disclaimers <!-- SFM-008, SFM-105, SFM-119 --> | Learn. Never vendor <!-- SFM-008 --> |
| [LIPSinc TalkBack 1.1](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/utils/phonemeextractor/talkback.h) in that repository: `talkback.h`, four `talkback_*.lib`, `talkback.doc` | Proprietary (code, binaries, documentation). `talkback.h`: "Copyright 1998-2002 LIPSinc. All rights reserved." `talkback.doc`: "Copyright 1998-2001 by LIPSinc", no reproduction without LIPSinc's written permission. No licence to them in the repository, and no entry in `thirdpartylegalnotices.txt` <!-- SFM-007, SFM-107 --> | Never use, vendor or ship <!-- SFM-007, SFM-107 --> |
| [Microsoft Speech SDK 5.1](https://www.microsoft.com/en-us/download/details.aspx?id=10121) | Microsoft Speech SDK 5.1 EULA, `license51.htm` in the SDK download (SDK and redistributable code): the SDK only to design, develop and test programs for Windows Platforms; redistributables only inside your SAPI application, only with Windows Platforms, no onward redistribution <!-- SFM-108 --> | Never vendor <!-- SFM-108 --> |
| `studiomdl.exe`, shipped with SFM and with Source games on Steam | [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/) (SSA) section 2.C, Valve Developer Tools (the tool and content made with it): "solely on a non-commercial basis", except where a tool's own Subscription Terms say otherwise; whether SFM's Subscription Terms reach the studiomdl it ships is unsettled; commercial requests go to `sourceengine@valvesoftware.com` <!-- SFM-109 --> | Run for tests only. Do not ship compiled output until this is settled <!-- SFM-109 --> |
| Valve game assets in SFM: characters, props, particles, textures and sounds <!-- SFM-088 --> | [SFM Subscription Terms](https://www.sourcefilmmaker.com/sfm_subscription_agreement/) with the SSA (content): personal, non-commercial use in connection with the games <!-- SFM-110 --> | Learn |
| Source SDK sample content and game expression files: `facerules_xsi.qci`, `standardflex_xsi.qci`, the `male_06` sources, Dota 2's `phonemes.txt` | Valve content. No licence to reuse it outside Source was found, and it was read from third-party mirrors ([HL2reUpdate](https://github.com/megakarlach/HL2reUpdate), [dota_vpk_updates](https://github.com/spirit-bear-productions/dota_vpk_updates)), so its terms were not pinned down <!-- SFM-015, SFM-032, SFM-043 --> | Learn. Never vendor |
| [VDC wiki](https://developer.valvesoftware.com/wiki/Valve_Developer_Community:Terms_of_Use) text | Valve Developer Community Terms of Use (posted content): licensed only "in connection with the Source engine and Source SDK (and games, mods and other products based thereon)"; not Creative Commons <!-- SFM-083 --> | Learn, paraphrase, link |
| [ValveResourceFormat](https://github.com/ValveResourceFormat/ValveResourceFormat) | MIT (its contributors' code, not `Tests/Files`, nothing over Valve's formats or content; keep the notice). Not clean-room: its `.vfe` work used Valve's leaked 2007 source as reference <!-- SFM-016 --> | Run |
| [Blender Source Tools](https://github.com/Artfunkel/BlenderSourceTools) add-on | GPL-2.0-or-later (add-on code), from per-file headers; no repository `LICENSE` file <!-- SFM-048, SFM-084 --> | Run as an add-on (practice) <!-- SFM-118 --> |
| Its [`datamodel.py`](https://github.com/Artfunkel/BlenderSourceTools/blob/master/io_scene_valvesource/datamodel.py) | MIT (that file's code), "Copyright (c) 2014 Tom Edwards" <!-- SFM-084 --> | Copy, header intact <!-- SFM-084 --> |
| [srctools](https://github.com/TeamSpen210/srctools) 2.7.0 | MIT (code), except bundled `libsquish/` under its own MIT-style licence; keep both notices <!-- SFM-087 --> | Install or copy <!-- SFM-087 --> |
| [SourceIO](https://github.com/REDxEYE/SourceIO) | MIT (REDxEYE's code); ships a prebuilt `pylib` from a repository with no licence file, statically linking a VTFLib fork (LGPL-2.1), and a Windows-only `Serpent.dll` with no stated licence <!-- SFM-077 --> | Run; do not bundle |
| [Crowbar](https://github.com/ZeqMacaw/Crowbar) | CC BY-SA 3.0 Unported (Crowbar's own code and binaries), credit to ZeqMacaw; covers Crowbar, not the models put through it. <!-- SFM-076 --> Its repository also bundles third-party Steamworks and compression binaries under their own terms | Run. Redistribute only under CC BY-SA 3.0 with credit, never relicensed as Apache-2.0; not vendored (practice) <!-- SFM-076, SFM-115 --> |
| [StudioMDL-helper](https://github.com/LoveRenamon/StudioMDL-helper) | MIT (code) <!-- SFM-075 --> | Run |
| [SourceOps](https://github.com/bonjorno7/SourceOps) | GPL-3.0 (code) <!-- SFM-075 --> | Run |
| SFM community scripts: [advancedfx/afx-sfm-scripts](https://github.com/advancedfx/afx-sfm-scripts), [Ganonmaster/sfm-scripts](https://github.com/Ganonmaster/sfm-scripts) and [KiwifruitDev/sfm-bridge](https://github.com/KiwifruitDev/sfm-bridge); [kumfc/sfm-tools](https://github.com/kumfc/sfm-tools), [AlanChatham/SFMKinectFacialAnimation](https://github.com/AlanChatham/SFMKinectFacialAnimation), [AlanChatham/SFMBodyTracker](https://github.com/AlanChatham/SFMBodyTracker) and [ClintonM0/sfmphys](https://github.com/ClintonM0/sfmphys) | The first three: MIT (code). The other four: no licence file, so all rights reserved, and [GitHub's Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) allow viewing and forking only. The two AlanChatham repositories also hold Microsoft Kinect SDK sample code marked "All rights reserved" <!-- SFM-121 --> | Learn |

The SDK's README says it "is licensed to users on a non-commercial basis", and the licence has no grant for commercial use or for any engine other than a Source 1 Valve game mod. <!-- SFM-008, SFM-106 -->

::: danger Reading the SDK is fine. Pasting it is not
Copying `phonemeextractor.cpp`, `sentence.cpp` or `c_baseflex.cpp` into this non-Source pipeline, or into assets or games made with it and sold commercially, is not licensed. <!-- SFM-008 --> Using them as reference is fine, but no code may be copied. <!-- SFM-008 --> Treat the phoneme table, `phonemes.txt` rows and the face rules the same way: design your own and write down how.
:::

On TalkBack, Valve's Yahn Bernier wrote on the [hlcoders list on 2007-06-08](https://www.mail-archive.com/hlcoders@list.valvesoftware.com/msg19786.html) that Valve's IMS (formerly LipSinc) extractor needed a separate licence, so Valve could not offer it in the SDK. <!-- SFM-007 --> `talkback.h` and `talkback.doc` have been in the repository since its first commit on 2013-06-26, and the commits API dates the four `.lib` files to the "Add Team Fortress 2 SDK" commit of 2025-02-18. <!-- SFM-007 --> The public record shows no licence for these files to be reused and cannot show whether Valve later got permission, so treat them as not licensed to you. <!-- SFM-007 -->

**SFM's own output.** Checked 2026-09-15. The [SFM Subscription Terms](https://www.sourcefilmmaker.com/sfm_subscription_agreement/), part of the SSA, allow the tool to be used to create animated movies for commercial or non-commercial purposes, but Valve's game assets only for personal, non-commercial use. <!-- SFM-110 --> Valve's [FAQ](https://www.sourcefilmmaker.com/faq/) says you can make money with SFM only if your movies and images contain none of Valve's assets. <!-- SFM-088, SFM-110 --> An SFM movie that has credits must include "Created using the Source® Filmmaker. © Valve 201_."; one without credits need not add them. <!-- SFM-111 --> Other Valve developer tools fall under section 2.C of the [SSA](https://store.steampowered.com/subscriber_agreement/) (revision of 2026-09-10), set out in the studiomdl row above. <!-- SFM-109 --> Valve's [Video Policy](https://store.steampowered.com/video_policy) gives no right to use Valve assets inside a game. <!-- SFM-112 -->

**Mixing licences.** Blender Source Tools' GPL-2.0-or-later add-on code could legally be vendored, because such code combines with Apache-2.0 code under GPLv3 ([FSF licence list](https://www.gnu.org/licenses/license-list.html#apache2)), provided each file keeps its notices and the combination is distributed under GPLv3. <!-- SFM-118 --> This repository keeps GPL code out of its tree by its own policy ([licensing](/guide/licensing#this-repository-s-own-licence)), so of Blender Source Tools only `datamodel.py` (MIT) is a candidate to copy. <!-- SFM-084, SFM-118 --> Crowbar code cannot be relicensed under Apache-2.0, because [no non-CC licence has been designated compatible](https://creativecommons.org/share-your-work/licensing-considerations/compatible-licenses/) with CC BY-SA 3.0; it could still sit in the tree unmodified under its own licence and credit, so keeping it out is a choice. <!-- SFM-115 -->

## What not to do

**Do not transcribe Valve's tables.** The phoneme table is SDK code under the SOURCE 1 SDK LICENSE. <!-- SFM-008, SFM-011 --> The SDK's sample face rules (`facerules_xsi.qci`) were read from a third-party mirror, and no licence letting them be used outside Source was found ([uncertainty](#honest-uncertainty)). <!-- SFM-032 --> [Lip sync](/reference/lip-sync#the-mapping-to-adopt) already derives this repository's mouth table from Rhubarb's README; extend that one rather than transcribing Valve's.

**Do not put SFM, studiomdl or Wine in the container.** SFM runs only on Windows, its scripting is Python 2.7.5, and its last update was in January 2015. <!-- SFM-067, SFM-079, SFM-095 --> studiomdl is a Windows executable. <!-- SFM-073 --> Nothing this pipeline ships needs an MDL.

**Do not ship a model compiled with studiomdl in something you sell.** Under SSA section 2.C, content made with Valve's developer tools is non-commercial by default. <!-- SFM-109 -->

**Do not ship TalkBack or SAPI, even as a convenience download.** One has no licence to you and the other is tied to Windows by its EULA. <!-- SFM-007, SFM-108 -->

**Do not paste wiki text into these docs.** Paraphrase, and link.

**Do not trust a README's feature table, version line or licence file.** SourceIO's table says it exports no VTF, and it does; srctools' README says Python 3.8, and the package needs 3.9. <!-- SFM-077, SFM-087 --> An MIT licence on ValveResourceFormat is not evidence of a clean-room reader. <!-- SFM-016 --> Read the code and the per-file headers.

**Do not sell a render that contains Valve's assets.** The SFM FAQ and Subscription Terms limit Valve assets to non-commercial use, and the Video Policy lets videos with Valve content earn only through the YouTube Partner Program and similar programmes, not be sold or licensed. <!-- SFM-088, SFM-110, SFM-112 -->

**Do not copy the within-word timing as if it were measured.** Valve's SAPI extractor spreads phonemes across a word by fixed weights. <!-- SFM-003 --> An aligner that places phonemes acoustically is the upgrade.

## What to build

Ranked. None of it duplicated an existing script when proposed. The notes under items 1, 2, 4 and 7 say what was built on 2026-09-16, what it measured and what is still untested; items 3, 5 and 6 have not been started.

1. **`scripts/name_bones.py`.** Derive roles from skeleton geometry with the rules already in [rigging](/guide/rigging#bone-names-are-not-human-readable), rename `bone_0` to `bone_N` to a role vocabulary of this repository's own, write the map beside the FBX, and key `poses/*.json` on roles. Source makes names the join key for every tool, and this repository keeps a pose set per rig for want of one. <!-- SFM-055 --> Done when one `walk.json` renders on both the 28-bone and the 47-bone figure.

   **Built on 2026-09-16 as [`scripts/bone_roles.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/bone_roles.py), and the bar was met.** It leaves bone names alone. `map` reads the skeleton's geometry, plus skin weights for the one call geometry cannot make, which bone is the head, and writes a roles file; `compile` turns a pose written against roles, in the character's own axes, into the ordinary per-rig transforms file `render_sheet.py` reads; `probe` reports which way each part moved. The role poses are `poses/roles/walk.json`, `attack.json`, `hit.json` and `idle.json`, and `poses/_bones.md` gives the role table. Measured on five articulationxl rigs of 24, 28, 30, 30 and 47 bones: all four role poses compiled for all five, and all 20 sheets rendered with no `--check` findings, so one walk file renders on both the 28-bone and the 47-bone figure. On the walk's first contact frame the leading toe went forward 0.434 to 0.470 rig units on the five rigs, and the derived roles agreed with all 29 hand-mapped bones on the 28-bone rig. The old per-rig walk files bend the knee the wrong way on their passing frames, swinging the foot forward by 41.9 to 45.6 degrees; the role walk swings it back by 42.0 degrees on all five. The role files carry `_note` strings, so `render_sheet.py` refuses them if they are passed in without compiling. Known limits: the feet are not kept on the ground, since contact frames leave them 0.026 to 0.100 rig units above the rest floor; a `translate` moves only bones not connected to their parent, such as the pelvis and the neck, and `compile` refuses one on a connected bone; and the role axes assume arms hanging at rest, since on a T-pose Mixamo rig the walk's hand swing was 0.051 of the figure's height, against 0.153 on a 47-bone articulationxl rig. Still untested: the IK of item 3; rigs that do not face an armature axis; a hip bone; a head bone carrying between 0.175 and 0.611 of the skin weight of the bone below it, where the head rule's 0.25 threshold sits; translating hands, feet and toes; rendering any non-articulationxl skeleton (a Mixamo and an MPFB2 rig were mapped but not rendered); and using the compiled poses in a game engine.
2. **`scripts/check_vendored_licences.py`.** Fail when a file outside `docs/` contains `Copyright Valve Corporation`, `LIPSinc`, `SOURCE 1 SDK LICENSE`, a GPL licence block or `Creative Commons Attribution-ShareAlike`, because each trap in the licence table gets in through a pasted snippet. Wiki text pasted into `docs/` and transcribed tables carry no marker, so those stay a review rule.

   **Built.** [`scripts/check_vendored_licences.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/check_vendored_licences.py) checks the files git tracks outside `docs/` and `research/` for markers of Valve, LIPSinc, the Source 1 SDK licence, GPL licence text and notices, CC BY-SA, Daz and Genesis, and exits 1 on any hit its allowlist does not cover; `--markers` lists them with the reason for each. Run on 2026-09-16 with `--untracked`, so that this change's new files were included, it passed with 35 allowlisted mentions. As its help says, it cannot tell whether code was copied: a pasted function with its header stripped matches nothing.
3. **Experiment: `render_sheet.py --poses ik:FILE`.** Give a pose as foot and hand targets with knee and elbow pole targets, solved by two-bone IK as `rig_biped_simple.py` builds its limbs. <!-- SFM-068 --> Measure foot contact in bpy as each foot bone's world-space height above the ground; `sheet_check.py` does not measure contact, so this is a new check. Success is one target file giving grounded walks on both the 28-bone and 47-bone rigs, where `--poses transforms:FILE` needs a file per rig.
4. **Experiment: Valve's blend rules in the cue-to-frame comparison.** [Lip sync](/reference/lip-sync#the-timeline-file) proposes sampling each frame at its midpoint, with a closure rule as a second candidate. Add two rules adapted from Valve's box filter, which weights each phoneme by its share of a look-ahead window: show the cue with the largest share of a fixed 0.08 s window, Valve's low-detail setting, or of that window widened into the next cue, its close-up setting. <!-- SFM-035, SFM-036 --> Picking a single cue adapts the filter to discrete mouth frames; Valve blends. <!-- SFM-013 --> Compare all four on one 340 px portrait at 12 fps, because the midpoint rule can drop short cues and Valve widens its window only for faces seen up close, which a portrait is. <!-- SFM-035, SFM-036 -->

   **The fixed window was built on 2026-09-16; the widened one was not.** `scripts/lipsync_cues.py --fps N --rule share` gives each frame the cue with the largest overlap of the window from the frame's start to max(1/N, 0.08 s) after it, and an exact tie to the later cue, as `midpoint` does. [`research/experiments/rhubarb/reproduce.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/experiments/rhubarb/reproduce.py) measured it against `midpoint` on one LibriSpeech line recognised on one thread, once with its transcript (87 cues, the shortest 0.06 s) and once with `-r phonetic` (102 cues, the shortest 0.05 s). At 12 fps `share` gave the same 171 frames as `midpoint` and dropped the same 4 cues, where `closure` dropped 7. From 8 to 12.5 fps it matched `midpoint` in every frame except 2 phonetic frames at 9 fps. It differed in 3 frames at 6 fps (10 phonetic), and in 8, 41 and 61 frames at 15, 24 and 30 fps (8, 51 and 72 phonetic). An earlier version, which gave an exact tie to the earlier cue, differed from `midpoint` in 8 frames at 10 fps (12 phonetic). Still untested: the widened close-up window, the comparison on a 340 px portrait, and whether any of the rules looks right on a face.
5. **Side experiment, outside the container, only if someone needs SFM.** Rename a UniRig FBX's bones, export DMX at Binary 5 and Model 18, and write a QC with `$definebone` for every bone. <!-- SFM-058, SFM-072 --> Compile it under Wine and open it in SFM on Windows, because only the export step has run and this would show whether 47 bones survive culling. Under SSA section 2.C the compiled MDL is non-commercial by default, so treat it as a test, not an asset. <!-- SFM-109 -->
6. **Experiment: loudness as emphasis on one 340 px portrait.** Map a line's RMS envelope through Valve's 0.40 and 0.60 thresholds. <!-- SFM-014 --> Compare blending each open mouth toward the closed one by the envelope against weak and strong variants of C and D only, recording the extra images made and whether a viewer can tell them apart. One scalar from the audio could vary Rhubarb's nine mouths without tripling the art. The VDC wiki says Half-Life 2 shipped without Valve's weak and strong classes, so that game is no evidence the idea works. <!-- SFM-014 -->
7. **One line in [licensing](/guide/licensing#the-licences-of-the-tools-themselves).** Say that no Source engine tool is in the image and link this note's licence table, so readers find these traps without a second copy to keep dated.

   **Done.** The line, "Source engine tools. None is in the image.", sits under [researched, not shipped](/guide/licensing#researched-not-shipped) rather than the section named here, and links this note's licence table.

## Honest uncertainty

- **SSA section 2.D got two verdicts.** One check rejected the summary that commercial use of Valve game content runs "only through" Steam Workshop or a Steam Subscription Marketplace; the other accepted it with that wording corrected. <!-- SFM-113 --> Both read the text the same way: Fan Art using Valve game content is non-commercial except where 2.D or separate Subscription Terms say otherwise, the two Steam features are examples ("features such as"), and nothing in 2.D lets Valve content into a game sold outside them ([agreement](https://store.steampowered.com/subscriber_agreement/), revision of 2026-09-10). <!-- SFM-113 -->
- **Whether studiomdl may compile assets for a commercial non-Valve game.** SSA section 2.C sets a non-commercial default for developer tools, and whether SFM's own terms reach the studiomdl it ships was not settled. <!-- SFM-109 --> 2.C gives an address for commercial requests, not terms, and what Valve grants through it is unknown. <!-- SFM-109 -->
- **studiomdl forks.** The VDC StudioMDL page names NekoMDL, and mentions StudioMDL++ as a workaround for the broken 64-bit TF2-branch build; neither was checked for a Linux build or a licence. <!-- SFM-074 -->
- **SFM's own limits.** Its 128 flex controllers come only from a community `help()` dump, where public headers say 96, and its 256-bone limit rests on the wiki alone; Valve publishes no SFM header. <!-- SFM-034, SFM-041, SFM-066, SFM-089 -->
- **`sfmUtils.py` was not read.** What `BuildArmLeg` does, and whether `FindFirstDag` returns the first name that exists, rest on the VDC command page and a third-party copy of a related function. <!-- SFM-068, SFM-093 -->
- **DMX without Blender.** Whether srctools or `datamodel.py` writes a model DMX with flex controls that studiomdl accepts is untested.
- **Terms for Valve's sample files and presets.** The terms of the SDK sample content (`facerules_xsi.qci`, the `male_06` sources) were not pinned down, since it was read from a third-party mirror. <!-- SFM-032, SFM-043 --> Whether SFM's phoneme presets count as Valve game content was not checked either, so treat them as if they do. <!-- SFM-114 -->
- **Whether Valve's short controller names** such as `jaw_drop` are protectable is a legal judgement no source addresses. A vocabulary of your own avoids the question.
- **FACS names.** Whether naming shapes after FACS Action Units carries any constraint in a commercial tool was not checked.
- **SFM's Extract Phonemes dialog was never observed**, so whether SFM demands a transcript is unconfirmed. Steam community threads say per-model `.pre` preset files sit beside the model, for example in `models/player/hwm/`.
- **Language.** The SFM wiki says lines can be recorded in other languages; that was not checked, and the code's table knows only American English symbols. <!-- SFM-004, SFM-018 -->
- **SMD line endings.** The VDC SMD page asks for CR or CRLF line endings rather than bare LF; this was not checked against studiomdl. <!-- SFM-078 -->
- **Wiki freshness.** Several VDC pages were read through Wayback captures, and some SFM pages date from 2012. <!-- SFM-017, SFM-071 -->

## Sources worth reading

The first five are the reading order.

- [VDC: Flex animation](https://developer.valvesoftware.com/wiki/Flex_animation): the face system on one page, with limits, stereo, rules and correctives.
- [`c_baseflex.cpp`](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/game/client/c_baseflex.cpp): runtime visemes with the filter, crossfade and emphasis constants; read it, do not copy it. <!-- SFM-008 -->
- [VDC: Phoneme Tool/data format](https://developer.valvesoftware.com/wiki/Phoneme_Tool/data_format) and [`sentence.cpp`](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/sentence.cpp): the VDAT block from both ends.
- [CGW: Larger than Half-Life](https://www.cgw.com/Publications/CGW/2004/Volume-27-Issue-3-March-2004-/Larger-than-Half-Life.aspx): Valve's FACS design intent in plain language, 2004.
- [VDC: SFM/Python script commands](https://developer.valvesoftware.com/wiki/SFM/Python_script_commands): the rig and two-bone IK commands, to read beside `rig_biped_simple.py`.
- [VDC: DMX model](https://developer.valvesoftware.com/wiki/DMX_model): where shapes, balance, controls and rules live in a DMX.
- [VDC: $forcephonemecrossfade](https://developer.valvesoftware.com/wiki/$forcephonemecrossfade): the crispness note, to read beside `c_baseflex.cpp`.
- [VDC: SFM/Lip-sync animation and Extract Phonemes](https://developer.valvesoftware.com/wiki/SFM/Lip-sync_animation_and_Extract_Phonemes): which models work and why.
- [VDC: Skeletons and Rigging](https://developer.valvesoftware.com/wiki/Skeletons_and_Rigging): skeleton versus control rig.
- [VDC: SFM/Making custom rigs](https://developer.valvesoftware.com/wiki/SFM/Making_custom_rigs): adapting the stock rig script to another skeleton.
- [VDC: SFM/Command-line startup options](https://developer.valvesoftware.com/wiki/SFM/Command-line_startup_options): the load and layoff switches.
- [`phonemeextractor.cpp`](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/utils/phonemeextractor/phonemeextractor.cpp): transcript-constrained recognition and weighted phoneme spacing.
- [SOURCE 1 SDK LICENSE](https://github.com/ValveSoftware/source-sdk-2013/blob/master/LICENSE): why none of the SDK may be copied. <!-- SFM-008 -->
- [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/): sections 2.C and 2.D, the non-commercial default for developer tools and fan art. <!-- SFM-109, SFM-113 -->
- [SFM Subscription Terms](https://www.sourcefilmmaker.com/sfm_subscription_agreement/) and [FAQ](https://www.sourcefilmmaker.com/faq/): what SFM output may be sold. <!-- SFM-088, SFM-110 -->
- [Blender Source Tools](https://github.com/Artfunkel/BlenderSourceTools): SMD, VTA and DMX export, and the MIT `datamodel.py`. <!-- SFM-048, SFM-084 -->
- [erysdren: Half-Life 2 choreo system research](https://erysdren.me/blog/2026-03-06/): a community summary of the whole choreography pipeline.
