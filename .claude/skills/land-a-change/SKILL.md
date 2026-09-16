---
name: land-a-change
description: Finish a change to this repo so nothing that lists it is left behind, whether a skill, graph, script, weight or docs page was added, renamed or removed. Use before committing, or when asked to land, wrap up or check that a change to this repo is complete.
---

# Land a change

## 1. Required first: the sync check

```sh
python3 scripts/check_docs_sync.py        # must exit 0; fix every line it prints
```

It checks the skill tables and counts, graph `_comment`s, `docs/reference/workflows.md` rows, the `NOTES` in `scripts/api_to_ui.py`, `docs/reference/scripts.md` rows and the sidebar. Below is only what it cannot check.

## 2. An end-user skill in `skills/`

- Add its subject to the `description` and `keywords` in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
- Run `claude plugin validate .` and `claude --plugin-dir . plugin details game-asset-engine`, then copy the inventory and token lines into `docs/guide/claude.md` and the count into `CLAUDE.md`.
- The script checks only those counts, so grep for the old count word too, such as `git grep -niw --untracked seven -- README.md CLAUDE.md docs skills .claude-plugin` when a seventh skill becomes an eighth (`git grep` skips the built site in `docs/.vitepress/dist`).
- A maintainer-only skill goes in `.claude/skills/` and must leave that inventory unchanged.

## 3. A graph in `workflows/api/`

- Edit the API JSON only, never a preset or `workflows/default/workflows/`.
- Make the `_comment` match measured behaviour, and name the run that measured it.
- Run `scripts/build_presets.py` to regenerate the presets from the base graphs, then `scripts/build_presets.py --check`, then `scripts/validate_workflows.py` against the live server. It checks node types, widget names and required inputs, so a valid graph wired to the wrong node still passes.
- Add a `NOTES` entry, then run `scripts/api_to_ui.py --check`.
- Queue it once, and only with the owner's go-ahead.

## 4. Hand-offs

- Weights, a node pack, a tool or a hosted service: use the `licence-audit` skill, whose step 5 is the one list of files that state a licence.
- A page under docs/: use the `research-note` skill.

## 5. Last

Run `python3 scripts/check_vendored_licences.py` and `npm run docs:build`.
