#!/usr/bin/env python3
"""Make a scalp texture for make_hair.py's cap with the repo's ComfyUI text-to-image graph.

    scripts/make_scalp.py --colour black                       # output/hair/scalp_black.png
    scripts/make_scalp.py --colour brown --style stubble --seed 3
    scripts/make_scalp.py --colour auburn --raw output/hair/scalp_black_raw.png   # retint, no job
    scripts/make_hair.py --style short --colour black --cap-diffuse output/hair/scalp_black.png

One ComfyUI job at the graph's native size (the ground preset, 1024 square,
by default), fetched back over /view so the repo's output mount is never
assumed, made to tile with make_seamless.py's own functions, tinted to the
hair colour's root darkened by the CAP_DARKEN that make_hair.py's painted cap
uses (0.75, HAIR-047), and written beside a JSON of the prompt, seed, graph,
timings and the seam scores.  A 2 by 2 tiled preview is written too, because
a seam score can pass while the tile still repeats recognisably
(skills/ground-texture).

The generator cannot draw a tiling image (no circular padding decode in this
install, make_seamless.py), so the seam is mended afterwards.  The tint is
monotone per texel, so tiling first and tinting second keeps the mend.

The queue is read before the job and the script waits until it is empty, so
it never queues on top of someone else's job and never two of its own.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import make_hair                                    # noqa: E402  COLOURS, CAP_DARKEN, colour_arg
import make_seamless                                # noqa: E402  trim_border, make_seamless, seam_score
import run_workflow as rw                           # noqa: E402  api, queue_ids, wait_for

OUT = ROOT / "output" / "hair"
GRAPH = ROOT / "workflows" / "api" / "preset_ground_texture.json"

# The Positive text keeps every protective clause of the ground preset
# (skills/ground-texture: overhead, uniform density, no focal point, macro
# crop, flat light), because each one stops a failure that would also wreck a
# scalp: a horizon, a composition, a baked shadow.  The subject sentence is
# what changes with --style, and it frames the skin as a DERMATOSCOPE view and
# never says "scalp" or "head": asked for "a human scalp with short dark hair"
# and then for "buzz-cut hair stubble growing from pale skin", the model drew
# a whole head with a forehead and a grey background both times, whatever
# the negative said (seed 1 on the ground preset, 2026-09-22); the
# dermatoscope wording gave a flat top-down field of strokes on skin first
# time.  The scalp wants defined follicles, not a colour fill (HAIR-047,
# HAIR-048), so the hair shafts are asked for by name; the tint is applied
# afterwards, so the colour asked for here only has to give dark hair on
# lighter skin.
STYLE_SUBJECT = {
    "crop": "pale skin with short dark hair shafts emerging from their follicles, cut to a few "
            "millimetres of stubble, thousands of them",
    "stubble": "pale skin freshly shaved, with fine dark dots where each hair shaft was cut "
               "flush with its follicle, mostly bare skin between the dots",
    "bald": "bare shaved pale skin with fine pores and faint empty follicles, no hair",
}
POSITIVE = ("A seamless tileable texture, a dermatoscope view of the surface of {subject}, "
            "filling the whole frame edge to edge, looking straight down at the skin. Fine "
            "even detail spread uniformly across the whole frame, the same density "
            "everywhere, no large shapes and no focal point, like a close macro crop of a "
            "much larger surface. Flat shadowless overcast light, no highlights, no shine, "
            "stylised flat painted game texture, matte colours, crisp small-scale detail.")
# The preset's negative, plus what a hair prompt invites: a head, a face, a
# hairline, long hair, a background, and the specular shine a rendered cap
# must not carry.
NEGATIVE = ("horizon, sky, perspective, vanishing point, buildings, figures, people, animals, "
            "path, road, river, fence, text, watermark, signature, border, frame, vignette, "
            "drop shadow, strong directional shadow, single large object, centred subject, "
            "large shapes, sweeping curves, arcs, swirls, composition, focal point, tilt "
            "shift, blur, depth of field, mosaic, tiles, bricks, head, scalp outline, face, "
            "eyes, ears, nose, mouth, eyebrows, forehead, neck, head silhouette, skull shape, "
            "hairline, parting, background, plain background, grey background, long hair, "
            "wavy hair, strands, comb over, specular highlight, shine, gloss, wet, glossy, "
            "photograph, photo realistic, 3d render")

# make_seamless.py's own pass condition (both tests must fail before it warns).
SEAM_RATIO_MAX, SEAM_ABS_MAX = 1.6, 4.0
# How far a texel may go above the median before the tint clips it (guess): at
# 2.5 a black cap's brightest skin texel is 0.25, a little below the tip.
LUM_MAX = 2.5


def node_by_title(graph: dict, title: str) -> dict:
    for node in graph.values():
        if isinstance(node, dict) and node.get("_meta", {}).get("title") == title:
            return node
    raise SystemExit(f"the graph has no node titled {title!r}; it needs Positive, Negative, "
                     "Latent, Sampler and Save, as the txt2img graphs have")


def wait_queue_empty(limit: float, poll: float = 5.0) -> float:
    """Seconds spent waiting for /queue to empty; refuses after [limit].

    Another track may be using the server, and the rule is one job at a time
    and never on top of someone else's, so the script waits rather than
    queueing behind them."""
    t0 = time.time()
    while True:
        running, pending = rw.queue_ids()
        if not running and not pending:
            return round(time.time() - t0, 1)
        waited = time.time() - t0
        if waited > limit:
            raise SystemExit(f"the ComfyUI queue still has {len(running)} running and "
                             f"{len(pending)} pending after {waited:.0f}s; nothing was queued. "
                             "Raise --queue-wait or try later")
        print(f"\r  waiting for the queue ({len(running)} running, {len(pending)} pending, "
              f"{waited:.0f}s)", end="", flush=True)
        time.sleep(poll)


def fetch_output(entry: dict) -> tuple[bytes, str]:
    """The first image the job saved, fetched over GET /view."""
    for out in entry.get("outputs", {}).values():
        for it in out.get("images", []) or []:
            if isinstance(it, dict) and "filename" in it:
                q = urllib.parse.urlencode({"filename": it["filename"],
                                            "subfolder": it.get("subfolder", ""),
                                            "type": it.get("type", "output")})
                url = f"{rw.SERVER.rstrip('/')}/view?{q}"
                with urllib.request.urlopen(url, timeout=120) as r:
                    return r.read(), f"{it.get('subfolder', '')}/{it['filename']}".lstrip("/")
    raise SystemExit("the job finished but saved no image; the graph's Save node recorded nothing")


def generate(args, prompt: str, negative: str, timings: dict) -> tuple[Image.Image, dict]:
    graph = json.loads(args.graph.read_text())
    node_by_title(graph, "Positive")["inputs"]["text"] = prompt
    node_by_title(graph, "Negative")["inputs"]["text"] = negative
    sampler = node_by_title(graph, "Sampler")["inputs"]
    sampler["seed"] = args.seed
    if args.steps is not None:
        sampler["steps"] = args.steps
    latent = node_by_title(graph, "Latent")["inputs"]
    node_by_title(graph, "Save")["inputs"]["filename_prefix"] = f"hair/scalp/{args.style}"
    meta = {"graph": str(args.graph.relative_to(ROOT) if args.graph.is_relative_to(ROOT) else args.graph),
            "native_size": [latent["width"], latent["height"]],
            "seed": sampler["seed"], "steps": sampler["steps"], "cfg": sampler["cfg"],
            "sampler": sampler["sampler_name"], "scheduler": sampler["scheduler"]}
    for title in ("Qwen Diffusion", "Checkpoint"):
        try:
            ins = node_by_title(graph, title)["inputs"]
            meta["model"] = ins.get("unet_name") or ins.get("ckpt_name")
        except SystemExit:
            pass
    if args.dry_run:
        print(json.dumps({k: v for k, v in graph.items() if isinstance(v, dict) and "class_type" in v},
                         indent=2))
        raise SystemExit(0)

    timings["queue_wait_s"] = wait_queue_empty(args.queue_wait)
    if timings["queue_wait_s"]:
        print()
    graph = {k: v for k, v in graph.items() if isinstance(v, dict) and "class_type" in v}
    t0 = time.time()
    res = rw.api("/prompt", {"prompt": graph, "client_id": "make_scalp"})
    if res.get("node_errors"):
        print(json.dumps(res["node_errors"], indent=2))
        raise SystemExit(1)
    pid = res["prompt_id"]
    print(f"  queued    {pid} on {meta['graph']} at {latent['width']}x{latent['height']}, "
          f"seed {args.seed}, {sampler['steps']} steps")
    entry = rw.wait_for(pid)
    timings["generate_s"] = round(time.time() - t0, 1)
    if entry.get("status", {}).get("status_str") == "error":
        rw.report(entry, since=t0)
        raise SystemExit(1)
    t0 = time.time()
    raw, server_name = fetch_output(entry)
    timings["fetch_s"] = round(time.time() - t0, 2)
    meta.update({"prompt_id": pid, "server_file": server_name})
    return Image.open(io.BytesIO(raw)).convert("RGB"), meta


def square(im: Image.Image) -> tuple[Image.Image, bool]:
    """Centre-crop a non-square generation, because make_seamless's --size would squash it."""
    w, h = im.size
    if w == h:
        return im, False
    s = min(w, h)
    return im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)), True


