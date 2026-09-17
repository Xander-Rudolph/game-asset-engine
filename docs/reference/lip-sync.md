# Lip sync and talking portraits

::: tip Status: researched on 2026-09-15, partly built on 2026-09-16
Five of the eight [What to build](#what-to-build) items have now been built or tried, in part or whole, and that list says what each measured and what is still untested. [`scripts/lipsync_cues.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/lipsync_cues.py) turns a voice line into a gated timeline, with Rhubarb fetched into `tools/` by [`scripts/fetch_tools.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/fetch_tools.py) rather than put in the image. [`scripts/make_mouths.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/make_mouths.py), [`scripts/compose_mouths.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/compose_mouths.py) and [`scripts/preview_lipsync.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/preview_lipsync.py) make and play a talking portrait. [`scripts/face_rig.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/face_rig.py) adds a jaw and borrows shape keys, and `scripts/render_sheet.py` now sets shape keys per pose. [`research/experiments/rhubarb/reproduce.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/experiments/rhubarb/reproduce.py) reruns the Rhubarb measurements. The guide to using them is [talking portraits](/guide/talking-portraits). No graph was added, and Rhubarb is downloaded on demand into the gitignored `tools/`, not committed. Statements measured on 2026-09-16 while building carry no claim id; each says which script produced it, or sits in a passage that does.

Rhubarb Lip Sync was run on this machine's host (peak memory on 2026-09-16), the Blender probes ran in the repo's container, and a generated rig and sprite sheet were measured. <!-- LIP-061 LIP-064 LIP-067 LIP-068 LIP-086 LIP-153 LIP-155 LIP-170 --> Statements marked as community reports or not checked were not verified; everything else, including every licence, was read without running it. The verified claims behind this page are in [research/claims/lip-sync.json](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/claims/lip-sync.json) on GitHub.
:::

How to make a generated character appear to talk, when its rig has no jaw, its mesh has no mouth and the repo makes no speech. <!-- LIP-061 --> Source Filmmaker's phoneme system is covered in [Source Filmmaker](/reference/source-filmmaker), and Genesis faces in [DAZ Genesis](/reference/daz-genesis).

## The short answer

- **Speech to mouth shapes: Rhubarb Lip Sync.** Its code is MIT, and the non-binding summary in its [LICENSE.md](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md) says the lip sync data it makes "belongs to you alone" (checked 2026-09-15). <!-- LIP-001 --> With `--threads 1`, which a reproducible cue file needs, a 14.22 s line took 11.02 s on this machine's CPU, about 0.78 times real time. <!-- LIP-161 LIP-163 LIP-170 --> `scripts/lipsync_cues.py` runs it that way behind a speech gate.
- **No faces on the sprite sheets.** At a 128 px cell a mouth would be about 3 to 4 px wide, an estimate scaled from the warrior sheet. <!-- LIP-086 --> Measured on 2026-09-16 with `scripts/face_rig.py`, a jaw opened 20 degrees on a generated rig changed 12 pixels by 16 levels or more in a 128 px front view ([faces only read on a portrait](#faces-only-read-on-a-portrait)).
- **A talking face is a portrait:** one image, nine mouth overlays and a cue list, with no face rig. The overlay step was tried on one portrait on 2026-09-16: seven of the nine mouths were kept, and no pixel outside the mouth box changed ([tried on one portrait](#tried-on-one-portrait)).
- **The voice is the gate.** Rhubarb needs speech, and XTTS-v2 and Fish Speech without a separate written licence from Fish Audio may not be used in a game you sell, while the lessac voice in Piper's CLI examples is not cleared for one (checked 2026-09-15, see [text-to-speech](#text-to-speech-whose-lines-may-ship)). <!-- LIP-119 LIP-122 LIP-131 -->

## Speech to mouth shapes

Licences checked 2026-09-15 against the linked pages. Only Rhubarb was run.

| Tool | Gives you | Licence | Headless on Linux without a GPU |
|---|---|---|---|
| [Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync) 1.14.0 | Mouth cues A to H and X from WAV or Ogg Vorbis, with an optional transcript <!-- LIP-003 LIP-085 --> | Code: MIT. PocketSphinx and sphinxbase: CMU variation of 2-clause BSD. Acoustic model: Alpha Cephei variation of 2-clause BSD. Other bundled parts: permissive notices listed in LICENSE.md. Cue data: yours, per its non-binding summary <!-- LIP-001 LIP-002 LIP-151 LIP-152 --> | Command line; yes, measured below <!-- LIP-085 LIP-153 LIP-155 --> |
| [Montreal Forced Aligner](https://montreal-forced-aligner.readthedocs.io/en/latest/first_steps/index.html) 3.4.2 | Word and phone TextGrids from audio plus a transcript <!-- LIP-007 --> | Code: MIT. english_mfa v2.0.0 to v3.1.0, english_us_arpa v2.0.0 to v3.0.0 and all 27 English dictionaries: CC BY 4.0 ([mfa-models catalogue](https://mfa-models.readthedocs.io/en/latest/dictionary/English/index.html)) <!-- LIP-006 --> | Command line; yes, alignment has no CUDA flag <!-- LIP-007 --> |
| [Gentle](https://github.com/lowerquality/gentle) | Word times and phone durations, as JSON <!-- LIP-009 --> | Code: MIT. Kaldi: Apache-2.0. Model zip: no licence file; [kaldi-asr.org](https://kaldi-asr.org/models.html) says its models "may be downloaded and used for any purpose" <!-- LIP-008 LIP-009 --> | Command line or REST server; GPU use not checked; Docker image last updated 2017-06-05 <!-- LIP-009 --> |
| [WhisperX](https://github.com/m-bain/whisperX) on [Whisper](https://github.com/openai/whisper) | Word timestamps; Whisper's own are labelled "(experimental)" <!-- LIP-010 LIP-011 --> | WhisperX code: BSD-2-Clause. Default English alignment weights: MIT. OpenAI Whisper code and original checkpoints: MIT. The faster-whisper, VAD and diarisation weights it loads: their own licences, not checked <!-- LIP-010 LIP-011 --> | Command line; yes, with `--device cpu --compute_type int8` <!-- LIP-011 --> |
| [wav2vec2-lv-60-espeak-cv-ft](https://huggingface.co/facebook/wav2vec2-lv-60-espeak-cv-ft) | Approximate phoneme times at 20 ms steps, no words | Weights: `apache-2.0` card tag only, no LICENSE file | Python, through Transformers; GPU not checked <!-- LIP-012 --> |
| [charsiu](https://github.com/lingjzhu/charsiu) | English and Mandarin phone alignment | Code: MIT. Weights: no licence at all <!-- LIP-014 --> | Not checked |
| [allosaurus](https://github.com/xinjli/allosaurus) 1.0.2 | IPA phones with approximate times | Repository: GPL-3.0. Weights: no licence file; phone inventories from PHOIBLE (CC BY-SA 3.0) | Python package; CPU by default <!-- LIP-015 --> |
| [Papagayo-NG](https://github.com/morevnaproject-org/papagayo-ng) | A lip sync editor that runs Rhubarb or allosaurus and exports Moho, Alelo, images and JSON <!-- LIP-016 LIP-091 --> | Code: GPL-2.0-or-later <!-- LIP-016 --> | PySide2 GUI with no documented command line (not checked) <!-- LIP-092 --> |
| [OpenFaceFX](https://github.com/OpenFaceFX/OpenFaceFX) 0.24.0 | Conversion between viseme sets; exporters for Rhubarb, Moho, Godot, Spine, Live2D and Unity | Code: MIT | Python package needing only numpy <!-- LIP-057 --> |
| [Audio2Face-3D](https://github.com/NVIDIA/Audio2Face-3D-SDK) | Facial motion; ARKit-named weights, which only drive a character that already has matching ARKit blendshapes <!-- LIP-022 --> | SDK: MIT. Models: [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/) of 2025-10-24, "commercially usable", no claim on outputs, revocable. Audio2Emotion models: for use with Audio2Face only <!-- LIP-019 LIP-020 LIP-021 --> | No: NVIDIA GPU, CUDA 12.8 or newer below 13.0, TensorRT 10.13 or newer below 11.0 <!-- LIP-022 --> |
| [Oculus Lipsync](https://developers.meta.com/horizon/documentation/unity/audio-ovrlipsync-viseme-reference) 29.0.0 | 15 visemes, baked inside the Unity or Unreal editor <!-- LIP-035 LIP-037 --> | Unsettled. Source headers such as `OVRLipSync.h` cite the Oculus Audio SDK License 3.3, which one reading notes Meta's [3.3 page](https://developers.meta.com/horizon/licenses/audio-3.3/) calls "no longer in effect"; both treat Meta's [SDK License Agreement](https://developers.meta.com/horizon/licenses/oculussdk/), limited to "MPT Approved Products", as the cautious reading <!-- LIP-038 --> | Editor only; no Linux build; end-of-life <!-- LIP-037 --> |

No ComfyUI node wrapping Rhubarb turned up in a search (not checked). <!-- LIP-028 --> MFA's current `mfa align` form is deprecated and becomes `mfa align_legacy` in MFA 4.0, planned for the end of 2026. <!-- LIP-007 -->

**Rhubarb uses a transcript as a hint.** <!-- LIP-004 --> With `-d` it still recognises the words itself, but prefers words in the file. <!-- LIP-004 --> The default recogniser is English only; the `phonetic` recogniser is language-independent, "usually less precise", and ignores the transcript. <!-- LIP-003 LIP-004 LIP-158 --> So `-r phonetic` is the only Rhubarb route for other languages today, and its accuracy was not measured here. <!-- LIP-004 -->

**Known text does not give timings.** No text-to-speech model below was checked for per-phoneme timing output, so the measured route is to render the audio and run Rhubarb on it with `-d`. <!-- LIP-159 --> Kokoro's package is reported to make phonemes with its misaki library (not checked); if it returns them, they would give a cheap check against the cues. <!-- LIP-116 -->

**Video lip-sync models make video, not cues.** <!-- LIP-027 --> Checked 2026-09-15:

| Model | Code | Weights | In a game you sell |
|---|---|---|---|
| [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) | No licence file | README: "any form of commercial use is strictly prohibited" | Not allowed <!-- LIP-023 --> |
| [LatentSync](https://github.com/bytedance/LatentSync) 1.6 | Apache-2.0 | An `openrail++` tag, no licence text | No licence text; README minimum VRAM 18GB <!-- LIP-025 --> |
| [MuseTalk](https://github.com/TMElyralab/MuseTalk) | MIT | README: "available for any purpose, even commercially"; [weights repo](https://huggingface.co/TMElyralab/MuseTalk) tagged `creativeml-openrail-m` | Unsettled; one reading adds a face parser trained on CelebAMask-HQ, whose terms allow non-commercial research only <!-- LIP-026 --> |
| [SadTalker](https://github.com/OpenTalker/SadTalker) | [Apache-2.0](https://github.com/OpenTalker/SadTalker/blob/main/LICENSE) | Not clearly covered by the Apache grant; they include face-vid2vid parts from a CC BY-NC 4.0 repository | Unsettled <!-- LIP-027 --> |
| [Hallo](https://github.com/fudan-generative-vision/hallo) | [MIT](https://github.com/fudan-generative-vision/hallo/blob/main/LICENSE) | Tagged MIT; both readings find InsightFace models "for non-commercial research purposes only" | Unsettled <!-- LIP-027 --> |
| [EchoMimic](https://github.com/antgroup/echomimic) | Apache-2.0; README: "intended for academic research" | Apache-2.0 LICENSE, but the repo also bundles sd-image-variations-diffusers (CreativeML OpenRAIL-M) | Unsettled <!-- LIP-027 --> |

## Rhubarb on this machine

Run on 2026-09-15 on the reference machine's host (i7-14700K, 28 logical CPUs, glibc 2.42), outside the container, from the official Linux release with nothing installed. <!-- LIP-153 LIP-155 LIP-163 --> Timings are single runs unless repeats are given. <!-- LIP-156 LIP-157 -->

[`research/experiments/rhubarb/reproduce.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/experiments/rhubarb/reproduce.py) reruns every measurement in this section from the release that `scripts/fetch_tools.py --download rhubarb` unpacks, and prints each number beside the published one. Its [README](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/experiments/rhubarb/README.md) has the whole comparison and what it adds: the speech gate's inputs on real and made-up audio, the frame rules from 6 to 30 fps, and the text-only flap. It was rerun on 2026-09-16 on the same host, taking 457.9 s with other work running (load average 4.39 at the start). Where the rerun differs from the 2026-09-15 numbers, the difference is given below; everything else matched.

The release is v1.14.0 of 2025-04-03: `Rhubarb-Lip-Sync-1.14.0-Linux.zip` is 87,225,003 bytes, sha256 `a9a9074862cff47b2d59b8bf399a678a3b0b74f9452ad6ad94cb292913dd8667`, and unpacks to 166,606,778 bytes. <!-- LIP-005 --> The 7,331,192-byte `rhubarb` binary is dynamically linked, needs `GLIBC_2.29` and `GLIBCXX_3.4.26` or newer, and must sit next to the zip's 86,255,327-byte `res/sphinx/` folder; without it, both recognisers exit with code 1 on speech. <!-- LIP-153 -->

The main test line is LibriSpeech test-clean 6930-75918-0001, 14.225 s and 43 words, under [CC BY 4.0](https://www.openslr.org/12/). <!-- LIP-154 --> Utterances 0000 (3.5 s) and 0002 (5.0 s) were timed too. <!-- LIP-170 --> The 10 s test files came from ffmpeg's `sine=frequency=440:sample_rate=16000:duration=10`, `anoisesrc=colour=white:amplitude=0.3` and `anullsrc` sources, as 16 kHz mono 16-bit PCM. <!-- LIP-165 LIP-166 -->

```sh
ffmpeg -i 6930-75918-0001.flac -ar 16000 -ac 1 -c:a pcm_s16le 6930-75918-0001.wav
./rhubarb -f json 6930-75918-0001.wav
./rhubarb -f json -d 6930-75918-0001.txt 6930-75918-0001.wav
./rhubarb -f json -d 6930-75918-0001.txt --threads 1 6930-75918-0001.wav
./rhubarb -f json -r phonetic 6930-75918-0001.wav
./rhubarb -f json -d 6930-75918-0001.txt --extendedShapes "" 6930-75918-0001.wav
./rhubarb -f dat --datFrameRate 12 -d 6930-75918-0001.txt 6930-75918-0001.wav
./rhubarb -q -f json -d 6930-75918-0001.txt --logFile trace.log --logLevel Trace 6930-75918-0001.wav
./rhubarb -f json -d 6930-75918-0000.txt 6930-75918-0000.wav
./rhubarb -f json -d 6930-75918-0002.txt 6930-75918-0002.wav
./rhubarb -f json silence_10s.wav
./rhubarb -f json sine440_10s.wav
./rhubarb -f json whitenoise_10s.wav
./rhubarb -f json -r phonetic whitenoise_10s.wav
```

The trace log lists what PocketSphinx recognised as `##word[start-end]: word` lines; the word error rates below come from it.

### Speed and the transcript

| Run | Flags | Wall | CPU | Cues | Shapes used | Rerun on 2026-09-16: wall, CPU, cues |
|---|---|---|---|---|---|---|
| Default recogniser | `-f json` | 6.51 s | 11.97 s | 85, or 87 in 4 of 14 repeats | A B C E F G H X <!-- LIP-155 --> | 7.02 s, 12.76 s, 85 |
| With transcript | `-d` | 6.27 s | 11.66 s | 85 or 87 | A B C E F G H X <!-- LIP-156 --> | 9.65 s, 17.26 s, 85, in a single run with other work on the host; five `-d --threads 2` repeats had a median wall time of 6.39 s |
| One thread, with transcript | `-d --threads 1` | 11.02 s | Not checked | Byte-identical on every repeat <!-- LIP-161 LIP-163 --> | Not checked | 11.52 s, 11.42 s, 87, using A B C E F G H X |
| Phonetic recogniser | `-r phonetic` | 1.01 s | 1.36 s | 101 or 102 | All nine <!-- LIP-157 --> | 1.00 s, 1.40 s, 102 |

**A transcript removes the recognition errors.** <!-- LIP-159 --> Without it, PocketSphinx made 9 edits over the 43 words, a 20.9% word error rate; with `-d` it made none. <!-- LIP-159 --> That changed 28 of 85 cues and 8.3% of the running time, well above the 0.5 to 2.4% by which repeat runs differ. <!-- LIP-159 LIP-161 --> Whether the cues became more accurate was not measured. The full rerun matched both error rates and the 28 of 85 cues. Those two runs are multi-threaded, though, and the count depends on which of their two cue sets they return: two other runs of `reproduce.py` that day got 87 cues from one of them and gave 37 of 85 and 39 of 87 cues changed (10.1% and 10.2% of the time).

**The phonetic recogniser was about 6.5 times faster in wall time** than the default without a transcript (6.2 times against the run with one), and gave 16 to 20% more cues using all nine shapes. <!-- LIP-157 --> Whether its shapes are right was not measured. In the rerun it was 6.99 times faster than the default recogniser and 9.62 times faster than the transcript run, which was slow that time (see the table), with 20% more cues than the transcript run. It ignores `-d`, but Rhubarb still reads the file first, so a missing or non-UTF-8 transcript stops even a phonetic run with exit code 1 and no output. <!-- LIP-158 --> Run directly on 2026-09-16 while `scripts/lipsync_cues.py` was built, with the default recogniser, a non-UTF-8 dialog file stopped Rhubarb with `File encoding is not ASCII or UTF-8.` and exit code 1, and an empty one did not stop it. `lipsync_cues.py -r phonetic` reads no transcript and passes no `-d`, so a transcript cannot stop its phonetic runs.

**Threading, not a fixed loading cost, explains the long line's speed.** <!-- LIP-170 --> Rhubarb recognises on min(`--threads`, voice-activity sections, whole seconds divided by 5) threads, so this two-section line used 2 threads even with `--threads 28`. <!-- LIP-163 --> With `-d`, the 3.5 s and 5.0 s lines took 2.89 s and 3.51 s on one thread (0.83 and 0.70 times real time), and the 14.2 s line 6.27 s on two (0.44 times) or 11.02 s on one (0.78 times). <!-- LIP-163 LIP-170 --> Peak resident memory per process, measured on 2026-09-16, was about 156MiB for the short lines on one thread and 311MiB for the long line on two. <!-- LIP-170 --> The rerun gave 2.88 s and 3.63 s for the short lines (0.82 and 0.72 times real time), and peak memory of 155.8MiB and 155.4MiB for them, 304.4MiB for the long line on two threads and 157.6MiB for it on one.

Shape B, slightly open with clenched teeth, covered about 44% of the line, so it is the mouth to get right. <!-- LIP-156 --> The rerun gave 43.7%. D never appeared on this line. <!-- LIP-155 LIP-164 --> Rhubarb needs all six basic shapes anyway. <!-- LIP-033 --> The shortest cue was 0.06 s and the median 0.14 s. <!-- LIP-155 LIP-156 -->

::: warning Use `--threads 1` for any cue file you keep
With more than one recognition thread, the same command gives different files. <!-- LIP-161 --> Five runs with `--threads 2` gave 3 different cue files, disagreeing on 0.5 to 2.4% of the running time. <!-- LIP-161 --> With `--threads 1`, five runs were byte-identical, and so were six with `-d`. <!-- LIP-161 --> Lines under 10 s already run on one thread. <!-- LIP-161 LIP-163 --> In the 2026-09-16 rerun, five runs each with `--threads 1` and with `-d --threads 1` were byte-identical again, five with `-d --threads 2` gave 2 different files, 1.9% apart, and five with the default threads gave 3, with 85 and 87 cues.
:::

The likely cause of the differing files is PocketSphinx's dither sharing random state between decoder threads, inferred from the source, not proven. <!-- LIP-162 -->

### Many cues are shorter than a 12 fps frame

At 12 fps, 38% of the cues from the default recogniser with transcript (32 of 85) and 48% from the phonetic one (49 of 102) last under one frame. <!-- LIP-167 --> None is shorter than a 24 fps frame. <!-- LIP-167 --> That is one line's figure, not a general rate. <!-- LIP-167 --> The rerun matched both counts; its one-thread run, which returns the same cues every time, had 36 of 87 cues under a 12 fps frame. Rhubarb's frame format cannot help: `--datFrameRate 12` exits with code 1 and `Frame rate must be between 24 and 100 fps.` <!-- LIP-168 --> The rerun recorded the whole line: `[Fatal] Application terminating with error: Frame rate must be between 24 and 100 fps.` Quantise from the JSON in your own code, as `lipsync_cues.py --fps` does ([the timeline file](#the-timeline-file)).

`--extendedShapes` chooses which of G, H and X may appear. <!-- LIP-164 --> A disabled G or X becomes A, and a disabled H becomes C; with `--extendedShapes ""`, closed-mouth A rose from 0.65 s to 2.20 s of the line. <!-- LIP-164 --> So a set drawn without G and H still plays. <!-- LIP-033 LIP-164 -->

### Audio that is not speech

::: warning White noise comes back as talking
Rhubarb's voice detector took 10 s of white noise as speech. <!-- LIP-166 --> The default recogniser heard the word "think", used 6.2 s of CPU, and returned one 9.90 s B cue between two short X cues; the phonetic recogniser made 9 cues. <!-- LIP-166 --> Keep music, ambience and sound effects away from Rhubarb, including tracks from [music](/guide/music). <!-- LIP-174 -->
:::

The rerun on 2026-09-16 used another white noise sample, with `seed=1`, and it again came back as talking: the default recogniser heard "of", used 11.09 s of CPU and returned 4 cues, the longest a 9.85 s G, and the phonetic recogniser returned 8 cues, the longest a 3.48 s B.

Music was then tried, through `lipsync_cues.py` on 2026-09-16, on two 15 s excerpts of this repository's own generated tracks, and both came back as cues. With no transcript, the battle music's non-X cues of 1.0 s or more covered 51.0% of its voiced time and the gate refused it, but with `-r phonetic` they covered 19.3% and it passed with a warning. The forest ambience made no cue that long and passed with both recognisers. Given another line's transcript, both were refused on words ([the timeline file](#the-timeline-file) has the gate).

Silence and a 440 Hz sine peaking at about -18 dBFS each gave one X cue in about 0.13 s on a cold run. <!-- LIP-165 --> The same tone peaking between about -15 and -0.8 dBFS was taken as speech and came back as a C cue lasting almost the whole 10 s. <!-- LIP-165 --> The rerun matched the silence and the quiet tone (0.13 s wall, 0.03 s CPU, 25.4MiB each), and the tone peaking at -6 dBFS came back as a 9.88 s C cue.

## Mouth-shape sets

Every set answers "how many mouths" differently. Checked 2026-09-15.

| Set | Shapes | Names |
|---|---|---|
| [Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/README.adoc) | 6, plus 3 optional | A to F; G, H, X <!-- LIP-033 --> |
| Preston Blair, as shipped in [Papagayo-NG](https://github.com/morevnaproject-org/papagayo-ng) | 10 | AI, O, E, U, etc, L, WQ, MBP, FV, rest <!-- LIP-048 --> |
| Fleming and Dobbs, as shipped in Papagayo-NG | 11 | MBP, NLTDR, FV, TH, GK, SH, O, EHSZ, AA, IY, rest <!-- LIP-048 --> |
| [Adobe Character Animator](https://helpx.adobe.com/adobe-character-animator/desktop/export-projects/export.html) export | 12 | Neutral, Aa, D, Ee, F, L, M, Oh, R, S, Uh, W-Oo <!-- LIP-094 --> |
| [Live2D](https://docs.live2d.com/en/cubism-sdk-manual/lipsync/) motion-sync | 6 | Silence, A, I, U, E, O <!-- LIP-053 --> |
| [VRM 1.0](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/expressions.md) presets | 5, all vowels | aa, ih, ou, ee, oh <!-- LIP-052 --> |
| [Oculus/Meta](https://developers.meta.com/horizon/documentation/unity/audio-ovrlipsync-viseme-reference), and MPEG-4 | 15 | sil, PP, FF, TH, DD, kk, CH, SS, nn, RR, aa, E, ih, oh, ou <!-- LIP-035 --> |
| [Microsoft SAPI 5.3](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms720881(v=vs.85)) | 22 | SVP_0 (silence) to SVP_21 (p, b, m) <!-- LIP-039 --> |
| [Apple ARKit](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation) | 52 blendshapes, 27 of them mouth and jaw | jawOpen, mouthClose, mouthFunnel, mouthPucker and others <!-- LIP-042 --> |

Genesis 8, 8.1 and 9 carry the same 17 viseme dials, AA, EE, EH, ER, F, IH, IY, K, L, M, OW, S, SH, T, TH, UW and W, with no R or CH; [DAZ Genesis](/reference/daz-genesis#faces) covers how they are built. <!-- LIP-046 DAZ-083 --> Source's phoneme table has 54 entries: 47 standard phonemes, 6 aliases that reuse standard codes, and `<sil>` ([Source Filmmaker](/reference/source-filmmaker#the-phoneme-set-and-the-vdat-chunk)). <!-- LIP-043 -->

### The mapping to adopt

**Store Rhubarb's letters.** Rhubarb produces them, engine add-ons read them, and nine is a set a model can make per character. <!-- LIP-054 LIP-095 LIP-111 --> Convert phoneme-level sources, such as an aligner, through the Oculus fifteen, which OpenFaceFX uses as its native channels. <!-- LIP-057 LIP-059 --> For ARKit shapes its `arkit` preset is a starting point, and like every Oculus-to-ARKit mapping it is community-made, because Meta publishes none. <!-- LIP-057 -->

The table is derived here from Rhubarb's README and animation rules, not copied. <!-- LIP-033 LIP-049 --> Where Rhubarb allows several shapes for a sound, the Oculus and Genesis columns give the usual one: B or F for S, CH, TH and SH, and B, E or F for R. <!-- LIP-049 --> The Genesis column has not been tried on a figure.

| Rhubarb | Mouth | Sounds | Oculus visemes | Genesis dials | Preston Blair name |
|---|---|---|---|---|---|
| X | Idle, lips closed and relaxed | Pauses | sil | All at 0 | rest <!-- LIP-033 LIP-034 LIP-035 LIP-046 DAZ-083 --> |
| A | Closed, slight pressure | P, B, M | PP | M | MBP <!-- LIP-033 LIP-034 LIP-035 LIP-046 DAZ-083 --> |
| B | Slightly open, clenched teeth | Most consonants (K, S, T), and EE | DD, kk, SS, CH, TH, nn, ih | K, S, SH, T, TH, EE, IH, IY | etc <!-- LIP-033 LIP-034 LIP-035 LIP-046 DAZ-083 --> |
| C | Open | EH, AE, some consonants | E | EH | E <!-- LIP-033 LIP-034 LIP-035 LIP-046 DAZ-083 --> |
| D | Wide open | AA | aa | AA | AI <!-- LIP-033 LIP-034 LIP-035 LIP-046 DAZ-083 --> |
| E | Slightly rounded | AO, ER | oh (for AO), RR | ER | O <!-- LIP-033 LIP-034 LIP-035 LIP-046 DAZ-083 --> |
| F | Puckered | UW, OW, W | ou, oh (for OW) | UW, OW, W | U <!-- LIP-033 LIP-034 LIP-035 LIP-046 DAZ-083 --> |
| G | Upper teeth on lower lip | F, V | FF | F | FV <!-- LIP-033 LIP-034 LIP-035 LIP-046 DAZ-083 --> |
| H | Tongue raised behind upper teeth | L held 0.2 s or longer | nn (for a long L) | L | L <!-- LIP-033 LIP-034 LIP-035 LIP-046 LIP-049 DAZ-083 --> |

Three traps:

- **Preston Blair's E is Rhubarb's C, and Rhubarb's E exports as O.** <!-- LIP-034 LIP-168 --> A set named in one convention and played in the other is wrong on the vowels.
- **The CMU-39 table in Papagayo-NG's `rhubarb.json` contradicts Rhubarb.** <!-- LIP-049 --> It maps S and CH to G, TH and R to H, and L to C, where Rhubarb gives G only to F and V and forces H only for a long L. <!-- LIP-049 -->
- **Frame order differs by integration.** godot-baked-lipsync numbers the shapes X=0, A=1 through H=8, and Rhubarb's After Effects script and a community Godot add-on are reported to use other orders (not checked). <!-- LIP-054 LIP-095 LIP-096 LIP-103 --> A strip in the wrong order is wrong on every shape, so the manifest records it.

## How 2D games play talking portraits

Statements marked as community reports or not checked come from forums, wikis or third-party projects and were not verified.

**Driven by the text, not the audio.** Celeste's portraits have three animation prefixes per expression: `begin_` plays first, `idle_` when not talking and `talk_` while talking, and markup such as `[THEO left normal]` picks the character, side and expression. <!-- LIP-100 --> Ren'Py's `config.speaking_attribute` adds an image attribute while a character speaks, and community examples loop two or three mouth images at 0.2 to 0.3 s over a still base (not checked). <!-- LIP-098 LIP-099 -->

**A base plus a mouth overlay.** GBA Fire Emblem portraits are described as a base image with eye and mouth frames drawn over it at fixed coordinates, and Ace Attorney as swapping whole sprites (community reports). <!-- LIP-101 LIP-102 --> The overlay stores less and cannot disturb the rest of the face.

**Audio-driven playback is discrete.** [godot-baked-lipsync](https://github.com/fbcosentino/godot-baked-lipsync) (MIT, read at commit f3619c1, checked 2026-09-15) runs Rhubarb with `-f tsv --machineReadable` and bakes a mouth track with nearest interpolation and discrete updates. <!-- LIP-095 --> It emits `mouth_shape_changed(mouth_shape: int)`, its 2D example swaps a mouth Sprite2D's texture, and its editor dock downloads Rhubarb 1.13.0 rather than bundling it, keeping it out of exported games. <!-- LIP-095 --> Rhubarb's release zip ships a Spine integration in `extras/EsotericSoftwareSpine/`, and Unity importers exist as community projects (not checked). <!-- LIP-002 LIP-097 -->

**Live2D drives a parameter.** Basic lip sync passes a 0 to 1 level to `ParamMouthOpenY` or similar; its viseme route, motion-sync, is a proprietary plugin with no listed Linux support. <!-- LIP-053 --> **Adobe Character Animator** exports timing only by copying visemes to the clipboard, and runs only on Windows and macOS. <!-- LIP-094 -->

## A portrait, nine mouths and a timeline

A design for a talking portrait made headlessly with what the repo already runs. It was first tried on 2026-09-16, on one generated character; [tried on one portrait](#tried-on-one-portrait) says what that found, and [talking portraits](/guide/talking-portraits) is the guide to doing it.

### Faces only read on a portrait

Measured on 2026-09-15 in the first front-facing frame of `output/sheets/warrior_idle.png` (220 px cells): the figure is 176 px tall, with a closed helm about 26 to 27 px tall and no visible mouth. <!-- LIP-086 --> Taking a mouth as about a quarter of head height, a bare head that size would have a mouth about 6 to 7 px wide and a jaw that opens 1 to 2 px, while a 256 px portrait whose head fills three quarters of its height would have one about 42 to 48 px wide. <!-- LIP-086 --> At 340 px, the smallest portrait size in [facings](/guide/facings#sizes), the same rule gives about 56 to 64 px. <!-- LIP-086 --> These are estimates, not renders, but they make the talking face its own asset rather than a row on a facings sheet.

**Measured on 2026-09-16.** Two sets of renders now stand in for those estimates.

A jaw on a generated rig replaces the sprite-sheet estimates: the 6 to 7 px mouth and 1 to 2 px of jaw opening on a 220 px sheet, and the 3 to 4 px mouth at 128 px in [the short answer](#the-short-answer). [`scripts/face_rig.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/face_rig.py) `add-jaw` gave the 30-bone articulationxl rig `unit_alchemist` a jaw, and `scripts/render_sheet.py` rendered it at 0 and 20 degrees. The whole figure was 175 px tall in the 220 px cells and 102 px in the 128 px ones. Pixels changed between the two rows, per view:

| Cell | Views | Pixels changed | By 16 levels or more | Silhouette pixels |
|---|---|---|---|---|
| 220 px | Square-on (`--flat`), azimuths 0, 90, 180, 270 | 251, 145, 29, 172 | 34, 43, 6, 32 | 0, 2, 1, 3 |
| 128 px | Square-on, the same azimuths | 99, 65, 21, 65 | 12, 15, 1, 15 | 0, 1, 1, 1 |
| 220 px | Isometric, azimuths 45, 135, 225, 315 | 249, 54, 70, 241 | 38, 17, 15, 45 | 0, 1, 1, 0 |
| 128 px | Isometric, the same azimuths | 89, 25, 34, 91 | 10, 4, 6, 12 | 0, 0, 0, 0 |

In the square-on front view the change fitted a 28 by 17 px box at 220 px and a 16 by 11 px box at 128 px. The mesh has no parted lips, so the jaw stretches the lower face and its texture rather than opening a mouth.

Visemes on a CC0 head replace the portrait estimates, the 42 to 48 px mouth at 256 px and the 56 to 64 px mouth at 340 px, with what can be told apart. [`scripts/mpfb_probe.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/mpfb_probe.py) built a MakeHuman body with MPFB2's 15 Meta/Oculus-style visemes as shape keys ([DAZ Genesis](/reference/daz-genesis#makehuman-and-mpfb2)) and rendered each in clay, with no skin material, in three framings. Pixels changed against `viseme_sil` by more than 8 levels, fewest to most over the other 14 visemes:

| Framing | 128 px | 220 px | 340 px |
|---|---|---|---|
| Whole figure | 0 to 8 | 1 to 18 | 4 to 46 |
| Head, front | 38 to 244 | 127 to 722 | 311 to 1654 |
| Head, turned 35 degrees | 58 to 273 | 190 to 738 | 464 to 1629 |

By one reader's eye, on enlarged crops: on the whole figure no viseme shows at 128 px, only `aa` at 220 px, and `aa`, `E` and `O` at 340 px. In the head framing `aa` reads at every size, and at 340 px `aa`, `O`, `CH`, `PP`, `I`, `E` and `U` can be told apart, while `DD`, `kk`, `nn`, `SS`, `RR`, `TH` and `FF` look alike. The head framing runs from the crown to the neck, so the head fills less than three quarters of the cell. The whole-figure counts also bear on the sprite-sheet estimates: at 128 and 220 px, 18 changed pixels was the most any viseme made.

### Making the mouths

1. **Start from an approved portrait.** Make a head-and-shoulders image of 340 px or more from the approved concept with `img_edit_qwen.json` ([Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509)), ask for lips closed and relaxed, and approve it by eye. That mouth is X.
2. **Mark the mouth box.** A rectangle around mouth and chin, stored beside the portrait, guessed by script and movable by a person.
3. **Inpaint A to H inside the mask** at a fixed seed, prompted from Rhubarb's shape descriptions. The [ComfyUI Qwen-Image tutorial](https://docs.comfy.org/tutorials/image/qwen/qwen-image) loads `qwen_image_inpaint_diffsynth_controlnet.safetensors` with `ModelPatchLoader` and feeds the mask to `QwenImageDiffsynthControlnet`. <!-- LIP-108 --> [InstantX](https://huggingface.co/InstantX/Qwen-Image-ControlNet-Inpainting) publishes a 4.23GB inpainting ControlNet for base Qwen-Image, native in ComfyUI since 0.3.59. <!-- LIP-109 --> Whether either works with the Qwen-Image 2512 release the repo loads was not checked.
4. **Paste back only the mask**, so everything outside the mouth is identical by construction.
5. **Downsample last**, with the same method as the portrait.

Whole-image edits drift. The repo's concept-edit skill already records drift in untouched areas, and the cards for [Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) and [2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) promise better consistency with no numbers. <!-- LIP-104 --> Even diffusers' `QwenImageEditInpaintPipeline` resizes the image to about 1 megapixel, and without `padding_mask_crop` the unmasked pixels come back as a VAE reconstruction, not a copy. <!-- LIP-107 --> FLUX.1 Kontext [dev]'s licence is unsettled for a game you sell ([licences](#licences)). <!-- LIP-105 -->

The set's manifest records where the mouth goes and the strip order, which follows godot-baked-lipsync's numbering. <!-- LIP-095 --> `fallback` is Rhubarb's own substitution for disabled shapes (G and X become A, H becomes C). <!-- LIP-164 --> With G, H and X all disabled (`--extendedShapes ""`), the measured line gave 86 cues rather than 85. <!-- LIP-164 --> `scripts/compose_mouths.py` writes this shape with paths relative to the manifest's folder, lists under `shapes` only the mouths it made, and adds `drift`, `drift_sides`, `ring`, `feather` and `sources`.

```json
{
  "portrait": "smith/portrait.png",
  "size": [340, 340],
  "mouth": { "x": 130, "y": 199, "w": 80, "h": 58 },
  "order": ["X", "A", "B", "C", "D", "E", "F", "G", "H"],
  "shapes": {
    "X": "smith/mouth_X.png", "A": "smith/mouth_A.png", "B": "smith/mouth_B.png",
    "C": "smith/mouth_C.png", "D": "smith/mouth_D.png", "E": "smith/mouth_E.png",
    "F": "smith/mouth_F.png", "G": "smith/mouth_G.png", "H": "smith/mouth_H.png"
  },
  "fallback": { "G": "A", "H": "C", "X": "A" }
}
```

### Tried on one portrait

Measured on 2026-09-16 with [`scripts/make_mouths.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/make_mouths.py), [`scripts/compose_mouths.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/compose_mouths.py) and [`scripts/preview_lipsync.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/preview_lipsync.py), on one generated character's portrait at one seed. [Talking portraits](/guide/talking-portraits) walks through the commands.

- **Whole-image edits, not inpainting.** Each mouth is an edit of the whole portrait through `img_edit_qwen.json` at denoise 0.85, and `compose_mouths.py` keeps only the mouth box, so step 4 holds but step 3's inpaint ControlNets were not tried.
- **The portrait.** A 340 by 340 px crop of the concept, edited at denoise 1.0, came back at 1024 by 1024 px in 154.4 s, and a second run at the same seed gave a pixel-identical portrait. The edit graph resizes its input to a trained size and crops the centre when the aspect ratio differs (a 700 by 900 px image came back at 880 by 1184 px), so `make_mouths.py` refuses a mouth box that crop would cut before queueing any edit.
- **Cost.** Each mouth took 143.4 to 157.4 s at 1024 by 1024 px and 20 steps. The whole 16GB card peaked at 15,178 to 15,344MiB during them, with other work sharing it.
- **Nothing outside the box changed.** `compose_mouths.py --check` counted 0 changed pixels outside the 204 by 190 px mouth box for all seven overlays. Drift, the mean difference in a 6 px ring just outside the box, was 1.48 to 1.74 levels out of 255; the X edit, of the rest mouth the portrait already has, drifted 1.54, so that is about as low as drift gets here. A 184 by 160 px box that cut off the lowered chin drifted up to 3.04 on D.
- **Which mouths read**, judged by one reader on the contact sheet at the portrait's size, not at 340 px. X, B, D and F read as their shapes. The first C opened as far as D (8,860 against 8,606 pixels more than 40 levels from X); reworded, it opened about half as far (4,443) and read as C, but now sits close to E (4.64 levels apart on average), which reads only weakly. A looks the same as X (0.68 levels apart). G showed both rows of teeth and H put the tongue out past the lips with each of two wordings, so the set keeps seven overlays and plays G as A and H as C.
- **Playback.** `preview_lipsync.py` wrote MP4 previews whose decoded frames each matched the shape the timeline gave (85 of 85, 43 of 43 and 75 of 75 frames). Whether the mouth looks in sync with the voice was not judged by ear or by eye.

Not tried: another face or seed, the inpaint ControlNets, downsampling the set to a game size (step 5), and an engine reading the manifest.

### The timeline file

Keep Rhubarb's JSON and add fields around it. Papagayo-NG reads its `mouthCues` array of `start`, `end` and `value`; godot-baked-lipsync reads the TSV form instead. <!-- LIP-003 LIP-016 LIP-095 --> Rewrite `metadata.soundFile`, which Rhubarb writes as an absolute path. <!-- LIP-003 --> The example below is the design; what [`scripts/lipsync_cues.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/lipsync_cues.py) writes follows it.

```json
{
  "line": "smith_refusal_01",
  "text": "No.",
  "audio": "smith_refusal_01.ogg",
  "cues": "rhubarb 1.14.0: -f json -d smith_refusal_01.txt --threads 1",
  "duration": 0.42,
  "mouthCues": [
    { "start": 0.00, "end": 0.06, "value": "X" },
    { "start": 0.06, "end": 0.18, "value": "B" },
    { "start": 0.18, "end": 0.36, "value": "F" },
    { "start": 0.36, "end": 0.42, "value": "X" }
  ],
  "fps": 12,
  "frames": ["X", "B", "F", "F", "X"]
}
```

**What `lipsync_cues.py` writes.** Built on 2026-09-16, it converts any audio ffmpeg reads to 16 kHz mono WAV, runs Rhubarb from `tools/` on the host with `--threads 1 --logFile LINE.log --logLevel Trace`, plus `-d LINE.txt` when there is a transcript, and writes these fields, checked in its output files:

- `line`, `text` (null with `-r phonetic`, which reads no transcript), and `audio`, relative to the timeline;
- `cues`, the Rhubarb version and flags; `command`, the exact argument list; and `converted`, the ffmpeg step quoted for a shell;
- `duration`, `metadata` with `soundFile` rewritten relative to the timeline, and `mouthCues` as Rhubarb wrote them;
- `gate`, below;
- with `--fps N` only: `fps`, `rule`, `frames` and `dropped`, which counts the cues no frame shows and the A cues among them.

The log goes beside the timeline, and `--text-only` writes the same shape with `audio` null.

**The speech gate.** Two checks, both read from the trace log. The word check refuses a line when the words PocketSphinx heard differ from the transcript by more than 60% word error rate; it is skipped with no transcript and with `-r phonetic`. The flat-mouth check adds up the non-X cues lasting 1.0 s or more and refuses the line when they cover more than 50% of the voiced time; a cue that long below that share only warns. A refused line writes nothing and exits with code 3, unless `--force` writes it with `"passed": false`. `gate` records `passed`, `reasons` and `warnings`; the word counts, `wer` and `wer_max`, or why the word check was skipped; and `voiced_s`, `longest_cue`, `long_cues`, `long_s`, `long_share`, `long_share_max` and `flat_min_s`. The thresholds rest on `reproduce.py`'s runs: speech at normal speed, under steady noise and with a vowel stretched 16 times never made a non-X cue of 1.0 s, and ten seconds of loud noise or a loud sine covered 76.8% to 99.5% and were refused. What gets through is in its [README](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/experiments/rhubarb/README.md): a 2 s noise tail after a 3.5 s line passes with a warning, generated battle music passes with `-r phonetic` ([audio that is not speech](#audio-that-is-not-speech)), and a line slowed to half speed was refused on words at 87.5%. Those fixtures are made from one speaker's lines, ffmpeg noise and two music excerpts, which separates these cases but is not an error rate.

**Frames only for baked animation.** An engine that keys on cue times, as godot-baked-lipsync does, needs no frames. <!-- LIP-095 --> Write `fps` and `frames` only for a baked, frame-based animation; 12 fps is an example. Sampling each frame at its midpoint can drop up to the 38% of cues shorter than a 12 fps frame on the measured line. <!-- LIP-167 --> A lost P, B or M closure is the likeliest to show, so a second rule to try is that any frame containing an A cue shows A. `lipsync_cues.py --rule` has both, as `midpoint` and `closure`, plus `share`, adapted from Valve's phoneme filter ([Source Filmmaker](/reference/source-filmmaker#what-to-build)). Counted on 2026-09-16 on a one-thread run of the measured line with its transcript (87 cues, 36 of them shorter than a frame), `--fps 12` wrote 171 frames and dropped 4 cues with `midpoint`, 7 with `closure` and 4 with `share`, and no rule dropped any of the 7 A cues. `closure` differed from `midpoint` in 7 frames, and `share` in none; `reproduce.py`'s README sweeps the same rules from 6 to 30 fps. No rule has been judged on a portrait.

**With no voice.** Until lines have audio, write the same file from the text: alternate two or three open shapes at a fixed interval while the text prints, and end on X. That is the text-driven pattern above. `lipsync_cues.py --text-only` writes it as C, B, D, B repeating every 0.14 s for as long as the text takes at 15.6 characters per second, then X. Those are the median cue length (0.14 s over 142 cues) and speaking rate (354 characters in 22.74 s) of the three LibriSpeech lines, from `reproduce.py` on 2026-09-16. The flap has not been judged on a portrait, and the Ren'Py figures above are community reports, not checked. <!-- LIP-099 -->

## Faces on generated meshes

This only pays off for a 3D portrait renderer, given the pixel figures above. <!-- LIP-086 --> Since 2026-09-16, `scripts/render_sheet.py` opens a `.blend` and sets shape keys (`"@shape_keys"`) and rig properties (`"@props"`) per pose as well as bones, and [`scripts/face_rig.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/face_rig.py) adds a jaw and borrows shape keys by the methods below. The walk sheet rendered after that change differed from the one before it by 0 pixels. [Rigging](/guide/rigging) covers the body rig.

### The riggers give you no face

- **UniRig articulationxl.** A generated warrior's rig has 28 bones named `bone_0` to `bone_27`, none of them jaw, eye, mouth or face bones, and a 19,943-vertex mesh with no shape keys; another articulationxl warrior has 47 bones. Measured in bpy 4.5.9. <!-- LIP-061 -->
- **mesh2motion.** The human rig's head chain is `neck_01`, `head`, `head_leaf`, with no jaw, eye or mouth joints and zero morph targets, and rigging runs only in a browser. <!-- LIP-080 -->
- **Meshy.** Its docs mention no face bones, blendshapes or morph targets, and its FAQ answers "Not directly" to rigging facial expressions. <!-- LIP-078 --> Tripo and Mixamo are reported to emit no face either (not checked). <!-- LIP-079 LIP-081 -->

### What Blender does headlessly

The jaw, Surface Deform, glTF and Rigify results were measured on 2026-09-15 in `asset-engine-comfy:0.1.1` (bpy 4.5.9 LTS, background mode), on test spheres and Rigify's Human metarig. <!-- LIP-064 LIP-067 LIP-068 --> Bind restrictions, Data Transfer, Rigify's face requirements and the add-ons were read from the Blender manual, source and add-on pages, checked 2026-09-15. <!-- LIP-029 LIP-065 LIP-066 LIP-069 LIP-082 LIP-083 -->

**A jaw bone placed by rule works.** <!-- LIP-067 --> A `jaw` bone parented to a bone named `head`, weighting vertices low and to the front with a 0.3-unit fade, moved 123 of 642 vertices when rotated 20 degrees. <!-- LIP-067 --> `face_rig.py add-jaw` applies the rule to rigged characters. On 2026-09-16, on five generated articulationxl rigs of 24 to 47 bones, it weighted 194 to 534 vertices and moved 185 to 493 of them at 20 degrees. The topmost bone was a poor guess for the head there: on three of the five rigs it was the heaviest weight on 5 vertices or fewer, so the script takes, from the topmost bone down, the bone that is the heaviest weight on the most of the highest 2% of vertices, and prints its pick.

**A shape key transfers with Surface Deform.** <!-- LIP-064 --> `bpy.ops.object.surfacedeform_bind` bound a 642-vertex sphere to a 1,106-vertex template whose `jawOpen` key moved vertices 0.3 down, and `bpy.ops.object.modifier_apply_as_shapekey` turned the deformation into a new key of about 0.30 at most. <!-- LIP-064 --> The key takes the modifier's name, so rename it. <!-- LIP-064 --> The bind's restrictions fall on the template: no edges shared by more than two faces, no concave faces, no doubled vertices and no faces with collinear edges. <!-- LIP-065 -->

**Data Transfer cannot copy shape keys.** <!-- LIP-066 --> It copies vertex groups, UVs, colour attributes and custom normals, so it suits jaw weights, not blendshapes. <!-- LIP-066 -->

**Both survive glTF.** <!-- LIP-067 --> Bones, vertex groups and `jawOpen` came back after `export_scene.gltf(export_morph=True)` and re-import, but the mesh returned with 3,840 vertices instead of 642, so vertex indices do not survive. <!-- LIP-067 -->

**Rigify generates headlessly but does not fit.** <!-- LIP-068 LIP-069 --> Enabling the add-on, adding the Human metarig and calling `rigify.generate.generate_rig` built a 706-bone rig with `jaw_master` and `DEF-jaw` in about 2.2 to 2.3 s. <!-- LIP-068 --> The metarig uses the deprecated `faces.super_face` rig; after Upgrade Face Rig, the modular jaw rig needs four lip chains meeting at the mouth corners, or generation stops with `Could not find all mouth corners`. <!-- LIP-068 LIP-069 --> Rigify cannot fit the face bones automatically, so every generated head would need its jaw and lip chains moved by hand from fixed human-sized positions. <!-- LIP-069 -->

**The facial add-ons need a person.** <!-- LIP-029 LIP-082 LIP-083 --> [Faceit](https://faceit-doc.readthedocs.io/en/latest/landmarks/) (US$78 to US$289 by tier on [Gumroad](https://fbra.gumroad.com/l/Faceit)) makes the 52 ARKit shape keys only after the user places landmarks by hand, with no documented headless mode. <!-- LIP-083 --> Auto-Rig Pro's facial markers are placed or refined by hand, and its [licences](https://www.lucky3d.fr/auto-rig-pro/doc/license.html) mix GPL-3.0 for the bpy-derived source in `src`, a proprietary per-device AI binary, and assets that "may not be extracted for use in other projects". <!-- LIP-082 --> [Rhubarb Lipsync NG](https://github.com/Premik/blender_rhubarb_lipsync_ng) (MIT) bakes a user-chosen Action per cue to NLA strips on an armature or shape-key mesh, from sidebar panels. <!-- LIP-029 --> Its Linux zip bundles `rhubarb` and its CI runs the operators headless, but no scripted workflow is documented and every version test ran on Windows. <!-- LIP-029 -->

### Heads to borrow shapes from

Checked 2026-09-15 against the linked licence pages. Genesis heads are covered in [DAZ Genesis](/reference/daz-genesis).

| Head | Shapes | Licence and what it covers | In a game you sell |
|---|---|---|---|
| [ICT-FaceKit](https://github.com/USC-ICT/ICT-FaceKit), light release | 53 ARKit-style expressions, with no `tongueOut` | MIT, covering code, head mesh and morph data; the notice is embedded in the OBJ files. The Full ICT Face Model, promised under a separate USC licence, is not covered | Allowed with the MIT notice. With no tongue shape, H falls back to C, as Rhubarb substitutes when H is disabled. Its Blender script needs `bpy.ops.import_scene.obj` changed to `bpy.ops.wm.obj_import` for Blender 4.5 <!-- LIP-071 LIP-164 --> |
| [MPFB2](https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md) | Face packs as shape keys: see [DAZ Genesis](/reference/daz-genesis#makehuman-and-mpfb2) | Code: GPL-3.0-or-later. Bundled assets, including base mesh and expressions: CC0 1.0. The three face packs, downloaded separately: CC0 1.0. Other separately downloaded packs keep their own licences. No claim on output | Bundled assets and the three face packs allowed; check any other pack's licence <!-- LIP-072 DAZ-095 -->. Ran headless in the container on 2026-09-16, with its Meta/Oculus-style visemes loaded ([DAZ Genesis](/reference/daz-genesis#makehuman-and-mpfb2)) |
| [Filmic Worlds "colin"](https://filmicworlds.com/blog/solving-face-scans-for-arkit/) | 52 ARKit shapes in `colin_dst_rig.fbx` | CC0 1.0 for John Hable's rights in a scanned head | Unclear. CC0 does not clear the scanned person's likeness or FaceCap's possible rights, and the author says lips and eyelids need fixing <!-- LIP-074 --> |
| [FLAME](https://flame.is.tue.mpg.de/modellicense.html) 2017 to 2023 | Not checked | Academic Model License, for the models and add-on | Not allowed <!-- LIP-070 --> |
| FLAME 2023 Open | Not checked | Open Model License, which the site calls CC BY 4.0, plus bans on pornographic, fake, libellous, misleading or defamatory use | Allowed with attribution, after registration <!-- LIP-070 --> |
| [MetaHuman](https://www.metahuman.com/license) | Not checked | Unreal Engine EULA, update 21 (code), and the Epic Content License Agreement with its MetaHuman Content Addendum (content) | Unsettled; [DAZ Genesis](/reference/daz-genesis#metahuman) sets out both readings, including the AI and database ban. Use as a shape donor not checked <!-- LIP-075 LIP-076 DAZ-110 --> |
| A free [Gumroad "MetaHuman Head"](https://dragonboots.gumroad.com/l/metahumanhead) | 52 ARKit shapes taken from MetaHuman's rig | No licence; "intended for study purposes only" | Not allowed <!-- LIP-087 --> |

## Text-to-speech whose lines may ship

As with MusicGen on the [licensing](/guide/licensing#music-and-sound) page, many open voices pair permissive code with restricted weights or training data. <!-- LIP-119 LIP-125 --> TTS adds a fourth layer on top of code, weights and output: the voice itself, whether a trained preset or a sample you clone. <!-- LIP-119 LIP-132 -->

Checked 2026-09-15 against the linked licences, cards and terms, which change. Nothing in this section was run.

### Allowed

| Option | Licence | Voices |
|---|---|---|
| [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) v1.0 | Weights: Apache-2.0. The card says training used permissive or non-copyrighted audio, including some CC BY recordings and synthetic audio from closed TTS models from large providers. Package licence not checked | 54 presets, 8 languages, no cloning <!-- LIP-115 --> |
| [Chatterbox](https://huggingface.co/ResembleAI/chatterbox) | Code and weights: MIT, including Multilingual (23 languages) and Turbo (English) | Zero-shot cloning. The official package's `generate()` adds Resemble's Perth watermark to every output; it is not in the weights <!-- LIP-126 --> |
| [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) | Code and weights: Apache-2.0 | 10 languages; Base models clone from 3 seconds <!-- LIP-139 --> |
| [Parler-TTS Mini v1](https://huggingface.co/parler-tts/parler-tts-mini-v1) | Code and weights: Apache-2.0 | English, voice from a text description, no cloning <!-- LIP-134 --> |
| [MeloTTS](https://github.com/myshell-ai/MeloTTS) | Code and checkpoints: MIT. BERT models fetched at run time keep their own licences | English, Spanish, French, Chinese, Japanese, Korean <!-- LIP-135 --> |

Chatterbox's "Llama backbone" carries no Meta weights: its shape matches no Meta release, so the Llama licence does not attach. <!-- LIP-128 -->

### Allowed with conditions

| Option | Licence | Condition |
|---|---|---|
| [Kyutai TTS 1.6B](https://huggingface.co/kyutai/tts-1.6b-en_fr) | Weights: CC BY 4.0. Code: MIT for Python, Apache (version not recorded) for the Rust backend | Voices are licensed per folder in [kyutai/tts-voices](https://huggingface.co/kyutai/tts-voices): CC0 `voice-donations`; CC BY 4.0 `vctk`, `cml-tts/fr`, `alba-mackenna`; CC BY-NC 4.0 `expresso` and `ears`, which a sold game may not use; `unmute-prod-website` mixed, including a non-commercial clip. CC BY weights and voices need attribution <!-- LIP-132 --> |
| [NeuTTS Air](https://huggingface.co/neuphonic/neutts-air) | Weights: tagged apache-2.0. Code: [NeuTTS Open License v1.0](https://github.com/neuphonic/neutts/blob/main/LICENSE) since 2026-01-14 | The code licence allows commercial use of code, derivatives and outputs only while annual revenue is under US$5,000,000, and ends automatically on breach; commits before 2026-01-14 are Apache-2.0. Perth watermark by default, skipped with only a warning if resemble-perth fails to import <!-- LIP-144 --> |
| [IndexTTS-2](https://github.com/index-tts/index-tts/blob/main/LICENSE) | bilibili Model Use License Agreement, code and weights | A separate licence above 100 million MAU or a revenue threshold the prevailing Chinese text puts at RMB 100 million. Outputs may count as Derivative Works, with contract and notice duties <!-- LIP-142 --> |
| [ElevenLabs](https://elevenlabs.io/terms-of-use) | Service terms of 2026-03-31 | Paid plans only; Studio is non-commercial except on Enterprise. No AI training on output. Clone only voices you are authorised to use. ElevenLabs takes a perpetual, irrevocable, royalty-free licence to your input and output (section 4(d)), and output may not be unique (section 10) <!-- LIP-145 --> |
| [OpenAI TTS](https://developers.openai.com/api/docs/guides/text-to-speech) | Its TTS guide; the Usage Policies it cites do not repeat the rule | Tell players the voice is AI-generated. Custom voices need the owner's consent recording <!-- LIP-146 --> |

### Not allowed

| Option | Licence | Why |
|---|---|---|
| [XTTS-v2](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt) | Coqui Public Model License 1.0.0, weights and output | Non-commercial only, and its notice duty reaches output <!-- LIP-122 --> |
| [Fish Speech](https://github.com/fishaudio/fish-speech/blob/main/LICENSE) and OpenAudio S1-mini | Fish Audio Research License for code and weights on the main branch since 2026-03-10; S1-mini weights CC BY-NC-SA 4.0 | Commercial use needs a separate written licence from Fish Audio <!-- LIP-131 --> |
| [F5-TTS](https://huggingface.co/SWivid/F5-TTS) pretrained weights | Weights: `CC-BY-NC-4.0` in [TTS-Audio-Suite's licence table](https://github.com/diodiogod/TTS-Audio-Suite/blob/main/LICENSE); the card is under [Honest uncertainty](#honest-uncertainty) <!-- LIP-147 --> | Non-commercial <!-- LIP-125 LIP-147 --> |
| Piper `en_US-lessac` | Dataset: [Blizzard 2013 Research Licence Agreement](https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html), research purposes only. Weights: `rhasspy/piper-voices` tagged MIT, which does not clear the data | Excludes any commercial purpose <!-- LIP-119 --> |
| Piper `en_US-libritts_r` | Its [MODEL_CARD](https://huggingface.co/rhasspy/piper-voices/raw/main/en/en_US/libritts_r/medium/MODEL_CARD) lists CC BY 4.0 data, but the voice was fine-tuned from lessac | Inherits lessac's terms <!-- LIP-121 --> |

### Unsettled

::: danger Unsettled is not the same as allowed
Each of these has a permissive-looking licence and a statement pointing the other way, or was read two ways. Don't ship lines from them in something you sell.
:::

- **Bark.** Code and weights are MIT, and the README says "available for commercial use"; the [card](https://huggingface.co/suno/bark) says "This model is meant for research purposes only". <!-- LIP-124 -->
- **VibeVoice-1.5B.** Tagged MIT, but its [card](https://huggingface.co/microsoft/VibeVoice-1.5B) says it "is limited to research purpose use", and Microsoft removed the TTS code on 2025-09-05. <!-- LIP-140 -->
- **Dia and Dia2.** Apache-2.0 code and weights, but the [README](https://github.com/nari-labs/dia) calls the model "intended for research and educational use" and forbids audio resembling real people without permission. <!-- LIP-129 --> Dia2 also loads a CC BY 4.0 codec and clones through AGPL-3.0 whisper-timestamped. <!-- LIP-129 -->
- **StyleTTS 2.** [MIT code](https://github.com/yl4579/StyleTTS2); the pre-trained checkpoints have no licence. <!-- LIP-136 --> The README's only condition covers cloning a voice outside the training set: have the owner's permission, or say the speech is synthesised. <!-- LIP-136 -->
- **Sesame CSM-1B.** [Weights](https://huggingface.co/sesame/csm-1b) tagged apache-2.0, but its [reference code](https://github.com/SesameAILabs/csm) loads a tokeniser from Meta's gated Llama-3.2-1B repo, and whether Llama terms reach the weights is unresolved. <!-- LIP-138 -->
- **Orpheus 3B.** The [card](https://huggingface.co/canopylabs/orpheus-3b-0.1-ft) is tagged apache-2.0, but a Canopy Labs collaborator said in [issue #29](https://github.com/canopyai/Orpheus-TTS/issues/29) and #33 that the weights fall under the Llama licence as a derivative work. <!-- LIP-130 --> Both readings treat them as bound by the Llama 3.2 Community License, and the release meets none of its agreement copy, "Built with Llama" or naming terms. <!-- LIP-130 -->
- **Higgs TTS 2 and 3.** Both readings put [v2](https://huggingface.co/bosonai/higgs-tts-2-3b-base) under the Boson Higgs Audio 2 Community License, with an expanded licence above 100,000 annual active users and attribution to Boson and Meta Llama 3, and the [Higgs TTS 3](https://huggingface.co/bosonai/higgs-tts-3-4b) speech model under a Research and Non-Commercial License. <!-- LIP-141 --> One also notes separate Apache-2.0 "Higgs Audio v3 STT" checkpoints. <!-- LIP-141 -->
- **Kyutai Pocket TTS.** One reading: an English CPU model with CC BY 4.0 weights and MIT code. <!-- LIP-133 --> The other: its [card](https://huggingface.co/kyutai/pocket-tts) is out of date, the repository ships six languages, and some preset voices are non-commercial. <!-- LIP-133 -->

::: danger Piper's example voice was trained on research-only data
Piper's code moved from MIT [rhasspy/piper](https://github.com/rhasspy/piper), archived 2025-10-06, to GPL-3.0 [piper1-gpl](https://github.com/OHF-Voice/piper1-gpl). <!-- LIP-117 --> `en_US-lessac-medium`, the voice in Piper's CLI examples, was trained on research-only data, although the voices repo is tagged MIT. <!-- LIP-119 -->

Other voices are unsettled. <!-- LIP-118 --> One reading trusts [VOICES.md](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md), which says each MODEL_CARD "contains important licensing information"; the other finds most cards license the dataset, not the weights, and about 90 voices fine-tuned from lessac or ryan (CC BY-NC-SA 4.0) that do not pass those terms on. <!-- LIP-118 --> `en_GB-alan` is not clean on either reading: both variants list Mycroft's `apope_low`, whose [LICENSE](https://github.com/MycroftAI/mimic3-voices/blob/master/voices/en_UK/apope_low/LICENSE) reads "All Rights Reserved", and were fine-tuned from non-commercial base voices: medium from lessac, low from ryan. <!-- LIP-120 -->
:::

### Fitting the container

The container runs Python 3.11 with pip constraints of torch 2.6.0 and transformers 4.57.6 on cu124, and the host's 550 driver caps CUDA at 12.4 ([docker](/reference/docker)). <!-- LIP-143 --> None of these was installed.

| Option | Declared requirements | In this container |
|---|---|---|
| Kokoro | Python 3.10 to 3.13, torch unpinned (not checked) <!-- LIP-116 --> | Not tried |
| Chatterbox | torch 2.6.0 pinned (not checked) <!-- LIP-127 --> | Not tried; its transformers pin not checked |
| Qwen3-TTS | transformers 4.57.3 pinned, torch not pinned <!-- LIP-139 --> | Clashes with the container's transformers 4.57.6 <!-- LIP-139 LIP-143 --> |
| Dia | torch 2.6.0 pinned, CUDA 12.6 wheels <!-- LIP-129 --> | Not tried |
| Dia2 | torch 2.8.0 or newer, CUDA 12.8 or newer <!-- LIP-129 --> | No <!-- LIP-129 LIP-143 --> |
| IndexTTS-2 | PyTorch 2.8 wheels for CUDA 12.8 <!-- LIP-142 --> | No <!-- LIP-142 LIP-143 --> |
| NeuTTS Air | Real time on CPU, per its README <!-- LIP-144 --> | Not tried |
| MeloTTS | "Fast enough for CPU real-time inference", the README's own claim <!-- LIP-135 --> | Not tried |
| TTS-Audio-Suite, a ComfyUI pack of 16 TTS engines | Python 3.12 or higher in its README; its installer does not check | Unsupported on 3.11, not proven to fail <!-- LIP-147 --> |

## Licences

What a talking portrait might ship, checked 2026-09-15 against the pages linked above.

| What ships | Licence, and what it covers | What you owe |
|---|---|---|
| Rhubarb cue files, and frames made from them | [LICENSE.md](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md)'s summary, "not legally binding", says the data "belongs to you alone"; the binding MIT text asks for its notice only in copies or substantial portions of the Software | Nothing <!-- LIP-001 --> |
| The `rhubarb` binary and `res/`, for runtime lip sync or inside a published image | Code: MIT. Statically linked PocketSphinx and sphinxbase: CMU variation of 2-clause BSD. Acoustic model: Alpha Cephei variation of 2-clause BSD. Other bundled parts: MIT, BSD, Boost, Unicode and WTFPL notices listed in LICENSE.md | Rhubarb's whole LICENSE.md: the MIT notice, plus the notice, conditions and disclaimer of every bundled component it lists (Boost, PocketSphinx, sphinxbase, the CMU acoustic model, Flite, WebRTC, utf8proc and its Unicode data, libogg, libvorbis and others). Flite also requires modified files to be marked, its authors' names kept, and no endorsement in their names without written permission <!-- LIP-001 LIP-002 LIP-151 LIP-152 --> |
| Frames rendered in Blender | [Blender](https://www.blender.org/about/license/): source GPL-2.0-or-later, binaries GPL-3.0-or-later; what you create with it is "your sole property" | Nothing <!-- LIP-084 --> |
| Overlays from Qwen-Image-Edit 2509 or 2511, or the Qwen-Image inpaint ControlNets | Weights: Apache-2.0 (the Qwen-Image-Edit 2509 and 2511 cards; the tag on Comfy-Org's DiffSynth ControlNet repo; the tag on InstantX's card), which says nothing about generated images | Nothing stated <!-- LIP-104 LIP-108 LIP-109 --> |
| Shape keys transferred from ICT-FaceKit | MIT, covering its mesh and morph data | The MIT notice, on the cautious reading that transferred shapes carry its data <!-- LIP-071 --> |
| Voice lines | Per model and per voice | See [text-to-speech](#text-to-speech-whose-lines-may-ship) |

**GPL tools.** Papagayo-NG is GPL-2.0-or-later, so at most run it as a separate, unmodified program. <!-- LIP-016 --> The allosaurus repository is GPL-3.0, [phonemizer](https://github.com/bootphon/phonemizer) and [espeak-ng](https://github.com/espeak-ng/espeak-ng) are GPL-3.0-or-later, and piper1-gpl is GPL-3.0. <!-- LIP-015 LIP-030 LIP-117 --> Whether their licences reach the data they produce was not checked. Don't copy their code or tables into the repo or a game.

**Whether the Rhubarb archive as a whole is permissive is unsettled.** <!-- LIP-002 --> Both readings agree LICENSE.md lists only permissive parts, and that the zip's unlisted `extras/EsotericSoftwareSpine/rhubarb-for-spine-1.14.0.jar` bundles OpenJFX (GPL-2.0 with Classpath Exception) and javax.json (CDDL-1.1 or GPL-2.0); they differ on whether the archive can still be called permissive. <!-- LIP-002 --> Copying only `rhubarb`, `res/` and `LICENSE.md` sidesteps it. <!-- LIP-002 -->

**FLUX.1 Kontext [dev] is unsettled.** <!-- LIP-105 --> Under the [FLUX.1 [dev] Non-Commercial License v1.1.1](https://github.com/black-forest-labs/flux/blob/main/model_licenses/LICENSE-FLUX1-dev) you "may use Output for any purpose (including for commercial purposes), except as expressly prohibited herein", but section 4(a) bans use "for any commercial or production purposes". <!-- LIP-105 --> One reading calls Outputs made while developing a sold game not clearly covered; the other says that work needs a commercial licence from BFL. <!-- LIP-105 --> Treat it as the licensing page treats MusicGen.

## What not to do

**Do not rig faces for the sprite sheets.** A mouth at 128 px would be a few pixels wide ([faces only read on a portrait](#faces-only-read-on-a-portrait)). <!-- LIP-086 --> Measured since with `scripts/face_rig.py` and `scripts/mpfb_probe.py`, a 20 degree jaw changed at most 15 pixels by 16 levels or more in a 128 px view, and on a whole figure no viseme changed more than 18 pixels at 128 or 220 px.

**Do not run Rhubarb on music or noise.** Its voice detector accepts white noise as speech ([audio that is not speech](#audio-that-is-not-speech)). <!-- LIP-166 --> `lipsync_cues.py`'s gate refused all 18 runs on 10 s of loud noise or a loud sine, but a 2 s noise tail after a line, and generated battle music with `-r phonetic`, got through with a warning.

**Do not keep cue files made on more than one thread.** The same command gives different files. <!-- LIP-161 -->

**Do not ask the `dat` export for sprite frame rates.** It refuses anything under 24 fps. <!-- LIP-168 -->

**Do not copy Papagayo-NG's mapping tables.** They ship in a GPL-2.0-or-later program, and its CMU-39 Rhubarb table contradicts Rhubarb. <!-- LIP-016 LIP-049 -->

**Do not use video lip-sync models for game assets.** They make video, not cues, and their weight licences are prohibitive, unpublished or unsettled. <!-- LIP-023 LIP-025 LIP-026 LIP-027 -->

**Do not trust a licence tag alone.** NeuTTS Air's weights are tagged apache-2.0 while its code carries a revenue cap, and Piper's voices repo is tagged MIT over a voice trained on research-only data. <!-- LIP-119 LIP-144 --> A ComfyUI node's MIT licence does not cover the weights it downloads either; the F5-TTS node's README is reported not to say they are non-commercial (not checked). <!-- LIP-147 LIP-148 -->

**Do not ship lines from XTTS-v2, Fish Speech (without Fish Audio's written licence), F5-TTS's pretrained weights or Piper's lessac voice.** Their weights or training data bar commercial use. <!-- LIP-119 LIP-122 LIP-125 LIP-131 LIP-147 -->

**Do not borrow shapes from FLAME's academic models or a free MetaHuman-derived head.** FLAME's Academic Model License forbids commercial products, and the free head has no licence at all. <!-- LIP-070 LIP-087 -->

**Do not build on Oculus Lipsync.** It is end-of-life with no Linux build. <!-- LIP-037 -->

## What to build

Ranked. None duplicated an existing script when proposed. The notes under items 1, 2, 3, 7 and 8 say what was built or tried on 2026-09-16, what it measured and what is still untested; the other items have not been started.

1. **`scripts/lipsync_cues.py`, with Rhubarb in the image.** Add a Dockerfile step that keeps only `rhubarb`, `res/` and `LICENSE.md` (about 94MB of the 167MB unpacked), and put Rhubarb's notices in `NOTICE` and `CREDITS.md`, because a published image redistributes the binary ([redistributing](/guide/redistributing)). <!-- LIP-001 LIP-005 LIP-153 --> The binary needs `GLIBC_2.29` and `GLIBCXX_3.4.26` or newer. <!-- LIP-153 --> The image's base is Ubuntu 22.04 (the Dockerfile's `CUDA_TAG`). Whether its glibc and libstdc++ meet that floor was not recorded, and the binary has not been run in the container. The script converts a line to 16 kHz mono WAV, runs `rhubarb -f json -d <line>.txt --threads 1 --logFile <line>.log --logLevel Trace`, rewrites `soundFile` and writes the timeline; `--text-only` writes the text-driven flap. As an untested speech gate, it compares the log's `##word` lines with the text and refuses a poor match, or a single cue over most of the file. Keep the 10 s silence and sine WAVs as fixtures that should each give one X cue. <!-- LIP-165 --> Run lines as separate one-thread processes at about 156MiB each; parallel runs were not measured. <!-- LIP-170 --> It is the one measured, licence-clear route, and the wrapper handles the thread, path and frame-rate traps measured here. <!-- LIP-003 LIP-161 LIP-168 -->

   **Built on 2026-09-16, without the image step.** [`scripts/lipsync_cues.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/lipsync_cues.py) exists, but Rhubarb is not in the image: [`scripts/fetch_tools.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/fetch_tools.py) downloads the release pinned in `tools.json` by size and sha256 and unpacks only `rhubarb`, `res/` and `LICENSE.md` into the gitignored `tools/`, and the script runs it on the host. So the Dockerfile and `NOTICE` were not changed, and `CREDITS.md` lists Rhubarb among the tools as fetched, not redistributed. The script converts, runs Rhubarb, rewrites `soundFile` and writes the timeline as described, and has `--text-only`. Its gate adds up every non-X cue of 1.0 s or more rather than looking for a single long cue, and its thresholds were measured ([the timeline file](#the-timeline-file)). It adds `--fps` with three frame rules, and a `--selftest` of 14 checks that makes the silence, sine and white noise fixtures itself; it passed in 13.74 s. Still untested: Rhubarb inside the container, so the glibc and libstdc++ floor there is still unrecorded; MP3, Opus, M4A and AAC input; parallel runs and their memory; and real slow, sung or shouted lines, synthetic voices, non-English speech and recordings with noise or music under the voice.
2. **Experiment: masked mouth edits on one portrait.** Run A to H through the ComfyUI inpaint ControlNet and as whole-image edits through `img_edit_qwen.json`, recording VRAM and seconds per shape on the 16GB card, mean pixel difference outside the mouth box, and which shapes read at 340 px, because the design rests on the mouths matching and no model card gives a number. <!-- LIP-104 -->

   **Half tried on 2026-09-16.** Only the whole-image route ran, through [`scripts/make_mouths.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/make_mouths.py), on one portrait at one seed: 143.4 to 157.4 s per shape, the whole card peaking at 15,178 to 15,344MiB, drift of 1.48 to 1.74 levels just outside the mouth box, and seven of nine shapes kept ([tried on one portrait](#tried-on-one-portrait)). Still untested: the inpaint ControlNet route, which shapes read at 340 px rather than at 1024 px, the edit's own VRAM apart from other work on the card, and any other face or seed.
3. **`scripts/compose_mouths.py`, with a mouth-set check in `sheet_check.py`.** Crop, paste back, write overlays and a manifest with `order` and `fallback`, and confirm every pixel outside the mask is identical, because that guarantee should be checked by number rather than by eye.

   **Built on 2026-09-16, with the check in the script itself.** [`scripts/compose_mouths.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/compose_mouths.py) undoes the edit graph's resize and centre crop, measures drift, crops and feathers each mouth, and writes the overlays and a manifest with `order` and `fallback`. `--check` pastes every overlay back and fails unless no pixel outside the box changes, every size matches and A to F are present; on the one set made it counted 0 changed pixels outside the box for all seven overlays. `sheet_check.py` was not changed. [`scripts/preview_lipsync.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/preview_lipsync.py) plays a set against a timeline as an MP4 and lays the mouths out on a contact sheet. Still untested: RGBA portraits, an odd-sized portrait through the edit, and whether an engine or add-on reads the manifest and overlays.
4. **Experiment: a generated voice through Rhubarb.** Install Kokoro and Chatterbox without moving torch or transformers, or in their own virtual environments as separate processes if a pin clashes. Speak the LibriSpeech transcript and rerun the Rhubarb commands and word check, because Rhubarb was only measured on human recordings.
5. **Experiment: non-English lines.** Run one CC0 or CC BY line in another language through `-r phonetic` and through wav2vec2-lv-60-espeak-cv-ft with `output_char_offsets`, mapped to the nine cues by a small IPA table, and count visibly wrong shapes, because the English recogniser cannot be used and the phonetic one is unmeasured. <!-- LIP-004 LIP-012 -->
6. **Doc section: voice lines in [licensing](/guide/licensing).** Move the TTS tables there in the MusicGen shape, with per-line `sources.json` fields for model, weights revision, voice or sample provenance and consent, licence and watermark, because the voice is a licence layer the other three do not cover. Share one schema with the character-source fields [DAZ Genesis](/reference/daz-genesis#what-to-build) proposes.
7. **Experiment: jaw pixels on a real sheet.** Add a jaw by the measured rule to a bare-headed character, taking the head as the topmost bone by tail height on the articulationxl skeleton (untested), render at 220 and 128 px with the jaw at 0 and 20 degrees, and count changed pixels, to replace this note's estimate with a measurement.

   **Done on 2026-09-16.** [`scripts/face_rig.py`](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/scripts/face_rig.py) `add-jaw` places and weights the jaw, and the counts are in [faces only read on a portrait](#faces-only-read-on-a-portrait). The counts come from one generated rig, `unit_alchemist`. The topmost bone by tail height turned out not to be the head on three of the five articulationxl rigs tried, so the script picks the head by skin weight instead ([what Blender does headlessly](#what-blender-does-headlessly)). `add-jaw` checks that the jaw moves vertices before it saves anything. Still untested: its check that the chin drops rather than rises, `--front` other than `-y`, and Mixamo, mesh2motion and Genesis rigs.
8. **Experiment: face shapes onto a TRELLIS head.** Try ICT-FaceKit, with its loader fixed, and MPFB2's Meta/Oculus-style viseme pack (licence in [DAZ Genesis](/reference/daz-genesis#makehuman-and-mpfb2)), sharing the `bpy` setup that item 1 in [DAZ Genesis](/reference/daz-genesis#what-to-build) needs. Shrinkwrap and scale the template onto the head, bind with Surface Deform, apply `jawOpen` and a few mouth shapes, and check that `transfer_weights.py` keeps shape keys when it runs afterwards. Only then add shape key values to `render_sheet.py`, a change DAZ Genesis item 4 also proposes, because the transfer is measured on spheres only. <!-- LIP-064 -->

   **Partly done on 2026-09-16.** `face_rig.py transfer-shapes` binds a template with Surface Deform, applies its keys and reports how far they move in world units, and `--region` keeps them to the head; a template that cannot bind fails with Blender's `Target has edges with more than two polygons` and writes nothing. Six ICT-FaceKit mouth keys went onto the generated `unit_alchemist` head with `--region`: `jawOpen` moved 802 vertices by up to 0.0372 units, and no vertex outside the head moved. The ICT head had been placed on that model by hand in a scratch script, and at 220 px its `jawOpen` row changed 362, 128, 123 and 371 pixels per view. The shape key values in `render_sheet.py` were added too, as DAZ Genesis item 4, and render the MPFB2 visemes from a `.blend`. MPFB2's visemes were loaded onto MPFB's own body only, not moved onto a generated head. Still untested: whether `transfer_weights.py` keeps shape keys, fitting a template that is not already on the model's surface, replacing a key the model already has, and a `.glb` model or template.

## Honest uncertainty

- **Rhubarb ran on the host, not in the container**, on three clean English LibriSpeech lines plus noise, silence and tones. <!-- LIP-154 LIP-165 LIP-166 LIP-170 --> Word error rate and run-to-run determinism were measured on one line; whether the cues are accurate was not. <!-- LIP-159 LIP-161 --> Synthetic voices and non-English accuracy were not tested. Ogg Vorbis and FLAC lines went through `lipsync_cues.py` on 2026-09-16, which converts them to WAV first, so Rhubarb's own Ogg reader was not tested; line 0000 as Ogg Vorbis gave 20 cues against 22 from the WAV. The 2026-09-16 runs were on the host too.
- **The thread non-determinism mechanism is inferred, not proven.** <!-- LIP-162 -->
- **Measured since, but narrowly.** The speech gate was measured on 2026-09-16 on one speaker's lines, stretched and noise-mixed copies of them, ffmpeg noise and tones, and two generated music excerpts, which separates those cases but gives no error rate. The frame rules' drops were counted on one line. Whole-image mouth edits were measured on one portrait at one seed, with memory read for the whole shared card. Whether the inpaint patches work with Qwen-Image 2512, and how consistent inpainted mouths are, are still not measured.
- **The Blender probes used spheres.** <!-- LIP-064 LIP-067 --> Since then, on 2026-09-16, a jaw went onto five generated articulationxl rigs, ICT-FaceKit shapes went onto one generated head placed by hand, and MPFB2's face packs loaded without a UI ([DAZ Genesis](/reference/daz-genesis#makehuman-and-mpfb2)). Fitting a template to a generated head without a hand-placed start, fitting Rigify's face bones, and driving Rhubarb Lipsync NG from Python were not tried.
- **The research disagreed on the pivot set,** recommending the Oculus fifteen in one place and Rhubarb's letters in another; this note stores the letters and converts through Oculus names. <!-- LIP-059 LIP-111 -->
- **Kokoro's training data.** Its card lists CC BY recordings and synthetic audio from closed TTS models from large providers. <!-- LIP-115 --> It does not say whether attribution reaches generated speech, or whether those providers' terms allowed training on their output.
- **F5-TTS was read two ways, on a detail.** Both readings of its [card and README](https://github.com/SWivid/F5-TTS) take the pretrained weights as CC BY-NC 4.0 "due to the training data Emilia" and find `torch>=2.0.0` declared; they differ only over an early report of a PyTorch 2.4 minimum, which no file states: 2.4.0 is only its Dockerfile's base image and an older install option. <!-- LIP-125 -->
- **Zonos v0.1 is left out because its record is contested.** <!-- LIP-137 --> Both readings of [Zonos](https://github.com/Zyphra/Zonos) take its code and weights as Apache-2.0, about 1.6B parameters per model, with GPL-3.0 espeak-ng and phonemizer dependencies; they differ only on a rounded "2B" on its Hugging Face page. <!-- LIP-137 -->
- **Not checked:** Chatterbox's transformers pin against the container's 4.57.6; whether a game's players count towards Higgs TTS 2's user threshold; whether CC BY 4.0 on MFA's models reaches alignment output.
- **OpenAI's Text-to-Speech Supplemental Agreement for custom voices was not read**, and the disclosure duty appears in the TTS guide but not in the Usage Policies or Service Terms. <!-- LIP-146 -->

## Sources worth reading

- [Rhubarb Lip Sync README](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/README.adoc): the nine shapes, every flag and every output format.
- [Rhubarb LICENSE.md](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md): the cue data clause and every bundled notice.
- [Meta's viseme reference](https://developers.meta.com/horizon/documentation/unity/audio-ovrlipsync-viseme-reference): the fifteen visemes other sets convert through.
- [godot-baked-lipsync](https://github.com/fbcosentino/godot-baked-lipsync): a small, complete engine integration of Rhubarb cues.
- [diffusers QwenImageEditInpaintPipeline](https://github.com/huggingface/diffusers/blob/main/src/diffusers/pipelines/qwenimage/pipeline_qwenimage_edit_inpaint.py): what a mask protects, and what it does not.
- [Blender manual: Surface Deform](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/surface_deform.html): the bind restrictions.
- [ICT-FaceKit](https://github.com/USC-ICT/ICT-FaceKit): an MIT head with ARKit-style shapes.
- [Blizzard 2013 Lessac licence](https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html): why Piper's lessac voice is not cleared to ship.
- [FLUX.1 [dev] Non-Commercial License](https://github.com/black-forest-labs/flux/blob/main/model_licenses/LICENSE-FLUX1-dev): the full definition of Non-Commercial Purpose.
