#!/usr/bin/env python3
"""Make a generated music track loop without a seam, at a set loudness.

    scripts/make_loop.py output/music/plains_00001.flac plains.mp3 --bpm 90
    scripts/make_loop.py in.flac out.mp3 --lufs -14 --bitrate 96k

A game loops its music: the last sample runs straight into the first, so a
track that ends on a fade, a closing chord or half a bar stumbles at the join
every time round. This does five things, in order:

1. **Trims.** Silence comes off the front. The ending comes off the back: the
   track is cut after the last second still within `--tail-db` of its typical
   loudness, so a fade-out or a ringing final chord goes.
2. **Chooses where the loop starts and ends.** A generated take rarely holds
   one level. Most open quietly and build, and some swell or thin out near
   the end, so a loop from the very first bar dips every time it comes round.
   The start is searched over the first `--search` of the track (30%) and the
   end over the last, and every pair is scored on four things:
   - the jump in level where the loop comes round: the bars after the start
     against the bars before the end's crossfade;
   - how far either of those passages sits under the track's typical level,
     so a quiet opening is never matched with an equally quiet ending;
   - how well the rhythm (the onset envelope) of the two crossfaded passages
     matches, so the beats line up through the join even if the model drifted
     off the tempo it was asked for, which a cut at whole bars would not;
   - length, lightly: a longer loop repeats less, so it wins a near tie.
3. **Joins.** The end's last bars are crossfaded over the start's first and
   the track is cut there, so the file's last sample leads straight into its
   first: the join is continuous by construction. The fade keeps the level
   steady for how alike the two passages are. Two rhythm-matched passages are
   partly in phase, and a plain equal-power fade adds up to 3 dB where they
   overlap; the gains are divided by sqrt(c^2 + s^2 + 2*rho*c*s), with rho
   the passages' measured correlation, which is equal power when they are
   unrelated and equal gain when they are identical.
4. **Sets the level** with one constant gain, never a time-varying one, which
   would leave a step in level at the join.
5. **Limits the peaks** the gain pushed past the ceiling. A limiter is
   time-varying, so run over the loop once it would treat the end and the
   start differently. It runs over three copies back to back instead, and
   keeps the middle one, which is limited exactly as it will be heard: after
   its own end. `--no-limit` holds the gain back instead, quieter than asked.
   Limiting takes loudness off, and so does the encoder, so the written file
   is measured and the gain made up, in up to three passes.

Then it encodes by the output's extension (.mp3, .ogg, .opus, .flac, .wav)
and measures the result again, because the encoder is the last thing to touch
it. The report names what a listener would catch: a jump in intensity where
the loop comes round, the crossfade's own swell (the overlap against the
louder of the two passages in it), silence inside the loop, and its loudness
range, which is how much the level moves while it plays. `start_s` and
`end_s` say which part of the source became the loop.

Needs ffmpeg on the PATH and numpy.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import numpy as np
except ImportError:
    sys.exit("needs numpy: pip install --user numpy")

SR = 44100
HOP = 512
N_FFT = 2048

# How a start and end pair is scored, in dB or the equivalent. A 1 dB jump at
# the restart costs 1; a boundary passage more than DIP_TOL under the typical
# level costs its shortfall; a rhythm match of 0.5 instead of 1 costs 2; and
# every 10 s of loop given up costs 0.2.
DIP_TOL = 1.0
RHYTHM_WEIGHT = 4.0
LENGTH_WEIGHT = 0.02


def decode(path: Path) -> np.ndarray:
    """The whole file as float32 stereo at SR, shape (samples, 2)."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2",
         "-ar", str(SR), "-"], capture_output=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg could not read {path}:\n{r.stderr.decode()[-800:]}")
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, 2).copy()


