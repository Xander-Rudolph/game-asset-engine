# Lip sync and talking portraits

::: tip Status: researched on 2026-09-15
This is research: nothing here is built or shipped, and none of the scripts, graphs or downloads it proposes exist in the repo. Rhubarb Lip Sync was run on this machine's host (peak memory on 2026-09-16), the Blender probes ran in the repo's container, and a generated rig and sprite sheet were measured. Statements marked as community reports or not checked were not verified; everything else, including every licence, was read without running it.
:::

How to make a generated character appear to talk, when its rig has no jaw, its mesh has no mouth and the repo makes no speech. Source Filmmaker's phoneme system is covered in [Source Filmmaker](/reference/source-filmmaker), and Genesis faces in [DAZ Genesis](/reference/daz-genesis).

## The short answer

- **Speech to mouth shapes: Rhubarb Lip Sync.** Its code is MIT, and the non-binding summary in its [LICENSE.md](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md) says the lip sync data it makes "belongs to you alone" (checked 2026-09-15). With `--threads 1`, which a reproducible cue file needs, a 14.22 s line took 11.02 s on this machine's CPU, about 0.78 times real time.
- **No faces on the sprite sheets.** At a 128 px cell a mouth would be about 3 to 4 px wide, an estimate scaled from the warrior sheet.
- **A talking face is a portrait:** one image, nine mouth overlays and a cue list, with no face rig. The overlay step is designed below, not tested.
- **The voice is the gate.** Rhubarb needs speech, and XTTS-v2, Fish Speech without a separate written licence from Fish Audio, and the lessac voice in Piper's CLI examples may not be used in a game you sell (checked 2026-09-15, see [text-to-speech](#text-to-speech-whose-lines-may-ship)).

## Speech to mouth shapes

Licences checked 2026-09-15 against the linked pages. Only Rhubarb was run.

