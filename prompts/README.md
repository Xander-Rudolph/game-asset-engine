# Prompt library

Two kinds of file live here, and the difference matters.

**Technique is shared.** The `_style.txt` in each folder carries the clauses that
make a picture convert well into 3D: one subject, whole thing in frame, plain
background, even lighting, large readable shapes, no ragged edges. Those clauses
are the same whatever you are making, and each one is preventing a specific
failure. Keep them.

**Art direction is yours.** Each `_style.txt` has an `<<< ART DIRECTION: ... >>>`
slot. Replace that one phrase with your project's look. Nothing else in the file
should need changing.

If you leave the slot unfilled, `scripts/generate_concepts.sh` prints a warning
and leaves the placeholder out of the prompt, so you get the technique with no
look. The drop-in presets in `workflows/` are built from these files and keep the
slot text as it is written, so replace it in the Positive node there too.

That split exists because a shared style file is the single highest-leverage
place to contaminate a whole asset set. A house style baked into the default
means every generation carries someone else's project, silently.

**Subject files hold the subject only.** The style is put in front of each one at
run time. A subject file that repeats the framing, background or rendering
clauses sends them to the model twice.

## Layout

```
characters/   full-body figures
creatures/    animals and constructs, plus _hstyle.txt for humanoids
buildings/    isometric building dioramas
scenery/      small props
ground/       tileable overhead ground textures
icons/        UI icons on a flat background
music/        instrumental game music: one track file per loop, for generate_music.py
examples/     one project's filled-in art direction, kept as worked examples
```

`icons/` and `ground/` have no `_style.txt`. Each prompt in them is written out in
full.

`_negative.txt` in each folder is passed as the negative prompt for every subject
in it. A single subject can override it with `<name>.neg.txt`, which is worth
doing when the shared style describes something that subject does not have.

Three files at the top level are edit instructions for art you already have,
not subjects:

```
simplify_character.txt        redraw busy character art as a clean game-ready design
simplify_character_heavy.txt  a harder REMOVE / SIMPLIFY / KEEP push for dense figures
realism_pass.txt              keep the design, re-render the materials photorealistically
```

The simplify preset in `workflows/` is built from `simplify_character.txt`.

Name the keeps for your own art. An edit prompt that only says what to remove
is read as permission to remove everything, the rendering included. The first
simplify pass stripped a figure to featureless brown clay. What brought it back
was naming each keep: the focal accessory, the exact metal and cloth colours,
brown leather gloves and boots NOT grey, and the same face, hair, pose and
background. The closing floor (NOT flat untextured plastic, NOT a clay render)
helped too. The shipped KEEP lines are generic, so write your character's own
feature and colours into them.

## The examples folder

`examples/` holds the art direction from the project this pipeline was built for,
including a complete set of eight character subjects and, in `examples/music/`,
the prompt folder behind that game's twelve music tracks. It is there to show what a
filled-in `<<< ART DIRECTION >>>` looks like in practice, and what a consistent
set reads like. Nothing in the default path reads from it.

Copy a phrase out of it, do not point the pipeline at it.

## Generating a folder

```sh
scripts/generate_concepts.sh prompts/creatures          # everything in it
scripts/generate_concepts.sh prompts/creatures golem    # named subjects only
```

To simplify busy art with the heavier prompt:

```sh
PROMPT_FILE=prompts/simplify_character_heavy.txt DENOISE=0.93 \
    scripts/simplify_concepts.sh path/to/art/*.png
```