def window_db(x: np.ndarray, win: int) -> np.ndarray:
    """RMS level in dBFS of consecutive windows of `win` samples."""
    n = max(1, len(x) // win)
    seg = x[: n * win].reshape(n, win, 2).astype(np.float64)
    return 20 * np.log10(np.sqrt((seg ** 2).mean(axis=(1, 2))) + 1e-12)


def level_db(x: np.ndarray) -> float:
    return float(window_db(x, len(x))[0])


def trim(x: np.ndarray, head_db: float, tail_db: float):
    """Drop leading silence and the ending. Returns (audio, cut_front_s,
    cut_back_s, typical_db): typical is the median one-second level of the
    middle 80%."""
    win = int(0.02 * SR)
    loud = np.nonzero(window_db(x, win) > head_db)[0]
    if loud.size == 0:
        sys.exit("the track is silent at --head-db")
    start = int(loud[0]) * win
    body = x[start:]
    db = window_db(body, SR)
    lo, hi = int(len(db) * 0.1), max(int(len(db) * 0.9), int(len(db) * 0.1) + 1)
    typical = float(np.median(db[lo:hi]))
    keep = np.nonzero(db >= typical + tail_db)[0]
    end = (int(keep[-1]) + 1) * SR if keep.size else len(body)
    end = min(end, len(body))
    return body[:end], start / SR, (len(body) - end) / SR, typical


def onset_envelope(mono: np.ndarray) -> np.ndarray:
    """Spectral flux per hop, normalised: where the notes and hits land."""
    frames = 1 + max(0, (len(mono) - N_FFT) // HOP)
    win = np.hanning(N_FFT).astype(np.float32)
    env = np.zeros(frames, dtype=np.float32)
    prev = None
    for c0 in range(0, frames, 1024):
        c1 = min(frames, c0 + 1024)
        seg = np.stack([mono[s:s + N_FFT] for s in range(c0 * HOP, c1 * HOP, HOP)])
        mag = np.log1p(10 * np.abs(np.fft.rfft(seg * win, axis=1))).astype(np.float32)
        first = prev if prev is not None else mag[0]
        diff = np.diff(np.vstack([first[None, :], mag]), axis=0)
        env[c0:c1] = np.maximum(diff, 0).sum(axis=1)
        prev = mag[-1]
    return (env - env.mean()) / (env.std() + 1e-9)


def find_loop(env: np.ndarray, power: np.ndarray, m: int, start_limit: int,
              end_limit: int, step: int, min_frames: int, typical_db: float) -> dict:
    """The start and end frames scoring best (see the module docstring).

    `env` is the onset envelope, `power` the mean square per hop frame, `m`
    the crossfade in frames. The loop is frames [start + m, end), with
    [start, start + m) crossfaded over its last m."""
    n = len(env)
    e64 = env.astype(np.float64)
    c1 = np.concatenate([[0.0], np.cumsum(e64)])
    c2 = np.concatenate([[0.0], np.cumsum(e64 ** 2)])
    cp = np.concatenate([[0.0], np.cumsum(power[:n].astype(np.float64))])

    def level(a, b):
        return 10 * np.log10((cp[b] - cp[a]) / np.maximum(b - a, 1) + 1e-12)

    e_lo = max(3 * m, n - end_limit)
    ends = np.arange(e_lo, n + 1)
    if ends.size == 0:
        sys.exit("the track is too short for this crossfade")
    # The tails' norms after removing their means, for a normalised
    # correlation; the head has its mean removed, so the tails' means drop
    # out of the dot product on their own.
    t_sum = c1[ends] - c1[ends - m]
    t_norm = np.sqrt(np.maximum(c2[ends] - c2[ends - m] - t_sum ** 2 / m, 0.0))
    before = level(ends - 2 * m, ends - m)
    # The end's crossfaded passage: heard fading out, so a quiet one is a
    # hole at the join however well the passages around it agree.
    fading = np.maximum(0.0, typical_db - level(ends - m, ends) - DIP_TOL)
    seg = e64[e_lo - m:n]
    best = None
    for s in range(0, max(0, start_limit) + 1, max(1, step)):
        if s + 2 * m > n:
            break
        head = e64[s:s + m] - e64[s:s + m].mean()
        norm = float(np.linalg.norm(head))
        if norm < 1e-9:
            continue
        match = np.correlate(seg, head / norm, mode="valid") / (t_norm + 1e-9)
        after = float(level(s + m, s + 2 * m))
        jump = after - before
        dip = (max(0.0, typical_db - after - DIP_TOL)
               + max(0.0, typical_db - float(level(s, s + m)) - DIP_TOL)
               + np.maximum(0.0, typical_db - before - DIP_TOL) + fading)
        length = ends - m - s
        cost = (np.abs(jump) + dip + RHYTHM_WEIGHT * (1 - match)
                + LENGTH_WEIGHT * (n - length) * HOP / SR)
        cost = np.where(length >= min_frames, cost, np.inf)
        i = int(np.argmin(cost))
        if np.isfinite(cost[i]) and (best is None or cost[i] < best["cost"]):
            # Plain floats: a numpy float would reach the JSON report intact.
            best = {"cost": float(cost[i]), "start": s, "end": int(ends[i]),
                    "match": float(match[i]), "jump": float(jump[i])}
    if best is None:
        sys.exit("the track is too short for this crossfade and --min-loop")
    return best


def join(x: np.ndarray, start: int, end: int, xfade: int):
    """Crossfade x[end-xfade:end] over x[start:start+xfade] and cut, so the
    result's end runs into its own start: it ends on x[start+xfade-1] and
    begins at x[start+xfade].

    Returns (loop, correlation, swell_db, dip_db): the passages' correlation,
    how far the overlap rose above the louder of the two passages in it, and
    how far it fell below the quieter of the bars either side of it."""
    tail = x[end - xfade:end].astype(np.float64)
    head = x[start:start + xfade].astype(np.float64)
    rho = float((tail * head).sum() /
                (np.sqrt((tail ** 2).sum() * (head ** 2).sum()) + 1e-12))
    rho = min(max(rho, 0.0), 1.0)
    t = (np.arange(xfade, dtype=np.float64) / xfade)[:, None]
    c, s = np.cos(t * np.pi / 2), np.sin(t * np.pi / 2)
    mix = (tail * c + head * s) / np.sqrt(c * c + s * s + 2 * rho * c * s)
    swell = level_db(mix) - max(level_db(tail), level_db(head))
    around = min(level_db(x[end - 2 * xfade:end - xfade]),
                 level_db(x[start + xfade:start + 2 * xfade]))
    loop = np.concatenate([x[start + xfade:end - xfade], mix.astype(np.float32)])
    return loop, rho, swell, level_db(mix) - around


def run_ffmpeg_filter(x: np.ndarray, filt: str) -> np.ndarray:
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
         "-af", filt, "-f", "f32le", "-ar", str(SR), "-ac", "2", "-"],
        input=x.astype(np.float32).tobytes(), capture_output=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg filter {filt!r} failed:\n{r.stderr.decode()[-800:]}")
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, 2)


