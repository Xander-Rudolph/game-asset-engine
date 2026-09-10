# Redistributing the image

Building the image for yourself carries no obligations. **Publishing it does**, and
this repository's Apache-2.0 licence does not discharge them, because the
obligations belong to software this repository does not own and does not contain.

None of this is legal advice. It is an inventory taken by reading the image, so
that the question is at least answerable.

::: danger Scope this before you rely on it
The inventory below was taken from a **running container** built from an earlier
Dockerfile than the one in this repository today. The two differ in ways that
change the answer: the running image gets its node packs from a host bind mount,
while the current Dockerfile clones them into the image.

A compliance note written against a running container and one written against a
fresh build are different documents. **Rebuild, then re-verify**, before treating
any of this as describing what you actually published.
:::

## Two duties, not one

The commonest mistake here is collapsing these into each other. They are separate,
and satisfying one does not satisfy the other.

**Include the licence text.** If you distribute GPL software, in source or binary
form, you must give recipients a copy of the licence itself. Per-file SPDX headers
are notices, not a licence copy.

**Offer the corresponding source.** If you distribute compiled object code, you
must also make the source that produced it available. GPLv3 section 6(d) lets you
do this by offering it from a network location alongside the object code, which is
the practical route when you publish to a registry.

A component can need one, both, or neither.

## What is in the image

### Source is present, so distribution is self-satisfying

These carry their own source, so conveying them conveys the corresponding source
too. Nothing extra to do beyond leaving them intact.

| Component | Licence | Why it is satisfied |
|---|---|---|
| ComfyUI v0.30.2 (`dec5d945`) | GPL-3.0 | Full non-shallow clone at `/app`, 49,214 objects, and `/app/LICENSE` is verbatim GPLv3 |
| comfyui-manager 4.2.2 | GPL-3.0-only | Pure Python, `LICENSE.txt` present |
| ultralytics 8.4.143 and friends | **AGPL-3.0** | Pure Python. See the network clause below |
| plyfile, easydict, comfyui-embedded-docs, PyGithub | GPL-3.0+, LGPL-3.0 | Pure Python |

### Compiled binaries whose source is not present

Each of these needs a source offer, and the offer has to name an exact version to
be worth anything.

| Component | Version | Licence | Size on disk |
|---|---|---|---|
| bpy (Blender) | 4.5.9 | see below | 89 shared objects, ~652 MB |
| pymeshlab | 2025.7.post1 | GPL-3.0 | 151 shared objects, ~278 MB |
| igraph | 1.0.0 | GPL-2.0 | 4 shared objects, ~15 MB |
| pymeshfix | 0.18.1 | AGPL-3.0 classifier, GPL-3.0 text | 1 shared object |
| comfy-3d-viewers | 0.2.44 | GPL-3.0-or-later | Minified JS, no licence file at all |
| ffmpeg (apt) | 7:4.4.2 | GPL-2.0+ (built `--enable-gpl`) | |
| ffmpeg (bundled in imageio-ffmpeg) | 7.0.2 | GPL-3.0 (`--enable-gpl --enable-version3`) | ~80 MB |
| The Ubuntu 22.04 base | 396 GPL-mentioning packages | various | no source in the image |

::: warning This list is longer than it first appears
An earlier draft of this project's `NOTICE` named only Blender. That was
materially incomplete: 278 MB of GPL-3.0 mesh-processing binaries, two separate
GPL ffmpeg builds, and the entire base layer are in exactly the same position.
:::

### Blender is the interesting one

It is worth stating precisely, because the obvious summary is wrong in both
directions.

**Some Blender source *is* in the image.** The wheel ships 746 Python files under
`bpy/4.5/scripts/`, 395 of them headed `SPDX-License-Identifier: GPL-2.0-or-later`.
So the image distributes GPL source, which triggers the licence-copy duty.

**The wheel ships no copy of the GPL text.** Nothing in the `bpy` tree matches
"GNU GENERAL PUBLIC LICENSE", and its `dist-info` has no LICENSE file. The image as
a whole does carry `/usr/share/common-licenses/GPL-2` and `GPL-3` from the Debian
base, so the gap is in the package rather than the image, but do not rely on an
accident of the base layer to discharge a duty.

**The C and C++ source is genuinely absent**, and `bpy/__init__.so` is 213 MB of
object code built from it. That is the part needing a source offer.

**The licence identifier conflicts with itself.** The wheel's METADATA declares
`License: GPL-3.0`, while every GPL-headered file it ships says
`GPL-2.0-or-later`, which matches Blender upstream. Write "GPL-2.0-or-later" and
note the metadata discrepancy rather than picking one silently.

The C and C++ source that *does* ship, under `addons_core/cycles/source/`, is the
Cycles render kernel and is Apache-2.0, BSD-3-Clause, MIT and Zlib. It is not the
corresponding source for the binary, and it is not GPL. Do not count it as either.

## The AGPL question, which is not answered here

`ultralytics` is AGPL-3.0, and the entire purpose of this image is to serve
ComfyUI over a network port. AGPL section 13 extends the source obligation to
users interacting with the program remotely.

Whether that reaches you depends on whether you expose the server to other people
and whether ultralytics is reachable through what you expose. **This was not
analysed.** If you plan to host this image as a service rather than run it
locally, resolve it before you do.

## What to do before publishing

1. **Rebuild from the current Dockerfile** and re-take this inventory. The
   published artefact is the one that matters.
2. **Ship the licence texts.** GPL-2.0 and GPL-3.0 both, given Blender's "or
   later" and UniRig's GPL-3.0 election.
3. **Publish a source offer** naming exact versions, alongside the image, and keep
   it reachable for as long as the image is offered. Blender's source is at
   `download.blender.org/source/`; the others have upstream releases.
4. **Decide the AGPL question** if the image will be hosted rather than run.
5. **Remember the territorial and non-commercial terms** on the vendored Tencent
   code, covered in [licensing](/guide/licensing). A public registry reaches every
   territory, including the three the Hunyuan licences exclude.

## What is still unresolved

Recorded so the gaps are visible rather than implied to be absent.

- **15 installed distributions declare no licence at all.** One of them,
  `comfyui_frontend_package`, is minified JavaScript whose source maps embed the
  original TypeScript. Whether a source map is the "preferred form for making
  modifications" is a legal call, not a technical one.
- **libigl and gpytoolbox each ship two licence files** (a GPL text alongside
  MPL-2.0 and MIT respectively). Which files each governs is not answerable from
  the wheel.
- **nvdiffrast** carries a restrictive NVIDIA licence upstream. Not copyleft, but
  it has its own terms and they were not read.
- **Per-file licensing inside ComfyUI-3D-Pack** was not re-audited here. That is a
  file-level audit rather than a metadata sweep.
- **The pixi environment UniRig builds on first run** provisions further components
  after the image ships, and was not inventoried.
