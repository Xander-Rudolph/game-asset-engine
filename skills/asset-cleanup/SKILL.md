---
name: asset-cleanup
description: Keep only the finished parts of a generated asset - concept image, model, textures and pose sheets - and sweep the intermediates. Use when the user asks to clean up, tidy, prune or free space in the asset pipeline, or when a run has finished and the working files are no longer needed.
---

# Asset cleanup: curate, then sweep

Work in the asset-engine repo root. The tool is `scripts/cleanup.py`.

A finished asset is four things: the **concept image**, the **model**, its
**textures**, and its **pose sheets**. Everything else under `output/` is
working material.

**Nothing on disk records which concept produced which mesh** — filenames are
counters and timestamps (`qwen_00002_.png`, `Hunyuan21_2026-09-08-15-10-01.glb`).
So the tool never infers. You name the keepers, they are **copied** into
`output/assets/<name>/`, and only then is anything removed.

## Before you start

```sh
scripts/doctor.py --skip-models --quiet || scripts/doctor.py --skip-models
```

Cleanup does not need the GPU, but it does need `output/` to be readable and
owned by you. If the doctor reports the folders are not writable, files were
written by a container running as root, and deleting them will fail partway
through. Fix `PUID` and `PGID` in `.env` first.

## Order of operations, do not reverse it

### 1. Look

```sh
scripts/cleanup.py
```

Two lists. **SCRATCH** is by-products with no judgement attached — per-frame
renders that were composed into a sheet, unlit silhouette checks, TexGen's
working directory, UV `.npz` files, run logs. **UNCLAIMED** is everything
generated that has not been curated.

### 2. Curate

Work out which files are the keepers before running this. If unsure which mesh
or concept the user means, **ask** — a wrong answer here is what makes the sweep
destructive.

```sh
scripts/cleanup.py keep <name> \
    --concept output/concept/qwen_00002_.png \
    --model   output/mesh/textured_2026-09-08-22-22-18.glb \
    --rig     output/rigged_1788911741_articulationxl.fbx \
    --sheets  output/sheets/<name>_walk.png output/sheets/<name>_attack.png
```

- **Prefer the textured model** over the shape-only one. A `.glb` embeds its
  textures; sidecar maps beside the model (`_albedo`, `_metallic`, `_roughness`,
  `.mtl` for an `.obj`) are picked up automatically, and `--textures` adds any
  that live elsewhere, such as Hunyuan TexGen's `output/Hun2-1/`.
- `--rig` is optional; include it whenever a rigged FBX exists, since it is the
  only thing that can be animated.
- This writes `sources.json` recording the original paths. That file is what
  makes step 3 safe: `keep` **renames** as it copies (`concept.png`,
  `model.glb`, `rig.fbx`), so without it the originals would not be recognised
  as claimed and would be offered for deletion.

### 3. Sweep

```sh
scripts/cleanup.py sweep                      # dry run, always
scripts/cleanup.py sweep --delete             # scratch only
scripts/cleanup.py sweep --delete --unclaimed # also uncurated files
```

- **`--delete` alone is safe** and needs no permission dance: it removes only
  by-products that re-running a step recreates.
- **`--unclaimed` is not.** It deletes rejected concepts, superseded meshes and
  diagnostic renders permanently. Show the user the list and get an explicit yes
  before using it. It refuses outright if nothing has been curated.

## Rules

- **Never sweep before curating.** With no `output/assets/` entries every file
  is unclaimed, which is why the tool refuses that combination.
- **Report what was freed and what was kept**, not just that it ran.
- `keep` copies rather than moves, on purpose: an interrupted or mistaken sweep
  cannot destroy a curated asset.
- Curated assets live in `output/assets/<name>/` — `concept.png`, `model.glb`,
  `rig.fbx`, `textures/`, `sheets/`, `sources.json`. That folder is what gets
  moved into the game; everything else is disposable.
- `output/` is gitignored in full, so curated assets are **not** in version
  control. Copy them into the project proper when they are final.
- Run logs belong in `logs/`, not the project root. `setup.sh` and
  `postinstall.sh` tee there automatically; redirect other long runs there too.
  The sweep treats `logs/` as scratch.
