# Scripts

Everything in `scripts/`. Each takes `--help`.

## Setup and health

| Script | Does |
|---|---|
| `doctor.py` | Checks the whole stack and prints the one next step. `--fix` does the safe repairs. `--json` for tooling. |
| `setup.sh` | Clone nodes, seed, fetch weights, build, start, post install. Safe to re-run. |
| `fetch_models.py` | Check or download model weights by group. Stdlib only. |
| `fetch_tools.py` | Check or download the command-line tools that `tools.json` pins by URL, byte size and sha256, into the gitignored `tools/`. Stdlib only, on the host. Only the files an entry's `keep` list names are unpacked, and a short download keeps its `.part` for the next `--download` to resume. `--licenses` prints each tool's licence, and `--path NAME` prints a binary's path for other scripts. Rhubarb Lip Sync 1.14.0 is the only entry so far. |
| `postinstall.sh` | Node installs that have to happen inside the running container. |
| `patch_nodes.py` | Compatibility patches to the cloned node sources. `--check` verifies them. |
| `entrypoint.sh` | Container entrypoint. Seeds empty mounts, reports missing weights before starting. |
| `publish_image.sh` | Build and push the image to a registry. Local build on purpose, it is 27.6GB. |

## Running the pipeline

| Script | Does |
|---|---|
| `run_workflow.py` | Queue a graph, wait, report the outputs. On a preset, `--subject` fills only the SUBJECT slot and keeps the house technique, which `--prompt` would replace. `--free`, `--interrupt PROMPT_ID` and `--delete PROMPT_ID` manage the queue, and refuse to touch a job that is not the one named. |
| `validate_workflows.py` | Check every graph against a live server's node definitions. |
| `api_to_ui.py` | Convert graphs into the editor's format. `--check` verifies every value survived. |
| `build_presets.py` | Generate the drop in presets from base graphs plus the prompt library. |
| `generate_concepts.sh` | Generate a whole prompt folder in the house style. |
| `simplify_concepts.sh` | Redraw existing art as simpler game ready versions. |
| `asset_to_mesh.sh` | Concepts to shapes to textures to sheets to curated assets, correctly staged. |
| `rig_units.sh` | Rig figures one at a time, with the settings that work. |
| `make_hair.py` | Lay out a head of hair the repo owns: Poisson roots on a scalp cap, a whorl, a parting, cluster guides, and four layers of guide curves over a cap mesh with its own maps, written as an atlas plan, a numpy fallback OBJ and a preview, then handed to `bake_hair.py`. Styles, looks and colours are presets over flags. See [below](#make-hair-py). |
| `bake_hair.py` | Sweep `make_hair.py`'s guides into closed lens shells and flat cards in the container's Blender, render the atlas from real strands, set the normals, and write one OBJ that `daz_import_probe.py scene --wear-obj` places. See [below](#bake-hair-py). |
| `make_scalp.py` | Paint a scalp texture for `make_hair.py --cap-diffuse` with the repo's ComfyUI text-to-image graph: one job, made to tile, tinted to a hair colour, with a JSON of the prompt, seed and seam check. See [below](#make-scalp-py). |
| `list_animations.py` | What animation clips are actually installed, read from the files. |
| `bone_roles.py` | Name an articulationxl rig's `bone_N` bones by role (pelvis, chest, head, left thigh and so on) with `map`, then `compile` a role pose from `poses/roles/` into that rig's transforms file for `render_sheet.py`. `probe` says which way each part moved. See [below](#bone-roles-py). |
| `generate_music.py` | Generate a folder of music prompts with ACE-Step 1.5. `--loop DIR` makes each take a seamless loop, and `--keep-best` keeps the take that loops best. Resumable: seeds already in `DIR/picks.json` are skipped, and `--reloop` loops the recorded takes again without generating. A take the server already made, for a run that died, is used rather than made again, and `--no-wait` queues the missing takes and exits. A track file can carry a section script as its lyrics, after a line of `---`. |

## Looking at results

| Script | Does |
|---|---|
| `render_sheet.py` | Render a model to a sprite sheet. Angles across, poses down. `--span` and `--look-at` frame a fixed world box at a fixed height, for a set that must share a scale or for a head rather than a whole figure. |
| `decimation_report.py` | Measure what each face budget costs, three ways, or bisect for an answer. |
| `sheet_check.py` | Check a sprite sheet for the faults that are arithmetic. Exits non-zero on a fault. |
| `transfer_weights.py` | Move a skeleton from a decimated proxy onto the original mesh. |
| `normalise_mesh.py` | Scale a mesh to a declared world size and record the rule. `--check` gates a whole folder. |
| `make_seamless.py` | Make a texture tile, and say whether it worked. |
| `cut_icon.py` | Cut an icon out of its background and size it for a UI. |
| `make_loop.py` | Make a music track loop without a seam at a set loudness: it chooses where in the take the loop starts and ends, keeps any silence in the take out of the loop, and reports what you would hear where it comes round. |
| `cleanup.py` | Curate the keepers, then sweep the rest. Folders `keep` cannot claim, such as music takes, icons and mouth sets, are protected from the sweep. `keep --generator --source --licence --licence-url` records provenance rows in `sources.json`. `keep` refuses Daz 3D data, and keeps only renders from `output/daz/` ([below](#cleanup-py)). |

## Faces and lip sync

What these are for, and what was measured, is in [lip sync and talking portraits](/reference/lip-sync).

| Script | Does |
|---|---|
| `lipsync_cues.py` | Mouth cues for voice lines. Runs Rhubarb Lip Sync from `tools/` on the host, refuses a line that fails its speech gate, and writes a timeline JSON to `output/lipsync/`. `--fps N` adds one mouth shape per frame, and `--text-only` writes a placeholder flap for a line with no voice yet. Needs ffmpeg. See [below](#lipsync-cues-py). |
| `make_mouths.py` | Make a talking portrait from a concept with `--portrait-from`, then, once it is approved and the mouth box chosen, one whole-image edit per mouth shape through `img_edit_qwen.json`, and compose them. Before every edit it waits until no Blender job is running and the ComfyUI queue is empty. The box is checked before any edit is queued, and a shape whose edit exists is skipped, so a stopped run resumes. |
| `compose_mouths.py` | Cut the mouth box out of each edit into `mouth_<S>.png` overlays and a `manifest.json`, and measure drift in a ring round the box. `--check MANIFEST` fails unless no pixel outside the box changes, every size matches and A to F are present. `--selftest` rechecks the 33 measured sizes in the script's `PROBED` table and composes a set from made-up pixels, so it needs no pictures and no GPU. Host, numpy and Pillow. |
| `preview_lipsync.py` | Play a mouth set against a timeline as an MP4, with the line's audio when there is some, and lay the mouths out on a labelled contact sheet. A shape the set lacks plays Rhubarb's fallback. Needs ffmpeg and ffprobe. |
| `face_rig.py` | Give a rig a face in Blender. `add-jaw` adds a jaw bone under the head, weighted by rule, turns it 20 degrees as a check, and writes nothing when that barely moves the mesh. `transfer-shapes` copies a template head's shape keys onto a model with Surface Deform, and `spheres` writes the test files the method was proved on. A generated mesh has no parted lips, so the jaw stretches the lower face rather than opening a mouth. |
| `mpfb_probe.py` | Probe MPFB 2, MakeHuman's Blender add-on, in the container's Blender. `fetch` downloads the add-on and three face packs, pinned by size and sha256, into the gitignored `input/_devtools/mpfb2/`. `build` makes a body with the 15 Meta/Oculus-style visemes as shape keys, as a `.blend` and a `.glb` in `output/mpfb/`, and `render` draws one viseme per row. `--help` records the licences as read and what was measured. |

## Daz figures

What these are for, and what was measured, is in the [Daz figures](/guide/daz-figures)
guide, and the licence that limits what may ship is in
[DAZ Genesis](/reference/daz-genesis#licences). `daz_library.py` writes the
library outside the repo, and `daz_import_probe.py` writes everything it makes
from Daz content to the gitignored `output/daz/`. None of it may be committed.

| Script | Does |
|---|---|
| `daz_library.py` | Install content zips downloaded by hand into a content library outside the repo, `MODELS_DIR/daz_library` by default, and record every file with its CRC-32, and the licence held with the date you read the EULA. Every path is checked before anything is written. `intake` does that for every zip in a folder, verifies what landed, deletes each zip and keeps a Markdown ledger beside them. `list`, `licence`, `verify`, `uninstall`, `case-check` and a `selftest` with invented packages. Standard library only, on the host. See [below](#daz-library-py). |
| `daz_import_probe.py` | Import a Genesis figure into the container's Blender with the Diffeomorphic DAZ Importer, which `fetch` pins by size and sha256 into the gitignored `input/_devtools/import_daz/`. `build` saves a `.blend` whose 17 viseme controllers come from FACS, `scene` adds morph sets, character shape dials, sliders, clothing and hair merged into the figure's rig and a pose preset, `verify` reopens a saved `.blend` with no add-on, and `render` draws a row per viseme with `render_sheet.py` and in three framings of its own, or measures what each moves with `--motion-only`. See [below](#daz-import-probe-py). |
| `daz_characters.py` | Roll random Genesis characters from whatever the Daz library holds, build each one in the container's Blender through `daz_import_probe.py`, render it front and side with `render_sheet.py`, and write a JSON beside its two images holding the roll, the two commands that rebuild it and what was drawn. `list` prints what the library offers for each slot. The `.blend` is deleted once the views are drawn. See [below](#daz-characters-py). |
| `daz_inventory.py` | List the figures, bones, morphs, aliases and HD morphs in a Daz content library outside this repo, reading every `.dsf` with the standard library. Figures are grouped by the content type their author set, aliases and other modifiers are counted apart from morphs, and a valid JSON file that is not DSON is skipped, not an error. It refuses a path in or above the repo. See [below](#daz-inventory-py). |

## Keeping the repo honest

Run both before a commit, with `npm run docs:build`.

| Script | Does |
|---|---|
| `check_docs_sync.py` | Fails when a skill, graph or script is missing from a table or count that lists it: the README, the Claude guide, the skills and workflows references, this page and the editor-graph notes. `--untracked` also counts files git does not track yet. |
| `check_vendored_licences.py` | Fails when a tracked file outside `docs/` and `research/` carries a sign of pasted licence-restricted content, such as a Valve or Daz copyright line or the body of a GPL or share-alike licence. `--markers` lists what it looks for and why. |

## The ones worth reading before using

### `render_sheet.py`

```sh
scripts/render_sheet.py MODEL [--poses SPEC] [--angles N] [--azimuth-start DEG]
                        [--azimuths DEG,DEG] [--elevation DEG] [--size PX]
                        [--zoom N] [--persp]
                        [--span UNITS] [--look-at UNITS] [--key N] [--ambient N]
                        [--engine {cycles,eevee}] [--samples N] [--denoise]
                        [--clay] [--clay-color R,G,B] [--flat] [--out PATH]
                        [--check] [--keep-frames] [--timeout SECONDS]
                        [--max-wait SECONDS] [--no-wait]
```

`--poses` takes `static`, `frames:1,7,13`, `even:N` or `transforms:FILE`.

`--angles N` spaces N facings evenly from `--azimuth-start`. `--azimuths` names
them instead, comma separated, for a set of facings that is not evenly spaced:
`--azimuths 0,90 --elevation 0` is the front and side a character reference
wants. It overrides `--angles`, `--azimuth-start` and `--flat`.

`--span <units>` frames against a fixed world height rather than the subject's
own extent, which is what makes a set share a scale. Without it each model is
framed to its own bounding box, so a wrong scale renders perfectly.

`--check` runs the [sheet checks](#sheet-check-py) on the finished sheet and
exits non-zero if one fails. It already knows the cell size and angles from the
run, so it also names the cell where the figure faces down and to the right.

`--timeout` gives up on Blender after that many seconds (default 1800), so a hung
render stops instead of waiting forever. The per-cell frames are deleted once the
sheet is put together. `--keep-frames` leaves them in `output/_sheet_frames/`.

Defaults are the isometric camera: elevation 30, first facing at 45 degrees,
orthographic. See [facings](/guide/facings).

**`--engine`, `--samples` and `--denoise`.** `--engine` picks Cycles, the
default since 2026-09-18, or EEVEE. `--samples N` sets the samples a cell gets,
and its default follows the engine: 128 for Cycles, where adaptive sampling
makes it a ceiling, and 64 for EEVEE, which is Blender's own and is left
untouched. `N` is checked on the host, before the
model loads, and refused unless it is a whole number from 1 to 16,777,216 for
Cycles or 2,147,483,647 for EEVEE, which are the engines' own limits on the
property in bpy 4.5.9:

```text
--samples is 0. Expected a whole number from 1 to 16777216, which is as far as Cycles counts samples in bpy 4.5.9. Leave --samples out for 128, this engine's default
```

`--denoise` is off by default and denoises a Cycles render with
OpenImageDenoise, on the CPU, because OptiX denoising needs driver libraries
this container has not. EEVEE has no denoiser, so under EEVEE the flag changes
nothing and says so rather than being ignored: `! --denoise is a Cycles option
and does nothing here: EEVEE has no denoiser, and this sheet renders exactly as
it would without it. Add --engine cycles to denoise.`

Cycles path traces on the card, because it needs no GL context. EEVEE
rasterises on the CPU through llvmpipe in this container, because the NVIDIA
runtime gives it no GL libraries, and that is why the default changed.
Measured on 2026-09-18 in `comfyui-packaged`, on the 16 cell sheet
`scripts/render_sheet.py output/assets/alchemist_warrior/rig.fbx --poses
transforms:output/poses/alchemist_warrior_walk.json --angles 4 --size 128`:
EEVEE, then the default, took 108.7 s wall and Cycles 3.12 s wall, which is
5.97 s against 0.138 s per 128 px cell at 128 samples. Cycles
took 1,531 MiB of the RTX 4070 Ti SUPER's 16,376 MiB while it ran (nvidia-smi
sampled every 0.1 s, 1,865 MiB in use on the card before it started) and less
host memory than EEVEE, 869 MB against 2,386 MB.

EEVEE at factory settings has no bounce lighting: `scene.eevee.use_raytracing`
is `False` out of the box (read from bpy 4.5.9 after
`wm.read_factory_settings`, 2026-09-18) and the script leaves it there, which is
why an EEVEE sheet comes out flat and even. Switching it on moves EEVEE towards
Cycles without landing on it: on the clay basilisk at 4 cells, 2026-09-18, the
lit surface went from 131.88 to 128.77 of 255, past Cycles' 129.92, for 40.10 s
against 34.42 s, while the mean absolute difference from Cycles rose from 3.39
to 4.03.

::: warning One engine for a whole set
The two are the same drawing with occlusion added, not the same pixels.
Measured on 2026-09-18: at sprite size 95 per cent of lit pixels move under 3.2
levels of 255, but Cycles separates a clay mesh's belly, the underside of its
jaw and the gap between its legs, an open viseme that moved a pixel 37 levels
under EEVEE moves it 89 under Cycles, and mixing engines across one figure puts
about 11 per cent of its lit pixels 10 or more levels apart. Two sheets drawn
by different engines will not sit beside each other on an atlas.

**Every sheet in this repo was drawn by EEVEE until the default changed on
2026-09-18**, so one of those re-rendered now will not match the rest of its
set. Re-render such a set whole
rather than topping it up, or pass `--engine eevee` to match what is already
there.

Which engine drew a sheet is not recorded in the PNG. It is in the RENDERED
json the Blender job prints, which the run reports as its `engine` line, either
`engine  Cycles on the GPU (<device>), 128 samples, not denoised` or
`engine  EEVEE Next, 64 samples`, along with the device, the sample count and
whether it was denoised.
The comparison behind the default is [two render engines](/guide/render-engines).
:::

**Waiting for the card.** A Cycles render, which since 2026-09-18 is what a
sheet is unless `--engine eevee` says otherwise, waits first: it polls every
30 s until
ComfyUI's queue is empty and no other `python3 -c` job runs in the container,
the same wait `scripts/make_mouths.py` does before an edit. Blender and ComfyUI
share one card: an image edit through `make_mouths.py` peaked at 15,178 to
15,344 MiB of the 16,376 MiB card on 2026-09-16 ([lip sync](/reference/lip-sync#tried-on-one-portrait)),
and a second job beside it ends in a CUDA out-of-memory error rather than a
fallback to the CPU. It prints each Blender job's pid and how long it has run
while it waits, stops without rendering after `--max-wait` seconds (default
7200), and stops at once when `docker top` or ComfyUI's queue cannot be read,
because a machine that cannot be seen is not an idle one. `--no-wait` skips the
wait. An EEVEE render never waits, because it never touches the card.

**A `.blend` as MODEL.** It is opened as saved rather than imported, because an
import keeps shape keys but not the drivers that connect rig properties to them.
Then the parts an import would not bring are set aside: the file's lights,
cameras and light probes are left out, its render, EEVEE and colour management
settings go back to the factory ones, its compositor and sequencer are switched
off, only the active view layer renders, and holdouts are cleared. An object is
neither framed nor rendered when it is hidden from render or from the camera, or
sits only in collections that are excluded or switched off for render. A file in
which nothing is left exits 1 with `no mesh in that file renders: each is hidden
from render or from the camera, or in a collection that is excluded or switched
off for render`. Measured on 2026-09-16: the walk sheet (`poses/walk.json` on
`output/assets/alchemist_warrior/rig.fbx`) rendered 0 pixels different from the
script before `.blend` input was added, and so did the same rig saved as a
`.blend` with its own lamp, camera, render settings and hidden objects. A `.blend`
that links objects from a library has not been tried. Opening a `.blend` runs its
Python-expression drivers, so treat one from someone else as code.

**`@shape_keys` and `@props`.** A `transforms:` pose may carry two reserved keys
beside its bones:

```json
[
  {},
  {"@shape_keys": {"jawOpen": 1.0}},
  {"@shape_keys": {"jawOpen": 0.4, "mouthFunnel": 0.8},
   "@props": {"mouth_open": 0.5},
   "jaw": {"rotate": [12, 0, 0]}}
]
```

- `@shape_keys` sets each named key on every rendered mesh that has one by that
  name. Every key starts each pose at 0, so no row inherits the one above it. A
  key with a driver follows its driver instead. Naming the reference key, usually
  `Basis`, does nothing and is reported.
- `@props` sets a custom property on the armature object, or on its armature
  data when the property lives there, and runs the drivers that read it. A
  property named in any pose starts each later pose at the value the file gave
  it. Properties on pose bones are not reached. A property an add-on saved can
  refuse a value of another type: on the MPFB human, a list for the float
  `MhScaleFactor` was refused with `Cannot assign a 'list' value to the existing
  'MhScaleFactor' Float IDProperty`, reported, and the sheet was still written.
- Unknown bones, shape keys and properties, and refused values, are printed and
  kept in the result.
- The framing is measured once, before the first pose, so a key that grows the
  mesh can reach the cell's edge: raise `--zoom`. A sphere with a `jawOpen` key
  touched its border in 4 cells at the default and passed `--check` at
  `--zoom 1.6` (128 px, 2026-09-16). `--check` compares silhouettes first, then
  pixels inside a matching silhouette: a row that changes only a face passes and
  names how many pixels changed per angle, and a row with no change of
  `--colour-levels` (default 8) or more is still the rest pose repeated.

**Pose checks.** A `transforms:` file is checked on the host before Blender
starts, and refused, naming the pose, when a pose is not a JSON object, a bone's
value is not an object, `rotate` or `translate` is not three finite numbers, a
shape key value is not a finite number from -10 to 10 (Blender's slider limits),
or a property is not a number, true or false, a string or a list of numbers.
JSON parsing accepts `NaN` and `Infinity`, and both are refused. For example:

```text
<file>: pose 1: bone 'jaw' holds a number. Expected an object such as {"rotate": [x, y, z]}
<file>: pose 1: shape key 'jawOpen' is 11. Expected a number from -10 to 10, Blender's slider limits
```

where `<file>` is the pose file's path.

The role files in `poses/roles/` carry `_note` strings, which this check refuses
(`bone '_note' holds a string`), so compile them with
[`bone_roles.py`](#bone-roles-py) rather than pass them to `--poses`.

#### Framing a head rather than a whole figure

`--span` fixes the frame's height in world units and `--look-at` fixes what it
points at, as a height above the model's own floor. Without the second, the
camera aims at half the frame: ask for a 0.42 m span on a 1.75 m figure and it
frames the knees. `--span 0.42 --look-at 1.60` is a head and shoulders on
Genesis 9 (measured 2026-09-22).

### `bone_roles.py`

```sh
scripts/bone_roles.py map RIG [--out ROLES_JSON] [--timeout SECONDS]
scripts/bone_roles.py compile ROLE_POSES ROLES_JSON_OR_RIG [--out TRANSFORMS_JSON]
                              [--timeout SECONDS]
scripts/bone_roles.py probe TRANSFORMS RIG [--frame N] [--all] [--json]
                            [--timeout SECONDS]
```

UniRig's articulationxl rigs call their bones `bone_0` to `bone_N`, and the count
and order change from figure to figure, so a pose file keyed on bone names fits
only the rig it was written for. `map` works out each bone's role from the
skeleton's geometry, with skin weights to settle which bone is the head, and
writes `output/rigged/<stem>.roles.json`. Pass `--out` for a rig saved as
`output/assets/<name>/rig.fbx`, or every asset's map lands on the same
`output/rigged/rig.roles.json`. [`poses/_bones.md`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/poses/_bones.md)
has the role tables for the test rigs.

`compile` turns one role pose file, such as `poses/roles/walk.json`, `attack.json`,
`hit.json` or `idle.json`, into a rig's own transforms file, by default
`output/poses/<rig>_<poses>.json`, for `render_sheet.py --poses transforms:`. It
takes a roles file or the rig itself, which it maps first without writing a
roles file. Rotations are degrees about the character's own axes: X to its
right, Y forward, Z up. They assume the arms hang at rest, as on articulationxl
rigs: on a T-pose Mixamo rig the walk's hand swing was 0.051 of the figure's
height, against 0.153 on `unit_warrior`.

- A role the rig lacks, and a `translate` on a bone connected to its parent,
  which Blender ignores, are dropped and listed, and compile exits 1 with the
  file still written, for example `! translate on a connected bone, which Blender
  ignores: chest (bone_2, frame 1)`. On the test rigs the pelvis, spine, neck,
  thighs and shoulders are never connected, so in practice translate the pelvis.
- `@shape_keys` and `@props` are copied through unchanged. Any other `@` key, a
  `rotate` or `translate` that is not three numbers, and invalid JSON are refused
  with one line naming the file, and the frame where there is one.
- A roles file from an older `map` is refused with `run map again`.

Measured on 2026-09-16 on five articulationxl rigs of 24, 28, 30, 30 and 47
bones: walk, attack, hit and idle compiled for each, and all 20 sheets rendered at
220 px passed `--check`. The posed armature matched what compile asked for to
within 1.44e-05. Mixamo and MPFB rigs have been mapped but not rendered, and feet
are not kept on the floor.

### `decimation_report.py`

```sh
scripts/decimation_report.py MODEL [--target-iou IOU] [--sweep] [--faces LIST]
                             [--sprite PX] [--floor-faces N] [--max-iters N]
                             [--elevation DEG] [--azimuth DEG] [--json PATH]
                             [--timeout SECONDS]
```

`--target-iou` bisects for the lowest face count that holds the silhouette above
the threshold and prints an answer. `--sweep` forces the full table instead.
`--max-iters` is how many budgets it tries (default 8) and `--floor-faces` is the
lowest it will go (default 200).

The renders it measures are saved in `output/_dec/`, so you can look at the
pictures behind the numbers. `--timeout` defaults to 3600 seconds here, because a
long sweep is the slowest job in the repo.

Pass `--sprite` at the size the asset is really seen at. Judging a budget at 340
pixels and shipping at 128 wastes geometry.

### `sheet_check.py`

```sh
scripts/sheet_check.py SHEET... --cell PX [--azimuths LIST] [--empty-floor F]
                       [--same-eps F] [--quiet]
```

Checks a sheet you already have for the faults a number can catch: an empty
cell, a pose row identical to the first row at every angle (the pose did
nothing), a subject touching its cell border, and a subject that fills far more
of one angle's cell than another's, which usually means a framing problem. It
exits non-zero if any sheet fails.

Pass `--cell` at the `--size` the sheet was rendered at, and `--azimuths` to have
it name the down-and-right facing. It does not judge whether the motion looks
right. That part is still yours.

### `normalise_mesh.py`

```sh
scripts/normalise_mesh.py MODEL... (--height UNITS | --footprint UNITS)
                          [--out-dir DIR] [--suffix S] [--check] [--tolerance F]
                          [--timeout SECONDS]
```

`--height` for anything that stands, `--footprint` for anything tile bound: a
character is sized by how tall it stands, a building by the tile it occupies.
Both put the lowest vertex on z=0.

`--check` changes nothing and exits non-zero if any model is outside the
tolerance, so it works as a gate in a script. Each normalised model gets a
`.scale.json` beside it recording the rule and factor, which is what answers
"was this one normalised, and to what?" six months later.

### `transfer_weights.py`

```sh
scripts/transfer_weights.py RIGGED_FBX DENSE_MESH [--out PATH] [--no-align]
                            [--timeout SECONDS]
```

Only use `--no-align` when both meshes already share a coordinate frame, which is
rare, because the rigger normalises its output.

### `cleanup.py`

```sh
scripts/cleanup.py                                    # what is scratch, what is unclaimed
scripts/cleanup.py keep NAME --concept ... --model ... --rig ... --sheets ...
scripts/cleanup.py sweep --delete                     # by products only
scripts/cleanup.py sweep --delete --unclaimed         # permanent
```

`--delete` alone is safe. `--unclaimed` is not, and refuses to run when nothing
has been curated. It leaves alone the folders `keep` has no slot for
(`output/music/`, `icons/`, `scenery/`, `ground/`, `materials/`, `lipsync/` and
`mpfb/`) unless `--include-protected` is given too. `output/daz/` is not one of
them: `sweep` lists its files as unclaimed, and `--unclaimed` deletes them.

**Daz content.** `keep` refuses Daz 3D data before anything happens: no
provenance is read, no asset folder is made and nothing is copied. It exits 1
and lists every refused path on stderr, under `keep: refused. Daz 3D data may
not be curated into a shippable asset folder under the standard Daz EULA:`. It
refuses:

- `--model`, `--rig` or `--textures` under `output/daz/`, whatever the file type;
- `--concept` or `--sheets` under `output/daz/` unless it is an image or a video
  (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.bmp`, `.tga`, `.tif`, `.tiff`,
  `.exr`, `.mp4` or `.webm`);
- a file given to any flag from a Daz content library: `MODELS_DIR/daz_library`,
  or any folder holding the `.daz_library` records `daz_library.py` writes;
- a native Daz file from anywhere: `.duf`, `.dsf`, `.dhdm`, `.dbz`, `.dsa`,
  `.dse` or `.dsx`, in any case;
- when `--model` itself passes, the files `keep` would copy from beside it, by
  the same rules.

Paths are compared with symlinks followed, by device and inode. A render kept
from `output/daz/` prints `note: renders from output/daz/ may ship, but keep
them out of the AI stages and any training until Daz answers in writing: see
"The AI clauses" in docs/reference/daz-genesis.md.` The
guard goes by path and suffix only: a mesh copied out of `output/daz/` under
another name is not recognised. For 11 commands with no Daz content, the script
before and after the guard gave identical output, exit codes and files
(2026-09-16, in scratch copies of `output/`).

### `lipsync_cues.py`

```sh
scripts/lipsync_cues.py INPUT [--text TEXT | --text-file FILE | --no-text] [--out PATH]
                        [-r {pocketSphinx,phonetic}] [--fps N]
                        [--rule {midpoint,closure,share}] [--force]
                        [--timeout SECONDS]
scripts/lipsync_cues.py --text-only TXT [--fps N] [--out PATH]
scripts/lipsync_cues.py --selftest
```

It runs on the host. Fetch Rhubarb once with `scripts/fetch_tools.py --download
rhubarb`, and have ffmpeg on the PATH. INPUT is an audio file in any format ffmpeg
reads, or a folder of them. The transcript comes from `--text`, `--text-file` or
`LINE.txt` beside the audio, in that order, and must be UTF-8. Rhubarb runs on one
thread, because with more the same command gave different cue files: 3 different
files in 5 runs on one line, against 1 on one thread. The timeline goes to
`output/lipsync/LINE.json` with Rhubarb's log beside it, and
[the timeline file](/reference/lip-sync#the-timeline-file) describes its shape.

**The speech gate.** Rhubarb's voice detector takes noise for speech and returns a
mouth that talks all the way through it, so each line is checked against
Rhubarb's trace log and refused when either check fails:

- **Words:** the word error rate against the transcript is above 60%. Skipped
  with no transcript, with `--no-text`, and with `-r phonetic`, which reads no
  transcript at all and writes `"text": null`.
- **A flat mouth:** the non-X cues of 1.0 s or more together cover more than 50%
  of the voiced time. One such cue below that share prints a warning only.

A refused line writes no timeline unless `--force` is given, which writes it with
`"passed": false` in `gate`. In the runs of 2026-09-16 behind those thresholds,
10 s of white, pink, brown and velvet noise and of a sine at -6 dBFS were refused
with either recogniser. A 2 s noise tail after a line passed with a warning. A 15 s
generated battle track with no transcript was refused, but passed with
`-r phonetic`. One line slowed to half speed failed the word check against its
own transcript. So keep music, ambience and effects away from it, or give every
line its transcript. The tables are in the
[Rhubarb experiment's README](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/experiments/rhubarb/README.md),
and `--help` gives the numbers. Not yet tried: Rhubarb inside the container,
synthetic voices, and real speech in other languages through `-r phonetic`.

**Exit codes.**

| Code | Means |
|---|---|
| 0 | every line written and passed the gate; `--selftest` passed |
| 1 | a tool or input problem: Rhubarb not installed, ffmpeg missing or failing, Rhubarb failing or timing out, an unreadable transcript, or `--text-only` about to overwrite a timeline made from audio |
| 2 | bad arguments |
| 3 | the gate refused at least one line, with or without `--force` |
| 4 | `--selftest` ran and an expectation failed |

A folder run carries on past a failed line, then exits 1 if any line failed, else
3 if any was refused.

`--fps N` adds one mouth shape per frame for a baked animation, by one of three
rules: `midpoint` (the default), `closure`, which shows A in any frame an A cue
overlaps, and `share`, adapted from the 0.08 s window of
[Valve's phoneme filter](/reference/source-filmmaker#visemes-are-rows-of-weights).
None has been judged on a portrait. `--text-only` writes a placeholder flap to `output/lipsync/text-only/`
and never overwrites a timeline made from audio.

### `make_hair.py`

```
scripts/make_hair.py --list
scripts/make_hair.py [--style NAME] [--look {stylised,realistic}] [--colour NAME|R,G,B]
                     [--part centre|left|right|none|X] [--part-width DEG] [--part-flow F]
                     [--name STEM] [--out DIR] [--layers NAME=N,...] [--length CM]
                     [--variation CM] [--wave F] [--cap DEG] [--hairline DEG]
                     [--head-radius CM] [--lift F] [--guide-distance CM] [--jitter F]
                     [--sweep F] [--cling CM] [--volume CM] [--band F] [--ramp F]
                     [--cap-diffuse PNG] [--no-drape] [--seed N] [--no-preview] [--no-bake]
                     [--beard {none,stubble,short,full}] [--beard-length CM] [--curl CM]
                     [--curl-turns N] [--curl-start F] [--card-width SCALE]
```

Hair the repo owns outright, because the two other routes to it both stop short.
A Daz hair product renders but may not ship as 3D without an Interactive License
for that product. A strand hair is not even that: the two in the library carry
236,136 and 167,264 vertices and **no polygons**, so Cycles draws the cap and
nothing else, which is why `daz_characters.py` leaves them out.

This is the numpy half of a two-script pipeline designed from the
[hair cards research](/reference/hair-cards): it lays out the hair and grows
guide curves in layers over a scalp cap, then hands them to
[`bake_hair.py`](#bake-hair-py), which sweeps them into geometry in the
container's Blender and renders the atlas. Everything below was measured on
2026-09-22 on the host's `python3` unless it says otherwise.

#### What it writes, all under `output/hair/`

`<name>_guides.npz` (the guide polylines with a layer, a lock, a width, an atlas
slot and a mirror flag per curve), `<name>_atlas.json` (the eight-slot sheet
plan), `<name>_cap.obj` with `.mtl` and two 1024 px maps, `<name>_fallback.obj`
with its own painted atlas (the numpy-only result, for a host with no
container), `<name>_preview.obj` (the fallback and the cap on a plain scalp
sphere, for `render_sheet.py`), and `<name>.json` with every setting and
measurement. Then, unless `--no-bake`, it runs `bake_hair.py` as a child
process and the baked `<name>.obj` is the one to use.

**Static geometry.** No rig, no fitting, no morphs, no physics. It is placed on
a head rather than skinned to one, which `daz_import_probe.py scene --wear-obj`
does by measurement.

#### Layers, not a population

Every published card workflow builds hair as a stack over a cap, thick to thin
outward <!-- HAIR-001, HAIR-044 -->, so the generator has a `LAYERS` table and
grows each layer separately: 90 **shells** (the base, 2.4 cm wide tapering to
0.35, roots 0.05 cm inside the scalp so their closed ends hide under the cap),
150 **breakup** cards in 50 three-card tents <!-- HAIR-002 --> (1.4 to 0.5 cm,
0.8 cm off the scalp), 40 **hairline** cards on a 12 degree band inside the
hairline (1.0 to 0.4 cm, 0.6 of the style's length) and 30 **flyaways** (0.5 to
0.2 cm, 1.5 cm off). Width is constant over the first 60 percent of a card then
tapers <!-- HAIR-013 -->. `--layers shell=120,flyaway=0` overrides any count,
and a style scales all of them (short 1.3, long 1.1). The counts and the
offsets in centimetres are guesses; no source gives either.

#### Roots, flow, locks

Roots are Bridson Poisson-disk samples on the sphere cap, with a density mask
that thins the frontal region to 0.6 and a hairline that is 48 degrees from the
crown at the front, 76 at the temples and 83 at the nape <!-- HAIR-118 -->.
Against the old Fibonacci spiral at the same count, the shell roots' nearest
neighbour distance is 2.169 cm with a coefficient of variation of 0.162 where
the spiral gave 2.085 cm and 0.363: as even, with a third of the scatter.

Flow leaves a whorl 18 degrees behind the crown and 8 to one side
<!-- HAIR-106 --> along the scalp, 0.85 away from the whorl and 0.15 down, tilted
off the scalp by an exit angle of 12 degrees at the rim rising to 30 at the
crown behind `--lift` (15 to 50 on the first bake fanned the crown out like a
palm). A parting is a rejected strip closing to nothing at the nape, with the
hair swept off it by `--part-flow`; 0.5 left a bare wedge, 0.35 leaves a line.
Hair rooted over the face is brushed aside by `--sweep` as it falls. The
curly style winds each strand in a helix round its own centreline, `--curl`
1.1 cm in radius over `--curl-turns` 3 from `--curl-start` 0.2 of the length,
in Blender's Curl Hair Curves terms <!-- HAIR-117 -->, with a phase shared by
the lock; the sideways sine wave the style had before read as no curl at all
on the figure (2026-09-22).

Cluster centres are a second Poisson set at `--guide-distance` (4.5 cm
stylised, 2.5 realistic; on the default bob 14 centres, 20 cards each), every
root takes its nearest centre as its lock, and each strand is pulled towards
its lock's centre guide by 0.8 shaped linearly root to tip with a 0.3 cm tip
spread, the semantics of Blender's Clump Hair Curves <!-- HAIR-117 -->. A
card's width comes from its lock's spread <!-- HAIR-101 -->, clamped to its
layer's bounds.

#### Draping over the body

Long hair needs something to land on. The body below the head is five capsules
in the hair's own frame, measured on the Genesis 9 base figure on 2026-09-22 by
height band below the fitted skull centre (`output/hair/_exp/measure_body.py`):
a neck 6.5 cm in radius sitting 1.5 cm behind the scalp centre from 11 to
24 cm down, a shoulder bar 22 cm each side at 27 cm down, and three chest
capsules of 9 cm below that; they scale with `--head-radius`. As a strand is
stepped, any point that lands inside a capsule plus 0.8 cm of clearance is
pushed out to it and the strand's heading loses its component into the
surface, so it slides along the neck and over the shoulder; on the flat top of
a shoulder, where sliding leaves no direction, the strand is sent forward or
back to whichever side it is already on. The cluster pull and the wave come
after, so a final pass pushes every point out again.

Before this the 30 cm and 34 cm styles splayed outward from their exit angle
and passed through the shoulders; with it they hang down the neck and turn at
the shoulders, and on the figure `--declip 1.5` finds 4.64 and 4.57 percent of
their vertices inside the body and leaves 0.00 percent, pushing at most
10.9 mm. At 0.5 cm of clearance it had left 0.55 and 0.48 percent deeper than
its 20 mm reach. `--no-drape` switches the capsules off. The preview OBJ draws
them in grey under the scalp sphere so the drape can be judged with no figure
in the frame.

#### A beard, on a jaw that was measured

`--beard stubble|short|full` grows a second asset, `<name>_beard`, or the
beard alone with `--style none`. It grows on a jaw ellipsoid rather than the
scalp sphere: the lower face of the Genesis 9 base figure was read by height
band below the fitted skull centre (a read-only `bpy` script on 2026-09-22;
the nose tip 8 cm down and 13.5 cm forward, the lips 9.5 to 12.5 down, the chin
13 to 16.5 down at 11.1 forward, the jaw 7.2 cm each side at the lips and 5.6
at the chin) and a bounded Nelder-Mead fit over 1,274 of those vertices gave
an ellipsoid centred (0, -11.1, 2.1) cm with radii (6.9, 7.2, 9.0), rms
0.63 cm; the guessed one had put the sides 1.6 cm too wide and the bottom
2.8 cm too high. Only the fitted numbers are in the script. The beard region
is the ellipsoid below a line from the lower lip at the midline up to the
cheeks and back to the jaw angle, down to a neckline 17.5 cm below the scalp
centre, plus a moustache band on the upper lip with the lower lip bare, 3.05
steradians of the ellipsoid's own space. Roots are the same Poisson sampler
run on the ellipsoid, the flow is down the face with 0.25 outward at a fixed
exit angle of 20 degrees, every point is held clear of the ellipsoid, and the
beard drapes over the body capsules with the neck starting at the neckline.
Stubble is the cap and 60 flyaways of 0.4 cm; short is 3 cm of cards; full is
7 cm with 30 shells. The beard cap is the region of the ellipsoid at 0.15 cm,
its opacity 0.4, 0.45 and 0.7 by beard and blurred over 130 px at the edge: at
70 px and 0.85 to 1.0 it read as a dark band with a straight top edge across
the cheeks. Baked, the full beard is 6,176 triangles, the short 4,316 and the
stubble 1,536, each in about 2 s wall in Blender; placed on the figure the
declip finds 10.5, 8.0 and 26.1 percent of their vertices inside the face and
leaves 0.5, 0.46 and 1.94 (`--declip-max-push 30`), the remainder at the
chin, which sits 1.1 cm outside the ellipsoid. A second `--wear-obj` puts a
beard under a hairstyle in one scene. Everything in that paragraph beyond the
fit is a guess set by looking once; the short and stubble caps still read as
a soft patch on the cheek.

#### The cap

A dome at the scalp radius plus 0.15 cm bounded by the same hairline, 14 rings
of 48 with one pole vertex (1,296 triangles), a top-down UV, and two maps: a
diffuse of the root colour at 0.75 with 9,000 follicle strokes flowing away
from the whorl and a slightly lighter parting line, and an opacity that is one
inside the hairline, blurred over 40 px at the rim and 0.85 along the parting
<!-- HAIR-047, HAIR-048 -->. The first bake's parting stripe, a fifth of the cap
wide at 0.7, read as a bald wedge. `--cap-diffuse PNG` replaces the painted
colour with an image made elsewhere, resized to the cap map; the cap's own
opacity still cuts the hairline and lightens the parting.

#### The atlas plan and the fallback

`<name>_atlas.json` is a 2048 by 1024 sheet of eight 256 px slots with 16 px
gaps, strands 48, 32, 20, 12, 8, 4, 2 and 1 per slot, banded base, breakup,
sparse and flyaway <!-- HAIR-018, HAIR-062 -->. `bake_hair.py` renders it from
real strands; the fallback OBJ paints the same ladder in numpy, root at the
bottom row, RGBA opacity with the mask in all four channels (Blender's OBJ
importer wires `map_d`'s image *Alpha* output into Principled Alpha, and a
greyscale PNG has none). Its slot mean alphas measured 0.394 down to 0.010
against the rendered sheet's 0.380 down to 0.009.

#### Winding

`build()` emits each ribbon's triangles as `(a, d, b), (a, c, d)`, and the
report prints the mean signed dot of every face's normal against the radial
direction from the head centre: cap +1.000, shells +0.917, cards +0.940 on the
default bob. The previous generator emitted `(a, b, d), (a, d, c)`, wound into
the head, which is what made the hair render black ([the note](/reference/hair-cards#what-was-measured-here-before-anything-was-read)).

#### Cost

The default bob took 0.99 to 1.33 s wall over three runs (grow 0.19 to 0.22,
cap maps 0.51 to 0.89, write 0.18): 310 curves, 1,930 points, a 4,536-triangle
fallback. The retired flags of the old generator (`--strands`, `--round`,
`--hairs` and the rest) exit 2 with the name of what replaced them.

### `bake_hair.py`

```
scripts/bake_hair.py NAME [--dir DIR] [--dome-mix F] [--card-mix F] [--thickness F]
                     [--samples N] [--timeout S] [--no-wait]
```

The Blender half. It reads `<name>_guides.npz`, `<name>_atlas.json` and the cap
files that `make_hair.py` wrote, runs one job in the container's Blender 4.5.9
(the way `daz_import_probe.py` does, waiting for an empty ComfyUI queue first),
and writes `<name>.obj`, `<name>.mtl`, `<name>_diffuse.png` (RGBA, alpha is
the opacity), `<name>_opacity.png`, `<name>_pack.png` (root gradient, random
id, spare) and `<name>_bake.json`. Measured 2026-09-22 on the default bob.

- **Shells.** Layer 0 becomes closed lens shells: Curve to Mesh over an 8-point
  circle scaled to `--thickness` 0.12 of the width, with end caps, on curves set
  to POLY (a Catmull-Rom curve of 8 points made 84 quads), the radius
  attribute feeding the 4.5 Scale input, and Set Curve Normal to the radial
  direction so the lens lies flat on the scalp <!-- HAIR-133 -->. The report
  checks which face is outward by radius (u = 0 sits 0.63 cm further from the
  head centre than u = 0.5) and that every shell is manifold with a positive
  signed volume. 90 shells are 11,160 triangles.
- **Cards.** Layers 1 to 3 become flat ribbons from a line profile, each
  corner's UV laid over its card's atlas slot, mirrored when the card is
  flagged.
- **Normals.** Shell corner normals are the shell's own, with edges sharper
  than 60 degrees split so the lens crease does not smear into a dark band,
  mixed half way to a smooth dome's by Data Transfer (`--dome-mix` 0.5; at 1.0
  a shell on the side of the head faces away from a front camera)
  <!-- HAIR-020, HAIR-066 -->. Cards blend their ribbon frame 0.6 of the way to
  the radial, flyaways 0.3. After the OBJ round trip the corner normals match
  to a dot of 0.9979 on the unsplit mesh.
- **The atlas** is rendered from 127 Cycles hair curves as ribbons in three
  passes (diffuse with alpha, root gradient, random id) at 64 samples, about
  0.35 s each, then the colour is dilated 32 px under alpha 0 by a distance
  transform <!-- HAIR-054 -->. Slot mean alphas 0.380, 0.286, 0.179, 0.122,
  0.083, 0.041, 0.018, 0.009. The shells wear the base slot's colour along
  their length, opaque: a flat colour read as beige plastic, and laying `u`
  straight round the closed profile put only the slot's edge quarters on the
  outward face and every shell wore a dark band down each flank. The outward
  face now spans the whole slot and the back mirrors it.
- **The file.** One `o hair`, faces inside to outside, `usemtl <name>_cap`,
  `<name>_shell`, `<name>_card`, exported with normals and UVs on the axes
  `--wear-obj` imports, re-imported to check: the cap block lands within
  0.000001 cm of `<name>_cap.obj`.

The default bob bakes in 2.1 to 2.6 s in Blender, 2.6 to 2.9 s wall: 8,853
vertices and 14,436 triangles. Across the six styles the skill lists, baked
triangles are bob 14,436, curtains 14,436, crop 18,378, elder 15,750 and
bounce 14,436, all inside the 4k to 20k budget <!-- HAIR-016 -->, and curls
24,198, over it by design: each curly strand is a helix of 20 points, and at
fewer the ringlets flatten. A 12-point profile had put the bob at 20,196. The six,
generated, baked, placed on Genesis 9 and rendered at three angles each, took
73 s wall.

### `make_scalp.py`

```
scripts/make_scalp.py [--colour NAME|R,G,B] [--style {crop,stubble,bald}] [--graph JSON]
                      [--seed N] [--steps N] [--raw PNG] [--contrast F] [--blend F]
                      [--size PX] [--name STEM] [--out DIR] [--queue-wait S] [--dry-run]
```

A scalp texture for `make_hair.py --cap-diffuse` from the repo's own ComfyUI
graphs, the one AI stage in the hair pipeline; no Daz content goes near it,
the prompt is text. One job on `preset_ground_texture.json` at its native 1024
px square (Qwen-Image, 20 steps, cfg 4, euler simple), fetched back over
`/view`, made to tile with `make_seamless.py`'s mend, and tinted so the
image's median lands on the hair colour darkened by the same 0.75 the painted
cap uses. It writes `output/hair/scalp_<colour>.png`, the raw and tiled
images beside it, and a JSON with the prompt, seed, graph, seam scores and
timings. `--raw` retints an earlier image with no job; `--style` swaps the
prompt for a crop, stubble or bald scalp.

Measured 2026-09-22 on the RTX 4070 Ti SUPER: a job takes 85 to 95 s from
`/prompt` to history, the tile and tint under 0.1 s. The seam check went from
2.01 times the interior at 29 levels to 1.05 at 1.65 for the black crop, and
passed on every colour and style tried; the third prompt wording worked and the
two before it did not. Under the crop the difference from the painted cap is
9 pixels of 940,800 in the head render, because the shells hide the cap; bare
and from above, the AI cap shows follicle strokes radiating from a whorl where
the painted one is featureless, which is the case it is for.

### `daz_library.py`

```sh
scripts/daz_library.py install ZIP... [--dry-run] [--overwrite] [--eula-read YYYY-MM-DD]
                              [--interactive-license] [--vendor NAME]
                       [--interactive-license]
scripts/daz_library.py intake [--source DIR] [--ledger NAME] [--dry-run] [--keep-zips]
                              [--vendor NAME]
scripts/daz_library.py list
scripts/daz_library.py licence SKU [--eula-read YYYY-MM-DD]
                       [--interactive-license | --standard-license]
scripts/daz_library.py verify [SKU] [--crc]
scripts/daz_library.py uninstall SKU [--part NN] [--dry-run] [--force]
scripts/daz_library.py case-check
scripts/daz_library.py selftest [--dir DIR]
```

Every command but `selftest` takes `--library DIR`, `--json` and `--examples N`.
**Packages that are not Daz packages.** A Daz Install Manager zip is named for
its SKU and lists its files in `Manifest.dsx`. A zip from anywhere else has
neither, so `--vendor NAME` records who made it, the record is named after the
file, and the content root is found by looking: the first folder, or the zip
root, that holds one of a library's own folders. Anything beside those is left
in the zip and named. The licence wording in this script was read from Daz's
EULA and is not applied to anyone else's content: the record keeps the vendor,
the terms files the package shipped and the date you say you read them. A Daz
package a browser numbered as a second download is refused by name, because it
would otherwise install a second copy of a product under a name of its own. See
[Daz figures](/guide/daz-figures#content-that-is-not-a-daz-package).

`selftest --json` fails with `daz_library.py: error: unrecognized arguments:
--json`.

**Where.** The library is `MODELS_DIR/daz_library`, with `MODELS_DIR` read from
the environment, else from `.env`, and a relative value resolved against the
repo root as compose does. The container sees it as `/app/models/daz_library`.
A library inside the repo, or one containing it, is refused.

**What it installs.** A package is a Daz Install Manager zip whose name matches
Daz's pattern, such as `IM00086958-01_Genesis9StarterEssentials1Of3.zip`,
matched in full and in ASCII only. Only the File elements of its
`Manifest.dsx` with `TARGET="Content"` and `ACTION="Install"` are extracted,
with `Content/` removed, so the parts of a product merge into one folder. A
part number that disagrees with `Supplement.dsx`, a GlobalID that differs from
the one recorded for the SKU, and two zips for one part are refused as signs of
a renamed zip. Do not script the Daz website: download by hand.

**Checks first, then the lock.** An install opens and checks the zips, takes
the library's lock (`<library>/.daz_library/.lock`), reads the records and runs
every path check inside it. When there is no lock file yet, the checks also run
once before, so a refused run creates nothing, not even the library folder.
`--dry-run` takes no lock and writes nothing. A refused path stops the whole run
with `nothing was installed`. Among the refusals:

- `a symlink is at its temporary name <tmp>`, and `something other than a
  regular file is at its temporary name <tmp>`;
- `a symlink already exists at this path`, even one pointing inside the library;
- `a name ending in .daz_library-part, which this script uses for temporary
  files`;
- `it needs <prefix> as a folder, but <zip> lists that path as a file`, within
  one zip or across the zips of a run;
- and a second install while one holds the lock, `another daz_library.py is
  changing <library>; wait for it to finish`.

Each file is written to `.<name>.daz_library-part` beside it, created with
`O_EXCL` and `O_NOFOLLOW`, and renamed into place after the zip's CRC-32 check
passes. A regular file left there by an interrupted run is replaced. A file
already present with other bytes is a conflict unless `--overwrite` is given.
The checks see the library as it is when they run: another program changing it
during an install, without the lock, is not guarded against beyond the
temporary name.

**Stopping.** Any error while writing a package, a corrupt, encrypted or
unsupported entry included, removes the temporary file and stops that package
as `partial`, with the files already placed recorded as `"complete": false`.
Later packages still run, and the exit status is 1. `list` shows the part under
`incomplete_parts`, `verify` exits 1, and `uninstall SKU` removes what was
placed. The first SIGINT, SIGTERM or SIGHUP prints `<SIG> received: stopping at
the current file and recording what is placed; send it again to stop at once`,
stops after the current 1 MiB chunk and records the part as `interrupted`, and
packages not yet started as `not_started`. The report ends `stopped by <SIG>:
install again to finish`. A second signal stops at once and still records the
files placed.

**The record and the licence.** `<library>/.daz_library/<SKU>.json` holds the
product, each part's zip name, sha256, size and times, and every file with its
size, CRC-32 and the parts that list it. Its licence block has two inputs: the
licence held, the Daz Standard License unless `--interactive-license` records a
bought Interactive License, which the script cannot check, and `eula_read`, the
date given with `--eula-read`, else null. The rest of the block
(`renders_and_sprites`, `mesh_rig_morphs_textures`, its conditions, `ai_stages`
and the URLs) is wording rebuilt whenever the record is saved, and `licence SKU`
prints it. Records saved by the first version keep the older fields
(`mesh_rig_morphs_textures_may_ship` and the like) until their next save.

**`intake` is `install` over a folder you have finished with.** It installs
every `.zip` in `<library>/Source`, or `--source DIR`, in a stable order with
the parts of one product in one install run, so every check above still
applies. After a package installs, the files the record now lists for that part
are verified, present, a regular file, at their recorded size and CRC-32, and
the part recorded complete. Only then is its zip deleted. A package that is
refused, conflicts, stops part way or fails that verify keeps its zip, and so
does every other part of the same product; `--keep-zips` deletes nothing and
`--dry-run` writes nothing, deletes nothing and says what each zip would do. A
zip whose files are all installed and identical is reported as `already
installed` and deleted under the same rule. Nothing but a zip the run has just
processed is ever deleted, and a folder with no `.zip` in it gives `no .zip
files in <source>: nothing to do`, exit 0. The exit status is 2 for a refused
name, package or path and 1 for a package left uninstalled by a conflict, a
shortage of space or a stop part way.

**The ledger** is one Markdown file in the source folder, `PROCESSED.md` unless
`--ledger NAME` says otherwise, appended to and never rewritten, so a later
intake adds rows below the earlier ones. Its header says what the file is, that
the zips were deleted on purpose and that a package can be downloaded again
from your own Daz account under the same SKU. Each row carries the date, the
product name from `Supplement.dsx`, the SKU and part, the zip's name, its size
in bytes and its sha256, what happened and what became of the zip, and the
number of files the manifest listed for Content. It records names and counts
only: no Daz content, and no file list long enough to reproduce a product.

**`verify`** uses `lstat`, so a symlink at a recorded path is `not_a_file` even
when it points at identical bytes. **`case-check`** lists names in one folder
that differ only in case, and references inside the library's `.dsf` and `.duf`
files that find their file only when case is ignored.

| Exit | Means |
|---|---|
| 0 | done |
| 1 | a conflict, a skipped or partial package, a `verify` or `case-check` finding, or a failed self-test check |
| 2 | a refused path, name, package, library or argument, or the lock held by another run |
| 128 plus the signal | an install stopped by a signal: 130 SIGINT, 143 SIGTERM, 129 SIGHUP |

Measured on 2026-09-16 with Genesis 9 Starter Essentials (SKU 86958), host
`python3` 3.13, after the review fixes: `selftest` passed 67 checks in 4.70 and
4.80 s wall, `verify 86958 --crc` passed 6499 of 6499 in 0.51 to 0.93 s, and a
dry run of all three parts against the installed library exited 0 in 6.84 s
wall with every file identical. Installing all three into an empty library took
7.59 and 6.90 s wall before the fixes.

Measured on 2026-09-19 on the same host, on six zips in
`/models/daz_library/Source`, 2,224,386,560 bytes: `intake --dry-run` exited 0
in 8.04 s wall (`time`), and `intake` took 8.64 s wall (`date +%s.%N` before
and after). It found the three Genesis 9 Starter Essentials parts already
installed, in 6.66 s for the product, and installed three products that were
not: SKU 87397 in 0.60 s, SKU 88643 in 0.14 s and SKU 91304 in 0.28 s. Each
part's recorded files then verified at their size and CRC-32 in 0.03 to 0.32 s,
all six zips were deleted and six rows were appended to `Source/PROCESSED.md`.
`verify --crc` over the four products passed 7,106 of 7,106 files in 0.62 s,
and `intake` over the emptied folder exited 0 having done nothing. The
[guide](/guide/daz-figures#a-library-outside-the-repo) has the rest.

### `daz_import_probe.py`

```sh
scripts/daz_import_probe.py fetch
scripts/daz_import_probe.py build --out output/daz/NAME.blend [--facs] [--visemes]
                            [--subdivision {keep,off}] [--figure DUF]
                            [--anatomy auto|none|DUF,...] [--library DIR]
                            [--mat-preset DUF[@MESH,...]] [--mat-replace DUF[@MESH,...]]
                            [--no-auto-materials] [--no-fit-report]
                            [--no-textures] [--material-method M] [--fit F]
                            [--content-dir DIR] [--no-dir-check] [--verbosity N]
                            [--timeout SECONDS] [--no-wait]
scripts/daz_import_probe.py scene --out output/daz/NAME.blend [--figure DUF]
                            [--anatomy auto|none|DUF,...] [--library DIR]
                            [--morphs SET,...] [--custom-morphs DIR]
                            [--custom-files F,...] [--custom-category NAME]
                            [--custom-bodypart {Face,Body,Custom}] [--facs]
                            [--mat-preset DUF[@MESH,...]] [--mat-replace DUF[@MESH,...]]
                            [--no-auto-materials] [--hide NAME,...] [--hide-figure]
                            [--hide-material NAME,...] [--offset MESH=DX,DY,DZ]
                            [--declip MM] [--declip-max-push MM] [--declip-max-verts N]
                            [--declip-skip NAME,...] [--no-fit-report]
                            [--set NAME=VALUE] [--wear DUF] [--no-transfer]
                            [--wear-obj PATH] [--obj-bone NAME] [--obj-scale S|auto]
                            [--obj-offset DX,DY,DZ] [--obj-yaw DEG] [--obj-radius CM]
                            [--obj-no-shadow] [--obj-forward AXIS] [--obj-up AXIS]
                            [--skip-transfer NAME,...] [--set-dressed NAME=VALUE]
                            [--pose DUF] [--pose-affects-morphs] [--no-verify]
                            [--subdivision {keep,off}] [--material-method M]
                            [--fit F] [--verbosity N]
                            [--timeout SECONDS] [--no-wait]
scripts/daz_import_probe.py verify --blend output/daz/NAME.blend [--rig NAME]
                            [--props NAME,...] [--timeout SECONDS] [--no-wait]
scripts/daz_import_probe.py render --blend output/daz/NAME.blend [--only AA,OW]
                            [--sizes 128,220,340] [--columns body,face,face34]
                            [--samples N] [--subdivision {off,as-saved}]
                            [--materials] [--sheet-size PX] [--no-sheet]
                            [--motion-only] [--label TEXT] [--threshold N]
                            [--keep-frames] [--timeout SECONDS] [--no-wait]
```

**`fetch`** downloads GitHub's archive of import_daz's `version_5_2_0` tag,
pinned at 1,697,629 bytes and sha256
`b6921c46e9a876fe88ab0ef75f47c8eac67cf4c4314059871d2a78bdcfccf9d2`, checks the
commit its zip comment names, and unpacks 296 files into
`input/_devtools/import_daz/ext/import_daz`. Any download error deletes the
`.part` file and tries the next URL. It unpacks again when a file is missing or
has another size, but does not compare contents. The importer is
GPL-2.0-or-later, and is run, never copied into the repo.

**`build`** registers the importer as a local extension, points its content
directory at the library and checks that the importer resolves the figure,
because a wrong path raises nothing. `--library` is the host path, by default
`/models/daz_library`, not read from `MODELS_DIR`, and the container must mount
it. `--figure` and `--anatomy` entries are relative to the library with no `..`
part, or the run exits 2 with `expected a path relative to the library with no
.. part, got ...`. With `--anatomy auto` it reads the post-load figure list
from the figure's `.duf`, gzip-compressed or plain. Use `--facs`: on Genesis 9
`--visemes` loads nothing, so a build with it exits 1 by design. Use
`--subdivision off`: the default `keep` saves the importer's Subsurf levels, up
to 3 for render. It writes `NAME.blend`, `NAME_build.json`, which records the
command line and every step, `NAME_blender.log` and `NAME_poses.json`.

**Moving a garment.** `--offset "MESH=DX,DY,DZ"` shifts a worn mesh in
millimetres along the world axes before the declip runs. Measure first: on a
measured figure the hooded cloak's apex sat 69.6 mm below the crown of the head
it covers, and raising it that far lifts its hem by the same amount.

**Hiding one zone of a garment.** `--hide-material NAME,...` takes a material
zone's alpha to zero, which is how a hooded cloak loses its hood and keeps the
cloak. The mesh stays whole, so the framing still allows for it.

**Hiding a figure under its costume.** `--hide-figure` keeps the figure's own
meshes out of the render, its body and the eyes, mouth, lashes, tear and
eyebrows a post-load script brings with it, and `--hide NAME,...` names any
others. Nothing is deleted, so the clothes still fit and `render_sheet.py`
frames what is left: a skull inside a hood instead of a face.

**Fit, and pushing a garment out.** Every build measures how each mesh sits
against the body: how many of its vertices are inside it, how deep, and the
mean gap. Garments should be outside; an eyeball is inside the head whatever
you do. `scene --declip MM` pushes each worn mesh's vertices clear of the body
by that much, which took a pair of shorts from 73.3% of their vertices inside
to 0 (2026-09-21), leaves a mesh above `--declip-max-verts` alone so a card
hair keeps its shape, and refuses a posed figure because it edits the rest
shape. See [Daz figures](/guide/daz-figures#cloth-that-clips-measured-rather-than-judged).

**Material presets.** A Genesis 9 eyelash, eye, mouth or eyebrow figure arrives
with no map at all, and Daz Studio fills them in afterwards with a MAT preset.
Both `build` and `scene` now do that: they read the presets beside the figure
and beside each anatomy file and wire the cutout opacity, the colour map or
flat colour, and a plainly stacked layered colour image, filling in only what a
material is missing. `--mat-preset FILE[@MESH,...]` names one, applied before
those and winning over them; `--no-auto-materials` leaves the materials as the
importer built them, which draws an eyelash card as an opaque fan.
`--mat-replace FILE[@MESH,...]` is the other half: it swaps the maps a material
already has, matched by what each file name says the map is for, which is what
a skin swap needs. It runs after the fill. The report
says, per preset, what was filled in, what was left alone, and what it could
not resolve. Material merging is off in every import, because bare anatomy
materials are identical and were merged into one slot. See
[Daz figures](/guide/daz-figures).

**`scene`** does everything `build` does and then drives the figure, in this
order, each step recording its seconds, peak RSS and
`import_daz.get_error_message()` and carrying on when it fails:

- `--morphs` runs one standard morph operator per named set, from `anime`,
  `body`, `expressions`, `facs`, `facsdetails`, `facsexpr`, `feminine`,
  `flexions`, `head`, `jcms`, `masculine`, `powerpose`, `units` and `visemes`.
  Called from Python the selector dialog never opens, so each one loads every
  file the add-on's paths table lists for the figure. On Genesis 9, `units`,
  `expressions`, `visemes`, `head` and `facsexpr` have no table and add
  nothing.
- `--custom-morphs` runs `bpy.ops.daz.import_custom_morphs()` with
  `onDrivers='RIG'` on a folder inside the library, `--custom-files` naming the
  `.dsf` files in it (the default is every one). That is the only way to load
  the `Base Characters 9` shape dials, which no standard set lists.
- `--facs`, as in `build`, so `render --blend` finds its viseme properties.
- Every numeric property on the rig object and its data goes to
  `NAME_morphs.json` with its value, hard and soft limits and default.
- `--set NAME=VALUE`, repeatable, writes a property, tags the rig and its
  objects so the drivers run, and measures how far each deformed mesh moves in
  millimetres.
- `--wear` imports a clothing or hair `.duf` onto the figure already in the
  scene, repeatable and in the order given, parents its armature to the body
  rig and calls `bpy.ops.daz.merge_rigs(useOnlySelected=True)`.
- `bpy.ops.daz.transfer_shapekeys(transferMethod='NEAREST')` runs from the body
  to those meshes unless `--no-transfer`; `--skip-transfer` leaves named
  objects out of it, which a strand hair mesh needs.
- `--set-dressed` is `--set` again, after the wearables are on.
- `--pose` applies a pose preset with `bpy.ops.daz.import_pose()`, passing
  `affectMorphs=False` as the operator's own `invoke()` does, because the
  property default is `True` and with `useClearMorphs` also `True` a pose
  preset zeroes every dial on the figure. `--pose-affects-morphs` leaves the
  default alone.
- After saving, `verify` runs on the file unless `--no-verify`.

It writes `NAME.blend`, `NAME_scene.json`, `NAME_morphs.json`,
`NAME_blender.log` and `NAME_poses.json`, and a `NAME_build.json` beside them
so `render --blend` works on it. `--fit DBZFILE` exits 1 on this host: the
route needs a `.dbz` exported from Daz Studio.

**`verify`** reopens a `.blend` in a second Blender with no DAZ add-on enabled,
no extension repository and auto-run scripts off, and reports the bones, posed
bones, drivers, properties and meshes it finds, then clears the pose and zeroes
the properties `--props` names to say how far each mesh moves. With no `--rig`
or `--props` it reads them from the `_scene.json` beside the file.

**`render`** reads `NAME_build.json` for the viseme properties and runs two
stages, each a neutral row and then a row per viseme, all 17 or those `--only`
names: `render_sheet.py` on the whole figure at `--sheet-size`, then the probe's
`body`, `face` and `face34` framings at `--sizes`. Both stages rasterise with
EEVEE on the CPU: the probe's own renderer has no other engine, and the
`render_sheet.py` stage is pinned to `--engine eevee` rather than taking that
script's Cycles default, so the two can be read side by side and so the numbers
below still describe what it draws. `--samples` sets the probe's own framings
only. With `--subdivision off`, the
default, a `.blend` with any Subsurf modifier on is copied to
`output/daz/_NAME_sheet_<pid>.blend` with them off for `render_sheet.py`, and
the copy is deleted afterwards. `--only` given an empty list exits 2 with `name
at least one viseme, such as AA, from AA, EE, ...`.

Its files are `NAME_<label>_...`. The label is `--label`, or by default the
options that differ from their defaults, in this order: the `--only` visemes,
the `--sizes`, the `--columns`, `s<samples>`, `materials`, `as-saved`,
`no-sheet` or `sheet<size>`, and `t<threshold>`, so a short run never
overwrites a full one. A default run and `--motion-only` have no label, and
`--label ""` forces none. A label must match `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`,
or the run exits 2. `NAME[_label]_render.json` records the command line, every
option, `render_sheet.py`'s command and exit, and the pixels each viseme changes
against the neutral row. It and `NAME_motion.json` record what each viseme
moves: vertices, shape keys and pose bones.

**Waiting and stopping.** Before each Blender job it polls every 30 s until
ComfyUI's queue is empty and no other `python3 -c` job runs in the container,
unless `--no-wait`. On Ctrl-C or SIGTERM, and whenever `render_sheet.py` exits
non-zero or runs past the host's timeout, it ends the Blender job it started,
found by a path unique to that job, with SIGTERM and then SIGKILL after 10 s,
and prints `stopped   Blender job(s) [<container pids>] in <container>`. It
deletes that job's frames, the temporary copy and the rows file. A stop writes
no report and prints `! stopped by Ctrl-C` or `! stopped by SIGTERM`.
`--keep-frames` keeps only the probe's own cells, under `output/daz/_frames/`.

| Exit | Means |
|---|---|
| 0 | done |
| 1 | a download, checksum, Blender step or check failed; `render_sheet.py` exited non-zero, as its `--check` does when a row repeats the rest pose; or Blender ran past `--timeout` |
| 2 | bad arguments |
| 130 | stopped by Ctrl-C |
| 143 | stopped by SIGTERM |

Measured on 2026-09-16 in `comfyui-packaged`, EEVEE on llvmpipe:
`build --facs --subdivision off` took 5.7 s wall at a peak of 711 MiB;
`render --motion-only` 0.6 s in Blender; `render --only AA --sizes 128 --columns
face --samples 16` on that build, 28.9 s for `render_sheet.py`'s 2 rows and
17.7 s for the probe's 2 cells; and with `--subdivision as-saved` on a build
that kept its levels, 88.7 s for 2 face cells. The full default render on the
cage, with the version before the Subsurf copy, took 184.3 s and then 1287.6 s,
about 25 minutes. Every figure, and what failed on the way, is in the
[guide](/guide/daz-figures#importing-without-a-ui).

Measured on 2026-09-18 in the same container: `scene` with eleven morph sets,
six character dials and two sliders set took 5.0 s wall, 4.86 s in Blender, at
a peak of 642.0 MB, and left 1593 numeric properties on the rig; with three
wearables instead, 5.2 s wall at a peak of 998.4 MB; and the whole dressed,
posed build, a character preset with `body,jcms,flexions`, FACS, a shirt,
shorts, hair and a pose, 17.5 s wall at a peak of 1643.7 MB for a 140,971,653
byte `.blend` of 258 bones. `verify` on the outfit build took 0.8 s wall at a
peak of 578.5 MB. `render --blend output/daz/g9_dressed.blend --only AA --sizes
128 --columns face --samples 16 --no-sheet` drew 2 cells in 20.0 s. What each
stage measured, and the two things that need Daz Studio, are in the
[guide](/guide/daz-figures#a-dressed-posed-character-headless).

#### Wearing something that is not a Daz product

`--wear-obj PATH` puts a Wavefront OBJ on the figure. It is for geometry the
repo owns, `scripts/make_hair.py` being the one that writes it, and it takes a
different route from `--wear`, which loads a fitted Daz wearable.

The OBJ is placed by measurement, not by guesswork. The body vertices that
`--obj-bone` owns, meaning that bone's vertex group carries their largest
weight, are collected; a sphere is fitted by least squares to the upper half of
them; the OBJ's own origin goes to that sphere's centre; and `--obj-scale auto`,
the default, is the scale that lands the OBJ's roots, `--obj-radius` from its
origin, on that sphere.

On Genesis 9 the `head` bone owns **2,471** body vertices, and a sphere fitted
to the upper **636** of them has a radius of **8.26 cm**, centred 162.1 cm up,
which every one of those 636 sits within **4.6 mm** of on average and 10.9 mm at
worst. A 9.5 cm scalp therefore arrives at scale 0.008693 (measured
2026-09-22).

The object is then bone-parented rather than skinned, so it follows a pose like
a hat rather than like skin, and `--obj-offset DX,DY,DZ` in millimetres and
`--obj-yaw DEG` are there for what the report says is still wrong. The OBJ
importer's axes are `--obj-forward NEGATIVE_Z` and `--obj-up Y` by default,
which turns a +Y up OBJ into Blender's +Z up with its +Z at the figure's front.

**The declip reaches it.** An imported OBJ is not a rigid prop: it is a sheet of
hair or cloth modelled around a sphere, and bending it onto the body it rests
against is the point. A skull is not a ball everywhere, and hair grown for a
9.5 cm scalp sat inside the body on **11.24% of its 9,600 vertices**, mostly
where it hangs past the head onto the neck and shoulders. `--declip 1.5` moved
**1,830** of them out, by at most **8.38 mm**, and left **0.00%** inside
(measured 2026-09-22).

**`--obj-no-shadow` for hair.** Cards stacked several deep shadow each other.
The same hair, alone in frame under the same light, measured **mean luma 38.7
casting shadows and 51.7 not** on 2026-09-22; measured again the same day with
the mesh's winding fixed ([hair cards](/reference/hair-cards)), the cost of
shadows is 149.0 against 167.9, about 11 percent. Still worth the flag for
stylised hair, no longer the difference between black and brown.

The material comes from the OBJ's own MTL, and the probe then sets the map
feeding Alpha to Non-Color and switches off backface culling, because the
importer leaves the alpha map in sRGB.

### `daz_characters.py`

```sh
scripts/daz_characters.py list [--library DIR] [--generation NAME]
scripts/daz_characters.py keep SLUGS [--dir DIR] [--out FILE]
scripts/daz_characters.py make [--from FILE] [--prune] [--count N] [--seed N] [--size PX]
                          [--poses {none,upright,any}] [--dials {none,small,any}]
                          [--declip MM] [--azimuths DEG,DEG] [--facings front,side]
                          [--elevation DEG] [--span METRES] [--key N] [--ambient N]
                          [--samples N] [--sheet-cell PX] [--sheet-columns N]
                          [--any-brow-colour] [--library DIR] [--generation NAME]
                          [--timeout SECONDS] [--keep-blend] [--dry-run]
```

A roster of characters out of whatever the library holds. The character presets
and the two kinds of outfit are dealt out, so twelve characters use all six
presets twice and half of them wear the armour; everything else is a draw: one
of the four base skins for that build or the character's own, a hair colour the
beard matches, an eyebrow colour, which armour pieces, and a weapon. The draw is seeded, so
the same seed and the same library give the same characters, and `--dry-run`
prints the roll and builds nothing.

**No pose by default.** Genesis 9's rest pose is the A pose a character sheet
wants; `--poses upright` rolls a standing, walking, flexing, running or
stretching one, and `--poses any` rolls from all 58. `--span` follows: 2.0 m in
the rest pose, 2.4 m when a pose is rolled, because a stretching figure reaches
higher than a standing one.

**No body dials by default either**, because the clothes and the face do not
follow one: with three proportion dials set, 68.7% of a figure's trouser
vertices sat inside its own legs and its eyes sat 14 mm inside its head
(2026-09-21). `--dials small` and `--dials any` roll them anyway. Each garment
is pushed clear of the body with `--declip`, 1.5 mm by default, and each
character's JSON keeps the fit numbers that proves it.

**Lit brighter than a sprite sheet.** `--key 6.5 --ambient 1.3` rather than
`render_sheet.py`'s 1.6 and 0.22, under which a Daz figure's lit pixels
averaged 0.248 of 1 (2026-09-21).

Every slot is read from the library rather than named in the script, and from
one figure generation at a time: `--generation` names the folder under
`People/`, and by default it is the one the character presets sit in, so a
Genesis 8 hair and a Genesis 9 Toon outfit are left out of a Genesis 9 roll.
A wearable is anything under `Hair/` or `Clothing/` whose `.duf` says it is
one; the weapons are the `Base`, `Masculine` and `Feminine` right-hand grips,
which arrive bone-parented to `r_hand`; the poses are the ones whose names say
standing, walking, flexing, running or stretching, because the rest are seated,
laying or flying. The dForce pixie hair is left out and the run says why: its
strand mesh follows no bone and draws nothing.

Each character is built by `daz_import_probe.py scene` and drawn by
`render_sheet.py --azimuths 0,90 --elevation 0`, square on at eye level, framed
against a fixed `--span` so a short character reads as short. The sheet is cut
into one image per facing, and the `.blend`, about 150 MB, is deleted once they
are drawn unless `--keep-blend`.

**Keeping the ones worth keeping.** A roll is only as good as its luck, and
most of a roster is thrown away. `keep 1,3,4,12` writes those characters'
recipes to `roster.json`, and `make --from roster.json` builds exactly them
again, with no seed to remember: the same figure, skin, hair colour, outfit
and weapon. The file is JSON and is meant to be edited, which is how a
character changes its clothes or its hair without rolling anything.
`make --prune` then deletes the character folders the run did not write, so
what is left is that roster and nothing else.

**What a run writes**, under `output/daz/characters/<slug>/`: `<slug>_front.png`
and `<slug>_side.png`, `<slug>.json` with the roll, the two commands that
rebuild it, the exit codes, the seconds and the drawn pixel count of each view,
`<slug>_scene.json` from the probe, and the two logs. Beside them,
`characters.json` indexes the run and `roster_sheet.png` holds every character,
views side by side on a flat grey under a line naming what it is made of, at
`--sheet-cell` pixels a cell and `--sheet-columns` characters a row. All of it
is Daz content: gitignored, and never committed.

**Measured on 2026-09-21**, twelve characters in the rest pose at 768 px,
Cycles on the card at 128 samples, in `comfyui-packaged`: 10.3 to 25.5 s to
build each one and 2.1 to 3.1 s to draw its two views, 230.9 s and 30.9 s over
the twelve, every exit code 0, no garment left inside a body, and 8.1 MB kept
once the twelve `.blend` files, 71 to 179 MB each, were deleted. The sheet is
4096 by 1629 px.

### `daz_inventory.py`

```sh
scripts/daz_inventory.py DIRECTORY [--brief | --json]
scripts/daz_inventory.py --selftest
scripts/daz_inventory.py --sample DIR
```

DIRECTORY is a content library, such as `MODELS_DIR/daz_library`, or any folder
inside one, outside the repo.

- **Morphs, aliases and other modifiers.** A modifier whose channel type is
  `alias` is an alias, a second name for another modifier's channel, and is
  counted and grouped apart. A morph has a morph block, or a float or int
  channel, so controllers such as the visemes count. Anything else is an other
  modifier. Only morphs count toward the morph groups, and only morphs can be
  HD morphs.
- **Content types.** A figure file is still any `.dsf` with geometry. Its role
  comes from the `presentation.type` its author set: `Actor` is a body,
  `Follower/Attachment` an attachment, and `Follower/Wardrobe`,
  `Follower/Hair` and `Prop` wardrobe, hair and prop. Nothing in DSON tells an
  optional eyebrow style from face anatomy, or a projection template from real
  clothing.
- **Not DSON.** A `.dsf` that is valid JSON but not an object with a
  `file_version`, `asset_info`, `scene` or `*_library` key is skipped, listed
  under `NOT DSON, SKIPPED` and in `--json`'s `not_dson`, and does not change
  the exit status. Unreadable files still get a `skipped <file>: <reason>`
  line on stderr and exit 1.

Exit 0 when every `.dsf` was read or skipped as not DSON; 1 when a `.dsf` was
unreadable, a folder could not be listed, a link into the repo was skipped, or
a self-test check failed; 2 for a refused or missing path. On Genesis 9 Starter
Essentials at `/models/daz_library` on 2026-09-16 it exited 0 with nothing on
stderr in 2.79 to 2.84 s wall: 3210 `.dsf`, 1 of them not DSON, and 51 figure
files. `--selftest` passed 67 checks in 0.45 to 0.48 s wall.

## Where scripts run

Most call into the container. Two conventions matter:

**Container paths.** Nodes that read files from inside the container want
`/app/output/...` rather than a host path. `output/` is mounted at `/app/output`
and `input/` at `/app/input`. The scripts translate host paths automatically;
graphs do not.

**Blender lives in the container.** Sheet rendering, posing, decimation measuring,
weight transfer, `face_rig.py`, `bone_roles.py`, `mpfb_probe.py` and
`daz_import_probe.py` all run `python3` inside it. That is the only place in this stack with a glTF importer, an
FBX importer and a renderer together. Which of them reaches the graphics card
depends on the engine: measured in `comfyui-packaged` on 2026-09-16, EEVEE
there draws through llvmpipe, Mesa's software OpenGL, on the CPU
([DAZ Genesis, rendering](/reference/daz-genesis#rendering)), while Cycles finds
the card through CUDA and needs no GL context (2026-09-18). `render_sheet.py`
uses Cycles by default; `decimation_report.py`, `mpfb_probe.py` and
`daz_import_probe.py` rasterise with EEVEE, so they stay on the CPU.

**Some run only on the host.** `fetch_tools.py`, `daz_library.py` and
`daz_inventory.py` use only the standard library. `lipsync_cues.py` runs Rhubarb from `tools/`, so the
published image does not carry it, and needs ffmpeg. `compose_mouths.py` and
`preview_lipsync.py` need numpy and Pillow in the system `python3`, and the
preview needs ffmpeg and ffprobe.

**The container's name depends on how you started it:** `comfyui-packaged` for
the published image, `comfyui` or `comfyui-local` for a source build. The scripts
find whichever one is running, and `ASSET_ENGINE_CONTAINER` overrides the choice.
To run your own command in the same container:

```sh
docker exec "$(python3 scripts/_engine.py)" python3 -c "import bpy; print(bpy.app.version_string)"
```
