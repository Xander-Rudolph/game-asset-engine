# Installing it for Claude

This repo is a Claude Code plugin. It ships six skills that drive the pipeline
and the MCP server definitions that go with them.

## Install

Installing from GitHub goes through a marketplace: the first command registers
this repo as one, the second installs the plugin from it.

**In a Claude Code session:**

```
/plugin marketplace add Xander-Rudolph/game-asset-engine
/plugin install game-asset-engine@game-asset-engine
```

**Or from a shell:**

```sh
claude plugin marketplace add Xander-Rudolph/game-asset-engine
claude plugin install game-asset-engine@game-asset-engine --scope user
```

`--scope` is `user` (you, everywhere), `project` (committed, shared with
collaborators) or `local` (you, this repo only).

Or skip installing entirely and run Claude Code from the repo root, which finds
`skills/` without any setup. That is the better option while you are still
editing the repo, because you are always testing what is on disk.

::: tip A private repo works, if git does
The clone uses your git credentials, so a private repo installs fine when your
GitHub CLI or SSH auth is already set up. If it is not, the marketplace add
fails at the clone rather than saying anything about permissions.
:::

## Check it took

```sh
claude plugin list
claude plugin details game-asset-engine@game-asset-engine
```

The second prints the component inventory and what each skill costs in tokens:

```
Component inventory
  Skills (6)  asset-cleanup, asset-pipeline, concept-edit, ground-texture, mesh-budget, pose-sheet
  MCP servers (1)  meshy

Projected token cost
  Always-on:   ~714 tok   added to every session
```

Skills are discovered from `skills/<name>/SKILL.md`. You do not list them in
`plugin.json`.

## If you are packaging your own

Two manifests, and missing the second is the one that bites:

- `.claude-plugin/plugin.json` describes the plugin.
- `.claude-plugin/marketplace.json` is what makes the repo installable **from
  GitHub**. Without it, `marketplace add` fails with `Marketplace file not found`
  even though the plugin itself is perfectly valid.

Check both before pushing:

```sh
claude plugin validate .
claude plugin validate .claude-plugin/marketplace.json
```

## You do not invoke skills by name

Skills are selected from their `description` frontmatter, so you describe what
you want in ordinary language and the right one is chosen.

| Say something like | Runs |
|---|---|
| "make me a mossy stone golem for the map" | `asset-pipeline` |
| "use that one but swap the shoulder pauldron" | `concept-edit` |
| "render walk and attack sheets for the golem" | `pose-sheet` |
| "I need a tileable swamp ground texture" | `ground-texture` |
| "how many faces should this be", "rig this 600k mesh" | `mesh-budget` |
| "tidy up, I'm done with this asset" | `asset-cleanup` |

That is why the descriptions are written from your side rather than the
implementation's. If you add a skill, write its description as the words someone
would actually say.

## What happens first, every time

Every skill runs `scripts/doctor.py` before doing anything.

This is not ceremony. Almost every confusing failure in this pipeline is one of a
handful of ordinary things: no GPU runtime, no `.env`, the container stopped,
weights missing, Blender not importable, sparse convolution broken. Each of them
surfaces much later disguised as a broken workflow. Two seconds of checking
removes the guessing, and if something is missing the skill walks you through it
rather than guessing around it.

## How the skills are meant to behave

Worth knowing, because it is how you tell when something has gone wrong.

**One stage per turn.** Concept art is shown and approved before a mesh is built,
and the mesh before a rig. The gates are deliberate: a rejected mesh three stages
later costs far more than a rerolled image, which takes thirty seconds. If Claude
runs two stages without asking, that is a bug, not efficiency.

**It shows you the picture.** Every generated image is read back into the
conversation. A printed file path is not a result, and a skill that reports one
has skipped the only check that matters.

**It checks instead of assuming.** Face counts, body counts, bone names and node
availability are read off the running server and the real files. Nothing is
described from memory. The commands to do that are written into each skill, so
you can run them yourself.

**It says what it chose and why.** Which generator, which camera angle, what it
added to your prompt. Generator choice in particular has licensing consequences,
so it should never be silent.

## Bring your own art direction

The prompt library ships **technique**, not a look.

Each `prompts/*/_style.txt` carries the clauses that make an image convert cleanly
to 3D: one subject, whole thing in frame, plain background, even lighting, large
readable shapes, clean hems. Every one of those is preventing a specific failure.
In the middle sits an `<<< ART DIRECTION: ... >>>` slot.

Put your project's style in that one phrase and change nothing else. The style is
composed with the subject when a generation runs, so it is genuinely one file.

`prompts/examples/` holds one project's filled-in version, so you can see what a
finished art direction looks like. Nothing in the default path reads from it.

::: tip This is the part worth getting right
A shared style file is the highest-leverage place to contaminate a whole asset
set. Bake a house style into the default and every generation silently carries
it. That is why the technique and the art direction are separated here rather
than written as one paragraph.
:::

## MCP servers

`.mcp.json` declares what this repo expects. Keys come from the environment,
never from the repo:

```sh
export MESHY_API_KEY=...
```

Meshy is a hosted service, so it complements this pipeline rather than being part
of it. It is useful when you want a mesh without a local GPU, or to compare a
hosted generator against the local one. It costs credits per call, and its
exports are photogrammetry scale, often around two million triangles, which is
far more than anything here produces. See
[face counts and decimation](/guide/decimation) before importing one.

## The skills

| Skill | For |
|---|---|
| `asset-pipeline` | Prompt to rigged model, with a gate at every stage |
| `concept-edit` | Change one element of an approved image without redrawing it |
| `pose-sheet` | Sprite sheets, facing sheets, and authoring bone poses |
| `ground-texture` | Tileable terrain, and fixing seams |
| `mesh-budget` | Face counts, decimation, rigging heavy meshes |
| `asset-cleanup` | Curate the keepers, sweep the rest |

## Writing your own

Put it in `skills/<name>/SKILL.md` with frontmatter:

```markdown
---
name: my-skill
description: What it does, and the phrases someone would use when they want it.
---
```

Two things make a skill work here. Start the body with the health check, the way
every skill in this repo does. And write the description from the user's side:
name the problem and the words they would say, not the implementation.
