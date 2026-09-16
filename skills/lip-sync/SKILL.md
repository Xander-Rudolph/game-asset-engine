---
name: lip-sync
description: Make a 2D dialogue portrait talk - mouth shapes edited from the portrait, timed to a voice line with Rhubarb Lip Sync and previewed as a video. Use when the user says "make this portrait talk" or "lip sync this line", or wants mouth shapes or Rhubarb mouth cues for a dialogue portrait. Not for a 3D model's face rig, and it makes no voice.
---

# Lip sync: a talking portrait, one gate per turn

Work in the asset-engine repo root. The long version, with every measurement
and what failed on the way, is `docs/guide/talking-portraits.md`. The research
behind it, including which voices may ship, is `docs/reference/lip-sync.md`.

A set is one portrait, one mouth overlay per shape cut from whole-image edits
of it, a `manifest.json`, a timeline JSON per voice line, and an MP4 to judge
it by. A game draws the portrait and swaps only the mouth box.

The shapes are Rhubarb Lip Sync's letters: X rest, A closed (P, B, M), B teeth
together (K, S, T, EE), C open (EH, AE), D wide open (AA), E rounded (AO, ER),
F puckered (UW, OW, W), G upper teeth on the lower lip (F, V), H tongue raised
(a long L).

**One stage per turn.** Show each result, get an answer, then start the next:
the voice, the portrait, the mouth box, the mouths, the timeline, the preview.
If you run two stages without asking, that is a bug.

## First, is this the right route?

Ask what the user has and wants before the checks below.

- **A 3D model, a rigged character or a sprite sheet that should talk.** Say
  that a face does not read at sprite size: a 20 degree jaw added to one
  generated rig changed at most 15 pixels by 16 levels or more in a 128 px
  view, and on a whole MakeHuman figure no viseme changed more than 18 pixels
  at 128 or 220 px (`docs/reference/lip-sync.md`, "What not to do"). Offer a
  2D portrait instead. If they still want a jaw or shape keys on the model,
  that is `scripts/face_rig.py`, in `docs/guide/rigging.md`, "Faces", not this
  skill.
- **Mouth cues only, for mouth art they already have.** Do step 1, then go
  straight to step 5. That needs only Rhubarb and ffmpeg on the host, not the
  container or the edit model. Stop after step 5: step 6 plays a set that
  step 4 made.
- **A voice.** Nothing in this repo makes speech. Say so, and use step 1 to
  check whichever voice they bring.

## Before you start

```sh
scripts/doctor.py --skip-models
scripts/fetch_models.py --group qwen_edit --group qwen   # the edit model, and the qwen files it reuses
scripts/fetch_tools.py                        # is Rhubarb unpacked in tools/?
command -v ffmpeg ffprobe                     # both needed on the host
```

Read the doctor's output and do not start until it says ready. With
`--skip-models` the doctor checks no weights, and the edit model reuses the
`qwen` group's text encoder and VAE, so check both groups. If either is
missing, say the size first: `--download --group qwen_edit` is
19.0GB, and `--download --group qwen` is about 48GB (`--list-groups`), of
which the edit uses only the 8.7GB text encoder and the 242.0MB VAE.
If Rhubarb is missing, `scripts/fetch_tools.py --download rhubarb` fetches the
1.14.0 release pinned in `tools.json` by size and sha256, and unpacks only
`rhubarb`, `res/` and `LICENSE.md` (93,614,327 bytes) into the gitignored
`tools/`.

Rhubarb and ffmpeg run on the host. Rhubarb inside the container was never
tried.

## Rules for the shared machine

- **One ComfyUI job at a time, and never while Blender runs.** Blender and
  ComfyUI share one container and one card. Queue every edit, the portrait's
  included, through `scripts/make_mouths.py`: before each one it polls every
  30 s until no Blender job (`python3 -c`) runs in the container and
  ComfyUI's queue is empty. Never queue these edits with
  `scripts/run_workflow.py` directly. The first portrait was made that way
  and was queued while a Blender job was running.
- **Say the cost before queueing.** One edit took 143 to 157 s, so nine
  mouths are about 23 minutes of GPU, and the whole card peaked at 15,178 to
  15,344 MiB during the edits. Other people's Blender jobs can add a wait: one
  probe waited about 37 minutes before it could queue.
- **Stop only what you started.** Check `curl -s http://127.0.0.1:8188/queue`
  and interrupt by `prompt_id`. Never restart the container for this skill.

