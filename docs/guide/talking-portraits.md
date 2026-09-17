# Talking portraits

*A dialogue portrait that talks: mouth overlays edited from one image, and
mouth cues timed to a voice line with Rhubarb Lip Sync.*

Everything below was run on 2026-09-15 and 2026-09-16 on the reference
machine: Rhubarb and ffmpeg on the host, the image edits in the container on a
16GB card shared with other jobs. One portrait, `lord_vitriol`, was made, at
one seed. Each section says what failed and what worked instead, and the page
ends with [what was not tested](#what-was-not-tested).

The background (other mouth-shape sets, other aligners, how 2D games play
portraits, and which voices may ship) is in the research note
[lip sync and talking portraits](/reference/lip-sync). The Rhubarb
measurements, with a script that reruns them, are in
[research/experiments/rhubarb](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/experiments/rhubarb/README.md)
on GitHub.

## What you end up with

```
output/lipsync/lord_vitriol/
  source_crop.png      the square crop of the concept
  portrait.png         the approved portrait, 1024x1024
  edits/X.png ...      one whole-image edit per shape
  mouth_X.png ...      the mouth box cut from each edit, 204x190
  manifest.json        portrait, box, shape order, overlays, fallbacks, drift
  make_mouths.json     seconds, card memory, instruction and drift per edit
  contact_sheet.png    the portrait with its box, and every mouth labelled
  concord.json         a timeline: Rhubarb's cues and the speech gate's verdict
  concord.mp4          the set playing that timeline, with its audio
```

A game draws the portrait, then the overlay for the current cue at the box's
position. The shapes are Rhubarb's letters: X rest, A closed (P, B, M), B teeth
together (K, S, T, EE), C open (EH, AE), D wide open (AA), E rounded (AO, ER),
F puckered (UW, OW, W), G upper teeth on the lower lip (F, V) and H tongue
raised (a long L). The manifest keeps the order X, A to H, and a shape the set
lacks plays its fallback, G as A, H as C and X as A, the substitutions Rhubarb
makes itself when a shape is turned off.

The whole run, with an approval after every step:

```sh
scripts/fetch_tools.py --download rhubarb
scripts/make_mouths.py --portrait-from output/assets/lord_vitriol/concept.png \
    --crop 372,65,340,340 --out output/lipsync/lord_vitriol
scripts/make_mouths.py output/lipsync/lord_vitriol/portrait.png \
    --box 410,440,204,190 --shapes XABCDEF --feather 8
scripts/compose_mouths.py --check output/lipsync/lord_vitriol/manifest.json
scripts/lipsync_cues.py lines/smith_01.ogg --out output/lipsync/lord_vitriol/smith_01.json
scripts/preview_lipsync.py output/lipsync/lord_vitriol/manifest.json \
    output/lipsync/lord_vitriol/smith_01.json
```

The `lip-sync` skill runs these one stage per turn and shows each result
([installing it for Claude](/guide/claude)).

## Start with the voice

A game ships the voice as well as the mouths, so the lines have to come from a
voice you may ship. [Text-to-speech whose lines may ship](/reference/lip-sync#text-to-speech-whose-lines-may-ship)
sorts open models and hosted services into allowed, allowed with conditions,
not allowed and unsettled. XTTS-v2, Fish Speech without a written licence from
Fish Audio, F5-TTS's pretrained weights and Piper's lessac voice are in the
not-allowed table. Those licences were read on 2026-09-15 and nothing in that
section was run.

Every line tested here was a human recording from LibriSpeech test-clean,
which [openslr.org/12](https://www.openslr.org/12/) gave as
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) when read on
2026-09-16; the attribution is in the experiment's
[README](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/experiments/rhubarb/README.md#the-audio-its-licence-and-attribution).
A male reader played on a female portrait tests timing and nothing else, and
none of it ships. No synthetic voice has been through Rhubarb in this repo.

## Rhubarb, fetched into tools/

```sh
scripts/fetch_tools.py                       # what is installed
scripts/fetch_tools.py --download rhubarb    # fetch and unpack it
scripts/fetch_tools.py --licenses
```

`tools.json` pins Rhubarb Lip Sync 1.14.0's Linux release by URL, size
(87,225,003 bytes) and sha256. The download goes to a `.part` file, is checked
against both, and only then is unpacked, and only `rhubarb`, `res/` and
`LICENSE.md` come out: 14 files, 93,614,327 bytes, in the gitignored
`tools/rhubarb/1.14.0/`. The zip's Spine extras jar is never unpacked
([licensing](/guide/licensing#lip-sync)).

Tested against the real GitHub asset, fetched into a scratch folder: a wrong
sha256 was refused after the whole 83.2MB download and the `.part` deleted,
and a 30MB partial download resumed and installed in 2.53 s. A download that
stops short keeps its `.part` for the next `--download`; that and a server
refusing to resume were tested against a local HTTP server only.

Rhubarb and ffmpeg run on the host, so the published image contains neither
this binary nor its bundled parts. The binary needs `GLIBC_2.29` and
`GLIBCXX_3.4.26` or newer, and must sit next to its `res/` folder. Whether it
runs inside the container was not tried.

## From a voice line to a timeline

```sh
scripts/lipsync_cues.py lines/smith_01.ogg                  # reads lines/smith_01.txt
scripts/lipsync_cues.py lines/smith_01.ogg --text "No."
scripts/lipsync_cues.py lines/ --out output/lipsync/smith   # a whole folder
```

`scripts/lipsync_cues.py` converts the line with ffmpeg to 16 kHz mono WAV,
runs Rhubarb with a trace log, gates the result, and writes Rhubarb's JSON with
fields around it: the transcript, the audio path relative to the timeline, the
exact Rhubarb and ffmpeg commands, and the gate's verdict. The log goes beside
it. Ogg Vorbis and FLAC input were run in the last round of tests; MP3, Opus,
M4A and AAC were not.

### One thread, always

With more than one recognition thread, the same command gives different
files. Rerun on 2026-09-16 on LibriSpeech 6930-75918-0001 (14.22 s, 43 words),
five runs with Rhubarb's default threads gave 3 different cue files, 85 and 87
cues, 0.5 to 2.4% of the running time apart, and five with `-d --threads 2`
gave 2. Five runs on one thread were byte-identical, with and without a
transcript. So the script always passes `--threads 1`.

One thread costs time on a long line. The script took 11.24 s for the 14.22 s
line, with the host's load average about 7. In `reproduce.py`, one thread
peaked at 157.6 MiB on that line, and lines of 3.50 s and 5.02 s took 2.88 s
and 3.63 s.

### Give it the transcript

Rhubarb's default recogniser still listens to the words with a transcript, but
prefers the transcript's. Without one it made 9 word edits against the long
line's 43-word transcript, a 20.9% word error rate, and with one it made none.
The transcript changed 28 of 85 cues and 8.3% of the running time in that run. That figure
comes from a multi-threaded run and moved with it: two other runs the same day
gave 37 of 85 and 39 of 87. Whether the cues became more accurate was not
measured.

The transcript is the `.txt` beside the audio, `--text` or `--text-file`, and
must be UTF-8. Given any other encoding, Rhubarb itself exits 1 with
`File encoding is not ASCII or UTF-8.`, so the script refuses first and says
so.

### The speech gate

::: warning Rhubarb takes noise for speech
Rhubarb's voice detector took ten seconds of white noise for speech, and
returned 4 cues, one of them a G held for 9.85 s. Its phonetic recogniser cut
the same noise into B cues of 3.48, 2.45, 1.75 and 0.84 s with short C cues
between.
:::

The script refuses a line, exits 3 and writes nothing for it, on either of two
checks read from the trace log:

- **Words.** The word error rate between the transcript and the words heard is
  above 60%. The three LibriSpeech lines scored 0% against their own
  transcripts, and 0001 with one word changed scored 7.0%. Given another
  line's transcript they scored 90.9% to 500%, and two 15 s music excerpts
  given 0001's transcript scored 83.7% and 93.0%.
- **A flat mouth.** The non-X cues of 1.0 s or more, added up, cover more than
  50% of the voiced time. On speech at normal speed, under steady pink noise
  and with a vowel stretched 16 times, no non-X cue reached 1.0 s (the longest
  was 0.98 s). Speech slowed to half speed reached 1.37 s, covering 13.5%.
  Loud white, pink, brown and velvet noise and a -6 dBFS sine covered 76.8% to
  99.5%, and all 18 runs were refused.

The first version of the flat-mouth check looked only at the longest single
cue and refused at 75%. The phonetic recogniser's noise got through it,
because its longest cue covered only 34.8% of the voiced time. The same noise's
long cues add up to 76.8%, which the summed check refuses.

What gets through, and what is refused, near the line:

| Input | Recogniser and transcript | Long cues cover | Gate |
|---|---|---|---|
| 3.5 s line, then 2 s of white noise | either | 38.1% to 39.3% | passed, with a warning |
| The same, 4 s of noise | either | 50.6% to 55.4% | refused |
| The same, 10 s of noise | either | 76.0% to 79.2% | refused |
| 15 s of generated battle music | default, none | 51.0% | refused |
| The same | phonetic | 19.3% | passed, with a warning |
| 15 s of generated forest ambience | either, none | 0% | passed |
| The 3.5 s line slowed to half speed | default, its own | 0% (word error rate 87.5%) | refused on words |

The noise tails and slowed speech come from `reproduce.py`'s fixtures; the
music excerpts were run through the script with `--force`. So music can pass,
and very slow delivery can fail. Keep music, ambience and sound effects away
from Rhubarb, and give every line its transcript. `--force` writes a refused
line's timeline anyway, with `"passed": false` in its `gate` block.

### Other languages

The default recogniser is English only. `-r phonetic` is Rhubarb's
language-independent recogniser, and it ignores a transcript, so the script
reads none, passes none and writes `"text": null`. Only the flat-mouth check
guards a phonetic line. On the long line it took 1.00 s against the default's
7.02 s and gave 102 cues using all nine shapes. Whether those shapes are right
was not measured, and no line in another language has been run.

### Frames, only for a baked animation

An engine that plays cue times needs no frames. For a frame-based animation,
`--fps N` adds one shape per frame, chosen by `--rule`:

- `midpoint`, the default: the cue playing at the frame's midpoint.
- `closure`: as midpoint, except that a frame any A cue overlaps shows A,
  because a lost P, B or M closure is the likeliest drop to show.
- `share`: the cue with the largest overlap of a window from the frame's
  start, one frame or 0.08 s long, whichever is longer.

Don't ask Rhubarb's own `dat` export for sprite rates: at 12 fps it exits 1
with `[Fatal] Application terminating with error: Frame rate must be between
24 and 100 fps.`

On the long line on one thread, 36 of 87 cues are shorter than a 12 fps frame.
At 12 fps midpoint dropped 4 of them, closure 7 and share 4, and none dropped
an A cue. Closure's seven include a 0.13 s C whose frames went to A.

`share` and `midpoint` first broke exact ties in opposite directions, and at
10 fps that made them differ in 8 frames. They now both give a tie to the later
cue. On the same line share then matched midpoint in every frame from 8 to
12.5 fps, except 2 phonetic frames at 9 fps, and differed at 6 fps and from
15 fps up. None of the three rules has been judged on a portrait.

### Before there is a voice

```sh
scripts/lipsync_cues.py --text-only lines/smith_01.txt --fps 12
```

This writes the same timeline shape with no audio: C, B, D, B repeating every
0.14 s for as long as the text would take at 15.6 characters per second, then
X. The interval is the median cue on the three LibriSpeech lines (0.14 s over
142 cues), and the speed is their 354 characters over 22.74 s. It writes to
`output/lipsync/text-only/` and refuses to overwrite a timeline made from
audio. The flap has not been judged on a portrait.

## The portrait

```sh
scripts/make_mouths.py --portrait-from output/assets/lord_vitriol/concept.png \
    --crop 372,65,340,340 --out output/lipsync/lord_vitriol
```

This crops the approved concept, keeps the crop as `source_crop.png`, and edits
it with `img_edit_qwen.json` at denoise 1.0, with `prompts/mouths/portrait.txt`:
sharpen it, close the lips, keep everything else. Then it stops, so that a
person approves the portrait and chooses the box. It never replaces an existing
`portrait.png`.

**Crop a square.** The graph's FluxKontextImageScale node resizes every input
to the nearest of its trained sizes, and crops the centre when the aspect ratio
differs. A ComfyUI probe of that node gave:

| Input | Edit comes back at |
|---|---|
| 341x341 | 1024x1024 |
| 700x900 or 1104x1472 | 880x1184 |
| 1024x768 | 1184x880 |
| 1600x900 | 1392x752 |
| 900x1600 | 752x1392 |
| 512x1536 | 672x1568 |
| 2000x1000 | 1456x720 |

The 340x340 crop came back at 1024x1024 with the lips closed. The edit took
136 s and then 154.4 s, both on 2026-09-16, and the second run, at the same
crop, seed and instruction, was pixel-identical to the first. The card peaked
at 15,224 and 15,221 MiB.

The first portrait was queued with `run_workflow.py` directly, while a Blender
job was running in the same container, which the shared machine's rules
forbid. The portrait step moved into `make_mouths.py` so that it waits like the
mouth edits ([one job at a time](#one-job-at-a-time)).

## The mouth box

The box goes round the mouth **and the whole chin, with room for the jaw to
drop**. Only the box of each edit is kept, so drift in a 6 px ring just outside
it says how well a mouth meets the portrait: the mean difference, in 0 to 255
levels averaged over R, G and B, between the edit and the portrait.

The first box, 184x160 at 420,444, stopped 36 px under the resting chin. Both
boxes, composed from the set's own edits with `compose_mouths.py` on
2026-09-16:

| Box | X | A | B | C | D | E | F | Worst side |
|---|---|---|---|---|---|---|---|---|
| 184x160 at 420,444 | 1.53 | 1.47 | 1.48 | 1.61 | 3.04 | 1.68 | 2.10 | D bottom, 5.41 |
| 204x190 at 410,440 | 1.54 | 1.48 | 1.50 | 1.57 | 1.74 | 1.59 | 1.58 | C bottom, 1.86 |

The small box cut D's lowered chin along its bottom edge. The larger one
brought every shape near X's 1.54. X's edit asks for the resting mouth the
portrait already has, so about 1.5 is the floor a whole-image edit leaves.

`make_mouths.py` checks a box before any GPU work: inside the portrait, and
inside the part of the edit the node's centre crop keeps. It reads the node's
size list from the running container for that. A 700x900 portrait with a box
at its left edge is refused with `the edit graph returns 880x1184 for this
700x900 portrait and keeps only its 668x900 centre at 16,0, which cuts the
mouth box ...`. `--dry-run` runs the checks and prints the instructions
without queueing anything.

## Nine mouths

```sh
scripts/make_mouths.py output/lipsync/lord_vitriol/portrait.png \
    --box 410,440,204,190 --shapes XABCDEF --feather 8
```

For each shape this runs `img_edit_qwen.json` once on the portrait, at seed 0,
with that shape's instruction from `prompts/mouths/shapes.txt`, and keeps the
result as `edits/<S>.png`. Then `compose_mouths.py` cuts the box out of each
edit, measures drift and writes the manifest. The repo has no inpainting model
for Qwen-Image, so each edit re-diffuses the whole portrait and only the box is
kept.

Each edit took 143.4 to 157.4 s, so nine take about 23 minutes, and the whole
card peaked at 15,178 to 15,344 MiB during them, other work on it included.
A shape whose edit exists is skipped, so a stopped run resumes.

### Denoise 0.85, not the graph's 1.0

D, wide open, was the shape that showed it. On the 184x160 box at seed 0, in
an earlier round that was not rerun:

| D instruction | Denoise | Drift | Worst side | What happened |
|---|---|---|---|---|
| First wording | 1.0 | 6.49 | bottom, 15.59 | The chin dropped out of the box |
| Revised wording | 1.0 | 19.70 | top, 50.15 | The whole face became a shout |
| Revised wording | 0.85 | 3.04 | bottom, 5.41 | The mouth opened; this is the D that ships |

At 1.0 the model redraws the face, as it redraws the style in
[concept art](/guide/concept-art#denoise-behaves-like-a-cliff-not-a-dial).
That is one shape on one face; a shape that barely changes at 0.85 may need
more.

### C's first wording opened as far as D

The first C instruction asked for an opening of medium height. Counting the
pixels of each overlay that differ from `mouth_X.png` by more than 40 levels,
C opened as far as D: 8,860 pixels against 8,606. A review of that set found
it playing as a gaping "oh" on 15 of the test clip's 85 frames. The instruction
was rewritten to ask for a slight parting, with the edges of the upper front
teeth showing over a narrow dark gap about as tall as those teeth. The new C
took 154.2 s:

| Overlay | Pixels over 40 levels from X | Mean difference from X |
|---|---|---|
| A | 0 | 0.68 |
| F | 1,641 | 6.42 |
| B | 2,384 | 8.02 |
| C, second wording | 4,443 | 13.35 |
| E | 4,730 | 14.26 |
| D | 8,606 | 24.64 |
| C, first wording | 8,860 | 25.27 |

That halved C, and moved it next to E: the two are 4.64 levels apart, with
1,032 pixels differing by more than 40. At contact-sheet size E is only
slightly taller and rounder, so the pair reads as two versions of C more than
as C and a rounded E. E was not remade.

### A looks like X

After two wordings, pressed lips came out the same as the resting mouth, 0.68
levels apart inside the box. Nothing plays wrong, but P, B and M show no
closure.

### G and H were left out

Two wordings each failed. G, upper teeth on the lower lip, showed both rows of
teeth, and H, the tongue raised behind the upper teeth, put the tongue out past
the lips. Both were moved out of `edits/`, so the set plays G as A and H as C.
A third wording, or a higher denoise, was not tried for A, G or H.

Run with the default `--shapes`, `make_mouths.py` would make G and H again at
the same seed with the same instructions, and put them back in the set. So
this set is made with `--shapes XABCDEF`.

## Checking the set

```sh
scripts/compose_mouths.py --check output/lipsync/lord_vitriol/manifest.json
scripts/preview_lipsync.py output/lipsync/lord_vitriol/manifest.json
```

`--check` pastes every overlay onto the portrait and fails unless no pixel
outside the box changes, every overlay is the box's size and A to F are
present. On the set it passed, with 0 pixels changed outside the box for each
of X and A to F.

`--feather 8` fades each edit into the portrait over the box's outer 8 px,
inside the box only, so the outside stays untouched. It was chosen over a hard
edge by eye.

A portrait that is not at a trained size comes back from the edit graph resized
and centre-cropped, and `compose_mouths.py` puts each edit back where it came
from. On real node output for 700x900, 1600x900 and 1024x768 inputs, the undo
landed within 0.03 to 0.10 levels of the source; 3 px off it measured 3.58 to
4.30. Odd-sized portraits were not run through a real mouth edit.

The numbers say nothing about whether a mouth reads as its shape. That is what
`contact_sheet.png` is for: the portrait with its box in red, and every mouth
labelled with its sounds, its drift and, given a timeline, how many frames it
plays. Judge it one shape at a time.

## The preview

```sh
scripts/preview_lipsync.py output/lipsync/lord_vitriol/manifest.json \
    output/lipsync/lord_vitriol/concord.json
scripts/preview_lipsync.py output/lipsync/lord_vitriol/manifest.json \
    output/lipsync/lord_vitriol/concord_12fps.json --label --no-sheet
```

This writes an H.264 MP4 beside the timeline, with the line's audio when the
timeline's `audio` file exists, at the timeline's `fps` or 24. With `frames`
in the timeline it plays them as they are; otherwise it samples the cues at
each frame's midpoint. `--label` prints the shape and time on every frame.

On LibriSpeech 6930-75918-0000, the 22 cues gave 84 frames at 24 fps, held on
X for one more to cover the audio: X 10, A 4, B 29, C 15, D 5, E 13, F 5 and
H 4, played as C. Decoding the three full-size MP4s and matching every frame to
its nearest overlay gave 85 of 85, 43 of 43 and 75 of 75 frames as the timeline
said.

Every frame's shape is resolved before ffmpeg starts, and the MP4 replaces
the output only when ffmpeg succeeds. A timeline naming a shape the set cannot
play exits 1 and leaves the earlier MP4 byte-identical.

Nobody has judged the sync by watching with sound. Only frame order and labels
were checked, with the audio muxed from the start.

## One job at a time

Blender and ComfyUI share one container and one card here. Before every edit,
the portrait's included, `make_mouths.py` polls every 30 s until no Blender job
(`python3 -c`) is running in the container and ComfyUI's queue is empty. A
size probe during this work waited about 37 minutes on other people's Blender
renders before it could queue. Queue these edits through `make_mouths.py`
rather than `run_workflow.py`.

Two jobs can still collide: another Blender job can start in the seconds
between the check and the queueing. `make_mouths.py` takes ComfyUI's address
from `COMFY_URL`, as `run_workflow.py` does.

## What was not tested

- **Sync by eye and ear.** Frame order was checked against the timeline, not
  watched.
- **Any other portrait or seed.** Every drift, denoise and opening figure above
  is one face at seed 0.
- **A synthetic voice, another language, or a line with music or room noise
  under it.** The noise and slowed-speech fixtures were made with ffmpeg and
  rubberband, not spoken, and music was two 15 s excerpts.
- **Rhubarb in the container**, and several lines run at once.
- **A game size.** The set stays at 1024x1024; nothing here scales it down.
- **An engine reading the manifest or the timeline.**
- **The frame rules and the text-only flap on a portrait.**
- `make_mouths.py`'s `--timeout` and `--retries` paths, and odd-sized or RGBA
  portraits through a real edit.
