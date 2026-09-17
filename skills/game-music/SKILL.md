---
name: game-music
description: Generate licence-clear instrumental game music with ACE-Step 1.5 and turn it into seamless loops at a set loudness. Use when the user wants background music, a soundtrack, battle or menu themes, ambient loops, or asks about replacing music made with MusicGen or another non-commercial model.
---

# Game music: generate, loop, pick, listen

Work in the asset-engine repo root. The long version is
`docs/guide/music.md`; the licence detail is in `docs/guide/licensing.md`,
"Music and sound".

## Before you start

```sh
scripts/doctor.py --skip-models
scripts/fetch_models.py --group music      # add --download if anything is missing
scripts/validate_workflows.py workflows/api/txt2music_acestep15.json
```

## 1. Write a prompt folder

One `<name>.txt` per track: settings, a blank line, the caption, then for
anything with a tune a line of `---` and a section script. Copy the format
from `prompts/music/`, and copy its `_style.txt` too.

```
bpm: 96
key: D minor
time: 4
seconds: 200
seed: 1
lufs: -16
planner: yes

Epic fantasy orchestral march, noble and heroic, a steady string ostinato and
snare drum under a soaring melody on French horns and strings, full orchestra
throughout, warm, lush, studio-polished cinematic mix.
---
[Main Theme - horns over string ostinato]

[Variation - strings over snare]

[Main Theme - full orchestra]

[Variation - horns over string ostinato]
```

- **Planner on** (`planner: yes`) for menus, themes and battles: anything
  with a melody or a beat. Off only for ambient beds.
- **A section script** of themes and variations. Never `[Intro]`,
  `[Breakdown]`, `[Outro]` or `[Silence]`. Keep each tag short and consistent
  with the caption.
- **Give a slow theme a pulse.** An ostinato or a steady drum under it is what
  kept a slow theme from falling silent.
- Ask for about 200 seconds. A loop comes out shorter than its take: 75 to
  182 seconds from takes of 145 to 210. Use `lufs: -16` for ambience and
  menus and `-14` for battles.

## 2. Generate several takes and keep the best loops

```sh
scripts/generate_music.py path/to/prompts --takes 3 --loop out/music --keep-best
```

`out/music/<name>.mp3` is the kept loop, `out/music/takes/` holds the others,
and `out/music/picks.json` records every take's measurements and seed. Put
that record next to the shipped files.

`picks.json` is written after every take. Run the same command again after a
stop and it skips the seeds already recorded; `--takes 6` after `--takes 3`
adds three more and picks from all six. After changing `make_loop.py` or a
track's `lufs`, add `--reloop` to loop the recorded takes again without
generating anything.

If a run is stopped, the server still finishes the prompts it was given, and
the next run finds those takes and records them instead of making them
again. On a busy or low-memory box, queue a track's takes together with
`--no-wait`, then run the same command without it to loop and record them.

## 3. Put every take in front of the listener, not just the winner

The picker measures silence, level jumps and loudness. It cannot hear whether
a track is any good or whether a voice crept in. Say that plainly, and hand
over `out/music/takes/` as well as the kept loops. In the game's own listening
pass, two of the four menu and battle takes kept by ear were the ones the
measurements ranked first, and a battle prompt whose three takes measured among
the cleanest was turned down (`docs/guide/music.md`, "Several takes, picked by
measurement").

## Rules

- **Never use MusicGen, MAGNeT, AudioLDM or Udio output in something that is
  sold.** Their weights or terms are non-commercial. ACE-Step 1.5 is MIT.
- **Planner on for anything with a tune, with a section script.** Without the
  planner a menu theme, a chamber piece and two battle tracks were rejected by
  ear, while ambient beds were fine. With it and only `[Instrumental]`, takes
  came back as songs with 20-second silences. With a script, six battle takes
  of six held together.
- **The planner takes about 4.5 minutes of CPU per 150-second take** and holds
  the ComfyUI queue. On the shared server, say so before queueing a batch.
- **Keep the text encoders on the CPU** (the graph already does). On the
  image's PyTorch 2.6 the planner's GPU sampling hits NaNs, and the CUDA
  assert aborts the whole shared ComfyUI server, taking every queued job with
  it (Comfy-Org/ComfyUI#12274).
- **No negatives in a caption.** Write "[Instrumental]" in the lyrics, never
  "no vocals" in the caption.
- **The ComfyUI server is shared.** Stop only jobs you started: interrupt by
  `prompt_id` after checking `/queue`, and never kill processes by script
  name.
- **If you script `run_workflow.py` yourself, read a prompt's outputs from
  the lines with nothing after the path.** It also prints every other file
  written to `output/` while it waited, each with a size after it, and on a
  shared server that includes other jobs' files and the previous take.
