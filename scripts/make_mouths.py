#!/usr/bin/env python3
"""Make a talking portrait, then its nine mouths, with the edit graph, and compose them.

    # 1. the portrait: a head-and-shoulders crop of the concept, lips closed
    scripts/make_mouths.py --portrait-from output/assets/lord_vitriol/concept.png \\
        --crop 372,65,340,340 --out output/lipsync/lord_vitriol

    # 2. the mouths, once the portrait is approved and the box chosen
    scripts/make_mouths.py output/lipsync/lord_vitriol/portrait.png \\
        --box 410,440,204,190 --shapes XABCDEF --feather 8

    scripts/make_mouths.py output/lipsync/lord_vitriol/portrait.png \\
        --box 410,440,204,190 --shapes XAB --dry-run      # print the prompts only

Every edit, the portrait's included, runs `workflows/api/img_edit_qwen.json`
through `scripts/run_workflow.py`, and waits for the machine first (below).

THE PORTRAIT (`--portrait-from SOURCE --out DIR`): crops SOURCE to `--crop`
if given, keeps that as `source_crop.png`, and edits it at `--seed` and denoise
1.0 with `prompts/mouths/portrait.txt` into `portrait.png`. Then it stops: look
at the portrait, approve it, and choose the box on it. An existing
`portrait.png` is never replaced; delete it to make it again. Crop a square: the
graph's FluxKontextImageScale snaps every input to its nearest trained
resolution, and a square comes back at 1024x1024. lord_vitriol's 340x340 crop
at 372,65 did, with the lips closed, and a second run at the same seed gave a
pixel-identical portrait.

THE BOX goes around the mouth and the whole chin, with room for the jaw to
drop. On lord_vitriol a 184x160 box that stopped 36 px under the resting chin
drifted up to 3.04 on D, 5.41 along its bottom edge where the lowered chin was
cut; a 204x190 box brought every shape to between 1.48 and 1.74, about what the
X edit drifts (1.54). compose_mouths.py can be rerun on the same edits with
another box. The box is checked before any edit: it must lie inside the
portrait, and inside the part of it the edit graph keeps. The graph's size list
is read from the running container for that; if it cannot be read, the check
runs on the first edit's real size instead, before a second edit is queued.

THE MOUTHS (`PORTRAIT --box`): for each shape in `--shapes` (default all nine,
X and A to H) this runs the edit once on the portrait, at one fixed seed, with
that shape's instruction from `prompts/mouths/shapes.txt`, and keeps the result
as `edits/<S>.png` beside the portrait. Then it calls
`scripts/compose_mouths.py`, which cuts the mouth box out of each edit, measures
drift in a ring round the box and writes `manifest.json`. Then check it and
look at it:

    scripts/compose_mouths.py --check output/lipsync/lord_vitriol/manifest.json
    scripts/preview_lipsync.py output/lipsync/lord_vitriol/manifest.json

lord_vitriol's set is made with `--shapes XABCDEF` because its G and H edits
failed and were moved to `_trials/pass2`; asking it for all nine would make
them again, with the same seed and instructions, and put them back in the set.

WHY WHOLE-IMAGE EDITS: the repo has no inpainting model for Qwen-Image, so each
edit re-diffuses the whole portrait and only its mouth box is kept. Everything
outside the box is the portrait's own pixels by construction; the drift figure
says how well the kept box meets them.

RESUMES: a shape whose `edits/<S>.png` exists is skipped, so a stopped run
picks up where it left off. Delete an edit to make it again. The seconds, card
memory and prompt of every edit are kept in `make_mouths.json` across runs,
with the drift from the latest compose.

DENOISE: 0.85 for mouths by default, not the graph's 1.0. On one portrait,
lord_vitriol, with the same D instruction and seed, 1.0 reshaped the whole face
into a shout and drifted 19.70 round the box, and 0.85 opened the mouth and
drifted 3.04. That is one shape on one face: rerun a shape that barely changed
with a higher `--denoise` after deleting its edit. The portrait uses 1.0.

WAITS FOR THE MACHINE: before every edit, the portrait's too, it waits, polling
every 30 s, until no Blender job (`python3 -c`) is running in the container and
ComfyUI's queue is empty, because Blender and ComfyUI share one container and
one card. Queue edits through this script rather than run_workflow.py directly.
While it waits it prints each Blender job's pid and how long it has run, so a
stuck one can be found. It stops, queueing nothing, after `--max-wait` seconds,
and at once when `docker top` fails (a wrong ASSET_ENGINE_CONTAINER, no Docker
permission), because a process list it cannot read is not an idle machine.

UPLOADS: the image goes to ComfyUI under a name made from its content, so two
jobs uploading different pictures with the same file name cannot swap them.

Peak card memory is the most `nvidia-smi` reported during the edit, for the
whole card, so anything else on it counts too. ComfyUI's address is COMFY_URL,
as for run_workflow.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _engine import container                       # noqa: E402
from compose_mouths import (ORDER, compose, crop_covers_box, kontext_crop,  # noqa: E402
                            parse_box, settings_problem)
from run_workflow import SERVER                     # noqa: E402

try:
    from PIL import Image
except ImportError:
    sys.exit("needs numpy and Pillow: pip install --user numpy Pillow")

WORKFLOW = ROOT / "workflows" / "api" / "img_edit_qwen.json"
PROMPTS = ROOT / "prompts" / "mouths" / "shapes.txt"
PORTRAIT_PROMPT = ROOT / "prompts" / "mouths" / "portrait.txt"
# Where FluxKontextImageScale's size list lives in every compose service's image.
KONTEXT_SOURCE = "/app/comfy_extras/nodes_flux.py"
MIN_PORTRAIT = 340


def show(path: Path) -> str:
    """A path relative to the repo when it is inside it."""
    p = path.resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def read_prompts(path: Path) -> dict:
    """`S: text` starts a shape; indented lines continue it; # lines are comments."""
    prompts, cur = {}, None
    for line in read_text(path, "--prompts").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([XA-H]):\s*(.*)$", line)
        if m:
            cur = m.group(1)
            prompts[cur] = m.group(2).strip()
        elif cur and line[:1].isspace():
            prompts[cur] += " " + line.strip()
        else:
            raise SystemExit(f"{path}: cannot read line {line!r}")
    return prompts


