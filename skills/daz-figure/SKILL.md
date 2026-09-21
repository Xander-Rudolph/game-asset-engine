---
name: daz-figure
description: Install a Daz 3D product the user downloaded, import its Genesis figure into Blender and render its visemes, within the Daz licence. Use when the user says "I downloaded Genesis 9 from Daz", "import a Daz figure into Blender" or "render a Genesis character's visemes", or has Daz Install Manager zips. Renders may ship; the 3D data needs an Interactive License.
---

# Daz figure: a Genesis figure in Blender, rendered, never shipped as 3D

Work in the asset-engine repo root. The long version, with every measurement
and what failed on the way, is `docs/guide/daz-figures.md`. The licence, read
from Daz's own pages, is in `docs/reference/daz-genesis.md`, "Licences" and
"What not to do".

Everything below was measured on 2026-09-16 and 2026-09-18 on one product,
Genesis 9 Starter Essentials (SKU 86958): the library scripts on the host's
`python3`, the importer and the renders in the container's `bpy` 4.5.9, whose
EEVEE draws through llvmpipe on the CPU, not on the card. Every time below is
an EEVEE one and stays one: `daz_import_probe.py` rasterises its own framings
with EEVEE and pins `--engine eevee` on its `render_sheet.py` stage, rather
than taking the Cycles default that script took on 2026-09-18. Genesis 8, 8.1
and other products were never run.

**One stage per turn.** The licence, the install, the build, then whichever of
the morphs, character, outfit and pose stages they want, then the renders. Show
each result and get an answer before the next. If you run two stages without
asking, that is a bug.

**Everything this skill produces that may ship is a render.** Dialling a
character's shape, dressing it and posing it does not change that: the figure,
its morphs, its outfits, its hair and the `.blend` they live in are Daz 3D data
and may not go into a game build without an Interactive License for each
product used (step 1).

## First, is this the right route?

Ask what the user wants to end up with.

- **A 3D character in their game**, as a mesh, rig or exported FBX or glTF.
  Say first that the 3D data needs an Interactive License for each product,
  with conditions (step 1). With none, offer MakeHuman through MPFB2, whose
  bundled assets and face packs are CC0 (`docs/reference/daz-genesis.md`,
  "MakeHuman and MPFB2", built with `scripts/mpfb_probe.py`).
- **Sprites or portraits rendered from a Genesis figure.** This skill.
- **A character dialled, dressed and posed, then rendered.** This skill,
  stages 4 to 7. No Daz Studio is needed for any of it, but two things do not
  work on this host: the `.dbz` fitting route, and clothes taking a character's
  shape (step 6).
- **Several characters at once, as reference or as sprites.** Step 9b:
  `scripts/daz_characters.py` rolls a roster out of the library and renders each
  one front and side.
- **A talking dialogue portrait from a Genesis render.** Not through the
  `lip-sync` skill: its portrait and mouths are Qwen-Image edits, an AI stage
  a Daz render must stay out of (step 1).
- **A face that reads on a sprite.** On the whole figure at 128 px each viseme
  changed 0 to 4 pixels; in a face framing at 340 px, 533 to 1873 (step 9).
  Say that the face reads only close up.
- **Getting the product.** The user downloads it in a browser from their own
  Daz account. Never open daz3d.com with any tool, whether curl, a fetch tool
  or browser automation: Daz's Terms of Service forbid automated access. The
  user reads the product page and the EULA themselves.

## Before you start

```sh
scripts/doctor.py --skip-models
python3 scripts/daz_library.py list      # where the library is, and what it holds
```

Read the doctor's output and do not start until it says ready: the build and
the renders run in the container. No model weights are used.

`daz_library.py` keeps the library at `MODELS_DIR/daz_library`, outside the
repo, where the container sees it as `/app/models/daz_library`, and refuses a
library inside the repo. `list` prints its host path on the first line.
`daz_import_probe.py build` reads `/models/daz_library` unless given
`--library`, so pass the path `list` printed when it differs.

