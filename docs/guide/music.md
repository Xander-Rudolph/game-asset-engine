# Music

*Instrumental game music from a caption with ACE-Step 1.5, and a tool that
turns each track into a loop a game can play forever.*

Everything below was run on a 16GB card in a container shared with other
jobs. Each section says what failed and what worked instead.

## Why ACE-Step 1.5

The weights are **MIT**, and the model card says the music it makes may be
used commercially. It also says the model was trained on licensed,
royalty-free and synthetic music. Meta's MusicGen, the best-known open music
model, is non-commercial ([licensing](/guide/licensing#music-and-sound)).

It runs on ComfyUI's own nodes in this image, so there is nothing to install
but the weights:

```sh
scripts/fetch_models.py --download --group music
```

That is four files, about 10GB: the music transformer (4.8GB), a 0.6B text
encoder (1.2GB), a 1.7B planner model (3.7GB) and the audio VAE (0.3GB).
ComfyUI also publishes an all-in-one checkpoint of the same four parts. It
can't be used here, for the reason in the next section.

## Keep the text encoders on the CPU

The first run took the whole server down. The text encoder node can run the
1.7B planner to lay out the track before the music is generated. On this
image's PyTorch 2.6, sampling that planner on the GPU produced NaN
probabilities, and the CUDA assert that caught them (`probability tensor
contains either inf, nan or element < 0`) aborted the ComfyUI process. The
container restarted, and every job queued behind it failed too, including
other projects' jobs on the same server.

It is a known bug ([Comfy-Org/ComfyUI#12274](https://github.com/Comfy-Org/ComfyUI/issues/12274),
open). The maintainer's answer is a newer PyTorch, which this image can't take
without rebuilding its compiled 3D extensions.

What works is loading the text encoders with `DualCLIPLoader` set to the CPU.
That is why the split files: the checkpoint loader has no device option. On an
i7-14700K the planner sampled 725 audio codes in 5 minutes 38 seconds, about
2.3 seconds of CPU per second of music. Setting the temperature to 0 also
avoids the assert, but upstream reports it gives a single held note.

## The planner: on for anything with a tune

The planner is the 1.7B model that lays a track out before the music is made.
ACE-Step's own tutorial says the codes it writes carry the melody and the
orchestration, and ComfyUI's tooltip for the switch says it "will increase the
quality". A listening test agreed. A game score made without it kept its
ambient and dark-ambient beds, and had its menu theme, its chamber piece and
both battle tracks rejected by ear.

**Off, it is fine for beds, and fast.** A take cost about 7 seconds of GPU
when the queue was clear. Most takes still opened quietly and built: the loop
search started 45 of 67 loops 10 seconds or more into the take. Captions
written around what carries through the whole piece ("built on a continuous
low drone that sustains throughout", "a slow, unbroken heartbeat pulse")
brought the six swingiest tracks from 9 to 23 LU down to 6.7 to 11.6 LU.

**On, with only `[Instrumental]` for lyrics, it writes a song**: an intro,
breaks and an ending. Two menu-theme takes came back with 21 and 27 seconds of
silence in the middle.

**On, with a section script, it holds together.** The lyrics are the track's
timeline, and [a track file](#prompts) can carry a script of themes and
variations with no intro, breakdown, ending or silence section. Six battle
takes out of six held together, at loudness ranges of 2.4 to 9.2 LU, one with
a 2.5-second stop.

**A slow theme still falls apart, so give it a pulse.** The same kind of
script on a 76 bpm orchestral theme gave takes with 30 seconds and more of
silence and an early ending, and a 68 bpm chamber piece had gaps of 1 to 4
seconds in two takes of three. The theme rewritten as a march at 96 bpm over a
steady string ostinato and snare came back continuous both times, at 7.8 and
11.7 LU.

In this image the planner runs on the CPU (see above): about 4.5 minutes for a
150-second take, holding the ComfyUI queue the whole time, so on a shared
server say so before queueing a batch. The graph leaves it off; turn it on for
a track with `planner: yes`.

## The graph

`workflows/api/txt2music_acestep15.json` uses the official ComfyUI template's
settings: 8 steps, guidance 1.0, euler with the simple scheduler, AuraFlow
sampling shift 3 and a zeroed negative. The node titles for `--set` are
`Music`, `Length`, `Sampler` and `Save`.

Six things about it that cost a run each:

- **There is no negative prompt.** Say only what the track should be. Put
  `[Instrumental]` in the lyrics, and don't write "no vocals" in the caption:
  [naming a thing summons it](/guide/concept-art#what-a-good-prompt-for-this-pipeline-says).
- **The length is set in two places.** `Music.duration` and `Length.seconds`
  are separate inputs and nothing ties them together.
- **The time signature is a menu of strings.** Pass `"4"` JSON-quoted to
  `--set`, or `run_workflow.py` turns it into a number the menu refuses.
- **Audio saves as `<prefix>_00001.flac`**, with no trailing underscore. Image
  saves are `<prefix>_00001_.png`, so a script looking for `_00001_.` finds
  nothing.
- **Save FLAC.** The loop and encode step should start from lossless audio.
- **Take the files the prompt saved, not the last path printed.**
  `run_workflow.py` lists the prompt's own outputs first, read from the
  server's history, then every other file written to `output/` while it
  waited, each with its size after it. On a shared server that means other
  people's files, and often the previous take still finishing its write.
  Taking the last `.flac` printed looped seed 2's take a second time in place
  of seed 3's.

## Prompts

`scripts/generate_music.py` runs a whole folder of track files. A track file
is settings, a blank line, then the caption:

```
bpm: 92
key: G major
time: 4
seconds: 200
seed: 1
lufs: -16

Pastoral folk: open, sunlit exploration music. Acoustic guitar and hammered
dulcimer, a gentle wooden flute melody, soft string pads and a light hand
drum, hopeful and unhurried.
```

Below the caption, a line of three dashes can start the lyrics. For ACE-Step
the lyrics are the track's timeline, and for an instrumental loop that means a
section script: one structure tag per section, a blank line between.

```
bpm: 120
key: C minor
time: 4
seconds: 150
seed: 1
lufs: -14
planner: yes

Dark medieval battle music, grim and aggressive, frame drums and low toms,
galloping cellos and basses, a snarling low brass motif, gritty, punchy,
polished mix.
---
[Main Riff - frame drums and galloping cellos]

[Brass Motif - aggressive]

[Main Riff - low toms and basses]

[Brass Motif - aggressive]
```

Keep each tag to a section name and one hint, and name the instruments the
caption names: ACE-Step's tutorial warns that a stack of adjectives in a tag
can be sung, and that tags which contradict the caption confuse it. Leave out
`[Intro]`, `[Breakdown]`, `[Outro]`, `[Fade Out]` and `[Silence]`; without a
script the planner writes those on its own.

A `_style.txt` in the folder is added after every caption. The one in
`prompts/music/` asks for "an even, steady piece that holds one intensity from
start to finish", which is what a loop wants. It says so positively, as
everything in a caption should.

Write captions the way ComfyUI's own templates do: a genre label, then a
sentence or two on mood, instruments and pace.

```sh
scripts/generate_music.py prompts/music                        # every track
scripts/generate_music.py prompts/music battle --takes 3       # three seeds
scripts/generate_music.py my_game/music --takes 3 --loop out/music --keep-best
```

## Making it loop

`scripts/make_loop.py` turns a take into a file a game can loop. What it does,
and what each step measured:

- **It trims both ends.** Silence comes off the front. The ending comes off
  the back: the cut falls after the last second within 6 dB of the take's
  typical level, so a fade or a final chord goes.
- **It chooses where the loop starts, not just where it ends.** A take opens
  quietly and builds, planner or not, and the first version of this tool
  looped from the first bar: 10 of 14 takes came round with a drop of 6 to
  20 dB. The start is now searched over the first 30% of the take and the end
  over the last 30%. Each pair is scored on the jump in level where the loop
  comes round, on either passage sitting under the take's typical level, on
  how well the rhythm of the two crossfaded passages matches, and lightly on
  length. On the same 14 takes every restart came in within 0.4 dB, and the
  rhythm match rose from 0.23–0.70 to 0.36–0.92. The start it chose was 2 to
  58 seconds in.
- **It keeps silence out of the loop.** A take that stops dead part way, as
  planner takes often do, is searched a stretch at a time between its
  silences. A battle take with a 2.5-second stop gave a 76-second loop from
  the stretch after the stop, where it had given a 128-second loop with the
  stop inside. If no stretch is long enough the whole take is used, and the
  report still says the loop holds a gap.
- **It crossfades for how alike the two passages are.** Two rhythm-matched
  passages are partly in phase, so a plain equal-power crossfade rose 0.8 dB
  where they overlapped (correlation 0.30). Gains scaled for the measured
  correlation rose 0.1 dB. The report also gives the crossfade's dip, against
  the quieter of the bars either side of it, because a quiet passage faded in
  is a hole at the join even when the passages around it agree.
- **It sets the level with one gain, then limits over three copies.** A test
  take reached the true-peak ceiling 2.2 dB short of −14 LUFS. A limiter
  would get there, but it treats the end of the file differently from the
  start. Run over the loop three times back to back, keeping the middle copy,
  it reached −14.6 LUFS at −1.8 dBTP with the join untouched.
- **It measures the file it wrote, and makes up the difference.** Limiting
  takes loudness off, and so does the encoder: a loop asked for −14 LUFS came
  out at −15.2. The encoded file is measured and the gain raised again, in up
  to three passes, and the same take came out at −16.1 and −14.1 when asked
  for −16 and −14.
- **Aim ambience and menus at −16 LUFS and battles at −14.** These takes are
  normalised to full scale, with a lot of room between their peaks and their
  average. An orchestral theme needed 6.3 dB of limiting to reach −14, and
  4.0 dB to reach −16.

::: warning Don't measure the join, measure the restart
The level just before and just after the join says nothing: the audio there is
continuous by construction, and the first version of the report flagged a 5 dB
"step" that was just the music. What a listener hears is the bars after the
restart against the bars before the crossfade. That number is what caught the
planner's silent intro: −45 dB.
:::

::: danger A peak of exactly 0.0 is still a measurement
ACE-Step's takes are normalised to full scale, so a loop's true peak before
any gain often measured exactly 0.0 dBTP. The first version read it as
`before["true_peak"] or -99`, and Python's `or` treats 0.0 as missing: the
limiter never ran, and 6 of the first 23 loops peaked above full scale, up to
+5.8 dBTP. Test for `None`, and check the file you wrote: the report now says
when a true peak is over 0, and `generate_music.py` rules that take out.
:::

A loop comes out shorter than its take: 75 to 182 seconds from takes of 145 to
210. Ask for about 200 seconds.

MP3 adds padding at both ends of the file and records how much in a header. A
112-second loop decoded 3 ms long when the decoder read that header and 38 ms
long when it didn't, which is a short gap every time round. Whether a player
reads the header is up to the player, so listen to the loop in the one that
will actually play it.

## Several takes, picked by measurement

`--takes 3 --loop DIR --keep-best` loops every take into `DIR/takes/`, keeps
the one with the lowest penalty as `DIR/<name>.mp3`, and writes every take's
report to `DIR/picks.json`. Silence inside a loop, or a true peak over full
scale, rules a take out. A jump at
the restart, a crossfade that swells or dips, a wide loudness range in the
loop, heavy limiting, a weak rhythm match and a loop under 90 seconds all
count against it.

`picks.json` is written after every take, and a run skips every seed already
recorded there for the same caption and settings. A stopped run picks up where
it left off, and `--takes 6` after `--takes 3` makes three more and picks from
all six. `--reloop` generates nothing: it loops every recorded take again with
the current `make_loop.py` and picks again. That is how the start search was
measured against the first version, on the same takes.

**A take is never made twice.** Before queueing a take, `generate_music.py`
looks for the same graph in the server's queue and history: a match still
queued is waited for, and a finished one is used. On this box a low-memory
guard stopped these runs three times while another project's jobs loaded
their models. Each time the server went on to finish the prompt it had
already been given, and the next run recorded that take instead of making it
again. `--no-wait` does this on purpose: it queues every missing take and
exits, and a run without it loops and records them. Eighteen takes queued
together finished in about two minutes of GPU.

**None of that says whether a take is any good**, or whether a voice crept in.
Listen to the winners before anything ships.

The game's own listening pass bore that out. Of the four menu and battle
takes kept by ear, two were the ones the measurements ranked first. A whole
battle prompt whose three takes measured among the cleanest (no gaps, 0.9 to
9.8 LU) was turned down, and the main menu ended up with a chamber piece
written for another screen. Put every take in front of the listener, not just
the winner.
