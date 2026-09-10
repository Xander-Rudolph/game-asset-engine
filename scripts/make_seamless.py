#!/usr/bin/env python3
"""Turn a generated texture into one that tiles without a visible seam.

    scripts/make_seamless.py in.png --out output/materials/plains.jpg
    scripts/make_seamless.py in.png --out out.jpg --size 1024 --check

No node in this ComfyUI install generates tiling textures — there is no
circular-padding VAE decode and no tiled sampler — so the seam has to be
dealt with afterwards.

**Rolling the image by half does nothing.** That is the trick everyone
reaches for first, and it is a phase shift: a tile repeats exactly as
badly after it, because whether the right column continues into the left
one is not something a shift can change. Measured, it took an 81% seam
to 78%.

What works is to fade each far edge INTO its near one, so that by the
time the image reaches its right-hand border it *is* its left-hand
border, and the same top to bottom. Then the join is real and the tile
is periodic. Rolling by half afterwards is worth doing for a different
reason: it moves that join off the edges, where a tile meets its
neighbour and the eye is looking, into the middle where nobody is.

`--check` measures what is left, against the right yardstick: how much
the edge columns differ compared with how much ANY two adjacent columns
differ. A tiling texture's edges are neighbours, so 1.0 is seamless. The
materials already shipped score 1.0 to 1.2.
"""

import argparse
import pathlib
import sys

import numpy as np

try:
    from PIL import Image
except ImportError:
    sys.exit("needs Pillow: pip install --user Pillow")


def seam_score(a):
    """How badly the edges disagree, against how much neighbours differ.

    NOT against the image's contrast, which was the first try and was
    useless: it scored an already-perfect texture at 81%, because two
    adjacent columns of any organic texture differ by a good fraction of
    its standard deviation. With nothing to compare against, good and
    bad both looked bad.

    A tiling texture's first and last columns are NEIGHBOURS — they sit
    side by side when the tile repeats — so the honest question is
    whether they differ by about as much as any other adjacent pair.
    1.0 is seamless. A freshly generated texture scores several times
    that.

    Returns the ABSOLUTE difference as well, and it is the one to trust
    on a smooth texture. The water material scores 2.06 by the ratio and
    its edges differ by 2.1 levels out of 255, which no eye will ever
    see: when neighbouring pixels barely differ, dividing by that makes
    a nothing look like a problem. Acting on the ratio alone, this tool
    "repaired" that texture into a worse one.
    """
    adjacent = (np.abs(a[:, :-1] - a[:, 1:]).mean()
                + np.abs(a[:-1, :] - a[1:, :]).mean()) / 2 or 1.0
    edge = (np.abs(a[:, 0] - a[:, -1]).mean()
            + np.abs(a[0, :] - a[-1, :]).mean()) / 2
    return edge / adjacent, edge