def limit_seamless(loop: np.ndarray, ceiling_db: float) -> np.ndarray:
    """Limit peaks as the loop is heard: over three copies, keeping the middle,
    so the limiter's state at the end matches its state at the start."""
    n = len(loop)
    limit = 10 ** (ceiling_db / 20)
    y = run_ffmpeg_filter(
        np.concatenate([loop, loop, loop]),
        f"alimiter=limit={limit:.5f}:attack=5:release=80:level=disabled:latency=true")
    if len(y) != 3 * n:
        sys.exit(f"the limiter changed the length ({len(y)} vs {3 * n}); rerun with --no-limit")
    return y[n:2 * n].copy()


def measure(path: Path) -> dict:
    """Integrated loudness, loudness range and true peak, via ebur128."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
         "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
        capture_output=True, text=True)
    text = r.stderr[r.stderr.rfind("Summary:"):]

    def grab(pattern):
        m = re.search(pattern, text)
        return float(m.group(1)) if m else None

    return {"lufs": grab(r"I:\s+(-?[\d.]+) LUFS"), "lra": grab(r"LRA:\s+(-?[\d.]+) LU"),
            "true_peak": grab(r"Peak:\s+(-?[\d.inf]+) dBFS")}


def write(x: np.ndarray, dst: Path, bitrate: str) -> None:
    codec = {
        ".mp3": ["-c:a", "libmp3lame", "-b:a", bitrate],
        ".ogg": ["-c:a", "libvorbis", "-b:a", bitrate],
        ".opus": ["-c:a", "libopus", "-b:a", bitrate],
        ".flac": ["-c:a", "flac"],
        # Float, so a probe of audio above full scale measures what is
        # there instead of what a 16-bit file would have clipped it to.
        ".wav": ["-c:a", "pcm_f32le"],
    }.get(dst.suffix.lower())
    if codec is None:
        sys.exit(f"unsupported output type {dst.suffix}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2",
         "-i", "-", *codec, str(dst)], input=x.astype(np.float32).tobytes(),
        capture_output=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg could not write {dst}:\n{r.stderr.decode()[-800:]}")


def probe(x: np.ndarray) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "probe.wav"
        write(x, p, "")
        return measure(p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--bpm", type=float,
                    help="the tempo asked for; sizes the crossfade in bars and "
                         "steps the start search a beat at a time")
    ap.add_argument("--beats-per-bar", type=int, default=4)
    ap.add_argument("--xfade-bars", type=float, default=2.0)
    ap.add_argument("--xfade", type=float, default=3.0,
                    help="crossfade in seconds when --bpm is not given (default 3)")
    ap.add_argument("--search", type=float, default=0.3,
                    help="how much of the track, from each end, to search for "
                         "the loop's start and end (default 0.3)")
    ap.add_argument("--min-loop", type=float, default=30.0,
                    help="shortest loop to accept, in seconds (default 30)")
    ap.add_argument("--lufs", type=float, default=-14.0,
                    help="target integrated loudness (default -14)")
    ap.add_argument("--true-peak", type=float, default=-1.0,
                    help="ceiling for the true peak in dBTP (default -1)")
    ap.add_argument("--limit", action=argparse.BooleanOptionalAction, default=True,
                    help="limit peaks to reach --lufs (default); --no-limit holds the gain back instead")
    ap.add_argument("--bitrate", default="96k")
    ap.add_argument("--head-db", type=float, default=-45.0,
                    help="leading audio quieter than this is silence (dBFS)")
    ap.add_argument("--tail-db", type=float, default=-6.0,
                    help="the ending starts where the level stays this far below typical")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    a = ap.parse_args()

    src, dst = Path(a.src), Path(a.dst)
    x = decode(src)
    source_s = len(x) / SR
    x, cut_front, _, typical_db = trim(x, a.head_db, a.tail_db)

    if a.bpm:
        beat_s = 60.0 / a.bpm
        xfade_s = a.xfade_bars * a.beats_per_bar * beat_s
    else:
        beat_s, xfade_s = 0.5, a.xfade
    m = max(1, round(xfade_s * SR / HOP))
    env = onset_envelope(x.mean(axis=1))
    n = len(env)
    power = (x[: n * HOP].astype(np.float64) ** 2).mean(axis=1).reshape(n, HOP).mean(axis=1)
    reach = round(n * min(max(a.search, 0.0), 0.5))
    pick = find_loop(env, power, m, start_limit=reach, end_limit=reach,
                     step=max(1, round(beat_s * SR / HOP)),
                     min_frames=round(a.min_loop * SR / HOP), typical_db=typical_db)
    xfade = m * HOP
    start, end = pick["start"] * HOP, min(pick["end"] * HOP, len(x))
    loop, rho, swell_db, dip_db = join(x, start, end, xfade)

    before = probe(loop)
    if before["lufs"] is None:
        sys.exit("could not measure the loudness of the loop")
    # Not `or`: a take normalised to full scale measures a true peak of
    # exactly 0.0, which `or` reads as no measurement at all. That skipped
    # the limiter and made loops that peaked at up to +4.2 dBTP.
    peak = before["true_peak"] if before["true_peak"] is not None else -99.0
    joined = loop
    gain = a.lufs - before["lufs"]
    for _ in range(3):
        held = limited = 0.0
        over = peak + gain - a.true_peak
        if over > 0 and not a.limit:
            held = over
        loop = joined * np.float32(10 ** ((gain - held) / 20))
        if over > 0 and a.limit:
            # Half a dB of room: the limiter holds sample peaks, and encoding
            # lifts the true peak a little past them.
            loop = limit_seamless(loop, a.true_peak - 0.5)
            limited = over
        write(loop, dst, a.bitrate)
        after = measure(dst)
        # Limiting takes loudness off, and so does the encoder, so measure
        # what was written and make the difference up.
        if held > 0 or after["lufs"] is None or abs(a.lufs - after["lufs"]) < 0.2:
            break
        gain += a.lufs - after["lufs"]
    gain -= held

    # Where the loop comes round: the bars after the restart against the
    # bars before the crossfade.
    jump_db = level_db(loop[:xfade]) - level_db(loop[-2 * xfade:-xfade])
    half = window_db(loop, SR // 2)
    silent = run = 0
    for lvl in half:
        run = run + 1 if lvl < -50 else 0
        silent = max(silent, run)

    report = {
        "src": str(src), "dst": str(dst), "source_s": round(source_s, 2),
        "start_s": round(cut_front + start / SR, 2), "end_s": round(cut_front + end / SR, 2),
        "loop_s": round(len(loop) / SR, 2), "crossfade_s": round(xfade / SR, 2),
        "rhythm_match": round(pick["match"], 3),
        "crossfade_correlation": round(rho, 3), "crossfade_swell_db": round(swell_db, 2),
        "crossfade_dip_db": round(dip_db, 2),
        "restart_jump_db": round(jump_db, 2), "longest_silence_s": silent / 2,
        "gain_db": round(gain, 2), "peaks_limited_db": round(limited, 2),
        "held_under_target_db": round(held, 2),
        "lufs": after["lufs"], "lra": after["lra"], "true_peak": after["true_peak"],
    }
    if a.json:
        print(json.dumps(report))
    else:
        print(f"{dst}: {report['loop_s']}s loop from {report['start_s']}s to "
              f"{report['end_s']}s of {report['source_s']}s, "
              f"{report['crossfade_s']}s crossfade, rhythm match {pick['match']:.2f}, "
              f"crossfade swell {swell_db:+.1f} dB, "
              + (f"crossfade dips {dip_db:+.1f} dB under the bars around it, " if dip_db < -0.5 else "")
              + f"restart jump {jump_db:+.1f} dB, "
              f"{after['lufs']} LUFS, loudness range {after['lra']} LU, "
              f"true peak {after['true_peak']} dBTP"
              + (f", peaks limited by {limited:.1f} dB" if limited > 0.05 else "")
              + (f", held {held:.1f} dB under target" if held > 0.05 else "")
              + (f"  WARNING: {silent / 2:.1f}s of silence inside" if silent >= 3 else "")
              + (f"  WARNING: true peak {after['true_peak']} dBTP, over full scale"
                 if after["true_peak"] is not None and after["true_peak"] > 0 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
