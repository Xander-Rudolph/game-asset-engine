# Game Asset Engine

Driving the pipeline? The skills carry it, and every one starts with `scripts/doctor.py`. Editing the repo? These rules apply. Only Claude running in this repo root reads this file; installed-plugin users never load it.

## Where things live

- `skills/` ships to every plugin installer, and every description costs always-on tokens. Measure the cost with `claude --plugin-dir . plugin details game-asset-engine` after changing a description, rather than quoting an old figure.
- Maintainer skills go in `.claude/skills/`, which installers never load. Anything at the plugin root, `.mcp.json` included, starts for every installer.
- MCP: do not add a server that repeats `run_workflow.py`, `validate_workflows.py`, `doctor.py`, `fetch_models.py` or `gh`. Personal servers stay at user scope with `${VAR}` keys.
- `research/claims/` holds the claim registers behind the research notes in `docs/reference/`; `research/README.md` explains them.
- `tools/` is the gitignored cache of command-line tools that `scripts/fetch_tools.py` fetches from `tools.json`.
- The Daz content library lives at `MODELS_DIR/daz_library`, outside the repo, installed by `scripts/daz_library.py`. `output/daz/` holds Daz content: its 3D data is never curated (`cleanup.py keep` refuses it), and nothing in it is ever committed.
- `docs/` is the VitePress site. `CREDITS.md` mirrors `docs/credits.md`, with absolute links.

## The container

- Resolve the container name with `scripts/_engine.py`; never hardcode it in a script. The `packaged` profile is the default.
- `scripts/validate_workflows.py` and `scripts/api_to_ui.py` need a live server, because they read `/object_info`.
- Never restart the container while someone else's jobs may be queued (check `/queue`), and never run `docker image prune -a`.
- Host scripts run on the system `python3`. `.venv` is only the notebook kernel and has no numpy.

## Generated files

Regenerate them, never hand-edit: the presets (`scripts/build_presets.py`, confirmed with `--check`), the editor graphs in `workflows/default/workflows/` (`scripts/api_to_ui.py`, plus a `NOTES` entry for a new graph) and the notebook (`notebooks/build_notebook.py`).

## Writing

- en-GB: licence as a noun, license as a verb, colour, normalise. No em dashes or en dashes anywhere.
- Keep exact error strings exact and measured facts as facts. Stay engine-neutral: no game engine is assumed.
- When a claim changes, grep beyond `docs/`: `skills/`, `README.md`, graph `_comment` fields, the `NOTES` in `scripts/api_to_ui.py` and each script's `--help`.

## Evidence

- Every number carries the tool or run that produced it, and says whether it was measured, run, or read and not run.
- Re-measure before rewriting a number. A number with no source is removed or re-measured, never replaced by another guess.
- Reference machine: RTX 4070 Ti SUPER 16 GB, i7-14700K, 31 GB RAM, 16 GB tmpfs on `/tmp` (nvidia-smi, lscpu, free -g and df -h, 2026-09-16).

## Licences

- Never vendor third-party code or copy licence-restricted content into the repo. Link to it and describe it.
- Never put Valve or Daz content in the repo: no SDK code, no game or store assets, and nothing compiled or exported from them.
- Research notes follow `.claude/skills/research-note/`, and a note never states a claim more strongly than its register in `research/claims/`.

## AUDIT.md

A backlog, not a guide. List it with `grep '^### ' AUDIT.md` and read only the finding you need; never read it whole, rewrite it or delete a finding. Re-check a "fixed" marker before trusting it.

## Owner decisions

Open, and not to be settled in passing (ask in one line, or open an issue): the face budget (18,000 in the docs, 48,000 in the graphs, per AUDIT.md "Read this one first"), the Meshy MCP server at the plugin root, the address compose publishes port 8188 on, the AGPL question for a hosted image, whether Claude may read a Daz render from `output/daz/` into a conversation (none is read until then), and whether the TripoSG and TripoSR graphs stay.

## Before a commit

Run `scripts/check_docs_sync.py`, `scripts/check_vendored_licences.py` and `npm run docs:build`.

## Commits

Follow `git log`: an imperative sentence-case subject, `Close #N: ...` when it closes an issue, and a prose body saying what was verified and what was not.