def read_text(path: Path, what: str) -> str:
    try:
        return path.read_text()
    except OSError as e:
        raise SystemExit(f"{what}: cannot read {path}: {e.strerror or e}")


def read_one_prompt(path: Path) -> str:
    """The portrait instruction: every non-comment line, joined."""
    lines = [l.strip() for l in read_text(path, "--portrait-prompt").splitlines()
             if l.strip() and not l.lstrip().startswith("#")]
    if not lines:
        raise SystemExit(f"{path} holds no instruction")
    return " ".join(lines)


# The longest wait for the machine before an edit, in seconds: a guard against a
# stuck job, not a measured figure. A probe on 2026-09-16 waited about 37 min
# behind other agents' sheet renders before it could queue.
MAX_WAIT = 7200
POLL = 30


def blender_jobs() -> list[tuple[str, str]]:
    """(pid, seconds running) of each `python3 -c` process in the container.

    Stops the run when `docker top` fails: an unreadable process list is not an
    idle machine, and treating it as one queues an edit beside a Blender job.
    """
    name = container()
    cmd = ["docker", "top", name, "-o", "pid,etimes,args"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except OSError as e:
        raise SystemExit(f"cannot run docker top ({e}), so whether a Blender job is "
                         "running is unknown. No edit was queued")
    except subprocess.TimeoutExpired:
        return [("?", "docker top did not answer within 30 s")]
    if r.returncode != 0:
        raise SystemExit(f"`{' '.join(cmd)}` exited {r.returncode}: "
                         f"{(r.stderr or r.stdout).strip()}\n"
                         "Whether a Blender job is running is unknown, so no edit was "
                         "queued. Check the container name (ASSET_ENGINE_CONTAINER) and "
                         "that you can run docker")
    jobs = []
    for line in r.stdout.splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) == 3 and "python3 -c" in parts[2]:
            jobs.append((parts[0], parts[1]))
    return jobs


