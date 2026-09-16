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
| `list_animations.py` | What animation clips are actually installed, read from the files. |
| `bone_roles.py` | Name an articulationxl rig's `bone_N` bones by role (pelvis, chest, head, left thigh and so on) with `map`, then `compile` a role pose from `poses/roles/` into that rig's transforms file for `render_sheet.py`. `probe` says which way each part moved. See [below](#bone-roles-py). |
| `generate_music.py` | Generate a folder of music prompts with ACE-Step 1.5. `--loop DIR` makes each take a seamless loop, and `--keep-best` keeps the take that loops best. Resumable: seeds already in `DIR/picks.json` are skipped, and `--reloop` loops the recorded takes again without generating. A take the server already made, for a run that died, is used rather than made again, and `--no-wait` queues the missing takes and exits. A track file can carry a section script as its lyrics, after a line of `---`. |

## Looking at results

| Script | Does |
|---|---|
| `render_sheet.py` | Render a model to a sprite sheet. Angles across, poses down. |
| `decimation_report.py` | Measure what each face budget costs, three ways, or bisect for an answer. |
| `sheet_check.py` | Check a sprite sheet for the faults that are arithmetic. Exits non-zero on a fault. |
| `transfer_weights.py` | Move a skeleton from a decimated proxy onto the original mesh. |
| `normalise_mesh.py` | Scale a mesh to a declared world size and record the rule. `--check` gates a whole folder. |
| `make_seamless.py` | Make a texture tile, and say whether it worked. |
| `cut_icon.py` | Cut an icon out of its background and size it for a UI. |
| `make_loop.py` | Make a music track loop without a seam at a set loudness: it chooses where in the take the loop starts and ends, keeps any silence in the take out of the loop, and reports what you would hear where it comes round. |
| `cleanup.py` | Curate the keepers, then sweep the rest. Folders `keep` cannot claim, such as music takes, icons and mouth sets, are protected from the sweep. `keep --generator --source --licence --licence-url` records provenance rows in `sources.json`. |

## Faces and lip sync

What these are for, and what was measured, is in [lip sync and talking portraits](/reference/lip-sync).

| Script | Does |
|---|---|
| `lipsync_cues.py` | Mouth cues for voice lines. Runs Rhubarb Lip Sync from `tools/` on the host, refuses a line that fails its speech gate, and writes a timeline JSON to `output/lipsync/`. `--fps N` adds one mouth shape per frame, and `--text-only` writes a placeholder flap for a line with no voice yet. Needs ffmpeg. See [below](#lipsync-cues-py). |
| `make_mouths.py` | Make a talking portrait from a concept with `--portrait-from`, then, once it is approved and the mouth box chosen, one whole-image edit per mouth shape through `img_edit_qwen.json`, and compose them. Before every edit it waits until no Blender job is running and the ComfyUI queue is empty. The box is checked before any edit is queued, and a shape whose edit exists is skipped, so a stopped run resumes. |
| `compose_mouths.py` | Cut the mouth box out of each edit into `mouth_<S>.png` overlays and a `manifest.json`, and measure drift in a ring round the box. `--check MANIFEST` fails unless no pixel outside the box changes, every size matches and A to F are present. Host, numpy and Pillow. |
| `preview_lipsync.py` | Play a mouth set against a timeline as an MP4, with the line's audio when there is some, and lay the mouths out on a labelled contact sheet. A shape the set lacks plays Rhubarb's fallback. Needs ffmpeg and ffprobe. |
| `face_rig.py` | Give a rig a face in Blender. `add-jaw` adds a jaw bone under the head, weighted by rule, turns it 20 degrees as a check, and writes nothing when that barely moves the mesh. `transfer-shapes` copies a template head's shape keys onto a model with Surface Deform, and `spheres` writes the test files the method was proved on. A generated mesh has no parted lips, so the jaw stretches the lower face rather than opening a mouth. |
| `mpfb_probe.py` | Probe MPFB 2, MakeHuman's Blender add-on, in the container's Blender. `fetch` downloads the add-on and three face packs, pinned by size and sha256, into the gitignored `input/_devtools/mpfb2/`. `build` makes a body with the 15 Meta/Oculus-style visemes as shape keys, as a `.blend` and a `.glb` in `output/mpfb/`, and `render` draws one viseme per row. `--help` records the licences as read and what was measured. |
| `daz_inventory.py` | List the figures, bones, morphs and HD morphs in a Daz content library installed outside this repo, reading every `.dsf` with the standard library. It refuses a path in or above the repo. Not yet run on a real library, because none is installed here: `--selftest` and `--sample DIR` use an invented one. Why it exists is in [DAZ Genesis](/reference/daz-genesis). |

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
                        [--elevation DEG] [--size PX] [--zoom N] [--persp]
                        [--span UNITS] [--key N] [--ambient N] [--clay]
                        [--clay-color R,G,B] [--flat] [--out PATH] [--check]
                        [--keep-frames] [--timeout SECONDS]
```

`--poses` takes `static`, `frames:1,7,13`, `even:N` or `transforms:FILE`.

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
`mpfb/`) unless `--include-protected` is given too.

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

## Where scripts run

Most call into the container. Two conventions matter:

**Container paths.** Nodes that read files from inside the container want
`/app/output/...` rather than a host path. `output/` is mounted at `/app/output`
and `input/` at `/app/input`. The scripts translate host paths automatically;
graphs do not.

**Blender lives in the container.** Sheet rendering, posing, decimation measuring,
weight transfer, `face_rig.py`, `bone_roles.py` and `mpfb_probe.py` all run
`python3` inside it. That is the only place in this stack with a glTF importer, an
FBX importer and a renderer together. The renderer is not the graphics card:
measured in `comfyui-packaged` on 2026-09-16, EEVEE there draws through
llvmpipe, Mesa's software OpenGL, on the CPU
([DAZ Genesis, rendering](/reference/daz-genesis#rendering)).

**Some run only on the host.** `fetch_tools.py` and `daz_inventory.py` use only
the standard library. `lipsync_cues.py` runs Rhubarb from `tools/`, so the
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
