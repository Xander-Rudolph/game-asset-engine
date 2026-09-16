# Skills and MCP

This repo doubles as a Claude Code plugin. It ships the skills that drive the
pipeline and the MCP server definitions that go with them.

## Installing it as a plugin

```
/plugin marketplace add Xander-Rudolph/game-asset-engine
/plugin install game-asset-engine@game-asset-engine
```

Full detail, including the second manifest that GitHub installation needs, is in
[installing it for Claude](/guide/claude).

## What ships

| Skill | Use it for |
|---|---|
| `asset-pipeline` | Prompt to rigged model, with an approval gate at every stage |
| `concept-edit` | Change one element of an approved image without redrawing it |
| `pose-sheet` | Sprite sheets, facing sheets, and authoring bone poses |
| `ground-texture` | Tileable terrain textures and fixing seams |
| `mesh-budget` | Choosing face counts, decimating, rigging heavy meshes |
| `asset-cleanup` | Curating the keepers and sweeping the rest |
| `game-music` | Licence-clear instrumental music, looped seamlessly at a set loudness |

Each one starts by running `scripts/doctor.py`, so a session never begins by
guessing whether ComfyUI is up. If it is not, the skill walks the user through
getting it running rather than failing later in a confusing way.

## The rules they share

Each of these was learned by getting it wrong. Not every skill needs every rule,
so this says which skills carry which.

**Check the engine first.** All seven start with `scripts/doctor.py`.

**Check, do not assume.** Each skill carries the commands for its own checks, so
nothing describes what a file probably contains. `asset-pipeline` reads a mesh's
real face and body counts and prints a rig's bone count. `pose-sheet` dumps the
rig's real bone names. `concept-edit` asks the running server which node types it
loaded. `mesh-budget` measures a face budget rather than guessing one.

**Show, do not report.** The skills that make images, `asset-pipeline`,
`concept-edit`, `pose-sheet` and `ground-texture`, read each one back into the
conversation, because printing a path is not showing a picture. `game-music`
makes audio, which the conversation cannot show, so it puts every take in front
of the person to listen to.

**One stage per turn.** Only `asset-pipeline` has stages, and it gates each one,
because a rejected mesh three stages later costs far more than a rerolled
concept image.

**Say what was chosen and why.** `asset-pipeline` names the generator, the camera
angle and what it added to the prompt.

## MCP servers

`.mcp.json` declares the servers this repo expects:

```json
{
  "mcpServers": {
    "meshy": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@meshy-ai/meshy-mcp-server"],
      "env": { "MESHY_API_KEY": "${MESHY_API_KEY}" }
    }
  }
}
```

Meshy is a hosted service, so it is a complement to this pipeline rather than
part of it. It is useful when you want a mesh without a local GPU, or when you
want to compare a hosted generator against the local one.

::: warning Keys come from the environment
The key is read from `MESHY_API_KEY` at run time. Never write a key into
`.mcp.json`, because this repo is public and a committed key is a leaked key.

```sh
export MESHY_API_KEY=...        # in your shell profile, not in the repo
```
:::

Four things to know before using it, checked on 2026-09-16 against the
[Meshy MCP server README](https://github.com/meshy-dev/meshy-mcp-server#readme)
and the 0.5.1 package:

- **The API key needs a Pro plan or above**, and most tools cost credits. The
  README lists the price of each.
- **Downloads land in `meshy_output/`** under the directory the server runs in.
  Claude Code starts it in the project you opened, so for someone who installed
  the plugin that is their own game repo. Add `meshy_output/` to that repo's
  ignore file.
- **Polycount is a setting, not a given.** An export can be photogrammetry
  scale, often around two million triangles, which is far more than this
  pipeline's assets. Smart topology takes a configurable polycount, and the
  remesh tool takes a `target_polycount` from 100 to 300,000. Either way, see
  [decimation](/guide/decimation) before importing one.
- **The version is not pinned.** `.mcp.json` runs
  `npx -y @meshy-ai/meshy-mcp-server` with no version, so a new release can be
  picked up the next time the server starts. 0.5.1 was the current release on
  2026-09-16.

## Writing your own skill

Put it in `skills/<name>/SKILL.md` with frontmatter:

```markdown
---
name: my-skill
description: What it does, and the phrases a person would use when they want it.
---
```

The description is what decides whether the skill gets picked, so write it from
the user's side. Name the problem and the words they would say, not the
implementation.

Start the body with the health check. Every skill here does:

```sh
scripts/doctor.py --skip-models
```
