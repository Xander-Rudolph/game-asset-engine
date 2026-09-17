# Research

Research notes live on the docs site, in `docs/reference/`. What each statement in a note rests on, and what checking it found, lives here.

| Folder | Holds |
|---|---|
| `claims/` | One claim register per research note, as JSON |
| `experiments/` | Run artefacts, owned by whoever runs them. Do not edit or tidy someone else's |

`untested.md` lists what was built but not tested for real, and the owner decisions still open.

## One register per note

A register is `claims/<note>.json`, with the same base name as `docs/reference/<note>.md`, and its `note` key holds that path.

| Note | Register | Claim ids |
|---|---|---|
| `docs/reference/source-filmmaker.md` | `claims/source-filmmaker.json` | `SFM-001` onwards |
| `docs/reference/lip-sync.md` | `claims/lip-sync.json` | `LIP-001` onwards |
| `docs/reference/daz-genesis.md` | `claims/daz-genesis.json` | `DAZ-001` onwards |

A claim id cited in a note, such as `LIP-001`, names the register by its prefix and the claim by its `id` field. Ids are unique within a register. `conflicts_found` and `conflicts_with` refer to claims by the same ids.

What a register does not hold: numbers measured on this machine by the repo's own scripts. A note states those with their date and the command that produced them, with no claim id, the way the guides do.

## What a register holds

Six top-level keys:

| Key | Holds |
|---|---|
| `note` | The note's path, such as `docs/reference/lip-sync.md` |
| `researched` | The date the research was done |
| `checked` | The date, or range of dates, the checks ran |
| `statuses` | How many claims carry each status |
| `conflicts_found` | One line per contradiction between claims, as `ID vs ID: what differs` |
| `claims` | The claims |

Each claim carries:

| Field | Holds |
|---|---|
| `id` | The claim id, such as `DAZ-001` |
| `status` | One of the five statuses below |
| `kind` | `licence`, `fact`, `capability` or `recommendation` |
| `load_bearing` | `true` when a conclusion in the note depends on it |
| `claim` | The wording the note may use. Once a claim is checked, this is the checked wording |
| `sources` | The pages, files and repo paths it was read from |
| `as_first_reported` | The researcher's wording before any check. Present on every checked claim, and never edited |
| `checks` | One entry per check, each with `lens`, `verdict` (`confirmed` or `refuted`), `read` (what the checker read), `evidence` and `notes` |
| `conflicts_with` | Only on a claim in a contradiction: the other ids, and what differs |

## The five statuses

| Status | Means | How the note may state it |
|---|---|---|
| `confirmed` | Every check confirmed it | As a fact, dated and linked |
| `corrected` | Every check refuted part of it as first reported. `claim` holds the corrected wording | Only in the corrected wording |
| `unsettled` | A licence claim whose two checks disagreed: one lens confirmed it and the other refuted it | Only as unsettled, giving both readings |
| `unverifiable` | No check could settle it either way. It has no `checks` | Not as a checked fact |
| `unchecked` | Minor, and never checked: a fact or capability that is not load-bearing, or a recommendation. It has no `checks` | As a report, marked as not checked |

A note never states a corrected or unsettled claim more strongly than its register does.

## How claims were checked

- **Every licence claim**, load-bearing or not, was checked twice, through two lenses, in this order:
  1. `text`, the primary text. The claim is read against the licence, EULA or terms page itself. Every quoted clause must appear there as quoted, and the claim must say no more than the text does.
  2. `drift`, drift and conflation. Has the text changed since the date on the claim, across dated snapshots, releases or versions? And does the claim run two things together, such as the code and the weights, a non-binding summary and the binding text, or two products that share a name?
- **Every load-bearing fact or capability** was checked once, through the `fact` lens, against its sources, or marked `unverifiable`.
- **Minor facts and capabilities, and recommendations**, were not checked, and stay `unchecked`.

## Changing a register

- A new check updates the register first, and the note second. Add the entry to `checks`, set `status`, put any corrected wording in `claim`, and bring `statuses` and `checked` up to date. Leave `as_first_reported` as it is.
- Quote only what a check needs as evidence. Never copy third-party code or licence-restricted content into `research/`.
- Research notes are written with the `research-note` skill in `.claude/skills/research-note/`, and licence claims are checked with `.claude/skills/licence-audit/`.

Every claim's status must be one of the five above, and `statuses` must match the claims. Run from the repo root, this prints the counts per register and exits 1 on anything else:

```sh
python3 -c "import json,glob,collections as c; ok={'confirmed','corrected','unsettled','unverifiable','unchecked'}; [print(f, dict(n)) or (set(n) <= ok and n == c.Counter(d['statuses']) or exit(f + ': bad status or stale statuses')) for f in sorted(glob.glob('research/claims/*.json')) for d in [json.load(open(f))] for n in [c.Counter(x['status'] for x in d['claims'])]]"
```
