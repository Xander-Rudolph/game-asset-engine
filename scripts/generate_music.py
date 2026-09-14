#!/usr/bin/env python3
"""Generate game music from a prompt folder with ACE-Step 1.5.

    scripts/generate_music.py prompts/music                    # every track
    scripts/generate_music.py prompts/music battle --takes 3   # three seeds of one
    scripts/generate_music.py my_game/music --loop out/music   # then make loops
    scripts/generate_music.py my_game/music --takes 3 --loop out/music --keep-best
    scripts/generate_music.py my_game/music --loop out/music --keep-best --reloop

A prompt folder holds one <name>.txt per track, plus an optional _style.txt
added after every caption: the same split the concept prompts use, so the
shared technique lives in one place.

A track file is settings, one per line, then a blank line, then the caption:

    bpm: 92
    key: G major
    time: 4
    seconds: 200
    seed: 1
    lufs: -16

    Pastoral folk: open, sunlit exploration music. Acoustic guitar and ...

`key` is one of the model's key names ("C# minor", "Bb major"). `time` is the
beats in a bar: 2, 3, 4 or 6. `seconds` sets both length inputs, which the
graph keeps separate. `lufs` only matters with --loop. `planner: yes` turns
the planner on for one track (see --planner). Leave a setting out and the
graph's default stands.

After the caption, a line of three dashes can start the lyrics, which for
ACE-Step are the song's timeline as much as its words: structure tags such as
[Main Theme - strings] or [Variation - horns], one section per line with a
blank line between. Without them the lyrics are "[Instrumental]", and the
planner lays the sections out itself: intros, breaks and endings included.

**The planner is off unless asked for, and most tracks should ask.** ACE-Step
1.5 can have a 1.7B language model lay the track out before the music is made,
and its codes carry the melody and the orchestration. Without it, ambient beds
held up, and a menu theme, a chamber piece and two battle tracks were rejected
by ear. With only "[Instrumental]" for lyrics it lays out a song, breaks and
all, so give it a section script with no intro, break or ending, and give a
slow theme a pulse: a 76 bpm theme still fell silent for half a minute, and
the same theme as a 96 bpm march did not. In this image the planner runs on
the CPU (see the workflow's _comment), about 4.5 minutes for a 150-second
take, and holds the queue while it does.

Takes land in output/music/<name>_NNNNN.flac. With --loop DIR each one is
turned into a seamless loop by make_loop.py at the track's own tempo and
metre, written as DIR/<name>.mp3, or DIR/<name>_seedN.mp3 with more than one
take. With --keep-best as well, every take is looped into DIR/takes/, the one
that loops best is copied to DIR/<name>.mp3, and DIR/picks.json keeps every
take's report and why the winner won.

picks.json also makes a run resumable. It is written after every take, and a
seed already recorded there for the same caption and settings is not made
again, so a stopped run picks up where it left off, and --takes 6 after
--takes 3 makes seeds 4 to 6 and picks from all six. Change the caption or a
setting other than lufs and that track starts over. --reloop makes nothing
new: it loops every recorded take again with the current make_loop.py and
picks again, for when the loop step has changed.

A take is never made twice, even when the run that asked for it died. Before
one is queued, the server's queue and history are searched for the same
graph: a match still in the queue is waited for, and a finished one is used.
So a run stopped part way (by a low-memory guard, say, while other jobs load
their models) loses nothing the server went on to finish. --no-wait does it
on purpose: it queues every take that is missing and exits, and the next run
without it loops and records them.

"Best" only knows what can be measured. Silence inside the loop, or a true
peak over full scale, rules a take out. A jump in level where the loop comes
round, a crossfade that swells over its passages or dips under the bars
around it, a wide loudness range in the loop, heavy limiting, a weak rhythm
match and a loop under 90 s all count against it. Whether a take is any good,
and whether a voice crept in, is not in it: listen to the winners.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_workflow  # noqa: E402  (api, apply_override and wait_for)

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / "workflows" / "api" / "txt2music_acestep15.json"
QUEUED = "queued"


def _yes(value: str) -> bool:
    return value.strip().lower() in ("1", "on", "true", "yes")


SETTINGS = {"bpm": int, "key": str, "time": str, "seconds": float, "seed": int,
            "lufs": float, "planner": _yes}


LYRICS_BREAK = "---"


def _split(path: Path) -> tuple[list[str], str]:
    """A track file's lines before its lyrics, and the lyrics."""
    lines = path.read_text().splitlines()
    marks = [i for i, line in enumerate(lines) if line.strip() == LYRICS_BREAK]
    if not marks:
        return lines, ""
    return lines[:marks[0]], "\n".join(lines[marks[0] + 1:]).strip()


def read_lyrics(path: Path) -> str:
    """The lyrics after a line of ---, or "[Instrumental]"."""
    return _split(path)[1] or "[Instrumental]"