def tint(im: Image.Image, cap_rgb01: np.ndarray, contrast: float) -> Image.Image:
    """The image's luminance about its median, times the darkened root colour.

    The median texel is the skin between the hairs (the image's mode), and it
    lands on the base colour the painted cap uses, so a scalp from here sits
    under the same hair at the same darkness with the follicles below it,
    which is the sense HAIR-047 asks for (scalp darker than the strips,
    follicles defined).  --contrast scales that swing.
    """
    g = np.asarray(im.convert("L"), dtype=np.float32) / 255.0
    lum = g / max(float(np.median(g)), 1e-3)
    lum = np.clip(1.0 + (lum - 1.0) * contrast, 0.0, LUM_MAX)
    rgb = np.clip(lum[..., None] * cap_rgb01[None, None, :], 0.0, 1.0)
    return Image.fromarray((rgb * 255.0 + 0.5).astype(np.uint8), mode="RGB")


def tiled_preview(im: Image.Image, path: Path) -> None:
    w, h = im.size
    sheet = Image.new("RGB", (w * 2, h * 2))
    for y in range(2):
        for x in range(2):
            sheet.paste(im, (x * w, y * h))
    sheet.resize((w, h), Image.LANCZOS).save(path)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="colours: " + ", ".join(sorted(make_hair.COLOURS)))
    ap.add_argument("--colour", type=make_hair.colour_arg, default="black", metavar="NAME|R,G,B",
                    help="hair colour the scalp is tinted to, a make_hair.py name or sRGB R,G,B "
                         "(default black); the root colour times 0.75, as the painted cap")
    ap.add_argument("--style", choices=sorted(STYLE_SUBJECT), default="crop",
                    help="what the prompt asks for (default crop): crop is short dark hair on "
                         "skin, stubble is shaved dots, bald is bare skin with pores")
    ap.add_argument("--graph", type=Path, default=GRAPH,
                    help="the text-to-image graph to run (default workflows/api/"
                         "preset_ground_texture.json, Qwen at 1024 square); txt2img_qwen.json "
                         "and txt2img_sdxl.json work too, and a non-square native size is "
                         "centre-cropped before tiling")
    ap.add_argument("--seed", type=int, default=1, help="sampler seed (default 1)")
    ap.add_argument("--steps", type=int, default=None,
                    help="sampler steps; default is the graph's own (20 on the preset)")
    ap.add_argument("--raw", type=Path, default=None, metavar="PNG",
                    help="skip the ComfyUI job and tile and tint this image instead, for "
                         "example the _raw.png of an earlier run in another colour")
    ap.add_argument("--contrast", type=float, default=1.0,
                    help="scale of the follicle contrast about the cap colour (default 1.0, "
                         "the image's own)")
    ap.add_argument("--blend", type=float, default=0.16,
                    help="how much of the tile make_seamless's handover spans (default 0.16, "
                         "its own default)")
    ap.add_argument("--size", type=int, default=make_hair.CAP_TEXTURE,
                    help=f"written size in px (default {make_hair.CAP_TEXTURE}, the cap map)")
    ap.add_argument("--name", default=None,
                    help="output stem (default scalp_<colour>)")
    ap.add_argument("--out", type=Path, default=OUT,
                    help="output directory (default output/hair)")
    ap.add_argument("--queue-wait", type=float, default=900.0, metavar="S",
                    help="how long to wait for the ComfyUI queue to empty before giving up "
                         "(default 900)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the resolved graph and queue nothing")
    args = ap.parse_args()

    root_rgb, _tip, _fly = args.colour
    named = next((n for n, c in make_hair.COLOURS.items() if c == args.colour), None)
    stem = args.name or "scalp_" + (named or "-".join(str(c) for c in root_rgb))
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    cap01 = np.array(root_rgb, dtype=np.float64) / 255.0 * make_hair.CAP_DARKEN
    prompt = POSITIVE.format(subject=STYLE_SUBJECT[args.style])

    started = time.time()
    timings, meta = {}, {}
    if args.raw:
        src = args.raw if args.raw.is_absolute() else ROOT / args.raw
        im = Image.open(src).convert("RGB")
        meta = {"raw_from": str(src)}
        print(f"  raw       {src} {im.size[0]}x{im.size[1]}, no job")
    else:
        im, meta = generate(args, prompt, NEGATIVE, timings)
        print(f"  generated {im.size[0]}x{im.size[1]} in {timings['generate_s']} s "
              f"(queue wait {timings['queue_wait_s']} s)")
    files = {"raw": out / f"{stem}_raw.png"}
    im.save(files["raw"])

    t0 = time.time()
    im, cropped = square(im)
    im, border = make_seamless.trim_border(im)
    before, before_abs = (float(v) for v in
                          make_seamless.seam_score(np.asarray(im.convert("L"), dtype=np.float32)))
    tile = make_seamless.make_seamless(im, args.blend)
    # make_seamless rolls the image by half so the mend sits in the middle;
    # rolled back, the tile is still periodic and the layout is the one the
    # model drew, which matters here because the cap uses the image ONCE with
    # its top row at the face: the whorl the model draws near the bottom
    # centre then lands at the back of the crown, near make_hair.py's own.
    tile = Image.fromarray(np.roll(np.roll(np.asarray(tile), -(tile.size[0] // 2), axis=1),
                                   -(tile.size[1] // 2), axis=0))
    if tile.size != (args.size, args.size):
        tile = tile.resize((args.size, args.size), Image.LANCZOS)
    timings["tile_s"] = round(time.time() - t0, 2)
    t0 = time.time()
    final = tint(tile, cap01, args.contrast)
    timings["tint_s"] = round(time.time() - t0, 2)
    g = np.asarray(final.convert("L"), dtype=np.float32)
    after, after_abs = (float(v) for v in make_seamless.seam_score(g))
    passed = not (after > SEAM_RATIO_MAX and after_abs > SEAM_ABS_MAX)
    files["png"] = out / f"{stem}.png"
    files["tiled"] = out / f"{stem}_tiled.png"
    files["json"] = out / f"{stem}.json"
    final.save(files["png"])
    tiled_preview(final, files["tiled"])
    timings["total_s"] = round(time.time() - started, 1)

    cap8 = [int(round(c * 255)) for c in cap01]
    print(f"  square    {'centre-cropped' if cropped else 'native square'}, "
          f"border trimmed {border} px")
    print(f"  seam      {after:.2f}x ({after_abs:.1f}/255) after, was {before:.2f}x "
          f"({before_abs:.1f}/255); {'passed' if passed else 'STILL SHOWS, raise --blend'} "
          f"(fails only when both exceed {SEAM_RATIO_MAX}x and {SEAM_ABS_MAX}/255)")
    print(f"  tint      {named or 'custom'} root {tuple(root_rgb)} x {make_hair.CAP_DARKEN} = "
          f"{tuple(cap8)}; median written {tuple(int(v) for v in np.median(np.asarray(final).reshape(-1, 3), axis=0))}")
    # for scale: make_hair.py's painted caps measure 1.1 (crop, black) and
    # 2.3 (bob, brown) by the same figure (2026-09-22), so a dark cap is
    # flat by nature and make_seamless.py's ground threshold of 8 does not apply
    print(f"  contrast  {g.std():.1f} levels std (the painted crop cap is 1.1, the bob 2.3)")
    print(f"  wrote     {files['png'].name} {final.size[0]}px, {files['tiled'].name}, "
          f"{files['raw'].name}, {files['json'].name} in {out}")

    report = {
        "made_by": "scripts/make_scalp.py", "date": str(date.today()),
        "colour": named or list(root_rgb), "root_rgb": list(root_rgb), "cap_rgb": cap8,
        "cap_darken": make_hair.CAP_DARKEN, "style": args.style if not args.raw else None,
        "prompt": prompt if not args.raw else None, "negative": NEGATIVE if not args.raw else None,
        **meta,
        "square": "centre-cropped" if cropped else "native",
        "border_trimmed_px": border, "blend": args.blend, "contrast_scale": args.contrast,
        "seam": {"before_ratio": round(before, 3), "before_abs": round(before_abs, 2),
                 "after_ratio": round(after, 3), "after_abs": round(after_abs, 2),
                 "passed": passed},
        "contrast_std": round(float(g.std()), 2), "size": final.size[0],
        "timings": timings,
        "files": {k: str(v) for k, v in files.items()},
    }
    files["json"].write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
