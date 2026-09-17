#!/usr/bin/env python3
"""Rerun the 2026-09-15 Rhubarb Lip Sync measurements and compare them with
the published numbers in docs/reference/lip-sync.md.

    scripts/fetch_tools.py --download rhubarb       # once
    research/experiments/rhubarb/reproduce.py        # everything
    research/experiments/rhubarb/reproduce.py --repeats 3
    research/experiments/rhubarb/reproduce.py --skip-determinism --jobs 8

Standard library only; runs on the host and needs ffmpeg on the PATH.

1. **Audio.** LibriSpeech test-clean utterances 6930-75918-0000, 0001 and
   0002 (CC BY 4.0, Panayotov, Chen, Povey and Khudanpur), found through the
   Hugging Face datasets-server rows API for openslr/librispeech_asr, config
   clean, split test, rows 0 to 2. Each FLAC and its transcript is checked
   against a pinned sha256 and cached in input/_devtools/librispeech/, which is
   gitignored, so a second run downloads nothing. ffmpeg converts each to 16 kHz
   mono 16-bit PCM WAV, and makes the 10 s silence, 440 Hz sine and white noise
   files with the note's lavfi sources (the noise with seed=1, which the note's
   run did not set).
2. **Runs** Rhubarb from tools/ one process at a time, with the note's
   commands. Each process is timed on its own: wall time, CPU time and peak
   resident memory come from os.wait4, so they are per process, not the
   running maximum over all children.
3. **Measures** the note's table (default recogniser, with transcript, one
   thread with transcript, phonetic), the word error rates from trace logs,
   how much the transcript changes the cues, the short lines on one thread,
   peak memory, run-to-run determinism, cues shorter than a 12 fps and a 24 fps
   frame, the dat exporter's 12 fps refusal, --extendedShapes "", and the
   non-speech files.
4. **Adds** what the note did not measure, labelled as additions, for
   scripts/lipsync_cues.py:
   - the inputs of its speech gate on the three lines given a right, a
     missing and a wrong transcript (word error rate, longest non-X cue, and
     the share of voiced time in non-X cues of 1.0 s or more);
   - the same gate on made-up audio, with both recognisers: the lines slowed
     to half speed, the vowel of "place" in 0000 stretched 8 and 16 times,
     0001 under steady pink noise, 0000 followed by 2, 4 and 10 s of white
     noise, 10 s of white noise with five seeds, quiet white, pink, brown,
     blue and velvet noise, and a 440 Hz sine at -18 and -6 dBFS. These runs
     are not timed and go --jobs at a time;
   - which cues each --fps rule drops at 12 fps, and where share and
     midpoint differ from 6 to 30 fps;
   - the basis for the text-only flap (median cue length and characters per
     second of these lines).
5. **Writes** results.json beside this file and prints each measurement next
   to the published number.

Word error rate: the ##word lines of a Trace log, fillers such as <s>, <sil>
and [BREATH] and markers such as (2) removed, against the transcript's words,
lower-cased; the word edit distance over the transcript's word count, with
lipsync_cues.py's own functions. "Cues changed" counts cues of the run with a
transcript that do not appear, with the same start, end and shape, in the run
without; "time changed" is the share of 10 ms steps whose shape differs.

Wall times depend on what else the host is running; the load average at the
start is recorded. The stretched fixtures need ffmpeg's rubberband filter;
without it they are skipped and results.json says so. Exit codes: 0 ran to
the end; 1 Rhubarb, ffmpeg or the audio could not be had, or a checksum did
not match.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_tools  # noqa: E402
import lipsync_cues  # noqa: E402

CACHE = ROOT / "input" / "_devtools" / "librispeech"
WORK = CACHE / "work"
FIXTURES = CACHE / "fixtures"
SWEEP_FPS = (6, 8, 9, 10, 11, 12, 12.5, 15, 24, 30)
RESULTS = HERE / "results.json"

ROWS_API = "https://datasets-server.huggingface.co/rows"
DATASET = "openslr/librispeech_asr"
REVISION = "71cacbfb7e2354c4226d01e70d77d5fca3d04ba1"
# sha256 of each FLAC as served, and of its transcript as UTF-8 with no newline.
UTTERANCES = {
    "6930-75918-0000": ("9ce35224156f071ab58eb7feb8a5ceae600f6f9f353da2a6cbf797b6b1ac8a23",
                        "9c3fd9c37616a15061047594d2ccca4213721d77b81077613c9c1005bc3d0fe7"),
    "6930-75918-0001": ("3dfad7eb0793eddd5040d04f1f2f3046ceeee39e0ec461794856a350e1bd728e",
                        "825062619f36e473f4f2291947f5996ee75eec895ce49db8916a8fed678d1f59"),
    "6930-75918-0002": ("74ecfd628f49dca71995972c075fcc9904df804d49a4eb5b11fb712b3584f789",
                        "28176eba884aa96b09ad6f37c9e31b7b272e4c37f72dfc6a9a48a11e75392742"),
}
MAIN = "6930-75918-0001"

# The note's published numbers (docs/reference/lip-sync.md, "Rhubarb on this
# machine", run 2026-09-15; peak memory 2026-09-16).
PUBLISHED = {
    "table.default": {"wall_s": 6.51, "cpu_s": 11.97, "cues": "85, or 87 in 4 of 14 repeats",
                      "shapes": "ABCEFGHX"},
    "table.transcript": {"wall_s": 6.27, "cpu_s": 11.66, "cues": "85 or 87", "shapes": "ABCEFGHX"},
    "table.threads1": {"wall_s": 11.02, "cpu_s": "not checked",
                       "cues": "byte-identical on every repeat", "shapes": "not checked"},
    "table.phonetic": {"wall_s": 1.01, "cpu_s": 1.36, "cues": "101 or 102", "shapes": "ABCDEFGHX"},
    "words.no_transcript": {"edits": 9, "words": 43, "wer": 0.209},
    "words.transcript": {"edits": 0, "wer": 0.0},
    "transcript_effect": {"cues_changed": 28, "of": 85, "time_changed": 0.083,
                          "repeat_noise": "0.5 to 2.4%"},
    "phonetic_speedup": {"vs_default": 6.5, "vs_transcript": 6.2, "more_cues": "16 to 20%"},
    "short_lines_threads1": {"6930-75918-0000": {"wall_s": 2.89, "rtf": 0.83},
                             "6930-75918-0002": {"wall_s": 3.51, "rtf": 0.70},
                             MAIN + " on two threads": {"wall_s": 6.27, "rtf": 0.44},
                             MAIN + " on one thread": {"wall_s": 11.02, "rtf": 0.78}},
    "threads_used": {MAIN: 2},
    "peak_rss_mib": {"short lines, one thread": 156, "long line, two threads": 311},
    "shape_B_share": 0.44, "shortest_cue_s": 0.06, "median_cue_s": 0.14,
    "determinism": {"threads2": "5 runs, 3 different files, 0.5 to 2.4% of time",
                    "threads1": "5 runs byte-identical", "threads1_transcript": "6 runs byte-identical"},
    "subframe": {"transcript_12fps": "32 of 85 (38%), from a run on two threads", "phonetic_12fps": "49 of 102 (48%)",
                 "under_24fps_frame": 0},
    "dat12": {"exit": 1, "message": "Frame rate must be between 24 and 100 fps."},
    "extended_none": {"cues": 86, "A_s_before": 0.65, "A_s_after": 2.20},
    "nonspeech": {"silence": "one X cue, about 0.13 s cold", "sine440": "one X cue, about 0.13 s cold",
                  "whitenoise": "heard 'think', 6.2 s CPU, one 9.90 s B cue between two short X",
                  "whitenoise_phonetic": "9 cues"},
}


# ------------------------------------------------------------------ helpers

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def need(ok: bool, msg: str) -> None:
    if not ok:
        print(f"ERROR {msg}", file=sys.stderr)
        sys.exit(1)


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "asset-engine-reproduce"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def fetch_audio() -> dict[str, str]:
    """Download and verify the three utterances; return {id: transcript}."""
    CACHE.mkdir(parents=True, exist_ok=True)
    texts = {}
    todo = [u for u in UTTERANCES
            if not ((CACHE / f"{u}.flac").is_file() and (CACHE / f"{u}.txt").is_file())]
    rows = {}
    if todo:
        q = urllib.parse.urlencode({"dataset": DATASET, "config": "clean", "split": "test",
                                    "offset": 0, "length": 3})
        print(f"rows API: {ROWS_API}?{q}")
        for r in get_json(f"{ROWS_API}?{q}")["rows"]:
            rows[r["row"]["id"]] = r["row"]
    for u, (flac_sha, text_sha) in UTTERANCES.items():
        flac, txt = CACHE / f"{u}.flac", CACHE / f"{u}.txt"
        if u in todo:
            need(u in rows, f"the rows API did not return {u}")
            src = rows[u]["audio"][0]["src"]
            if f"/--/{REVISION}/--/" not in src:
                print(f"  ! {u}: served from a revision other than {REVISION[:12]}; "
                      "relying on the checksum")
            req = urllib.request.Request(src, headers={"User-Agent": "asset-engine-reproduce"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            need(sha256_bytes(data) == flac_sha,
                 f"{u}.flac sha256 {sha256_bytes(data)} does not match the pinned {flac_sha}")
            text = rows[u]["text"]
            need(sha256_bytes(text.encode()) == text_sha,
                 f"{u} transcript sha256 {sha256_bytes(text.encode())} does not match {text_sha}")
            flac.write_bytes(data)
            txt.write_text(text, encoding="utf-8")
            print(f"  downloaded {u}.flac ({len(data)} bytes), checksums match")
        else:
            need(sha256_bytes(flac.read_bytes()) == flac_sha, f"cached {flac} has the wrong sha256")
            need(sha256_bytes(txt.read_bytes()) == text_sha, f"cached {txt} has the wrong sha256")
        texts[u] = txt.read_text(encoding="utf-8")
    return texts


def ffmpeg(*args: str) -> None:
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *args],
                       capture_output=True, text=True)
    need(r.returncode == 0, f"ffmpeg {' '.join(args)}: {r.stderr.strip()}")


def make_wavs() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    for u in UTTERANCES:
        wav = CACHE / f"{u}.wav"
        if not wav.is_file():
            ffmpeg("-i", str(CACHE / f"{u}.flac"), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                   str(wav))
    sources = {"silence_10s": "anullsrc=channel_layout=mono:sample_rate=16000:duration=10",
               "sine440_10s": "sine=frequency=440:sample_rate=16000:duration=10",
               "whitenoise_10s": "anoisesrc=colour=white:amplitude=0.3:sample_rate=16000:duration=10:seed=1"}
    for name, src in sources.items():
        wav = CACHE / f"{name}.wav"
        if not wav.is_file():
            ffmpeg("-f", "lavfi", "-i", src, "-t", "10", "-ac", "1", "-c:a", "pcm_s16le", str(wav))


class Run:
    """One Rhubarb process, measured on its own."""

    def __init__(self, binary: Path, args: list[str], timeout: float = 900):
        self.args = args
        out_path = WORK / "stdout.tmp"
        err_path = WORK / "stderr.tmp"
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            t0 = time.perf_counter()
            p = subprocess.Popen([str(binary)] + args, cwd=CACHE, stdout=out, stderr=err)
            timer = threading.Timer(timeout, p.kill)
            timer.start()
            _, status, ru = os.wait4(p.pid, 0)
            self.wall = time.perf_counter() - t0
            timer.cancel()
        p.returncode = os.waitstatus_to_exitcode(status)
        self.exit = p.returncode
        self.cpu = ru.ru_utime + ru.ru_stime
        self.rss_mib = ru.ru_maxrss / 1024.0
        self.stdout = out_path.read_bytes()
        self.stderr = err_path.read_text(errors="replace")
        self.json = None
        if self.exit == 0 and "json" in args:
            self.json = json.loads(self.stdout)

    @property
    def cues(self) -> list[dict]:
        return self.json["mouthCues"] if self.json else []

    def md5(self) -> str:
        return hashlib.md5(self.stdout).hexdigest()

    def summary(self) -> dict:
        d = {"command": "rhubarb " + " ".join(a if a else '""' for a in self.args),
             "exit": self.exit, "wall_s": round(self.wall, 3), "cpu_s": round(self.cpu, 3),
             "peak_rss_mib": round(self.rss_mib, 1)}
        if self.json:
            cues = self.cues
            lens = [c["end"] - c["start"] for c in cues]
            dur = self.json["metadata"]["duration"]
            d.update({
                "duration_s": dur, "cues": len(cues),
                "shapes": "".join(sorted({c["value"] for c in cues})),
                "shortest_cue_s": round(min(lens), 3), "median_cue_s": round(statistics.median(lens), 3),
                "longest_cue_s": round(max(lens), 3),
                "shape_time_s": {s: round(sum(c["end"] - c["start"] for c in cues if c["value"] == s), 2)
                                 for s in sorted({c["value"] for c in cues})},
                "md5": self.md5(), "realtime_factor": round(self.wall / dur, 3) if dur else None})
        return d


def shape_at_steps(cues: list[dict], duration: float) -> list[str]:
    steps = int(round(duration * 100))
    out, k = [], 0
    for i in range(steps):
        t = (i + 0.5) / 100
        while k < len(cues) - 1 and t >= cues[k]["end"]:
            k += 1
        out.append(cues[k]["value"])
    return out


def time_disagreement(a: list[dict], b: list[dict], duration: float) -> float:
    sa, sb = shape_at_steps(a, duration), shape_at_steps(b, duration)
    return sum(x != y for x, y in zip(sa, sb)) / max(1, len(sa))


def log_info(log: str) -> dict:
    heard, voiced = lipsync_cues.parse_log(log)
    m = re.search(r"Speech recognition using (\d+) threads", log)
    return {"heard": heard, "voiced_s": voiced, "threads": int(m.group(1)) if m else None}


def wer_against(text: str, heard: list[str]) -> dict:
    ref = lipsync_cues.words_of(text)
    edits = lipsync_cues.edit_distance(ref, heard)
    return {"words": len(ref), "heard": len(heard), "edits": edits,
            "wer": round(edits / len(ref), 4) if ref else None}


def trace_run(binary: Path, extra: list[str], wav: str, name: str) -> tuple[Run, dict]:
    log = WORK / f"{name}.log"
    if log.exists():
        log.unlink()
    r = Run(binary, ["-q", "-f", "json", *extra, "--logFile", str(log.relative_to(CACHE)),
                     "--logLevel", "Trace", wav])
    return r, log_info(log.read_text(errors="replace") if log.is_file() else "")


# ------------------------------------------------------------------ gate fixtures

def has_rubberband() -> bool:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    return re.search(r"\srubberband\s", r.stdout) is not None


def make_gate_fixtures() -> tuple[dict[str, tuple[Path, str | None]], list[str]]:
    """{name: (wav, utterance whose transcript is right, or None)}, and what was skipped."""
    FIXTURES.mkdir(parents=True, exist_ok=True)
    fx: dict[str, tuple[Path, str | None]] = {}
    skipped = []

    def lavfi(name: str, src: str) -> None:
        wav = FIXTURES / f"{name}.wav"
        if not wav.is_file():
            ffmpeg("-f", "lavfi", "-i", src, "-t", "10", "-ac", "1", "-c:a", "pcm_s16le", str(wav))
        fx[name] = (wav, None)

    for seed in range(1, 6):
        lavfi(f"white_seed{seed}", f"anoisesrc=colour=white:amplitude=0.3:sample_rate=16000:seed={seed}")
    lavfi("white_quiet", "anoisesrc=colour=white:amplitude=0.03:sample_rate=16000:seed=1")
    lavfi("pink", "anoisesrc=colour=pink:amplitude=0.5:sample_rate=16000:seed=2")
    lavfi("brown", "anoisesrc=colour=brown:amplitude=0.5:sample_rate=16000:seed=3")
    lavfi("blue", "anoisesrc=colour=blue:amplitude=0.3:sample_rate=16000:seed=4")
    lavfi("velvet", "anoisesrc=colour=velvet:amplitude=0.3:sample_rate=16000:seed=6")
    lavfi("sine440_m18dB", "sine=frequency=440:sample_rate=16000")
    lavfi("sine440_m6dB", "sine=frequency=440:sample_rate=16000,volume=12dB")

    for u in UTTERANCES:
        fx[f"speech_{u[-4:]}"] = (CACHE / f"{u}.wav", u)
    line0, line1 = "6930-75918-0000", "6930-75918-0001"
    for tail in (2, 4, 10):
        wav = FIXTURES / f"tail{tail}s_0000.wav"
        if not wav.is_file():
            ffmpeg("-i", str(CACHE / f"{line0}.wav"), "-f", "lavfi", "-i",
                   f"anoisesrc=colour=white:amplitude=0.3:sample_rate=16000:seed=5:duration={tail}",
                   "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", "-ac", "1",
                   "-c:a", "pcm_s16le", str(wav))
        fx[f"tail{tail}s_0000"] = (wav, line0)
    wav = FIXTURES / "pinknoise_0001.wav"
    if not wav.is_file():
        ffmpeg("-i", str(CACHE / f"{line1}.wav"), "-f", "lavfi", "-i",
               "anoisesrc=colour=pink:amplitude=0.05:sample_rate=16000:seed=7:duration=14.22",
               "-filter_complex", "[0:a][1:a]amix=inputs=2:normalize=0:duration=first",
               "-ac", "1", "-c:a", "pcm_s16le", str(wav))
    fx["pinknoise_0001"] = (wav, line1)
    if has_rubberband():
        for u in (line0, line1):
            wav = FIXTURES / f"slow_{u[-4:]}.wav"
            if not wav.is_file():
                ffmpeg("-i", str(CACHE / f"{u}.wav"), "-af", "rubberband=tempo=0.5",
                       "-ac", "1", "-c:a", "pcm_s16le", str(wav))
            fx[f"slow_{u[-4:]}"] = (wav, u)
        for k in (8, 16):
            # The vowel of "place", 2.00 to 2.15 s in 0000, stretched k times.
            wav = FIXTURES / f"held{k}x_0000.wav"
            if not wav.is_file():
                ffmpeg("-i", str(CACHE / f"{line0}.wav"), "-filter_complex",
                       "[0:a]asplit=3[a][b][c];[a]atrim=0:2.00,asetpts=N/SR/TB[a1];"
                       f"[b]atrim=2.00:2.15,asetpts=N/SR/TB,rubberband=tempo={1 / k}[b1];"
                       "[c]atrim=2.15,asetpts=N/SR/TB[c1];[a1][b1][c1]concat=n=3:v=0:a=1",
                       "-ac", "1", "-c:a", "pcm_s16le", str(wav))
            fx[f"held{k}x_0000"] = (wav, line0)
    else:
        skipped.append("slow_0000, slow_0001, held8x_0000, held16x_0000: ffmpeg has no rubberband filter")
    return fx, skipped


def flat_fields(g: dict) -> dict:
    """The flat-mouth numbers of a lipsync_cues.gate result."""
    c, voiced = g.get("longest_cue"), g.get("voiced_s")
    longest = round(c["end"] - c["start"], 2) if c else None
    return {"longest_non_x_s": longest,
            "longest_share": round(longest / voiced, 4) if c and voiced else None,
            "long_s": g.get("long_s"), "long_share": g.get("long_share"), "voiced_s": voiced}


def gate_run(binary: Path, wav: Path, text_id: str | None, recognizer: str, texts: dict,
             tag: str) -> dict:
    """One untimed one-thread Rhubarb run through lipsync_cues.gate."""
    log = WORK / f"{tag}.log"
    args = ["-q", "-f", "json"]
    if text_id:
        args += ["-d", str(CACHE / f"{text_id}.txt")]
    if recognizer == "phonetic":
        args += ["-r", "phonetic"]
    args += ["--threads", "1", "--logFile", str(log), "--logLevel", "Trace", str(wav)]
    r = subprocess.run([str(binary)] + args, capture_output=True, text=True, timeout=900)
    need(r.returncode == 0, f"rhubarb {' '.join(args)} exited {r.returncode}: {r.stderr[-300:]}")
    data = json.loads(r.stdout)
    cues = data["mouthCues"]
    g = lipsync_cues.gate(cues, log.read_text(errors="replace"),
                          texts[text_id] if text_id else None, recognizer)
    longest = g.get("longest_cue")
    return {"cues": len(cues), "shapes": "".join(sorted({c["value"] for c in cues})),
            "duration_s": data["metadata"]["duration"], "voiced_s": g.get("voiced_s"),
            "wer": g.get("wer"),
            "longest_non_x_s": round(longest["end"] - longest["start"], 2) if longest else None,
            "longest_value": longest["value"] if longest else None,
            "long_cues": g.get("long_cues"), "long_s": g.get("long_s"),
            "long_share": g.get("long_share"), "passed": g["passed"], "reasons": g["reasons"],
            "shortest_cue_s": round(min(c["end"] - c["start"] for c in cues), 2),
            "mouthCues": cues}


# ------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repeats", type=int, default=5,
                    help="runs per determinism case (default: 5, as in the note)")
    ap.add_argument("--skip-determinism", action="store_true",
                    help="leave out the repeat runs, the slowest part")
    ap.add_argument("--jobs", type=int, default=4,
                    help="untimed gate-fixture runs at a time (default: 4)")
    args = ap.parse_args()
    if args.jobs < 1 or args.repeats < 1:
        ap.error("--jobs and --repeats must be at least 1")

    binary = fetch_tools.tool_path("rhubarb")
    need(binary is not None, "Rhubarb is not installed; run scripts/fetch_tools.py --download rhubarb")
    need(shutil.which("ffmpeg") is not None, "ffmpeg is not on the PATH")
    version = lipsync_cues.rhubarb_version(binary)
    print(f"rhubarb {version} at {binary.relative_to(ROOT)}")
    texts = fetch_audio()
    make_wavs()
    load = os.getloadavg()
    res: dict = {
        "date": time.strftime("%Y-%m-%d"), "rhubarb": version,
        "host": {"cpus": os.cpu_count(), "machine": platform.machine(),
                 "python": platform.python_version(), "loadavg_at_start": [round(x, 2) for x in load]},
        "dataset": {"name": DATASET, "revision": REVISION, "licence": "CC BY 4.0",
                    "utterances": list(UTTERANCES)},
        "published": PUBLISHED,
    }
    M = f"{MAIN}.wav"
    D = ["-d", f"{MAIN}.txt"]
    t_all = time.perf_counter()

    # --- the note's table -----------------------------------------------------
    print("\nthe table")
    table = {
        "default": Run(binary, ["-f", "json", M]),
        "transcript": Run(binary, ["-f", "json", *D, M]),
        "threads1": Run(binary, ["-f", "json", *D, "--threads", "1", M]),
        "phonetic": Run(binary, ["-f", "json", "-r", "phonetic", M]),
    }
    res["table"] = {k: v.summary() for k, v in table.items()}
    for k, v in table.items():
        s = res["table"][k]
        print(f"  {k:<11} wall {s['wall_s']:6.2f} s  cpu {s['cpu_s']:6.2f} s  "
              f"cues {s.get('cues')}  shapes {s.get('shapes')}  rss {s['peak_rss_mib']:.0f} MiB")

    # --- words, from trace logs ----------------------------------------------
    print("\nword error rate on the main line")
    _, no_text = trace_run(binary, [], M, "trace_default")
    _, with_text = trace_run(binary, D, M, "trace_transcript")
    res["words"] = {"no_transcript": {**wer_against(texts[MAIN], no_text["heard"]),
                                      "threads": no_text["threads"], "voiced_s": no_text["voiced_s"]},
                    "transcript": {**wer_against(texts[MAIN], with_text["heard"]),
                                   "threads": with_text["threads"]}}
    res["threads_used"] = {MAIN: no_text["threads"]}
    for k, v in res["words"].items():
        print(f"  {k:<14} {v['edits']} edits over {v['words']} words, WER {v['wer']:.1%}, "
              f"{v['threads']} threads")

    a, b = table["default"].cues, table["transcript"].cues
    dur = table["default"].json["metadata"]["duration"]
    a_set = {(c["start"], c["end"], c["value"]) for c in a}
    changed = sum(1 for c in b if (c["start"], c["end"], c["value"]) not in a_set)
    res["transcript_effect"] = {"cues_changed": changed, "of": len(b),
                                "time_changed": round(time_disagreement(a, b, dur), 4)}
    res["phonetic_speedup"] = {
        "vs_default": round(table["default"].wall / table["phonetic"].wall, 2),
        "vs_transcript": round(table["transcript"].wall / table["phonetic"].wall, 2),
        "more_cues_vs_transcript": round(len(table["phonetic"].cues) / len(b) - 1, 3)}

    tr = table["transcript"]
    res["shape_B_share"] = round(sum(c["end"] - c["start"] for c in b if c["value"] == "B") / dur, 3)
    res["D_used"] = any(c["value"] == "D" for c in b)

    # --- short lines, peak memory ---------------------------------------------
    print("\nshort lines (one thread by default under 10 s)")
    shorts = {}
    for u in ("6930-75918-0000", "6930-75918-0002"):
        _, info = trace_run(binary, ["-d", f"{u}.txt"], f"{u}.wav", f"trace_{u}")
        r = Run(binary, ["-f", "json", "-d", f"{u}.txt", f"{u}.wav"])
        shorts[u] = {**r.summary(), "threads": info["threads"],
                     "wer_transcript": wer_against(texts[u], info["heard"])["wer"]}
        print(f"  {u} wall {r.wall:.2f} s ({shorts[u]['realtime_factor']}x), "
              f"{info['threads']} thread(s), rss {r.rss_mib:.0f} MiB, {len(r.cues)} cues")
    res["short_lines"] = shorts
    res["peak_rss_mib"] = {
        "short lines, one thread": [shorts[u]["peak_rss_mib"] for u in shorts],
        "long line, default threads, with transcript": res["table"]["transcript"]["peak_rss_mib"],
        "long line, one thread, with transcript": res["table"]["threads1"]["peak_rss_mib"]}

    # --- sub-frame cues ---------------------------------------------------------
    def subframe(cues, fps):
        return sum(1 for c in cues if c["end"] - c["start"] < 1 / fps - 1e-9)
    ph = table["phonetic"].cues
    t1 = table["threads1"].cues
    res["subframe"] = {"transcript_12fps": [subframe(b, 12), len(b)],
                       "transcript_threads1_12fps": [subframe(t1, 12), len(t1)],
                       "phonetic_12fps": [subframe(ph, 12), len(ph)],
                       "under_24fps_frame": [subframe(b, 24), subframe(t1, 24), subframe(ph, 24)]}
    res["frame_rules_12fps"] = {}
    for rule in ("midpoint", "closure", "share"):
        for name, cues, d in (("threads1", table["threads1"].cues,
                               table["threads1"].json["metadata"]["duration"]),):
            _, _, dropped = lipsync_cues.to_frames(cues, d, 12, rule)
            res["frame_rules_12fps"][rule] = {
                "run": name, "dropped": len(dropped), "of": len(cues),
                "A_dropped": sum(1 for j in dropped if cues[j]["value"] == "A"),
                "A_of": sum(1 for c in cues if c["value"] == "A")}

    # --- dat, extended shapes ------------------------------------------------------
    dat = Run(binary, ["-f", "dat", "--datFrameRate", "12", *D, M])
    res["dat12"] = {"exit": dat.exit, "stderr": dat.stderr.strip().splitlines()[-1] if dat.stderr.strip() else ""}
    ext = Run(binary, ["-f", "json", *D, "--extendedShapes", "", M])
    a_time = lambda cues: round(sum(c["end"] - c["start"] for c in cues if c["value"] == "A"), 2)
    res["extended_none"] = {"cues": len(ext.cues), "shapes": ext.summary().get("shapes"),
                            "A_s_before": a_time(b), "A_s_after": a_time(ext.cues)}

    # --- non-speech ------------------------------------------------------------------
    print("\nnon-speech")
    ns = {}
    for name, extra in (("silence", []), ("sine440", []), ("whitenoise", []),
                        ("whitenoise_phonetic", ["-r", "phonetic"])):
        wav = name.replace("_phonetic", "") + "_10s.wav"
        r = Run(binary, ["-f", "json", *extra, wav])
        _, info = trace_run(binary, extra, wav, f"trace_{name}")
        ns[name] = {**r.summary(), "heard": info["heard"], "voiced_s": info["voiced_s"]}
        print(f"  {name:<20} {len(r.cues)} cues {ns[name]['shapes']}, longest "
              f"{ns[name]['longest_cue_s']} s, wall {r.wall:.2f} s, cpu {r.cpu:.2f} s, heard {info['heard']}")
    res["nonspeech"] = ns

    # --- determinism -----------------------------------------------------------------
    if not args.skip_determinism:
        print(f"\ndeterminism, {args.repeats} runs each")
        det = {}
        for name, extra in (("default", []), ("threads2_transcript", [*D, "--threads", "2"]),
                            ("threads1", ["--threads", "1"]),
                            ("threads1_transcript", [*D, "--threads", "1"])):
            runs = [Run(binary, ["-f", "json", *extra, M]) for _ in range(args.repeats)]
            files = {}
            for r in runs:
                files.setdefault(r.md5(), r)
            distinct = list(files.values())
            worst = max((time_disagreement(x.cues, y.cues, dur) for i, x in enumerate(distinct)
                         for y in distinct[i + 1:]), default=0.0)
            pairs = [time_disagreement(x.cues, y.cues, dur) for i, x in enumerate(distinct)
                     for y in distinct[i + 1:]]
            det[name] = {"runs": len(runs), "distinct_files": len(distinct),
                         "cue_counts": sorted({len(r.cues) for r in runs}),
                         "time_disagreement_min": round(min(pairs), 4) if pairs else 0.0,
                         "time_disagreement_max": round(worst, 4),
                         "wall_s_median": round(statistics.median(r.wall for r in runs), 2)}
            print(f"  {name:<20} {len(distinct)} distinct of {len(runs)}, cue counts "
                  f"{det[name]['cue_counts']}, disagreement up to {worst:.1%}")
        res["determinism"] = det

    # --- additions: the gate's inputs and the flap's basis ----------------------------
    print("\naddition: speech gate inputs (lipsync_cues.py functions, one thread)")
    gate_rows = []
    ids = list(UTTERANCES)
    for u in ids:
        for label, text_id in [("right", u), ("none", None)] + [("wrong", o) for o in ids if o != u]:
            extra = ["-d", f"{text_id}.txt"] if text_id else []
            r, info = trace_run(binary, [*extra, "--threads", "1"], f"{u}.wav",
                                f"gate_{u}_{label}_{text_id or 'none'}")
            log = (WORK / f"gate_{u}_{label}_{text_id or 'none'}.log").read_text(errors="replace")
            g = lipsync_cues.gate(r.cues, log, texts[text_id] if text_id else None, "pocketSphinx")
            recog = wer_against(texts[u], info["heard"])["wer"]
            row = {"line": u, "transcript": label, "transcript_of": text_id,
                   "wer_vs_given": g.get("wer"), "wer_vs_true": recog, **flat_fields(g),
                   "passed": g["passed"], "wall_s": round(r.wall, 2)}
            gate_rows.append(row)
            print(f"  {u} transcript {label:<5} {text_id or '':<16} WER vs given "
                  f"{row['wer_vs_given']}, vs true {recog}, longest non-X {row['longest_non_x_s']} s "
                  f"= {row['longest_share']} of voiced, long share {row['long_share']}")
    for name in ("sine440", "whitenoise"):
        r, info = trace_run(binary, ["--threads", "1"], f"{name}_10s.wav", f"gate_{name}")
        log = (WORK / f"gate_{name}.log").read_text(errors="replace")
        g = lipsync_cues.gate(r.cues, log, None, "pocketSphinx")
        gate_rows.append({"line": name, "transcript": "none", **flat_fields(g),
                          "passed": g["passed"]})
        print(f"  {name} longest non-X share {gate_rows[-1]['longest_share']}, "
              f"long share {gate_rows[-1]['long_share']}")
    res["gate_inputs"] = gate_rows

    print(f"\naddition: speech gate on made-up audio, one thread, {args.jobs} at a time")
    fixtures, skipped = make_gate_fixtures()
    jobs = []
    for name, (wav, right) in fixtures.items():
        if name.startswith("speech_"):
            jobs.append((name, wav, None, "phonetic"))
            continue
        jobs.append((name, wav, None, "pocketSphinx"))
        jobs.append((name, wav, None, "phonetic"))
        if right:
            jobs.append((name, wav, right, "pocketSphinx"))
    fixture_rows = []
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as ex:
        futures = [(job, ex.submit(gate_run, binary, job[1], job[2], job[3], texts,
                                   f"fixture_{job[0]}_{job[3]}_{'right' if job[2] else 'none'}"))
                   for job in jobs]
        for (name, wav, text_id, rec), fut in futures:
            row = {"fixture": name, "recognizer": rec, "transcript": "right" if text_id else "none",
                   **fut.result()}
            fixture_rows.append(row)
            print(f"  {name:<16} {rec:<12} {row['transcript']:<5} {row['cues']:>3} cues, longest "
                  f"non-X {row['longest_non_x_s']} s, long share {row['long_share']}, "
                  f"WER {row['wer']}, {'passed' if row['passed'] else 'refused'}")
    cue_lists = {(r["fixture"], r["recognizer"], r["transcript"]): r.pop("mouthCues")
                 for r in fixture_rows}
    res["gate_fixtures"] = {"skipped": skipped, "rows": fixture_rows}

    def span(rows, key):
        vals = [r[key] for r in rows if r[key] is not None]
        return [min(vals), max(vals)] if vals else None
    groups = {
        "speech": lambda r: r["fixture"].startswith("speech_"),
        "slowed": lambda r: r["fixture"].startswith("slow_"),
        "held_vowel": lambda r: r["fixture"].startswith("held"),
        "pink_noise_under_speech": lambda r: r["fixture"] == "pinknoise_0001",
        "tail2s": lambda r: r["fixture"] == "tail2s_0000",
        "tail4s": lambda r: r["fixture"] == "tail4s_0000",
        "tail10s": lambda r: r["fixture"] == "tail10s_0000",
        "loud_noise_and_sine": lambda r: r["fixture"] in {
            "white_seed1", "white_seed2", "white_seed3", "white_seed4", "white_seed5",
            "pink", "brown", "velvet", "sine440_m6dB"},
        "quiet_or_unvoiced": lambda r: r["fixture"] in {"white_quiet", "blue", "sine440_m18dB"},
    }
    summary = {}
    for g, pick in groups.items():
        rows = [r for r in fixture_rows if pick(r)]
        if rows:
            summary[g] = {"runs": len(rows), "longest_non_x_s": span(rows, "longest_non_x_s"),
                          "long_share": span(rows, "long_share"), "wer": span(rows, "wer"),
                          "refused": sum(1 for r in rows if not r["passed"])}
    # The phonetic longest single cue on loud noise, which is why cues are summed.
    ph_noise = [r for r in fixture_rows if groups["loud_noise_and_sine"](r) and r["recognizer"] == "phonetic"]
    if ph_noise:
        summary["loud_noise_phonetic_longest_share"] = min(
            round(r["longest_non_x_s"] / r["voiced_s"], 4) for r in ph_noise)
    res["gate_fixtures"]["summary"] = summary
    for g, v in summary.items():
        print(f"  {g}: {v}")

    # --- additions: where share and midpoint differ -----------------------------------
    sweep_sets = {"threads1_transcript": (t1, table["threads1"].json["metadata"]["duration"])}
    key = ("speech_0001", "phonetic", "none")
    if key in cue_lists:
        sweep_sets["threads1_phonetic"] = (cue_lists[key], dur)
    res["fps_sweep"] = {}
    for label, (cues, d) in sweep_sets.items():
        rows = []
        for fps in SWEEP_FPS:
            fm, _, dm = lipsync_cues.to_frames(cues, d, fps, "midpoint")
            fs, _, ds = lipsync_cues.to_frames(cues, d, fps, "share")
            _, _, dc = lipsync_cues.to_frames(cues, d, fps, "closure")
            rows.append({"fps": fps, "frames": len(fm),
                         "share_differs_from_midpoint": sum(x != y for x, y in zip(fm, fs)),
                         "dropped": {"midpoint": len(dm), "share": len(ds), "closure": len(dc)}})
        res["fps_sweep"][label] = {"cues": len(cues), "shortest_cue_s": round(
            min(c["end"] - c["start"] for c in cues), 2), "rows": rows}
        print(f"  fps sweep, {label}: " + ", ".join(
            f"{r['fps']} fps {r['share_differs_from_midpoint']}" for r in rows))

    right = [x for x in gate_rows if x["transcript"] == "right"]
    all_cues = []
    for x in right:
        for c in Run(binary, ["-f", "json", "-d", f"{x['line']}.txt", "--threads", "1",
                              f"{x['line']}.wav"]).cues:
            all_cues.append(c["end"] - c["start"])
    chars = sum(len(" ".join(texts[u].split())) for u in ids)
    secs = sum(shorts[u]["duration_s"] for u in shorts) + dur
    res["flap_basis"] = {"median_cue_s": round(statistics.median(all_cues), 3), "cues": len(all_cues),
                         "characters": chars, "seconds": round(secs, 2),
                         "characters_per_second": round(chars / secs, 2)}
    print(f"  flap basis: median cue {res['flap_basis']['median_cue_s']} s over {len(all_cues)} cues; "
          f"{chars} characters in {secs:.2f} s = {chars / secs:.2f} per second")

    res["total_s"] = round(time.perf_counter() - t_all, 1)
    RESULTS.write_text(json.dumps(res, indent=1) + "\n")
    compare(res)
    print(f"\nwrote {RESULTS.relative_to(ROOT)} in {res['total_s']} s")
    return 0


def compare(res: dict) -> None:
    P = PUBLISHED
    rows = []

    def row(what, published, today):
        rows.append((what, str(published), str(today)))

    for k in ("default", "transcript", "threads1", "phonetic"):
        t = res["table"][k]
        row(f"{k}: wall s", P[f"table.{k}"]["wall_s"], t["wall_s"])
        row(f"{k}: CPU s", P[f"table.{k}"]["cpu_s"], t["cpu_s"])
        row(f"{k}: cues", P[f"table.{k}"]["cues"], t.get("cues"))
        row(f"{k}: shapes", P[f"table.{k}"]["shapes"], t.get("shapes"))
    w = res["words"]
    row("WER without transcript", f"{P['words.no_transcript']['wer']:.1%} (9 of 43)",
        f"{w['no_transcript']['wer']:.1%} ({w['no_transcript']['edits']} of {w['no_transcript']['words']})")
    row("WER with transcript", "0.0%", f"{w['transcript']['wer']:.1%}")
    e = res["transcript_effect"]
    row("cues changed by the transcript", "28 of 85, 8.3% of time",
        f"{e['cues_changed']} of {e['of']}, {e['time_changed']:.1%} of time")
    s = res["phonetic_speedup"]
    row("phonetic faster, wall", "6.5x (6.2x vs transcript)", f"{s['vs_default']}x ({s['vs_transcript']}x)")
    row("threads used on the main line", 2, res["threads_used"][MAIN])
    for u, pub in P["short_lines_threads1"].items():
        if u in res["short_lines"]:
            v = res["short_lines"][u]
            row(f"{u}: wall s (x real time)", f"{pub['wall_s']} ({pub['rtf']})",
                f"{v['wall_s']} ({v['realtime_factor']}), {v['threads']} thread(s)")
    row("peak RSS MiB, short lines one thread", 156, res["peak_rss_mib"]["short lines, one thread"])
    row("peak RSS MiB, long line default threads", 311,
        res["peak_rss_mib"]["long line, default threads, with transcript"])
    row("shape B share of the line", P["shape_B_share"], res["shape_B_share"])
    row("D used", "never", res["D_used"])
    row("shortest / median cue s", "0.06 / 0.14",
        f"{res['table']['transcript']['shortest_cue_s']} / {res['table']['transcript']['median_cue_s']}")
    sf = res["subframe"]
    row("cues under a 12 fps frame, transcript", P["subframe"]["transcript_12fps"],
        f"{sf['transcript_12fps'][0]} of {sf['transcript_12fps'][1]} on two threads; "
        f"{sf['transcript_threads1_12fps'][0]} of {sf['transcript_threads1_12fps'][1]} on one")
    row("cues under a 12 fps frame, phonetic", P["subframe"]["phonetic_12fps"],
        f"{sf['phonetic_12fps'][0]} of {sf['phonetic_12fps'][1]}")
    row("cues under a 24 fps frame", 0, sf["under_24fps_frame"])
    row("dat at 12 fps", "exit 1, " + P["dat12"]["message"], f"exit {res['dat12']['exit']}, {res['dat12']['stderr']}")
    x = res["extended_none"]
    row('--extendedShapes "": cues, A seconds', "86, 0.65 -> 2.20",
        f"{x['cues']}, {x['A_s_before']} -> {x['A_s_after']}")
    for name, pub in P["nonspeech"].items():
        v = res["nonspeech"][name]
        row(f"{name}", pub, f"{v['cues']} cues {v['shapes']}, longest {v['longest_cue_s']} s, "
            f"wall {v['wall_s']} s, CPU {v['cpu_s']} s, heard {v['heard']}")
    if "determinism" in res:
        d = res["determinism"]
        row("repeats, --threads 2 with transcript", P["determinism"]["threads2"],
            f"{d['threads2_transcript']['runs']} runs, {d['threads2_transcript']['distinct_files']} files, "
            f"up to {d['threads2_transcript']['time_disagreement_max']:.1%}")
        row("repeats, --threads 1", P["determinism"]["threads1"],
            f"{d['threads1']['runs']} runs, {d['threads1']['distinct_files']} file(s)")
        row("repeats, --threads 1 with transcript", P["determinism"]["threads1_transcript"],
            f"{d['threads1_transcript']['runs']} runs, {d['threads1_transcript']['distinct_files']} file(s)")
        row("repeats, default", "85 or 87 cues",
            f"{d['default']['runs']} runs, {d['default']['distinct_files']} files, cues {d['default']['cue_counts']}")
    print("\ncomparison with the note")
    w1 = max(len(r[0]) for r in rows)
    w2 = min(40, max(len(r[1]) for r in rows))
    print(f"  {'measurement':<{w1}}  {'published':<{w2}}  today")
    for what, pub, today in rows:
        print(f"  {what:<{w1}}  {pub:<{w2}}  {today}")


if __name__ == "__main__":
    sys.exit(main())