## Rules for the shared machine

- **One Blender job at a time, never beside a ComfyUI job.** Before each Blender
  job `daz_import_probe.py` polls every 30 s until ComfyUI's queue is empty and
  no other `python3 -c` job runs in the container. Do not pass `--no-wait`.
- **Say the cost before every render** (steps 8 and 9). Start short.
- **Stop only what you started.** Ctrl-C or SIGTERM to the probe ends the
  Blender job it started, deletes that job's frames and writes no report
  (exit 130 or 143). Never restart, stop or remove the container.

## 1. The licence, before anything is installed

Say this plainly, and say it is a reading of the EULA, not legal advice. The
EULA carries no version and Daz may change it.

- **Renders and sprites may ship** in a sold game with no purchase, unless the
  product page says otherwise, as long as nothing shipped lets the content be
  extracted. Selling them as a separate in-game purchase has no ruling: ask
  Daz first.
- **The 3D data may not go into a build** without an Interactive License for
  that product or a separate agreement signed by both parties. That covers the
  mesh, rig, morphs and textures, and any FBX or glTF exported from them. Under
  an Interactive License it may go in only on all four conditions: never in
  native formats such as `.duf` or `.dsf`; protected against extraction; Daz's
  written consent before selling it, or its 2D or 3D derivatives, as a separate
  in-game purchase; and Daz's written consent before delivering it through the
  cloud or after install when annual revenue is above US$1,000,000. The add-on
  was US$50.00 on Genesis 9 Starter Essentials when checked on 2026-09-15.
- **Daz content stays out of every AI stage.** Never give its mesh, textures or
  UV maps to any model, and never give a render from `output/daz/` to
  Qwen-Image (concept art, concept edits, mouth edits), ControlNet, TRELLIS,
  Hunyuan3D or any training, until Daz answers in writing. An Interactive
  License does not lift this. So no Daz render, mesh or texture goes into
  `asset-pipeline`, `concept-edit` or `lip-sync`, whose stages are those models.
- **Never curate Daz 3D data with `scripts/cleanup.py keep`.** It refuses
  `--model`, `--rig` or `--textures` from `output/daz/`, any file in the
  library, and a native Daz file from anywhere, with exit 1 and `keep: refused.
  Daz 3D data may not be curated into a shippable asset folder under the
  standard Daz EULA:`.
- **Never put Daz content in the repo**, a commit or the image.
- **Never script the Daz website.**

**No Daz render comes into this conversation.** The AI clause's examples name
chatGPT, a chat model like you, and the research note does not say whether a
render counts. So never read an image from `output/daz/` back: the user opens
each labelled sheet and says what they see, and you give the pixel counts from
its `_render.json`. If the user asks you to look yourself, say in one line that
this is open until Daz answers in writing, and read a sheet only if they then
decide it is allowed.

