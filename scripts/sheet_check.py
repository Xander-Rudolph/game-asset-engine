#!/usr/bin/env python3
"""Check a sprite sheet for the faults that are arithmetic, so eyes are spent on taste.

    scripts/sheet_check.py output/sheets/golem_walk.png --cell 220 \\
        --azimuths 45,135,225,315
    scripts/sheet_check.py output/sheets/*.png --cell 220 --quiet

    # render_sheet.py runs these checks itself with --check, with the cell size
    # and azimuths of the run; the pose file is compiled for the rig first
    scripts/bone_roles.py compile poses/roles/walk.json output/rigged/unit_warrior.fbx \\
        --out output/poses/unit_warrior_walk.json
    scripts/render_sheet.py output/rigged/unit_warrior.fbx \\
        --poses transforms:output/poses/unit_warrior_walk.json --check

WHY: some faults in a sheet are a number, and a number should be computed, not
found by eye. Which cell faces down and to the right follows from the azimuth
list, so give --azimuths and it is named (render_sheet.py --check passes the
list it rendered). An empty cell and a subject cut by its cell border are
counts of alpha pixels. A pose that did nothing is a comparison between two
rows.

HOW A ROW IS COMPARED WITH ROW 0: silhouettes first, then colour. A row whose
silhouette differs from row 0 moved. A row whose silhouette matches (less than
--same-eps of the cell differs at every angle) and in which no pixel changed by
--colour-levels or more at any angle is the rest pose repeated, and that is a
fault. A row whose silhouette matches but whose pixels inside it changed, as a
jaw, a shape key or another face-only pose leaves it, is reported as a fact
with the changed pixel count per angle, not as a fault: the check cannot tell
whether that change is the one you meant, so look at it.

WHAT IT WILL NOT TELL YOU: whether the cycle looks good, whether the proportions
are right, or whether the pose is the pose you meant. A sheet that passes every
check here can still be wrong in the way that matters. The one check that is
taste, whether the motion reads as the motion, stays with a person.

Exit codes: 0 every sheet passed; 1 a sheet has a fault or is smaller than one
cell; 2 a sheet was not found, or bad arguments.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError:
    sys.exit("needs numpy and Pillow. On Debian or Ubuntu: sudo apt install python3-numpy python3-pil. "
             "Or in a venv: python3 -m venv ~/.venvs/asset && ~/.venvs/asset/bin/pip install numpy Pillow, "
             "then run this script with ~/.venvs/asset/bin/python")

ROOT = Path(__file__).resolve().parent.parent

# A pixel counts as changed between two rows when one of its RGBA channels moved
# by this many levels or more. Measured on this repo's EEVEE sheets on
# 2026-09-16: rows given the same pose changed 0 px at any level
# (output/face_rig/r2/mpfb_ge_props.png rows 2 and 3,
# output/face_rig/r2/driven_sheet.png rows 3 and 4), and every face-only row
# checked changed at least 7 px by 8 levels in its busiest angle (the MPFB
# viseme_aa row at 128 px; the add-jaw and ICT mouth sheets changed more).
# The floor still holds on Cycles, which render_sheet.py has drawn with since
# 2026-09-18: `render_sheet.py output/assets/alchemist_warrior/rig.fbx --poses
# frames:1,1 --angles 2 --size 128 --check` (2026-09-18) called row 1 the rest
# pose repeated, `silhouette max difference 0.0000, and no pixel changed by 8
# levels or more`, so path tracing one scene twice is not noise this has to
# survive. What a
# face-only row changes on Cycles was not re-measured; the sampling above says
# it moves pixels further, not fewer.
COLOUR_LEVELS = 8


def slice_sheet(path: Path, cell: int):
    """Cut a sheet into [row][col] RGBA arrays (height, width, 4). Angles across,
    poses down."""
    im = Image.open(path).convert("RGBA")
    cols, rows = im.width // cell, im.height // cell
    if cols < 1 or rows < 1:
        raise SystemExit(f"{path.name}: {im.width}x{im.height} is smaller than "
                         f"one {cell}px cell. Pass the --cell size it was rendered at.")
    a = np.asarray(im)
    return [[a[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell]
             for c in range(cols)] for r in range(rows)], rows, cols


def check(cells, rows, cols, azimuths=None, empty_floor=0.005, same_eps=0.002,
          colour_levels=COLOUR_LEVELS):
    """Return (findings, facts). A finding is something wrong.

    cells are RGBA arrays from slice_sheet. A 2D array is read as alpha alone,
    and then rows are compared by silhouette only."""
    findings, facts = [], []
    alpha = [[c[..., 3] if c.ndim == 3 else c for c in row] for row in cells]
    mask = [[a > 128 for a in row] for row in alpha]
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
    #    The silhouette alone cannot see a pose that moves only what is inside
    #    it, such as a jaw or a mouth shape key, so a row with row 0's
    #    silhouette is also compared pixel by pixel before it is called a repeat.
    if rows > 1:
        for r in range(1, rows):
            diffs = [np.abs(mask[r][c].astype(np.float32)
                            - mask[0][c].astype(np.float32)).mean()
                     for c in range(cols)]
            if max(diffs) >= same_eps:
                continue
            colour = all(c.ndim == 3 for c in cells[0] + cells[r])
            changed = [int((np.abs(cells[r][c].astype(np.int16)
                                   - cells[0][c].astype(np.int16)).max(axis=2)
                            >= colour_levels).sum())
                       for c in range(cols)] if colour else []
            if colour and max(changed):
                facts.append(
                    f"pose row {r} keeps row 0's silhouette at every angle, but "
                    f"{'/'.join(str(n) for n in changed)} px inside it changed by "
                    f"{colour_levels} levels or more, as a face-only pose does: "
                    "look at it to judge whether that is the change you meant")
                continue
            findings.append(
                f"pose row {r} is identical to row 0 at every angle "
                f"(silhouette max difference {max(diffs):.4f}"
                + (f", and no pixel changed by {colour_levels} levels or more"
                   if colour else "; colour not compared")
                + "). The pose did nothing: you are looking at the rest pose repeated")

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
    ap.add_argument("--empty-floor", type=float, default=0.005,
                    help="a cell with less of its area covered is empty (default 0.005)")
    ap.add_argument("--same-eps", type=float, default=0.002,
                    help="a row whose silhouette differs from row 0 by less than this "
                         "share of the cell at every angle keeps its silhouette "
                         "(default 0.002)")
    ap.add_argument("--colour-levels", type=int, default=COLOUR_LEVELS,
                    help="a pixel changed when an RGBA channel moved by this many "
                         f"levels or more (default {COLOUR_LEVELS}). A row that keeps "
                         "row 0's silhouette and changes no pixel is the rest pose "
                         "repeated")
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
                                args.empty_floor, args.same_eps, args.colour_levels)
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
