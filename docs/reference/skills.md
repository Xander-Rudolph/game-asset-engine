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

Each one starts by running `scripts/doctor.py`, so a session never begins by
guessing whether ComfyUI is up. If it is not, the skill walks the user through
getting it running rather than failing later in a confusing way.

## The rules they share

These are written into every skill because each one was learned by getting it
wrong.

**Check, do not assume.** Every skill has commands for asking the running server
what it actually loaded, reading a mesh's real face and body counts, and dumping
a rig's real bone names. Nothing describes what a file probably contains.

**Show, do not report.** An image that was generated gets read back into the
conversation so the person can see it. Printing a path is not showing a picture.

**One stage per turn.** The pipeline gates at each stage because a rejected mesh
three stages later costs far more than a rerolled concept image.

**Say what was chosen and why.** Which generator, which camera angle, what was
added to the prompt.

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

Meshy costs credits per call. If you use it, note that its exports are
photogrammetry scale, often around two million triangles, which is far more than
this pipeline's assets. See [decimation](/guide/decimation) before importing one.

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
