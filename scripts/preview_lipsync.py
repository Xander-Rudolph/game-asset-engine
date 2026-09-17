#!/usr/bin/env python3
"""Play a mouth set against a timeline as an MP4, and lay the mouths out on one labelled sheet.

    scripts/preview_lipsync.py output/lipsync/lord_vitriol/manifest.json \\
        output/lipsync/lord_vitriol/concord.json

    scripts/preview_lipsync.py output/lipsync/lord_vitriol/manifest.json \\
        output/lipsync/lord_vitriol/concord_12fps.json --label --no-sheet

    scripts/preview_lipsync.py output/lipsync/lord_vitriol/manifest.json \\
        output/lipsync/lord_vitriol/vial_12fps.json --height 512 --no-sheet

    scripts/preview_lipsync.py output/lipsync/lord_vitriol/manifest.json   # sheet only

WHY: a mouth set is judged in two ways, and neither is a number. Each mouth must
read as its shape, which needs the nine side by side; and the set must read as
speech when it plays, which needs it moving. The sheet is a PNG so it can be
read back into a conversation, which a video cannot.

THE MANIFEST is the one `scripts/compose_mouths.py` writes: the portrait, the
mouth box, and one overlay per shape, with paths relative to the manifest. A
shape the set lacks plays its fallback (G as A, H as C, X as A), as Rhubarb
itself substitutes for disabled shapes.

THE TIMELINE is Rhubarb's JSON with fields added around it, as in
docs/reference/lip-sync.md, "The timeline file":

    {"duration": 0.42, "fps": 12,
     "mouthCues": [{"start": 0.00, "end": 0.06, "value": "X"}, ...],
     "frames": ["X", "B", "F", "F", "X"]}

- `frames` present: they are played as they are, one per frame, at `fps`.
- otherwise `mouthCues` are sampled at each frame's midpoint; a time no cue
  covers shows X. The clip lasts `duration`, or to the last cue's end.
- the frame rate is the timeline's `fps`, or 24 when it has none.
- audio: `--audio`, or else the timeline's `audio` field when that file exists
  beside the timeline. With audio the clip is held on X until the audio ends.

OUTPUTS: by default `<timeline stem>.mp4` beside the timeline and
`contact_sheet.png` beside the manifest. H.264 in yuv420p, so an odd width or
height is padded by one pixel, and an odd `--height` is rounded up to the next
even number. Every frame's shape is resolved before ffmpeg starts, and the MP4
is written to a hidden partial file that replaces the output only when ffmpeg
succeeds, so a bad timeline never leaves a short clip behind. Needs ffmpeg and
ffprobe on the PATH.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("needs numpy and Pillow: pip install --user numpy Pillow")

ORDER = ["X", "A", "B", "C", "D", "E", "F", "G", "H"]
# Short captions for the sheet, after "The mapping to adopt" in docs/reference/lip-sync.md.
CAPTION = {
    "X": "rest, lips relaxed",
    "A": "closed: P B M",
    "B": "teeth together: K S T, EE",
    "C": "open: EH AE",
    "D": "wide open: AA",
    "E": "rounded: AO ER",
    "F": "puckered: UW OW W",
    "G": "teeth on lip: F V",
    "H": "tongue up: long L",
}


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                 # Pillow before 10.1 has one fixed size
        return ImageFont.load_default()


def read_json(path: Path, what: str) -> dict:
    try:
        data = json.loads(path.read_text())
    except OSError as e:
        raise SystemExit(f"cannot read the {what} {path}: {e.strerror or e}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"the {what} {path} is not valid JSON: {e}")
    if not isinstance(data, dict):
        raise SystemExit(f"the {what} {path} is not a JSON object")
    return data


def open_image(path: Path, mode: str) -> Image.Image:
    try:
        with Image.open(path) as im:
            return im.convert(mode)
    except OSError as e:
        raise SystemExit(f"cannot read {path}: {e}")


def load_set(manifest_path: Path):
    m = read_json(manifest_path, "manifest")
    missing = [k for k in ("portrait", "size", "mouth", "shapes") if k not in m]
    if missing:
        raise SystemExit(f"the manifest {manifest_path} has no {', '.join(missing)}. "
                         "Write it with scripts/compose_mouths.py")
    here = manifest_path.parent
    portrait = open_image(here / m["portrait"], "RGB")
    box = m["mouth"]
    overlays = {s: open_image(here / p, "RGBA") for s, p in m["shapes"].items()}
    return m, portrait, box, overlays


def resolve(shape: str, m: dict, overlays: dict) -> str:
    seen = []
    s = shape
    while s not in overlays:
        seen.append(s)
        s = m.get("fallback", {}).get(s)
        if s is None or s in seen:
            raise SystemExit(f"shape {shape!r} is not in the set and has no "
                             f"fallback that is (tried {' -> '.join(seen)})")
    return s


def composite(portrait: Image.Image, box: dict, overlay: Image.Image) -> Image.Image:
    im = portrait.copy()
    im.paste(overlay.convert("RGB"), (box["x"], box["y"]), overlay.getchannel("A"))
    return im


def frames_from_timeline(t: dict, audio_seconds: float | None):
    """(fps, [shape per frame], how) from a timeline dict."""
    fps = t.get("fps") or 24
    if t.get("frames"):
        frames = [str(v) for v in t["frames"]]
        how = f"{len(frames)} frames from 'frames'"
        if not t.get("fps"):
            how += ", which has no 'fps': played at 24"
    else:
        cues = t.get("mouthCues")
        if not cues:
            raise SystemExit("timeline has neither 'frames' nor 'mouthCues'")
        end = t.get("duration") or max(float(c["end"]) for c in cues)
        n = max(1, math.ceil(round(float(end) * fps, 6)))
        frames = []
        for i in range(n):
            mid = (i + 0.5) / fps
            hit = next((c["value"] for c in cues
                        if float(c["start"]) <= mid < float(c["end"])), "X")
            frames.append(str(hit))
        how = f"{len(cues)} cues sampled at frame midpoints into {n} frames"
    if audio_seconds is not None:
        need = math.ceil(round(audio_seconds * fps, 6))
        if need > len(frames):
            how += f", held on X for {need - len(frames)} more to cover the audio"
            frames += ["X"] * (need - len(frames))
    return float(fps), frames, how


def probe_seconds(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nokey=1:noprint_wrappers=1", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise SystemExit(f"ffprobe could not read a duration from {path}:\n{r.stderr[-800:]}")


def write_mp4(out: Path, frames: list[str], fps: float, m: dict, portrait: Image.Image,
              box: dict, overlays: dict, audio: Path | None, label: bool,
              height: int | None) -> None:
    cache = {}
    w, h = portrait.size
    tag_font = font(max(14, h // 24))
    # Resolve every frame first: a shape with no overlay and no fallback must
    # fail before ffmpeg has written anything.
    shown_per_frame = [resolve(s, m, overlays) for s in frames]

    def frame_image(i: int, s: str) -> bytes:
        shown = shown_per_frame[i]
        if shown not in cache:
            cache[shown] = composite(portrait, box, overlays[shown])
        if not label:
            return cache[shown].tobytes()
        im = cache[shown].copy()
        d = ImageDraw.Draw(im)
        text = s + (f" as {shown}" if shown != s else "") + f"  {i / fps:5.2f}s"
        d.rectangle((0, 0, w, getattr(tag_font, "size", 11) + 12), fill=(0, 0, 0))
        d.text((8, 6), text, fill=(255, 255, 255), font=tag_font)
        return im.tobytes()

    vf = []
    if height:
        vf.append(f"scale=-2:{height}:flags=lanczos")
    else:
        vf.append("pad=ceil(iw/2)*2:ceil(ih/2)*2")
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-framerate", f"{fps:g}", "-i", "-"]
    if audio:
        cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k"]
    out.parent.mkdir(parents=True, exist_ok=True)
    partial = out.with_name(f".{out.stem}.partial{out.suffix}")
    cmd += ["-vf", ",".join(vf), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-movflags", "+faststart", "-f", "mp4", str(partial)]
    done = False
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for i, s in enumerate(frames):
                proc.stdin.write(frame_image(i, s))
            proc.stdin.close()
        except BrokenPipeError:
            pass
        err = proc.stderr.read().decode(errors="replace")
        if proc.wait() != 0:
            raise SystemExit(f"ffmpeg failed ({proc.returncode}), {out} left as it was:\n"
                             f"{err[-2000:]}")
        os.replace(partial, out)
        done = True
    finally:
        if not done:
            partial.unlink(missing_ok=True)


def contact_sheet(out: Path, m: dict, portrait: Image.Image, box: dict,
                  overlays: dict, cell: int = 300, usage: dict | None = None) -> None:
    """The portrait with its box on the left, the nine mouths in a 3x3 grid."""
    x, y, bw, bh = box["x"], box["y"], box["w"], box["h"]
    # Show the box plus half its size on each side, so the seam is in view.
    mx, my = bw // 2, bh // 2
    region = (max(0, x - mx), max(0, y - my),
              min(portrait.width, x + bw + mx), min(portrait.height, y + bh + my))
    rw, rh = region[2] - region[0], region[3] - region[1]
    ch = round(cell * rh / rw)
    cap_h = 44
    grid_w, grid_h = 3 * cell, 3 * (ch + cap_h)
    th = grid_h
    tw = round(portrait.width * th / portrait.height)
    sheet = Image.new("RGB", (tw + grid_w, grid_h), (24, 24, 24))
    thumb = portrait.resize((tw, th), Image.LANCZOS)
    d = ImageDraw.Draw(thumb)
    k = th / portrait.height
    d.rectangle((x * k, y * k, (x + bw) * k, (y + bh) * k), outline=(255, 64, 64), width=2)
    sheet.paste(thumb, (0, 0))
    d = ImageDraw.Draw(sheet)
    big, small = font(20), font(14)
    drift = m.get("drift", {})
    for i, s in enumerate(ORDER):
        cx, cy = tw + (i % 3) * cell, (i // 3) * (ch + cap_h)
        shown = resolve(s, m, overlays)
        im = composite(portrait, box, overlays[shown]).crop(region)
        sheet.paste(im.resize((cell, ch), Image.LANCZOS), (cx, cy + cap_h))
        title = s if shown == s else f"{s}  (absent: plays {shown})"
        d.text((cx + 8, cy + 4), title, fill=(255, 255, 255), font=big)
        info = CAPTION[s]
        if s in drift and shown == s:
            info += f"   drift {drift[s]:.2f}"
        if usage is not None:
            n = usage.get(s, 0)
            info += f"   {n} frame{'' if n == 1 else 's'}"
        d.text((cx + 8, cy + 26), info, fill=(200, 200, 200), font=small)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("timeline", type=Path, nargs="?",
                    help="timeline JSON; without one only the contact sheet is made")
    ap.add_argument("--audio", type=Path, help="audio to mux into the MP4")
    ap.add_argument("--out", type=Path, help="MP4 path (default: <timeline stem>.mp4 beside it)")
    ap.add_argument("--sheet", type=Path,
                    help="contact sheet path (default: contact_sheet.png beside the manifest)")
    ap.add_argument("--no-sheet", action="store_true", help="skip the contact sheet")
    ap.add_argument("--label", action="store_true",
                    help="print the shape and time on every frame of the MP4")
    ap.add_argument("--height", type=int, help="scale the MP4 to this height")
    ap.add_argument("--cell", type=int, default=300, help="sheet cell width (default 300)")
    args = ap.parse_args()
    if args.height is not None:
        if args.height <= 0:
            ap.error("--height must be a positive number of pixels")
        if args.height % 2:
            print(f"  --height {args.height} is odd, which H.264 in yuv420p cannot "
                  f"encode: using {args.height + 1}")
            args.height += 1
    if args.cell <= 0:
        ap.error("--cell must be a positive number of pixels")

    for tool in ("ffmpeg", "ffprobe"):
        if args.timeline and not shutil.which(tool):
            raise SystemExit(f"{tool} is not on the PATH")
    m, portrait, box, overlays = load_set(args.manifest)
    if portrait.size != tuple(m["size"]):
        print(f"  ! portrait is {portrait.width}x{portrait.height}, manifest says "
              f"{m['size'][0]}x{m['size'][1]}. Run compose_mouths.py --check")

    usage = None
    if args.timeline:
        t = read_json(args.timeline, "timeline")
        audio = args.audio
        if audio is None and t.get("audio"):
            cand = Path(os.path.normpath(args.timeline.parent / t["audio"]))
            if cand.exists():
                audio = cand
            else:
                print(f"  timeline names audio {t['audio']!r}, not found beside it: silent")
        if audio is not None and not audio.exists():
            raise SystemExit(f"no such audio: {audio}")
        seconds = probe_seconds(audio) if audio else None
        try:
            fps, frames, how = frames_from_timeline(t, seconds)
        except (KeyError, TypeError, ValueError) as e:
            raise SystemExit(f"the timeline {args.timeline} has a malformed entry "
                             f"({type(e).__name__}: {e}); cues need start, end and value")
        usage = {s: frames.count(s) for s in ORDER}
        out = args.out or args.timeline.with_suffix(".mp4")
        write_mp4(out, frames, fps, m, portrait, box, overlays, audio,
                  args.label, args.height)
        print(f"  timeline {args.timeline}: {how}")
        print(f"  shapes   " + " ".join(f"{s}:{usage[s]}" for s in ORDER if usage[s]))
        print(f"  mp4      {out}  ({len(frames)} frames at {fps:g} fps, "
              f"{len(frames) / fps:.2f}s{', with ' + str(audio) if audio else ', silent'})")

    if not args.no_sheet:
        sheet = args.sheet or args.manifest.parent / "contact_sheet.png"
        contact_sheet(sheet, m, portrait, box, overlays, cell=args.cell, usage=usage)
        print(f"  sheet    {sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
