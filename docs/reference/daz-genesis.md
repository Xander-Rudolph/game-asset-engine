# DAZ Genesis as a character base

::: tip Status: researched on 2026-09-15
Research only; nothing on this page is built, installed or shipped. Everything here was read, not run: Daz's licence, product and file-list pages, the DSON specification, the Diffeomorphic importer's source and wiki, forum threads, a third-party copy of a few `.dsf` files, the licence files of the alternatives and the free Quaternius and KayKit downloads. No importer was tried in the container. This repository's `scripts/render_sheet.py` and `scripts/cleanup.py` were read on 2026-09-16.
:::

Characters in this pipeline start as a Qwen-Image painting. That painting becomes a TRELLIS or Hunyuan3D mesh, and UniRig rigs it with bones named `bone_0` to `bone_N` and no face at all ([rigging](/guide/rigging#bone-names-are-not-human-readable)). Daz 3D's Genesis figures are the opposite: a fixed, posable human with named bones, joint correctives and a face rig. Could Genesis be the human base for the sprite pipeline? Can it run on a Linux box with no desktop session? And what may a game sold worldwide ship?

Source Filmmaker has [its own note](/reference/source-filmmaker). Phonemes, visemes and facial rigs for generated meshes are covered in [lip sync](/reference/lip-sync).

## The answer in brief

- **Renders ship; 3D data needs a paid licence.** Under the standard Daz EULA you may sell 2D renders and animation frames, sprites included, unless a product page says otherwise. Shipping the mesh, morphs or textures needs an Interactive License per product, where its creator offers one, or a separate signed agreement. Under the Interactive License the content must stay out of native formats and be protected against extraction ([EULA](https://www.daz3d.com/eula), [Interactive License page](https://www.daz3d.com/interactive-license-info), checked 2026-09-15).
- **Daz content is a poor input to the AI stages.** The EULA excludes Content, "in whole or in part", from any AI system that can auto-generate material "derivative, imitative, or otherwise plagiaristic of the Content". A Genesis mesh fed to a model is the plain case; whether a render counts is not said.
- **Genesis has a face rig.** Genesis 8, 8.1 and 9 all carry the same 17 viseme dials, as pose controllers rather than blendshapes, and 8.1 and 9 add a FACS layer.
- **Daz Studio has no Linux build.** On Linux it runs only under unsupported Wine. In the container the practical route is the Diffeomorphic importer in Blender, which has no explicit handling for background mode.
- **The look does not match painted concept art**, and a diffusion restyle is the step the AI clause puts in doubt.
- **MakeHuman through MPFB2 is the cleaner base.** Its bundled assets and face packs are CC0 1.0 (content) and its code is GPL-3.0-or-later ([MPFB2 licence](https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md), checked 2026-09-15). Its visemes are shape keys.

## Anatomy of Genesis 8, 8.1 and 9

Everything in this section was read from Daz's specification and file lists, from Diffeomorphic's data tables or from forum posts. The contents of a few `.dsf` files were read through a third-party GitHub copy of Daz content, which is not linked here and may differ from Daz's current files. None of it was measured here.

### The files are JSON

Daz content is stored as DSON. Specification 0.6.1.0 says DSON is JSON and its binary form "is merely a zlib compressed (aka 'zipped') version of the text format"; in practice Daz Studio writes gzip. `.dsf` support files hold shared definitions, and `.duf` user files are top-level scenes and presets that no other file can reference. A morph is a set of sparse per-vertex deltas, and joint correctives follow bone rotations through formulas in the same files. HD detail sits in a separate, undocumented binary `.dhdm`, so a base-resolution reader sees only base-mesh deltas.

### Side by side

| | Genesis 8 | Genesis 8.1 | Genesis 9 |
|---|---|---|---|
| Base figures | Female and Male, two different meshes | Female 8.1 and Male 8.1, inside Genesis 8 Starter Essentials | One figure, Feminine and Masculine as shapes |
| Body mesh, base resolution | Female 16,556 vertices, 16,368 quads; Male 16,384 vertices, 16,196 faces | Not checked | 25,182 vertices, 25,156 quads |
| Separate fitted figures | Eyelashes | Eyelashes, Tear, and a Face Controls widget | Eyes, Mouth, Eyelashes, Tear (base anatomy); since 2024-11 also six Toon sub-figures, including a Toon Mouth |
| Bones | 170 | Not checked | 143 |
| Viseme dials | 17 `eCTRLv*`, bone-driven | 17 `facs_ctrl_v*`, plus the 17 legacy `eCTRLv*` | 17 `facs_ctrl_v*` |
| Other face controls | 114 (Female) or 115 (Male) `eCTRL` head pose controls | FACS: `facs_bs_`, `facs_cbs_`, `facs_jnt_`, `facs_ctrl_` | FACS: `facs_bs_`, `facs_cbs_`, `facs_ctrl_`, no `facs_jnt_` |

The mesh counts are community figures, from Daz Studio scene info, Blender imports and Diffeomorphic's figure fingerprint. Genesis 8's 170 bones come from Diffeomorphic's rig table and forum counts, and Genesis 9's 143 from Daz's own `genesis_9_rig.json`.

### Skeletons

Genesis 8 names are l/r-prefixed camelCase (`lShldrBend`, `lThighTwist`, `abdomenLower`), except ten toe segments with an underscore suffix (`lSmallToe1_2`) and eight face bones with a capital (`Nose`, `Chin`). Of its bones, 77 sit under `head`, including `lowerJaw`, four tongue bones and 16 eyelid bones. Those are DSON node names, and 27 of the 170 bones carry a node ID that differs from the name (`lThigh`, `chest_2`, and typos such as `lLipCorver`). Every bone also has a spaced English label, so check which identifier an exporter writes before matching on names.

Genesis 9 names are lowercase with an `l_` or `r_` prefix and compound words run together: `l_thigh`, `spine1` to `spine4`, `l_upperarm`, `l_forearmtwist1`, `neck1`. Its face rig is simpler, at 42 bones, with five tongue bones.

Either skeleton keeps stable, readable names, unlike UniRig's `bone_N` output, whose count changes per figure ([rigging](/guide/rigging#bone-names-are-not-human-readable)). Retargeting this repo's Mixamo or mesh2motion clips onto Genesis was not tried.

### Faces

All three generations carry the same 17 viseme names, AA, EE, EH, ER, F, IH, IY, K, L, M, OW, S, SH, T, TH, UW and W, under Pose Controls > Head > Visemes. They are pose controllers, not ready-made blendshapes. The Genesis 8 viseme files contain no morph deltas and only move face bones, and on 8.1 and 9 the visemes blend FACS shapes with jaw joints. Getting them into an engine as blendshapes therefore means baking the bone-driven part.

**Genesis 8.1** adds four FACS families: `facs_bs_` shape units, most of them HD `_div2` morphs with a `.dhdm`; `facs_cbs_` correctives; bone-driven `facs_jnt_` units; and `facs_ctrl_` controllers. Its eight expression controllers, Afraid to Surprised, sit in a separate `FACSExpressions` folder.

**Genesis 9** has no `facs_jnt_` family. `facs_bs_JawOpen` is a vertex morph whose formulas also rotate `lowerjaw`, and eye look is bone-driven. Its base FACS folder has no `.dhdm`; the HD variants sit in `FACS Details`. The separate Mouth figure carries 10 viseme controllers of its own. Its FACS names use Apple's ARKit vocabulary, but the set is not a one-to-one ARKit-52 set: Daz splits many shapes into left and right or upper and lower parts, with a controller on top.

The free Genesis 9 base includes the viseme controllers, but the 40-dial Genesis 9 Expressions set is a separate [US$21.98 product](https://www.daz3d.com/genesis-9-expressions) (checked 2026-09-15). The free product's page never mentions visemes or FACS, so read its file list. For emotions on a dialogue portrait with no purchase, Genesis 8.1 is the free option: its eight `FACSExpressions` controllers ship in Genesis 8 Starter Essentials.

[Lip sync](/reference/lip-sync#the-mapping-to-adopt) maps Rhubarb's nine letters onto the 17 Genesis dials; that column has not been tried on a figure. The third-party [Emphasized Visemes for Genesis 9](https://www.daz3d.com/emphasized-visemes-for-genesis-9) by dobit (US$19.98, SKU 88578, checked 2026-09-15) has 15 dials: AA, CH, DD, E, FF, I, K, O, PP, RR, S, TH, U, W and SIL. Those are close to the Oculus fifteen in [lip sync's table](/reference/lip-sync#mouth-shape-sets), with W where Oculus has nn. Diffeomorphic is reported to map Moho `.dat` lip sync onto Genesis visemes, with a Rhubarb table among others (read from its wiki, not verified). Its tables ship in a GPL-2.0-or-later add-on, so copy none of them into this repository.

## Getting Genesis into Blender on Linux

### Daz Studio runs on Windows and macOS

Daz Studio is free, proprietary software for Windows and macOS only; Linux users can run it only under unsupported Wine. The current general release is 6.25 (build 6.25.2026.14722, 2026-06-04), and the final Daz Studio 4 release, 4.24.0.4, installs alongside it. The official bridges and Diffeomorphic's `.dbz` export script run inside Daz Studio, so they are Windows and macOS only too.

Forum reports from 2025 have Daz Studio 4.x running under Lutris-managed Wine, with DIM installing content in the same prefix, and Iray GPU rendering working for some users on nvidia-libs with wine-staging 10.9 or 10.14. Others on the same thread never got the GPU detected. Daz Studio 6 did not run under Lutris and Wine as of 2025-06. Whether any of these setups runs without a display was not checked.

The Daz to Blender Bridge is a Daz Studio plugin that writes an FBX plus a `.dtu` JSON file. Plain FBX export keeps no ERC links, so joint correctives do not fire when the figure is posed (forum reports).

### Diffeomorphic reads the content files directly

The Diffeomorphic DAZ Importer (`import_daz`) is GPL-2.0-or-later for its code only, and it imports native `.duf` and `.dsf` files. Version 5.2.0 (2026-08-10) declares `blender_version_min` 4.2.0 and was tested on Blender 3.6 and 5.2. The container's `bpy` 4.5.9 is inside that range; the importer was not run on it. Master's `bl_info` already carries the unreleased 5.3.0, so install from the `version_5_2_0` tag.

The rest of this subsection was read from the importer's source at master commit `3437e54`, its wiki and its blog. None of it was run.

**It needs no Daz Studio to read files.** It opens `.duf` and `.dsf` itself, gzip first and plain text second. Content roots are a plain list that a script sets with `import_daz.set_global_setting('contentDirs', [...])`. The bulk imports behind `useVisemes` and `useFacs` read per-figure tables that hard-code Daz's own `data/DAZ 3D/...` folders, so the content must keep Daz's layout. DIM packages are reported as `IM<SKU>-<part>_Name.zip` files with a `Manifest.dsx` and a `Content` folder, whose `data`, `People` and `Runtime` subfolders merge into one content directory (Daz's work-in-progress docs and a forum thread, not verified).

::: warning A wrong content path fails silently
A content directory that does not exist raises no `DazError`. The importer drops it, and an unresolvable reference makes `get_absolute_paths()` return an empty list with no message at the default verbosity. Check that the directories exist and that the figure's path resolves before importing anything.
:::

**It is scriptable.** From 4.4.0 (2025-04-06) the calls are `bpy.ops.daz.easy_import_daz(directory=..., files=[{"name": "x.duf"}])` and `bpy.ops.daz.import_visemes()`, after which `rig["eCTRLvAA"] = 1.0` sets a viseme. `set_silent_mode(True)` sends errors to the terminal instead of a pop-up, `import_daz.get_error_message()` returns them, and an extension installed into Blender's default repository imports as `bl_ext.user_default.import_daz`.

**Headless use is unhandled.** No file references `bpy.app.background`, and all nine `invoke_props_dialog` calls sit on operator `invoke()` paths. Neither the code nor the wiki mentions `blender -b` or `--background`. Whether calling the operators from Python avoids those dialogs was not checked.

**Morphs arrive as drivers, approximately.** Morphs import as rig property sliders whose drivers move shape keys, bones or both. TCB splines are approximated with `smoothstep()`, and morphs that change the rest pose are ignored by default.

**The best path wants a file from Daz Studio.** Default fitting reads a `.dbz` written by a script inside Daz Studio. Since 2021-03-24 a `.duf` can be imported without one, using Mesh Fitting "Morphed (Characters)", but the wiki warns "Not all shapekeys are found" and "Shapekeys are not transferred to clothes".

### What runs where

| Step | Where | Status |
|---|---|---|
| Get the free Starter Essentials | A Daz account; DazCentral, Daz Connect, DIM or Manual Install | DIM under Wine on Linux reported working (community); browser Manual Install not checked |
| Read `.duf` and `.dsf` | Any Python: JSON behind gzip | Read from specification and source |
| Import figure, visemes, FACS | Diffeomorphic in `bpy` | Background mode unhandled, not run |
| Import with `.dbz` fitting | Daz Studio on Windows or macOS, or under Wine on Linux | Needs Daz Studio; not run |
| Bridges, FBX morph export | Daz Studio plugin | Needs Daz Studio; not run |
| EEVEE render and sheet | `scripts/render_sheet.py` in the container | Exists: bones only, no shape keys, no `.blend` |

### Rendering

Diffeomorphic converts Daz's Iray materials three ways, and its own labels admit the loss: "BSDF (Cycles Only)" is "For Cycles, best IRAY quality", "Extended Principled" is "For Eevee and Cycles, limited IRAY quality", and "FBX Compatible" has "very limited IRAY quality". FilaToon shaders get a dedicated toon node tree. `scripts/render_sheet.py` renders with `BLENDER_EEVEE_NEXT`, a transparent film, a sun light that rides the camera and, by default, an orthographic camera (read from the script), so "limited IRAY quality" is the best on offer.

## How it would fit this sprite pipeline

**Where it slots in.** For a human, Genesis would replace concept art, mesh generation and rigging in one step, giving a Blender scene with named bones and a face. `render_sheet.py` opens only `.fbx`, `.glb`, `.gltf` or `.obj` and poses bones only (read from the script), so each pose or viseme would need its own baked export, or the script would need shape key and `.blend` support. Genesis 8's visemes only move face bones, so they are the one face data its `--poses transforms:` path could carry; that is untested. Under the standard Daz EULA the sheet may ship, but the `.blend` and any exported FBX may not.

**It should not feed the AI stages.** A Daz render used as a Qwen-Image reference, a ControlNet input or a TRELLIS image is the use the AI exclusion puts in doubt (see [the AI clauses](#the-ai-clauses)). The doubt covers renders only. Loading the Genesis mesh, its textures or its UV maps into Hunyuan3D 2.1 texturing, UniRig or any other model is the plain case of the exclusion: Content input to a system that auto-generates material from it. Texturing is the tempting case, because that stage paints a mesh to match a concept ([textures](/guide/textures)), and Hunyuan3D's territory exclusion would stack on top ([licensing](/guide/licensing#hunyuan3d-2-and-2-1)).

**The face pays off at portrait size.** Sprites here are 128 px for a map token and 220 px for a close-up, and portraits start at 340 px ([facings](/guide/facings#sizes)). A viseme mouth can read in a dialogue portrait; at 128 px the rig's value is consistent proportions and poses across a cast.

**The style mismatch.** The house concept prompt asks for a "Detailed painted fantasy illustration with realistic materials and lighting", and its negative prompt excludes "cartoon, cel shaded, anime, flat vector art" ([concept art](/guide/concept-art#what-a-good-prompt-for-this-pipeline-says)). Genesis ships Iray materials: Genesis 9 Starter Essentials alone has 753 maps of up to 8192 by 8192. The gap is texture detail and skin realism against painted realistic materials, not the shading model. Three ways to narrow it:

- **Render under the same lights as everything else.** Import with "Extended Principled", the EEVEE material option, and render with `render_sheet.py`'s own `--key` and `--ambient` lighting, as the TRELLIS assets are, with the maps scaled down towards sprite size. Neither step was tried, and whether those materials survive a glTF export was not checked, so this may need `.blend` input.
- **Restyle through diffusion.** Likely the closest match to the painted art, but the option the AI clause puts most in doubt.
- **Toon content, for a cel-style project only.** The free Genesis 9 Starter Essentials includes Base Anime Feminine and Masculine, Toon Base clothing variants and Toon Base Anime Hair. It also ships the six Toon sub-figures in the table above and a `Base Anime FACS` folder of 12 `_NoJaw` variants. Blender's Shader to RGB node, the usual base of a toon ramp, works only on EEVEE and breaks the PBR pipeline and every render pass except Combined. This pipeline's own concepts exclude that look.

### Genesis as a shape donor

[Lip sync](/reference/lip-sync#heads-to-borrow-shapes-from) lists heads whose shapes could be moved onto a generated mesh, and [measured a Surface Deform transfer](/reference/lip-sync#what-blender-does-headlessly) on test spheres. A Genesis head is the licence-heavy case.

On a plain reading, Genesis shape keys transferred onto a TRELLIS or Hunyuan3D mesh are a derived three-dimensional work, which the EULA allows only if it is "designed to require or encourage the use of Content available through the online DAZ store" ([derived works](#derived-works)). A generated mesh does neither, so the EULA's grant for derived 3D works does not cover it, and Daz may also demand at its sole discretion that distribution stop. An Interactive License does not lift the condition. Addendum 3.0 restates it for game use, where Daz may stop a work that "fails to require the use of Content", with no "or encourage". Sprites rendered from such a mesh would otherwise fall under the 2D works clause, but the derived-works condition attaches to creating the work, not only to distributing it. All of this is a reading of the EULA text, not a ruling from Daz.

## Other character bases compared

Licence cells were checked on 2026-09-15 against the pages linked below and in [Sources](#sources-worth-reading).

| Base | Tool licence | Base assets licence | Mesh in a sold game | Renders in a sold game | AI terms |
|---|---|---|---|---|---|
| DAZ Genesis | Daz Studio: [Daz EULA](https://www.daz3d.com/eula), proprietary (code). Diffeomorphic: GPL-2.0-or-later (code) | Standard Daz EULA (content) | Interactive License per product, or a separate signed agreement; never in native formats; protected against extraction | Yes, unless the product page says otherwise | Excludes Content input to AI that can generate derivative material (content) |
| MakeHuman, MPFB2 | MakeHuman: AGPL-3.0-or-later (code). MPFB2: GPL-3.0-or-later (code) | CC0 1.0 (bundled assets, content); community and several official packs differ | Yes | Yes, no claim over output | No AI clause (content) |
| MB-Lab | GPL-3.0-or-later (code) | AGPL-3.0-or-later (meshes, images, JSON: content) | Only under AGPL-3.0 | Yes, except a texture-extraction render | Not checked |
| CharMorph | GPL-3.0-or-later (code) | Per character: MB-Lab AGPL-3.0-or-later; Vitruvian CC0; Antonia CC BY 3.0; Reom CC BY, no version (content) | Vitruvian yes; CC BY with credit; MB-Lab characters only under AGPL-3.0 | Yes, except a texture-extraction render | Not checked |
| Human Generator | GPL-3.0 (code) | [Human Generator Digital Asset License](https://help.humgen3d.com/license), proprietary (content) | Commercial tier only, not extractable, never as `.fbx` | Commercial tier only | No AI-training clause (content) |
| VRoid Studio | VRoid Studio Terms of Use, 2026-06-24, and Guidelines, 2023-12-21 (code and content) | Terms Art. 13(1): pixiv's copyright, "not CC0", any use except building a model-generating app (content) | Yes, unless the item has its own clause | Yes | Not checked |
| Character Creator 5 | Reallusion Software EULA, 2026-05-25 (code) | Reallusion Content License Policy (License Update 2025.8.1) and Content EULA (2025-08-01), Standard License (content) | Unclear. The Standard License allows commercial games and export to outside engines, but Content EULA 2.1 Restrictions (C) also bars use "As embedded content within applications or online services"; read both before shipping. 3D models only in proprietary formats a publicly available application cannot open; not as paid in-software or downloadable content; not in character generation; topology and rigs stay Reallusion's | Yes | Bans AI training (code); bans ML, AI training and AI-generated output (content) |
| MetaHuman | Unreal Engine EULA, update 21 (code) | Unreal Engine EULA and Epic Content License Agreement with MetaHuman Content Addendum (content); readings differ, see [MetaHuman](#metahuman) | Unsettled | Unsettled | Bans using MetaHuman characters and animation curves to build or enhance a database or to train or test AI (both readings) |
| Mixamo characters | Adobe General Terms of Use, 2025-10-03 (service) | General Terms section 3.6, embedded only; Mixamo FAQ, 2021-09-14, royalty free (content) | Yes, embedded, never stand-alone | Yes | Bans using output to train AI, section 17(C) (service) |
| SMPL, SMPL-X | SMPL Blender add-on: GPL-3.0 (code), discontinued | SMPL-Model and SMPL-X Model licences, non-commercial (weights and content); SMPL-Body subset CC BY 4.0 (content) | Not without a commercial licence; SMPL-Body only without shape blendshapes, with credit | Not without a commercial licence; SMPL-Body with credit | Bans training for commercial use (weights) |
| Quaternius Universal Base Characters | No tool (content only) | CC0 1.0 (content) | Yes | Yes | Not checked |
| KayKit Adventurers | No tool (content only) | CC0 1.0 (content) | Yes | Yes | Not checked |

Prices checked on 2026-09-15.

| Base | Face | Skeleton | On this Linux box | Cost |
|---|---|---|---|---|
| DAZ Genesis | 17 viseme dials; FACS on 8.1 and 9 | 170 named bones on Genesis 8, 143 on Genesis 9 | No Daz Studio; Diffeomorphic not run headless | Starter Essentials US$0.00; Interactive License US$50.00 on Genesis 9 Starter Essentials |
| MPFB2 | Shape keys from separate packs: 22 Microsoft-style visemes, 15 Meta/Oculus-style visemes, 52 ARKit units | Presets such as `game_engine` and `mixamo` documented, not checked | Blender 4.2 or newer; not run in the container | Free |
| MB-Lab | Not checked | Not checked | Not checked; reported archived in 2024-07 (not verified) | Free |
| CharMorph | Not checked | Not checked | Not checked | Free |
| Human Generator | Not checked | Not checked | Not checked | US$68.00 Personal, US$128.00 Commercial, per user |
| VRoid Studio | VRM presets, optional per file | Not checked | No Linux build | Free |
| Character Creator 5 | Not checked | Not checked | Windows only | US$29.00/month, US$99.00/year or US$299.00 perpetual |
| MetaHuman | Not checked | Not checked | Creator plugin in the Unreal Editor, on Linux since MetaHuman 5.7 | No Seat under US$1,000,000 gross revenue over the last 12 months; paid Seats above, unless another exception applies (both readings) |
| Mixamo characters | Not checked | Not checked | Browser service, not checked | Free with an Adobe ID; not for Enterprise or Federated IDs or a China country code |
| SMPL, SMPL-X | FLAME expression blendshapes reported for SMPL-X (not verified) | Skeleton rig, joint count not checked | Blender add-on discontinued | Commercial licence from Meshcapade, price not checked |
| Quaternius Universal Base Characters | No morph targets | 65 joints, Unreal-mannequin-style names, no jaw or eye bones | Plain glTF and FBX | Standard free; Source US$19.99 or more |
| KayKit Adventurers | No facial blendshapes | 23-joint `Rig_Medium`, one head bone | Plain FBX and glTF | Free tier; `.blend` US$11.95 or more |

### MakeHuman and MPFB2

[MakeHuman's licence](https://github.com/makehumancommunity/makehuman/blob/master/LICENSE.md) puts its base mesh, targets, textures, clothes, poses and expressions under CC0 1.0 and claims nothing over output; assets from community repositories carry their own licences. MPFB2, the Blender add-on, keeps that split, and its FAQ answers yes to selling models and to using them in a closed-source game. Several official packs on MakeHuman's [asset index](https://static.makehumancommunity.org/assets/assetpacks.html), such as Hair 02 and 03, Shirts 02 and 03 and Bodyparts 02 and 03, are CC BY rather than CC0, so dressing a character from them adds a credit. MPFB2 needs Blender 4.2 or newer, and v2.0.17 shipped on 2026-07-22.

The face is what makes it a Genesis alternative. From v2.0.15, FaceService loads face packs as shape keys at value 0.0: 22 Microsoft-style visemes, 15 Meta/Oculus-style visemes (`viseme_aa`, `viseme_CH`, `viseme_sil`) and 52 ARKit face units. The three packs are separate CC0 "functional asset packs" on the asset index, and FaceService loads from installed packs, so install them first. Whether MPFB runs in a UI-less `bpy` was not checked.

### The others, briefly

**MB-Lab and CharMorph.** [MB-Lab's licence](https://mb-lab-docs.readthedocs.io/en/latest/license.html) says generated models "must be distributed under AGPL 3", an obstacle it names for a closed-source game. [CharMorph's license.txt](https://github.com/Upliner/CharMorph/blob/master/license.txt) keeps that for MB-Lab characters.

**VRoid Studio.** The [Terms of Use](https://policies.pixiv.net/en.html#vroidstudio) (revised 2026-06-24) and [Guidelines](https://vroid.com/en/studio/guidelines) (2023-12-21) forbid building an application that outputs avatars or 3D models by deforming or combining pixiv's Provided Content without a separate licence, unless it is made only for personal use. Mouth presets are covered in [lip sync](/reference/lip-sync#mouth-shape-sets).

**Character Creator.** The [Content License Policy](https://www.reallusion.com/license/content.html)'s Standard License now lets you "create unlimited characters across multiple titles or projects", but the FAQ lower on the same page still carries older, contradictory wording. The [Content EULA](https://www.reallusion.com/Content/EULA/EULA.htm) (updated 2025-08-01) is the binding text. Its Standard License allows commercial games, yet bars use "As embedded content within applications or online services" and "For machine learning, AI training, or AI-generated output".

**Mixamo.** Adobe's [Mixamo FAQ](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html) (updated 2021-09-14) says characters and animations may be used royalty free, including in video games. [Adobe's General Terms of Use](https://www.adobe.com/legal/terms.html) (2025-10-03), which Mixamo's footer links, allow distribution only embedded in your product (section 3.6) and forbid using output to train AI (section 17(C)). The Mixamo row in [licensing](/guide/licensing#animations-are-all-clear) predates this reading and lacks both terms.

**SMPL and SMPL-X.** The [SMPL](https://smpl.is.tue.mpg.de/modellicense.html) and [SMPL-X](https://smpl-x.is.tue.mpg.de/modellicense.html) model licences allow only non-commercial research, education and artistic use, and send commercial licensing to Meshcapade (smpl@max-planck-innovation.de). The CC BY 4.0 SMPL-Body subset has no shape blendshapes, CC BY grants no patent rights, and the model is covered by patent US10395411B2.

**Quaternius and KayKit.** Quaternius's [FAQ](https://quaternius.com/faq.html) still says everything is CC0, but its new [Quaternius Asset License](https://quaternius.com/license.html) 1.0 (2026-08-28) covers at least one pack and bans redistributing assets as assets; Universal Base Characters is still CC0. [KayKit Adventurers](https://kaylousberg.itch.io/kaykit-adventurers) is CC0 1.0, and its only blendshape is a bow string. These sets are bodies, not talking heads.

### MetaHuman

MetaHuman Creator is a plugin inside the Unreal Editor, not a Blender tool. The creator plugin reached Linux with MetaHuman 5.7 on 2025-11-12.

Whether its characters can ship outside Unreal is unsettled, and the [Unreal Engine EULA](https://www.unrealengine.com/eula/unreal) (update 21, checked 2026-09-15) supports two readings. Both treat character models developed with Engine Code as royalty-free Non-Engine Products, even in other engines. Both say royalty-free work can still need paid Seats unless gross revenue over the last 12 months is under US$1,000,000 or another exception applies, that MetaHuman characters and animation curves may not be used to build or enhance a database or to train or test AI, and that "certain assets that we make available under separate agreements are available for use only with Unreal Engine". The dispute is over those separate agreements. One reading adds that the MetaHuman Content Addendum keeps downloaded MetaHuman Content UE-Only, while [Epic's licence FAQ](https://www.metahuman.com/license) says in-engine MetaHumans from UE 5.6 may be used in any engine.

## Licences

Checked 2026-09-15 against the linked pages. The Daz EULA carries no version or effective date, and Daz may amend it from time to time, so re-read it before relying on this. None of it is legal advice.

### Renders and sprites: the standard Daz EULA

The [Daz EULA](https://www.daz3d.com/eula#general_license), section 1.0, "Two-Dimensional Works", allows using Content "in the creation and presentation of two-dimensional animations and renderings". It covers "two-dimensional images that simulate motion of three-dimensional objects", and lets you "publish, market, distribute, transfer, sell or sublicense" them. The condition is that nothing distributed lets the Content "be separately exported, extracted or de-compiled into any re-distributable form or format".

Daz's [Interactive License page](https://www.daz3d.com/interactive-license-info) says 2D artwork you render is "completely owned by you (unless specified otherwise on the product page)". It exempts content built from "a stack of renders, such as a sprite", for which the standard agreement suffices. Forum moderator Richard Haseltine said the same of sprite sets and pre-rendered cut-scenes ([2023-12](https://www.daz3d.com/forums/discussion/665356/daz-interactive-license)), and that free content bundled with Daz Studio has the same licence as the rest of the store ([2018-12](https://www.daz3d.com/forums/discussion/294811/use-free-stuff-for-commercial-purpose)). Forum posts are not the EULA.

So sheets and portraits rendered from the free Genesis figures may ship in a sold game with no purchase, unless the product page says otherwise and as long as nothing shipped lets the Content be extracted. Unless otherwise specified, Interactive Licenses are "not eligible for returns or refunds".

### Shipping 3D data: the Interactive License

The standard Daz EULA forbids distributing anything from which Content "or any substantially similar version of the Content" can be extracted, and transferring Content without Daz's written consent. Shipping it in a game needs Addendum 3.0, the Interactive License, or a separate agreement signed by both parties.

The add-on is bought per product, and only where the product's creator offers one. The per-artist Game Developer License still appears in the EULA, but none was for sale on 2026-09-15. A product without the option cannot be used in a game as a 3D asset, although its renders still can. Even with the licence, the content must not reach end users in native formats, and you must protect it "by employing technology, asset protection, encryption or any other resources at User's disposal".

| What ships | Licence needed |
|---|---|
| Sprite sheets, portraits, pre-rendered frames | Standard Daz EULA, no purchase, unless the product page says otherwise |
| Mesh, rig, morphs, textures, exported FBX or glTF inside the build | Interactive License per product, or a separate agreement signed by both parties; never in native formats; protected against extraction |
| `.duf`, `.dsf` or other native Daz files | Not allowed under the standard Daz EULA or the Interactive License |
| Daz content or its 2D or 3D derivatives sold as a separate in-game purchase | Interactive License plus written consent |
| Cloud or post-install delivery by an individual or business above US$1,000,000 annual revenue | Interactive License plus written consent |

Add-on prices on 2026-09-15 were US$50.00 on Genesis 9 Starter Essentials, Victoria 9 HD and Genesis 9 Expressions, and US$35.00 on Genesis 9 Body Shapes, Genesis 8 Female Expressions and the dobit viseme pack. So under per-product licences, a Genesis 9 figure with the Expressions set ships in 3D only with two Interactive Licenses, US$100.00 in all, plus the US$21.98 product. Only a [2024 forum reply](https://www.daz3d.com/forums/discussion/686221) claims that one licence bought for a bundle covers every item in it. The original poster's Product Library still listed the item as Standard License only, so confirm with Daz support.

### What is genuinely free

[Genesis 9 Starter Essentials](https://www.daz3d.com/genesis-9-starter-essentials) (SKU 86958) is US$0.00, "included for FREE with your Daz Base membership and Daz Studio download". Genesis 8 Starter Essentials (SKU 42071) is also US$0.00, and it contains the Genesis 8.1 figures and their FACS morphs. Free items carry the same EULA as paid ones. Product pages can add restrictions, and content flagged "for editorial use only" is limited to fair use, so treat it as unusable in a commercial game.

Elsewhere, Renderosity freebies carry each creator's terms. One Genesis 8 pose freebie checked on 2026-09-15, [Isazforms' Fever dance pose 1](https://www.renderosity.com/freestuff/items/88906/free-daz-pose-for-genesis-8-female-daz-studio-fever-dance-pose-1), allows commercial renders but forbids redistributing its files. Renderosity's paid [Standard License](https://www.renderosity.com/standard-license) allows "2D rendered images for games" but not real-time games "where the Product files are distributed".

### The AI clauses

The EULA "expressly excludes the use, incorporation, or input of any Content, in whole or in part, in connection with i) any AI engine, program, or system ... with capabilities or instructions to auto-generate materials that are derivative, imitative, or otherwise plagiaristic of the Content". Clause ii) adds "any activity contrary to the intended use of the Content License". AI is defined broadly enough, with DALL-E 2 named, to cover diffusion models, and the Interactive License does not lift the clause.

The clause has not always been there. Wayback copies show it added between 2023-03 and 2023-05, missing from a revision captured on 2024-06-16, and back by 2024-08-03 through to the live page, so a copy of the EULA saved in mid-2024 lacks it. Check the live page, not an old saved copy.

The EULA says nothing explicit about renders used for img2img or ControlNet. It calls a render an image "derived by User from the Content" and never says whether that counts as Content "in part". Silence is not permission. The only guidance on renders is two forum posts by moderator Richard Haseltine. On [2023-09-24](https://www.daz3d.com/forums/discussion/651506/usage-for-lora-training) he said it "should be OK to use images to which you have title ... in AI training", with legal questions open, and did not mention the AI clause already in the EULA. On [2026-05-11](https://www.daz3d.com/forums/discussion/761731/ai-training-data), after offering to ask Daz, he posted: "yes, you can use your renders as training material or input for AI ... no, you cannot use the 3D data as training material without a special license from Daz". Daz itself has published no such statement.

::: danger Keep Daz content out of the AI stages
Feeding a Daz render to Qwen-Image, ControlNet, TRELLIS or Hunyuan3D for something you sell rests on forum posts. Against it stand licence text that bars Content "in whole or in part" and a catch-all clause. Get a written answer from Daz first, and keep it with the asset. The mesh itself, its textures and its UV maps carry no such doubt: never load them into Hunyuan3D 2.1 texturing, UniRig or any other model.
:::

Anything uploaded to a Daz website, gallery or forum grants Daz a worldwide, royalty-free, non-exclusive licence to display, modify and make derivative works from it, with a moral-rights waiver where the law allows (EULA Addendum 4.0). Either side can end it for an item on written notice, except for combined works Daz has already sold or distributed. Daz's [Terms of Service](https://www.daz3d.com/terms-of-service) (undated, checked 2026-09-15) separately forbid using "any AI, robot, spider, or other automatic device" to access its website.

### Derived works

A derived 3D work, such as a morph or a new figure, may be created and distributed only if it is "designed to require or encourage the use of Content available through the online DAZ store". On written request you must stop distributing it if Daz decides, at its sole discretion, that it "is substantially similar to or is a clone of existing Content", fails that test, or otherwise violates the EULA. Addendum 3.0 restates these conditions for game use, where the second ground reads "fails to require the use of Content", with no "or encourage". Whether a reworked mesh is too similar is left to Daz's discretion.

### Tools that touch Daz content

- **Diffeomorphic** is GPL-2.0-or-later (code). Imported assets keep their owners' licence rights, and the MHX rig assets it adds are CC0.
- **The DSON specification** text is CC BY 3.0 Unported. That covers the documentation, not Daz content or software.
- **The bridges** (unsettled, checked 2026-09-15). Both readings find the DazToBlender, DazToUnity, DazToUnreal and DazToRoblox repositories Apache-2.0 (code) ([DazToBlender LICENSE](https://github.com/daz3d/DazToBlender/blob/master/LICENSE)). Both also find that downloading the Daz to Roblox Studio Exporter binds you to the [Daz to Roblox Studio Terms](https://www.daz3d.com/roblox-terms), which use a paid Roblox Reseller License instead of the Interactive License and apply only below US$1,000,000 annual revenue without Daz's written consent. One reading still counts the exporter as an Apache-2.0 tool. The other says it is not governed by Apache-2.0 alone, and notes that Daz's [open-source page](https://www.daz3d.com/open-source) leaves it out.

## What not to do

**Never put Daz 3D data in this repository or the container image. Never put it in a game build without an Interactive License for each product used, and even then keep it out of native formats and protect it against extraction.** The standard Daz EULA forbids distributing extractable Content and transferring Content without consent. A published image containing the content library would be distribution ([redistributing](/guide/redistributing)). For a Daz-sourced asset, give `cleanup.py keep` no `--model` or `--rig`: it copies them into `output/assets/<name>/`, the curated asset folder ([cleanup](/guide/cleanup)), and its `sources.json` records only original paths, so nothing there would mark the mesh as Daz data (read from the script).

**Do not feed Daz renders to Qwen-Image, ControlNet, TRELLIS, Hunyuan3D or any training** for a game you sell until Daz answers in writing, **and never load the Genesis mesh, textures or UV maps into Hunyuan3D texturing, UniRig or any other model.**

**Do not ship a generated mesh carrying Genesis-derived shape keys.** It is a derived 3D work that requires no Daz store content, which the derived-works grant does not cover, with or without an Interactive License. It also ships Daz morph data.

**Do not buy an Interactive License for a sprite-only game.** A stack of renders needs only the standard Daz EULA unless the product page says otherwise, and unless stated otherwise the add-on is not refundable. If 3D data might ship later, a Daz forum moderator said in 2022-09 that in-house development needs no Interactive License until "you have something ready to share"; that is a [forum post](https://www.daz3d.com/forums/discussion/588916), not the EULA.

**Do not sell Daz-derived sprites as a separate in-game purchase without asking.** Under the Interactive License that needs written consent, and no ruling covers standard-licence renders.

**Do not upload pipeline renders to Daz's galleries or forums.** An upload licenses Daz to modify them.

**Do not script the Daz website.** Download through Daz's installers or a browser.

**Do not plan on the bridges on Linux.** They run only inside Daz Studio, which has no Linux build.

**Do not ship MB-Lab meshes in a closed-source game.** Its data is AGPL-3.0-or-later, and generated models "must be distributed under AGPL 3". **Do not ship SMPL or SMPL-X meshes in a commercial game without a commercial licence.** The CC BY 4.0 SMPL-Body subset is the exception, without shape blendshapes and with credit.

## What to build

Ranked. None of it duplicates an existing script.

1. **Experiment: MPFB2 in the container's `bpy`.** Install MPFB 2.0.17 and its three CC0 face packs into `bpy` 4.5.9, build a human from CC0 assets recording every pack and its licence, bake each of the 15 Oculus-style visemes into its own `.glb`, render them through `render_sheet.py`, and record every step that fails. Among the bases compared here it is the one whose bundled mesh and face shape keys are both CC0, and running it without a UI was not checked.
2. **`scripts/daz_inventory.py`.** Standard-library `gzip` and `json` only. For a content directory outside the repo, print per figure the vertex and face counts, bone names and count, morph names grouped by prefix (`eCTRLv`, `facs_ctrl_v`, `facs_bs_`, `facs_cbs_`, `facs_jnt_`, `pJCM`, `body_cbs_`), and whether each `_div2` `.dsf` holds deltas or only an `hd_url`. It needs no Blender, desktop or AI stage, turns this page's community counts into measured ones, and settles two open questions below.
3. **Experiment: a Diffeomorphic headless probe.** Install `import_daz` from the `version_5_2_0` tag, register it under `bpy` 4.5.9 in background mode, and bind-mount a hand-installed Genesis 9 Starter Essentials tree read-only, outside `output/`; `docker-compose.yml` has no such mount. Check that `contentDirs` exist, run `easy_import_daz` with visemes and FACS, and record shape key names per figure (body, Mouth, Eyes, Eyelashes, Tear), whether the Mouth figure gets its 10 viseme controllers, bone count, `get_error_message()`, and wall time, peak RAM and peak VRAM for one EEVEE render of a figure with 753 maps of up to 8192 by 8192 on the 16 GB card. The whole Linux route rests on background use the importer neither handles nor documents.
4. **A shape key pose kind in `render_sheet.py`.** Let `--poses` set named shape keys and rig custom properties, and accept a `.blend`. Every face route here is shape keys or rig properties, and item 8 in [lip sync's build list](/reference/lip-sync#what-to-build) needs the same change, so build it once.
5. **Doc section: "Character bases" in [licensing](/guide/licensing).** The Daz render-versus-3D-data split, the AI clause and the MPFB2 row, dated and linked, with the two questions to put to Daz in writing, plus Adobe General Terms sections 3.6 and 17(C) in the Mixamo row. A Genesis sprite looks exactly like one that is safe to ship, and that page is where readers decide per asset.
6. **Licence fields and guards in `scripts/cleanup.py`.** Extend `keep` to write source, SKU, artist, licence held, EULA read date and a SHA-256 of the saved EULA text into `sources.json`, in one schema with the voice-line fields proposed in lip sync. Have it refuse `--model` and `--rig` for a `daz` source unless an Interactive License is recorded, and have `run_workflow.py` refuse an input image whose asset's `sources.json` says `daz`. The EULA has no version and binds you to amendments, so a dated record is the only proof of what was agreed, and the AI-stage rule is enforced, not remembered.
7. **Experiment: lip sync's Genesis column on a figure.** Once items 3 and 4 work, set the dials that [lip sync's mapping](/reference/lip-sync#the-mapping-to-adopt) gives for X and A to H on an imported Genesis 9 figure and render each at 340 px. That column has never been tried on a figure, and a talking Genesis portrait depends on it.

## Honest uncertainty

- **Whether a render is "Content" under the AI clause.** The licence is silent. The only guidance is two moderator forum posts, and the 2026 post does not say Daz gave the answer.
- **Selling standard-licence sprites as DLC.** Section 1.0 allows selling 2D works, and Addendum 3.0's sale ban is written for Interactive-licensed content. No ruling covers renders.
- **Sprites from a mesh carrying Genesis-derived shapes.** The derived-works condition attaches to creating the work, and no ruling covers renders of it.
- **Character Creator content inside a game.** The Content EULA's Standard License allows commercial games and export to outside engines, but its 2.1 Restrictions (C) bars use "As embedded content within applications or online services", and the policy page's FAQ still carries older wording. Which term governs a character shipped in a build is not settled; read the [Content EULA](https://www.reallusion.com/Content/EULA/EULA.htm) (checked 2026-09-15).
- **Whether Diffeomorphic registers under the pip `bpy` module and runs with `--background`.** Not tried.
- **Whether a saved `.blend` works without the add-on.** Diffeomorphic's drivers look like plain expressions that vanilla `bpy` could evaluate; this was inferred from source, not run. Whether they need Blender's auto-run Python scripts enabled was not checked.
- **What an import without a `.dbz` loses on Genesis 9**, whose visemes are split across the body and Mouth figures, and whether its Toon sub-figures import at all.
- **Whether Genesis 8.1's `_div2` `.dsf` files carry useful base-resolution deltas**, or mostly point at `.dhdm` data.
- **Daz Studio without a display.** Daz documents `-headless` and `-noPrompt` flags and script rendering to file through `DzRenderMgr.doRender` (read, not verified). Whether they work under Wine with no display was not tried.
- **Daz Studio 6 under Wine.** A [2026-06 forum report](https://www.daz3d.com/forums/discussion/comment/9567361/) says it runs under Bottles, but it was not verified.
- **MPFB2 face packs without a UI.** Loading them in the container's `bpy` was not tried, here or in [lip sync](/reference/lip-sync#honest-uncertainty); experiment 1 settles it.
- **Unsettled licence readings.** Whether the Daz to Roblox Studio Exporter counts as an Apache-2.0 tool, and whether MetaHuman characters may ship outside Unreal, are set out above.

## Sources worth reading

- [Daz EULA](https://www.daz3d.com/eula): the 2D works clause, the AI exclusion and Addendum 3.0.
- [Daz Interactive Licenses](https://www.daz3d.com/interactive-license-info): the sprite exception in Daz's words.
- [Genesis 9 file list](https://docs.daz3d.com/public/read_me/index/86958/file_list) and [Genesis 8 file list](https://docs.daz3d.com/public/read_me/index/42071/file_list): every viseme and FACS file on the free figures.
- [DSON file types](https://docs.daz3d.com/public/dson_spec/format_description/file_types/start): the format, before writing a reader.
- [Diffeomorphic import_daz](https://github.com/Diffeomorphic/import_daz): the importer, source and wiki.
- [Diffeomorphic scripting improvements](https://diffeomorphic.blogspot.com/2025/03/scripting-improvements.html): the keyword-argument API.
- [Daz Studio and Linux, page 56](https://www.daz3d.com/forums/discussion/60901/daz-studio-and-linux/p56): the Wine reports.
- [Daz to Roblox Studio Terms](https://www.daz3d.com/roblox-terms): the reseller terms behind the unsettled bridge reading.
- [MPFB2 licence](https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md) and [FaceService](https://github.com/makehumancommunity/mpfb2/blob/master/docs/services/faceservice.md): CC0 assets and the viseme packs.
- [MakeHuman asset packs](https://static.makehumancommunity.org/assets/assetpacks.html): which packs are CC0 and which CC BY.
- [MB-Lab licence](https://mb-lab-docs.readthedocs.io/en/latest/license.html) and [CharMorph license.txt](https://github.com/Upliner/CharMorph/blob/master/license.txt): the AGPL output trap, and per-character licences.
- [VRoid Studio Terms of Use](https://policies.pixiv.net/en.html#vroidstudio): what "not CC0" allows.
- [Reallusion Software EULA](https://www.reallusion.com/Content/EULA/AP/EULA_AP.htm), [Content License Policy](https://www.reallusion.com/license/content.html) and [Content EULA](https://www.reallusion.com/Content/EULA/EULA.htm): the Base Model clause, the 2025.8.1 table and the Standard License restrictions.
- [Unreal Engine EULA](https://www.unrealengine.com/eula/unreal): Non-Engine Products and the MetaHuman AI clause.
- [Adobe General Terms of Use](https://www.adobe.com/legal/terms.html): sections 3.6 and 17(C), which govern Mixamo.
- [SMPL-X model licence](https://smpl-x.is.tue.mpg.de/modellicense.html) and [SMPL add-on LICENSE.md](https://github.com/Meshcapade/SMPL_blender_addon/blob/main/LICENSE.md): non-commercial models, and which files need a commercial licence.
- [Quaternius licence](https://quaternius.com/license.html): the new non-CC0 asset licence.
- [Renderosity Standard License](https://www.renderosity.com/standard-license): the same renders-yes, files-no split outside Daz.
