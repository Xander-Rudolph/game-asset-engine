# Daz figures

*A Genesis figure from a Daz product you downloaded yourself: installed outside
the repo, imported into Blender with its viseme controllers, and rendered as
sprite rows. The renders may ship. The figure's 3D data may not, without an
Interactive License.*

Everything below was run on 2026-09-16 on the reference machine, on one
product, Genesis 9 Starter Essentials (SKU 86958), downloaded in a browser. The
library and inventory scripts ran on the host's `python3` 3.13. The importer and
every render ran in the `comfyui-packaged` container's `bpy` 4.5.9 LTS, where
EEVEE reports its renderer as `llvmpipe (LLVM 15.0.7, 256 bits)`: Mesa's
software OpenGL on the CPU, not the graphics card. One figure was imported
plainly and one character preset with its textures. Each section says what
failed and what worked instead, and the page ends with
[what was not tested](#what-was-not-tested).

The background, and the licence read from Daz's own pages, is in the research
note [DAZ Genesis as a character base](/reference/daz-genesis). This page
repeats only as much of the licence as you need before you start.

::: danger Read the licence before you install anything
From the research note's [Licences](/reference/daz-genesis#licences) and
[What not to do](/reference/daz-genesis#what-not-to-do), checked on 2026-09-15;
not legal advice.

- **Renders and sprites may ship** in a sold game with no purchase, unless the
  product page says otherwise, as long as nothing shipped lets the content be
  extracted.
- **The mesh, rig, morphs and textures may not go into a build**, nor an FBX or
  glTF exported from them, without an Interactive License for each product or a
  separate agreement signed by both parties. Even then they must stay out of
  native formats and be protected against extraction, and some sales and
  deliveries need Daz's written consent
  ([Shipping 3D data](/reference/daz-genesis#shipping-3d-data-the-interactive-license)).
- **Keep Daz content out of the AI stages.** Never load the mesh, textures or UV
  maps into any model, and do not feed a render to Qwen-Image, ControlNet,
  TRELLIS, Hunyuan3D or any training until Daz answers in writing
  ([the AI clauses](/reference/daz-genesis#the-ai-clauses)).
- **Do not script the Daz website.** Download through Daz's installers or a
  browser.
:::

## What you end up with

```
/models/daz_library/                  MODELS_DIR/daz_library, outside the repo
  data/  People/  Runtime/            the product, as Daz Studio would lay it out
  .daz_library/86958.json             what was installed, and the licence held
input/_devtools/import_daz/           the importer, fetched and pinned, gitignored
output/daz/                           Daz content: gitignored, never committed
  g9_cage.blend                       the imported figure, 70,928,008 bytes
  g9_cage_build.json                  every import step, its time and memory
  g9_cage_blender.log                 the importer's own output
  g9_cage_motion.json                 what each viseme moves
  g9_cage_render_sheet_128.png        render_sheet.py: the whole figure, a row per viseme
  g9_cage_sheet_340_labelled.png      the probe's framings, a row per viseme
  g9_cage_render.json                 the command, every option, pixels changed
```

The whole run, with an approval after every step:

```sh
python3 scripts/daz_library.py install ~/Downloads/IM00086958-0?_*.zip --dry-run
python3 scripts/daz_library.py install ~/Downloads/IM00086958-0?_*.zip --eula-read YYYY-MM-DD
python3 scripts/daz_library.py verify 86958 --crc
python3 scripts/daz_import_probe.py fetch
python3 scripts/daz_import_probe.py build --facs --subdivision off --out output/daz/g9_cage.blend
python3 scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend --motion-only
python3 scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend \
    --only AA --sizes 128 --columns face --samples 16
python3 scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend
```

The `daz-figure` skill runs these one stage per turn, with the licence first,
and has you open each sheet yourself rather than reading it into the
conversation ([installing it for Claude](/guide/claude)). The three scripts' commands and
exit codes are in [the scripts reference](/reference/scripts#daz-figures).

## Getting the product

Genesis 9 Starter Essentials was US$0.00 when the research note checked it on
2026-09-15. Sign in to your own Daz account and download the product's Daz
Install Manager packages in a browser. For SKU 86958 those are three zips,
`IM00086958-01_Genesis9StarterEssentials1Of3.zip` to `...-03_...3Of3.zip`.
Daz's Terms of Service forbid any automated access to the website, so nothing
in this repo downloads from it, and no tool should be pointed at it for you.

## A library outside the repo

```sh
python3 scripts/daz_library.py install ~/Downloads/IM00086958-0?_*.zip --dry-run
python3 scripts/daz_library.py install ~/Downloads/IM00086958-0?_*.zip --eula-read YYYY-MM-DD
python3 scripts/daz_library.py list
python3 scripts/daz_library.py verify 86958 --crc
```

`scripts/daz_library.py` puts the library at `MODELS_DIR/daz_library`, which
compose mounts into the container as `/app/models/daz_library`. `--library`
names another folder. A library inside the repo, or one containing it, is
refused before anything is read.

Each zip holds a `Manifest.dsx`. Only its File elements with `TARGET="Content"`
and `ACTION="Install"` are extracted, with the leading `Content/` removed, so
`data/`, `People/` and `Runtime/` land at the library root and the three parts
merge into one folder. In the three packages the manifests listed 4528, 197 and
1780 files, all of them Content and Install, and no zip entry was left unlisted.
Three `Runtime/Support/DAZ_3D_86958_*` files are in all three parts with
identical bytes, so a later part skips them.

| Run | Result | Time |
|---|---|---|
| `install` of all three into an empty library | 6499 files, 2,452,887,819 bytes, which `du -sb` agreed with | 7.59 s, then 6.90 s wall |
| `install` of all three over a complete install | every file identical, nothing written | 6.98 s wall |
| `uninstall 86958` | 6499 files and 553 folders removed | 0.15 s |
| `install --dry-run` of all three against the installed library, after the fixes below | exit 0, every file identical, record unchanged | 6.84 s wall |
| `install` of part 03 alone into an empty library, after the fixes | 1780 files, 241,415,839 bytes | 0.89 s wall |
| `verify 86958 --crc`, after the fixes | 6499 of 6499 | 0.51 to 0.93 s |
| `selftest --dir`, after the fixes | 67 checks passed | 4.70 and 4.80 s wall |

The first three rows ran before the review fixes and were not run again. The
times are to the page cache: nothing is synced to disk.

### What it refuses

Every path in every zip is checked before anything is written, and one refused
path stops the whole run with `nothing was installed`, exit 2. It refuses
absolute paths, `..`, backslashes, a zip entry stored as a symlink, a path into
its own `.daz_library/` records, a path that another listed path needs as a
folder, a symlink already at a file's path or its temporary name, and a path
that leaves the library through a symlink already in it. Seven crafted zip-slip
packages, with no Daz content in them, were all refused with nothing written
anywhere.

It also refuses a renamed or mixed-up zip: a name that breaks Daz's documented
package pattern, a part number that disagrees with the "(N of M)" in
`Supplement.dsx`, a GlobalID that differs from the one recorded for the SKU, or
two zips for the same part. A copy of part 03 cut to half its size was refused
as not a readable zip.

A file already present with different bytes is a conflict: that package
installs nothing and lists the conflicts, exit 1, unless `--overwrite` is
given. Each file is written to a hidden temporary name beside it, and renamed
into place only after the zip's CRC-32 check passes. A copy of part 03 with one
byte flipped inside entry 1088 changed nothing in the installed library; into
an empty one, 1087 files landed and the part was recorded incomplete. The
half-size and flipped-byte copies were tried before the review fixes below.

One install at a time holds the library's lock. A second exits 2 with
`another daz_library.py is changing <library>; wait for it to finish`.

### Stopping part way

If writing a package fails for any reason, its temporary file is removed, the
package stops as partial, and the files already placed are recorded with
`"complete": false`. `list` shows them under `incomplete_parts`, `verify` exits
1, and installing the same zip again finishes the part.

The first Ctrl-C, SIGTERM or SIGHUP stops after the chunk being copied, records
what is placed, and exits 128 plus the signal number. On an invented package, a
small file then a 1.5 GB entry, `timeout --preserve-status -s INT|TERM|HUP 0.7`
gave exit 130, 143 and 129, and each time the small file was recorded, the part
marked incomplete and no temporary file left. A second signal stops at once and
still records what was placed.

### The licence it records

The record, `<library>/.daz_library/86958.json`, holds the product, each part's
zip name, sha256, size and install time, every file with its size and CRC-32,
and a licence block. Only two things in that block are yours to set:

- **The licence held.** "Daz Standard License (EULA)" unless you pass
  `--interactive-license`, which records a bought Interactive License. The
  script cannot check a purchase, and `licence 86958 --standard-license` takes
  it back off.
- **The date you last read the EULA**, with `--eula-read YYYY-MM-DD` on
  `install` or `licence`. Daz's EULA carries no version and may change, so a
  dated record is the only note of what you read. Until you give one, `list`
  says `EULA last read: not recorded`.

The rest of the block is wording rebuilt whenever the record is saved, and
`licence 86958` prints it: renders and sprites may ship on conditions, the 3D
data needs an Interactive License, the four conditions that still apply under
one, and the AI-stage exclusion. The record installed on 2026-09-16 still holds
the older wording until its next save.

### Paths that differ only in case

```sh
python3 scripts/daz_library.py case-check
```

Linux keeps `Daz 3D` and `DAZ 3D` apart; Windows does not. No folder in the
installed product held two names differing only in case. But `case-check` read
the product's own 3847 `.dsf` and `.duf` files in 7.22 s, none unreadable, and
76 of the 5185 paths they reference match a file only when case is ignored:
52 through `runtime/`
for `Runtime/`, 18 through `DAZ 3D`, 4 through `Daz` for `DAZ`, and 2 in file
names. Another 93 point at nothing in the product, such as Daz Studio's
built-in FilaToon and PBRSkin shaders. `case-check` exits 1 on these. The
importer below matched the library's `Daz 3D` folder against its own `DAZ 3D`
tables, because it compares names without regard to case on Linux; whether it
resolves all 76 was not checked.

### What failed on the way

A review of the first version, with synthetic packages, found four things now
fixed:

- **A symlink at a temporary name wrote outside the library.** A symlink planted
  at `.f.dsf.daz_library-part` was followed on open and renamed into place, the
  install exited 0, and `verify` passed it. The temporary file is now created
  with `O_EXCL` and `O_NOFOLLOW`, a symlink there is refused with `a symlink is
  at its temporary name <tmp>`, and `verify` counts a symlink as not a file.
- **Some failures left files out of the record.** An entry with an unsupported
  compression method raised `NotImplementedError` and exited 1 with a file on
  disk, `list` said `no products recorded`, and `uninstall` could not remove
  it. Ctrl-C did the same and left an 878,706,688-byte temporary file. Every
  failure and signal now records what was placed.
- **Two installs could lose a record.** Both read the records before taking the
  lock, so with a 2 s delay injected, the one that waited overwrote the other's
  part. The lock is now taken first.
- **The Interactive License wording said too much.** It named only the
  native-format and extraction conditions; the consent conditions for separate
  sale and for cloud or post-install delivery are now in it.

## What the library holds

```sh
python3 scripts/daz_inventory.py /models/daz_library --brief
```

`scripts/daz_inventory.py` reads every `.dsf` with the standard library, with
no Blender. On the installed product it exited 0 with nothing on stderr, in
2.75 to 2.86 s by its own timer:

- **3210 `.dsf` files:** 3209 plain JSON, none gzip, 1 skipped as not DSON.
- **51 figure files**, grouped by the content type their author set: 1 body
  (`Actor`), 31 attachments (eyes, mouth, lashes and tear, but also 22 eyebrow
  files, which carry the same type), and 19 other geometry (12 wardrobe, 5
  hair, 1 prop, 1 other).
- **`Genesis9.dsf`:** 25,182 vertices, 25,156 quads and 138 bones, as the
  research note's community figures had it. The note's 143 bones are body and
  Mouth together: the five tongue bones are only in `Genesis9Mouth.dsf`.
- **Its modifiers:** 1114 morphs, 398 aliases and 5 other modifiers. The morphs
  include 17 `facs_ctrl_v` viseme controllers, 204 `facs_bs_`, 25 `facs_cbs_`
  and 103 `body_cbs_`, and no `eCTRLv`, `facs_jnt_` or `pJCM`. 51 are HD morphs
  with base deltas as well as an `hd_url`, and none is named `_div2`.

Across the product 54 morphs carry an `hd_url` and 52 `.dhdm` files are on disk.
The two missing are for Toon Hair morphs, and no file of either name is
anywhere in the library.

The research note quotes the product page's "753 ... Maps (256 x 256 to 8192 x
8192)". That was not reproduced: a PIL header read of `Runtime/Textures` found
762 image files, and 45 of them are smaller than 256 px. Which files Daz counts
as maps was not checked.

The first run on real content found two bugs, both fixed:

- **Aliases counted as morphs.** An alias is a second name for another
  modifier's channel, so the first run reported 1517 morphs and 34 viseme
  controllers where there are 17. Aliases and other modifiers are now counted
  apart.
- **A valid file called unreadable.** `Sculpting Optimized.dsf`, a face group
  file whose only key is `group_list`, made a clean install exit 1. A valid
  JSON file with no DSON key is now skipped and listed as not DSON.

## The importer, fetched and pinned

```sh
python3 scripts/daz_import_probe.py fetch
```

The [Diffeomorphic DAZ Importer](https://github.com/Diffeomorphic/import_daz)
reads `.duf` and `.dsf` files with no Daz Studio. `fetch` downloads GitHub's
archive of the `version_5_2_0` tag, pinned at 1,697,629 bytes and sha256
`b6921c46e9a876fe88ab0ef75f47c8eac67cf4c4314059871d2a78bdcfccf9d2`, checks
that the zip's comment names commit `1abc6815`, and unpacks its 296 files into
the gitignored `input/_devtools/import_daz/`. GitHub publishes no checksum for
tag archives, so the pins are the bytes downloaded that day, the same from
github.com and codeload.github.com. A wrong sha256 was refused, and the `.part`
file deleted.

Its code is GPL-2.0-or-later (its `blender_manifest.toml`), copyright 2016-2026
Thomas Larsson, both read on 2026-09-16. It is run in the container and never
copied into the repo. Daz content keeps the Daz EULA after import.

## Importing without a UI

```sh
python3 scripts/daz_import_probe.py build --facs --subdivision off --out output/daz/g9_cage.blend
```

That build exited 0 in 5.7 s wall, 5.51 s of it in Blender, at a peak of
711 MiB. The research note had the importer's background use as unhandled and
not run. It ran headless in the container's `bpy` with no change to the image,
added as a local extension repository and enabled as
`bl_ext.import_daz_probe.import_daz`, the way
[MPFB2](/reference/daz-genesis#makehuman-and-mpfb2) was. Before `import bpy`,
`BLENDER_USER_RESOURCES` and `HOME` point under `input/_devtools/import_daz/`,
so the importer's settings land there. No operator called from Python waited on
a dialog: the importer's nine `invoke_props_dialog` calls sit on `invoke()`
paths, and none of its code checks `bpy.app.background` (read at the tag).

Each step records its time, peak memory and `import_daz.get_error_message()`,
because every operator returns `FINISHED`, even when it failed.

### Blender drops bl_info

The first build stopped with `AttributeError: module
'bl_ext.import_daz_probe.import_daz' has no attribute 'bl_info'`. Blender
deletes `bl_info` from a module it enables as an extension, so the probe reads
the version from `blender_manifest.toml` instead: 5.2.0, BUILD 3018.

### Silent mode turns itself off

`import_daz.set_silent_mode(True)` sends the importer's errors to the terminal
and `get_error_message()` rather than to a pop-up. But `easy_import_daz` sets
silent mode back to off when it returns (`main.py` at the tag, read). So the
probe sets it again before every operator, and the build report records that
it did.

### The figure is more than one file

The build imports `People/Genesis 9/Genesis 9.duf`, the load Daz Studio offers.
Daz Studio loads the Eyes, Mouth, Eyelashes, Tear and eyebrow figures through a
post-load script that the importer never runs. So the probe reads that
script's file list from the `.duf` and imports each figure, parents its rig to
the body's and merges the rigs with `bpy.ops.daz.merge_rigs`. The first try at
that failed on the eyebrow path, which the `.duf` gives with a leading slash.

Mesh fitting is Morphed, because the default wants a `.dbz` exported from
inside Daz Studio. The imported meshes have the research note's counts: body
25,182 vertices and 25,156 faces, Mouth 5079 and 5000, Eyes 2120 and 2112,
Eyelashes 2028 and 858, Tear 280 and 220. The build log prints `Missing
geonode` for two HD morphs the `.duf` names, `body_bs_Navel_HD3` and
`head_bs_MouthRealism_HD3`.

The rig had 152 bones after the figure (138 Daz bones and 14 "(drv)" helpers the
importer adds), 157 after the merge, and 177 after FACS: 143 Daz bones, with
`tongue01` to `tongue05` from the Mouth, and 34 helpers. The Developer Kit's
`Genesis 9 Dev Load.duf` with `--anatomy none` built in 0.9 s wall with 150
bones.

### import_visemes does nothing on Genesis 9

```sh
python3 scripts/daz_import_probe.py build --visemes --facs --out output/daz/g9_visemes.blend
```

This exits 1 by design. `bpy.ops.daz.import_visemes()` returns `FINISHED`, logs
`Load Visemes to Genesis 9 Mesh (0 morphs)` and the same for the other four
meshes, and leaves `get_error_message()` empty: the importer's
`data/paths/genesis9.json` has no viseme table (read). The research note's
`rig["eCTRLvAA"] = 1.0` example does not apply: Genesis 9 has no `eCTRLv`
controllers.

The visemes come from `bpy.ops.daz.import_facs()` instead, which took 4.19 s.
It loads 285 morphs onto the body and 21 onto the Mouth, 10 of them the Mouth's
own viseme controllers, and makes `facs_ctrl_vAA` to `facs_ctrl_vW` 17 rig
properties, with 17 "(fin)" twins on the armature data. The Mouth's controllers
take the same property names, so one property drives both. No shape key
carries a viseme name: the body has 179 shape keys, 178 of them driven, and the
Mouth 7.

### A wrong content path fails quietly

```sh
python3 scripts/daz_import_probe.py build --content-dir /app/models/daz_library_missing \
    --no-dir-check --anatomy none --out output/daz/g9_wrongdir.blend
```

`set_global_setting('contentDirs', ...)` raised nothing, and
`get_root_paths()` and `get_absolute_paths()` returned `[]`.
`easy_import_daz` returned `FINISHED` and made no object. Only
`get_error_message()` said `Some assets were not found. Check that all DAZ root
paths have been set up correctly.`, and listed five `.dsf` files, at verbosity
3. So the build checks first that the folder and the figure exist and that the
importer resolves the figure, and stops if not.

### The .blend works without the add-on

The `g9_visemes` build's rig carries 409 drivers and its shape keys 325, every
one a simple expression, and nothing is added to `bpy.app.driver_namespace`.

```sh
python3 scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend --motion-only
```

This opened `g9_cage.blend` with no DAZ add-on enabled and auto-run scripts
off, set each viseme to 1, and rendered nothing: 0.6 s in Blender, 3.8 s for
the command (rerun on 2026-09-16 for this page). `facs_ctrl_vAA` moved 2880
body vertices by up to 7.8 mm, before subdivision, and 12 body shape keys.
Over the 17 visemes the body moved 1419 (T) to 3494 (EE) vertices, by up to
2.8 (T) to 11.8 (W) mm, and 3 (L) to 41 (OW) shape keys.

M moves 24 shape keys and no bone. Every other viseme changes the same 33 pose
bones in armature space, while no Daz bone's own channels change:

- 15 are the importer's "(drv)" helpers. The drivers pose 9 to 14 of them,
  depending on the viseme, and the rest move with their parent.
- 15 are Daz bones following their helper through a Copy Transforms
  constraint: `lowerjaw`, `tongue01` to `tongue05`, the left and right upper
  lip, lower lip, lip corner and lower cheek bones, and `liplowermiddle`.
- 3, `lowerteeth`, `lowerfacerig` and `chin`, are carried by a moving parent.

`lowerjaw` moves for 16 of the 17 visemes.

## Rendering the visemes

```sh
python3 scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend \
    --only AA --sizes 128 --columns face --samples 16
```

`render` runs two stages, each a neutral row and then one row per viseme: all
17, or those `--only` names.

1. **`scripts/render_sheet.py`**: the whole figure from one angle, 128 px by
   default, each row setting its viseme property through `"@props"`.
2. **The probe's own framings**, in clay: `body`, the whole figure; `face`,
   front on, with the band from the crown down to the lowest vertex AA moves
   filling three quarters of the cell; and `face34`, the same turned 35 degrees
   and raised 10. The head band was 0.2541 m of the cage's 1.7011 m.

Files are named `<name>_<label>_...`, where the label lists the options that
differ from the defaults, so the short run above writes
`g9_cage_AA_128_face_s16_render.json` and its sheets, and never overwrites a
full run's files. The `_render.json` records the command line, every option,
`render_sheet.py`'s command and exit, and the pixels each viseme changes
against the neutral row.

That short run exited 0. `render_sheet.py` drew its 2 rows in 28.9 s wall, and
AA changed 1 pixel on the whole figure. The probe's 2 cells took 17.7 s at a
peak of 2709 MiB, and AA changed 210 pixels in the face framing.

### Subdivision is the cost

The importer saves 5 Subsurf modifiers at level 1 in the viewport and up to 3
for render, and on llvmpipe that multiplies every render.

| Command, on `g9_visemes.blend` | Subdivision | Result |
|---|---|---|
| `render --no-sheet --subdivision as-saved --only AA --sizes 128 --columns face --samples 16` | as saved | 2 face cells in 88.7 s, peak 4593 MiB, container 4.54 to 8.83 GiB |
| `render --only AA --sizes 128 --columns face --samples 16` | off | a Subsurf-off copy in 0.5 s, `render_sheet.py`'s 2 rows in 28.8 s, the probe's 2 cells in 17.9 s, peak 2655 MiB |

It showed first in the whole-figure stage. An earlier version of the probe
handed `render_sheet.py` the `.blend` as saved, and its cells at 64 samples came
about 238 s apart, so 18 rows would have run past its 3600 s timeout. That run
was stopped after 3 cells. An earlier version still, with no `--subdivision`
option, took 681.1 s for 18 face cells at 128 px and 16 samples. So
`build --subdivision off` saves the cage, and `render` now switches Subsurf off
for both stages unless given `--subdivision as-saved`, handing
`render_sheet.py` a temporary copy when the file has any on.

### The full run, and what reads

```sh
python3 scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend
```

Run once on the cage with the version before the Subsurf copy and the option
record, which renders the same rows for that file, and not run again:

- **`render_sheet.py`:** 18 rows in 184.3 s wall. Its `--check` called 7 rows,
  IH, K, L, S, T, TH and W, the rest pose repeated, and the others changed 1 to
  4 pixels, so it exited 1, and so did the probe.
- **The probe:** 162 cells, 3 framings at 3 sizes over 18 rows at 64 samples,
  in 1287.6 s wall: 390.1 s at 128 px, 422.9 s at 220 px and 473.5 s at 340
  px. Peak 3401 MiB, and the container went from 4.54 to 7.67 GiB.

Pixels changed against the neutral row at threshold 8, as `mpfb_probe.py`
counts them, fewest to most over the 17 visemes:

| Framing | 128 px | 220 px | 340 px |
|---|---|---|---|
| body | 0 to 4 | 2 to 12 | 9 to 27 |
| face | 67 to 258 | 213 to 791 | 533 to 1873 |
| face34 | 87 to 253 | 238 to 704 | 537 to 1559 |

On a MakeHuman body through MPFB2, the whole figure gave 0 to 8, 1 to 18 and 4
to 46, and the head framing 38 to 244, 127 to 722 and 311 to 1654
([lip sync](/reference/lip-sync#faces-only-read-on-a-portrait)). Genesis reads
no better on a whole figure. At the [sprite sizes](/guide/facings#sizes) of 128
and 220 px, a viseme is a handful of pixels.

By eye, in clay, as read by Claude, the assistant that ran the import, from a
crop it made of the 340 px face column: OW and UW read as rounded mouths, EH
and ER as open with teeth, EE and IY as teeth behind parted lips, and M as
pressed lips. F, K, L, S, T, TH, IH and W look like one slightly parted mouth,
and AA opens less than OW. That is one reading, by an AI model, of one figure.
Whether a Daz render may be read into Claude at all is open
([below](#what-was-not-tested)), so the `daz-figure` skill has you open the
sheet and say what you see, and gives only the pixel counts.

### Textures cost memory at render time

```sh
python3 scripts/daz_import_probe.py build --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf" \
    --facs --out output/daz/g9_kat.blend
python3 scripts/daz_import_probe.py render --blend output/daz/g9_kat.blend --no-sheet --materials \
    --sizes 340 --columns face --only AA --samples 16
```

`Genesis 9.duf`'s own body materials use no image maps. The Kat preset
references 26: 4 at 8192 px, 16 at 4096, 5 at 1024 and 1 at 256 (host PIL
header reads). Its builds took 8.7 s wall each. The figure import alone
reached 1444 MiB in 3.02 s, because the importer reads the images as it
imports; `--no-textures` removes them only afterwards, and reached 1456 MiB.

| `.blend` | 2 face cells at 340 px, 16 samples, `--materials` | Peak | Container |
|---|---|---|---|
| `g9_kat.blend` | 81.9 s | 6312 MiB | 4.54 to 10.63 GiB |
| `g9_kat_notex.blend`, built with `--no-textures` | 27.7 s | 2836 MiB | 4.66 to 7.25 GiB |

The materials are the importer's "Extended Principled", which its own label
calls "limited IRAY quality". How they compare with Iray was not judged.

### Stopping a render

Blender and ComfyUI share the container. Before each Blender job the probe
polls every 30 s until ComfyUI's queue is empty and `docker top` shows no other
`python3 -c` job. On Ctrl-C or SIGTERM, and whenever `render_sheet.py` exits
non-zero or runs past its time, it ends the Blender job it started, found by a
path unique to that job, with SIGTERM and then SIGKILL after 10 s. It deletes
that job's frames and temporary files, and on a stop writes no report and exits
130 or 143.

That clean-up came from a failure. A SIGINT sent to a background job in a
non-interactive shell, whose process group ignored it, reached only the docker
client, which printed `context canceled`. `render_sheet.py` exited 1 while its Blender job kept running in the
container; before the clean-up it would have run on until its own alarm, and
now the probe ends it. Another: `--only ,` once parsed as an empty list, which
meant all 17, and started the full job, stopped by hand after 7 rows. It now
exits 2 with `name at least one viseme, such as AA, from AA, EE, ...`.

## Keeping Daz content where it belongs

- **`output/daz/` is Daz content**, and gitignored. The `.blend`, logs, reports
  and renders all go there. The one exception is `render_sheet.py`, which draws
  its cells in `output/_sheet_frames/<pid>_<time>/`. It deletes them when it
  finishes, and the probe deletes them when it fails or is stopped.
- **`cleanup.py keep` refuses Daz 3D data**, before anything is copied, with
  exit 1: `--model`, `--rig` or `--textures` from `output/daz/`, any file in a
  Daz library, and a native Daz file (`.duf`, `.dsf`, `.dhdm`, `.dbz`, `.dsa`,
  `.dse`, `.dsx`) from anywhere. The message starts `keep: refused. Daz 3D data
  may not be curated into a shippable asset folder under the standard Daz
  EULA:` and names each path. It goes by path and suffix only, so a mesh
  exported out of `output/daz/` under another name is not recognised.
- **Renders can still be curated.** An image or video from `output/daz/` given
  as `--concept` or `--sheets` is kept, and `keep` prints a note to keep it out
  of the AI stages and any training ([curating](/guide/cleanup)).
- **`sweep` does not protect `output/daz/`.** It lists its files as unclaimed,
  and `sweep --delete --unclaimed` deletes them, `.blend` files included.
- **Nothing from Daz goes in the repo.** `scripts/check_vendored_licences.py`
  flags the words Daz and Genesis 8 or 9 in any file outside `docs/` and
  `research/` that its allowlist does not explain.

## What was not tested

- **Any other product**, Genesis 8 or 8.1, and third-party content, whose
  authors may set content types differently.
- **Installing again on the real library after the fixes.** Only the dry run,
  `list`, `licence` and `verify --crc` ran there; part 03 was installed into a
  throwaway library.
- **Daz Studio's own gzip-compressed files.** None of the product's 3210 `.dsf`
  or 637 `.duf` files is gzip (`daz_inventory.py` for the `.dsf`, and an ad hoc
  read of every file's first two bytes for both), so the gzip paths ran only on
  synthetic files and a gzip copy of `Genesis 9.duf`, and no build ran on one.
- **The library's harder stops:** a full disk, SIGKILL or power loss, two
  installs racing without an injected delay, and another program changing the
  library during an install.
- **The Mouth's controllers as separate dials**, FACS Details and HD morphs,
  the six Toon sub-figures and their FilaToon shaders.
- **A `.dbz` fit from Daz Studio**, other material methods, the importer's
  texture resize, and Cycles.
- **Exporting the visemes** as baked blend shapes to glTF or FBX, and any
  engine reading them. Shipping those needs an Interactive License anyway.
- **Lip sync's Genesis column** ([the mapping](/reference/lip-sync#the-mapping-to-adopt))
  on this figure.
- **Whether reading a Daz render into a Claude conversation** counts under the
  EULA's AI clause, whose examples name chatGPT. The research note leaves it
  open ([Honest uncertainty](/reference/daz-genesis#honest-uncertainty)). The
  by-eye reading above was made that way; until the owner decides, the skill
  reads no render into the conversation.
- **Peak VRAM**, since EEVEE here draws on the CPU, and render times with other
  jobs running in the container.
- **The default importer verbosity** on a wrong content path; the run used 3.
