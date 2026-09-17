---
name: research-note
description: Write or revise a page under docs/, such as a research note in docs/reference/ or a guide or reference page, so it states only what was checked and is wired into the site. Use when adding a page to docs/, turning research on a tool, model, format or asset base into a docs/ page, or changing what a docs/ page claims.
---

# Research note: a docs/ page that says only what was checked

The writing, evidence and licence rules are in `CLAUDE.md`. Follow them; this skill does not repeat them.

## 1. Shape

Take the shape from `docs/reference/lip-sync.md`, `docs/reference/source-filmmaker.md` and `docs/reference/daz-genesis.md`:

- Straight under the title, `::: tip Status: researched on <date>`. Say what was run and where (host or container), what was only read, and that nothing proposed is built. End it with a link to the register on GitHub, in the `https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/claims/<note>.json` form the three notes use, because the site does not serve `research/`.
- The answer in brief next, then the body.
- A `## Licences` section (the heading may carry a subtitle), with weights, code, content and assets, generated output and hosted-service terms kept apart, each dated. Establish every licence claim with the `licence-audit` skill.
- Then `## What not to do`, `## What to build`, `## Honest uncertainty` and `## Sources worth reading`.

A guide or reference page keeps only the sections that apply, but still says what was measured and what was read without running it.

## 2. Claim register

- A research note has a register at `research/claims/<note>.json`, with the same base name. `research/README.md` gives the fields, the claim ids (one prefix per note, such as `LIP-001`) and the five statuses.
- A register holds what was read from a source outside this repo: a licence, a model card, a spec, a forum post. A number measured on this machine by a script in this repo needs no claim id. Date it, and name the script and command that produced it, as every guide does. Say it was measured, not read.
- Update the register first and the page second. A page never states a claim more strongly than the register does: a `corrected` claim only in its `claim` wording, never `as_first_reported`, and an `unsettled` one only as unsettled, with both readings.
- Cite the ids behind each sentence, or table cell, as an HTML comment at its end, such as `<!-- LIP-001 -->` or `<!-- DAZ-001, DAZ-018 -->`. Change the comment whenever the sentence changes.
- Revising a page: read the ids behind each sentence you change, and re-check before you strengthen one.

## 3. Wire it in

- Add the page to the hand-kept sidebar in `docs/.vitepress/config.ts`: the Research group for a research note, otherwise the Reference group or the matching Guide group.
- Link sibling notes where they overlap, as the three notes above do.
- Renamed or removed a heading? The docs build fails on a link to a missing page but not on a link to a missing `#anchor` (VitePress 1.6.4, tested 2026-09-16). Grep for the old anchor and fix every hit (`git grep` skips the built site in `docs/.vitepress/dist`):

```sh
git grep -n --untracked '#old-anchor' -- docs skills README.md CLAUDE.md
```

## 4. Check

```sh
PAGE=docs/reference/lip-sync.md                # the page you changed
python3 scripts/check_docs_sync.py             # must exit 0
python3 scripts/check_vendored_licences.py
LC_ALL=C.UTF-8 grep -nP '[\x{2013}\x{2014}]' "$PAGE"     # must print nothing
grep -nwE 'color|colors|colored|behavior|normalize|normalized|normalizing|license|licenses' "$PAGE"
npm run docs:build
```

The spelling grep prints candidates: read each hit, because license is right as a verb and exact strings such as `--licenses` stay as they are. Run the status check at the end of `research/README.md` if you touched a register.

## 5. Leave owner decisions alone

If the research bears on an open decision listed under "Owner decisions" in `CLAUDE.md`, record what was found under "Honest uncertainty" and ask the owner in one line. Do not settle it in the page.
