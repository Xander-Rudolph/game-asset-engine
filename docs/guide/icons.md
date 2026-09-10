# Icons

Small UI art has a different set of problems from characters. It is read at 20
pixels, sits on a coloured background, and appears in rows where any inconsistency
between neighbours is obvious.

```sh
scripts/generate_concepts.sh prompts/icons
scripts/cut_icon.py output/icons/gold_00001_.png output/icons/res_gold.png
```

## Generate on a flat background on purpose

The icon prompts ask for a plain flat background, and that is not a style choice.
It makes cutting the icon out a flood fill rather than a matting model.

The four corners are background by construction, so the fill starts there and
spreads while the colour stays close. That handles the soft gradient some
generations come out with, which a single colour key would tear a hole in.

## Two details that matter at 20 pixels

**Feather the alpha, do not threshold it.** A hard cut leaves a ring of
background coloured pixels around the icon. On a white page you will not notice.
On a coloured or textured background it reads as a grey halo.

**Trim to the ink, then pad evenly.** The generator centres the subject by eye,
not by pixel. A two percent drift is invisible in one icon and a visible wobble in
a row of five.

## Islands the fill cannot reach

A flood fill only reaches background it has a path to. A corner that the subject
fences off survives as a pale scrap beside the icon.

Nothing about its colour marks it out. Its shape does, in a specific way: **it
touches the edge of the canvas**, and the subject never does, because the prompt
asked for the subject centred with space around it.

Sizing the rule by area instead was tried first and let a corner wedge through
beside a flask, because a wedge is easily a tenth of a thin bottle. Small specks
are dropped separately as cut edge crumbs.

## Where to stop

Painting every icon is not the goal. In the project this came from, 417 emoji
across 83 kinds were replaced with painted art, but only the frequent ones. A one
off mark that appears in a single screen costs a generated image to say what an
emoji already says.

Punctuation was deliberately left alone. Ticks, crosses, arrows and stars are
typography doing a typographic job, and painting a tick makes it a picture of a
tick.

## Swapping art in without rewriting strings

Worth knowing if you are retrofitting icons into an existing UI.

The costs and labels in that project were written as strings with emoji inside
them, like `Recruit 1👥 40🍞 20⚗️`. Rewriting each into a widget tree would have
meant touching every call site, and would have made a cost line unreadable in
source and unloggable in a text log.

Instead a text widget walks the string, swaps any glyph that has painted art for
an inline image, and leaves the rest as type. Ninety call sites became one word
longer, and no string changed.

One bug worth repeating: the first version walked the string by index, which
iterates UTF-16 code units. Every emoji above the basic plane is a surrogate
pair, so it could never match. That silently painted only the older glyphs and
left every newer one as type. A test caught it. Iterate by rune or by grapheme,
not by index.