def _mend(a, axis, band):
    """Close the discontinuity running through the middle of [axis].

    By fading in content from HALF A TILE AWAY, not by mirroring.

    Mirroring was the first attempt and it measures perfectly while
    looking terrible: reflecting the strip about the seam makes the two
    sides of it identical, so the tile grows a butterfly through its
    middle and the map reads as kaleidoscope wallpaper. The seam score
    said 0.98 and the picture was unusable, which is the whole argument
    for looking at the thing.

    What this does instead: near the seam, take the pixels from half a
    tile across. They are unrelated content but the same texture, and
    crucially they are CONTINUOUS with each other — a[x + w/2] and
    a[x+1 + w/2] are neighbours — so the discontinuity is replaced by
    ordinary ground. Weighted to 1 at the seam and 0 at the band's
    edges, the join to the surroundings is a fade between two pieces of
    the same texture, which reads as variation.
    """
    n = a.shape[axis]
    mid = n // 2
    b = max(2, int(band))
    x = np.arange(n, dtype=np.float32)
    d = np.abs(x - mid) / b
    w = np.clip(1 - d, 0, 1)
    w = w * w * (3 - 2 * w)                     # smoothstep
    shape = [1] * a.ndim
    shape[axis] = -1
    w = w.reshape(shape)
    far = np.roll(a, n // 2, axis=axis)
    return a * (1 - w) + far * w


def trim_border(im, flat=3.0):
    """Cut off a uniform mat the generator painted around the texture.

    Asked for a full-bleed surface, the model sometimes returns a
    *picture* of one: a smaller square inset on a white ground. Every
    edge is then the same flat colour, and tiling it lays a bright
    lattice across the map — which looks like a seam bug and is not one.
    Told not to draw a border in the negative prompt, it drew one
    anyway, so the prompt is not where this gets fixed.

    A mat is recognisable without knowing its colour: a row of it has
    almost no variance, where any row of real ground has plenty. Walk in
    from each edge while the rows stay flat.
    """
    a = np.asarray(im.convert("L"), dtype=np.float32)
    h, w = a.shape

    def walk(line_std, limit):
        i = 0
        while i < limit and line_std(i) < flat:
            i += 1
        return i

    top = walk(lambda i: a[i, :].std(), h // 4)
    bottom = walk(lambda i: a[h - 1 - i, :].std(), h // 4)
    left = walk(lambda i: a[:, i].std(), w // 4)
    right = walk(lambda i: a[:, w - 1 - i].std(), w // 4)
    if not (top or bottom or left or right):
        return im, 0
    # A couple of pixels more, because the mat's inner edge is feathered
    # by the JPEG and by the model's own soft edge.
    pad = 6
    box = (min(left + pad, w // 3), min(top + pad, h // 3),
           max(w - right - pad, w * 2 // 3), max(h - bottom - pad, h * 2 // 3))
    return im.crop(box), max(top, bottom, left, right)


def make_seamless(im, blend=0.16):
    """Roll the discontinuity into the middle, then mend it there.

    Rolling by half IS the right move, for a reason worth stating: the
    first and last rows of a rolled image were ADJACENT rows in the
    original, so the outer edges come out continuous by construction.
    What the roll does is move the one real discontinuity — between the
    original's last row and its first — into the middle of the tile,
    where it can be mended without touching the edges that have to
    match.

    (An earlier version blended the rolled image back toward the
    unrolled one, which put that discontinuity straight back on the
    edge. It measured as doing nothing, because it did nothing.)
    """
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    h, w, _ = a.shape
    a = np.roll(np.roll(a, w // 2, axis=1), h // 2, axis=0)
    a = _mend(a, 1, w * blend)
    a = _mend(a, 0, h * blend)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--blend", type=float, default=0.16,
                    help="how much of the tile the handover spans")
    ap.add_argument("--check", action="store_true",
                    help="report the seam score before and after")
    args = ap.parse_args()

    im = Image.open(args.src).convert("RGB")
    im, mat = trim_border(im)
    if mat:
        print(f"  trimmed a {mat}px flat border the generator painted "
              f"around it")
    if args.check:
        before, _ = seam_score(np.asarray(im.convert("L"), dtype=np.float32))
    out = make_seamless(im, args.blend)
    if args.size and out.size != (args.size, args.size):
        out = out.resize((args.size, args.size), Image.LANCZOS)

    dst = pathlib.Path(args.out)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.suffix.lower() in (".jpg", ".jpeg"):
        out.save(dst, quality=92, subsampling=0)
    else:
        out.save(dst)

    g = np.asarray(out.convert("L"), dtype=np.float32)
    after, abs_after = seam_score(g)
    note = (f"{dst}  {out.size[0]}px  contrast {g.std():.1f}  "
            f"seam {after:.2f}x ({abs_after:.1f}/255)")
    if args.check:
        note += f"  (was {before:.2f}x)"
    print(note)
    # Both tests have to fail before this is worth saying: a high ratio
    # on a smooth texture is an artefact of the ratio, not a seam.
    if after > 1.6 and abs_after > 4.0:
        print("  ! the seam still shows; raise --blend", file=sys.stderr)
    if g.std() < 8:
        print("  ! very flat — a texture this even reads as a painted "
              "rectangle at map scale", file=sys.stderr)


if __name__ == "__main__":
    main()
