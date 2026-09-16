#!/usr/bin/env python3
"""Mouth cues for voice lines: Rhubarb Lip Sync, a speech gate, and frames.

    scripts/fetch_tools.py --download rhubarb               # once
    scripts/lipsync_cues.py lines/smith_01.ogg              # reads lines/smith_01.txt
    scripts/lipsync_cues.py lines/smith_01.ogg --text "No."
    scripts/lipsync_cues.py lines/smith_01.ogg --text-file script/smith_01.txt
    scripts/lipsync_cues.py lines/ --out output/lipsync/smith   # a whole folder
    scripts/lipsync_cues.py lines/smith_01.ogg --fps 12 --rule closure
    scripts/lipsync_cues.py lines/other_language.ogg -r phonetic
    scripts/lipsync_cues.py --text-only lines/smith_01.txt --fps 12
    scripts/lipsync_cues.py --selftest

Runs on the host, not in the container. Rhubarb runs from tools/, where
scripts/fetch_tools.py unpacks it, so the published image never redistributes
the binary or its bundled components. Needs ffmpeg on the PATH.

For each line it:

1. **Converts** the audio with ffmpeg to 16 kHz mono 16-bit PCM WAV in a
   temporary folder, with the transcript beside it. Any format ffmpeg reads
   will do.
2. **Runs Rhubarb** in that folder, one thread, trace log on:

       rhubarb -f json -d LINE.txt --threads 1 --logFile LINE.log \\
               --logLevel Trace LINE.wav

   One thread because with more, the same command gives different cue files.
   The transcript is a hint: PocketSphinx still recognises the words, but
   prefers the transcript's. It comes from --text, --text-file, or LINE.txt
   next to the audio, in that order, and must be UTF-8: Rhubarb stops with
   exit code 1 on any other encoding. With none, or with --no-text, the line
   runs without -d.

   `-r phonetic` is Rhubarb's language-independent recogniser. It ignores
   the transcript, so this script reads none (not --text, --text-file or
   LINE.txt), passes no -d and writes "text": null. The word check below
   cannot run, so only the flat-mouth check guards a phonetic line.
3. **Gates** the result, because Rhubarb's voice detector takes noise for
   speech and returns a mouth that talks all the way through it. Two checks,
   both read from the trace log:
   - **Words.** The `##word[start-end]: word` lines are what PocketSphinx
     heard. Fillers (<s>, <sil>, [BREATH] and the like) and alternate
     pronunciation markers such as `(2)` are dropped, both sides are
     lower-cased and split into words, and the word error rate is the word
     edit distance over the transcript's word count. The line is refused
     when that is above {wer_max:.0%}. Skipped without a transcript and with
     -r phonetic.
   - **A flat mouth.** The non-X cues lasting {flat_min_s:.1f} s or more are added up,
     and the line is refused when together they cover more than {flat_share:.0%} of
     the voiced time (the voice detector's "Found N sections of voice
     activity" line). A non-X cue that long, below that share, only prints
     a warning. The cues are added up, not just the longest taken, because
     -r phonetic cuts noise into alternating B and C cues: on white noise its
     longest single cue covered as little as 35% of the voiced time.

   The thresholds come from runs on 2026-09-16, Rhubarb 1.14.0 on one thread,
   with research/experiments/rhubarb/reproduce.py (its README has the tables)
   and with this script (--force) on clips cut from that audio.
   Words: a right transcript scored 0% on LibriSpeech test-clean
   6930-75918-0000, 0001 and 0002 and on three one-word clips cut from them;
   0001's with one word changed scored 7.0%. Against the true words the
   recogniser reached 37.5% with no transcript and 50.0% when given another
   line's. Another line's transcript scored 90.9% to 500%, and 15 s excerpts
   of two generated music tracks given 0001's transcript 83.7% and 93.0%.
   Hence above 60%.
   Flat mouth: on the three lines, with either recogniser, with or without
   the transcript, the longest non-X cue was 0.70 s. On 0001 under steady
   pink noise it was 0.85 s, and on 0000 with the vowel of "place" stretched
   8 and 16 times, 0.98 s. The lines slowed to half speed reached 1.37 s,
   and their cues of 1.0 s or more covered at most 13.5% of voiced time. Ten
   seconds of white noise (five seeds), pink, brown and velvet noise and a
   440 Hz sine peaking at -6 dBFS covered 76.8% to 99.5% with either
   recogniser. Hence 1.0 s, and more than 50%: "most of the voiced time".

   **What gets through.** A short noise tail: 0000 followed by 2 s of white
   noise covered 38% to 39% and passed with a warning; with 4 s it covered
   51% to 55% and with 10 s 76% to 79%, and was refused, with either
   recogniser. Music with no transcript: of two 15 s generated excerpts, the
   forest ambience made no non-X cue of 1.0 s and passed without a warning;
   the battle music covered 51% and was refused, but with -r phonetic 19%,
   which passed with a warning. Keep music, ambience and effects away from
   this script, or give every line its transcript.
   **What gets refused that is speech.** 0000 slowed to half speed scored
   87.5% against its own transcript (0001 slowed, 30.2%), so very slow or
   drawn-out delivery can fail the word check.
4. **Writes the timeline**, Rhubarb's JSON with fields around it, to
   output/lipsync/LINE.json unless --out says otherwise, and its log to
   LINE.log beside it. `metadata.soundFile` and `audio` are rewritten
   relative to the timeline, `cues` records the Rhubarb version and flags,
   `command` the exact argument list (binary relative to the repository) and
   `converted` the ffmpeg step, quoted for a shell. A refused line writes no
   timeline unless --force is given, which writes it with "passed": false in
   `gate`.

**Frames**, only for a baked, frame-based animation: `--fps N` adds `fps`,
`rule`, `frames` (one shape per frame, round(duration x N) of them) and
`dropped`, the cues no frame shows. Frame i covers [i/N, (i+1)/N).
- `midpoint` (default): the cue playing at the frame's midpoint; a cue that
  starts exactly there wins.
- `closure`: as midpoint, except that a frame any A cue overlaps shows A,
  because a lost P, B or M closure is the likeliest drop to show.
- `share`: the cue with the largest overlap of [t, t + max(1/N, 0.08 s)],
  t the frame's start, adapted from Valve's 0.08 s phoneme box filter; an
  exact tie goes to the later cue, as in midpoint.
Up to 12.5 fps the share window is the frame itself. There, if no cue in a
frame is shorter than half the frame, the cue at the midpoint has the largest
overlap, so share gives the same frames as midpoint. On 0001 on one thread
(shortest cue 0.06 s, or 0.05 s with -r phonetic) share matched midpoint in
every frame from 8 to 12.5 fps, except 2 phonetic frames at 9 fps. It
differed in 3 frames at 6 fps (10 phonetic) and in 8 or more at 15 fps and
above, where the window looks past the frame. None of the three has been
judged on a portrait.

**--text-only** writes the same timeline shape with no audio, for lines that
have no voice yet: {flap_shapes} repeating every {flap_interval:.2f} s for as long as the
text would take at {flap_cps:.1f} characters per second (whitespace collapsed),
rounded up to a whole step, then one step of X. The input is a
.txt file, a folder of them, or an audio path whose .txt is read; --text
with --out also works. It writes to output/lipsync/text-only/ unless --out
says otherwise, and never overwrites a timeline made from audio. The interval
is the median cue length Rhubarb gave on the three LibriSpeech lines with
their transcripts on one thread (0.14 s over 142 cues) and the speed is those
lines' 354 characters over 22.74 s (15.57 per second), both from reproduce.py
on 2026-09-16. The flap has not been judged on a portrait.

**--selftest** checks the frame rules on hand-worked cue lists, then makes
three 10 s, 16 kHz mono files with ffmpeg (digital silence, a 440 Hz sine
peaking at -18 dBFS, white noise at amplitude 0.3 with seed 1) and expects
X only, X only, and a gate rejection, and a rejection again for the noise
with -r phonetic. Nothing is written outside a temporary folder.

Exit codes:
  0  every line written and passed the gate; --selftest passed
  1  a tool or input problem: Rhubarb not installed, ffmpeg missing or
     failing, Rhubarb failing or timing out, an unreadable transcript, or
     --text-only about to overwrite a timeline made from audio
  2  bad arguments
  3  the speech gate refused at least one line (nothing written for it,
     unless --force)
  4  --selftest ran and an expectation failed
A folder run carries on past a failed line and exits 1 if any line failed,
else 3 if any was refused.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_tools  # noqa: E402  (a sibling script, standard library only)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "output" / "lipsync"
TEXT_ONLY_OUT = DEFAULT_OUT / "text-only"
MAX_FPS = 1000
AUDIO_EXTS = {".wav", ".ogg", ".oga", ".opus", ".mp3", ".flac", ".m4a", ".aac",
              ".aif", ".aiff", ".wma"}

# ------------------------------------------------------------------ thresholds
# Measured as the module docstring says; change them only with a new measurement.
WER_MAX = 0.60
FLAT_SHARE = 0.50     # refused above this share of voiced time
FLAT_MIN_S = 1.0      # counting non-X cues at least this long
SPEECH_LONGEST_S = 0.70   # the longest non-X cue measured on speech at normal speed

# The text-driven flap.
FLAP_SHAPES = ("C", "B", "D", "B")
FLAP_INTERVAL = 0.14
FLAP_CPS = 15.6

SHARE_WINDOW_S = 0.08   # Valve's default phonemefilter

__doc__ = __doc__.format(
    wer_max=WER_MAX, flat_share=FLAT_SHARE, flat_min_s=FLAT_MIN_S,
    flap_shapes=" ".join(FLAP_SHAPES), flap_interval=FLAP_INTERVAL, flap_cps=FLAP_CPS)


class LineError(Exception):
    """A tool or input problem with one line: exit code 1."""


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


# ------------------------------------------------------------------ transcript

_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)*")


def words_of(text: str) -> list[str]:
    """Lower-case words, apostrophes kept inside a word, punctuation dropped."""
    text = text.lower().replace("’", "'").replace("‘", "'")
    return _WORD.findall(text)


def read_transcript(path: Path) -> str:
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LineError(f"{rel(path)} is not UTF-8 ({exc}); Rhubarb would stop "
                        "with exit code 1")
    except OSError as exc:
        raise LineError(f"cannot read transcript {rel(path)}: {exc}")
    if not text.strip():
        raise LineError(f"transcript {rel(path)} is empty")
    return text


# ------------------------------------------------------------------ the log

_WORD_LINE = re.compile(r"##word\[([\d.]+)-([\d.]+)\]: (\S+)")
_VOICE_LINE = re.compile(r"Found (\d+) sections of voice activity: ?(.*)$")
_SECTION = re.compile(r"(\d+)cs-(\d+)cs")


def parse_log(log: str) -> tuple[list[str], float | None]:
    """(words heard in time order, voiced seconds) from a Trace log."""
    heard = []
    voiced = None
    for line in log.splitlines():
        m = _WORD_LINE.search(line)
        if m:
            word = re.sub(r"\(\d+\)$", "", m.group(3))
            if word and word[0] not in "<[":
                heard.append((float(m.group(1)), word.lower()))
            continue
        m = _VOICE_LINE.search(line)
        if m:
            voiced = sum(int(b) - int(a) for a, b in _SECTION.findall(m.group(2))) / 100.0
    # Utterances are logged by whichever thread finishes first, so sort.
    heard.sort(key=lambda x: x[0])
    return [w for _, w in heard], voiced


def edit_distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def gate(cues: list[dict], log: str, text: str | None, recognizer: str) -> dict:
    heard, voiced = parse_log(log)
    g: dict = {"passed": True, "reasons": [], "warnings": []}
    if recognizer == "phonetic":
        g["words"] = "skipped: the phonetic recogniser reports no words"
    elif text is None:
        g["words"] = "skipped: no transcript"
    else:
        ref = words_of(text)
        dist = edit_distance(ref, heard)
        wer = dist / len(ref) if ref else 1.0
        g.update({"words_expected": len(ref), "words_heard": len(heard),
                  "word_edits": dist, "wer": round(wer, 4), "wer_max": WER_MAX})
        if wer > WER_MAX:
            g["passed"] = False
            g["reasons"].append(f"word error rate {wer:.1%} against the transcript "
                                f"is above {WER_MAX:.0%}")
    g["voiced_s"] = voiced
    talk = [c for c in cues if c["value"] != "X"]

    def length(c: dict) -> float:
        return round(c["end"] - c["start"], 2)

    if talk and voiced:
        longest = max(talk, key=length)
        long = [c for c in talk if length(c) >= FLAT_MIN_S]
        long_s = round(sum(length(c) for c in long), 2)
        share = long_s / voiced
        g.update({"longest_cue": longest, "long_cues": len(long), "long_s": long_s,
                  "long_share": round(share, 4), "long_share_max": FLAT_SHARE,
                  "flat_min_s": FLAT_MIN_S})
        if share > FLAT_SHARE:
            g["passed"] = False
            g["reasons"].append(
                f"{len(long)} non-X cue{'s' if len(long) > 1 else ''} of {FLAT_MIN_S:.1f} s or "
                f"more ({long_s:.2f} s, the longest a {longest['value']} of "
                f"{length(longest):.2f} s) {'cover' if len(long) > 1 else 'covers'} {share:.0%} of "
                f"{voiced:.2f} s voiced, "
                f"more than {FLAT_SHARE:.0%}")
        elif long:
            g["warnings"].append(
                f"a {longest['value']} cue lasts {length(longest):.2f} s, longer than any "
                f"measured on speech at normal speed ({SPEECH_LONGEST_S:.2f} s): music, "
                f"noise, or a noisy tail?")
    elif talk:
        g["warnings"].append("the log reports no voice activity, so the flat-mouth "
                             "check did not run")
    return g


# ------------------------------------------------------------------ frames

def _overlap(c: dict, t0: float, t1: float) -> float:
    return max(0.0, min(c["end"], t1) - max(c["start"], t0))


def _at(cues: list[dict], t: float) -> int:
    for k, c in enumerate(cues):
        if c["start"] <= t < c["end"]:
            return k
    return len(cues) - 1 if cues and t >= cues[-1]["end"] else -1


def to_frames(cues: list[dict], duration: float, fps: float, rule: str):
    """(frames, index of the cue each frame shows, dropped cue indices)."""
    n = max(1, round(duration * fps))
    src = []
    for i in range(n):
        t0, t1 = i / fps, (i + 1) / fps
        # (2i+1)/(2 fps), not (t0+t1)/2: at 10 fps it lands exactly on a cue
        # boundary such as 2.65, so midpoint and share break the tie alike.
        mid = (2 * i + 1) / (2 * fps)
        if rule == "midpoint":
            k = _at(cues, mid)
        elif rule == "closure":
            hits = [(round(_overlap(c, t0, t1), 6), -j) for j, c in enumerate(cues)
                    if c["value"] == "A" and _overlap(c, t0, t1) > 1e-9]
            k = -max(hits)[1] if hits else _at(cues, mid)
        elif rule == "share":
            w = max(1.0 / fps, SHARE_WINDOW_S)
            # An exact tie goes to the later cue, as midpoint's does.
            best = max(((round(_overlap(c, t0, t0 + w), 6), j)
                        for j, c in enumerate(cues)), default=(0.0, -1))
            k = best[1] if best[0] > 0 else _at(cues, t0)
        else:
            raise ValueError(rule)
        src.append(k)
    frames = [cues[k]["value"] if k >= 0 else "X" for k in src]
    shown = set(src)
    dropped = [j for j in range(len(cues)) if j not in shown]
    return frames, src, dropped


def add_frames(tl: dict, fps: float, rule: str) -> str:
    cues = tl["mouthCues"]
    frames, _, dropped = to_frames(cues, tl["duration"], fps, rule)
    tl["fps"] = int(fps) if float(fps).is_integer() else fps
    tl["rule"] = rule
    tl["frames"] = frames
    a_total = sum(1 for c in cues if c["value"] == "A")
    a_lost = sum(1 for j in dropped if cues[j]["value"] == "A")
    tl["dropped"] = {"cues": len(dropped), "of": len(cues), "A": a_lost, "A_of": a_total}
    return (f"{len(frames)} frames at {tl['fps']} fps, rule {rule}: dropped "
            f"{len(dropped)} of {len(cues)} cues, {a_lost} of {a_total} A")


# ------------------------------------------------------------------ writing

def dump_timeline(tl: dict) -> str:
    """JSON with one cue per line and the frame list on one line."""
    def one(v):
        return json.dumps(v, ensure_ascii=False)
    lines = ["{"]
    keys = list(tl)
    for i, k in enumerate(keys):
        v = tl[k]
        comma = "," if i < len(keys) - 1 else ""
        if k == "mouthCues":
            lines.append(f'  "{k}": [')
            for j, c in enumerate(v):
                lines.append(f"    {one(c)}" + ("," if j < len(v) - 1 else ""))
            lines.append(f"  ]{comma}")
        elif k in ("metadata", "gate") and isinstance(v, dict):
            inner = json.dumps(v, ensure_ascii=False, indent=2).replace("\n", "\n  ")
            lines.append(f'  "{k}": {inner}{comma}')
        else:
            lines.append(f'  "{k}": {one(v)}{comma}')
    lines.append("}")
    return "\n".join(lines) + "\n"


def write(path: Path, tl: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(dump_timeline(tl), encoding="utf-8")
    tmp.replace(path)


# ------------------------------------------------------------------ tools

_version_cache: dict[str, str] = {}


def rhubarb_binary() -> Path:
    p = fetch_tools.tool_path("rhubarb")
    if p is None:
        raise LineError("Rhubarb is not installed; run: scripts/fetch_tools.py --download rhubarb")
    return p


def rhubarb_version(binary: Path) -> str:
    key = str(binary)
    if key not in _version_cache:
        r = subprocess.run([str(binary), "--version"], capture_output=True, text=True,
                           timeout=60)
        m = re.search(r"version (\S+)", r.stdout + r.stderr)
        _version_cache[key] = m.group(1) if m else "unknown"
    return _version_cache[key]


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise LineError("ffmpeg is not on the PATH")
    return exe


def safe_name(stem: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", stem) or "line"


def failure_detail(log: str, stderr: str, max_lines: int = 12) -> str:
    """Whole lines explaining a Rhubarb failure: the log from its first Fatal
    or Error line, else the end of stderr without the progress bars."""
    lines = log.splitlines()
    for i, line in enumerate(lines):
        if "[Fatal]" in line or "[Error]" in line:
            return "\n".join(lines[i:i + max_lines])
    err = [l for l in re.split(r"[\r\n]+", stderr)
           if l.strip() and not l.lstrip().startswith("Progress")]
    return "\n".join(err[-max_lines:]) or "(no log and no error output)"


# ------------------------------------------------------------------ one line

def run_line(audio: Path, text: str | None, out: Path, recognizer: str,
             timeout: float, fps: float | None, rule: str, force: bool) -> tuple[str, dict | None]:
    """Make one timeline. Returns ('ok' | 'refused' | 'forced', timeline)."""
    audio = audio.resolve()
    binary = rhubarb_binary()
    version = rhubarb_version(binary)
    manifest = fetch_tools.find("rhubarb")
    if manifest and version != manifest["version"]:
        print(f"  ! rhubarb reports version {version}, tools.json pins {manifest['version']}")
    name = safe_name(audio.stem)
    t_start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="lipsync_") as tmp:
        tmpd = Path(tmp)
        wav = tmpd / f"{name}.wav"
        conv = [ffmpeg(), "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(audio), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                wav.name]
        try:
            r = subprocess.run(conv, cwd=tmpd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise LineError(f"ffmpeg timed out after {timeout:.0f}s on {rel(audio)}")
        if r.returncode != 0 or not wav.is_file():
            raise LineError(f"ffmpeg could not convert {rel(audio)}: {r.stderr.strip()[-800:]}")

        args = ["-f", "json"]
        if text is not None and recognizer != "phonetic":
            (tmpd / f"{name}.txt").write_text(text, encoding="utf-8")
            args += ["-d", f"{name}.txt"]
        if recognizer == "phonetic":
            args += ["-r", "phonetic"]
        args += ["--threads", "1", "--logFile", f"{name}.log", "--logLevel", "Trace", wav.name]
        try:
            r = subprocess.run([str(binary)] + args, cwd=tmpd, capture_output=True,
                               text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise LineError(f"rhubarb timed out after {timeout:.0f}s on {rel(audio)}; "
                            "raise --timeout for a long line")
        log_path = tmpd / f"{name}.log"
        log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
        out.parent.mkdir(parents=True, exist_ok=True)
        if log:
            shutil.copyfile(log_path, out.with_suffix(".log"))
        if r.returncode != 0:
            raise LineError(f"rhubarb exited {r.returncode} on {rel(audio)}:\n"
                            f"{failure_detail(log, r.stderr)}")
        try:
            data = json.loads(r.stdout)
        except ValueError as exc:
            raise LineError(f"rhubarb wrote no JSON for {rel(audio)}: {exc}")
    seconds = time.perf_counter() - t_start

    cues = data["mouthCues"]
    duration = data["metadata"]["duration"]
    g = gate(cues, log, text, recognizer)
    sound = os.path.relpath(audio, out.resolve().parent)
    data["metadata"]["soundFile"] = sound
    tl = {
        "line": audio.stem,
        "text": text.strip() if text is not None else None,
        "audio": sound,
        "cues": f"rhubarb {version}: " + " ".join(a if a else '""' for a in args),
        "command": [rel(binary)] + args,
        "converted": shlex.join(["ffmpeg"] + conv[1:conv.index("-i") + 1] + [audio.name]
                                + conv[conv.index("-i") + 2:]),
        "duration": duration,
        "metadata": data["metadata"],
        "mouthCues": cues,
    }
    frame_note = add_frames(tl, fps, rule) if fps else None
    tl["gate"] = g

    shapes = "".join(sorted({c["value"] for c in cues}))
    wer = f"WER {g['wer']:.1%}" if "wer" in g else "word check skipped"
    if "long_share" in g:
        share = (f"longest non-X {g['longest_cue']['end'] - g['longest_cue']['start']:.2f} s, "
                 f"cues of {FLAT_MIN_S:.1f} s or more {g['long_share']:.0%} of voiced")
    else:
        share = "no voiced non-X cue"
    print(f"  {rel(audio)}: {len(cues)} cues ({shapes}) over {duration:.2f} s in {seconds:.2f} s; "
          f"{wer}; {share}")
    if frame_note:
        print(f"    {frame_note}")
    for warning in g["warnings"]:
        print(f"    ! {warning}")
    if not g["passed"]:
        for why in g["reasons"]:
            print(f"    REFUSED: {why}")
        if not force:
            print(f"    nothing written; log at {rel(out.with_suffix('.log'))}")
            return "refused", tl
        write(out, tl)
        print(f"    written anyway (--force): {rel(out)}")
        return "forced", tl
    write(out, tl)
    print(f"    -> {rel(out)}")
    return "ok", tl


# ------------------------------------------------------------------ text-only

def flap(text: str, line: str, fps: float | None, rule: str) -> dict:
    spoken = " ".join(text.split())
    talk = len(spoken) / FLAP_CPS
    steps = max(1, math.ceil(talk / FLAP_INTERVAL - 1e-9))
    cues = []
    for k in range(steps + 1):
        value = FLAP_SHAPES[k % len(FLAP_SHAPES)] if k < steps else "X"
        cues.append({"start": round(k * FLAP_INTERVAL, 2),
                     "end": round((k + 1) * FLAP_INTERVAL, 2), "value": value})
    duration = cues[-1]["end"]
    tl = {
        "line": line,
        "text": text.strip(),
        "audio": None,
        "cues": (f"text-only flap: {' '.join(FLAP_SHAPES)} every {FLAP_INTERVAL:.2f} s "
                 f"at {FLAP_CPS:g} characters per second, then X"),
        "duration": duration,
        "mouthCues": cues,
    }
    if fps:
        print(f"    {add_frames(tl, fps, rule)}")
    return tl


# ------------------------------------------------------------------ self-test

def selftest(timeout: float) -> int:
    failures = []

    def expect(label, ok, detail=""):
        print(f"  {'ok  ' if ok else 'FAIL'} {label}{': ' + detail if detail else ''}")
        if not ok:
            failures.append(label)

    print("frame rules, on hand-worked cue lists")
    note = [{"start": 0.00, "end": 0.06, "value": "X"}, {"start": 0.06, "end": 0.18, "value": "B"},
            {"start": 0.18, "end": 0.36, "value": "F"}, {"start": 0.36, "end": 0.42, "value": "X"}]
    f, _, d = to_frames(note, 0.42, 12, "midpoint")
    expect("midpoint on the lip sync note's example", f == ["X", "B", "F", "F", "X"] and not d,
           " ".join(f))
    short_a = [{"start": 0.00, "end": 0.09, "value": "X"}, {"start": 0.09, "end": 0.12, "value": "A"},
               {"start": 0.12, "end": 0.30, "value": "C"}, {"start": 0.30, "end": 0.42, "value": "X"}]
    for rule, want, drops in (("midpoint", "XCCCX", [1]), ("closure", "XACCX", []),
                              ("share", "XCCCX", [1])):
        f, _, d = to_frames(short_a, 0.42, 12, rule)
        expect(f"{rule} on a 0.03 s A cue", "".join(f) == want and d == drops,
               f"{''.join(f)}, dropped {d}")
    # At 10 fps the midpoints fall on 0.05 and 0.25, where cues change: both
    # rules give the frame to the cue that starts there.
    tie = [{"start": 0.00, "end": 0.05, "value": "X"}, {"start": 0.05, "end": 0.25, "value": "B"},
           {"start": 0.25, "end": 0.30, "value": "X"}]
    for rule in ("midpoint", "share"):
        f, _, d = to_frames(tie, 0.30, 10, rule)
        expect(f"{rule} on exact ties at 10 fps", "".join(f) == "BBX" and d == [0],
               f"{''.join(f)}, dropped {d}")
    # At 24 fps share's 0.08 s window looks past the 0.042 s frame.
    ahead = [{"start": 0.00, "end": 0.03, "value": "X"}, {"start": 0.03, "end": 0.10, "value": "B"},
             {"start": 0.10, "end": 0.20, "value": "X"}]
    for rule, want in (("midpoint", "XBXXX"), ("share", "BBXXX")):
        f, _, _ = to_frames(ahead, 0.20, 24, rule)
        expect(f"{rule} at 24 fps", "".join(f) == want, "".join(f))

    print("\nflat-mouth check, on a hand-worked phonetic-style cue list")
    split = [{"start": 0.00, "end": 3.48, "value": "B"}, {"start": 3.48, "end": 3.76, "value": "C"},
             {"start": 3.76, "end": 6.21, "value": "B"}, {"start": 6.21, "end": 7.12, "value": "C"},
             {"start": 7.12, "end": 8.87, "value": "B"}, {"start": 8.87, "end": 10.00, "value": "X"}]
    g = gate(split, "Found 1 sections of voice activity: 0cs-1000cs", None, "phonetic")
    expect("three long B cues, none over half, are refused together", not g["passed"],
           f"long_share {g.get('long_share')}, longest {g['longest_cue']['end'] - g['longest_cue']['start']:.2f} s")

    try:
        binary = rhubarb_binary()
        exe = ffmpeg()
    except LineError as exc:
        print(f"  FAIL {exc}")
        return 1
    print(f"\naudio fixtures, rhubarb {rhubarb_version(binary)} at {rel(binary)}")
    sources = {
        "silence": "anullsrc=channel_layout=mono:sample_rate=16000",
        "sine440": "sine=frequency=440:sample_rate=16000",
        "whitenoise": "anoisesrc=colour=white:amplitude=0.3:sample_rate=16000:seed=1",
    }
    with tempfile.TemporaryDirectory(prefix="lipsync_selftest_") as tmp:
        tmpd = Path(tmp)
        results = {}
        for name, src in sources.items():
            wav = tmpd / f"{name}_10s.wav"
            r = subprocess.run([exe, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                                "-f", "lavfi", "-i", src, "-t", "10", "-ac", "1",
                                "-c:a", "pcm_s16le", str(wav)],
                               capture_output=True, text=True, timeout=timeout)
            if r.returncode != 0:
                print(f"  FAIL ffmpeg could not make {name}: {r.stderr.strip()}")
                return 1
            if name == "sine440":
                r = subprocess.run([exe, "-nostdin", "-hide_banner", "-i", str(wav),
                                    "-af", "volumedetect", "-f", "null", "-"],
                                   capture_output=True, text=True, timeout=timeout)
                m = re.search(r"max_volume: (-?[\d.]+) dB", r.stderr)
                peak = float(m.group(1)) if m else float("nan")
                expect("sine peak near -18 dBFS", abs(peak + 18) <= 0.5, f"{peak} dB")
            runs = [("pocketSphinx", name)]
            if name == "whitenoise":
                runs.append(("phonetic", "whitenoise_phonetic"))
            for recognizer, label in runs:
                try:
                    status, tl = run_line(wav, None, tmpd / "out" / f"{label}.json", recognizer,
                                          timeout, None, "midpoint", False)
                except LineError as exc:
                    print(f"  FAIL {label}: {exc}")
                    return 1
                results[label] = (status, tl)
        for name in ("silence", "sine440"):
            status, tl = results[name]
            values = sorted({c["value"] for c in tl["mouthCues"]})
            expect(f"{name} gives X only and passes", status == "ok" and values == ["X"],
                   f"{status}, shapes {''.join(values)}")
        for label, what in (("whitenoise", "white noise"),
                            ("whitenoise_phonetic", "white noise with -r phonetic")):
            status, tl = results[label]
            expect(f"{what} is refused by the gate", status == "refused",
                   f"{status}, {len(tl['mouthCues'])} cues, "
                   f"{'; '.join(tl['gate']['reasons']) or 'no reason'}")
    print(f"\n{'self-test passed' if not failures else 'self-test FAILED: ' + ', '.join(failures)}")
    return 0 if not failures else 4


# ------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", type=Path,
                    help="an audio file or a folder of them; with --text-only, a .txt "
                         "file or a folder of them")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--text", help="the line's transcript")
    src.add_argument("--text-file", type=Path, help="a UTF-8 file holding the transcript")
    src.add_argument("--no-text", action="store_true",
                     help="run without a transcript even if a .txt sits beside the audio")
    ap.add_argument("--out", type=Path,
                    help="a .json file for one line, or a folder (default: output/lipsync, "
                         "or output/lipsync/text-only with --text-only)")
    ap.add_argument("-r", "--recognizer", choices=("pocketSphinx", "phonetic"),
                    default="pocketSphinx",
                    help="Rhubarb's recogniser; phonetic is language-independent and "
                         "ignores the transcript")
    ap.add_argument("--fps", type=float, help="add one mouth shape per frame at this rate")
    ap.add_argument("--rule", choices=("midpoint", "closure", "share"), default="midpoint",
                    help="how --fps picks a frame's shape (default: midpoint)")
    ap.add_argument("--text-only", action="store_true",
                    help="write a text-driven flap with no audio")
    ap.add_argument("--force", action="store_true",
                    help="write a refused line's timeline anyway, marked as refused")
    ap.add_argument("--timeout", type=float, default=600,
                    help="seconds allowed for each ffmpeg or Rhubarb run (default: 600)")
    ap.add_argument("--selftest", action="store_true",
                    help="check the frame rules and the gate on generated audio")
    args = ap.parse_args()
    # Warnings go to stderr; keep them in order with the progress lines.
    sys.stdout.reconfigure(line_buffering=True)

    if args.selftest:
        return selftest(args.timeout)
    if args.fps is not None and not (math.isfinite(args.fps) and 0 < args.fps <= MAX_FPS):
        ap.error(f"--fps must be a number above 0 and at most {MAX_FPS}")
    if args.rule != "midpoint" and not args.fps:
        ap.error("--rule only applies with --fps")

    if args.text_only:
        if args.no_text:
            ap.error("--no-text does not apply to --text-only")
        return main_text_only(ap, args)

    if args.input is None:
        ap.error("give an audio file or a folder, or --selftest")
    if not args.input.exists():
        ap.error(f"{args.input} does not exist")
    phonetic = args.recognizer == "phonetic"
    if phonetic:
        print("! -r phonetic ignores the transcript: none is read, -d is not passed and "
              "the word check is skipped", file=sys.stderr)

    if args.input.is_dir():
        if args.text is not None or args.text_file is not None:
            ap.error("--text and --text-file name one line's transcript; a folder reads "
                     "each line's .txt beside it")
        if args.out and args.out.suffix == ".json":
            ap.error("--out must be a folder when the input is a folder")
        audio = sorted(p for p in args.input.iterdir()
                       if p.is_file() and p.suffix.lower() in AUDIO_EXTS)
        if not audio:
            print(f"no audio files in {args.input}", file=sys.stderr)
            return 1
        stems = [p.stem for p in audio]
        dupes = sorted({s for s in stems if stems.count(s) > 1})
        if dupes:
            ap.error(f"several files share a name, so their timelines would collide: {dupes}")
        out_dir = args.out or DEFAULT_OUT
        jobs = [(p, None, out_dir / f"{p.stem}.json") for p in audio]
    else:
        out = args.out or DEFAULT_OUT
        if out.suffix != ".json":
            out = out / f"{args.input.stem}.json"
        jobs = [(args.input, args.text, out)]

    failed, refused = 0, 0
    for path, text, out in jobs:
        try:
            if phonetic:
                text = None
            elif text is None and not args.no_text:
                if args.text_file is not None and len(jobs) == 1:
                    text = read_transcript(args.text_file)
                elif path.with_suffix(".txt").is_file():
                    text = read_transcript(path.with_suffix(".txt"))
            if text is None:
                if not phonetic:
                    print(f"  ! {rel(path)}: no transcript, so the word check is off",
                          file=sys.stderr)
            elif not text.strip():
                raise LineError("the transcript is empty")
            status, _ = run_line(path, text, out, args.recognizer, args.timeout,
                                 args.fps, args.rule, args.force)
            refused += status in ("refused", "forced")
        except LineError as exc:
            print(f"  ERROR {exc}", file=sys.stderr)
            failed += 1
    if len(jobs) > 1:
        print(f"\n{len(jobs) - failed - refused} written, {refused} refused, {failed} failed")
    return 1 if failed else 3 if refused else 0


def refuse_audio_timeline(out: Path) -> None:
    """A text-driven flap must never replace a timeline made from audio."""
    if not out.is_file():
        return
    try:
        audio = json.loads(out.read_text(encoding="utf-8")).get("audio")
    except (OSError, ValueError, AttributeError) as exc:
        raise LineError(f"{rel(out)} exists and is not a timeline this script can read "
                        f"({exc}); choose another --out")
    if audio is not None:
        raise LineError(f"{rel(out)} is a timeline made from audio ({audio}); "
                        "--text-only will not overwrite it, choose another --out")


def main_text_only(ap, args) -> int:
    if args.recognizer != "pocketSphinx":
        ap.error("-r does not apply to --text-only")
    jobs = []
    if args.input is None:
        if args.text is None and args.text_file is None:
            ap.error("--text-only needs a .txt file, a folder, --text or --text-file")
        if not args.out or args.out.suffix != ".json":
            ap.error("--text-only without an input file needs --out NAME.json")
        jobs.append((args.out.stem, args.text, args.text_file, args.out))
    elif args.input.is_dir():
        if args.text is not None or args.text_file is not None:
            ap.error("--text and --text-file name one line; a folder reads its .txt files")
        files = sorted(p for p in args.input.iterdir() if p.is_file() and p.suffix == ".txt")
        if not files:
            print(f"no .txt files in {args.input}", file=sys.stderr)
            return 1
        out_dir = args.out or TEXT_ONLY_OUT
        jobs = [(p.stem, None, p, out_dir / f"{p.stem}.json") for p in files]
    else:
        out = args.out or TEXT_ONLY_OUT
        if out.suffix != ".json":
            out = out / f"{args.input.stem}.json"
        # An audio path stands for the line: read the .txt beside it.
        own = args.input if args.input.suffix == ".txt" else args.input.with_suffix(".txt")
        jobs.append((args.input.stem, args.text,
                     args.text_file or (own if args.text is None else None), out))
    failed = 0
    for line, text, text_file, out in jobs:
        try:
            if text is None:
                text = read_transcript(text_file)
            if not text.strip():
                raise LineError("the text is empty")
            refuse_audio_timeline(out)
            tl = flap(text, line, args.fps, args.rule)
            write(out, tl)
            print(f"  {line}: {len(tl['mouthCues'])} cues over {tl['duration']:.2f} s "
                  f"-> {rel(out)}")
        except LineError as exc:
            print(f"  ERROR {exc}", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
