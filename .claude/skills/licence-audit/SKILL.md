---
name: licence-audit
description: Establish and record what a model, node pack, library, command-line tool, asset base or hosted service may be used for in a commercial game, before it is added to the repo or written about. Use when adding weights to models.json, a node pack or package to the Dockerfile, a tool to tools.json, or when a page, skill or graph comment states a licence.
---

# Licence audit: read the text, date it, record it everywhere at once

The licence rules are in `CLAUDE.md` under "Licences". This is how to establish a licence and record it.

## 1. Start from what the repo already says

```sh
scripts/fetch_models.py --licenses        # weights; !! forbids commercial use, ! has conditions
git grep -niF --untracked 'NAME' -- models.json tools.json NOTICE CREDITS.md Dockerfile README.md docs skills workflows/api scripts
git grep -liF --untracked 'NAME' -- research/claims     # registers are large; open the claim by id
```

`git grep` skips the gitignored build in `docs/.vitepress/dist`, which plain `grep -r` would read.

## 2. Read the licence itself

- Licence text is whatever the rights holder published: a LICENSE or COPYING file, per-file headers, the README, the model card, or a terms page or EULA. Read it on disk, inside the image (`docker exec "$(python3 scripts/_engine.py)" ...`) or upstream. Quote the clause that decides the question, and record the date and the release or commit you read.
- A Hugging Face Hub cardData licence or a GitHub detected licence that disagrees with the licence file is only a reason to open the licence file, never evidence on its own.
- A licence stated only in metadata the rights holder wrote, with no licence file, is recorded as exactly that, as `docs/guide/licensing.md` does for ComfyUI-mesh2motion: "MIT, declared in metadata, no licence file shipped".
- If you find no licence text anywhere, record that none was found and treat the thing as all rights reserved, the reading SFM-121 in `research/claims/source-filmmaker.json` records for GitHub repositories with no licence. Do not infer a licence from a badge or a tag alone.

## 3. Keep the layers apart

Record separately: **weights**; **code** (including anything it vendors or loads, which a root licence may not cover); **content and assets** (meshes, textures, sample files, documentation and wiki text); **generated output**; and **hosted-service terms**. For each, note territory, revenue thresholds, non-commercial or research-only use, attribution, and whether the terms can be amended or revoked.

## 4. Record the claim

For research, add each licence claim to the note's register in `research/claims/`, checked through both the `text` and `drift` lenses that `research/README.md` describes. If the two disagree the status is `unsettled`, and every page says unsettled.

## 5. Update every file that states it, in one change

- `models.json`: `license`, `license_url` and `commercial`, which `--licenses` reads
- `docs/guide/licensing.md`, and `docs/guide/redistributing.md` if it ends up in the image
- `docs/reference/models.md` ("Licences in one line each" and the groups table) and the rows in `docs/reference/workflows.md`
- `NOTICE`, `CREDITS.md` and `docs/credits.md`
- the `org.opencontainers.image.licenses` label in `Dockerfile`, if the image's contents change
- every other page, table row, skill, graph `_comment`, `NOTES` entry or script `--help` that the first grep in step 1 finds

This list lives here only; `land-a-change` links to it.

## 6. Prove research-only code is not reached

If a route must avoid a package whose licence rules out commercial use, block its import and run the route once, as "The vertex-colour route" in `docs/guide/trellis.md` records. Put a finder that raises `ImportError` for those names first on `sys.meta_path`, and check that none of them is already in `sys.modules`, or the finder never fires. In ComfyUI the server imports its node packs at start-up, so the block has to be in place before that, not added to a running server. A reading of the code is not a runtime check, so say which one you did. Queue a generation only with the owner's go-ahead.

## 7. Check

- Never soften a territorial, revenue or non-commercial clause while rewording. Quote it instead.
- Run `python3 scripts/check_vendored_licences.py`, then repeat the first grep in step 1 and read every hit for a statement the change contradicts.
