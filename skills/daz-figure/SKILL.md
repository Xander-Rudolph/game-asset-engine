---
name: daz-figure
description: Install a Daz 3D product the user downloaded, import its Genesis figure into Blender and render its visemes, within the Daz licence. Use when the user says "I downloaded Genesis 9 from Daz", "import a Daz figure into Blender" or "render a Genesis character's visemes", or has Daz Install Manager zips. Renders may ship; the 3D data needs an Interactive License.
---

# Daz figure: a Genesis figure in Blender, rendered, never shipped as 3D

Work in the asset-engine repo root. The long version, with every measurement
and what failed on the way, is `docs/guide/daz-figures.md`. The licence, read
from Daz's own pages, is in `docs/reference/daz-genesis.md`, "Licences" and
"What not to do".

Everything below was measured on 2026-09-16 on one product, Genesis 9 Starter
Essentials (SKU 86958): the library scripts on the host's `python3`, the
importer and the renders in the container's `bpy` 4.5.9, whose EEVEE draws
through llvmpipe on the CPU, not on the card. Genesis 8, 8.1 and other
products were never run.

**One stage per turn.** The licence, the install, the build, the renders. Show
each result and get an answer before the next. If you run two stages without
asking, that is a bug.

## First, is this the right route?

Ask what the user wants to end up with.

- **A 3D character in their game**, as a mesh, rig or exported FBX or glTF.
  Say first that the 3D data needs an Interactive License for each product,
  with conditions (step 1). With none, offer MakeHuman through MPFB2, whose
  bundled assets and face packs are CC0 (`docs/reference/daz-genesis.md`,
  "MakeHuman and MPFB2", built with `scripts/mpfb_probe.py`).
- **Sprites or portraits rendered from a Genesis figure.** This skill.
- **A talking dialogue portrait from a Genesis render.** Not through the
  `lip-sync` skill: its portrait and mouths are Qwen-Image edits, an AI stage
  a Daz render must stay out of (step 1).
- **A face that reads on a sprite.** On the whole figure at 128 px each viseme
  changed 0 to 4 pixels; in a face framing at 340 px, 533 to 1873 (step 5).
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
- **Say the cost before every render** (steps 4 and 5). Start short.
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
  render, which multiplies every render's time (step 5).
- `--figure` takes another `.duf` relative to the library, with no `..` part,
  such as `"People/Genesis 9/Characters/Kat for Genesis 9.duf"`, and
  `--no-textures` removes its images before saving.
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

Ask: **a short render** or **stop**.

## 4. A short render, for the user to look at

Say the cost first. Measured on 2026-09-16 on the cage build, llvmpipe, with
no other job in the container:

| Render | Cells | Time | Peak memory |
|---|---|---|---|
| `--only AA --sizes 128 --columns face --samples 16` | `render_sheet.py` 2 rows, then the probe 2 | 28.9 s, then 17.7 s | 2709 MiB, the probe |
| the default: all 17, three framings at 128, 220 and 340 px, 64 samples | `render_sheet.py` 18 rows, then the probe 162 | 184.3 s, then 1287.6 s: about 25 min | 3401 MiB, the probe; container 4.54 to 7.67 GiB |

The default row was measured with the script before its last changes, which
render the same rows for this file; it was not run again.

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

## 5. The full run, and what reads

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

## 6. Where things are, and what may leave

```
MODELS_DIR/daz_library/              the content library, outside the repo
  .daz_library/86958.json            what was installed, and the licence held
input/_devtools/import_daz/          the importer, gitignored
output/daz/                          Daz content: gitignored, never committed
  g9_cage.blend                      70928008 bytes
  g9_cage_build.json, _blender.log, _poses.json, _motion.json
  g9_cage[_<label>]_render.json, _render_sheet_128.png,
  g9_cage[_<label>]_sheet_<size>.png and _labelled.png
```

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
conditions in step 1. The library's native Daz files never ship.
