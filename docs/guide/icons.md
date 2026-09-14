# Icons

Small UI art has a different set of problems from characters. It is read at 20
pixels, sits on a coloured background, and appears in rows where any inconsistency
between neighbours is obvious.

```sh
scripts/generate_concepts.sh prompts/icons
scripts/cut_icon.py output/icons/gold_00001_.png output/icons/res_gold.png
```

## Generate on a flat background on purpose

The icon prompts ask for a flat plain mid-grey background, and that is not a
style choice. It makes cutting the icon out a flood fill rather than a matting
model.

The four corners are background by construction, so the fill starts there and
spreads while the colour stays close. That handles the soft gradient some
generations come out with, which a single colour key would tear a hole in.

In practice one corner often isn't background: a glow from the subject reaches
into it. So the fill compares against the median of the four corner colours, not
their average. With an average, that one corner dragged the reference colour
off, and the whole frame survived the cut as a grey box round the icon at every
`--tol`.

## Two critical details at 20 pixels

**Fade the edges, don't cut them hard.** A sharp cutout leaves a ring of
background-coloured pixels around the icon. The background is mid-grey, so that
ring shows as a grey halo on any UI that is not the same grey. `cut_icon.py`
pulls the edge in by a pixel before it softens it, so the ring goes with the
edge rather than being blurred back in.

**Trim tight, then pad evenly.** The generator centres the subject by eye, not
by pixel. A 2% drift is invisible in one icon but a visible wobble in a row of
five.

## Isolated background pockets

A flood fill only reaches background it can spread to. A corner cut off by the
subject leaves behind a scrap of grey background beside the icon.

Nothing about its colour marks it out. Its shape does: **it touches the canvas
edge**, and the subject never does, because the prompt asks for the subject
centred with clear space around it.

A rule based on size was tried first. It let a corner wedge through beside a
flask, because a wedge easily covers a tenth of the area of a thin bottle.
Specks smaller than 2% of the biggest piece are dropped separately, wherever
they are, as cut-edge crumbs.

A flood fill leaves a second kind of pocket that this rule never reaches:
background fenced in *inside* the subject, like sky between a tree's trunk and
its canopy. It never touches the canvas edge. Icons are mostly solid shapes and
rarely have one; props often do. See
[Props and scenery](/guide/props#clear-the-pockets-the-fill-cannot-reach).

## Where to stop

Painting every icon is not the goal. If your UI already uses emoji, replace the
frequent ones with painted art and leave the rest. A one-off mark that appears
on a single screen costs a generated image to say what an emoji already says.

Leave typographic symbols alone. Ticks, crosses, arrows and stars are typography
doing a typographic job, and painting a tick makes it a picture of a tick.

## Swapping art in without rewriting strings

Worth knowing if you're adding icons to an existing UI.

Say your costs and labels are strings with emoji inside them, such as a cost
line `Build 40🪵 20🪙`. Rewriting each one as a row of text and image elements
means rebuilding every call site, and a cost line would no longer read cleanly
in the source or in a text log.

Instead, have the text component walk the string and swap any emoji that has
painted art for an inline image, leaving the rest as text. Each call site
changes only which text component it uses, and no string changes.

One bug worth knowing: the first version walked the string by index, which in
many languages counts UTF-16 code units. Emoji outside the basic plane are
surrogate pairs, so they never matched. Nothing errored: symbols inside the
basic plane got painted, and every emoji outside it silently stayed as text. A
test caught it. Iterate by code point or by grapheme, not by index.
