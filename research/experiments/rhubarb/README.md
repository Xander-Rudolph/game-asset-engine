# Rhubarb Lip Sync, measured again

`reproduce.py` reruns the measurements behind [Rhubarb on this machine](../../../docs/reference/lip-sync.md#rhubarb-on-this-machine), first run on 2026-09-15, and prints each number next to the published one. It also measures what `scripts/lipsync_cues.py` rests on and the note did not: the inputs of its speech gate on real and made-up audio, how its frame rules behave, and the basis of its text-only flap.

The [lip sync note](../../../docs/reference/lip-sync.md) gives the rerun's numbers where they differ from its own, and cites these additions in [The timeline file](../../../docs/reference/lip-sync.md#the-timeline-file); the [Source Filmmaker note](../../../docs/reference/source-filmmaker.md#what-to-build) cites the frame sweep for the `share` rule. On the docs site they are [/reference/lip-sync](https://xander-rudolph.github.io/game-asset-engine/reference/lip-sync) and [/reference/source-filmmaker](https://xander-rudolph.github.io/game-asset-engine/reference/source-filmmaker).

## What it measures

All on the host, from the official Linux release that `scripts/fetch_tools.py --download rhubarb` unpacks into `tools/rhubarb/1.14.0/`. The timed runs go one process at a time, and wall time, CPU time and peak resident memory come from `os.wait4` for each process on its own.

- **The note's table** on LibriSpeech test-clean 6930-75918-0001 (14.22 s, 43 words): the default recogniser, with the transcript (`-d`), with the transcript on one thread, and `-r phonetic`.
- **Word error rate** with and without the transcript, from the `##word` lines of a Trace log, and how much the transcript changes the cues.
- **The short lines** 6930-75918-0000 (3.50 s) and 0002 (5.02 s), which run on one thread by default.
- **Peak memory**, **run-to-run determinism** (five runs each of the default, `-d --threads 2`, `--threads 1` and `-d --threads 1`), **cues shorter than a 12 fps and a 24 fps frame**, the **dat exporter at 12 fps**, and **`--extendedShapes ""`**.
- **Non-speech**: 10 s of digital silence, a 440 Hz sine peaking at -18 dBFS, and white noise at amplitude 0.3, from ffmpeg's `anullsrc`, `sine` and `anoisesrc` sources.
- **Additions, not in the note**, all on one thread:
  - the speech gate's inputs for every line given its own transcript, none, and each other line's;
  - the gate on made-up audio with both recognisers (the list is under [The gate on made-up audio](#the-gate-on-made-up-audio)). These runs are not timed and run `--jobs` at a time;
  - which cues each `--fps 12` rule drops, and in how many frames `share` and `midpoint` differ from 6 to 30 fps;
  - the median cue length and characters per second of the three lines.

Word error rate here is the word edit distance between the transcript's words and the words PocketSphinx heard, over the transcript's word count, lower-cased, with fillers such as `<s>`, `<sil>` and `[BREATH]` and markers such as `(2)` removed. "Cues changed" counts cues of the run with a transcript that do not appear, with the same start, end and shape, in the run without; "time changed" is the share of 10 ms steps whose shape differs. "Long share" is what the gate refuses on: the non-X cues lasting 1.0 s or more, added up, over the voiced time that Rhubarb's voice detector logs.

## The audio, its licence and attribution

The speech is three utterances from the **LibriSpeech ASR corpus** (openslr SLR12) by Vassil Panayotov, Guoguo Chen, Daniel Povey and Sanjeev Khudanpur, derived from LibriVox audiobooks, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). On 2026-09-16 [openslr.org/12](https://www.openslr.org/12/) read "License: CC BY 4.0" and the Hugging Face dataset [openslr/librispeech_asr](https://huggingface.co/datasets/openslr/librispeech_asr) carried the `cc-by-4.0` tag at revision `71cacbfb7e2354c4226d01e70d77d5fca3d04ba1`.

`reproduce.py` finds them through the Hugging Face datasets-server rows API (config `clean`, split `test`, rows 0 to 2), checks each FLAC and each transcript against a sha256 pinned in the script, and caches them in `input/_devtools/librispeech/`, which is gitignored. Nothing from the corpus is committed: `results.json` holds numbers only, plus the words heard in white noise. The script converts the FLACs to 16 kHz mono PCM WAV, and for the gate it slows them, stretches a vowel, mixes in noise and appends noise, into `input/_devtools/librispeech/fixtures/`. The clip runs further down also cut single words out of them. None of these changes is shipped.

## How to run it

```sh
scripts/fetch_tools.py --download rhubarb
research/experiments/rhubarb/reproduce.py
research/experiments/rhubarb/reproduce.py --repeats 3                    # fewer repeat runs
research/experiments/rhubarb/reproduce.py --skip-determinism --jobs 8    # no repeats, 8 gate runs at a time
```

It needs ffmpeg on the PATH, with the `rubberband` filter for the slowed and stretched fixtures (without it they are skipped and `results.json` lists them under `gate_fixtures.skipped`), and, on the first run only, network access. The full run took 457.9 s on 2026-09-16 and wrote `results.json` beside the script. `--skip-determinism --jobs 8` was run once as a check: it took 245.7 s, gave the same gate-fixture rows and frame sweep as the full run, and its `results.json` was then replaced by the full run's; `--repeats` with a value other than 5 was not tried. Wall times move with whatever else the host is doing: the load average was 4.39 at the start of the full run, with other work running.

## The rerun on 2026-09-16

Rhubarb 1.14.0, i7-14700K host with 28 logical CPUs, Python 3.13.12, ffmpeg 8.0.1. Single runs unless repeats are given.

| Measurement | Published (2026-09-15) | Rerun (2026-09-16) |
|---|---|---|
| Default recogniser: wall, CPU, cues, shapes | 6.51 s, 11.97 s, 85 or 87, ABCEFGHX | 7.02 s, 12.76 s, 85, ABCEFGHX |
| With transcript | 6.27 s, 11.66 s, 85 or 87, ABCEFGHX | 9.65 s, 17.26 s, 85, ABCEFGHX |
| One thread, with transcript | 11.02 s, CPU not checked | 11.52 s, 11.42 s, 87, ABCEFGHX |
| Phonetic recogniser | 1.01 s, 1.36 s, 101 or 102, all nine | 1.00 s, 1.40 s, 102, all nine |
| Word error rate without transcript | 20.9% (9 edits, 43 words) | 20.9% (9 edits, 43 words) |
| Word error rate with transcript | 0% | 0% |
| Cues changed by the transcript | 28 of 85, 8.3% of the time | 28 of 85, 8.3% of the time |
| Phonetic speed-up in wall time | 6.5 times (6.2 against the transcript run) | 6.99 times (9.62) |
| Recognition threads on the long line | 2 | 2 |
| 0000 and 0002 with transcript, one thread | 2.89 s and 3.51 s (0.83 and 0.70 times real time) | 2.88 s and 3.63 s (0.82 and 0.72) |
| Peak memory, short lines on one thread | about 156 MiB | 155.8 and 155.4 MiB |
| Peak memory, long line on two threads | about 311 MiB | 304.4 MiB |
| Peak memory, long line on one thread | not measured | 157.6 MiB |
| Share of the line in shape B | about 44% | 43.7% |
| D used on the long line | never | never |
| Shortest and median cue | 0.06 s and 0.14 s | 0.06 s and 0.14 s |
| Cues under a 12 fps frame, with transcript | 32 of 85, from a run on two threads | 32 of 85 on two threads; 36 of 87 on one thread |
| Cues under a 12 fps frame, phonetic | 49 of 102 | 49 of 102 |
| Cues under a 24 fps frame | none | none |
| `-f dat --datFrameRate 12` | exit 1, `Frame rate must be between 24 and 100 fps.` | exit 1, `[Fatal] Application terminating with error: Frame rate must be between 24 and 100 fps.` |
| `--extendedShapes ""` | 86 cues, A from 0.65 s to 2.20 s | 86 cues, A from 0.65 s to 2.20 s |
| Silence and 440 Hz sine | one X cue each, about 0.13 s | one X cue each, 0.13 s wall, 0.03 s CPU, 25.4 MiB |
| White noise, default recogniser | heard "think", 6.2 s CPU, one 9.90 s B cue between two short X | heard "of", 11.09 s CPU, 4 cues (B, G, X), longest a 9.85 s G |
| White noise, phonetic | 9 cues | 8 cues (B, C, X), longest 3.48 s |
| Five runs, `-d --threads 2` | 3 different files, 0.5 to 2.4% of the time | 2 different files, 1.9% apart |
| Five runs, `--threads 1`, without and with `-d` | byte-identical (six runs with `-d`) | byte-identical, both |
| Five runs, default threads | 85 or 87 cues | 3 different files, 85 and 87 cues, 0.5 to 2.4% apart |

**What held.** Both word error rates, the thread count, the cues changed by the transcript, the B share, the shortest and median cue, the sub-frame counts, the dat refusal, the `--extendedShapes` result, and the silence and sine results matched the note, and the short lines' times and the memory were within 4% of it. One thread again gave byte-identical files; two threads again did not.

**What depends on the run.** The rows computed from multi-threaded runs (cues changed by the transcript, and cues under a 12 fps frame with the transcript or phonetic) hold only when those runs return the same one of their two cue sets as the note's did. They did this time. The first rerun earlier the same day got 87 cues from the default run, and so 37 of 85 cues changed and 10.1% of the time. The `--skip-determinism` check got 87 from the transcript run: 39 of 87 cues changed, 10.2% of the time, and 36 of 87 under a 12 fps frame. The one-thread count, 36 of 87, does not move.

**What moved, and why.**
- The run with the transcript took 9.65 s instead of 6.27 s, and 17.26 s of CPU instead of 11.66 s. It was a single run with other work on the host. The five repeat runs with `-d --threads 2`, which also recognise on two threads, had a median of 6.39 s, and the phonetic speed-up against it is inflated for the same reason.
- Five runs with `-d --threads 2` gave 2 different files, not 3; the note's range is from runs on a different day.
- The white noise is a different sample: the note's command set no seed, and this one uses `seed=1`. On it the recogniser heard another word, used more CPU and chose G rather than B, but still returned one cue across nearly the whole 10 s.

## Additions

### Inputs of the speech gate

From `reproduce.py`, on one thread with a Trace log, using `lipsync_cues.py`'s own parsing. "Against the true words" scores the words heard against the line's real transcript, whatever was given. No cue in any of these speech runs reached 1.0 s, so every long share was 0%.

| Line | Transcript given | Error against the given text | Against the true words | Longest non-X cue | Its share of voiced time |
|---|---|---|---|---|---|
| 0000 | its own | 0% | 0% | 0.28 s | 9.2% |
| 0000 | none | | 37.5% | 0.49 s | 16.2% |
| 0000 | 0001's | 93.0% | 37.5% | 0.49 s | 16.2% |
| 0000 | 0002's | 90.9% | 50.0% | 0.49 s | 16.2% |
| 0001 | its own | 0% | 0% | 0.63 s | 4.6% |
| 0001 | none | | 20.9% | 0.70 s | 5.1% |
| 0001 | 0000's | 500% | 14.0% | 0.63 s | 4.6% |
| 0001 | 0002's | 372.7% | 11.6% | 0.70 s | 5.1% |
| 0002 | its own | 0% | 0% | 0.35 s | 7.2% |
| 0002 | none | | 18.2% | 0.35 s | 7.2% |
| 0002 | 0000's | 125% | 27.3% | 0.42 s | 8.7% |
| 0002 | 0001's | 95.3% | 27.3% | 0.42 s | 8.7% |
| White noise | none | | | 9.85 s | 98.5% |
| 440 Hz sine, -18 dBFS | none | | | no non-X cue | |

A wrong transcript did not make the recogniser hear the wrong words: against the given text it scored 90.9% or more, while against the true words it stayed between 11.6% and 50.0%, sometimes better and sometimes worse than with no transcript. So a mismatch shows up as a high error against the given text.

### The gate on made-up audio

From `reproduce.py`, each fixture through `lipsync_cues.gate` on one thread. A cell gives the longest non-X cue, the long share (non-X cues of 1.0 s or more over voiced time) and, with a transcript, the word error rate. The fixtures:

- **0000 and 0001 slowed to half speed** with ffmpeg's `rubberband=tempo=0.5`.
- **The vowel of "place"** (2.00 to 2.15 s in 0000) stretched 8 and 16 times with `rubberband`, the rest of the line untouched.
- **0001 under steady pink noise**, `anoisesrc` amplitude 0.05, seed 7, mixed in.
- **0000 followed by white noise** of 2, 4 and 10 s (amplitude 0.3, seed 5).
- **10 s of noise**: white at amplitude 0.3 with seeds 1 to 5; pink and brown at 0.5 (seeds 2 and 3); velvet (seed 6) and blue (seed 4) at 0.3; white at 0.03 (seed 1).
- **10 s of a 440 Hz sine** peaking at -18 dBFS, and 12 dB louder, at -6 dBFS.

| Fixture | Default recogniser, right transcript | Default, no transcript | `-r phonetic` |
|---|---|---|---|
| 0000 | (above) | (above) | 0.35 s, 0.0% |
| 0001 | (above) | (above) | 0.70 s, 0.0% |
| 0002 | (above) | (above) | 0.54 s, 0.0% |
| 0000 slowed | 0.91 s, 0.0%, WER 87.5%, **refused** | 0.72 s, 0.0% | 0.77 s, 0.0% |
| 0001 slowed | 1.27 s, 8.8%, WER 30.2% | 1.37 s, 13.5% | 0.87 s, 0.0% |
| Vowel stretched 8 times | 0.77 s, 0.0%, WER 25.0% | 0.49 s, 0.0% | 0.42 s, 0.0% |
| Vowel stretched 16 times | 0.98 s, 0.0%, WER 37.5% | 0.70 s, 0.0% | 0.52 s, 0.0% |
| 0001 under pink noise | 0.68 s, 0.0%, WER 14.0% | 0.51 s, 0.0% | 0.85 s, 0.0% |
| 0000 and 2 s of noise | 1.93 s, 38.1%, WER 12.5% | 1.93 s, 38.1% | 1.99 s, 39.3% |
| 0000 and 4 s of noise | 3.91 s, 55.4%, WER 12.5%, **refused** | 3.91 s, 55.4%, **refused** | 3.57 s, 50.6%, **refused** |
| 0000 and 10 s of noise | 9.92 s, 76.0%, WER 12.5%, **refused** | 9.92 s, 76.0%, **refused** | 10.34 s, 79.2%, **refused** |
| White noise, seed 1 | | 9.85 s, 98.5%, **refused** | 3.48 s, 76.8%, **refused** |
| White noise, seed 2 | | 9.95 s, 99.5%, **refused** | 7.12 s, 94.3%, **refused** |
| White noise, seed 3 | | 9.66 s, 96.6%, **refused** | 9.57 s, 95.7%, **refused** |
| White noise, seed 4 | | 9.88 s, 98.8%, **refused** | 6.30 s, 95.7%, **refused** |
| White noise, seed 5 | | 9.43 s, 94.3%, **refused** | 6.42 s, 91.5%, **refused** |
| Pink noise | | 9.95 s, 99.5%, **refused** | 7.12 s, 94.3%, **refused** |
| Brown noise | | 9.73 s, 97.3%, **refused** | 9.57 s, 95.7%, **refused** |
| Velvet noise | | 8.85 s, 89.6%, **refused** | 5.58 s, 99.0%, **refused** |
| Sine, -6 dBFS | | 9.88 s, 98.8%, **refused** | 9.78 s, 97.8%, **refused** |
| Quiet white noise | | no voice found | no voice found |
| Blue noise | | 0.21 s, 0.0% (0.4 s voiced) | 0.26 s, 0.0% |
| Sine, -18 dBFS | | no voice found | no voice found |

Pink noise and white noise with the same seed gave identical cues, though the files differ; that was checked by checksum.

**Why the cues are added up.** On white noise, the phonetic recogniser's longest single cue covered as little as 34.8% of voiced time (seed 1: B cues of 3.48, 2.45, 1.75 and 0.84 s with short C cues between). The gate used to refuse only a single cue covering 75% or more, so this noise passed. Adding up the cues of 1.0 s or more gives 76.8%.

**Where the thresholds come from.** On speech at normal speed, under steady noise and with a stretched vowel, no non-X cue reached 1.0 s, so the long share was 0%. The lines slowed to half speed reached 1.37 s and a long share of 13.5%. Loud noise and the loud sine gave 76.8% to 99.5% with either recogniser. `lipsync_cues.py` refuses a long share above 50%, the "most of the voiced time" its gate was specified with, and warns about any non-X cue of 1.0 s or more below that. A 2 s noise tail on a 3.5 s line (38 to 39%) gets through with the warning.

**A false refusal.** 0000 slowed to half speed scored 87.5% against its own transcript and was refused on words; 0001 slowed scored 30.2%. Stretching with `rubberband` is not the same as a slow speaker, but very slow delivery may fail the word check.

### Clips through `lipsync_cues.py`

These runs used `scripts/lipsync_cues.py --force` with the gate as it now stands; they are not in `reproduce.py`. The music is this repository's own generated output under `output/music/`, which is not in git, so a rerun needs tracks of its own.

```sh
L=input/_devtools/librispeech
ffmpeg -i $L/6930-75918-0000.wav -ss 0.45 -to 1.25 concord.wav
ffmpeg -i $L/6930-75918-0000.wav -ss 2.78 -to 3.45 tents.wav
ffmpeg -i $L/6930-75918-0002.wav -ss 0.10 -to 1.40 congratulations.wav
ffmpeg -i output/music/battle_1_00001.flac -ss 30 -t 15 music_battle.wav
ffmpeg -i output/music/ambient_forest_00001.flac -ss 30 -t 15 music_forest.wav
ffmpeg -f lavfi -i "sine=frequency=440:sample_rate=16000:duration=10,volume=12dB" -ac 1 -c:a pcm_s16le sine_loud.wav
sed 's/SUPPER/DINNER/' $L/6930-75918-0001.txt > near_0001.txt
scripts/lipsync_cues.py concord.wav --text "Concord" --force --out out/concord.json
scripts/lipsync_cues.py music_battle.wav --force --out out/music_battle.json
scripts/lipsync_cues.py music_battle.wav -r phonetic --force --out out/music_battle_ph.json
scripts/lipsync_cues.py music_battle.wav --text-file $L/6930-75918-0001.txt --force --out out/music_battle_text.json
scripts/lipsync_cues.py $L/6930-75918-0001.wav --text-file near_0001.txt --force --out out/near_0001.json
# and the same pattern for tents.wav, congratulations.wav, music_forest.wav and sine_loud.wav
```

| Clip | Recogniser and transcript | Word error rate | Longest non-X cue | Long share | Gate |
|---|---|---|---|---|---|
| "concord", 0.80 s | default, "Concord" | 0% | 0.28 s | 0% | passed |
| "tents", 0.67 s | default, "tents" | 0% | 0.27 s | 0% | passed |
| "congratulations", 1.30 s | default, "Congratulations" | 0% | 0.21 s | 0% | passed |
| 0001, 14.22 s | default, its own with SUPPER changed to DINNER | 7.0% (3 edits) | 0.70 s | 0% | passed |
| Battle music, 15 s, peak -0.4 dBFS | default, none | | 4.59 s | 51.0% (7.19 of 14.09 s) | refused |
| Battle music | phonetic | | 1.40 s | 19.3% | passed, with a warning |
| Battle music | default, 0001's | 83.7% | 3.50 s | 43.3% | refused on words |
| Forest ambience, 15 s, peak -0.4 dBFS | default, none | | 0.91 s | 0% | passed |
| Forest ambience | phonetic | | 0.91 s | 0% | passed |
| Forest ambience | default, 0001's | 93.0% | 1.47 s | 13.7% | refused on words |
| 440 Hz sine, peak -6.1 dBFS | default, none | | 9.88 s (C) | 98.8% | refused |

**Music can pass the gate.** Without a transcript only the flat-mouth check runs. The forest ambience passed it with both recognisers and no warning. The battle music was refused at 51.0%, just over the line, and passed at 19.3% with `-r phonetic`. Given 0001's transcript, both were refused on words.

### Frames

On 0001 with its transcript on one thread (87 cues, 36 of them shorter than a 12 fps frame), `scripts/lipsync_cues.py --fps 12` wrote 171 frames with each rule:

| Rule | Cues dropped | A cues dropped |
|---|---|---|
| midpoint | 4 of 87 (three C and one B, each 0.07 s) | 0 of 7 |
| closure | 7 of 87 (six of 0.07 s, and a 0.13 s C whose frames A cues took) | 0 of 7 |
| share | 4 of 87 | 0 of 7 |

`reproduce.py` counts the same drops on its own one-thread run (`frame_rules_12fps` in `results.json`). Closure differed from midpoint in 7 frames, and share gave the same 171 frames as midpoint.

That is a measurement, not a rule. `reproduce.py` swept the frame rate on the same cues and on a one-thread phonetic run of 0001 (`fps_sweep`):

| Frame rate | Frames | Share differs from midpoint (default, phonetic) | Cues dropped by midpoint, share, closure (default) | The same, phonetic |
|---|---|---|---|---|
| 6 | 85 | 3, 10 | 24, 26, 25 | 34, 38, 38 |
| 8 | 114 | 0, 0 | 12, 12, 15 | 22, 22, 25 |
| 9 | 128 | 0, 2 | 12, 12, 16 | 15, 16, 20 |
| 10 | 142 | 0, 0 | 11, 11, 12 | 13, 13, 18 |
| 11 | 156 | 0, 0 | 8, 8, 9 | 10, 10, 16 |
| 12 | 171 | 0, 0 | 4, 4, 7 | 8, 8, 15 |
| 12.5 | 178 | 0, 0 | 1, 1, 5 | 8, 8, 13 |
| 15 | 213 | 8, 8 | 0, 0, 1 | 1, 1, 3 |
| 24 | 341 | 41, 51 | 0, 0, 0 | 0, 0, 2 |
| 30 | 427 | 61, 72 | 0, 0, 0 | 0, 0, 0 |

Up to 12.5 fps the share window, max(1/N, 0.08 s), is the frame. There, if no cue in a frame is shorter than half the frame, the cue holding the midpoint always has the largest overlap, so the two rules can differ only on an exact tie. At 6 fps half a frame is 0.083 s, longer than many cues, and at 9 fps it is 0.056 s, longer than the phonetic run's 0.05 s cues; those are the rows where share differed. Above 12.5 fps the window looks past the frame.

Ties used to break in opposite directions: midpoint gave the frame to the cue starting at the midpoint, share to the earlier cue. At 10 fps that made share differ from midpoint in 8 frames on the default cues and 12 on the phonetic ones. Share now gives an exact tie to the later cue, as midpoint does, and `--selftest` checks both on a hand-worked tie. None of this was judged on a portrait.

### The text-only flap

The median cue on the three lines with their transcripts on one thread was 0.14 s, over 142 cues, and the lines hold 354 characters in 22.74 s, 15.57 characters per second. `lipsync_cues.py --text-only` flaps every 0.14 s at 15.6 characters per second. Whether that looks right on a portrait was not checked.

## Not measured

- Whether any cue is the right mouth shape: nothing here compares cues with a person's judgement or with video.
- A real slow or sung line, synthetic voices, other languages, recordings with room noise or music under the voice, and transcripts with numbers or names outside the CMU dictionary. The slowed and stretched fixtures are made with `rubberband`, not spoken.
- Music beyond the two 15 s excerpts.
- Rhubarb inside the container; everything ran on the host.
- `--repeats` with a value other than 5.
