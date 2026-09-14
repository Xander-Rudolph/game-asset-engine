# Curating and cleanup

The pipeline generates lots of files, and most of them are by products. Four
things per asset are worth keeping: the concept image, the model, the texture
maps, and the sprite sheets.

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

## `keep` copies, it does not move

This is intentional, and it was learned the hard way. A bug deleted a concept
image during testing, and only the copies survived.

A curated asset is safe from a mistaken sweep. The sweep never touches
`output/assets/`, and the files there are copies, so they survive when an
original is deleted.

## What `sources.json` does

`keep` renames files as it copies them. `concept.png` in the asset folder is a
copy of `qwen_00002_.png` in the concept folder.

Filenames alone can't tell if an original was curated. Without a record,
`--unclaimed` would offer to delete the originals you just curated.
`sources.json` records the original paths so the unclaimed check stays safe.

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
