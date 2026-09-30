# Video to 3D motion

::: tip Status: researched on 2026-09-30
Nothing was installed, downloaded or run for this note, and nothing it proposes is built. It was read: the licence files of each model and wrapper at a named commit, their READMEs and install files, the arXiv abstracts, the SMPL licence pages, the MediaPipe model card, and the pricing and terms pages of four hosted services. UniRig's and mesh2motion's node source were read inside the running `comfyui-packaged` container, and the Blender filters under [Clean-up](#clean-up) were checked for presence in the image's `bpy`, not run on a clip. The verified claims behind this page are in [research/claims/video-mocap.json](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/claims/video-mocap.json) on GitHub.
:::

How this repo could turn a video of a person, such as one Wan 2.2 makes in `complete_workflow.json`, into an animation clip on a rigged mesh, for a game that will be sold. Two nearby pieces do not do it. DWPose, the pose preprocessor in comfyui_controlnet_aux, gives 2D keypoints only, and its code carries CMU's non-commercial licence, as [licensing](/guide/licensing) records. Wan 2.2 image to video makes a video of a character moving, but extracts no motion from it. Rigging is covered in [rigging](/guide/rigging) and clips in [animation](/guide/animation); the SMPL body model's licence was first read for [DAZ Genesis](/reference/daz-genesis).

## The short answer

- **No open video-to-motion model read here is clear for a commercial game as released.** WHAM, TRAM and 4D-Humans are MIT code, but each needs the SMPL body model, which is licensed for non-commercial research, education and artistic use unless licensed separately. WHAM also detects people with Ultralytics' AGPL-3.0 YOLO, and TRAM tracks them with a CC BY-NC-SA 4.0 tracker. GVHMR's and SMPLer-X's own code is non-commercial, and MotionBERT's documented input comes from AlphaPose, which is non-commercial research only (checked 2026-09-30). <!-- VMC-001 VMC-002 VMC-003 VMC-004 VMC-005 VMC-006 VMC-007 VMC-008 VMC-052 -->
- **The open route worth a trial is SAM 3D Body with Meta's MHR body model.** SAM 3D Body's code and checkpoints are under Meta's SAM License, which has no non-commercial clause but can be amended by Meta, and its checkpoints are gated; MHR is Apache-2.0, assets included. It fits one image at a time, with no temporal model and no world trajectory, so a clip would be per-frame fits smoothed afterwards. Not run. <!-- VMC-009 VMC-010 VMC-032 VMC-051 -->
- **Hosted services are the quicker route, on a paid plan whose terms you have read.** DeepMotion's pricing page says its free accounts are "for personal, non-commercial use". Rokoko's terms say it does not claim ownership of what you create; its free plan gives 30 seconds of video capture a month, and BVH export starts at $10 a month billed annually. Plask's and Move.ai's terms could not be read (checked 2026-09-30). <!-- VMC-020 VMC-021 VMC-022 VMC-024 -->
- **The larger gap is in this repo, not in capture.** `rig_apply_animation.json` runs UniRig's Apply Animation node, which only accepts `mixamorig:` bone names and copies curves by name with no retargeting. This repo rigs with `articulationxl`, whose bones are `bone_0` to `bone_N`, so by reading the code that graph would refuse any clip on these rigs. Nothing here yet moves an outside clip onto a `bone_N` rig. <!-- VMC-035 VMC-036 -->

## The chain

A video becomes a game clip in five steps, and each one brings its own licence:

1. **Find and track the person** in each frame: a detector such as YOLO or ViTDet, and a tracker.
2. **Fit a body** to each frame: 2D keypoints lifted to 3D, or a body model's parameters.
3. **Make it motion**: a temporal model for smoothness, and camera motion for the path through the world.
4. **Move it onto the game rig**: a retarget from the body model's skeleton to the rig's bones.
5. **Clean it**: jitter, foot sliding, and a loop that joins.

Steps 1 to 3 are what the models and services below do. Step 4 is where this repo's rigs stand apart ([below](#getting-a-clip-onto-this-repo-s-rigs)).

## Open models

Read at the commits in the register, on 2026-09-30. "Stack" is what each install file targets; this image is Python 3.11, PyTorch 2.6.0 and CUDA 12.4. Nothing was installed.

| Model | Code | Body model | Other parts it loads | Output | Stack |
|---|---|---|---|---|---|
| [WHAM](https://github.com/yohanshin/WHAM) | MIT <!-- VMC-001 --> | SMPL <!-- VMC-001 --> | YOLOv8 through Ultralytics (AGPL-3.0), ViTPose (Apache-2.0), DPVO (MIT) <!-- VMC-008 VMC-015 --> | World-grounded motion, with contact-aware trajectory refinement against foot sliding <!-- VMC-030 --> | Python 3.9, PyTorch 1.11, CUDA 11.3, mmcv 1.3.9 <!-- VMC-031 --> |
| [GVHMR](https://github.com/zju3dv/GVHMR) | Educational, research and non-profit only <!-- VMC-002 --> | SMPL and SMPL-X <!-- VMC-002 --> | YOLOv8 through Ultralytics, ViTPose-Pytorch (GPL-3.0), optional DPVO <!-- VMC-002 VMC-008 VMC-015 --> | World-grounded motion, in gravity-and-view coordinates <!-- VMC-030 --> | Python 3.10, PyTorch 2.3.0, CUDA 12.1 <!-- VMC-031 --> |
| [TRAM](https://github.com/yufu-wang/tram) | MIT <!-- VMC-003 --> | SMPL <!-- VMC-003 --> | DEVA tracker (CC BY-NC-SA 4.0), DROID-SLAM (BSD-3-Clause), Detectron2, ZoeDepth <!-- VMC-003 VMC-015 --> | World-grounded trajectory and motion <!-- VMC-030 --> | Python 3.10, PyTorch 2.4.0, CUDA 11.8 <!-- VMC-031 --> |
| [4D-Humans](https://github.com/shubham-goel/4D-Humans) (HMR 2.0) | MIT <!-- VMC-004 --> | SMPL <!-- VMC-004 --> | ViTDet through Detectron2, PHALP tracker (MIT, "please follow the license for SMPL") <!-- VMC-004 --> | Tracked 3D pose and shape per person; world path not read <!-- VMC-004 --> | Python 3.10, CUDA 11.8 <!-- VMC-031 --> |
| [SMPLer-X](https://github.com/MotrixLab/SMPLer-X) | S-Lab License 1.0, non-commercial <!-- VMC-005 --> | SMPL-X <!-- VMC-005 --> | mmdet 2.26.0 <!-- VMC-005 --> | SMPL-X parameters <!-- VMC-005 --> | Python 3.8, PyTorch 1.12 <!-- VMC-031 --> |
| [MotionBERT](https://github.com/Walter0807/MotionBERT) | Apache-2.0 <!-- VMC-006 --> | SMPL, for its mesh output only <!-- VMC-006 --> | 2D keypoints from AlphaPose (non-commercial research only), as its guide documents <!-- VMC-006 --> | 17 Human3.6M joints in 3D, or an SMPL mesh <!-- VMC-006 --> | Python 3.7 <!-- VMC-031 --> |
| [SAM 3D Body](https://github.com/facebookresearch/sam-3d-body) | SAM License, code and checkpoints <!-- VMC-009 --> | [MHR](https://github.com/facebookresearch/MHR), Apache-2.0 <!-- VMC-010 --> | ViTDet through Detectron2 (weights' licence unverifiable), optional MoGe-2 (MIT) <!-- VMC-014 --> | One image at a time, MHR parameters <!-- VMC-032 --> | Python 3.11 <!-- VMC-031 --> |
| [MediaPipe](https://github.com/google-ai-edge/mediapipe) pose landmarker | Apache-2.0 <!-- VMC-013 --> | None | None | 33 keypoints for one person, z from synthetic data; out of scope for "metric accurate depth" <!-- VMC-013 --> | Not read |

MotionBERT's AlphaPose is the source its guide names, not a hard dependency, and another detector giving the same 17 joints could feed it; that was not tried. <!-- VMC-006 --> MHR ships a converter between MHR and SMPL or SMPL-X. <!-- VMC-010 --> SMPLer-X's README points to a successor, SMPLest-X, whose licence was not read. <!-- VMC-005 -->

**GVHMR's licence moved on 2026-09-15.** That day the repository adopted a "Project Registration License", which allowed any company to use it in any project, commercial or not, free once registered, and reverted to the non-commercial text within the day. The reading above is the reverted text. <!-- VMC-002 -->

### ComfyUI packs

Both are by the author of ComfyUI-UniRig and ComfyUI-CameraPack, which this image already carries. Neither is installed here.

- [ComfyUI-MotionCapture](https://github.com/PozzettiAndrea/ComfyUI-MotionCapture) is GPL-3.0 and runs GVHMR on a video. It "vendors GVHMR code which has its own license", so GVHMR's non-commercial terms come with it, and it ships arrays named for SMPL, such as `smpl_faces.npy`. <!-- VMC-011 --> Its nodes turn SMPL motion into BVH, retarget SMPL onto a character with `mixamorig:` bones by a fixed map, and retarget BVH onto an FBX or VRM character in Blender with Copy Rotation constraints, all by bone name. <!-- VMC-033 -->
- [ComfyUI-SAM3DBody](https://github.com/PozzettiAndrea/ComfyUI-SAM3DBody) wraps SAM 3D Body and has a "Save Skeleton" node that writes JSON, BVH or FBX, one image per run. <!-- VMC-034 --> Its own licence is unsettled: the root LICENSE file is GPL-3.0, while its README and `docs/licenses/LICENSE` say the wrapper is MIT and the vendored library is under the SAM License. <!-- VMC-012 -->

## Hosted services

Read on 2026-09-30. Prices are as the pricing pages showed them that day.

| Service | Terms read | Your output | Export | Price |
|---|---|---|---|---|
| [DeepMotion Animate 3D](https://www.deepmotion.com/pricing-animate3d) | Pricing FAQ only; the terms page renders in a browser and was not read <!-- VMC-020 --> | "Freemium accounts are available for personal, non-commercial use"; "only your plan type affects your licensing" <!-- VMC-020 --> | FBX, BVH, MP4, and GLB for custom characters <!-- VMC-020 --> | Not readable without a browser <!-- VMC-020 --> |
| [Rokoko Vision](https://www.rokoko.com/pricing) | [Terms of Use](https://www.rokoko.com/terms-of-use-update), effective 16 July 2026 <!-- VMC-021 --> | "we do not claim ownership over any User Content", which includes animations you create; no clause restricting commercial use by plan was found <!-- VMC-021 --> | FBX on Starter; BVH, custom characters, smoothing and loop segments from Basic <!-- VMC-022 --> | Starter $0, 30 s of video a month; Basic $10 a month billed annually, 600 s; Plus $20, 3,000 s; Pro $50, 15,000 s <!-- VMC-022 --> |
| [Plask](https://plask.ai/pricing) | Not found <!-- VMC-024 --> | Unverifiable <!-- VMC-024 --> | FBX, GLB, BVH on every tier <!-- VMC-023 --> | Freemium, 15 s a day; Standard $18 a month billed yearly, 10 min a month; Pro $50, 1 hour <!-- VMC-023 --> |
| [Move.ai](https://move.ai/) | An index of EULAs that renders only in a browser; not read <!-- VMC-024 --> | Unverifiable <!-- VMC-024 --> | Not read | Not read |

Rokoko's terms also forbid using assets obtained under them to train machine learning or AI models without its written consent. <!-- VMC-021 --> Whether any of these services exports a skeleton with `mixamorig:` bone names was not checked.

## Getting a clip onto this repo's rigs

**UniRig's Apply Animation node matches by name and does not retarget.** At the commit this image pins, it refuses a model whose bones lack the `mixamorig:` prefix with "Model does not have mixamorig: bone names!", and refuses such a clip the same way. It then copies the clip's curves onto bones with identical names, scaling only location keys, with no allowance for a different rest pose. Its `smpl` type raises "SMPL animation support is not yet implemented". Read in the container, not run. <!-- VMC-035 -->

**This repo's rigs do not have those names.** `mesh_rig_unirig.json` rigs with `articulationxl`, which names bones `bone_0` to `bone_N`, so `rig_apply_animation.json` would refuse its output for any clip, Mixamo's included. No clip was applied to check it. [Animation](/guide/animation) says UniRig gives "a Mixamo compatible skeleton, so anything from Mixamo retargets onto it", which holds only for the `mixamo` template that [rigging](/guide/rigging#use-articulationxl-not-mixamo) advises against. <!-- VMC-036 -->

So a clip from any source, dropped into `input/animation_templates/mixamo/`, reaches only a rig made with the `mixamo` template, and only when the clip's own bones carry `mixamorig:` names. <!-- VMC-035 VMC-036 -->

**mesh2motion does not close the gap.** Version 1.2.0 imports a self-contained FBX, with its mesh, skeleton and clips in one file, and plays it. Its retarget page maps mesh2motion's own library onto an uploaded skinned model. It documents no way to put an outside clip onto a UniRig rig. <!-- VMC-037 -->

What would close it is a retarget keyed on bone roles rather than names. `scripts/bone_roles.py map` already works out which `bone_N` is the pelvis, spine, chest, thighs, shins and arms on an `articulationxl` rig ([animation](/guide/animation#deriving-cycles-automatically)). A BVH skeleton names the same joints, so a Blender script could pair them by role and drive each rig bone with a Copy Rotation constraint, then bake. That is what ComfyUI-MotionCapture's BVH node does for named rigs. <!-- VMC-033 VMC-050 -->

## Clean-up

Checked on 2026-09-30 in `comfyui-packaged`, by asking the image's Blender 4.5.9 (`bpy`) whether each operator exists, not by running it on a clip:

- **Jitter:** `graph.butterworth_smooth`, `graph.gaussian_smooth` and `graph.smooth` exist, and `graph.euler_filter` for rotation flips.
- **Too many keys:** `graph.decimate` and `graph.clean`.
- **Loops:** the `CYCLES` F-curve modifier, and `nla.bake` to bake a result down.
- **Formats and retargeting:** BVH import and export, and the `IK` and `COPY_ROTATION` constraints.

Foot sliding is the hard one. Of what was read, only WHAM treats it, with contact-aware trajectory refinement. <!-- VMC-030 --> In Blender it would mean pinning each foot with IK on the frames where it touches the ground, which nothing here does; [animation](/guide/animation#not-tested-yet) already records that on its walk's contact frames the lowest foot or toe bone end sits 0.026 to 0.100 units above where it rests. Rokoko's Basic plan offers a smoothing filter and loop segments of its own. <!-- VMC-022 -->

## Licences

Read on 2026-09-30, and kept apart by layer.

- **Weights and body models.** SMPL and SMPL-X are for non-commercial research, education and artistic projects; commercial use goes through Max Planck Innovation or Meshcapade, and the pages were unchanged since the repo last read them. <!-- VMC-007 --> MHR and its assets are Apache-2.0. <!-- VMC-010 --> SAM 3D Body's checkpoints are under the SAM License and gated. <!-- VMC-009 --> The BlazePose GHUM 3D card says Apache-2.0. <!-- VMC-013 --> WHAM's, HMR 2.0's and MotionBERT's checkpoints state no licence of their own. <!-- VMC-001 VMC-004 VMC-006 --> The licence of the ViTDet detector weights SAM 3D Body loads is unverifiable. <!-- VMC-014 -->
- **Code.** As in the [table](#open-models): MIT for WHAM, TRAM and 4D-Humans; non-commercial for GVHMR and SMPLer-X; Apache-2.0 for MotionBERT, MHR and MediaPipe; the SAM License for SAM 3D Body. <!-- VMC-001 VMC-002 VMC-003 VMC-004 VMC-005 VMC-006 VMC-009 VMC-010 VMC-013 --> Among the parts they load, Ultralytics is AGPL-3.0, the DEVA tracker CC BY-NC-SA 4.0, AlphaPose non-commercial research only and ViTPose-Pytorch GPL-3.0. <!-- VMC-003 VMC-006 VMC-008 VMC-015 -->
- **Content and assets.** ComfyUI-MotionCapture ships arrays named for SMPL; whether they count as SMPL's Software under its licence was not settled. <!-- VMC-011 -->
- **Generated output.** None of the open licences read says anything about motion made with the model. Whether motion fitted with SMPL still falls under the SMPL licence once it is moved onto a rig that is not SMPL was not settled here.
- **Hosted-service terms.** DeepMotion's free tier is non-commercial by its own FAQ; Rokoko disclaims ownership of your recordings; Plask's and Move.ai's terms were not read. <!-- VMC-020 VMC-021 VMC-024 -->

## What not to do

- **Do not make assets for sale with GVHMR or ComfyUI-MotionCapture.** GVHMR's code is non-commercial, and the pack carries it. <!-- VMC-002 VMC-011 -->
- **Do not read an MIT code licence as clearance** when the model needs SMPL. WHAM, TRAM and 4D-Humans all do. <!-- VMC-001 VMC-003 VMC-004 VMC-007 -->
- **Do not use DeepMotion output made on its free tier** in a game. <!-- VMC-020 -->
- **Do not expect `rig_apply_animation.json` to animate an `articulationxl` rig**, from any clip. <!-- VMC-035 VMC-036 -->
- **Do not feed Rokoko-made assets into training** a model without Rokoko's written consent. <!-- VMC-021 -->

## What to build

None of these is built.

1. **A BVH retarget onto `articulationxl` rigs**, keyed on the roles `scripts/bone_roles.py map` writes: pair joints by role, drive each rig bone with Copy Rotation, bake, and check the result with `scripts/render_sheet.py --check`. It is the step every capture route needs, open or hosted. <!-- VMC-050 -->
2. **A Rokoko Vision trial on its free tier**: 30 seconds of one Wan 2.2 video, to see what skeleton, bone names and quality come back before paying for BVH. <!-- VMC-022 -->
3. **A SAM 3D Body trial**: one Wan 2.2 video, fitted frame by frame, with jitter measured before and after `graph.butterworth_smooth`. Needs the gated checkpoints approved first. <!-- VMC-009 VMC-032 VMC-051 -->
4. **A clean-up script** for any clip: Butterworth smoothing, the Euler filter, and a trimmed loop joined with the `CYCLES` modifier, all in the image's Blender.
5. **Correct the two pages that promise more than the code does**: [animation](/guide/animation) on Mixamo clips and the `_comment` in `rig_apply_animation.json`, after a run confirms the refusal. <!-- VMC-036 -->

## Honest uncertainty

- **Nothing was run.** Whether a Wan 2.2 video, which is synthetic and may bend anatomy between frames, gives usable motion through any of these routes is not known.
- **GVHMR's licence changed twice in one day**, fifteen days before this reading, and may change again. <!-- VMC-002 -->
- **The SAM License can be amended by Meta**, effective immediately, and the checkpoints need manual approval. <!-- VMC-009 -->
- **The ViTDet weights' licence** is unverifiable, and SAM 3D Body loads them by default. <!-- VMC-014 -->
- **DeepMotion's binding terms, and Plask's and Move.ai's terms**, were not read, so which paid plans carry which rights is not established here. <!-- VMC-020 VMC-024 -->
- **ComfyUI-SAM3DBody's wrapper licence** is unsettled between GPL-3.0 and MIT. <!-- VMC-012 -->
- **Whether any hosted service exports `mixamorig:` bone names**, which is what `rig_apply_animation.json` would need on a `mixamo` rig, was not checked.
- **What AGPL asks of a tool run offline to make assets**, rather than shipped or served, is not settled here; it touches CLAUDE.md's open AGPL question. <!-- VMC-008 -->

## Sources worth reading

- [WHAM](https://github.com/yohanshin/WHAM), [GVHMR](https://github.com/zju3dv/GVHMR) and its [LICENSE history](https://github.com/zju3dv/GVHMR/commits/main/LICENSE), [TRAM](https://github.com/yufu-wang/tram), [4D-Humans](https://github.com/shubham-goel/4D-Humans), [SMPLer-X](https://github.com/MotrixLab/SMPLer-X), [MotionBERT](https://github.com/Walter0807/MotionBERT)
- [SAM 3D Body](https://github.com/facebookresearch/sam-3d-body) and its [LICENSE](https://github.com/facebookresearch/sam-3d-body/blob/main/LICENSE); [MHR](https://github.com/facebookresearch/MHR)
- [SMPL](https://smpl.is.tue.mpg.de/modellicense.html) and [SMPL-X](https://smpl-x.is.tue.mpg.de/modellicense.html) model licences
- [BlazePose GHUM 3D model card](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf)
- [ComfyUI-MotionCapture](https://github.com/PozzettiAndrea/ComfyUI-MotionCapture) and [ComfyUI-SAM3DBody](https://github.com/PozzettiAndrea/ComfyUI-SAM3DBody)
- [DeepMotion pricing](https://www.deepmotion.com/pricing-animate3d), [Rokoko pricing](https://www.rokoko.com/pricing) and [Rokoko Terms of Use](https://www.rokoko.com/terms-of-use-update), [Plask pricing](https://plask.ai/pricing)
- The arXiv abstracts: [WHAM](https://arxiv.org/abs/2312.07531), [GVHMR](https://arxiv.org/abs/2409.06662), [TRAM](https://arxiv.org/abs/2403.17346)
