# Scripts

Everything in `scripts/`. Each takes `--help`.

## Setup and health

| Script | Does |
|---|---|
| `doctor.py` | Checks the whole stack and prints the one next step. `--fix` does the safe repairs. `--json` for tooling. |
| `setup.sh` | Clone nodes, seed, fetch weights, build, start, post install. Safe to re-run. |
| `fetch_models.py` | Check or download model weights by group. Stdlib only. |
| `postinstall.sh` | Node installs that have to happen inside the running container. |
| `patch_nodes.py` | Compatibility patches to the cloned node sources. `--check` verifies them. |
| `entrypoint.sh` | Container entrypoint. Seeds empty mounts, reports missing weights before starting. |
| `publish_image.sh` | Build and push the image to a registry. Local build on purpose, it is 27.6GB. |

## Running the pipeline

| Script | Does |
|---|---|
| `run_workflow.py` | Queue a graph, wait, report the outputs. |
| `validate_workflows.py` | Check every graph against a live server's node definitions. |
| `api_to_ui.py` | Convert graphs into the editor's format. `--check` verifies every value survived. |
| `build_presets.py` | Generate the drop in presets from base graphs plus the prompt library. |
| `generate_concepts.sh` | Generate a whole prompt folder in the house style. |
| `simplify_concepts.sh` | Redraw existing art as simpler game ready versions. |
| `asset_to_mesh.sh` | Concepts to shapes to textures to sheets to curated assets, correctly staged. |
| `rig_units.sh` | Rig figures one at a time, with the settings that work. |
| `list_animations.py` | What animation clips are actually installed, read from the files. |

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
| `cleanup.py` | Curate the keepers, then sweep the rest. |

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
has been curated.

## Where scripts run

Most call into the container. Two conventions matter:

**Container paths.** Nodes that read files from inside the container want
`/app/output/...` rather than a host path. `output/` is mounted at `/app/output`
and `input/` at `/app/input`. The scripts translate host paths automatically;
graphs do not.

**Blender lives in the container.** Sheet rendering, posing, decimation measuring
and weight transfer all run `python3` inside it. That is the only place in this
stack with a glTF importer, an FBX importer and a GPU renderer together.

**The container's name depends on how you started it:** `comfyui-packaged` for
the published image, `comfyui` or `comfyui-local` for a source build. The scripts
find whichever one is running, and `ASSET_ENGINE_CONTAINER` overrides the choice.
To run your own command in the same container:

```sh
docker exec "$(python3 scripts/_engine.py)" python3 -c "import bpy; print(bpy.app.version_string)"
```
