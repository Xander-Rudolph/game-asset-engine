#!/usr/bin/env python3
"""Cut a talking portrait's mouths out of whole-image edits, and prove the rest is untouched.

    scripts/compose_mouths.py output/lipsync/lord_vitriol/portrait.png \\
        --box 410,440,204,190 --edits output/lipsync/lord_vitriol/edits --feather 8

    scripts/compose_mouths.py output/lipsync/lord_vitriol/portrait.png \\
        --box 420,444,184,160 --edits output/lipsync/lord_vitriol/edits \\
        --out output/lipsync/lord_vitriol/_trials/small_box        # try another box

    scripts/compose_mouths.py --check output/lipsync/lord_vitriol/manifest.json

    scripts/compose_mouths.py --selftest                       # needs no pictures

WHY: the mouths come from `workflows/api/img_edit_qwen.json`, which re-diffuses
the whole picture, so every edit also moves the hair, the lighting and the
clothes a little. A game shows one portrait and swaps only the mouth over it,
so only the mouth box of each edit is kept, and anything outside the box is the
portrait's own pixels by construction. What the edit changed next to the box
cannot be thrown away like that: it is where the pasted mouth meets the
portrait, and a mismatch there is a visible seam. So it is measured.

INPUTS

- the portrait: the approved picture, whose own mouth is the rest shape X;
- `--box x,y,w,h`: the mouth box in the portrait's pixels, around mouth and chin;
- `--edits DIR`: one edited whole image per shape, named `X.png` and `A.png` to
  `H.png`. A missing shape is skipped; a missing X is cut from the portrait
  itself, because the portrait's mouth is X.

WHAT IT DOES

1. **Brings each edit back to the portrait's frame.** The graph returns the
   edit at a size of its own choosing, which need not be the portrait's shape,
   so it kept only the biggest middle piece of the portrait with the shape it
   returned. `kept_region` works that piece out from the two sizes, and the
   edit is resized (Lanczos) back onto it. A portrait already at a size the
   graph returns, such as 1024x1024, is not resized at all; a portrait the
   graph keeps the shape of avoids the crop, not the resize.
2. **Measures drift** as the mean absolute difference, in 0 to 255 levels
   averaged over R, G and B, between the edit and the portrait in a ring
   `--ring` pixels wide just outside the box, and again for each side of the
   box. Near 0, the pasted mouth meets the face it came from; large, and a seam
   or a shifted jaw line will show. The worst side says which edge to move.
3. **Crops the box** to `mouth_<S>.png`. `--feather N` fades the edit into the
   portrait over the box's outer N pixels, blending inside the box only, so a
   seam softens while the pixels outside the box still never change.
4. **Writes `manifest.json`** beside the mouths: portrait, size, mouth box,
   order X A B C D E F G H, shapes, and Rhubarb's fallback (G to A, H to C,
   X to A), plus the drift, ring and feather used. Paths in it are relative to
   the manifest's own folder, so the folder moves as one piece.

--check MANIFEST pastes every overlay onto the portrait and fails unless zero
pixels outside the box change, the portrait and every overlay are the sizes
the manifest says, and A to F are present. Exit status 1 on any failure.

WHAT IT WILL NOT TELL YOU: whether a mouth reads as its shape. Look at the
contact sheet from `scripts/preview_lipsync.py` for that.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("needs numpy and Pillow: pip install --user numpy Pillow")

ROOT = Path(__file__).resolve().parent.parent

ORDER = ["X", "A", "B", "C", "D", "E", "F", "G", "H"]
REQUIRED = ["A", "B", "C", "D", "E", "F"]
FALLBACK = {"G": "A", "H": "C", "X": "A"}


def parse_box(raw: str) -> dict:
    try:
        x, y, w, h = (int(v) for v in raw.split(","))
    except ValueError:
        raise SystemExit(f"--box wants x,y,w,h in whole pixels, got {raw!r}")
    if w <= 0 or h <= 0:
        raise SystemExit(f"--box {raw}: width and height must be positive")
    return {"x": x, "y": y, "w": w, "h": h}


def box_inside(box: dict, size: tuple[int, int]) -> bool:
    return (box["x"] >= 0 and box["y"] >= 0 and box["w"] > 0 and box["h"] > 0
            and box["x"] + box["w"] <= size[0] and box["y"] + box["h"] <= size[1])


def settings_problem(box: dict, size: tuple[int, int], ring: int, feather: int) -> str:
    """Why these compose settings cannot work on a portrait of [size], or ''.

    Needs no edits, so a caller can ask before spending any GPU time.
    """
    if not box_inside(box, size):
        return f"mouth box {box} is not inside the {size[0]}x{size[1]} portrait"
    if ring < 1:
        return f"--ring {ring}: the drift ring must be at least 1 px wide"
    if feather < 0:
        return f"--feather {feather}: the feather cannot be negative"
    if feather * 2 > min(box["w"], box["h"]):
        return f"--feather {feather} is more than half the box's smaller side"
    return ""


def nearest_whole(top: int, bottom: int) -> int:
    """top / bottom to the nearest whole number, an exact half going to the even one.

    Both must be positive. Whole numbers throughout, so the same two sizes always
    give the same answer, on any machine, with no floating point to drift.

    DO NOT CHANGE THE HALF TO ROUND UP on the evidence of `PROBED` alone. It
    would match the node on 8 of the 14 probed ties against this rule's 5, and be
    worse everywhere else: scored against the node's own arithmetic over the
    525,625 portrait sizes from 300 to 1024 in both directions, each against the
    size the graph returns for it, rounding the half up parts from the node on
    31,499 of them and rounding it down on 27,498, where rounding to even parts
    on 6,656 (scratchpad sweep, 2026-09-18; the 17-size list read from
    comfyui-packaged that day). The 14 probed ties are 14 of 58,997 tying sizes
    in that square, and they do not stand for it. `kept_region` says what the
    node's own arithmetic is and why it is not restated here.
    """
    whole, left = divmod(top, bottom)
    if 2 * left > bottom or (2 * left == bottom and whole % 2):
        whole += 1
    return whole


def halving_is_a_tie(portrait: tuple[int, int], edit: tuple[int, int]) -> bool:
    """Do these two sizes leave an odd number of pixels to share between the margins?

    Then the margin is an exact half-pixel and `kept_region` has to choose. The
    graph chooses in floating point and was measured going both ways, so for
    these sizes the region can be a pixel out; see `kept_region`.
    """
    pw, ph = portrait
    ew, eh = edit
    spare = pw * eh - ph * ew
    if spare > 0:
        return spare % (2 * eh) == eh
    if spare < 0:
        return -spare % (2 * ew) == ew
    return False


def kept_region(portrait: tuple[int, int], edit: tuple[int, int]):
    """The piece of the portrait an edit was made from: (x0, y0, w, h) in its pixels.

    Worked out here from the shape of what the graph returned and then measured
    against the graph, rather than copied from the graph's code.

    THE REASONING. An edit comes back at a size of the graph's choosing, which
    need not be the portrait's shape. To reach it the graph kept the biggest
    middle piece of the portrait that already had the shape it was about to
    return, and scaled that piece to the returned size. Nothing outside the
    piece is anywhere in the edit, so undoing the trip means naming the piece.

    Every rectangle shaped like the returned picture is `ew * k` by `eh * k` for
    some scale k, and it sits inside the portrait while `ew * k <= pw` and
    `eh * k <= ph`. The biggest sits at `k = min(pw / ew, ph / eh)`: one side of
    the portrait is kept whole and the other trimmed. Clearing the fractions,
    the width is kept whole when `pw * eh <= ph * ew` and the height otherwise,
    and the two are equal exactly when the shapes already agree, in which case
    the piece is the whole portrait. The piece is in the middle, so the trim is
    shared equally: the same whole number of pixels comes off both ends, half
    the difference rounded, which leaves the trimmed side with the portrait's
    own parity and within a pixel of the shape the graph returned.

    THE MEASUREMENT (2026-09-18, comfyui-packaged; the sizes are in `PROBED` and
    `--selftest` rechecks them). A probe fed the graph's scale node pictures that
    were black but for single-pixel lines at known places, and found the lines
    again in what came back. A resampling filter moves a line's centre of mass to
    exactly where the mapping sends it, so a straight line through the pairs
    gives the scale and the offset to a hundredth of a pixel. On all 19 of the 33
    sizes whose margin is a whole number of pixels, from 512x1536 to 2000x1000,
    this region was where the node's output says it was, the worst by 0.18 px,
    which is the probe's own scatter. Rounding the trimmed *side* to the nearest
    whole pixel instead of the *margin*, which holds the shape twice as close,
    was two pixels out on 8 of those 19: so it is the margin that is rounded, and
    the piece is exactly centred rather than exactly in shape.

    WHERE IT CAN BE A PIXEL OUT, AND WHAT THAT PIXEL BUYS. When the difference to
    trim is odd the margin is an exact half-pixel, and the node settles it in
    floating point, which was measured going both ways: of the 14 such sizes
    probed it took the larger margin on 8 (601x894 took 3 off each side, not 2)
    and the smaller on 6 (600x605 took 2, not 3). Halves go to the even margin
    here, which matched the node on 5 of the 14; on the other 9 the piece is a
    pixel off the node's in the margin and two in the side, which moves the edit
    by a pixel at the frame's edges and by nothing at its centre, where the mouth
    is. `halving_is_a_tie` says which sizes those are and `to_portrait_frame`
    prints it; 10,626 pairs of a portrait sized in multiples of 32 against a size
    the graph returns held not one of them.

    The pixel is a choice, not a wall, and the choice is not the rounding rule.
    The floating-point expression this function replaced restated the node's own
    centre-crop arithmetic, and it reproduces the node on all 33 probed sizes,
    the 14 ties included, within 0.2 px (replayed against PROBED, 2026-09-18).
    What no whole-number rounding of the half can do is follow that arithmetic
    everywhere, because the node's rounding depends on where its floating point
    lands: over the 525,625 portrait sizes from 300 to 1024 in both directions,
    each against the size the graph returns for it, 58,997 tie, and the even
    margin parts from the node's arithmetic on 6,656 of them, rounding down on
    27,498 and rounding up on 31,499 (same sweep and day). So the even rule is
    the closest of the three, the pixel it costs is the price of working the
    region out here rather than restating the graph's expression, which is what
    research/untested.md settled under "Restated ComfyUI arithmetic", and a
    reader who scores the rules on PROBED's 14 ties alone will pick the wrong one.
    """
    pw, ph = portrait
    ew, eh = edit
    if min(pw, ph, ew, eh) <= 0:
        raise ValueError(f"sizes must be positive, got {pw}x{ph} and {ew}x{eh}")
    spare = pw * eh - ph * ew
    if spare > 0:                       # the portrait is the wider shape: trim the sides
        x0 = min(nearest_whole(spare, 2 * eh), (pw - 1) // 2)
        return x0, 0, pw - 2 * x0, ph
    if spare < 0:                       # the taller shape: trim top and bottom
        y0 = min(nearest_whole(-spare, 2 * ew), (ph - 1) // 2)
        return 0, y0, pw, ph - 2 * y0
    return 0, 0, pw, ph


# The name scripts/make_mouths.py imports. It stays until that script, which is
# not this one's to edit, asks for kept_region by name.
kontext_crop = kept_region


def crop_covers_box(portrait: tuple[int, int], edit: tuple[int, int], box: dict) -> bool:
    """Does an edit of size [edit] still hold the whole mouth box?

    A box within a pixel of the trimmed edge is not settled by this, because
    `kept_region` can be a pixel out when `halving_is_a_tie`.
    """
    x0, y0, cw, ch = kept_region(portrait, edit)
    return (box["x"] >= x0 and box["y"] >= y0
            and box["x"] + box["w"] <= x0 + cw and box["y"] + box["h"] <= y0 + ch)


def to_portrait_frame(edit: Image.Image, portrait: Image.Image):
    """The edit resized onto the portrait's own pixel grid.

    Returns (array HxWx3 float32, covered bool HxW, note). Pixels the edit
    never saw (outside a centre crop) are the portrait's and marked uncovered.
    """
    base = np.asarray(portrait.convert("RGB"), dtype=np.float32)
    covered = np.zeros(base.shape[:2], dtype=bool)
    if edit.size == portrait.size:
        covered[:] = True
        return np.asarray(edit.convert("RGB"), dtype=np.float32), covered, "same size"
    x0, y0, cw, ch = kept_region(portrait.size, edit.size)
    resized = edit.convert("RGB").resize((cw, ch), Image.LANCZOS)
    out = base.copy()
    out[y0:y0 + ch, x0:x0 + cw] = np.asarray(resized, dtype=np.float32)
    covered[y0:y0 + ch, x0:x0 + cw] = True
    note = f"resized {edit.size[0]}x{edit.size[1]} to {cw}x{ch}"
    if (x0, y0) != (0, 0):
        note += f" at {x0},{y0} (back where the graph took it from)"
    if halving_is_a_tie(portrait.size, edit.size):
        note += " [the trim is an exact half here, so this may be a pixel out]"
    return out, covered, note


def ring_mask(size: tuple[int, int], box: dict, ring: int) -> np.ndarray:
    w, h = size
    m = np.zeros((h, w), dtype=bool)
    x, y, bw, bh = box["x"], box["y"], box["w"], box["h"]
    m[max(0, y - ring):min(h, y + bh + ring), max(0, x - ring):min(w, x + bw + ring)] = True
    m[y:y + bh, x:x + bw] = False
    return m


def side_masks(size: tuple[int, int], box: dict, ring: int) -> dict:
    """The drift ring split into the strips above, below, left and right of the box."""
    w, h = size
    x, y, bw, bh = box["x"], box["y"], box["w"], box["h"]
    x0, x1 = max(0, x - ring), min(w, x + bw + ring)
    out = {k: np.zeros((h, w), dtype=bool) for k in ("top", "bottom", "left", "right")}
    out["top"][max(0, y - ring):y, x0:x1] = True
    out["bottom"][y + bh:min(h, y + bh + ring), x0:x1] = True
    out["left"][y:y + bh, x0:x] = True
    out["right"][y:y + bh, x + bw:x1] = True
    return out


def feather_alpha(w: int, h: int, feather: int) -> np.ndarray:
    """1 in the middle of the box, fading towards its edges over [feather] px."""
    if feather <= 0:
        return np.ones((h, w, 1), dtype=np.float32)
    xs = np.minimum(np.arange(w), np.arange(w)[::-1])
    ys = np.minimum(np.arange(h), np.arange(h)[::-1])
    d = np.minimum(ys[:, None], xs[None, :]).astype(np.float32)
    return np.clip((d + 0.5) / feather, 0.0, 1.0)[..., None]


def rel(path: Path, start: Path) -> str:
    return Path(os.path.relpath(path.resolve(), start.resolve())).as_posix()


def compose(portrait_path: Path, box: dict, edits: Path, out: Path,
            ring: int = 6, feather: int = 0, quiet: bool = False) -> dict:
    """Write mouth_<S>.png and manifest.json into [out]; return the manifest."""
    say = (lambda *a: None) if quiet else print
    portrait = Image.open(portrait_path)
    portrait.load()
    size = portrait.size
    problem = settings_problem(box, size, ring, feather)
    if problem:
        raise SystemExit(problem)
    base = np.asarray(portrait.convert("RGB"), dtype=np.float32)
    x, y, w, h = box["x"], box["y"], box["w"], box["h"]
    rmask = ring_mask(size, box, ring)
    sides = side_masks(size, box, ring)
    alpha = feather_alpha(w, h, feather)
    out.mkdir(parents=True, exist_ok=True)

    shapes, drift, drift_sides, sources = {}, {}, {}, {}
    for s in ORDER:
        f = edits / f"{s}.png"
        if f.exists():
            arr, covered, note = to_portrait_frame(Image.open(f), portrait)
            if not covered[y:y + h, x:x + w].all():
                raise SystemExit(f"{f}: the edit graph cropped part of the mouth box "
                                 "away. Use a portrait at a size the edit graph keeps "
                                 "whole, such as 1024x1024")
            ring_px = rmask & covered
            diff = np.abs(arr - base).mean(axis=-1)
            d = float(diff[ring_px].mean()) if ring_px.any() else 0.0
            per_side = {k: round(float(diff[m & covered].mean()), 2)
                        for k, m in sides.items() if (m & covered).any()}
            sources[s] = rel(f, out)
        elif s == "X":
            arr, note, d = base, "no X edit: cut from the portrait itself", 0.0
            per_side = {k: 0.0 for k, m in sides.items() if m.any()}
            sources[s] = rel(portrait_path, out)
        else:
            say(f"  {s}  no edit at {f}, skipped")
            stale = out / f"mouth_{s}.png"
            if stale.exists():
                # Left from an earlier compose, it would look like part of the set.
                stale.unlink()
                say(f"      removed the earlier {stale}")
            continue
        crop = alpha * arr[y:y + h, x:x + w] + (1 - alpha) * base[y:y + h, x:x + w]
        name = f"mouth_{s}.png"
        Image.fromarray(np.clip(np.rint(crop), 0, 255).astype(np.uint8), "RGB").save(out / name)
        shapes[s] = name
        drift[s] = round(d, 2)
        drift_sides[s] = per_side
        worst = max(per_side, key=per_side.get) if per_side else "-"
        say(f"  {s}  drift {d:6.2f} (worst {worst} {per_side.get(worst, 0):.2f})  "
            f"{note}  -> {out / name}")

    manifest = {
        "portrait": rel(portrait_path, out),
        "size": [size[0], size[1]],
        "mouth": box,
        "order": ORDER,
        "shapes": shapes,
        "fallback": FALLBACK,
        "drift": drift,
        "drift_sides": drift_sides,
        "ring": ring,
        "feather": feather,
        "sources": sources,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    say(f"  manifest {out / 'manifest.json'}")
    missing = [s for s in REQUIRED if s not in shapes]
    if missing:
        say(f"  ! missing {', '.join(missing)}: --check will fail until they exist")
    return manifest


def check(manifest_path: Path) -> list[str]:
    """Return the failures; an empty list means the set is sound."""
    fails = []
    try:
        m = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return [f"cannot read {manifest_path}: {e}"]
    for key in ("portrait", "size", "mouth", "order", "shapes", "fallback"):
        if key not in m:
            fails.append(f"manifest has no {key!r}")
    if fails:
        return fails
    here = manifest_path.parent
    if m["order"] != ORDER:
        fails.append(f"order is {m['order']}, expected {ORDER}")
    for s in REQUIRED:
        if s not in m["shapes"]:
            fails.append(f"shape {s} is missing; A to F are required")
    for s, target in m["fallback"].items():
        if s not in m["shapes"] and target not in m["shapes"]:
            fails.append(f"{s} is missing and so is its fallback {target}")

    p = here / m["portrait"]
    if not p.exists():
        return fails + [f"portrait not found: {p}"]
    portrait = Image.open(p)
    portrait.load()
    if list(portrait.size) != list(m["size"]):
        fails.append(f"portrait is {portrait.size[0]}x{portrait.size[1]}, "
                     f"manifest says {m['size'][0]}x{m['size'][1]}")
    box = m["mouth"]
    if not box_inside(box, portrait.size):
        return fails + [f"mouth box {box} is not inside the portrait"]
    x, y, w, h = box["x"], box["y"], box["w"], box["h"]
    mode = "RGBA" if "A" in portrait.getbands() else "RGB"
    before = np.asarray(portrait.convert(mode))
    outside = np.ones(before.shape[:2], dtype=bool)
    outside[y:y + h, x:x + w] = False

    for s in ORDER:
        if s not in m["shapes"]:
            print(f"  {s}  absent, plays {m['fallback'].get(s, '(no fallback)')}")
            continue
        f = here / m["shapes"][s]
        if not f.exists():
            fails.append(f"{s}: overlay not found: {f}")
            continue
        ov = Image.open(f)
        ov.load()
        if ov.size != (w, h):
            fails.append(f"{s}: overlay is {ov.size[0]}x{ov.size[1]}, box is {w}x{h}")
        comp = portrait.convert(mode)
        if "A" in ov.getbands():
            comp.paste(ov.convert(mode), (x, y), ov.getchannel("A"))
        else:
            comp.paste(ov.convert(mode), (x, y))
        after = np.asarray(comp)
        changed = np.any(after != before, axis=-1)
        n_out = int(changed[outside].sum())
        n_in = int(changed[~outside].sum())
        if n_out:
            fails.append(f"{s}: {n_out} pixels outside the mouth box changed")
        print(f"  {s}  {ov.size[0]}x{ov.size[1]}  pixels changed inside {n_in}, "
              f"outside {n_out}")
    return fails


# ------------------------------------------------------------------ self-test

# Where the graph's scale node put the piece it kept, measured by the probe
# described in kept_region: the portrait's size, the size the node returned, and
# the piece the node's own output says it took, to a hundredth of a pixel. One
# run, 33 sizes, 21 marked lines each way, on 2026-09-18 in comfyui-packaged; no
# model was loaded and no job was queued. The scatter between a line's measured
# place and a whole pixel reaches 0.18, so 0.2 is the tolerance below.
PROBED = [
    ((1024, 1024), (1024, 1024), (-0.00, -0.00, 1024.00, 1024.00)),
    ((700, 900), (880, 1184), (16.00, 0.01, 668.01, 899.99)),
    ((1024, 768), (1184, 880), (-0.06, 3.02, 1024.11, 761.95)),
    ((512, 1536), (672, 1568), (-0.01, 170.99, 512.03, 1194.01)),
    ((2000, 1000), (1456, 720), (-0.02, 5.00, 2000.03, 990.00)),
    ((1600, 900), (1392, 752), (0.03, 18.00, 1599.93, 864.00)),
    ((1104, 1472), (880, 1184), (4.99, -0.06, 1094.02, 1472.11)),
    ((703, 901), (880, 1184), (17.00, 0.00, 669.01, 901.00)),
    ((704, 704), (1024, 1024), (-0.00, -0.00, 704.00, 704.00)),
    ((672, 896), (880, 1184), (2.99, -0.02, 666.01, 896.03)),
    ((800, 864), (944, 1104), (30.99, -0.01, 738.01, 864.01)),
    ((864, 672), (1184, 880), (-0.00, 15.00, 864.00, 642.00)),
    ((897, 705), (1184, 880), (-0.01, 19.00, 897.03, 667.00)),
    ((675, 988), (832, 1248), (7.99, -0.02, 659.03, 988.03)),
    ((747, 743), (1024, 1024), (2.01, -0.01, 742.99, 743.02)),
    ((749, 1001), (880, 1184), (2.98, 0.09, 743.03, 1000.82)),
    ((877, 1000), (944, 1104), (11.01, -0.07, 854.99, 1000.14)),
    ((935, 846), (1104, 944), (-0.02, 22.99, 935.04, 800.03)),
    ((789, 779), (1024, 1024), (5.00, 0.00, 779.01, 779.00)),
    # Sizes that leave an exact half to share between the two margins, which the
    # node settles in floating point. It lands where the even-margin rule here
    # lands on the first five and a pixel the other way on the last nine. These
    # 14 are not a fair sample of the sizes that tie: see `nearest_whole`.
    ((601, 600), (1024, 1024), (0.01, 0.00, 600.97, 600.00)),
    ((600, 601), (1024, 1024), (0.00, 0.01, 600.00, 600.97)),
    ((601, 897), (832, 1248), (2.01, -0.00, 596.99, 897.00)),
    ((600, 605), (1024, 1024), (0.00, 2.00, 600.00, 601.01)),
    ((600, 607), (1024, 1024), (0.00, 4.00, 600.00, 599.00)),
    ((601, 894), (832, 1248), (3.00, -0.00, 595.00, 894.01)),
    ((784, 777), (1024, 1024), (3.00, 0.01, 777.99, 776.98)),
    ((741, 740), (1024, 1024), (1.00, -0.00, 739.00, 740.01)),
    ((873, 868), (1024, 1024), (2.92, 0.06, 867.16, 867.88)),
    ((988, 929), (1024, 1024), (29.00, 0.00, 929.99, 929.00)),
    ((658, 631), (1024, 1024), (12.98, -0.00, 632.03, 631.00)),
    ((794, 761), (1024, 1024), (17.00, 0.03, 760.00, 760.94)),
    ((749, 736), (1024, 1024), (7.00, 0.01, 735.00, 735.99)),
    ((759, 706), (1024, 1024), (26.99, 0.00, 705.01, 706.00)),
]


def selftest() -> int:
    """Check the geometry against PROBED and compose a set out of made-up pixels."""
    import tempfile

    fails, ties = [], 0
    for portrait, edit, measured in PROBED:
        got = kept_region(portrait, edit)
        off = max(abs(a - b) for a, b in zip(got, measured))
        tie = halving_is_a_tie(portrait, edit)
        if off <= 0.2:
            continue
        if tie and off <= 2.2:
            ties += 1                   # the node's own halving went the other way
            continue
        fails.append(f"{portrait[0]}x{portrait[1]} -> {edit[0]}x{edit[1]}: "
                     f"kept_region says {got}, the node's output says {measured}"
                     + ("" if tie else " and the halving is not a tie"))
    print(f"  geometry: {len(PROBED)} measured sizes, {len(PROBED) - len(fails) - ties} "
          f"matched within 0.2 px, {ties} settled the other way at an exact half, "
          f"{len(fails)} wrong")

    if kept_region((1024, 1024), (1024, 1024)) != (0, 0, 1024, 1024):
        fails.append("a portrait the graph returns unchanged should be kept whole")
    real_box = {"x": 410, "y": 440, "w": 204, "h": 190}
    if not crop_covers_box((1024, 1024), (1024, 1024), real_box):
        fails.append("crop_covers_box says an untrimmed portrait loses its mouth box")
    corner = {"x": 0, "y": 0, "w": 50, "h": 50}
    if crop_covers_box((1024, 1024), (1568, 672), corner):
        fails.append("crop_covers_box says a box in a trimmed-off corner survives")
    try:
        kept_region((0, 100), (100, 100))
        fails.append("kept_region accepted a zero-width portrait")
    except ValueError:
        pass

    rng = np.random.default_rng(7)
    size, box = (96, 80), {"x": 24, "y": 40, "w": 48, "h": 32}
    base = rng.integers(0, 256, (size[1], size[0], 3), dtype=np.uint8)
    with tempfile.TemporaryDirectory(prefix="compose_mouths_selftest_") as tmp:
        root = Path(tmp)
        edits = root / "edits"
        edits.mkdir()
        Image.fromarray(base, "RGB").save(root / "portrait.png")
        for s in REQUIRED:
            arr = base.copy()
            arr[30:70, 16:80] = rng.integers(0, 256, (40, 64, 3), dtype=np.uint8)
            Image.fromarray(arr, "RGB").save(edits / f"{s}.png")
        out = root / "out"
        compose(root / "portrait.png", box, edits, out, ring=4, feather=6, quiet=True)
        problems = check(out / "manifest.json")
        fails += [f"the made-up set failed its own check: {p}" for p in problems]

    # An edit that came back at another size lands back where it was taken from.
    # Smooth pixels, because resizing noise up and down loses it either way.
    ys, xs = np.mgrid[0:size[1], 0:size[0]].astype(np.float32)
    smooth = np.stack([xs * 2, ys * 2, 128 + 100 * np.sin(xs / 9) * np.cos(ys / 11)], -1)
    smooth = np.clip(smooth, 0, 255).astype(np.uint8)
    big = (1024, 1024)
    x0, y0, cw, ch = kept_region(size, big)
    portrait = Image.fromarray(smooth, "RGB")
    piece = portrait.crop((x0, y0, x0 + cw, y0 + ch))
    arr, covered, note = to_portrait_frame(piece.resize(big, Image.LANCZOS), portrait)
    worst = float(np.abs(arr - smooth.astype(np.float32))[covered].max())
    print(f"  a {size[0]}x{size[1]} portrait sent out at {big[0]}x{big[1]} and brought "
          f"back: worst pixel {worst:.1f} levels out of 255 ({note})")
    if worst > 6:
        fails.append(f"bringing an edit back moved a pixel by {worst:.1f} levels")

    for f in fails:
        print(f"  ! {f}")
    print("  self-test failed" if fails else "  self-test passed")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("portrait", nargs="?", type=Path)
    ap.add_argument("--box", metavar="X,Y,W,H", help="mouth box in portrait pixels")
    ap.add_argument("--edits", type=Path, metavar="DIR",
                    help="folder of edited whole images named X.png, A.png to H.png")
    ap.add_argument("--out", type=Path, metavar="DIR",
                    help="where mouth_<S>.png and manifest.json go "
                         "(default: the portrait's folder)")
    ap.add_argument("--ring", type=int, default=6, metavar="PX",
                    help="width of the drift ring outside the box (default 6)")
    ap.add_argument("--feather", type=int, default=0, metavar="N",
                    help="fade the edit into the portrait over the box's outer "
                         "N pixels, inside the box only (default 0, a hard edge)")
    ap.add_argument("--check", type=Path, metavar="MANIFEST",
                    help="verify a composed set instead of composing one")
    ap.add_argument("--selftest", action="store_true",
                    help="check the geometry against what the graph was measured "
                         "doing, and compose a set out of made-up pixels")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.check:
        fails = check(args.check)
        for f in fails:
            print(f"  ! {f}")
        print("  check failed" if fails else "  check passed")
        return 1 if fails else 0

    if not (args.portrait and args.box and args.edits):
        ap.error("give a portrait, --box and --edits (or --check MANIFEST)")
    if not args.portrait.exists():
        raise SystemExit(f"no such portrait: {args.portrait}")
    if not args.edits.is_dir():
        raise SystemExit(f"no such edits folder: {args.edits}")
    if args.ring < 1:
        ap.error("--ring must be at least 1")
    if args.feather < 0:
        ap.error("--feather cannot be negative")
    compose(args.portrait, parse_box(args.box), args.edits,
            args.out or args.portrait.parent, ring=args.ring, feather=args.feather)
    return 0


if __name__ == "__main__":
    sys.exit(main())
