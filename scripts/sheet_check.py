#!/usr/bin/env python3
"""Check a sprite sheet for the faults that are arithmetic, so eyes are spent on taste.

    scripts/sheet_check.py output/sheets/golem_walk.png --cell 220
    scripts/sheet_check.py output/sheets/*.png --cell 220 --quiet
    scripts/render_sheet.py model.fbx --poses transforms:poses/walk.json --check

WHY: `skills/pose-sheet/SKILL.md` asks an agent to find, by eye, which cell shows
the figure facing down and to the right.  `render_sheet.py` computes that azimuth
list arithmetically and prints it.  The script already knows the answer and asks
the picture instead.  Same for "the pose did nothing and you are looking at the
rest pose repeated", which is a comparison between two rows that nothing performs.

So: every check whose answer is a number is computed here.  The one check that is
genuinely taste -- does the motion read as the motion -- stays with a human, and
this tool deliberately does not attempt it.

WHAT IT WILL NOT TELL YOU: whether the cycle looks good, whether the proportions
are right, or whether the pose is the pose you meant.  A sheet that passes every
check here can still be wrong in the way that matters.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("needs numpy and Pillow: pip install --user numpy Pillow")

ROOT = Path(__file__).resolve().parent.parent


def slice_sheet(path: Path, cell: int):
    """Cut a sheet into [row][col] alpha arrays. Angles across, poses down."""
    im = Image.open(path).convert("RGBA")
    cols, rows = im.width // cell, im.height // cell
    if cols < 1 or rows < 1:
        raise SystemExit(f"{path.name}: {im.width}x{im.height} is smaller than "
                         f"one {cell}px cell. Pass the --cell size it was rendered at.")
    a = np.asarray(im)[..., 3]
    return [[a[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell]
             for c in range(cols)] for r in range(rows)], rows, cols


def check(cells, rows, cols, azimuths=None, empty_floor=0.005, same_eps=0.002):
    """Return (findings, facts). A finding is something wrong."""
    findings, facts = [], []
    mask = [[c > 128 for c in row] for row in cells]
    cover = [[m.mean() for m in row] for row in mask]

    # 1. Empty or near-empty cells. The render failed, or the subject rotated
    #    out of frame, or the model is not where the camera is looking.
    for r in range(rows):
        for c in range(cols):
            if cover[r][c] < empty_floor:
                findings.append(
                    f"cell r{r}c{c} is {cover[r][c]:.2%} covered, effectively empty")

    # 2. Rest-pose repetition. missing_bones catches a typo; it does not catch a
    #    rotation that cancelled, was zero, or went to an axis with no effect.
    if rows > 1:
        for r in range(1, rows):
            diffs = [np.abs(mask[r][c].astype(np.float32)
                            - mask[0][c].astype(np.float32)).mean()
                     for c in range(cols)]
            if max(diffs) < same_eps:
                findings.append(
                    f"pose row {r} is identical to row 0 at every angle "
                    f"(max difference {max(diffs):.4f}). The pose did nothing: "
                    "you are looking at the rest pose repeated")

    # 3. Clipping. Any subject alpha touching a cell border means the frame is
    #    cutting the model, which a sheet makes surprisingly easy to miss.
    for r in range(rows):
        for c in range(cols):
            m = mask[r][c]
            if m[0, :].any() or m[-1, :].any() or m[:, 0].any() or m[:, -1].any():
                findings.append(f"cell r{r}c{c} touches its border: the subject "
                                "is clipped. Lower --zoom or raise --size")

    # 4. Coverage spread across angles. A subject that fills 40% of one cell and
    #    4% of another at the same pose is usually a framing or scale problem.
    for r in range(rows):
        lo, hi = min(cover[r]), max(cover[r])
        if hi > 0 and lo / hi < 0.35:
            findings.append(
                f"pose row {r} covers {lo:.1%} to {hi:.1%} across angles, a "
                f"{hi / max(lo, 1e-6):.1f}x spread. Expect some from a flat "
                "subject; this much usually means framing")

    # --- facts, not faults ---------------------------------------------------
    facts.append(f"{rows} pose row(s) x {cols} angle(s)")
    facts.append("coverage " + " ".join(f"{cover[r][c]:.1%}"
                                        for r in range(rows) for c in range(cols)))
    if azimuths:
        # The question the skill asks a human to answer by looking. Azimuth 45
        # is the model turned toward the viewer and to the right, which is the
        # down-right facing on an isometric grid.
        best = min(range(len(azimuths)),
                   key=lambda i: min(abs((azimuths[i] - 45) % 360),
                                     360 - abs((azimuths[i] - 45) % 360)))
        facts.append(f"cell {best} (azimuth {azimuths[best]:g}) is the "
                     "down-and-right facing: start your engine's mapping there")
    return findings, facts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheets", nargs="+", type=Path)
    ap.add_argument("--cell", type=int, required=True,
                    help="cell size in pixels, the --size the sheet was rendered at")
    ap.add_argument("--azimuths", help="comma separated, to report the facing index")
    ap.add_argument("--empty-floor", type=float, default=0.005)
    ap.add_argument("--same-eps", type=float, default=0.002)
    ap.add_argument("--quiet", action="store_true", help="only print problems")
    args = ap.parse_args()

    az = [float(x) for x in args.azimuths.split(",")] if args.azimuths else None
    bad = 0
    for sheet in args.sheets:
        p = sheet if sheet.is_absolute() else ROOT / sheet
        if not p.exists():
            sys.stderr.write(f"no such sheet: {p}\n")
            return 2
        cells, rows, cols = slice_sheet(p, args.cell)
        findings, facts = check(cells, rows, cols, az,
                                args.empty_floor, args.same_eps)
        if findings:
            bad += 1
            print(f"  FAIL {p.name}")
            for f in findings:
                print(f"       {f}")
        elif not args.quiet:
            print(f"  ok   {p.name}")
        if not args.quiet:
            for f in facts:
                print(f"       {f}")

    if not args.quiet:
        print()
        print(f"  {len(args.sheets) - bad}/{len(args.sheets)} sheet(s) passed")
        print("  These are the checks that are arithmetic. Whether the motion")
        print("  reads as the motion is still yours to judge.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