def read_track(path: Path) -> tuple[dict, str]:
    """A track file's settings and its caption."""
    lines = _split(path)[0]
    settings: dict = {}
    i = 0
    while i < len(lines) and lines[i].strip():
        m = re.fullmatch(r"\s*([a-z]+)\s*:\s*(.+?)\s*", lines[i])
        if not m or m.group(1) not in SETTINGS:
            break
        settings[m.group(1)] = SETTINGS[m.group(1)](m.group(2))
        i += 1
    caption = " ".join(line.strip() for line in lines[i:] if line.strip())
    if not caption:
        sys.exit(f"{path}: no caption after the settings")
    return settings, caption


def made_with(settings: dict) -> dict:
    """The settings that shape the music itself. `lufs` only matters to the
    loop, so a new level needs --reloop, not new takes."""
    return {k: v for k, v in settings.items() if k != "lufs"}


def overrides(name: str, settings: dict, caption: str, seed: int, planner: bool,
              lyrics: str = "[Instrumental]") -> list[str]:
    """The --set overrides that make one take."""
    def put(key: str, value) -> str:
        # JSON-encoded, so "4" stays the string the time signature menu
        # wants and a caption is never mistaken for JSON.
        return f"{key}={json.dumps(value)}"

    specs = [put("Music.tags", caption), put("Music.lyrics", lyrics),
             put("Music.seed", seed), put("Sampler.seed", seed),
             put("Music.generate_audio_codes", planner),
             put("Save.filename_prefix", f"music/{name}")]
    if "bpm" in settings:
        specs.append(put("Music.bpm", settings["bpm"]))
    if "key" in settings:
        specs.append(put("Music.keyscale", settings["key"]))
    if "time" in settings:
        specs.append(put("Music.timesignature", settings["time"]))
    if "seconds" in settings:
        specs += [put("Music.duration", settings["seconds"]),
                  put("Length.seconds", settings["seconds"])]
    return specs


def build_graph(workflow: Path, specs: list[str]) -> dict:
    """The graph run_workflow.py queues for these overrides."""
    graph = json.loads(workflow.read_text())
    with contextlib.redirect_stdout(io.StringIO()):
        for spec in specs:
            run_workflow.apply_override(graph, spec)
    return {k: v for k, v in graph.items() if isinstance(v, dict) and "class_type" in v}


def _nodes(graph: dict) -> dict:
    return {k: (v.get("class_type"), v.get("inputs")) for k, v in graph.items()
            if isinstance(v, dict) and "class_type" in v}


def flac_outputs(entry: dict) -> list[Path]:
    """The FLAC files a finished prompt saved that are still on disk."""
    found = []
    for out in entry.get("outputs", {}).values():
        for items in out.values():
            for it in items if isinstance(items, list) else []:
                if isinstance(it, dict) and str(it.get("filename", "")).endswith(".flac"):
                    path = ROOT / "output" / (it.get("subfolder") or "") / it["filename"]
                    if path.exists():
                        found.append(path)
    return found


def existing_take(graph: dict, wait: bool):
    """A take of exactly this graph that the server has made or is making.

    Its FLAC files if it is made (after waiting for it, if it was queued and
    `wait`), QUEUED if it is queued and not waited for, None if there is none."""
    want = _nodes(graph)
    try:
        q = run_workflow.api("/queue")
        for item in q.get("queue_running", []) + q.get("queue_pending", []):
            if _nodes(item[2]) == want:
                if not wait:
                    return QUEUED
                print(f"   already queued as {item[1]}; waiting for it", flush=True)
                return flac_outputs(run_workflow.wait_for(item[1])) or None
        # Read after the queue, and fresh each time, so a prompt that leaves the
        # queue between the two reads is in this one. A copy kept for 30 s
        # missed exactly that, and a take was made twice.
        history = run_workflow.api("/history?max_items=500")
    except SystemExit:
        return None
    for entry in reversed(list(history.values())):
        if (entry.get("status", {}).get("status_str") == "success"
                and _nodes(entry.get("prompt", [None, None, {}])[2]) == want):
            files = flac_outputs(entry)
            if files:
                return files
    return None


def submit(graph: dict) -> str | None:
    """Queue a graph without waiting for it; its prompt id."""
    try:
        res = run_workflow.api("/prompt", {"prompt": graph, "client_id": uuid.uuid4().hex})
    except SystemExit as e:
        print(e, file=sys.stderr)
        return None
    if res.get("node_errors"):
        print(json.dumps(res["node_errors"], indent=2), file=sys.stderr)
        return None
    return res.get("prompt_id")


