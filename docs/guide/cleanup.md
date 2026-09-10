# Curating and cleanup

This pipeline generates a lot of files. Most of them are by products. Four things
per asset are worth keeping: the concept image, the model, the texture maps, and
the sprite sheets.

```sh
scripts/cleanup.py                      # what is scratch, what is unclaimed
scripts/cleanup.py keep golem \
    --concept output/concept/golem_00001_.png \
    --model   output/mesh/golem_textured.glb \
    --rig     output/rigged/golem.fbx \
    --sheets  output/sheets/golem_walk.png
scripts/cleanup.py sweep --delete       # by products only
scripts/cleanup.py sweep --delete --unclaimed
```

Curated assets land in `output/assets/<name>/` as `concept.png`, `model.glb`,
`rig.fbx`, `textures/`, `sheets/` and `sources.json`.

## Keep copies, it does not move

This is deliberate and it is not paranoia. The bug that made this design
necessary deleted a concept image during testing, and only the copies survived.

A curated asset is safe from a mistaken sweep because the sweep operates on the
originals, and the curated folder holds copies.

## What `sources.json` is for

`keep` renames files as it copies them. `concept.png` in the asset folder was
`qwen_00002_.png` in the concept folder.

So a filename match cannot tell whether an original has been claimed. Without a
record, `--unclaimed` would cheerfully offer to delete the very files you just
curated. `sources.json` records the original paths, which is what makes the
unclaimed check safe.

## Two levels of deletion

`--delete` on its own removes only by products that a re-run recreates. Safe.

`--unclaimed` is permanent. It removes generated files that no curated asset
claims. It refuses to run when nothing has been curated, because that would mean
deleting everything.

## Do the curating as you go

The temptation is to generate twenty assets and tidy at the end. By then you
cannot remember which of six similar meshes was the good one, and the texture
maps have been overwritten five times over, because the texture stage always
writes to the same paths.

Curate each asset when it is finished. The batch script does this automatically
as its last stage, which is another reason to use it.