## 1. The voice: may these lines ship?

Ask where the voice lines come from before making anything. A game ships the
voice as well as the mouths.

- **A recording** needs the rights to ship that performance.
- **Text-to-speech:** check the model and the voice against
  `docs/reference/lip-sync.md`, "Text-to-speech whose lines may ship"
  (<https://xander-rudolph.github.io/game-asset-engine/reference/lip-sync#text-to-speech-whose-lines-may-ship>).
  XTTS-v2, Fish Speech without Fish Audio's written licence, F5-TTS's
  pretrained weights and Piper's lessac voice may not be used in a game that
  is sold, and an unsettled entry is not allowed either. Those tables were
  read on 2026-09-15, not run, and terms change.
- **No voice yet:** the text-only flap in step 5 works from the script.

If the voice may not ship, say so and stop. No synthetic voice has been run
through Rhubarb here, so say that a TTS line is untested too.

## 2. The portrait

```sh
scripts/make_mouths.py --portrait-from output/<approved concept>.png \
    --crop X,Y,W,H --out output/lipsync/<name>
```

- **Crop a square**, head and shoulders, from the approved concept. The edit
  graph snaps every input to a trained size, and a square comes back at
  1024x1024. A 340x340 crop did.
- It edits the crop at denoise 1.0 with `prompts/mouths/portrait.txt`: sharpen,
  close the lips, keep everything else. It took 136 s and 154.4 s on two runs,
  which gave pixel-identical portraits.
- It writes `source_crop.png` and `portrait.png`, then stops. It never
  replaces an existing `portrait.png`; delete it to make it again.

**Read `portrait.png` back** beside `source_crop.png`, and say what changed
besides the lips. The lips must be closed with no teeth showing, because the
portrait's own mouth is the rest shape. Ask: **approve**, **another crop**, or
**stop**.

## 3. The mouth box

Choose a box around the mouth **and the whole chin, with room for the jaw to
drop**, in portrait pixels. Draw it, read it back, and dry-run it:

```sh
python3 - output/lipsync/<name>/portrait.png X,Y,W,H output/lipsync/<name>/box.png <<'EOF'
import sys
from PIL import Image, ImageDraw
src, box, dst = sys.argv[1], [int(v) for v in sys.argv[2].split(",")], sys.argv[3]
x, y, w, h = box
im = Image.open(src).convert("RGB")
ImageDraw.Draw(im).rectangle([x, y, x + w - 1, y + h - 1], outline=(255, 0, 0), width=3)
im.save(dst)
EOF
scripts/make_mouths.py output/lipsync/<name>/portrait.png --box X,Y,W,H --dry-run
```

The dry run queues nothing. It checks that the box lies inside the portrait and
inside the part the edit graph keeps, then prints `box fits: ...` or the
reason it does not.

On the one set made so far, a 184x160 box that stopped short under the chin
drifted 3.04 on D, and 5.41 along its bottom edge where the lowered chin was
cut. A 204x190 box on the same edits kept every shape between 1.48 and 1.74,
close to the rest edit's own 1.54. Drift is the mean difference, in 0 to 255
levels, in a 6 px ring round the box.

Show `box.png` and ask: **approve and make the mouths**, or **move it**. Put
the cost in that question, so that approving covers it: one edit per shape at
143 to 157 s each, about 23 minutes of GPU for nine, the whole card peaking at
15,178 to 15,344 MiB, and possibly a wait first behind other people's Blender
jobs. Nothing is queued before that answer.

## 4. The mouths

Run this only on step 3's approval. If the shapes, box or instructions changed
since, say the new cost and ask again first.

```sh
scripts/make_mouths.py output/lipsync/<name>/portrait.png --box X,Y,W,H --feather 8
scripts/compose_mouths.py --check output/lipsync/<name>/manifest.json
```

**If `--check` exits 1, show its `!` lines and stop.** Do not draw the sheet,
preview or hand over the set; say what failed and ask what to redo. Only when
it passes, draw the contact sheet:

```sh
scripts/preview_lipsync.py output/lipsync/<name>/manifest.json    # sheet only
```

- One whole-image edit per shape, at seed 0 and denoise 0.85, with the
  instructions in `prompts/mouths/shapes.txt`, kept as `edits/<S>.png`. Only
  the box is cut out. `--check` fails unless zero pixels outside the box
  change, every overlay is the box's size and A to F are present.
- **Keep denoise at 0.85.** At the graph's 1.0 the D edit turned the whole
  face into a shout and drifted 19.70 round the box.
- A stopped run resumes: a shape whose edit exists is skipped. To redo one,
  delete its edit and run again with `--shapes <letter>`.
- `--feather 8` fades the box's outer 8 px into the portrait, inside the box
  only. It was chosen over 0 by eye.

**Read `contact_sheet.png` back and judge it shape by shape**, a line per
letter: does it read as its shape, and does it differ from its neighbours?
`compose_mouths.py` cannot tell. On the one set made so far these were weak,
so look at them first and name them:

- **A against X.** The pressed-lips A came out 0.68 levels from the rest mouth
  X inside the box, after two wordings: P, B and M show no closure.
- **E against C.** C's first wording opened as far as D. Its second halved the
  opening but landed next to E (4.64 levels apart), so E reads as a second C.
- **G and H fall back.** Two wordings each failed: G showed both rows of
  teeth, and H put the tongue out past the lips. They were left out, so G
  plays as A and H as C, as Rhubarb substitutes. The sheet marks them absent.

Ask per shape: **keep**, **redo** (delete its edit, then another wording in a
copy of `shapes.txt` passed with `--prompts`, or another `--seed`), or, for G
or H only, **leave it out** (move its edit out of `edits/` and run
`scripts/compose_mouths.py <portrait> --box X,Y,W,H --edits <set>/edits
--feather 8`). After that, pass `--shapes XABCDEF` to `make_mouths.py`, or it
makes G and H again. Only one portrait and one seed were ever tried, so do not
promise that a redo fixes a shape.

## 5. The timeline

Put each line's UTF-8 transcript beside its audio (`lines/smith_01.ogg` and
`lines/smith_01.txt`), then:

