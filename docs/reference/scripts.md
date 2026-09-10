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
| `publish_image.sh` | Build and push the image to a registry. Local build on purpose, it is 27.5GB. |

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
| `decimation_report.py` | Measure what each face budget costs, three ways. |
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
                        [--key N] [--ambient N] [--clay] [--clay-color R,G,B]
                        [--flat] [--out PATH]
```

`--poses` takes `static`, `frames:1,7,13`, `even:N` or `transforms:FILE`.

`--span <units>` frames against a fixed world height rather than the subject's
own extent, which is what makes a set share a scale. Without it each model is
framed to its own bounding box, so a wrong scale renders perfectly.

Defaults are the isometric camera: elevation 30, first facing at 45 degrees,
orthographic. See [facings](/guide/facings).

### `decimation_report.py`

```sh
scripts/decimation_report.py MODEL [--target-iou IOU] [--sweep] [--faces LIST]
                             [--sprite PX] [--floor-faces N] [--max-iters N]
                             [--elevation DEG] [--azimuth DEG] [--json PATH]
```

`--target-iou` bisects for the lowest face count that holds the silhouette above
the threshold and prints an answer. `--sweep` forces the full table instead.

Pass `--sprite` at the size the asset is really seen at. Judging a budget at 340
pixels and shipping at 128 wastes geometry.

### `normalise_mesh.py`

```sh
scripts/normalise_mesh.py MODEL... (--height UNITS | --footprint UNITS)
                          [--out-dir DIR] [--suffix S] [--check] [--tolerance F]
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
and weight transfer all run `docker exec comfyui python3`. That is the only place
in this stack with a glTF importer, an FBX importer and a GPU renderer together.