def machine_busy(server: str) -> str:
    """Why the machine is busy, or '' when an edit may be queued."""
    jobs = blender_jobs()
    if jobs:
        ages = ", ".join(f"pid {pid} for {age} s" if age.isdigit() else age
                         for pid, age in jobs)
        return f"{len(jobs)} Blender job(s) running in {container()} ({ages})"
    try:
        with urllib.request.urlopen(f"{server.rstrip('/')}/queue", timeout=30) as r:
            q = json.load(r)
    except OSError as e:
        raise SystemExit(f"Cannot reach ComfyUI at {server}: {e}")
    n = len(q.get("queue_running", [])) + len(q.get("queue_pending", []))
    return f"{n} ComfyUI job(s) queued or running" if n else ""


def wait_for_machine(server: str, max_wait: int = MAX_WAIT) -> None:
    started = time.time()
    while True:
        why = machine_busy(server)
        if not why:
            return
        waited = time.time() - started
        if waited >= max_wait:
            raise SystemExit(
                f"  still busy after {waited:.0f} s, the --max-wait of {max_wait} s: "
                f"{why}. No edit was queued. A Blender job running far longer than "
                "its tool's --timeout may be stuck: see "
                f"`docker top {container()} -o pid,etimes,args`")
        pause = round(min(POLL, max(1.0, max_wait - waited)))
        print(f"  waiting: {why}; checking again in {pause} s", flush=True)
        time.sleep(pause)