```sh
scripts/lipsync_cues.py lines/smith_01.ogg --out output/lipsync/<name>/smith_01.json
scripts/lipsync_cues.py lines/ --out output/lipsync/<name>        # a folder of lines
```

- **Always with a transcript**, from the `.txt` beside the audio, `--text` or
  `--text-file`. On a 14.22 s line, without one the recogniser made 9 word
  edits against the 43-word transcript (20.9% word error rate), and none with
  it.
- **Always on one thread.** The script passes `--threads 1` itself. Five runs
  on more threads gave 2 or 3 different cue files; five on one thread were
  byte-identical. Never keep a cue file from `rhubarb` run by hand on more
  threads. The 14.22 s line took 11.24 s.
- **The speech gate** refuses a line, exit 3 with nothing written, when the
  words heard miss the transcript by more than 60%, or when non-X cues of
  1.0 s or more cover more than half the voiced time, which is what noise and
  music look like. Tell the user which line and why. Pass `--force` only when
  they ask: it writes the timeline marked as refused. Music can still pass
  without a transcript, so keep music, ambience and effects out.
- **Not English:** `-r phonetic` reads no transcript, so only the flat-mouth
  check guards it, and its accuracy was never measured.
- **Frames only for a baked animation:** `--fps 12 --rule closure` adds a shape
  per frame. An engine that plays cue times needs none. No frame rule has been
  judged on a portrait.
- **No voice yet:** `scripts/lipsync_cues.py --text-only lines/smith_01.txt`
  writes a flap to `output/lipsync/text-only/`. It has not been judged on a
  portrait either.

Show each line's `gate` block (`wer`, `long_share`, `warnings`) and its cue
count. Ask before the preview.

## 6. The preview

```sh
scripts/preview_lipsync.py output/lipsync/<name>/manifest.json output/lipsync/<name>/smith_01.json
```

It writes `smith_01.mp4` beside the timeline, with the line's audio when the
timeline's `audio` file exists, and redraws `contact_sheet.png` with how many
frames each shape got. `--label` prints the shape and time on every frame.

**Read the contact sheet back and hand over the MP4**, which the conversation
cannot show. Say plainly that the frames were checked against the timeline
(85 of 85 matched on the test line) but sync has never been judged by
watching with sound: the user is that check. Ask: **approve**, **redo a
shape** (step 4) or **redo a line** (step 5).

When it is approved, list what ships: `portrait.png`, `mouth_*.png`,
`manifest.json` and each timeline, at 1024x1024; nothing here scales them to
a game size. Write down where each voice line came from, next to the lines.
