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

That split exists because a shared style file is the single highest-leverage
place to contaminate a whole asset set. A house style baked into the default
means every generation carries someone else's project, silently.

## Layout

```
characters/   full-body figures
creatures/    animals and constructs, plus _hstyle.txt for humanoids
buildings/    isometric building dioramas
scenery/      small props
ground/       tileable overhead ground textures
icons/        UI icons on a flat background
examples/     one project's filled-in art direction, kept as worked examples
```

`_negative.txt` in each folder is passed as the negative prompt for every subject
in it. A single subject can override it with `<name>.neg.txt`, which is worth
doing when the shared style describes something that subject does not have.

## The examples folder

`examples/` holds the art direction from the project this pipeline was built for,
including a complete set of eight character subjects. It is there to show what a
filled-in `<<< ART DIRECTION >>>` looks like in practice, and what a consistent
set reads like. Nothing in the default path reads from it.

Copy a phrase out of it, do not point the pipeline at it.

## Generating a folder

```sh
scripts/generate_concepts.sh prompts/creatures          # everything in it
scripts/generate_concepts.sh prompts/creatures golem    # named subjects only
scripts/generate_concepts.sh prompts/examples/lords     # the example set
```