def kontext_resolutions() -> tuple[list[tuple[int, int]], str]:
    """FluxKontextImageScale's preferred sizes, read from the running container.

    Read at run time rather than copied here, because the list is ComfyUI's.
    Returns ([], reason) when it cannot be read.
    """
    try:
        r = subprocess.run(["docker", "exec", container(), "cat", KONTEXT_SOURCE],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return [], f"docker exec failed: {e}"
    m = re.search(r"^PREFERRED_KONTEXT_RESOLUTIONS\s*=\s*\[(.*?)^\]", r.stdout, re.S | re.M)
    if r.returncode != 0 or not m:
        return [], f"no size list in {container()}:{KONTEXT_SOURCE}"
    sizes = [(int(w), int(h)) for w, h in re.findall(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)", m.group(1))]
    return (sizes, "") if sizes else ([], f"empty size list in {KONTEXT_SOURCE}")


def expected_edit_size(size: tuple[int, int], sizes: list[tuple[int, int]]):
    """The size the scale node will pick: the nearest aspect ratio, then the narrower."""
    aspect = size[0] / size[1]
    return min(sizes, key=lambda wh: (abs(aspect - wh[0] / wh[1]), wh[0], wh[1]))


def crop_problem(portrait: tuple[int, int], edit: tuple[int, int], box: dict) -> str:
    if crop_covers_box(portrait, edit, box):
        return ""
    x0, y0, cw, ch = kontext_crop(portrait, edit)
    return (f"the edit graph returns {edit[0]}x{edit[1]} for this {portrait[0]}x"
            f"{portrait[1]} portrait and keeps only its {cw}x{ch} centre at {x0},{y0}, "
            f"which cuts the mouth box {box}. Use a portrait at a size the edit "
            "graph keeps whole, such as 1024x1024")


class CardMemory:
    """Highest memory.used nvidia-smi reports while the block runs, in MiB."""

    def __init__(self):
        self.peak = None
        self.before = self._read()
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    @staticmethod
    def _read():
        if not shutil.which("nvidia-smi"):
            return None
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                                  "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=10).stdout
            return max(int(v) for v in out.split())
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return None

    def _run(self):
        while not self._stop.is_set():
            v = self._read()
            if v is not None:
                self.peak = v if self.peak is None else max(self.peak, v)
            self._stop.wait(1.0)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join()


def find_output(stdout: str, prefix: str) -> Path | None:
    """The image this edit saved, from run_workflow.py's report.

    Matches the whole save path, `output/<prefix>_00001_.png`, and takes the
    first hit: history is reported before the sweep for fresh files, and the
    sweep can list other jobs' files, including ones with the same file name in
    another folder.
    """
    rx = re.compile(r"^\s+(output/" + re.escape(prefix) + r"_\d+_\.png)(?:\s|$)", re.M)
    hit = rx.search(stdout)
    return ROOT / hit.group(1) if hit else None


def run_edit(image: Path, prompt: str, seed: int, denoise: float, prefix: str,
             retries: int, timeout: int) -> Path:
    digest = hashlib.sha1(image.read_bytes()).hexdigest()[:16]
    with tempfile.TemporaryDirectory(prefix="make_mouths_") as tmp:
        upload = Path(tmp) / f"mouths_{digest}{image.suffix.lower()}"
        shutil.copyfile(image, upload)
        cmd = [sys.executable, str(ROOT / "scripts" / "run_workflow.py"), str(WORKFLOW),
               "--image", str(upload),
               "--set", f"Positive.prompt={prompt}",
               "--set", f"Sampler.seed={seed}",
               "--set", f"Sampler.denoise={denoise}",
               "--set", f"Save.filename_prefix={prefix}",
               "--retries", str(retries)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise SystemExit(f"  the edit did not finish within --timeout {timeout} s. "
                             "It may still be running in ComfyUI; check "
                             f"{SERVER}/queue before starting again")
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(f"  run_workflow.py exited {r.returncode}")
    made = find_output(r.stdout, prefix)
    if made is None or not made.exists():
        raise SystemExit(f"  run_workflow.py reported no image saved as output/{prefix}_*.png")
    return made


def load_record(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"cannot read the record {path}: {e}")


def out_under_output(out: Path) -> Path:
    try:
        return out.relative_to(ROOT / "output")
    except ValueError:
        raise SystemExit(f"--out must be under {ROOT / 'output'}, where ComfyUI saves: {out}")


def make_portrait(args) -> int:
    source = args.portrait_from
    if not source.is_file():
        raise SystemExit(f"no such source image: {source}")
    if not args.out:
        raise SystemExit("--portrait-from needs --out DIR, the set folder under output/")
    out = args.out.resolve()
    out_rel = out_under_output(out)
    prompt = read_one_prompt(args.portrait_prompt)
    denoise = 1.0 if args.denoise is None else args.denoise
    try:
        src = Image.open(source)
        src.load()
    except OSError as e:
        raise SystemExit(f"cannot read {source}: {e}")
    crop = parse_box(args.crop) if args.crop else None
    if crop and not (crop["x"] >= 0 and crop["y"] >= 0
                     and crop["x"] + crop["w"] <= src.width
                     and crop["y"] + crop["h"] <= src.height):
        raise SystemExit(f"--crop {args.crop} is not inside the {src.width}x{src.height} source")
    target = out / "portrait.png"
    if args.dry_run:
        print(f"portrait: {prompt}")
        return 0
    if target.exists():
        print(f"  portrait exists, skipped: {show(target)}. Delete it to make it again.")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    if crop:
        image = out / "source_crop.png"
        src.crop((crop["x"], crop["y"], crop["x"] + crop["w"], crop["y"] + crop["h"])).save(image)
        print(f"  cropped {show(source)} at {args.crop} -> {show(image)}")
    else:
        image = source.resolve()
    wait_for_machine(SERVER, args.max_wait)
    print(f"  portrait  editing at seed {args.seed}, denoise {denoise}", flush=True)
    t0 = time.time()
    with CardMemory() as mem:
        made = run_edit(image, prompt, args.seed, denoise, f"{out_rel.as_posix()}/portrait_raw",
                        args.retries, args.timeout)
    seconds = round(time.time() - t0, 1)
    made.replace(target)
    with Image.open(target) as im:
        size = im.size
    record_path = out / "make_mouths.json"
    record = load_record(record_path)
    record["portrait_edit"] = {
        "source": show(source), "crop": crop, "image": show(image),
        "workflow": show(WORKFLOW), "prompt_file": show(args.portrait_prompt),
        "seconds": seconds, "seed": args.seed, "denoise": denoise,
        "card_mib_before": mem.before, "card_mib_peak": mem.peak,
        "prompt": prompt, "size": list(size), "portrait": "portrait.png"}
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    print(f"  portrait  {seconds} s, card peak {mem.peak} MiB, {size[0]}x{size[1]} "
          f"-> {show(target)}")
    if min(size) < MIN_PORTRAIT:
        print(f"  ! the portrait is under {MIN_PORTRAIT} px on its short side")
    print(f"  record    {show(record_path)}")
    print("\n  next: look at it, approve it, choose the mouth box, then")
    print(f"    scripts/make_mouths.py {show(target)} --box X,Y,W,H")
    return 0


def make_mouths(args, ap) -> int:
    if not args.box:
        ap.error("give --box X,Y,W,H with a portrait")
    portrait = args.portrait.resolve()
    if not portrait.is_file():
        raise SystemExit(f"no such portrait: {args.portrait}")
    box = parse_box(args.box)
    out = (args.out or portrait.parent).resolve()
    out_rel = out_under_output(out)
    shapes = [s for s in args.shapes.upper() if s in ORDER]
    bad = set(args.shapes.upper()) - set(ORDER)
    if bad or not shapes:
        raise SystemExit(f"--shapes takes letters from {''.join(ORDER)}, got {args.shapes!r}")
    prompts = read_prompts(args.prompts)
    missing = [s for s in shapes if s not in prompts]
    if missing:
        raise SystemExit(f"{args.prompts} has no instruction for {', '.join(missing)}")
    denoise = 0.85 if args.denoise is None else args.denoise

    # Everything that can fail without a GPU fails here, before the first edit.
    try:
        with Image.open(portrait) as im:
            size = im.size
    except OSError as e:
        raise SystemExit(f"cannot read the portrait {args.portrait}: {e}")
    problem = settings_problem(box, size, args.ring, args.feather)
    if problem:
        raise SystemExit(problem)
    edits = out / "edits"
    for s in ORDER:
        f = edits / f"{s}.png"
        if f.exists():
            with Image.open(f) as im:
                problem = crop_problem(size, im.size, box)
            if problem:
                raise SystemExit(f"{show(f)}: {problem}")
    todo = [s for s in shapes if not (edits / f"{s}.png").exists()]
    crop_checked = False
    if todo:
        sizes, why = kontext_resolutions()
        if sizes:
            expect = expected_edit_size(size, sizes)
            problem = crop_problem(size, expect, box)
            if problem:
                raise SystemExit(problem)
            crop_checked = True
            print(f"  box fits: the edit graph will return {expect[0]}x{expect[1]} "
                  f"for this {size[0]}x{size[1]} portrait and keep the whole box")
        else:
            print(f"  could not read the edit graph's sizes ({why}); the box is "
                  "checked against the first edit instead")

    if args.dry_run:
        for s in shapes:
            print(f"{s}: {prompts[s]}\n")
        return 0

    edits.mkdir(parents=True, exist_ok=True)
    record_path = out / "make_mouths.json"
    record = load_record(record_path)
    record.update({"portrait": show(portrait), "box": box, "workflow": show(WORKFLOW),
                   "prompts": show(args.prompts)})
    per = record.setdefault("shapes", {})

    for s in shapes:
        target = edits / f"{s}.png"
        if target.exists():
            print(f"  {s}  exists, skipped: {show(target)}")
            continue
        wait_for_machine(SERVER, args.max_wait)
        print(f"  {s}  editing at seed {args.seed}, denoise {denoise}", flush=True)
        t0 = time.time()
        with CardMemory() as mem:
            made = run_edit(portrait, prompts[s], args.seed, denoise,
                            f"{out_rel.as_posix()}/edits/{s}_raw",
                            args.retries, args.timeout)
        seconds = round(time.time() - t0, 1)
        made.replace(target)
        per[s] = {"seconds": seconds, "seed": args.seed, "denoise": denoise,
                  "card_mib_before": mem.before, "card_mib_peak": mem.peak,
                  "prompt": prompts[s], "edit": f"edits/{s}.png"}
        print(f"  {s}  {seconds} s, card peak {mem.peak} MiB -> {show(target)}")
        record_path.write_text(json.dumps(record, indent=2) + "\n")
        if not crop_checked:
            with Image.open(target) as im:
                problem = crop_problem(size, im.size, box)
            if problem:
                raise SystemExit(f"{problem}. The edit is kept at {show(target)}; "
                                 "no further edits were queued")
            crop_checked = True

    manifest = compose(portrait, box, edits, out, ring=args.ring, feather=args.feather)
    for s, d in manifest["drift"].items():
        per.setdefault(s, {})["drift"] = d
    for s, entry in per.items():
        # An edit moved out of edits/ is out of the set: its old drift would mislead.
        entry["in_manifest"] = s in manifest["shapes"]
        if not entry["in_manifest"]:
            entry.pop("drift", None)
    record["ring"], record["feather"] = args.ring, args.feather
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    print(f"  record   {show(record_path)}")
    print("\n  next:")
    print(f"    scripts/compose_mouths.py --check {show(out / 'manifest.json')}")
    print(f"    scripts/preview_lipsync.py {show(out / 'manifest.json')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("portrait", type=Path, nargs="?",
                    help="the approved portrait to make mouths for")
    ap.add_argument("--box", metavar="X,Y,W,H",
                    help="mouth box in portrait pixels, around mouth and chin")
    ap.add_argument("--portrait-from", type=Path, metavar="SOURCE",
                    help="make the portrait from this image instead of making mouths")
    ap.add_argument("--crop", metavar="X,Y,W,H",
                    help="with --portrait-from: crop the source to this first")
    ap.add_argument("--portrait-prompt", type=Path, default=PORTRAIT_PROMPT,
                    help="portrait instruction (default prompts/mouths/portrait.txt)")
    ap.add_argument("--out", type=Path, metavar="DIR",
                    help="set folder, under output/ (default: the portrait's folder)")
    ap.add_argument("--shapes", default="".join(ORDER),
                    help="which shapes to make, as letters (default XABCDEFGH)")
    ap.add_argument("--prompts", type=Path, default=PROMPTS,
                    help="shape instructions (default prompts/mouths/shapes.txt)")
    ap.add_argument("--seed", type=int, default=0, help="one seed for every edit (default 0)")
    ap.add_argument("--denoise", type=float,
                    help="edit strength (default 0.85 for mouths, where the graph's "
                         "own 1.0 moved the whole face, and 1.0 for the portrait)")
    ap.add_argument("--ring", type=int, default=6, help="drift ring width in px (default 6)")
    ap.add_argument("--feather", type=int, default=0,
                    help="blend the box's outer N px into the portrait (default 0)")
    ap.add_argument("--retries", type=int, default=1,
                    help="passed to run_workflow.py for a dropped connection (default 1)")
    ap.add_argument("--timeout", type=int, default=900,
                    help="seconds to allow one edit, waiting excluded (default 900)")
    ap.add_argument("--max-wait", type=int, default=MAX_WAIT, metavar="SECONDS",
                    help="longest wait for a free machine before each edit, then "
                         f"stop without queueing (default {MAX_WAIT})")
    ap.add_argument("--dry-run", action="store_true",
                    help="check the settings, print the instructions and stop")
    args = ap.parse_args()
    if args.max_wait < 0:
        ap.error("--max-wait cannot be negative")

    if args.portrait_from:
        if args.portrait or args.box:
            ap.error("--portrait-from makes a portrait; give a portrait and --box "
                     "in a separate run once it is approved")
        return make_portrait(args)
    if args.crop:
        ap.error("--crop goes with --portrait-from")
    if not args.portrait:
        ap.error("give a portrait and --box, or --portrait-from SOURCE --out DIR")
    return make_mouths(args, ap)


if __name__ == "__main__":
    sys.exit(main())