def queue(workflow: Path, name: str, specs: list[str]) -> list[Path]:
    """Run the graph once; the FLAC files it saved."""
    args = [sys.executable, str(ROOT / "scripts" / "run_workflow.py"), str(workflow)]
    for spec in specs:
        args += ["--set", spec]
    r = subprocess.run(args, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stdout.flush()
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        return []
    # Audio saves as <prefix>_00001.flac: no trailing underscore, unlike the
    # image savers' <prefix>_00001_.png, so accept either.
    #
    # Only the lines with nothing after the path: those are the files this
    # prompt saved, read from the server's history. run_workflow.py then lists
    # everything else written to output/ while it waited, with a size after
    # it, which on a shared server is other people's files and, often, the
    # previous take finishing its write. Taking the last match looped seed 2's
    # file a second time in place of seed 3's.
    found = re.findall(rf"^\s*output/(music/{re.escape(name)}_\d+_?\.flac)\s*$",
                       r.stdout, flags=re.M)
    return [ROOT / "output" / f for f in dict.fromkeys(found)]


def loop_take(src: Path, dst: Path, settings: dict, report: bool):
    """make_loop.py on one take. With `report`, its JSON report, else {};
    None if it failed."""
    cmd = [sys.executable, str(ROOT / "scripts" / "make_loop.py"), str(src), str(dst),
           "--lufs", str(settings.get("lufs", -14.0))]
    if "bpm" in settings:
        cmd += ["--bpm", str(settings["bpm"]),
                "--beats-per-bar", str(int(settings.get("time", "4")))]
    if not report:
        return {} if subprocess.call(cmd) == 0 else None
    r = subprocess.run(cmd + ["--json"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout)[-1500:])
        return None
    return json.loads(r.stdout.strip().splitlines()[-1])


def loudness_range(path: Path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                        "ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"LRA:\s+([\d.]+) LU", r.stderr[r.stderr.rfind("Summary:"):])
    return float(m.group(1)) if m else 99.0


def penalty(rep: dict) -> float:
    """What can be measured against a loop, lower is better."""
    return round(
        (100 if rep["longest_silence_s"] > 0 else 0)
        + (100 if rep.get("true_peak") is not None and rep["true_peak"] > 0 else 0)
        + abs(rep["restart_jump_db"]) * 2
        + max(0.0, rep["crossfade_swell_db"]) * 2
        + max(0.0, -rep.get("crossfade_dip_db", 0.0)) * 2
        + max(0.0, (rep.get("lra") or 0.0) - 6)
        + max(0.0, rep["peaks_limited_db"] - 3)
        + (1 - rep["rhythm_match"]) * 5
        + max(0.0, 90 - rep["loop_s"]) * 0.1, 2)


def take_path(loop_dir: Path, name: str, seed: int) -> Path:
    return loop_dir / "takes" / f"{name}_seed{seed}.mp3"


def loop_report(src: Path, name: str, seed: int, settings: dict, loop_dir: Path,
                raw_lra: float | None = None) -> dict | None:
    """Loop one take into loop_dir/takes/ and score it; None if that failed."""
    rep = loop_take(src, take_path(loop_dir, name, seed), settings, report=True)
    if rep is None:
        return None
    rep.update(seed=seed, source=str(src.relative_to(ROOT)),
               raw_lra=loudness_range(src) if raw_lra is None else raw_lra)
    rep["penalty"] = penalty(rep)
    print(f"   seed {seed}: penalty {rep['penalty']}, {rep['loop_s']}s loop from "
          f"{rep.get('start_s', 0)}s, restart jump {rep['restart_jump_db']:+.1f} dB, "
          f"loudness range {rep.get('lra')} LU (the raw take {rep['raw_lra']}), "
          f"silence {rep['longest_silence_s']}s", flush=True)
    return rep


def record(picks: dict, picks_path: Path, loop_dir: Path, name: str, caption: str,
           settings: dict, reports: list, lyrics: str = "[Instrumental]") -> dict:
    """Keep the best take as loop_dir/<name>.mp3 and write picks.json. Done
    after every take, so a stopped run loses nothing it finished."""
    best = min(reports, key=lambda r: r["penalty"])
    shutil.copy2(take_path(loop_dir, name, best["seed"]), loop_dir / f"{name}.mp3")
    picks[name] = {"kept_seed": best["seed"], "caption": caption, "lyrics": lyrics,
                   "settings": settings, "takes": reports}
    picks_path.write_text(json.dumps(picks, indent=1))
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("names", nargs="*", help="tracks to run (default: all)")
    ap.add_argument("--takes", type=int, default=1,
                    help="seeds per track, counting up from its own seed")
    ap.add_argument("--loop", type=Path, metavar="DIR",
                    help="make each take a seamless loop, written into DIR")
    ap.add_argument("--keep-best", action="store_true",
                    help="with --loop: keep the take that loops best as DIR/<name>.mp3")
    ap.add_argument("--reloop", action="store_true",
                    help="with --keep-best: make nothing new, loop the takes in "
                         "DIR/picks.json again and pick again")
    ap.add_argument("--no-wait", action="store_true",
                    help="queue every missing take and exit; the next run without "
                         "it finds them on the server, and loops and records them")
    ap.add_argument("--planner", action="store_true",
                    help="let the planner lay each track out first: slow, and it "
                         "plans a song with an intro, breaks and an ending")
    ap.add_argument("--workflow", type=Path, default=WORKFLOW)
    a = ap.parse_args()
    if a.keep_best and not a.loop:
        sys.exit("--keep-best needs --loop DIR")
    if a.reloop and not a.keep_best:
        sys.exit("--reloop needs --loop DIR --keep-best")
    if a.reloop and a.no_wait:
        sys.exit("--reloop makes nothing, so --no-wait has nothing to queue")

    style_file = a.folder / "_style.txt"
    style = style_file.read_text().strip() if style_file.exists() else ""
    tracks = sorted(p for p in a.folder.glob("*.txt") if not p.name.startswith("_"))
    if a.names:
        wanted = set(a.names)
        tracks = [p for p in tracks if p.stem in wanted]
        missing = wanted - {p.stem for p in tracks}
        if missing:
            sys.exit(f"no prompt for: {', '.join(sorted(missing))}")
    if not tracks:
        sys.exit(f"no track prompts in {a.folder}")

    picks_path = a.loop / "picks.json" if a.keep_best else None
    picks = json.loads(picks_path.read_text()) if picks_path and picks_path.exists() else {}
    failed = []
    for path in tracks:
        name = path.stem
        settings, caption = read_track(path)
        if style:
            caption = f"{caption} {style}"
        lyrics = read_lyrics(path)
        planner = settings.get("planner", a.planner)
        reports: list = []
        old = picks.get(name)
        if (old and old.get("caption") == caption
                and old.get("lyrics", "[Instrumental]") == lyrics
                and made_with(old.get("settings", {})) == made_with(settings)):
            reports = old["takes"]
        elif old:
            print(f"-- {name}: the prompt has changed since its recorded takes, so they are not reused")

        if a.reloop:
            again = []
            for rep in reports:
                src = ROOT / rep["source"]
                if not src.exists():
                    print(f"   seed {rep['seed']}: {rep['source']} is gone, so it is dropped")
                    continue
                print(f"== {name} (seed {rep['seed']}, looping again)", flush=True)
                new = loop_report(src, name, rep["seed"], settings, a.loop, rep.get("raw_lra"))
                if new is None:
                    failed.append(f"{name} seed {rep['seed']} (loop)")
                else:
                    again.append(new)
            if again:
                best = record(picks, picks_path, a.loop, name, caption, settings, again, lyrics)
                print(f"   kept seed {best['seed']} as {a.loop / (name + '.mp3')}", flush=True)
            continue

        done = {r["seed"] for r in reports}
        for take in range(a.takes):
            seed = settings.get("seed", 1) + take
            if seed in done:
                print(f"== {name} (seed {seed}) is already in {picks_path}", flush=True)
                continue
            specs = overrides(name, settings, caption, seed, planner, lyrics)
            graph = build_graph(a.workflow, specs)
            found = existing_take(graph, wait=not a.no_wait)
            if a.no_wait:
                if found is None:
                    pid = submit(graph)
                    print(f"== {name} (seed {seed}) "
                          + (f"queued as {pid}" if pid else "could not be queued"), flush=True)
                    if not pid:
                        failed.append(f"{name} seed {seed}")
                else:
                    print(f"== {name} (seed {seed}) is already "
                          + ("queued" if found == QUEUED else "made"), flush=True)
                continue
            print(f"== {name} (seed {seed}{', planner on' if planner else ''})", flush=True)
            if found:
                print(f"   already made by an earlier run: {found[-1].relative_to(ROOT)}", flush=True)
                outs = found
            else:
                outs = queue(a.workflow, name, specs)
            if not outs:
                failed.append(f"{name} seed {seed}")
                continue
            if not a.loop:
                continue
            if not a.keep_best:
                stem = name if a.takes == 1 else f"{name}_seed{seed}"
                if loop_take(outs[-1], a.loop / f"{stem}.mp3", settings, report=False) is None:
                    failed.append(f"{name} seed {seed} (loop)")
                continue
            rep = loop_report(outs[-1], name, seed, settings, a.loop)
            if rep is None:
                failed.append(f"{name} seed {seed} (loop)")
                continue
            reports.append(rep)
            record(picks, picks_path, a.loop, name, caption, settings, reports, lyrics)
        if a.keep_best and reports and not a.no_wait:
            best = min(reports, key=lambda r: r["penalty"])
            print(f"   kept seed {best['seed']} as {a.loop / (name + '.mp3')}", flush=True)
    if failed:
        print("FAILED:", "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