Ask whether they have read the EULA (<https://www.daz3d.com/eula>) and on what
date, and whether they hold an Interactive License for this product. Then ask:
**install** or **stop**.

## 2. Install the zips

The Daz Install Manager zips are named like
`IM00086958-01_Genesis9StarterEssentials1Of3.zip`. Dry-run first, then install:

```sh
python3 scripts/daz_library.py install ~/Downloads/IM00086958-0?_*.zip --dry-run
python3 scripts/daz_library.py install ~/Downloads/IM00086958-0?_*.zip --eula-read YYYY-MM-DD
python3 scripts/daz_library.py verify 86958 --crc
python3 scripts/daz_library.py licence 86958
```

- **`--eula-read` only with the date the user gave.** Never invent one; without
  it `list` shows `EULA last read: not recorded`. Add it later with
  `licence 86958 --eula-read YYYY-MM-DD`.
- **`--interactive-license` only when they say they bought one** for this
  product. The script cannot check a purchase. `licence 86958
  --standard-license` takes a mistaken flag back off.
- The dry run takes no lock and writes nothing. If it exits non-zero, show why
  and stop. Against the installed library all three parts' 4528, 197 and 1780
  files were identical, in 6.84 s wall.
- Installing all three into an empty library took 7.59 s and 6.90 s wall
  (6499 files, 2452887819 bytes), measured before the script's last review
  fixes. After them, part 03 alone into an empty library took 0.89 s wall,
  and `verify 86958 --crc` passed 6499 of 6499 in 0.51 to 0.93 s.
- Only the files `Manifest.dsx` lists for Content are extracted, so `data/`,
  `People/` and `Runtime/` land at the library root. The record, with the
  licence held, is `<library>/.daz_library/86958.json`.

| Exit | Means | Do |
|---|---|---|
| 0 | done | show the result and the `licence` output |
| 1 | a conflict, a skipped or partial package, or a `verify` finding | show the lines. Install the same zips again to finish a partial part. `--overwrite` replaces files whose bytes differ, only when the user asks |
| 2 | a refused path, name, package, library or argument, or the lock held | show the refusal; nothing was installed. For `another daz_library.py is changing <library>; wait for it to finish`, wait |
| 130, 143, 129 | stopped by SIGINT, SIGTERM or SIGHUP | the files placed are recorded as incomplete; install again to finish |

What the library holds, without Blender, from the path `list` printed:
`python3 scripts/daz_inventory.py /models/daz_library --brief`. On SKU 86958
it exited 0 in 2.8 s with 51 figure files: 1 body (`Genesis9.dsf`, 25182
vertices, 138 bones, 1114 morphs), 31 attachments and 19 other geometry.

Show `list` and `licence`, and ask: **build the figure** or **stop**.

## 3. Fetch the importer and build

```sh
python3 scripts/daz_import_probe.py fetch
python3 scripts/daz_import_probe.py build --facs --subdivision off --out output/daz/g9_cage.blend
python3 scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend --motion-only
```

- `fetch` downloads Diffeomorphic's import_daz 5.2.0 from GitHub, pinned at
  1697629 bytes and a sha256, and unpacks its 296 files into the gitignored
  `input/_devtools/import_daz/`. The code is GPL-2.0-or-later, run and never
  copied into the repo.
- `build` imports `People/Genesis 9/Genesis 9.duf`, then the Eyes, Mouth,
  Eyelashes, Tear and eyebrow figures that its Daz Studio post-load script
  names, merges their rigs and runs `import_facs`. Measured: exit 0, 5.7 s
  wall, peak 711 MiB, 5 Subsurf modifiers switched off.
- **`--facs`, not `--visemes`.** On Genesis 9 `import_visemes` loads 0 morphs
  and reports no error, so a build with `--visemes` exits 1 by design. The 17
  visemes arrive through `import_facs` as the rig properties `facs_ctrl_vAA` to
  `facs_ctrl_vW`.
- **`--subdivision off`.** The importer saves Subsurf at up to level 3 for
  render, which multiplies every render's time (step 9).
- `--figure` takes another `.duf` relative to the library, with no `..` part,
  such as `"People/Genesis 9/Characters/Kat for Genesis 9.duf"`, and
  `--no-textures` removes its images before saving.
- **The build fills in the anatomy materials, and says what it filled in.** A
  Genesis 9 eyelash, eye, mouth or eyebrow figure arrives with no map at all,
  and without this an eyelash card renders as an opaque fan across the eyelid.
  `build` and `scene` apply the MAT presets that sit beside the figure and
  beside each anatomy file, and only fill in what a material is missing. On Kat
  that is 16 of 16 materials and 18 images becoming 29. `--mat-preset FILE`
  names one, such as an eyebrow colour, and wins over the ones found by
  looking; `--no-auto-materials` goes back to bare materials. Measured on
  2026-09-21 on one mesh at 512 px in Cycles: the eyelashes went from 11,801
  opaque pixels to 1,848, the eyebrow cards from 9,981 to 4,664
  (docs/guide/daz-figures.md).
- `--motion-only` renders nothing: 0.6 s in Blender, 3.8 s for the command. It
  opens the `.blend` with no DAZ add-on and auto-run scripts off, and writes
  `g9_cage_motion.json`.

Read `output/daz/g9_cage_build.json` and `g9_cage_motion.json`, and say:

- `failures` (empty on the measured build) and the 17 names in `viseme_props`.
- The rig: 177 bones on the measured build, 143 of Daz's and 34 "(drv)"
  helpers the importer adds.
- What the visemes move. On the measured build AA moved 2880 body vertices up
  to 7.8 mm; over the 17 the body moved 1419 (T) to 3494 (EE) vertices, and M
  moved shape keys but no bone. If every viseme moves 0 vertices, stop and
  show the build report; do not render.

A wrong content path raises nothing: the import makes no object, and the step's
message is `Some assets were not found. Check that all DAZ root paths have been
set up correctly.`. For `! run \`scripts/daz_import_probe.py fetch\` first` or
`! figure not found on the host: ...`, fix that and build again.

Ask: **a short render** (step 8), **morphs and sliders** (step 4), or **stop**.

## Stages 4 to 7: dialling, dressing and posing, without Daz Studio

Only if the user wants more than the plain figure. They are one subcommand,
`daz_import_probe.py scene`, and they run in this order in one Blender: morph
sets, then character dials, then FACS, then the wearables, then the pose. Doing
them stage by stage is for showing the user each result; when they already know
what they want, run one `scene` command with all of it (step 7).

- **Order matters.** `transfer_shapekeys` needs the body to carry shape keys,
  so a morph set has to be loaded before the wearables, or the step fails with
  `RuntimeError: Operator bpy.ops.daz.transfer_shapekeys.poll() failed, context
  is incorrect`.
- **Say the cost first**, as for a render. These are seconds, not minutes: the
  longest measured `scene` was 17.5 s wall.
- **Still only renders may ship.** A dressed, posed, dialled figure is more Daz
  3D data, not less (step 1).
- Each step writes `NAME.blend`, `NAME_scene.json`, `NAME_morphs.json`,
  `NAME_build.json`, `NAME_blender.log` and `NAME_poses.json` to `output/daz/`.
  Read the JSON; never open the `.blend`.

## 4. Morph sets and the sliders they add

```sh
python3 scripts/daz_import_probe.py scene --out output/daz/g9_morphs.blend \
    --anatomy none --morphs body,jcms,flexions --subdivision off
```

Measured on 2026-09-18: all eleven sets plus six character dials and two
sliders took 5.0 s wall, 4.86 s in Blender, peak 642.0 MB, container 2.76 to
3.19 GiB. Per set, properties added to the rig object and its data, and body
shape keys: `body` 102 + 251 with 5 keys in 0.19 s, `jcms` 116 + 122 with 103
in 0.36 s, `flexions` 27 + 27 with 14, `masculine` 13 + 13 with 11, `feminine`
11 + 11 with 9, `powerpose` 88 + 92 with 52 in 1.24 s.

- **`units`, `expressions`, `visemes`, `head` and `facsexpr` add nothing** on
  Genesis 9: the importer has no table for them. Do not offer them. The visemes
  come from `--facs`, as in step 3.
- **Ask for what is wanted, not all eleven.** `body,jcms,flexions` is what the
  measured dressed build used.
- Read `NAME_morphs.json`: every numeric property with its range. The measured
  run left 1593 of them, 444 on the rig object and 1149 on its data. The Daz
  limits are the soft range, so `Kat_figure_ctrl_Character` reads 0.0 to 1.0;
  862 of the 1593 have no soft range, being the `(fin)` and `(rst)` twins and
  the correctives.
- `--set NAME=VALUE` sets a dial and measures it. Measured:
  `Kat_figure_ctrl_Character` at 1.0 moved all 25,182 body vertices by up to
  59.67 mm; `body_bs_ProportionHeight` at 1.0 moved 22,292 by up to 14.0 mm.
  The first of those is a character dial, which needs the custom morphs of
  step 5 in the same command. If a `--set` moves 0 vertices, the property name
  is wrong: show the names from `NAME_morphs.json`.

Ask: **a character preset** (step 5), **a render** (step 8), or **stop**.

## 5. A character preset

```sh
python3 scripts/daz_import_probe.py build \
    --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf" \
    --out output/daz/g9_char_kat.blend
```

The product ships six presets under `People/Genesis 9/Characters`. Measured on
2026-09-18 on Kat with that command, against the plain figure built the same
way: 4.7 s wall against 1.4 s, 158
bones against 157, 47 + 64 properties against 2 + 4, 90 drivers against 23, the
same 25,182 body vertices but with 40 shape keys against none, and 18 images
against 2. Those were measured before the build filled in the anatomy
materials: the same Kat build on 2026-09-21 took 4.2 s and saved 29 images,
because the eyelash, eyebrow, eye and mouth maps are now loaded (step 3).

- **The six shape dials in `Base Characters 9` are not in any preset's set.**
  They load only through `scene --custom-morphs "data/Daz 3D/Genesis 9/Base/
  Morphs/Daz 3D/Base Characters 9" --custom-files <name>.dsf --custom-category
  Characters --custom-bodypart Body`. All six took 1.43 s and added 86 + 630
  properties. Each call leaves `get_error_message()` reading `Found morphs that
  want to change the rest pose.`, which is expected.
- **`--no-textures` does not save memory during the import** (it still peaked
  at 1454.3 MB), only at render time (step 9).
- **Add `--facs` if the figure is to talk**, so `render --blend` has its
  visemes, and `--subdivision off` before a render, so the importer's own
  Subsurf levels do not cost a cell about 238 s (step 9). Neither was in the
  run the numbers above come from, and `--facs` adds its own time, properties,
  drivers and shape keys, so quoting those numbers for a `--facs` build would
  be wrong.

Ask: **an outfit and hair** (step 6), **a render** (step 8), or **stop**.

## 6. An outfit and hair

```sh
python3 scripts/daz_import_probe.py scene --out output/daz/g9_outfit.blend \
    --anatomy none --morphs body,jcms \
    --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shirt.duf" \
    --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shorts.duf" \
    --wear "People/Genesis 9/Hair/Daz Originals/Base Hair/G9 Base dForce Pixie Hair.duf" \
    --skip-transfer "dForce Pixie Cut Mesh,dForce Pixie Hair Cap Mesh" --subdivision off
```

The product ships 40 clothing and 27 hair `.duf` files. The run that measured
this on 2026-09-18 was that command with the `Kat_figure_ctrl_Character` dial
loaded (`--custom-morphs "..." --custom-files Kat_figure_ctrl_Character.dsf
--custom-category Characters --custom-bodypart Body`, step 5), set with
`--set-dressed Kat_figure_ctrl_Character=1.0`, and step 7's walking pose
applied, all into `g9_outfit.blend`: 5.2 s wall and a peak of 998.4 MB for the
whole of it, not for the wearables alone. Each wearable
arrives with its own armature (shirt 126 bones, shorts 126, hair cap 51) and is
merged into the body rig, which stayed at 233 bones, with its own vertex groups
kept.

**Say these two limits before running it**, because they are what the user will
notice:

- **An outfit does not take a character's shape.** The route that would fit it
  needs a `.dbz` exported from Daz Studio, one per `.duf`, which this host
  cannot make: `scene --fit DBZFILE` exits 1 with `Mesh fitting set to DBZ
  (JSON). Export "..." from Daz Studio to fit to dbz file.` On the route it uses
  instead,
  `transfer_shapekeys` returned `FINISHED` and added 0 shape keys to the
  clothes, so setting a character dial moved every shirt and shorts vertex by
  the same 57.25 mm, a rigid follow, while the body reshaped by up to 66.21 mm.
- **Strand hair follows nothing and draws nothing.** `dForce Pixie Cut Mesh`,
  236,136 vertices, has one vertex group, `dForce Pin`, a simulation group with
  no bone, so a pose moves 0 of its vertices, and deleting it changed 0 of a
  340 px render's 231,200 pixels. Pass such meshes to `--skip-transfer`. Only
  the 1085-vertex hair cap shows.

Ask: **a pose** (step 7), **a render** (step 8), or **stop**.

## 7. A pose, and the whole thing in one command

```sh
python3 scripts/daz_import_probe.py scene --out output/daz/g9_dressed.blend \
    --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf" \
    --morphs body,jcms,flexions --facs \
    --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shirt.duf" \
    --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shorts.duf" \
    --wear "People/Genesis 9/Hair/Daz Originals/Base Hair/G9 Base dForce Pixie Hair.duf" \
    --skip-transfer "dForce Pixie Cut Mesh,dForce Pixie Hair Cap Mesh" \
    --pose "People/Genesis 9/Poses/Daz Originals/Base Poses/Base/G9 Base Pose 13 Walking G9B.duf"
```

The product ships 87 pose `.duf` files. Measured on 2026-09-18 by that command
on the walking pose: 48 of its 258 pose bones moved, 50 carrying a rotation
once the drivers had run, no f-curve written, the body moving up to 765.45 mm,
the shirt 211.78, the shorts 211.79 and the hair cap 182.41. The whole command
took 17.5 s wall, peak 1643.7 MB, container 2.29 to 3.59 GiB, for a
140,971,653 byte `.blend` of 258 bones. The same pose on the lighter
`g9_outfit.blend` of step 6 moved 48 of 233 bones, the body 801.24 mm, the
shirt 214.70, the shorts 214.97 and the hair cap 180.89.

- **The probe passes `affectMorphs=False`.** The operator's own default is
  `True`, which zeroes every dial on the figure; the first measured run lost its
  character that way. `--pose-affects-morphs` asks for the old behaviour, and is
  only for resetting a figure on purpose.
- **`scene` checks its own work.** Unless `--no-verify`, it reopens the saved
  file in a Blender with no DAZ add-on and auto-run scripts off. On the measured
  outfit build, 0.8 s: 233 bones, 88 posed, 618 drivers and the dial still 1.0,
  and clearing the pose moved the body 801.24 mm. Say those numbers: they are
  what proves the file needs no add-on. `verify --blend output/daz/NAME.blend`
  runs it again on its own.
- Read `NAME_scene.json` and say `failures` (empty on the measured builds), the
  bone count, and what each stage moved in millimetres.

Ask: **a render** (step 8) or **stop**.

## 8. A short render, for the user to look at

Say the cost first. Measured on 2026-09-16 on the cage build, llvmpipe, with
no other job in the container:

| Render | Cells | Time | Peak memory |
|---|---|---|---|
| `--only AA --sizes 128 --columns face --samples 16` | `render_sheet.py` 2 rows, then the probe 2 | 28.9 s, then 17.7 s | 2709 MiB, the probe |
| the default: all 17, three framings at 128, 220 and 340 px, 64 samples | `render_sheet.py` 18 rows, then the probe 162 | 184.3 s, then 1287.6 s: about 25 min | 3401 MiB, the probe; container 4.54 to 7.67 GiB |

The default row was measured with the script before its last changes, which
render the same rows for this file; it was not run again.

On a dressed, posed figure, measured on 2026-09-18 from
`output/daz/g9_dressed.blend`: 2 face cells at 128 px and 16 samples in 20.0 s,
container peak 5.50 GiB. A four-facing sheet through `render_sheet.py` in clay
took 45.5 s at 128 px and 47.7 s at 220 px for 4 cells. With the imported
materials that same sheet did not finish one cell in 1500 s and was ended by
its alarm: that run took the EEVEE default of 64 samples, which came to 26.2 s
a sample here. The probe's own renderer takes `--samples`, and
2 portrait cells at 340 px and 16 samples cost 479.0 s with materials against
18.8 s in clay. Offer clay first, and never start a materials sheet at the
default 64 without saying it is hours. Lowering `--samples`, and
`render_sheet.py`'s own Cycles default, which path traces on the card rather
than on the CPU, are both untried on this figure, so do not promise a time for
either. A sheet asked for outside the probe, by running `render_sheet.py`
directly on a Genesis `.blend`, takes Cycles now and will not match the EEVEE
sheets in `output/daz/`.

```sh
python3 scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend \
    --only AA --sizes 128 --columns face --samples 16
```

It writes `g9_cage_AA_128_face_s16_render.json`, `_render_sheet_128.png`,
`_sheet_128.png` and `_sheet_128_labelled.png` in `output/daz/`. The label in
the name keeps a short run from overwriting a full one.

**Have the user open `output/daz/g9_cage_AA_128_face_s16_sheet_128_labelled.png`**,
and do not read it yourself (step 1). Ask: is the face in frame, and does the
AA row differ from the neutral row? Beside their answer, give the counts from
`g9_cage_AA_128_face_s16_render.json`: the probe's under
`probe_render.sizes["128"].face.visemes.AA.changed_px`, and `render_sheet.py`'s
whole figure in its `--check` line in `render_sheet.output_tail`. On the
measured build AA changed 210 pixels in the face framing and 1 on the whole
figure. If the face framing changed 0, nothing moved: stop and show the build
report.

Ask: **the full run** (about 25 min of CPU in the shared container) or
**stop**.

## 9. The full run, and what reads

```sh
python3 scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend
```

- **Exit 1 is expected here.** `render_sheet.py`'s `--check` calls a row with
  no pixel changed by 8 levels or more the rest pose repeated, and on the cage's
  whole figure it named IH, K, L, S, T, TH and W. The probe's own sheets are
  still written. Say which rows it named.
- **These cost more; say so before using them.** `--subdivision as-saved`: 2
  face cells at 128 px and 16 samples took 88.7 s and 4593 MiB, against 17.9 s
  and 2655 MiB with it off, and a whole-figure cell took about 238 s at 64
  samples with an earlier version, so 18 rows would pass the 3600 s timeout.
  `--materials` on Kat, whose
  preset references 26 texture maps, 4 of them 8192 px: 2 face cells at 340 px
  and 16 samples took 81.9 s and 6312 MiB, container up to 10.63 GiB, and
  27.7 s and 2836 MiB from a `--no-textures` build.

**Have the user open `output/daz/g9_cage_sheet_340_labelled.png`** and say,
viseme by viseme, which read as their sound and which look alike; do not read it
yourself (step 1). Give each viseme's count from `g9_cage_render.json`, under
`probe_render.sizes["340"].face.visemes`, fewest to most. For comparison, an
earlier reading of the measured cage, made by Claude on a crop of the 340 px
face column: OW and UW read as rounded mouths, EH and ER open with teeth, EE and
IY as teeth behind parted lips, and M as pressed lips; F, K, L, S, T, TH, IH and
W looked like one slightly parted mouth, and AA opened less than OW. Pixels
changed against the neutral row on that run, fewest to most:

| Framing | 128 px | 220 px | 340 px |
|---|---|---|---|
| body | 0 to 4 | 2 to 12 | 9 to 27 |
| face | 67 to 258 | 213 to 791 | 533 to 1873 |
| face34 | 87 to 253 | 238 to 704 | 537 to 1559 |

Ask: **keep a sheet**, **render another figure or framing**, or **done**.

## 9b. A roster of characters, front and side

When the user wants several characters rather than one figure, this does the
whole loop per character: roll, build, render, write it down.

```sh
python3 scripts/daz_characters.py list                      # what the library offers
python3 scripts/daz_characters.py make --count 12 --seed 20260921 --dry-run
python3 scripts/daz_characters.py make --count 12 --seed 20260921 --size 768
```

- **Show the dry run first and get an answer.** It prints each character's
  base, hair, beard, outfit, weapon and pose, and builds nothing.
- **Say the cost.** Measured on 2026-09-21 on twelve characters at 768 px:
  13.3 to 23.1 s to build each one and 2.1 to 3.9 s to draw its two views,
  230.6 s and 34.3 s over the twelve, and 6.2 MB kept once each `.blend` was
  deleted.
- Every slot comes from the library, one figure generation at a time, so a
  Genesis 8 hair is never put on a Genesis 9 figure. The same seed and library
  give the same twelve.
- Each character keeps `<slug>_front.png`, `<slug>_side.png`, `<slug>.json`
  with the roll and the two commands that rebuild it, the probe's
  `<slug>_scene.json`, and two logs. `characters.json` indexes the run and
  `contact_sheet.png` puts every front view on one page. The `.blend` is
  deleted unless `--keep-blend`.
- **Have the user open `output/daz/characters/contact_sheet.png`**; do not read
  it yourself (step 1). Ask whether the armour clips, whether the hair reads as
  hair and whether a weapon sits in the hand. Beside their answer, give the
  `drawn_px` of each view from its JSON.
- What it does not do: it never rolls a hair or clothing colour, because those
  materials already carry their maps and the material pass only fills in what
  is missing; a weapon arrives in the hand with the fingers open, because the
  grip pose is a second pose file and only one pose is applied.

## 10. Where things are, and what may leave

```
MODELS_DIR/daz_library/              the content library, outside the repo
  .daz_library/86958.json            what was installed, and the licence held
input/_devtools/import_daz/          the importer, gitignored
output/daz/                          Daz content: gitignored, never committed
  characters/<slug>/                 a rolled character: two views, its JSON,
                                     its scene report and two logs
  characters/characters.json         the run's index
  characters/contact_sheet.png       every front view on one page
  g9_cage.blend                      70928008 bytes
  g9_cage_build.json, _blender.log, _poses.json, _motion.json
  g9_cage[_<label>]_render.json, _render_sheet_128.png,
  g9_cage[_<label>]_sheet_<size>.png and _labelled.png
  g9_dressed.blend                   140971653 bytes, dialled, dressed, posed
  g9_dressed_scene.json, _morphs.json, _build.json, _blender.log, _poses.json
```

A dressed `.blend` is 141 MB against the plain figure's 71 MB, and every one
stays in `output/daz/`. Say so before building several.

- **Everything in `output/daz/` is Daz content.** The `.blend`, logs and
  reports never leave this machine. `render_sheet.py`'s cells pass through
  `output/_sheet_frames/` and are deleted.
- **A sheet to keep as a sprite:** `scripts/cleanup.py keep NAME --concept
  output/daz/<render>.png --sheets output/daz/<sheet>.png`. `keep` takes only
  images and videos from `output/daz/`, only as `--concept` or `--sheets`, and
  prints a note to keep them out of the AI stages and any training.
- **`output/daz/` is not a protected folder.** `scripts/cleanup.py sweep
  --delete --unclaimed` deletes it, `.blend` files included. Say so before any
  sweep.

When it is done, say what may ship: rendered sheets and portraits, on the
conditions in step 1. The `.blend` and anything exported from it may not ship
without an Interactive License for each product, and then only on the four
conditions in step 1. That is as true of a figure you dialled, dressed and
posed yourself as of the plain one: the character shape, the outfit, the hair
and the pose are all Daz content, and each product used needs its own licence.
The library's native Daz files never ship.
