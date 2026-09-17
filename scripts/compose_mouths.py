#!/usr/bin/env python3
"""Cut a talking portrait's mouths out of whole-image edits, and prove the rest is untouched.

    scripts/compose_mouths.py output/lipsync/lord_vitriol/portrait.png \\
        --box 410,440,204,190 --edits output/lipsync/lord_vitriol/edits --feather 8

    scripts/compose_mouths.py output/lipsync/lord_vitriol/portrait.png \\
        --box 420,444,184,160 --edits output/lipsync/lord_vitriol/edits \\
        --out output/lipsync/lord_vitriol/_trials/small_box        # try another box

    scripts/compose_mouths.py --check output/lipsync/lord_vitriol/manifest.json

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

1. **Brings each edit back to the portrait's frame.** The edit graph's
   FluxKontextImageScale resizes to the nearest trained resolution, cropping
   the centre when the aspect ratio differs. That crop is undone: the edit is
   resized (Lanczos) onto the part of the portrait it came from. A portrait
   already at a trained size, such as 1024x1024, needs no resize at all.
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


def kontext_crop(portrait: tuple[int, int], edit: tuple[int, int]):
    """The part of the portrait the edit graph kept: (x0, y0, w, h).

    Mirrors the centre crop ComfyUI's common_upscale applies before resizing
    when the aspect ratios differ, so an edit can be put back where it came from.
    """
    pw, ph = portrait
    ew, eh = edit
    old, new = pw / ph, ew / eh
    x0 = y0 = 0
    if old > new:
        x0 = round((pw - pw * (new / old)) / 2)
    elif old < new:
        y0 = round((ph - ph * (old / new)) / 2)
    return x0, y0, pw - 2 * x0, ph - 2 * y0


def crop_covers_box(portrait: tuple[int, int], edit: tuple[int, int], box: dict) -> bool:
    """Does an edit of size [edit] still hold the whole mouth box after the crop?"""
    x0, y0, cw, ch = kontext_crop(portrait, edit)
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
    x0, y0, cw, ch = kontext_crop(portrait.size, edit.size)
    resized = edit.convert("RGB").resize((cw, ch), Image.LANCZOS)
    out = base.copy()
    out[y0:y0 + ch, x0:x0 + cw] = np.asarray(resized, dtype=np.float32)
    covered[y0:y0 + ch, x0:x0 + cw] = True
    note = f"resized {edit.size[0]}x{edit.size[1]} to {cw}x{ch}"
    if (x0, y0) != (0, 0):
        note += f" at {x0},{y0} (undoing the edit graph's centre crop)"
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
    args = ap.parse_args()

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