| Tool | Gives you | Licence | Headless on Linux without a GPU |
|---|---|---|---|
| [Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync) 1.14.0 | Mouth cues A to H and X from WAV or Ogg Vorbis, with an optional transcript | Code: MIT. PocketSphinx and sphinxbase: CMU variation of 2-clause BSD. Acoustic model: Alpha Cephei variation of 2-clause BSD. Other bundled parts: permissive notices listed in LICENSE.md. Cue data: yours, per its non-binding summary | Command line; yes, measured below |
| [Montreal Forced Aligner](https://montreal-forced-aligner.readthedocs.io/en/latest/first_steps/index.html) 3.4.2 | Word and phone TextGrids from audio plus a transcript | Code: MIT. english_mfa v2.0.0 to v3.1.0, english_us_arpa v2.0.0 to v3.0.0 and all 27 English dictionaries: CC BY 4.0 ([mfa-models catalogue](https://mfa-models.readthedocs.io/en/latest/dictionary/English/index.html)) | Command line; yes, alignment has no CUDA flag |
| [Gentle](https://github.com/lowerquality/gentle) | Word times and phone durations, as JSON | Code: MIT. Kaldi: Apache-2.0. Model zip: no licence file; [kaldi-asr.org](https://kaldi-asr.org/models.html) says its models "may be downloaded and used for any purpose" | Command line or REST server; GPU use not stated; Docker image last updated 2017-06-05 |
| [WhisperX](https://github.com/m-bain/whisperX) on [Whisper](https://github.com/openai/whisper) | Word timestamps; Whisper's own are labelled "(experimental)" | WhisperX code: BSD-2-Clause. Default English alignment weights: MIT. OpenAI Whisper code and original checkpoints: MIT. The faster-whisper, VAD and diarisation weights it loads: their own licences, not checked | Command line; yes, with `--device cpu --compute_type int8` |
| [wav2vec2-lv-60-espeak-cv-ft](https://huggingface.co/facebook/wav2vec2-lv-60-espeak-cv-ft) | Approximate phoneme times at 20 ms steps, no words | Weights: `apache-2.0` card tag only, no LICENSE file | Python, through Transformers; GPU not checked |
| [charsiu](https://github.com/lingjzhu/charsiu) | English and Mandarin phone alignment | Code: MIT. Weights: no licence at all | Not checked |
| [allosaurus](https://github.com/xinjli/allosaurus) 1.0.2 | IPA phones with approximate times | Repository: GPL-3.0. Weights: no licence file; phone inventories from PHOIBLE (CC BY-SA 3.0) | Python package; CPU by default |
| [Papagayo-NG](https://github.com/morevnaproject-org/papagayo-ng) | A lip sync editor that runs Rhubarb or allosaurus and exports Moho, Alelo, images and JSON | Code: GPL-2.0-or-later | PySide2 GUI with no documented command line (not checked) |
| [OpenFaceFX](https://github.com/OpenFaceFX/OpenFaceFX) 0.24.0 | Conversion between viseme sets; exporters for Rhubarb, Moho, Godot, Spine, Live2D and Unity | Code: MIT | Python package needing only numpy |
| [Audio2Face-3D](https://github.com/NVIDIA/Audio2Face-3D-SDK) | Facial motion; ARKit-named weights, which only drive a character that already has matching ARKit blendshapes | SDK: MIT. Models: [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/) of 2025-10-24, "commercially usable", no claim on outputs, revocable. Audio2Emotion models: for use with Audio2Face only | No: NVIDIA GPU, CUDA 12.8 or newer below 13.0, TensorRT 10.13 or newer |
| [Oculus Lipsync](https://developers.meta.com/horizon/documentation/unity/audio-ovrlipsync-viseme-reference) 29.0.0 | 15 visemes, baked inside the Unity or Unreal editor | Unsettled. Source headers such as `OVRLipSync.h` cite the Oculus Audio SDK License 3.3, which one reading notes Meta's [3.3 page](https://developers.meta.com/horizon/licenses/audio-3.3/) calls "no longer in effect"; both treat Meta's [SDK License Agreement](https://developers.meta.com/horizon/licenses/oculussdk/), limited to "MPT Approved Products", as the cautious reading | Editor only; no Linux build; end-of-life |

No ComfyUI node wrapping Rhubarb turned up in a search (not checked). MFA's current `mfa align` form is deprecated and becomes `mfa align_legacy` in MFA 4.0, planned for the end of 2026.

**Rhubarb uses a transcript as a hint.** With `-d` it still recognises the words itself, but prefers words in the file. The default recogniser is English only; the `phonetic` recogniser is language-independent, "usually less precise", and ignores the transcript. So `-r phonetic` is the only Rhubarb route for other languages today, and its accuracy was not measured here.

**Known text does not give timings.** No text-to-speech model below was checked for per-phoneme timing output, so the measured route is to render the audio and run Rhubarb on it with `-d`. Kokoro's package is reported to make phonemes with its misaki library (not checked); if it returns them, they would give a cheap check against the cues.

**Video lip-sync models make video, not cues.** Checked 2026-09-15:

| Model | Code | Weights | In a game you sell |
|---|---|---|---|
| [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) | No licence file | README: "any form of commercial use is strictly prohibited" | Not allowed |
| [LatentSync](https://github.com/bytedance/LatentSync) 1.6 | Apache-2.0 | An `openrail++` tag, no licence text | No licence text; README minimum VRAM 18GB |
| [MuseTalk](https://github.com/TMElyralab/MuseTalk) | MIT | README: "available for any purpose, even commercially"; [weights repo](https://huggingface.co/TMElyralab/MuseTalk) tagged `creativeml-openrail-m` | Unsettled; one reading adds a face parser trained on CelebAMask-HQ, whose terms allow non-commercial research only |
| [SadTalker](https://github.com/OpenTalker/SadTalker) | [Apache-2.0](https://github.com/OpenTalker/SadTalker/blob/main/LICENSE) | Copies tagged MIT, in one reading; CC BY-NC 4.0 face-vid2vid parts, in the other | Unsettled |
| [Hallo](https://github.com/fudan-generative-vision/hallo) | [MIT](https://github.com/fudan-generative-vision/hallo/blob/main/LICENSE) | Tagged MIT; both readings find InsightFace models "for non-commercial research purposes only" | Unsettled |
| [EchoMimic](https://github.com/antgroup/echomimic) | Apache-2.0; README: "intended for academic research" | No licence stated, or Apache-2.0, by reading | Unsettled |

## Rhubarb on this machine

Run on 2026-09-15 on the reference machine's host (i7-14700K, 28 logical CPUs, glibc 2.42), outside the container, from the official Linux release with nothing installed. Timings are single runs unless repeats are given.

The release is v1.14.0 of 2025-04-03: `Rhubarb-Lip-Sync-1.14.0-Linux.zip` is 87,225,003 bytes, sha256 `a9a9074862cff47b2d59b8bf399a678a3b0b74f9452ad6ad94cb292913dd8667`, and unpacks to 166,606,778 bytes. The 7,331,192-byte `rhubarb` binary is dynamically linked, needs `GLIBC_2.29` and `GLIBCXX_3.4.26` or newer, and must sit next to the zip's 86,255,327-byte `res/sphinx/` folder; without it, both recognisers exit with code 1 on speech.

The main test line is LibriSpeech test-clean 6930-75918-0001, 14.225 s and 43 words, under [CC BY 4.0](https://www.openslr.org/12/). Utterances 0000 (3.5 s) and 0002 (5.0 s) were timed too. The 10 s test files came from ffmpeg's `sine=frequency=440:sample_rate=16000:duration=10`, `anoisesrc=colour=white:amplitude=0.3` and `anullsrc` sources, as 16 kHz mono 16-bit PCM.

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

| Run | Flags | Wall | CPU | Cues | Shapes used |
|---|---|---|---|---|---|
| Default recogniser | `-f json` | 6.51 s | 11.97 s | 85, or 87 in 4 of 14 repeats | A B C E F G H X |
| With transcript | `-d` | 6.27 s | 11.66 s | 85 or 87 | A B C E F G H X |
| One thread, with transcript | `-d --threads 1` | 11.02 s | Not checked | Byte-identical on every repeat | Not checked |
| Phonetic recogniser | `-r phonetic` | 1.01 s | 1.36 s | 101 or 102 | All nine |

**A transcript removes the recognition errors.** Without it, PocketSphinx made 9 edits over the 43 words, a 20.9% word error rate; with `-d` it made none. That changed 28 of 85 cues and 8.3% of the running time, well above the 0.5 to 2.4% by which repeat runs differ. Whether the cues became more accurate was not measured.

**The phonetic recogniser was about 6.5 times faster in wall time** than the default without a transcript (6.2 times against the run with one), and gave 16 to 20% more cues using all nine shapes. Whether its shapes are right was not measured. It ignores `-d`, but Rhubarb still reads the file first, so a missing or non-UTF-8 transcript stops even a phonetic run with exit code 1 and no output.

**Threading, not a fixed loading cost, explains the long line's speed.** Rhubarb recognises on min(`--threads`, voice-activity sections, whole seconds divided by 5) threads, so this two-section line used 2 threads even with `--threads 28`. With `-d`, the 3.5 s and 5.0 s lines took 2.89 s and 3.51 s on one thread (0.83 and 0.70 times real time), and the 14.2 s line 6.27 s on two (0.44 times) or 11.02 s on one (0.78 times). Peak resident memory per process, measured on 2026-09-16, was about 156MiB for the short lines on one thread and 311MiB for the long line on two.

Shape B, slightly open with clenched teeth, covered about 44% of the line, so it is the mouth to get right. D never appeared on this line. Rhubarb needs all six basic shapes anyway. The shortest cue was 0.06 s and the median 0.14 s.

::: warning Use `--threads 1` for any cue file you keep
With more than one recognition thread, the same command gives different files. Five runs with `--threads 2` gave 3 different cue files, disagreeing on 0.5 to 2.4% of the running time. With `--threads 1`, five runs were byte-identical, and so were six with `-d`. Lines under 10 s already run on one thread.
:::

The likely cause of the differing files is PocketSphinx's dither sharing random state between decoder threads, inferred from the source, not proven.

### Many cues are shorter than a 12 fps frame

At 12 fps, 38% of the cues from the default recogniser with transcript (32 of 85) and 48% from the phonetic one (49 of 102) last under one frame. None is shorter than a 24 fps frame. That is one line's figure, not a general rate. Rhubarb's frame format cannot help: `--datFrameRate 12` exits with code 1 and `Frame rate must be between 24 and 100 fps.` Quantise from the JSON in your own code.

`--extendedShapes` chooses which of G, H and X may appear. A disabled G or X becomes A, and a disabled H becomes C; with `--extendedShapes ""`, closed-mouth A rose from 0.65 s to 2.20 s of the line. So a set drawn without G and H still plays.

### Audio that is not speech

::: warning White noise comes back as talking
Rhubarb's voice detector took 10 s of white noise as speech. The default recogniser heard the word "think", used 6.2 s of CPU, and returned one 9.90 s B cue between two short X cues; the phonetic recogniser made 9 cues. Music was not tested, so keep music, ambience and sound effects away from Rhubarb, including tracks from [music](/guide/music).
:::

Silence and a 440 Hz sine peaking at about -18 dBFS each gave one X cue in about 0.13 s on a cold run. The same tone peaking between about -15 and -0.8 dBFS was taken as speech and came back as a C cue lasting almost the whole 10 s.

## Mouth-shape sets

Every set answers "how many mouths" differently. Checked 2026-09-15.

| Set | Shapes | Names |
|---|---|---|
| [Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/README.adoc) | 6, plus 3 optional | A to F; G, H, X |
| Preston Blair, as shipped in [Papagayo-NG](https://github.com/morevnaproject-org/papagayo-ng) | 10 | AI, O, E, U, etc, L, WQ, MBP, FV, rest |
| Fleming and Dobbs, as shipped in Papagayo-NG | 11 | MBP, NLTDR, FV, TH, GK, SH, O, EHSZ, AA, IY, rest |
| [Adobe Character Animator](https://helpx.adobe.com/adobe-character-animator/desktop/export-projects/export.html) export | 12 | Neutral, Aa, D, Ee, F, L, M, Oh, R, S, Uh, W-Oo |
| [Live2D](https://docs.live2d.com/en/cubism-sdk-manual/lipsync/) motion-sync | 6 | Silence, A, I, U, E, O |
| [VRM 1.0](https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_vrm-1.0/expressions.md) presets | 5, all vowels | aa, ih, ou, ee, oh |
| [Oculus/Meta](https://developers.meta.com/horizon/documentation/unity/audio-ovrlipsync-viseme-reference), and MPEG-4 | 15 | sil, PP, FF, TH, DD, kk, CH, SS, nn, RR, aa, E, ih, oh, ou |
| [Microsoft SAPI 5.3](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms720881(v=vs.85)) | 22 | SVP_0 (silence) to SVP_21 (p, b, m) |
| [Apple ARKit](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation) | 52 blendshapes, 27 of them mouth and jaw | jawOpen, mouthClose, mouthFunnel, mouthPucker and others |

Genesis 8, 8.1 and 9 carry the same 17 viseme dials, AA, EE, EH, ER, F, IH, IY, K, L, M, OW, S, SH, T, TH, UW and W, with no R or CH; [DAZ Genesis](/reference/daz-genesis#faces) covers how they are built. Source's phoneme table has 54 entries: 47 standard phonemes, 6 aliases that reuse standard codes, and `<sil>` ([Source Filmmaker](/reference/source-filmmaker#the-phoneme-set-and-the-vdat-chunk)).

### The mapping to adopt

**Store Rhubarb's letters.** Rhubarb produces them, engine add-ons read them, and nine is a set a model can make per character. Convert phoneme-level sources, such as an aligner, through the Oculus fifteen, which OpenFaceFX uses as its native channels. For ARKit shapes its `arkit` preset is a starting point, and like every Oculus-to-ARKit mapping it is community-made, because Meta publishes none.

The table is derived here from Rhubarb's README and animation rules, not copied. Where Rhubarb allows several shapes for a sound, the Oculus and Genesis columns give the usual one: B or F for S, CH, TH and SH, and B, E or F for R. The Genesis column has not been tried on a figure.

| Rhubarb | Mouth | Sounds | Oculus visemes | Genesis dials | Preston Blair name |
|---|---|---|---|---|---|
| X | Idle, lips closed and relaxed | Pauses | sil | All at 0 | rest |
| A | Closed, slight pressure | P, B, M | PP | M | MBP |
| B | Slightly open, clenched teeth | Most consonants (K, S, T), and EE | DD, kk, SS, CH, TH, nn, ih | K, S, SH, T, TH, EE, IH, IY | etc |
| C | Open | EH, AE, some consonants | E | EH | E |
| D | Wide open | AA | aa | AA | AI |
| E | Slightly rounded | AO, ER | oh (for AO), RR | ER | O |
| F | Puckered | UW, OW, W | ou, oh (for OW) | UW, OW, W | U |
| G | Upper teeth on lower lip | F, V | FF | F | FV |
| H | Tongue raised behind upper teeth | L held 0.2 s or longer | nn (for a long L) | L | L |

Three traps:

- **Preston Blair's E is Rhubarb's C, and Rhubarb's E exports as O.** A set named in one convention and played in the other is wrong on the vowels.
- **The CMU-39 table in Papagayo-NG's `rhubarb.json` contradicts Rhubarb.** It maps S and CH to G, TH and R to H, and L to C, where Rhubarb gives G only to F and V and forces H only for a long L.
- **Frame order differs by integration.** godot-baked-lipsync numbers the shapes X=0, A=1 through H=8, and Rhubarb's After Effects script and a community Godot add-on are reported to use other orders (not checked). A strip in the wrong order is wrong on every shape, so the manifest records it.

## How 2D games play talking portraits

Statements marked as community reports or not checked come from forums, wikis or third-party projects and were not verified.

**Driven by the text, not the audio.** Celeste's portraits have three animation prefixes per expression: `begin_` plays first, `idle_` when not talking and `talk_` while talking, and markup such as `[THEO left normal]` picks the character, side and expression. Ren'Py's `config.speaking_attribute` adds an image attribute while a character speaks, and community examples loop two or three mouth images at 0.2 to 0.3 s over a still base (not checked).

**A base plus a mouth overlay.** GBA Fire Emblem portraits are described as a base image with eye and mouth frames drawn over it at fixed coordinates, and Ace Attorney as swapping whole sprites (community reports). The overlay stores less and cannot disturb the rest of the face.

**Audio-driven playback is discrete.** [godot-baked-lipsync](https://github.com/fbcosentino/godot-baked-lipsync) (MIT, read at commit f3619c1, checked 2026-09-15) runs Rhubarb with `-f tsv --machineReadable` and bakes a mouth track with nearest interpolation and discrete updates. It emits `mouth_shape_changed(mouth_shape: int)`, its 2D example swaps a mouth Sprite2D's texture, and its editor dock downloads Rhubarb 1.13.0 rather than bundling it, keeping it out of exported games. Rhubarb's release zip ships a Spine integration in `extras/EsotericSoftwareSpine/`, and Unity importers exist as community projects (not checked).

**Live2D drives a parameter.** Basic lip sync passes a 0 to 1 level to `ParamMouthOpenY` or similar; its viseme route, motion-sync, is a proprietary plugin with no listed Linux support. **Adobe Character Animator** exports timing only by copying visemes to the clipboard, and runs only on Windows and macOS.

## A portrait, nine mouths and a timeline

A design for a talking portrait made headlessly with what the repo already runs. None of it has been built or tried.

### Faces only read on a portrait

Measured on 2026-09-15 in the first front-facing frame of `output/sheets/warrior_idle.png` (220 px cells): the figure is 176 px tall, with a closed helm about 26 to 27 px tall and no visible mouth. Taking a mouth as about a quarter of head height, a bare head that size would have a mouth about 6 to 7 px wide and a jaw that opens 1 to 2 px, while a 256 px portrait whose head fills three quarters of its height would have one about 42 to 48 px wide. At 340 px, the smallest portrait size in [facings](/guide/facings#sizes), the same rule gives about 56 to 64 px. These are estimates, not renders, but they make the talking face its own asset rather than a row on a facings sheet.

### Making the mouths

1. **Start from an approved portrait.** Make a head-and-shoulders image of 340 px or more from the approved concept with `img_edit_qwen.json` ([Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509)), ask for lips closed and relaxed, and approve it by eye. That mouth is X.
2. **Mark the mouth box.** A rectangle around mouth and chin, stored beside the portrait, guessed by script and movable by a person.
3. **Inpaint A to H inside the mask** at a fixed seed, prompted from Rhubarb's shape descriptions. The [ComfyUI Qwen-Image tutorial](https://docs.comfy.org/tutorials/image/qwen/qwen-image) loads `qwen_image_inpaint_diffsynth_controlnet.safetensors` with `ModelPatchLoader` and feeds the mask to `QwenImageDiffsynthControlnet`. [InstantX](https://huggingface.co/InstantX/Qwen-Image-ControlNet-Inpainting) publishes a 4.23GB inpainting ControlNet for base Qwen-Image, native in ComfyUI since 0.3.59. Whether either works with the Qwen-Image 2512 release the repo loads was not checked.
4. **Paste back only the mask**, so everything outside the mouth is identical by construction.
5. **Downsample last**, with the same method as the portrait.

Whole-image edits drift. The repo's concept-edit skill already records drift in untouched areas, and the cards for [Qwen-Image-Edit-2509](https://huggingface.co/Qwen/Qwen-Image-Edit-2509) and [2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) promise better consistency with no numbers. Even diffusers' `QwenImageEditInpaintPipeline` resizes the image to about 1 megapixel, and without `padding_mask_crop` the unmasked pixels come back as a VAE reconstruction, not a copy. FLUX.1 Kontext [dev]'s licence is unsettled for a game you sell ([licences](#licences)).

The set's manifest records where the mouth goes and the strip order, which follows godot-baked-lipsync's numbering. `fallback` is Rhubarb's own substitution for disabled shapes (G and X become A, H becomes C). With G, H and X all disabled (`--extendedShapes ""`), the measured line gave 86 cues rather than 85.

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

### The timeline file

Keep Rhubarb's JSON and add fields around it. Papagayo-NG reads its `mouthCues` array of `start`, `end` and `value`; godot-baked-lipsync reads the TSV form instead. Rewrite `metadata.soundFile`, which Rhubarb writes as an absolute path.

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

**Frames only for baked animation.** An engine that keys on cue times, as godot-baked-lipsync does, needs no frames. Write `fps` and `frames` only for a baked, frame-based animation; 12 fps is an example. Sampling each frame at its midpoint can drop up to the 38% of cues shorter than a 12 fps frame on the measured line; the actual drop rate was not counted. A lost P, B or M closure is the likeliest to show, so a second rule to try is that any frame containing an A cue shows A. Neither rule has been looked at on a portrait.

**With no voice.** Until lines have audio, write the same file from the text: alternate two or three open shapes at a fixed interval while the text prints, and end on X. That is the text-driven pattern above. No interval has been tried here, and the Ren'Py figures above are community reports, not checked.

## Faces on generated meshes

This only pays off for a 3D portrait renderer, given the pixel figures above. `scripts/render_sheet.py` poses bones only and has no shape key support, so playing visemes on a mesh would also need that added. [Rigging](/guide/rigging) covers the body rig.

### The riggers give you no face

- **UniRig articulationxl.** A generated warrior's rig has 28 bones named `bone_0` to `bone_27`, none of them jaw, eye, mouth or face bones, and a 19,943-vertex mesh with no shape keys; another articulationxl warrior has 47 bones. Measured in bpy 4.5.9.
- **mesh2motion.** The human rig's head chain is `neck_01`, `head`, `head_leaf`, with no jaw, eye or mouth joints and zero morph targets, and rigging runs only in a browser.
- **Meshy.** Its docs mention no face bones, blendshapes or morph targets, and its FAQ answers "Not directly" to rigging facial expressions. Tripo and Mixamo are reported to emit no face either (not checked).

### What Blender does headlessly

The jaw, Surface Deform, glTF and Rigify results were measured on 2026-09-15 in `asset-engine-comfy:0.1.1` (bpy 4.5.9 LTS, background mode), on test spheres and Rigify's Human metarig. Bind restrictions, Data Transfer, Rigify's face requirements and the add-ons were read from the Blender manual, source and add-on pages, checked 2026-09-15.

**A jaw bone placed by rule works.** A `jaw` bone parented to a bone named `head`, weighting vertices low and to the front with a 0.3-unit fade, moved 123 of 642 vertices when rotated 20 degrees.

**A shape key transfers with Surface Deform.** `bpy.ops.object.surfacedeform_bind` bound a 642-vertex sphere to a 1,106-vertex template whose `jawOpen` key moved vertices 0.3 down, and `bpy.ops.object.modifier_apply_as_shapekey` turned the deformation into a new key of about 0.30 at most. The key takes the modifier's name, so rename it. The bind's restrictions fall on the template: no edges shared by more than two faces, no concave faces, no doubled vertices and no faces with collinear edges.

**Data Transfer cannot copy shape keys.** It copies vertex groups, UVs, colour attributes and custom normals, so it suits jaw weights, not blendshapes.

**Both survive glTF.** Bones, vertex groups and `jawOpen` came back after `export_scene.gltf(export_morph=True)` and re-import, but the mesh returned with 3,840 vertices instead of 642, so vertex indices do not survive.

**Rigify generates headlessly but does not fit.** Enabling the add-on, adding the Human metarig and calling `rigify.generate.generate_rig` built a 706-bone rig with `jaw_master` and `DEF-jaw` in about 2.2 to 2.3 s. The metarig uses the deprecated `faces.super_face` rig; after Upgrade Face Rig, the modular jaw rig needs four lip chains meeting at the mouth corners, or generation stops with `Could not find all mouth corners`. Rigify cannot fit the face bones automatically, so every generated head would need its jaw and lip chains moved by hand from fixed human-sized positions.

**The facial add-ons need a person.** [Faceit](https://faceit-doc.readthedocs.io/en/latest/landmarks/) (US$78 to US$289 by tier on [Gumroad](https://fbra.gumroad.com/l/Faceit)) makes the 52 ARKit shape keys only after the user places landmarks by hand, with no documented headless mode. Auto-Rig Pro's facial markers are placed or refined by hand, and its [licences](https://www.lucky3d.fr/auto-rig-pro/doc/license.html) mix GPL-3.0 for the bpy-derived source in `src`, a proprietary per-device AI binary, and assets that "may not be extracted for use in other projects". [Rhubarb Lipsync NG](https://github.com/Premik/blender_rhubarb_lipsync_ng) (MIT) bakes a user-chosen Action per cue to NLA strips on an armature or shape-key mesh, from sidebar panels. Its Linux zip bundles `rhubarb` and its CI runs the operators headless, but no scripted workflow is documented and every version test ran on Windows.

### Heads to borrow shapes from

Checked 2026-09-15 against the linked licence pages. Genesis heads are covered in [DAZ Genesis](/reference/daz-genesis).

| Head | Shapes | Licence and what it covers | In a game you sell |
|---|---|---|---|
| [ICT-FaceKit](https://github.com/USC-ICT/ICT-FaceKit), light release | 53 ARKit-style expressions, with no `tongueOut` | MIT, covering code, head mesh and morph data; the notice is embedded in the OBJ files. The Full ICT Face Model, promised under a separate USC licence, is not covered | Allowed with the MIT notice. With no tongue shape, H falls back to C, as Rhubarb substitutes when H is disabled. Its Blender script needs `bpy.ops.import_scene.obj` changed to `bpy.ops.wm.obj_import` for Blender 4.5 |
| [MPFB2](https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md) | Face packs as shape keys: see [DAZ Genesis](/reference/daz-genesis#makehuman-and-mpfb2) | Code: GPL-3.0-or-later. Bundled assets, including base mesh and expressions: CC0 1.0. The three face packs, downloaded separately: CC0 1.0. Other separately downloaded packs keep their own licences. No claim on output | Bundled assets and the three face packs allowed; check any other pack's licence. Not run in the container |
| [Filmic Worlds "colin"](https://filmicworlds.com/blog/solving-face-scans-for-arkit/) | 52 ARKit shapes in `colin_dst_rig.fbx` | CC0 1.0 for John Hable's rights in a scanned head | Unclear. CC0 does not clear the scanned person's likeness or FaceCap's possible rights, and the author says lips and eyelids need fixing |
| [FLAME](https://flame.is.tue.mpg.de/modellicense.html) 2017 to 2023 | Not checked | Academic Model License, for the models and add-on | Not allowed |
| FLAME 2023 Open | Not checked | Open Model License, which the site calls CC BY 4.0, plus bans on pornographic, fake, libellous, misleading or defamatory use | Allowed with attribution, after registration |
| [MetaHuman](https://www.metahuman.com/license) | Not checked | Unreal Engine EULA, update 21 (code), and the Epic Content License Agreement with its MetaHuman Content Addendum (content) | Unsettled; [DAZ Genesis](/reference/daz-genesis#metahuman) sets out both readings, including the AI and database ban. Use as a shape donor not checked |
| A free [Gumroad "MetaHuman Head"](https://dragonboots.gumroad.com/l/metahumanhead) | 52 ARKit shapes taken from MetaHuman's rig | No licence; "intended for study purposes only" | Not allowed |

## Text-to-speech whose lines may ship

As with MusicGen on the [licensing](/guide/licensing#music-and-sound) page, many open voices pair permissive code with restricted weights or training data. TTS adds a fourth layer on top of code, weights and output: the voice itself, whether a trained preset or a sample you clone.

Checked 2026-09-15 against the linked licences, cards and terms, which change. Nothing in this section was run.

### Allowed

| Option | Licence | Voices |
|---|---|---|
| [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) v1.0 | Weights: Apache-2.0. The card says training used permissive or non-copyrighted audio, including some CC BY recordings and synthetic audio from closed TTS models from large providers. Package licence not checked | 54 presets, 8 languages, no cloning |
| [Chatterbox](https://huggingface.co/ResembleAI/chatterbox) | Code and weights: MIT, including Multilingual (23 languages) and Turbo (English) | Zero-shot cloning. The official package's `generate()` adds Resemble's Perth watermark to every output; it is not in the weights |
| [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) | Code and weights: Apache-2.0 | 10 languages; Base models clone from 3 seconds |
| [Parler-TTS Mini v1](https://huggingface.co/parler-tts/parler-tts-mini-v1) | Code and weights: Apache-2.0 | English, voice from a text description, no cloning |
| [MeloTTS](https://github.com/myshell-ai/MeloTTS) | Code and checkpoints: MIT. BERT models fetched at run time keep their own licences | English, Spanish, French, Chinese, Japanese, Korean |

Chatterbox's "Llama backbone" carries no Meta weights: its shape matches no Meta release, so the Llama licence does not attach.

### Allowed with conditions

| Option | Licence | Condition |
|---|---|---|
| [Kyutai TTS 1.6B](https://huggingface.co/kyutai/tts-1.6b-en_fr) | Weights: CC BY 4.0. Code: MIT for Python, Apache (version not recorded) for the Rust backend | Voices are licensed per folder in [kyutai/tts-voices](https://huggingface.co/kyutai/tts-voices): CC0 `voice-donations`; CC BY 4.0 `vctk`, `cml-tts/fr`, `alba-mackenna`; CC BY-NC 4.0 `expresso` and `ears`, which a sold game may not use; `unmute-prod-website` mixed, including a non-commercial clip. CC BY weights and voices need attribution |
| [NeuTTS Air](https://huggingface.co/neuphonic/neutts-air) | Weights: tagged apache-2.0. Code: [NeuTTS Open License v1.0](https://github.com/neuphonic/neutts/blob/main/LICENSE) since 2026-01-14 | The code licence allows commercial use of code, derivatives and outputs only while annual revenue is under US$5,000,000, and ends automatically on breach; commits before 2026-01-14 are Apache-2.0. Perth watermark by default, skipped with only a warning if resemble-perth fails to import |
| [IndexTTS-2](https://github.com/index-tts/index-tts/blob/main/LICENSE) | bilibili Model Use License Agreement, code and weights | A separate licence above 100 million MAU or a revenue threshold the prevailing Chinese text puts at RMB 100 million. Outputs may count as Derivative Works, with contract and notice duties |
| [ElevenLabs](https://elevenlabs.io/terms-of-use) | Service terms of 2026-03-31 | Paid plans only; Studio is non-commercial except on Enterprise. No AI training on output. Clone only voices you are authorised to use. ElevenLabs takes a perpetual, irrevocable, royalty-free licence to your input and output (section 4(d)), and output may not be unique (section 10) |
| [OpenAI TTS](https://developers.openai.com/api/docs/guides/text-to-speech) | Its TTS guide; the Usage Policies it cites do not repeat the rule | Tell players the voice is AI-generated. Custom voices need the owner's consent recording |

### Not allowed

| Option | Licence | Why |
|---|---|---|
| [XTTS-v2](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt) | Coqui Public Model License 1.0.0, weights and output | Non-commercial only, and its notice duty reaches output |
| [Fish Speech](https://github.com/fishaudio/fish-speech/blob/main/LICENSE) and OpenAudio S1-mini | Fish Audio Research License for code and weights on the main branch since 2026-03-10; S1-mini weights CC BY-NC-SA 4.0 | Commercial use needs a separate written licence from Fish Audio |
| [F5-TTS](https://huggingface.co/SWivid/F5-TTS) pretrained weights | Weights: `CC-BY-NC-4.0` in [TTS-Audio-Suite's licence table](https://github.com/diodiogod/TTS-Audio-Suite/blob/main/LICENSE); the card is under [Honest uncertainty](#honest-uncertainty) | Non-commercial |
| Piper `en_US-lessac` | Dataset: [Blizzard 2013 Research Licence Agreement](https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html), research purposes only. Weights: `rhasspy/piper-voices` tagged MIT, which does not clear the data | Excludes any commercial purpose |
| Piper `en_US-libritts_r` | Its [MODEL_CARD](https://huggingface.co/rhasspy/piper-voices/raw/main/en/en_US/libritts_r/medium/MODEL_CARD) lists CC BY 4.0 data, but the voice was fine-tuned from lessac | Inherits lessac's terms |

### Unsettled

::: danger Unsettled is not the same as allowed
Each of these has a permissive-looking licence and a statement pointing the other way, or was read two ways. Don't ship lines from them in something you sell.
:::

- **Bark.** Code and weights are MIT, and the README says "available for commercial use"; the [card](https://huggingface.co/suno/bark) says "This model is meant for research purposes only".
- **VibeVoice-1.5B.** Tagged MIT, but its [card](https://huggingface.co/microsoft/VibeVoice-1.5B) says it "is limited to research purpose use", and Microsoft removed the TTS code on 2025-09-05.
- **Dia and Dia2.** Apache-2.0 code and weights, but the [README](https://github.com/nari-labs/dia) calls the model "intended for research and educational use" and forbids audio resembling real people without permission. Dia2 also loads a CC BY 4.0 codec and clones through AGPL-3.0 whisper-timestamped.
- **StyleTTS 2.** [MIT code](https://github.com/yl4579/StyleTTS2); the pre-trained checkpoints have no licence. The README's only condition covers cloning a voice outside the training set: have the owner's permission, or say the speech is synthesised.
- **Sesame CSM-1B.** [Weights](https://huggingface.co/sesame/csm-1b) tagged apache-2.0, but its [reference code](https://github.com/SesameAILabs/csm) loads a tokeniser from Meta's gated Llama-3.2-1B repo, and whether Llama terms reach the weights is unresolved.
- **Orpheus 3B.** The [card](https://huggingface.co/canopylabs/orpheus-3b-0.1-ft) is tagged apache-2.0, but a Canopy Labs collaborator said in [issue #29](https://github.com/canopyai/Orpheus-TTS/issues/29) and #33 that the weights fall under the Llama 3.2 Community License. Both readings treat them that way, and the release meets none of its agreement copy, "Built with Llama" or naming terms.
- **Higgs TTS 2 and 3.** Both readings put [v2](https://huggingface.co/bosonai/higgs-tts-2-3b-base) under the Boson Higgs Audio 2 Community License, with an expanded licence above 100,000 annual active users and attribution to Boson and Meta Llama 3, and the [Higgs TTS 3](https://huggingface.co/bosonai/higgs-tts-3-4b) speech model under a Research and Non-Commercial License. One also notes separate Apache-2.0 "Higgs Audio v3 STT" checkpoints.
- **Kyutai Pocket TTS.** One reading: an English CPU model with CC BY 4.0 weights and MIT code. The other: its [card](https://huggingface.co/kyutai/pocket-tts) is out of date, the repository ships six languages, and some preset voices are non-commercial.

::: danger Piper's example voice was trained on research-only data
Piper's code moved from MIT [rhasspy/piper](https://github.com/rhasspy/piper), archived 2025-10-06, to GPL-3.0 [piper1-gpl](https://github.com/OHF-Voice/piper1-gpl). `en_US-lessac-medium`, the voice in Piper's CLI examples, was trained on research-only data, although the voices repo is tagged MIT.

Other voices are unsettled. One reading trusts [VOICES.md](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md), which says each MODEL_CARD "contains important licensing information"; the other finds most cards license the dataset, not the weights, and about 90 voices fine-tuned from lessac or ryan (CC BY-NC-SA 4.0) that do not pass those terms on. `en_GB-alan` is not clean on either reading: both variants list Mycroft's `apope_low`, whose [LICENSE](https://github.com/MycroftAI/mimic3-voices/blob/master/voices/en_UK/apope_low/LICENSE) reads "All Rights Reserved", and were fine-tuned from lessac and ryan.
:::

### Fitting the container

The container runs Python 3.11 with pip constraints of torch 2.6.0 and transformers 4.57.6 on cu124, and the host's 550 driver caps CUDA at 12.4 ([docker](/reference/docker)). None of these was installed.

| Option | Declared requirements | In this container |
|---|---|---|
| Kokoro | Python 3.10 to 3.13, torch unpinned (not checked) | Not tried |
| Chatterbox | torch 2.6.0 pinned (not checked) | Not tried; its transformers pin not checked |
| Qwen3-TTS | transformers 4.57.3 pinned, torch not pinned | Clashes with the container's transformers 4.57.6 |
| Dia | torch 2.6.0 pinned, CUDA 12.6 wheels | Not tried |
| Dia2 | torch 2.8.0 or newer, CUDA 12.8 or newer | No |
| IndexTTS-2 | PyTorch 2.8 wheels for CUDA 12.8 | No |
| NeuTTS Air | Real time on CPU, per its README | Not tried |
| MeloTTS | "Fast enough for CPU real-time inference", the README's own claim | Not tried |
| TTS-Audio-Suite, a ComfyUI pack of 16 TTS engines | Python 3.12 or higher in its README; its installer does not check | Unsupported on 3.11, not proven to fail |

## Licences

What a talking portrait might ship, checked 2026-09-15 against the pages linked above.

| What ships | Licence, and what it covers | What you owe |
|---|---|---|
| Rhubarb cue files, and frames made from them | [LICENSE.md](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md)'s summary, "not legally binding", says the data "belongs to you alone"; the binding MIT text asks for its notice only in copies or substantial portions of the Software | Nothing |
| The `rhubarb` binary and `res/`, for runtime lip sync or inside a published image | Code: MIT. Statically linked PocketSphinx and sphinxbase: CMU variation of 2-clause BSD. Acoustic model: Alpha Cephei variation of 2-clause BSD. Other bundled parts: MIT, BSD, Boost, Unicode and WTFPL notices listed in LICENSE.md | Rhubarb's whole LICENSE.md: the MIT notice, plus the notice, conditions and disclaimer of every bundled component it lists (Boost, PocketSphinx, sphinxbase, the CMU acoustic model, Flite, WebRTC, utf8proc and its Unicode data, libogg, libvorbis and others). Flite also requires modified files to be marked, its authors' names kept, and no endorsement in their names |
| Frames rendered in Blender | [Blender](https://www.blender.org/about/license/): source GPL-2.0-or-later, binaries GPL-3.0-or-later; what you create with it is "your sole property" | Nothing |
| Overlays from Qwen-Image-Edit 2509 or 2511, or the Qwen-Image inpaint ControlNets | Weights: Apache-2.0 (the Qwen-Image-Edit 2509 and 2511 cards; the tag on Comfy-Org's DiffSynth ControlNet repo; the tag on InstantX's card), which says nothing about generated images | Nothing stated |
| Shape keys transferred from ICT-FaceKit | MIT, covering its mesh and morph data | The MIT notice, on the cautious reading that transferred shapes carry its data |
| Voice lines | Per model and per voice | See [text-to-speech](#text-to-speech-whose-lines-may-ship) |

**GPL tools.** Papagayo-NG is GPL-2.0-or-later, so at most run it as a separate, unmodified program. The allosaurus repository is GPL-3.0, [phonemizer](https://github.com/bootphon/phonemizer) and [espeak-ng](https://github.com/espeak-ng/espeak-ng) are GPL-3.0-or-later, and piper1-gpl is GPL-3.0. Whether their licences reach the data they produce was not checked. Don't copy their code or tables into the repo or a game.

**Whether the Rhubarb archive as a whole is permissive is unsettled.** Both readings agree LICENSE.md lists only permissive parts, and that the zip's unlisted `extras/EsotericSoftwareSpine/rhubarb-for-spine-1.14.0.jar` bundles OpenJFX (GPL-2.0 with Classpath Exception) and javax.json (CDDL-1.1 or GPL-2.0); they differ on whether the archive can still be called permissive. Copying only `rhubarb`, `res/` and `LICENSE.md` sidesteps it.

**FLUX.1 Kontext [dev] is unsettled.** Under the [FLUX.1 [dev] Non-Commercial License v1.1.1](https://github.com/black-forest-labs/flux/blob/main/model_licenses/LICENSE-FLUX1-dev) you "may use Output for any purpose (including for commercial purposes), except as expressly prohibited herein", but section 4(a) bans use "for any commercial or production purposes". One reading calls Outputs made while developing a sold game not clearly covered; the other says that work needs a commercial licence from BFL. Treat it as the licensing page treats MusicGen.

## What not to do

**Do not rig faces for the sprite sheets.** A mouth at 128 px would be a few pixels wide ([faces only read on a portrait](#faces-only-read-on-a-portrait)).

**Do not run Rhubarb on music or noise.** Its voice detector accepts white noise as speech ([audio that is not speech](#audio-that-is-not-speech)).

**Do not keep cue files made on more than one thread.** The same command gives different files.

**Do not ask the `dat` export for sprite frame rates.** It refuses anything under 24 fps.

**Do not copy Papagayo-NG's mapping tables.** They ship in a GPL-2.0-or-later program, and its CMU-39 Rhubarb table contradicts Rhubarb.

**Do not use video lip-sync models for game assets.** They make video, not cues, and their weight licences are prohibitive, unpublished or unsettled.

**Do not trust a licence tag alone.** NeuTTS Air's weights are tagged apache-2.0 while its code carries a revenue cap, and Piper's voices repo is tagged MIT over a voice trained on research-only data. A ComfyUI node's MIT licence does not cover the weights it downloads either; the F5-TTS node's README is reported not to say they are non-commercial (not checked).

**Do not ship lines from XTTS-v2, Fish Speech (without Fish Audio's written licence), F5-TTS's pretrained weights or Piper's lessac voice.** Their weights or training data bar commercial use.

**Do not borrow shapes from FLAME's academic models or a free MetaHuman-derived head.** FLAME's Academic Model License forbids commercial products, and the free head has no licence at all.

**Do not build on Oculus Lipsync.** It is end-of-life with no Linux build.

## What to build

Ranked. None duplicates an existing script.

1. **`scripts/lipsync_cues.py`, with Rhubarb in the image.** Add a Dockerfile step that keeps only `rhubarb`, `res/` and `LICENSE.md` (about 94MB of the 167MB unpacked), and put Rhubarb's notices in `NOTICE` and `CREDITS.md`, because a published image redistributes the binary ([redistributing](/guide/redistributing)). The binary needs `GLIBC_2.29` and `GLIBCXX_3.4.26` or newer. The image's base is Ubuntu 22.04 (the Dockerfile's `CUDA_TAG`). Whether its glibc and libstdc++ meet that floor was not recorded, and the binary has not been run in the container. The script converts a line to 16 kHz mono WAV, runs `rhubarb -f json -d <line>.txt --threads 1 --logFile <line>.log --logLevel Trace`, rewrites `soundFile` and writes the timeline; `--text-only` writes the text-driven flap. As an untested speech gate, it compares the log's `##word` lines with the text and refuses a poor match, or a single cue over most of the file. Keep the 10 s silence and sine WAVs as fixtures that should each give one X cue. Run lines as separate one-thread processes at about 156MiB each; parallel runs were not measured. It is the one measured, licence-clear route, and the wrapper handles the thread, path and frame-rate traps measured here.
2. **Experiment: masked mouth edits on one portrait.** Run A to H through the ComfyUI inpaint ControlNet and as whole-image edits through `img_edit_qwen.json`, recording VRAM and seconds per shape on the 16GB card, mean pixel difference outside the mouth box, and which shapes read at 340 px, because the design rests on the mouths matching and no model card gives a number.
3. **`scripts/compose_mouths.py`, with a mouth-set check in `sheet_check.py`.** Crop, paste back, write overlays and a manifest with `order` and `fallback`, and confirm every pixel outside the mask is identical, because that guarantee should be checked by number rather than by eye.
4. **Experiment: a generated voice through Rhubarb.** Install Kokoro and Chatterbox without moving torch or transformers, or in their own virtual environments as separate processes if a pin clashes. Speak the LibriSpeech transcript and rerun the Rhubarb commands and word check, because Rhubarb was only measured on human recordings.
5. **Experiment: non-English lines.** Run one CC0 or CC BY line in another language through `-r phonetic` and through wav2vec2-lv-60-espeak-cv-ft with `output_char_offsets`, mapped to the nine cues by a small IPA table, and count visibly wrong shapes, because the English recogniser cannot be used and the phonetic one is unmeasured.
6. **Doc section: voice lines in [licensing](/guide/licensing).** Move the TTS tables there in the MusicGen shape, with per-line `sources.json` fields for model, weights revision, voice or sample provenance and consent, licence and watermark, because the voice is a licence layer the other three do not cover. Share one schema with the character-source fields [DAZ Genesis](/reference/daz-genesis#what-to-build) proposes.
7. **Experiment: jaw pixels on a real sheet.** Add a jaw by the measured rule to a bare-headed character, taking the head as the topmost bone by tail height on the articulationxl skeleton (untested), render at 220 and 128 px with the jaw at 0 and 20 degrees, and count changed pixels, to replace this note's estimate with a measurement.
8. **Experiment: face shapes onto a TRELLIS head.** Try ICT-FaceKit, with its loader fixed, and MPFB2's Meta/Oculus-style viseme pack (licence in [DAZ Genesis](/reference/daz-genesis#makehuman-and-mpfb2)), sharing the `bpy` setup that item 1 in [DAZ Genesis](/reference/daz-genesis#what-to-build) needs. Shrinkwrap and scale the template onto the head, bind with Surface Deform, apply `jawOpen` and a few mouth shapes, and check that `transfer_weights.py` keeps shape keys when it runs afterwards. Only then add shape key values to `render_sheet.py`, a change DAZ Genesis item 4 also proposes, because the transfer is measured on spheres only.

## Honest uncertainty

- **Rhubarb ran on the host, not in the container**, on three clean English LibriSpeech lines plus noise, silence and tones. Word error rate and run-to-run determinism were measured on one line; whether the cues are accurate was not. Synthetic voices, Ogg input and non-English accuracy were not tested.
- **The thread non-determinism mechanism is inferred, not proven.**
- **The speech gate, the quantisation rules, mouth-inpaint consistency and VRAM** have not been measured, nor whether the inpaint patches work with Qwen-Image 2512.
- **The Blender probes used spheres.** Surface Deform on a real TRELLIS head, fitting Rigify's face bones, loading MPFB2's face packs without a UI, and driving Rhubarb Lipsync NG from Python were not tried.
- **The research disagreed on the pivot set,** recommending the Oculus fifteen in one place and Rhubarb's letters in another; this note stores the letters and converts through Oculus names.
- **Kokoro's training data.** Its card lists CC BY recordings and synthetic audio from closed TTS models from large providers. It does not say whether attribution reaches generated speech, or whether those providers' terms allowed training on their output.
- **F5-TTS was read two ways, on a detail.** Both readings of its [card and README](https://github.com/SWivid/F5-TTS) take the pretrained weights as CC BY-NC 4.0 "due to the training data Emilia" and find `torch>=2.0.0` declared; they differ on whether PyTorch 2.4, used by its Dockerfile, is a tested version.
- **Zonos v0.1 is left out because its record is contested.** Both readings of [Zonos](https://github.com/Zyphra/Zonos) take its code and weights as Apache-2.0, about 1.6B parameters per model, with GPL-3.0 espeak-ng and phonemizer dependencies; they differ only on a rounded "2B" on its Hugging Face page.
- **Not checked:** Chatterbox's transformers pin against the container's 4.57.6; whether a game's players count towards Higgs TTS 2's user threshold; whether CC BY 4.0 on MFA's models reaches alignment output.
- **OpenAI's Text-to-Speech Supplemental Agreement for custom voices was not read**, and the disclosure duty appears only in the TTS guide.

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
