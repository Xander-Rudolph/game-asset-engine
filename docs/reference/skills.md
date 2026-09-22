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
| `lip-sync` | Talking portraits: a portrait, its mouth shapes, and cues timed to voice lines |
| `daz-figure` | A Daz Genesis figure you downloaded: installed outside the repo, imported into Blender, and its visemes rendered, with the licence stated first |
| `hair-mesh` | Hair cards grown on a scalp, with a diffuse and an opacity map, placed on a figure; the repo owns them, so they may ship |

Each one starts by running `scripts/doctor.py`, so a session never begins by
guessing whether ComfyUI is up. If it is not, the skill walks the user through
getting it running rather than failing later in a confusing way.

## The rules they share

Each of these was learned by getting it wrong. Not every skill needs every rule,
so this says which skills carry which.

**Check the engine first.** All nine start with `scripts/doctor.py`.

**Check, do not assume.** Each skill carries the commands for its own checks, so
nothing describes what a file probably contains. `asset-pipeline` reads a mesh's
real face and body counts and prints a rig's bone count. `pose-sheet` dumps the
rig's real bone names. `concept-edit` asks the running server which node types it
loaded. `mesh-budget` measures a face budget rather than guessing one.
`lip-sync` dry-runs a mouth box against the edit graph's size list, read from
the running container, and checks that no pixel outside the box changed.
`daz-figure` checks every installed file against its CRC-32, and reads the build
report and what each viseme moves before it renders anything.

**Show, do not report.** The skills that make images, `asset-pipeline`,
`concept-edit`, `pose-sheet`, `ground-texture` and `lip-sync`, read each one
back into the conversation, because printing a path is not showing a picture.
`daz-figure` is the exception. Whether a Daz render may go into a chat model
under Daz's AI clause is open, so it reads none back: the person opens each
labelled sheet and says what they see, and the skill gives the pixels each
viseme changed, from the render report.
`game-music` makes audio, which the conversation cannot show, so it puts every
take in front of the person to listen to. `lip-sync` reads back its portrait,
mouth box and contact sheet of mouths, then hands over the preview video for
the person to watch with sound.

**One stage per turn.** `asset-pipeline`, `lip-sync` and `daz-figure` have
stages, and gate each one. A rejected mesh three stages later costs far more
than a rerolled concept image, and nine mouth edits cost about 23 minutes of
GPU, so the portrait and the mouth box are approved before any mouth is made.
A full viseme render of a Genesis figure took about 25 minutes of CPU, so
`daz-figure` renders one viseme first.

**Say what was chosen and why.** `asset-pipeline` names the generator, the camera
angle and what it added to the prompt. `lip-sync` asks where the voice lines come
from and whether that voice may ship before it makes anything, and names the
mouth shapes that came out weak. `daz-figure` states the Daz licence before it
installs anything: renders may ship, the 3D data needs an Interactive License,
and Daz content stays out of every AI stage.

## MCP servers

Two, and they are not the same kind of thing. One is this repo's own pipeline,
wrapped as tools and registered by hand on the machine that runs it. The other
is a hosted service declared in `.mcp.json`.

### This repo's own server

`mcp/server.py` serves 23 of this repo's scripts as MCP tools, so a client with
no shell, or a client that is not on this machine, can drive the pipeline:
engine health, what is on disk, queueing a graph, Blender sprite sheets and
rigging, and lip sync cues. Nothing that deletes, uninstalls, downloads weights
or publishes is exposed (`python3 mcp/server.py --list-tools`, 2026-09-19).

Register it with one command, and read
[the MCP server](/guide/mcp) before you do, because the Blender tools need the
Docker socket and socket access is root on the host:

```sh
claude mcp add-json asset-engine "$(curl -fsSL https://xander-rudolph.github.io/game-asset-engine/mcp/asset-engine.json)"
```

::: warning Why it is registered by hand rather than shipped in the plugin
A plugin can carry MCP servers, and every server it carries starts for everyone
who enables the plugin, with no per-server opt out
([Claude Code MCP documentation](https://code.claude.com/docs/en/mcp), read
2026-09-19). Anything at the plugin root, `.mcp.json` included, is part of what
an installer gets.

A server that wants the Docker socket is not something a person should acquire
as a side effect of installing a plugin, so this one is not shipped that way.
It is published as a config file and a command instead, which is also why
`.mcp.json` in this repo declares Meshy and not this.
:::

### Meshy, a hosted service

`.mcp.json` declares the servers this repo ships to installers:

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
