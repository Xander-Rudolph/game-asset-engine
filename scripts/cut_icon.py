#!/usr/bin/env python3
"""Cut a generated icon out of its background and size it for the UI.

    scripts/cut_icon.py output/icons/gold_00001_.png \
        output/icons/res_gold.png

The concept prompts ask for a plain flat background precisely so this
can be a flood fill rather than a matting model: the four corners are
background by construction, so the fill starts there and spreads while
the colour stays close. That handles the soft warm gradient some of them
come out with, which a single-colour key would tear a hole in.

Two details that matter at 20px, which is where these are actually read:

- **Feather the alpha, do not threshold it.** A hard cut leaves a ring of
  background-coloured pixels that reads as a grey halo once the icon sits
  on parchment.
- **Trim to the ink, then pad evenly.** The generator centres the subject
  in the canvas by eye, not by pixel, and a two-percent drift is a
  visible wobble in a row of five icons.
"""

import argparse
import pathlib
import sys
from collections import deque

try:
    from PIL import Image, ImageFilter
except ImportError:
    sys.exit("needs Pillow: pip install --user Pillow")


def _drop_scraps(mask: Image.Image, w: int, h: int,
                 speck: float = 0.02) -> Image.Image:
    """Throw away opaque islands that are not the subject.

    The flood fill only reaches background it has a *path* to, so a
    corner the subject fences off survives as a pale scrap beside the
    icon. Nothing about its colour marks it out. Two things about its
    shape do, and the second is the one that works:

    - it is a separate island, and
    - **it touches the edge of the canvas.** The prompts ask for the
      subject centred with clear space around it, so the subject never
      does. Sizing the rule by area instead was tried first and let a
      corner wedge through beside the flask, because a wedge is easily a
      tenth of a thin bottle.

    Specks smaller than [speck] of the biggest piece go too, wherever
    they are: they are cut-edge crumbs.
    """
    px = mask.load()
    label = [0] * (w * h)
    areas, edge = [0], [False]
    cur = 0
    for y in range(h):
        for x in range(w):
            if px[x, y] < 8 or label[y * w + x]:
                continue
            cur += 1
            area = 0
            touches = False
            q = deque([(x, y)])
            label[y * w + x] = cur
            while q:
                cx, cy = q.popleft()
                area += 1
                if cx == 0 or cy == 0 or cx == w - 1 or cy == h - 1:
                    touches = True
                for nx, ny in ((cx + 1, cy), (cx - 1, cy),
                               (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and \
                            not label[ny * w + nx] and px[nx, ny] >= 8:
                        label[ny * w + nx] = cur
                        q.append((nx, ny))
            areas.append(area)
            edge.append(touches)
    if cur <= 1:
        return mask
    biggest = max(areas)
    keep = [False] + [
        a >= biggest * speck and not e for a, e in zip(areas[1:], edge[1:])
    ]
    # If the subject itself runs off the edge, keeping nothing would be
    # worse than keeping the lot: fall back to the biggest island.
    if not any(keep):
        keep = [a == biggest for a in areas]
    out = Image.new("L", (w, h))
    out.putdata([px[i % w, i // w] if keep[label[i]] else 0
                 for i in range(w * h)])
    dropped = sum(1 for i in range(1, cur + 1) if not keep[i])
    if dropped:
        print(f"  dropped {dropped} piece(s) the fill could not reach")
    return out


def cut(src: Image.Image, tol: int) -> Image.Image:
    """Alpha from a flood fill inward from the corners."""
    im = src.convert("RGB")
    w, h = im.size
    px = im.load()
    # 0 = background, 255 = keep.
    alpha = [255] * (w * h)
    seen = bytearray(w * h)
    q = deque()
    for c in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        q.append(c)
        seen[c[1] * w + c[0]] = 1
    # The MEDIAN of the corners, not the mean.
    #
    # One corner is often not background at all: a glow thrown by the
    # subject reaches into it, and the arts rune's did. Averaging let
    # that one corner drag the reference toward it, the real grey then
    # fell outside tolerance, and the whole frame survived the cut as a
    # grey box round the icon — at every tolerance, which is what made
    # it look like the picture rather than the fill was wrong. A median
    # over four samples ignores a single outlier.
    corners = [px[c] for c in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    ref = [sorted(c[i] for c in corners)[1:3] for i in range(3)]
    ref = [(lo + hi) / 2 for lo, hi in ref]
    while q:
        x, y = q.popleft()
        r, g, b = px[x, y]
        if abs(r - ref[0]) + abs(g - ref[1]) + abs(b - ref[2]) > tol:
            continue
        alpha[y * w + x] = 0
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]:
                seen[ny * w + nx] = 1
                q.append((nx, ny))
    mask = Image.new("L", (w, h))
    mask.putdata(alpha)
    mask = _drop_scraps(mask, w, h)
    # Pull the edge in by a hair before feathering, so the halo of
    # background-coloured pixels goes with it rather than being blurred
    # back into the icon.
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(
        ImageFilter.GaussianBlur(1.2))
    out = im.convert("RGBA")
    out.putalpha(mask)
    return out


def frame(im: Image.Image, size: int, pad: float) -> Image.Image:
    """Trim to the ink and re-centre it in a square of [size]."""
    box = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if box:
        im = im.crop(box)
    inner = max(1, int(size * (1 - pad * 2)))
    w, h = im.size
    k = inner / max(w, h)
    im = im.resize((max(1, round(w * k)), max(1, round(h * k))),
                   Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--size", type=int, default=256,
                    help="output square, default 256 (drawn at ~20-24, so "
                         "this is the retina headroom)")
    ap.add_argument("--tol", type=int, default=60,
                    help="how far a pixel may drift from the corner colour "
                         "and still count as background")
    ap.add_argument("--pad", type=float, default=0.04,
                    help="clear space around the ink, as a fraction")
    args = ap.parse_args()

    src = Image.open(args.src)
    out = frame(cut(src, args.tol), args.size, args.pad)
    dst = pathlib.Path(args.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)

    covered = sum(out.getchannel("A").point(lambda v: 1 if v > 8 else 0)
                  .histogram()[1:])
    share = covered / (args.size * args.size)
    print(f"{dst}  {out.size[0]}px  {share:.0%} ink")
    if share < 0.05:
        print("  ! almost nothing survived the cut — raise --tol", file=sys.stderr)
    if share > 0.92:
        print("  ! almost nothing was cut — lower --tol", file=sys.stderr)


if __name__ == "__main__":
    main()
