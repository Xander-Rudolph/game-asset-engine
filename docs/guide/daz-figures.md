# Daz figures

*A Genesis figure from a Daz product you downloaded yourself: installed outside
the repo, imported into Blender with its viseme controllers, and rendered as
sprite rows. The renders may ship. The figure's 3D data may not, without an
Interactive License.*

Everything below was run on 2026-09-16, 2026-09-18 and 2026-09-19 on the
reference machine, mostly on one product, Genesis 9 Starter Essentials (SKU
86958), downloaded in a browser. Three more products were taken into the same
library on 2026-09-19 with `daz_library.py intake`, and only the library and
inventory sections measure them
([a folder of downloads](#a-folder-of-downloads-in-one-command),
[what the library holds](#what-the-library-holds)). No figure of theirs has
been imported, dressed, posed or rendered. The library and inventory scripts ran on the host's `python3` 3.13.
The importer and every render ran in the `comfyui-packaged` container's `bpy`
4.5.9 LTS, where EEVEE reports its renderer as `llvmpipe (LLVM 15.0.7, 256
bits)`: Mesa's software OpenGL on the CPU, not the graphics card. Every render
time on this page is an EEVEE one, and stays one: `scripts/render_sheet.py`
took Cycles as its default on 2026-09-18, but `daz_import_probe.py` pins
`--engine eevee` for its sheet stage so that it matches its own framings, which
have no other engine ([scripts](/reference/scripts#render-sheet-py)). On 2026-09-16
one figure was imported plainly and one character preset with its textures; on
2026-09-18 one character was dialled, dressed, given hair and posed, and
rendered ([a dressed, posed character, headless](#a-dressed-posed-character-headless)).
Each section says what failed and what worked instead, and the page ends with
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
  Source/PROCESSED.md                 what `intake` took in, once its zips were deleted
input/_devtools/import_daz/           the importer, fetched and pinned, gitignored
output/daz/                           Daz content: gitignored, never committed
  g9_cage.blend                       the imported figure, 70,928,008 bytes
  g9_cage_build.json                  every import step, its time and memory
  g9_cage_blender.log                 the importer's own output
  g9_cage_motion.json                 what each viseme moves
  g9_cage_render_sheet_128.png        render_sheet.py: the whole figure, a row per viseme
  g9_cage_sheet_340_labelled.png      the probe's framings, a row per viseme
  g9_cage_render.json                 the command, every option, pixels changed
  g9_dressed.blend                    a dialled, dressed, posed character, 140,971,653 bytes
  g9_dressed_scene.json               every stage: morphs, dials, wearables, the pose
  g9_dressed_morphs.json              every slider on the rig, with its range
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

Dialling, dressing and posing a character is the same script's `scene`
subcommand, and `verify` reopens what it saved with no add-on at all
([a dressed, posed character, headless](#a-dressed-posed-character-headless)).

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

### A folder of downloads, in one command

```sh
python3 scripts/daz_library.py intake --dry-run   # then again without --dry-run
```

`intake` is `install` over a folder of zips you have finished with. It installs
every `.zip` in `MODELS_DIR/daz_library/Source`, or `--source DIR`, in a stable
order with the parts of one product in one run, so every check `install` makes
still applies. After a package installs, the files the record now lists for
that part are verified, present, a regular file, at their recorded size and
CRC-32, and the part recorded complete; only then is its zip deleted. A package
that is refused, conflicts, stops part way or fails that verify keeps its zip,
and so does every other part of the same product. `--keep-zips` deletes
nothing, `--dry-run` writes nothing and says what each zip would do, and a
folder with no `.zip` in it gives `no .zip files in <source>: nothing to do`.

It leaves one Markdown file behind in that folder, `PROCESSED.md` unless
`--ledger NAME` says otherwise, appended to and never rewritten. Each row gives
the date, the product name from `Supplement.dsx`, the SKU and part, the zip's
name, its size and sha256, what happened and what became of the zip, and the
number of files the manifest listed. It records names and counts only, so no
Daz content and no reproducible file list ever leaves the library.

Measured on 2026-09-19 on the host's `python3`, on six zips that were in
`/models/daz_library/Source`, 2,224,386,560 bytes in all:

| Run | Result | Time |
|---|---|---|
| `intake --dry-run` | exit 0; 3 zips already installed, 3 to install, nothing written | 8.04 s wall (`time`) |
| `intake` | all 6 installed or already installed, verified, deleted; 2,224,386,560 bytes freed, 6 ledger rows | 8.64 s wall |
| SKU 86958, three parts, already installed | 6,505 listed files all identical, nothing written | 6.66 s for the product |
| SKU 87397 Mavick Hair and Beard | 120 files, 369,742,988 bytes written | 0.60 s, verify 0.07 s |
| SKU 88643 dForce Leather Viking Armor | 242 files, 129,116,296 bytes written | 0.14 s, verify 0.03 s |
| SKU 91304 Tubal Weapons Collection | 245 files, 165,205,569 bytes written | 0.28 s, verify 0.03 s |
| `intake` again over the emptied folder | exit 0, nothing done | under 0.1 s |
| `verify --crc` over all four products | 7,106 of 7,106 files | 0.62 s |

No package warned about a path that differs only in case. The SKU 86958 parts
took most of the wall time because a package that is already installed is still
read in full: its sha256, then a byte comparison of every file it lists.

Five invented packages in a scratch folder, with no Daz content in them, were
all refused and all left in place, exit 2: a zip whose name says part 02 while
`Supplement.dsx` says `(1 of 2)`, a package cut to half its size, one part of a
product holding an entry stored as a symlink, that part's sibling, and a zip
whose name does not match Daz's pattern. A separate scratch product whose part
01 installed while part 02 hit a conflict exited 1 and kept both zips, which is
the rule that stops a half-taken product losing its downloads.

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

### What the three 2026-09-19 products added

Run again on 2026-09-19, after `intake`, `daz_inventory.py /models/daz_library
--brief` exited 0 with nothing on stderr and read 3418 `.dsf` files in 5.41 s:
183 gzip, 3234 plain, the same 1 skipped as not DSON and 0 unreadable. The 183
gzip files are the first in this library: Genesis 9 Starter Essentials ships
none, and the research note's "the shipped files are not compressed" is about
that product. The three products added 208 `.dsf` and 16 figure files:

| Product | Figure files | Content types | Vertices, bones, morphs |
|---|---|---|---|
| Mavick Hair and Beard (87397) | 4 | all `Follower/Hair` | Mavick Beard G8M 178,464 vertices, 133,848 quads, in two folders with 87 and 50 bones; Mavick HairStyle G8M 433,512 vertices, 336,418 quads and 56 triangles, in two folders with 26 and 50 bones; 1, 1, 7 and 8 morphs |
| dForce Leather Viking Armor (88643) | 7 | 3 `Follower/Wardrobe` (Shirt, Pant, Shoes), 4 `Follower/Accessory` (Torso twice, Arms/Lower, Waist) | Shirt 10,438 vertices and 57 bones; Arm Guard 28,366 and 37; Boots 6,420 and 53; Vest Straps 5,580 and 15; Pant 4,526 and 22; Vest 3,751 and 36; Belt 1,948 and 10; 159 morphs in all |
| Tubal Weapons Collection (91304) | 5 | all `Prop` | WarHammer 62,307 vertices, Sword 43,411, Dagger 43,073, Shield 41,375, Spear 31,003; no bones and no morphs |

Every one of those 176 morphs falls in the inventory's `other` group: none is
an `eCTRLv`, `facs_ctrl_v`, `facs_bs_`, `facs_cbs_`, `facs_jnt_`, `pJCM` or
`body_cbs_` name, so none of the three adds a viseme or a FACS dial. What the
Diffeomorphic importer makes of them was not tried.

The first run on real content found two bugs, both fixed:

- **Aliases counted as morphs.** An alias is a second name for another
  modifier's channel, so the first run reported 1517 morphs and 34 viseme
  controllers where there are 17. Aliases and other modifiers are now counted
  apart.
- **A valid file called unreadable.** `Sculpting Optimized.dsf`, a face group
  file whose only key is `group_list`, made a clean install exit 1. A valid
  JSON file with no DSON key is now skipped and listed as not DSON.

## Content that is not a Daz package

A Daz Install Manager zip is the well-lit path: its name carries the SKU and
the part, and `Manifest.dsx` lists every file to install. Content from
elsewhere, such as Renderosity's free section, comes in other shapes, and
`daz_library.py install --vendor NAME` takes all of them. Three turned up on
2026-09-21, in fourteen zips:

| Shape | Where the content starts | Seen in |
|---|---|---|
| `Manifest.dsx` at the zip root | `Content/`, as the manifest says | 8 of 14 |
| A library folder named in the zip | `My DAZ 3D Library/` | 2 of 14 |
| The folders at the zip root | the root itself | 1 of 14 |

Where there is no manifest, the content root is found by looking: the first
folder, or the zip root, that holds one of a library's own folders, such as
`data`, `People`, `Runtime`, `Props` or `Documentation`. Everything beside
those, a `readme/` folder or a loose PDF, is left in the zip and named in the
report.

Three of the fourteen were refused, each for a reason worth keeping:

- `IntergenPoseTransfer.dll`, a Daz Studio plugin. No content folder, and a
  Windows plugin for a program this stack does not run.
- A PDF on its own. No content folder either.
- `IM00087397-01_...(1).zip`, a Daz package a browser had numbered as a second
  download. Its name no longer matches Daz's pattern, so it would have been
  installed a second time under a name of its own; the refusal says to rename
  it or delete it.

### Whose terms

The licence wording in these scripts was read from Daz's EULA, and applies to
Daz's content. For a package from anywhere else the script states nothing: the
record keeps the vendor's name, the paths of the terms files the package
shipped, and the date the owner says they read them.

```
$ python3 scripts/daz_library.py licence mvrazel_carter-9_100068
Licence for mvrazel_carter-9_100068 (Carter 9): from Renderosity; this script has read
none of its terms
  The package shipped 1 file of terms. Read them in the library before shipping anything
  made from this content:
    Documentation/License.txt
```

Until those terms are read and recorded, this repo treats that content exactly
as it treats Daz content: out of the repo, out of a build, and out of every AI
stage.

### What fourteen free packages actually held

Installed on 2026-09-21, 11 packages, 3,464 files, 571 MB, all verified by
CRC-32:

- **Seven Genesis 9 characters** (Anjali, Carter, Heath, James, Kiva, Rebecca,
  Shelly), each a head and body morph with a `.duf` that loads them. They
  carry no skin of their own: each names the base Genesis 9 masculine or
  feminine maps, which the Starter Essentials already installed. `Carter 9.duf`
  imported in 1.03 s, 25,182 vertices with 3 shape keys, its own eyebrow card
  style and every anatomy figure.
- **An eighth character** that names neither base. `daz_characters.py` leaves
  it out of a roll and says why: nothing in the file says which skins fit it.
- **Two hand-grip pose sets**, which landed under the library's own `Props/`
  rather than under a figure. They are a second pose, for the fingers, and
  `scene` applies one pose, so nothing uses them yet.
- **A 558 MB material set** for a hair figure this library does not have: 792
  material presets and their textures, and no geometry at all. It installs
  cleanly and there is nothing to put it on.

### One library, two spellings of one folder

The characters install under `data/DAZ 3D/`, and Daz's own content is under
`data/Daz 3D/`. On this filesystem those are two folders, and `case-check`
finds them:

```
On disk: 1 folders hold names that differ only in case (2 names)
  data: DAZ 3D | Daz 3D
References in 5713 .dsf and .duf files: 50365 references to 6480 distinct paths
  6125 match a path exactly
  103 match a path only when case is ignored
```

The mismatch is not new and not only ours: 52 of those references spell
`runtime` where the disk has `Runtime`, and one product misspells its own
folder as `Tubal WEapons Collection`. Daz Studio runs on a case-insensitive
filesystem and never notices. Neither did the importer: the character above
loaded with its morphs from one spelling and its base figure from the other.
Nothing here rewrites a path to match the disk, because a package that says
`DAZ 3D` is installed as it is written.

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

### The maps the anatomy figures arrive without

An eyelash figure imported on its own renders as a set of opaque fans across
the eyelid. It is not a Blender problem, and not a bad transmap: the figure
carries no map at all. `data/Daz 3D/Genesis 9/Genesis 9 Eyelashes/Tools/Script
Loads/Genesis 9 Eyelashes.duf` is a wearable with two materials, `Eyelashes
Lower` and `Eyelashes Upper`, whose `Cutout Opacity` channel is the number 1
and whose file has no `image_library` at all (read 2026-09-21). The eyes, the
mouth and the eyebrow cards are the same. Daz Studio fills them in afterwards
by running a MAT preset, and the importer never runs one.

So `build` and `scene` now apply those presets themselves, and say what each
one filled in. `--no-auto-materials` puts the old behaviour back.

```sh
# the presets beside the figure and beside each anatomy file, then one named
python3 scripts/daz_import_probe.py build \
    --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf" \
    --mat-preset "People/Genesis 9/Anatomy/Daz Originals/Base Anatomy/Eyebrows Card/Materials/G9 Eyebrows Color Red.duf" \
    --subdivision off --out output/daz/g9_kat.blend
```

Three rules find them, each one a shape this product uses: a character preset
keeps its materials in a `Materials` folder beside it (`Kat G9 All MAT.duf`),
an anatomy figure keeps a `<name> MAT.duf` next to itself, and the eyebrow
cards keep one preset per colour, of which none is the default, so Brown is
taken. A preset named with `--mat-preset` is applied before those, and whatever
is set first wins.

**Only what is missing is filled in.** A material with something linked into
Base Color keeps it, and one that is already see-through, through a Transparent
BSDF, a `DAZ Transparent` group or its own Alpha, is left alone. So this adds
the eyelash, eyebrow, eye, mouth and teeth maps and changes nothing about the
skin the importer built. On Kat it filled in 16 of the 16 materials the presets
name, and the file went from 18 images to 29.

What it reads from a preset is the cutout opacity map or value, the colour map
or flat colour, a layered colour image when every layer is laid plainly over
the one below, and the refraction weight and index. Nothing else: no normal
map, no roughness, no layer with a rotation, an offset, a scale or a blend mode
of its own. Each of those is named in the report as unresolved rather than
guessed at.

### The film of moisture over an eye

Genesis 9 puts a separate surface over each eyeball, `EyeMoisture`, and the
character preset gives it `Refraction Weight` 1, `Refraction Index` 1.38,
`Thin Walled` true and a white diffuse. Reading only the colour out of that
makes it an opaque white dome, which is worse than leaving it bare: the eyes
disappear behind it. So a preset's refraction weight of 0.5 or more becomes the
Principled BSDF's Transmission Weight, with the index as its IOR, and the
material turns to glass.

Measured on Kat on 2026-09-21, the Eyes mesh rendered on its own at 512 px in
Cycles at 64 samples, over the 30,453 pixels it covers either way:

| | Lit mean RGB | Colour spread |
|---|---|---|
| Colour only | 0.6461, 0.6461, 0.6461 | 0.000 |
| With the refraction | 0.3171, 0.2888, 0.2775 | 0.041 |

The first row is a grey dome, the same value in all three channels, which is
what a white surface with no transmission renders as. The second is the iris
seen through it.

### Why the probe reads the preset itself

`bpy.ops.daz.import_daz_materials` exists for this and does load a preset onto
selected meshes, but it drops the maps of any material whose name has a space
in it. A hierarchical preset writes its values as "animations" whose url names
the material and the channel:

```
Genesis9Eyelashes#materials/Eyelashes%20Lower:?extra/studio_material_channels/channels/Cutout%20Opacity/image_file
```

The operator keys those by the url-quoted name, `Eyelashes%20Lower`, and looks
them up under the material's plain name, `Eyelashes Lower` (`main.py`,
`splitUrl` and `run`, read at the 5.2.0 tag). The two never meet. Run on Kat's
own presets on 2026-09-21 it returned `FINISHED` and left `Eyelashes Lower`,
`Eyelashes Upper`, `Eye Left`, `Eye Right`, `EyeMoisture Left` and `EyeMoisture
Right` with no image, while `Eyebrows_Primary`, which has no space, got all
five of its maps. So the probe parses the preset itself and wires the channels
it understands.

### Swapping a skin, without rebuilding the material

`--mat-preset` fills in what a material is missing and never replaces what is
there, which is right for the bare anatomy and useless for a skin: a skin swap
changes every channel. `--mat-replace` does that, and does it by pointing each
image node at another file rather than rebuilding anything.

The match is the file name. Every Genesis 9 map is named
`<skin>_<part>_<role>_<udim>`, and the role is the last of those that matters:
`D` colour, `SSS` translucency, `R` roughness, `SO` specular overlay, `NM`
normal, `SLW` specular lobe weight. So for each material the preset names, each
of its image nodes is looked up by the role its current file says it has, and
swapped for the preset's file with the same role. The graph the importer built
is untouched. Measured on Kat with `G9 Feminine Skin 03 MAT.duf`: 7 materials,
4 to 6 maps each, nothing left over.

It is applied after `--mat-preset`, because the importer leaves a skin's Base
Color with nothing linked into it and the colour map a swap points elsewhere is
one the fill pass has just added.

**A colour with a map behind it multiplies.** Daz treats a mappable colour
channel as the value times its map, so a hair colour preset carries both: flat
grey for the strands, which have no map, and the same grey over the cap, which
ships a scalp texture. Filling in what is missing cannot do that, because
nothing is missing. So where a preset gives a colour and the material's Base
Color is already linked, the swap puts a multiply between the two. Measured on
the Mavick hair and beard, whose grey preset covers five strand materials by
value and the cap by multiply: without it the cap kept its own brown and read
as hair that did not match the beard.

**Why not the importer's own material loader.** `bpy.ops.daz.import_daz_materials`
is built for exactly this, and on 2026-09-21 it left a Genesis 9 body with
three of its seven material slots: `Fingernails`, `Toenails` and `Legs`
survived, `Head`, `Body`, `Arms` and `Mouth Cavity` did not. It also drops the
channels of any material whose name holds a space, as
[above](#why-the-probe-reads-the-preset-itself). Neither fault is worth working
around when reading the file is this cheap.

### Material merging is off

`easy_import_daz` merges materials that are identical at import time, and every
anatomy material arrives bare and so identical to its neighbour. The eyelash
mesh came out with one material slot for both lash surfaces, and the eyes with
one for all four, which left nowhere for their preset to put anything. The
probe passes `useMergeMaterials=False`, and the eyes and lashes keep their own
materials.

### What the fix is worth, in pixels

Each mesh rendered on its own at 512 px, Cycles on the card, 16 samples,
nothing else in frame, counting pixels with alpha above 0.5 out of 262,144
(2026-09-21, Kat):

| Mesh | Before | After | Mean alpha |
|---|---|---|---|
| `Genesis 9 Eyelashes Mesh` | 11,801 | 1,848 | 0.0449 to 0.0081 |
| `G9 Eyebrows Card Style 12 Mesh` | 9,981 | 4,664 | 0.0377 to 0.0172 |

The cards are still there and still the same size. What changed is that the
lash strokes drawn on them are now the only opaque part, which is what the
`Genesis9_Eyelashes02_C.jpg` map says: 94.5% of it is below 8 of 255 and 3.1%
above 200.

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

## A dressed, posed character, headless

Everything above imports a figure and renders its mouth. This is the rest of
what a person does in Daz Studio: dial a character's shape, put clothes and
hair on it, pose it. Run on 2026-09-18 in the same container, with the same
library and no Daz Studio anywhere, through `scripts/daz_import_probe.py
scene`, which does the steps in the order below and records each one's
seconds, peak RSS and `import_daz.get_error_message()`.

```sh
# every standard morph set, the six character dials, two sliders set and measured
python3 scripts/daz_import_probe.py scene --out output/daz/g9_morphs.blend --anatomy none \
    --morphs units,expressions,visemes,head,body,jcms,flexions,masculine,feminine,powerpose,facsexpr \
    --custom-morphs "data/Daz 3D/Genesis 9/Base/Morphs/Daz 3D/Base Characters 9" \
    --custom-files Kat_figure_ctrl_Character.dsf,Amala_figure_ctrl_Character.dsf,Fabrice_figure_ctrl_Character.dsf,Laura_figure_ctrl_Character.dsf,Matt_figure_ctrl_Character.dsf,Ty_figure_ctrl_Character.dsf \
    --custom-category Characters --custom-bodypart Body \
    --set Kat_figure_ctrl_Character=1.0 --set body_bs_ProportionHeight=1.0 --subdivision off

# a character preset, with its rig, shape keys and materials
python3 scripts/daz_import_probe.py build --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf" \
    --out output/daz/g9_char_kat.blend

# a shirt, shorts and hair onto the figure, then a dial, then a pose
python3 scripts/daz_import_probe.py scene --out output/daz/g9_outfit.blend --anatomy none \
    --morphs body,jcms \
    --custom-morphs "data/Daz 3D/Genesis 9/Base/Morphs/Daz 3D/Base Characters 9" \
    --custom-files Kat_figure_ctrl_Character.dsf --custom-category Characters --custom-bodypart Body \
    --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shirt.duf" \
    --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shorts.duf" \
    --wear "People/Genesis 9/Hair/Daz Originals/Base Hair/G9 Base dForce Pixie Hair.duf" \
    --skip-transfer "dForce Pixie Cut Mesh,dForce Pixie Hair Cap Mesh" \
    --set-dressed Kat_figure_ctrl_Character=1.0 \
    --pose "People/Genesis 9/Poses/Daz Originals/Base Poses/Base/G9 Base Pose 13 Walking G9B.duf" \
    --subdivision off

# the character preset, dressed and posed, saved as the file the renders use
python3 scripts/daz_import_probe.py scene --out output/daz/g9_dressed.blend \
    --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf" --anatomy auto \
    --morphs body,jcms,flexions --facs \
    --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shirt.duf" \
    --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shorts.duf" \
    --wear "People/Genesis 9/Hair/Daz Originals/Base Hair/G9 Base dForce Pixie Hair.duf" \
    --skip-transfer "dForce Pixie Cut Mesh,dForce Pixie Hair Cap Mesh" \
    --pose "People/Genesis 9/Poses/Daz Originals/Base Poses/Base/G9 Base Pose 13 Walking G9B.duf"

# the saved file in a Blender with no add-on at all
python3 scripts/daz_import_probe.py verify --blend output/daz/g9_outfit.blend
```

Those are the commands the numbers below came from, less the `--timeout` each
carried and the `--no-verify` on the first. `scene` runs `verify` itself unless
`--no-verify` is passed, so the last command repeats by hand what the outfit
run already did.

| Stage | Result | Cost |
|---|---|---|
| Eleven morph sets, six character dials, two sliders set | 1593 numeric properties on the rig | 5.0 s wall, 4.86 s in Blender, peak 642.0 MB, container 2.76 to 3.19 GiB |
| A character preset | 158 bones, 40 body shape keys, 18 images | 4.7 s wall, against 1.4 s for `Genesis 9.duf`; the import step alone peaks at 1454.3 MB |
| Three wearables merged into the figure's rig, then a dial and a pose | 233 bones, unchanged by the merge | 5.2 s wall for the whole command, peak 998.4 MB, container 2.22 to 2.90 GiB |
| All of it at once, posed and saved | `g9_dressed.blend`, 140,971,653 bytes, 258 bones | 17.5 s wall, 17.39 s in Blender, peak 1643.7 MB, container 2.29 to 3.59 GiB |
| Reopened with no DAZ add-on | 233 bones, 88 posed, 618 drivers, the dial still 1.0 | 0.8 s wall, peak 578.5 MB |

### Morph sets load with no dialog

A morph operator opens a file selector for a person. Called from Python it
does not: `Selector.getScriptedValues()` returns `None` only for an operator
that was invoked, and otherwise a selection that a plain call never fills, so
the loop falls through to every file the add-on's table lists for the figure
(read in `selector.py` and `morphing.py`). Each set is one operator, and
`--morphs` names them:

| `--morphs` name | Operator | Properties, object + data | Body shape keys | Seconds |
|---|---|---|---|---|
| `units` | `import_units` | 0 + 0 | 0 | 0.00 |
| `expressions` | `import_expressions` | 0 + 0 | 0 | 0.00 |
| `visemes` | `import_visemes` | 0 + 0 | 0 | 0.00 |
| `head` | `import_head` | 0 + 0 | 0 | 0.00 |
| `facsexpr` | `import_facs_expressions` | 0 + 0 | 0 | 0.00 |
| `body` | `import_body_morphs` | 102 + 251 | 5 | 0.19 |
| `jcms` | `import_jcms` | 116 + 122 | 103 | 0.36 |
| `flexions` | `import_flexions` | 27 + 27 | 14 | 0.19 |
| `masculine` | `import_masculine` | 13 + 13 | 11 | 0.21 |
| `feminine` | `import_feminine` | 11 + 11 | 9 | 0.17 |
| `powerpose` | `import_powerpose` | 88 + 92 | 52 | 1.24 |

The first five add nothing for the same reason `import_visemes` does: the
importer's `data/paths/genesis9.json` has no table for them. Ask for the ones
you need, not all eleven: `body,jcms,flexions` is what the dressed build used.

### A character's shape dials are custom morphs

The six `*_figure_ctrl_Character.dsf` files under `data/Daz 3D/Genesis 9/Base/
Morphs/Daz 3D/Base Characters 9` are in no standard set's table, so no
standard operator finds them. `--custom-morphs` runs
`bpy.ops.daz.import_custom_morphs()` on them with `onDrivers='RIG'`. All six
added 86 object and 630 data properties and 61 body shape keys in 1.43 s, and
every call left `get_error_message()` reading `Found morphs that want to
change the rest pose.` One `*_figure_ctrl_Character.dsf` brings its own body
and head morphs with it.

### The sliders, and what they move

`scene` writes every numeric property on the rig object and its data to
`<name>_morphs.json` with its value, hard and soft limits and default. After
the morphs run above there were 1593 of them, 444 on the object and 1149 on
its armature data. The hard limits are the float limits; the Daz limits arrive
as the soft range, so `Kat_figure_ctrl_Character` reads 0.0 to 1.0 and
`body_bs_ProportionHeight` -2.0 to 2.0. Of the 1593, 417 have the soft range 0
to 1, 256 have -1 to 1, 28 have -2 to 2 and 862 have none: those are the
`(fin)` and `(rst)` twins and the corrective morphs, which the dials drive.

`--set NAME=VALUE` writes one and measures the result. Writing the property is
not enough on its own, because a plain write tags nothing and the depsgraph
never runs the drivers; `scene` tags the rig and its objects afterwards. On the
cage with Subsurf off:

| Dial | Vertices moved, of 25,182 | Largest | Mean |
|---|---|---|---|
| `Kat_figure_ctrl_Character` 0 to 1 | 25,182 | 59.67 mm | 42.15 mm |
| `body_bs_ProportionHeight` 0 to 1 | 22,292 | 14.0 mm | 2.34 mm |

### A character preset against the base figure

`--figure` takes a character preset, and the rest of the build is the same.
Measured with `build` on 2026-09-18, each run with `--figure` and `--out`
alone, so no `--facs` and the importer's own Subsurf levels kept:

| | `Genesis 9.duf` | `Kat for Genesis 9.duf` |
|---|---|---|
| Wall time | 1.4 s | 4.7 s |
| Bones | 157 | 158 |
| Properties, object + data | 2 + 4 | 47 + 64 |
| Drivers | 23 | 90 |
| Body mesh | 25,182 vertices, 0 shape keys | 25,182 vertices, 40 shape keys, 39 driven |
| Images | 2 | 18 |
| Eyebrows | Card Style 06, 6944 vertices | Card Style 12, 9000 vertices |

`--no-textures` gives the same mesh, rig and shape key counts with 29 image
texture nodes cleared and no image left in the file. It does not save memory
during the import: that step still peaked at 1454.3 MB, because the importer
reads the maps as it goes. It saves it at render time (see
[textures](#textures-cost-memory-at-render-time)).

### Clothing and hair, and what Morphed fitting loses

`--wear` imports a clothing or hair `.duf` with the figure already in the
scene, in the order given. Each one arrives as its own armature and mesh, the
mesh parented to that armature with an `Armature SkinBinding` modifier
pointing at it: G9 Base Shirt 126 bones, G9 Base Shorts 126, dForce Pixie Hair
Cap 51. `easy_import_daz`'s own `merge_rigs` only merges the rigs that one
import made, so `scene` parents each new armature to the body rig and calls
`bpy.ops.daz.merge_rigs(useOnlySelected=True)` again. It left no armature over
and did not change the body rig's 233 bones, so every wearable bone duplicates
one the figure already has. Afterwards each mesh is parented to the body rig,
its modifier points at it, and it keeps its own vertex groups: shirt 20,
shorts 7, hair cap 18.

::: warning Without a .dbz, an outfit follows the figure but does not reshape
The default fitting route wants a `.dbz` exported from inside Daz Studio, one
per `.duf`. `scene --fit DBZFILE` exits 1 at the figure import: the operator
returned `FINISHED` and made no object, and `get_error_message()` said

```
Mesh fitting set to DBZ (JSON).
Export "/app/models/daz_library/People/Genesis 9/Genesis 9.dbz"
from Daz Studio to fit to dbz file.
See documentation for more information.
```

So this host uses Morphed fitting, and
`bpy.ops.daz.transfer_shapekeys(transferMethod='NEAREST')` returned
`FINISHED`, said nothing, and added **0 shape keys** to the shirt, the shorts
and the face meshes. That is the importer's own documented limit for this
route: "Not all shapekeys are found. Shapekeys are not transferred to
clothes". What it costs, measured: setting `Kat_figure_ctrl_Character` to 1.0
with the outfit on moved every shirt and shorts vertex by 57.25 mm, mean and
maximum equal, a rigid follow of the changed rest pose, while the body itself
reshaped by up to 66.21 mm with a mean of 43.09. Dial a character in and the
clothes go along; they do not take its shape.

`transfer_shapekeys` also cannot run at all on a figure with no shape keys:
its poll wants an active mesh that has some, and it fails with `RuntimeError:
Operator bpy.ops.daz.transfer_shapekeys.poll() failed, context is incorrect`.
Import a morph set first, or pass `--no-transfer`.
:::

The strand hair is a third case. `dForce Pixie Cut Mesh`, 236,136 vertices and
no faces, has one vertex group, `dForce Pin`, which is a simulation group and
not a bone, so its Armature modifier deforms nothing: the pose below moved 0
of its vertices, while every vertex of the 1085-vertex hair cap moved. It also
draws nothing (see
[rendering the dressed figure](#rendering-the-dressed-figure)). Pass it to
`--skip-transfer` so the shape key transfer leaves it alone.

### A pose preset

`--pose` runs `bpy.ops.daz.import_pose()`. On `G9 Base Pose 13 Walking
G9B.duf` it moved 48 of the rig's 233 pose bones, 50 carrying a rotation once
the drivers had run, and wrote no f-curve, so it is a pose and not an
animation. The clothing followed through the shared rig: the body moved up to
801.24 mm, the shirt 214.70, the shorts 214.97, the hair cap 180.89 and the
hair strands 0.00.

::: danger A pose preset zeroes every dial unless you say otherwise
`import_pose` inherits `affectMorphs` and `useClearMorphs`, both `True` by
default, and the operator sets `affectMorphs=False` only in its `invoke()`,
which a Python caller never reaches (read in `animation.py`). The first run
here put `Kat_figure_ctrl_Character` back to 0.0, so the character's shape was
gone from the posed figure. `scene` now passes `affectMorphs=False`, as a person
picking the file in the UI would get. `--pose-affects-morphs` puts the old
behaviour back, for when a pose preset is meant to reset the figure.
:::

### The saved file needs no add-on

```sh
python3 scripts/daz_import_probe.py verify --blend output/daz/g9_outfit.blend
```

`verify` opens the `.blend` in a second Blender with no DAZ add-on enabled, no
extension repository and auto-run scripts off, then counts what is there,
clears the pose and zeroes the dials that were set. On the outfit build, 0.8 s
wall at a peak of 578.5 MB: 233 bones, 88 of them posed, 618 drivers, 267
object and 438 data properties, and `Kat_figure_ctrl_Character` still reading
1.0. Clearing the pose moved the body 801.24 mm, the shirt 214.86 and the
shorts 215.14; zeroing the dial moved the body 66.21 mm and the outfit 57.25.
`scene` runs it for you unless you pass `--no-verify`.

### Rendering the dressed figure

`g9_dressed.blend` is 140,971,653 bytes: 258 bones, 578 object and 803 data
properties, 1031 drivers, all 17 viseme properties, a body of 25,182 vertices
with 339 shape keys, a shirt of 8038, shorts of 8256, a hair cap of 1085,
236,136 hair strand vertices and the five anatomy meshes. Measured on
2026-09-18, from a copy with all 8 Subsurf modifiers off, because
`render_sheet.py` opens a `.blend` as saved and the body carries render level
3. `daz_import_probe.py render --subdivision off` makes that copy and deletes
it again; the sheets below came from one kept beside the file, made the same
way in 0.6 s:

```sh
python3 scripts/render_sheet.py output/daz/g9_dressed_nosubsurf.blend \
    --poses static --size 220 --clay --zoom 1.35 --check --engine eevee \
    --out output/daz/g9_dressed_iso_clay_220_zoom135.png
python3 scripts/daz_import_probe.py render --blend output/daz/g9_dressed.blend \
    --no-sheet --sizes 340 --columns face --only AA --samples 16 --label portraitclay
```

`--engine eevee` is written in because these runs were made before Cycles
became `render_sheet.py`'s default, later the same day. Without it the command still works
and is faster, but it draws a different sheet from the one timed below and from
the probe's own cells beside it.

| Render, all of them EEVEE on llvmpipe | Cells | Time | Container peak |
|---|---|---|---|
| `render_sheet.py --size 128 --clay`, the isometric default | 4 | 45.5 s | 3.46 GiB |
| the same at `--size 220` | 4 | 47.7 s | 3.46 GiB |
| the same with the imported materials | 0 of 4 | ended by its alarm at 1500 s | not sampled to a peak |
| `render --sizes 340 --columns face --only AA --samples 16 --no-sheet` | 2 | 18.8 s in Blender, 24.2 s wall | 3.97 GiB |
| the same with `--materials` | 2 | 479.0 s | 8.54 GiB |

Two things to know before asking for a sheet with the Daz materials on. The
run above took the EEVEE default of 64 samples, Blender's own, which was
`render_sheet.py`'s default at the time,
and on this figure that came out at 26.2 s a sample, from Blender's own
progress lines (sample 1 at 39.01 s, sample 25 at 642.38 s, sample 50 at
1296.78 s), so one cell is about 1700 s and a four-facing sheet about 6800 s.
In clay the same four cells take 45.5 s. Nothing forces the 64: `render_sheet.py
--samples N` lowers it, and the default engine is now Cycles, which path traces
on the card instead of rasterising on the CPU through llvmpipe, and on another
model drew a 16 cell sheet 35 times faster
([scripts](/reference/scripts#render-sheet-py), 2026-09-18). On 2026-09-21
Cycles drew a dressed, posed Genesis figure with its materials on at 768 px in
about 1.5 s a cell, twelve figures over, which is the measurement this
paragraph was waiting for ([below](#a-roster-of-characters-rolled-from-the-library)).
A materials sheet at a low `--samples` under EEVEE is still unmeasured.
The probe's own
renderer also takes `--samples` and keeps the file's settings, which is why the
340 px portraits above are affordable at 16.

In clay, fitted from two runs at each size, a cell costs about 6.9 s at 128 px
over about 17.8 s of fixed cost, and about 9.1 s at 220 px over about 10.5 s.
Those two slopes are derived from four runs, not measured directly.

What the sheets showed, all of it counted with numpy and none of it looked at:
the four facings cover 10.3 to 11.0 per cent of their cells at 128 px, and at
the default `--zoom 1.15` the back view is clipped at both sizes, `cell r0c2
touches its border: the subject is clipped`, which `--zoom 1.35` cleared.
Ignore the rest of that message. It ends `Lower --zoom or raise --size`, and
both halves are wrong: `render_sheet.py` sets the camera's ortho scale to the
subject's extent times `--zoom`, so lowering `--zoom` tightens the frame and
clips harder, while `--size` only changes how many pixels a cell has, which is
why 220 px clipped by 9 pixels where 128 px clipped by 7. Raise `--zoom` to
widen the frame. A
walking pose row differs from a rest row by 1830 to 2491 pixels a facing, 700
to 1573 of them silhouette. A shape dial swept 0.0, 0.5 and 1.0 down the rows
through `"@props"` raised the opaque pixels at every facing, 3694 to 3787 to
3902 at azimuth 45. And the 236,136-vertex strand hair contributes exactly 0
pixels: deleting it gave a 340 px clay portrait identical to the one with it,
0 of 231,200 pixels different by even one level.

### Cloth that clips, measured rather than judged

A garment worn by a figure it was not authored for comes through the skin, and
that is not a matter of taste: a garment vertex on the far side of the body's
surface is inside the body, and the render shows skin where cloth should be.
Every `scene` build now measures it. For each mesh it reports how many of its
vertices are inside, how deep the worst one is and the mean gap, against the
body's evaluated surface, and `--no-fit-report` turns it off.

Read the garments, not the anatomy. An eyeball belongs inside the head: the
Genesis 9 eyes measure 17% to 28% inside whatever you do, and so do the tear
and eyelash surfaces. A pair of shorts at 73% inside is a fault.

**What the dials cost.** Measured on 2026-09-21 on one character in the same
outfit, with and without the three proportion dials a roll had given it:

| | With the dials | With none |
|---|---|---|
| `LVA Pant` inside | 68.7%, up to 70.8 mm | 9.6%, up to 8.9 mm |
| `LVA Shirt` inside | 69.8%, up to 62.4 mm | 0.02%, up to 1.6 mm |
| `Genesis 9 Eyes` inside | 75.7%, up to 14.1 mm | 17.1%, up to 1.1 mm |
| `Genesis 9 Mouth` inside | 50.9%, up to 18.3 mm | 2.6%, up to 4.7 mm |

A dial reshapes the body and nothing it wears follows, because without a `.dbz`
from Daz Studio the clothes take no shape keys from it, and neither do the eye,
mouth and eyelash figures. That is why `daz_characters.py` rolls no dials by
default.

**What is left over without dials.** All six character presets, each in the
armour and in the base clothing, with no dials at all:

| Figure | Worst garment | Inside |
|---|---|---|
| Fabrice, Matt, Ty | none: the worst mesh is an eye or an eyelash | under 18% |
| Amala | `G9 Base Shorts` | 47.1%, up to 9 mm |
| Laura | `G9 Base Shorts` | 50.6%, up to 9 mm |
| Kat | `G9 Base Shorts`, `LVA Pant` | 73.3% and 33.9%, up to 17 mm |

So the armour fits the masculine figures and Amala and Laura, and the base
shorts fit nobody with hips.

### A product that misspells its own file

The Wise Wizard's character preset names its eyebrow figure
`data/Dan Alfaro/WWHD2024/Tools/Script Loads/WW_eyebrows.duf`. The package
installed `WW_Eyebrows.duf`. On Windows, where Daz Studio runs, those are the
same file; here they are not, and the eyebrows silently failed to load.

So every library path the probe is given, the figure, each post-load anatomy
file, each wearable and the pose, is looked up as it is written first and then
one case-insensitive step per segment, and the run says what it re-cased:

```
  anatomy   5 post-load figure file(s)
            re-cased: .../Script Loads/WW_eyebrows.duf is on disk as
                      .../Script Loads/WW_Eyebrows.duf
```

Nothing is renamed on disk. The library keeps what the package installed, the
record still verifies, and `daz_library.py case-check` still reports the
mismatch for whoever wants to know how much of it there is.

### Pushing a garment out of the body

`scene --declip MM` moves every vertex of a worn mesh that sits behind the
body's surface until it stands that far clear of it. The measuring is done on
the evaluated mesh and the moving on the rest shape, because that is what the
`.blend` keeps and the two differ: a character morph drives bones, so a figure
is deformed before any pose is applied. The difference is taken out by
repeating, up to four passes, and the passes stop when nothing moves.

Measured on Kat on 2026-09-21 at `--declip 1.5`, in 1.13 s:

| Mesh | Inside before | Inside after | Vertices moved | Worst push |
|---|---|---|---|---|
| `G9 Base Shorts` | 73.3% | 0.0% | 6,727 of 8,256 on the first pass | 13.95 mm |
| `LVA Pant` | 33.9% | 0.0% | 1,977 of 4,526 | 18.40 mm |
| `Mavick HairStyle` | 0.5% | 0.5% | left alone, 433,512 vertices | |

**A vertex too deep to be clipping is left alone.** A hood sits around a head
rather than through it, and pushing its vertices onto the scalp is what "the
cloak is shifted down" looks like: on the Wise Wizard's cloak, 1,749 vertices
were moved and the worst by 68.09 mm. `--declip-max-push`, 20 mm by default,
leaves those where the author put them. With the cap the same cloak moves 1,031
vertices, leaves 718 alone and keeps 4.95% of itself inside the head, which is
what a hood is; the shorts and trousers that needed pushing, at 13.95 and
18.40 mm, still get it.

Only what the rig deforms is pushed. A bone-parented prop, a staff or a
brooch, is placed rather than fitted, and pushing its vertices onto the body
would bend it: the Wise Wizard's brooch had all 4,560 of them moved before that
rule, and keeps its shape and its 3.25% overlap after it.

A mesh above `--declip-max-verts`, 100,000 by default, is left alone, which is
how a card hair keeps the shape that is its style. A garment carrying shape
keys moves with them: every key block takes the same delta, so whatever it was
adding it still adds. A posed figure is refused, because the rest shape is what
is being edited.

## A roster of characters, rolled from the library

One figure at a time is the slow way to find out what a library can do.
`scripts/daz_characters.py` draws a whole roster out of it: a character preset,
either another character's shape dial or a few proportion dials, an eyebrow
colour, hair, a beard, an outfit, a weapon and an upright pose, then builds each
one through `scene` and renders it front and side.

```sh
python3 scripts/daz_characters.py list                        # what each slot can be
python3 scripts/daz_characters.py make --count 12 --seed 20260921 --dry-run
python3 scripts/daz_characters.py make --count 12 --seed 20260921 --size 768
```

The character presets are dealt out rather than drawn one at a time, so twelve
characters spread over the library's own instead of landing on the same one
four times, and the outfit products are dealt out the same way, one roll each
in turn. Everything
else is a roll: a skin, a hair colour, a beard, an eyebrow colour, which
armour pieces, and a weapon.

Each character keeps the shape its preset gives it. `--dials small` and
`--dials any` roll body dials on top of that, and the measurements
[above](#cloth-that-clips-measured-rather-than-judged) are why they are off:
the clothes and the face do not follow a dial.

A skin is one of the four base skins for the figure's build, or the one the
character came with, swapped map for map with `--mat-replace`. Hair and beard
take the same colour, from the colour presets that sit beside the hair.

Nothing is named in the script. The slots are read from the library, one figure
generation at a time, which is the folder under `People/` that the character
presets sit in: that is what keeps a Genesis 8 hair and a Genesis 9 Toon outfit
out of a Genesis 9 roll, both of which were offered before the generation was
pinned. A character is any `.duf` whose own `asset_info` says `character`,
wherever it sits: one vendor files its own under
`People/<generation>/<vendor>/<product>/` rather than under `Characters/`.
Which base a character is built on decides which skins fit it, so a preset that
names neither keeps the skin it ships with, and one that names neither and
ships no skin is left out, with the reason. An outfit is rolled a product at a
time, and where the product ships a preset that wears all of it, such as
`LVA !All` or `WW Complete Set`, that is worn rather than a guess at which
pieces go together. A wearable is a `.duf` under `Hair/` or `Clothing/` whose
own `asset_info` says `wearable`. A weapon is one of the right-hand grips, which
arrive bone-parented to `r_hand`. A pose is one whose name says standing,
walking, flexing, running or stretching, because the other 61 of the 87 are
seated, laying or flying. The roll is seeded, so the same seed and the same
library give the same roster, and `--dry-run` prints it without building
anything.

### The rest pose, on purpose

No pose is applied by default. Genesis 9's rest pose is the A pose a character
sheet wants, and the library's poses are stretching, running, seated, laying
and flying: they hide as much as they show, and an arm across the chest tells
you nothing about the armour under it. `--poses upright` rolls one of the 26
standing, walking, flexing, running or stretching poses, and `--poses any` from
all 58.

### Framing a set

Every character is drawn by `render_sheet.py --azimuths 0,90 --elevation 0`:
square on at eye level, front and side, two cells cut into two files.
`--azimuths` was added for this, because `--angles` only ever gives evenly
spaced facings and 0 and 90 are not two of four.

The framing is `--span`, a fixed world height, rather than each figure's own
extent, so a short character reads as short instead of being scaled up to fill
its cell. A Genesis 9 figure is 1.755 m from heel to crown, and
`render_sheet.py` shows `--span` times its `--zoom` of 1.15, so the default is
2.0 m in the rest pose: the twelve then filled 75.0% to 80.2% of their cells,
with every pair of feet on one line and nothing touching an edge. With a pose
rolled it is 2.4 m, because at 2.0 a stretching figure was cut off at the top.

### Light, because Daz skin is dark under a sprite sheet's

`render_sheet.py` lights a sheet flat and even, at a sun of 1.6 and a world of
0.22, which suits a clay mesh and leaves a Daz figure in the dark. Measured on
a dressed figure at 512 px on 2026-09-21, over its lit pixels:

| Sun, world | Mean | Median | 95th | Clipped |
|---|---|---|---|---|
| 1.6, 0.22 | 0.248 | 0.228 | 0.337 | none |
| 5.0, 1.0 | 0.375 | 0.376 | 0.620 | 0.04% |
| 6.5, 1.3 | 0.425 | 0.427 | 0.698 | 0.06% |
| 8.0, 1.6 | 0.468 | 0.471 | 0.765 | 0.10% |

So a roster is drawn at 6.5 and 1.3, and `--key` and `--ambient` move it.

### What a run costs and what it keeps

Measured on 2026-09-21 in `comfyui-packaged` on the reference machine, twelve
characters at 768 px with Cycles on the card:

| | |
|---|---|
| Build, each | 10.3 to 25.5 s, 230.9 s over the twelve |
| Draw, two views each | 2.1 to 3.1 s, 30.9 s over the twelve |
| Every exit code | 0, for both commands, twelve times |
| Each `.blend`, before it was deleted | 71 to 179 MB |
| Kept on disk | 8.1 MB, the sheet 4096 by 1629 px of it |
| Height of each figure in its cell | 74.0% to 79.6%, feet on one line |
| Garment vertices inside a body | 0.00% on every garment of all twelve, after 36,455 were pushed out |
| Lit pixels, per figure | a mean of 0.241 to 0.433 of 1, which is the spread of Daz's own skin tones |

That is the first measurement of a Daz figure rendered with its materials on
Cycles, and it settles a question this page left open: on EEVEE through
llvmpipe, with the imported materials and the default 64 samples, one 128 px
cell was about 1700 s and never finished inside its alarm. The same figures
with materials, at 768 px on the card at 128 samples, take 1.43 s a cell.

Each character keeps, under `output/daz/characters/<slug>/`:

```
<slug>_front.png, <slug>_side.png     the two views
<slug>.json                           the roll, the two commands that rebuild
                                      it, exit codes, seconds, drawn pixels
<slug>_scene.json                     the probe's own report for that build
<slug>_build.log, <slug>_render.log   what the two commands printed
```

and beside them `characters.json`, the run's index, and `roster_sheet.png`,
which is the one to open: every character on a flat grey, its views side by
side, under a line naming its base, hair, outfit and weapon. The `.blend` goes
when its views are drawn, unless `--keep-blend`, because a dressed figure is
about 150 MB and twelve are 1.8 GB.

### Naming a character

A rolled character is named after what it is made of, `04-ty-basics`. One that
has been kept is somebody: give a roster entry a `"name"` and the slug, the
folder, the two images and the label on the sheet all take it, as
`01-warrior`, `06-lord-entropy`, `11-alchemist`.

### Keeping four of twelve

A roll is luck, and a roster is read by a person who keeps some of it. The ones
kept go into a roster file, which builds them again with no seed to remember:

```sh
python3 scripts/daz_characters.py keep 1,3,4,12         # writes roster.json
# edit roster.json: a character's clothes, its hair colour, its weapon
python3 scripts/daz_characters.py make --from output/daz/characters/roster.json --prune
```

The file holds one recipe per character, the same shape each character's JSON
already records, so editing it is how a character changes without rolling
anything: swap the `.duf` paths under `wear` for another outfit's, or the
colour preset under `mat_presets` for another colour. `--prune` deletes the
character folders the run did not write, so what is left under
`output/daz/characters/` is that roster and nothing else. Measured on
2026-09-21: four characters rebuilt in 79.5 s, drawn in 10.7 s, eight folders
pruned, `output/daz/` down from 8.1 MB to 2.8 MB.

### Hiding one zone of a garment

A garment is one mesh with several material zones, and the zone is often
exactly the part to lose: the Wise Wizard's cloak keeps its hood in
`03CloakHood`, apart from the cloak itself. `scene --hide-material NAME,...`
takes a zone's alpha to zero, removing any link into it first so the zero
holds, and Cycles then renders nothing there. The mesh stays whole, so
`render_sheet.py` still frames the space the hood occupied: expect a little
headroom above a figure whose hood was hidden.

### Hiding the figure under the costume

`scene --hide-figure` keeps the figure's own meshes out of the render: its
body, and the eyes, mouth, eyelashes, tear and eyebrows that its post-load
script brought with it. `--hide NAME,...` names any others. Nothing is deleted
and nothing moves, so the clothes still fit what they were fitted to and the
declip still has a body to push them off; `render_sheet.py` frames only what it
can see.

That is what a costume with a skull where the face should be needs. Measured on
2026-09-21, a Dark Sovereign set worn over a Genesis 9 character: six meshes
hidden, twelve rendered, every garment 0.00% inside the body, and the drawn
silhouette went from about 57,000 pixels for the same character in a shirt to
134,130 for the robes.

### What it does not roll

- **A hair or clothing colour.** Those materials arrive with their own maps,
  and the material pass only fills in what is missing, so a colour preset would
  change nothing while the JSON claimed it had. Only the eyebrows, which arrive
  bare, take a colour.
- **A grip.** A weapon is bone-parented to the right hand, but the fingers stay
  open: closing them is a second pose file, and `scene` applies one pose.
- **Anything about what it looks like.** The run reports how many pixels each
  view drew, and nothing else. Whether the armour clips, whether the hair reads
  as hair and whether the weapon sits in the hand rather than through it is for
  a person looking at the contact sheet.

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
- **A corrupt gzip file.** Gzip content itself is no longer untested: the
  products taken in on 2026-09-19 brought 260 gzip `.dsf` and `.duf` files, and
  they import. `LVA_Vest_3751.dsf` is gzip and its 3,751 vertex mesh arrived
  fitted; every `Tubal Sword *.duf` is gzip and one was read, imported and
  bone-parented (2026-09-21). None of Starter Essentials' own 3210 `.dsf` or
  637 `.duf` files is gzip. A truncated or corrupt gzip file, which should
  raise `zlib.error`, has still never been fed to any of this.
- **The library's harder stops:** a full disk, SIGKILL or power loss, two
  installs racing without an injected delay, and another program changing the
  library during an install.
- **The Mouth's controllers as separate dials**, FACS Details and HD morphs,
  the six Toon sub-figures and their FilaToon shaders.
- **A `.dbz` fit from Daz Studio**, other material methods, the importer's
  texture resize, and the imported materials under Cycles, which
  `render_sheet.py` now defaults to but which the probe's own renderer has
  not. Without a `.dbz` the clothes get no shape keys
  from the body; how much of that a `.dbz` would recover is unmeasured, and a
  hand-built shape transfer was not tried.
- **The rest of the library.** The roster run on 2026-09-21 covered all 6
  character presets, both Base Clothing pieces the roll uses, 6 of the 7 Viking
  armour pieces, the Mavick hair and beard, 4 of the 5 Tubal weapons and 12 of
  the 87 poses. Still untouched: every Toon figure, every geograft, the bikini
  and bra, `LVA !All`, and the 75 poses that are seated, laying or flying. The
  `anime` and `facsdetails` morph sets and the one-shot
  `bpy.ops.daz.import_standard_morphs()` were never called.
- **dForce simulation.** The pixie hair's 236,136 strand vertices stay in their
  rest shape in the saved file, follow no bone and draw no pixel, which is why
  `daz_characters.py` leaves that product out of a roll and says so. The Mavick
  hair, 433,512 vertices, does follow the rig through an armature modifier, and
  what it looks like has not been judged.
- **What any of it looks like.** Twelve characters were built and drawn on
  2026-09-21 and the run measured only how many pixels each view covered.
  Nobody has said whether the armour clips through the body, whether the hair
  reads as hair, or whether a weapon sits in the hand rather than through it.
- **What the material pass leaves out.** It wires cutout opacity, a colour map
  or flat colour, and a plainly stacked layered colour image. A normal map, a
  roughness map, a layered image with an offset, a scale, a rotation or its own
  blend mode, and every other Iray Uber channel stay as the importer set them,
  and the cost of that to a render is unmeasured.
- **Two dials at once, and values outside the Daz soft range.** One dial was
  swept, at 0.0, 0.5 and 1.0, in clay, at one size.
- **A four-facing sheet with the imported materials**, at any size, and any
  sheet at the Subsurf levels the importer saves. The one attempt at materials
  through `render_sheet.py` was ended by its alarm at 1500 s with no cell
  finished.
- **A portrait through `render_sheet.py`.** It frames the whole subject and has
  no way to aim at the head, so every portrait here comes from the probe's own
  renderer.
- **Any of these sheets beside a pipeline sprite.** Coverage and cell geometry
  were measured so they can be compared, but no side by side against a sheet
  from `output/sheets/` was run.
- **Exporting the visemes** as baked blend shapes to glTF or FBX, and any
  engine reading them. Shipping those needs an Interactive License anyway.
- **Lip sync's Genesis column** ([the mapping](/reference/lip-sync#the-mapping-to-adopt))
  on this figure.
- **Whether reading a Daz render into a Claude conversation** counts under the
  EULA's AI clause, whose examples name chatGPT. The research note leaves it
  open ([Honest uncertainty](/reference/daz-genesis#honest-uncertainty)). The
  by-eye reading above was made that way; until the owner decides, the skill
  reads no render into the conversation.
- **Peak VRAM**, since both render stages here rasterise with EEVEE on the CPU:
  the probe's own renderer has no other engine, and its `render_sheet.py` stage
  is pinned to `--engine eevee`. A Genesis sheet on the card, through
  `render_sheet.py`'s Cycles default, would have one and has not been run.
  Also render times with other jobs running in the container.
- **The default importer verbosity** on a wrong content path; the run used 3.
