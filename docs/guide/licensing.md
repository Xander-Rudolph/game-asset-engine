# Licensing

If you are making a game to sell, this is the page that matters. Two separate
questions: the animations you apply, and the models that generate the mesh.

None of this is legal advice. The linked licences are the authority.

```sh
scripts/fetch_models.py --licenses
```

## Animations are all clear

| Source | Licence | Catch |
|---|---|---|
| mesh2motion's 176 clips | CC0, public domain | None at all |
| Its 7 motion capture clips | Free for commercial use | Do not resell them as animations |
| Mixamo | Royalty free, no attribution | Same |

The one shared restriction does not bite you. They forbid redistributing the
animation files themselves as animation files. Baking a clip onto your own model
and shipping that inside a game is exactly the permitted use.

CC0 is the cleanest source in the stack, because it has no conditions at all.

## Models are where the constraints are

Most of the stack is MIT or Apache 2.0. Three are not.

### Hunyuan3D 2 and 2.1

The best mesh generator here and the most restricted.

It is royalty free, but the grant is **territorial**. The licence states it does
not apply in the **European Union, United Kingdom and South Korea**, and calls use
outside its territory unlicensed and unauthorised. Above 1 million monthly active
users you need a written licence from Tencent.

::: danger Rendering to 2D does not get around it
A common assumption is that shipping only sprites rather than meshes avoids the
territory clause. It does not. The licence bars using, reproducing, modifying,
distributing or **displaying** the output or results of the output outside the
territory, and output is defined as anything that results from operating the
model. A sprite rendered from a Hunyuan3D mesh is a result of the output.

There is also a clause saying Tencent claims no rights in the outputs you
generate. That is a copyright disclaimer, not a permission. Tencent does not claim
to own your mesh. The territory limit is a contractual condition you accepted when
you took the weights, and it binds regardless of who owns the output.
:::

### StableFast3D

Free under 1 million dollars annual revenue, enterprise licence above it. It is
gated on the model hub, so using it is opt in already.

### RMBG-1.4

Non commercial without a paid agreement. It is kept out of the default download
group and refuses to download without an explicit flag.

You do not need it. Hunyuan3D and TripoSG both remove backgrounds internally using
an Apache 2.0 tool.

### SDXL and SD1.5

OpenRAIL-M. Commercial use of the images is permitted. The licence's use
restrictions travel with the model, not with a mesh you derive from a render.

## Decide per asset, before it ships

| The asset will | Generate it with |
|---|---|
| Ship in a build sold or distributed worldwide | **TRELLIS** (MIT). TripoSG is MIT upstream but ships a territory-limited licence file in this pack, see below |
| Ship only outside the EU, UK and South Korea | Hunyuan3D is fine |
| Never ship: concept, blockout, prototype, look development | Hunyuan3D, freely |

A storefront that sells worldwide reaches all three excluded regions. Steam, itch,
Google Play and the App Store all do.

::: tip Record which generator made which asset
The territory question is unanswerable after the fact otherwise. `sources.json`
in each curated asset folder is the place for it.

If a Hunyuan3D mesh later needs to ship worldwide, the fix is to regenerate it
from the same concept image through TRELLIS. That only works if the concept image
still exists, which is why they are kept rather than swept.
:::

## The licences of the tools themselves

Separate question from the weights, and easy to conflate with them.

| Component | Licence |
|---|---|
| This repository | Apache-2.0 |
| ComfyUI | GPL-3.0 |
| ComfyUI-3D-Pack | MIT, for the pack author's own code |
| ComfyUI-UniRig | **GPL-3.0** |
| ComfyUI-mesh2motion | MIT, declared in metadata, no licence file shipped |
| ComfyUI-CameraPack | MIT, declared in metadata, no licence file shipped |
| Blender / bpy | GPL-2.0-or-later |

::: warning Two corrections to what this page used to say
Both were found by reading the licence files on disk rather than trusting the
upstream project descriptions.

**UniRig is GPL-3.0, not MIT.** Its licence file is 674 lines of verbatim GPLv3.
The "or later" election in the appendix is unfilled, so treat it as GPL-3.0-only.
This does not restrict your game assets, and it does not reach this repository's
own code, which drives ComfyUI over HTTP and imports nothing from the pack. It
does matter if you ever vendor or link that code.

**TripoSG's status inside this pack is unresolved.** Upstream TripoSG is MIT, but
the licence file shipped in `Gen_3D_Modules/TripoSG/` is the Tencent Hunyuan
FlashVDM Community License, carrying the same EU, UK and South Korea exclusion as
the Hunyuan licences, and the module contains FlashVDM code paths. Whether that
file governs the code or was copied in error cannot be settled from the files.

Until it is settled with the pack author, do not treat TripoSG in this install as
unconditionally territory-free. TRELLIS (MIT) is the clean choice for anything
shipping into those regions.

`img2mesh_trellis.json` ships and has been run end to end. It also needs no
cut-out, unlike TripoSG, because it removes the background itself.
[Details, and the second TRELLIS branch that is still unwired](/guide/trellis).
:::

## A route with the fewest conditions

If you would rather track as little of this as possible:

**Qwen-Image or SDXL, then TRELLIS, then decimate, then mesh2motion, then its CC0
clips.**

Qwen-Image is Apache-2.0, TRELLIS is MIT, and the clips are CC0. No territory
clause, no revenue cap, no user threshold on any of them.

Note what this route deliberately avoids and why: TripoSG because of the
unresolved licence file above, and UniRig because it is GPL-3.0. The GPL does not
restrict the assets you generate with it, so UniRig is fine for rigging things you
ship. It is called out only so the choice is a choice.

## This repository's own licence

Apache-2.0. It covers the scripts, the workflow graphs authored here, the prompts,
the poses, the skills, the notebook and these docs.

It covers nothing else, and it cannot. None of the third-party software is
vendored here: the Dockerfile fetches ComfyUI and the node packs at build time,
and weights are downloaded separately. Those licences reach you from their
authors directly.

Apache-2.0 rather than MIT for two practical reasons. It has an express patent
grant, which matters more for inbound contributions than for the code itself. And
its NOTICE mechanism gives the attribution and third-party restrictions a place to
travel with the code, which a project that orchestrates this many differently
licensed components actually needs. See the `NOTICE` file.

Apache-2.0 does not conflict with anything here. This repository imports no pack
code, and GPLv3's own section 5 says that combining a covered work with separate
independent works on the same distribution medium is mere aggregation and does not
extend the GPL to the other parts.

## Redistributing the container image

Building the image for yourself carries no obligations. Publishing it does, and
they are not discharged by this repository's licence.

There are two separate duties, and the image needs both: include the licence
texts, and offer the corresponding source for the compiled binaries. It is not
only Blender. There is 278 MB of GPL-3.0 mesh-processing binaries in there, two
separate GPL ffmpeg builds, and the whole Ubuntu base layer.

**[The full inventory is on its own page](/guide/redistributing)**, including what
is self-satisfying, what needs an offer, the AGPL question that hosting raises,
and what could not be determined.

## Hunyuan3D is kept here on purpose

It stays in this setup deliberately. It produces the best meshes of anything here
and the territory clause is a known, accepted condition rather than an oversight.
It is not the default in the walkthrough, and the licence caveat is repeated on
every page that mentions it, so the choice is always in front of you.
