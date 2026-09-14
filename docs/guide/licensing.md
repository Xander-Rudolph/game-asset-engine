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

Most of the stack uses MIT or Apache 2.0 licences. The four below don't.

### Hunyuan3D 2 and 2.1

The best mesh generator here and the most restricted.

It's royalty-free but **territory-limited**. The licence doesn't apply in the
**European Union, United Kingdom or South Korea**, and it calls any use there
unlicensed and unauthorised. There is a size limit too. If your products or
services had more than 1 million monthly active users in the month before that
Hunyuan version was released, you have no rights under it until Tencent grants
you a separate licence, which it can refuse.

::: danger Sprites don't escape the restriction
A common assumption is that shipping only 2D sprites avoids the territory limit.
It doesn't. The licence bars using, copying, changing, distributing or
**displaying** the model, its output or results of the model outside its
territory. Output means anything that comes from running the model. A sprite
rendered from a Hunyuan3D mesh is still a result of the model.

Tencent's statement that it claims no rights in your outputs is a copyright
disclaimer, not a permission. The territory limit is a condition you accepted by
using the weights. It applies regardless of who owns the output.
:::

### StableFast3D

Free under 1 million dollars annual revenue, enterprise licence above it. It is
gated on the model hub, so using it is opt in already.

### RMBG-1.4

Non commercial without a paid agreement. It is kept out of the default download
group and refuses to download without an explicit flag.

You do not need it. Hunyuan3D and TRELLIS both remove backgrounds themselves,
using rembg (MIT) with its u2net model (Apache 2.0). TripoSG does not remove
backgrounds.

### SDXL and SD1.5

OpenRAIL-M. Commercial use of the images is permitted. The licence's use
restrictions travel with the model, not with a mesh you derive from a render.

## Decide per asset, before it ships

| The asset will | Generate it with |
|---|---|
| Ship in a build sold or distributed worldwide | **TRELLIS** (MIT), left untextured, because the only texture graph runs Hunyuan3D. TripoSG is MIT upstream but ships a territory-limited licence file in this pack, see below, and does not currently produce usable meshes here |
| Ship only outside the EU, UK and South Korea | Hunyuan3D is fine |
| Never ship: concept, blockout, prototype, look development | Hunyuan3D, freely |

A storefront that sells worldwide reaches all three excluded regions. Steam, itch,
Google Play and the App Store all do.

::: tip Record which generator made which asset
The territory question is unanswerable after the fact otherwise. `sources.json`
in each curated asset folder is the place for it.

If a Hunyuan3D mesh later needs to ship worldwide, the fix is to regenerate it
from the same concept image through TRELLIS. That only works if the concept image
still exists, which is why they are kept rather than swept. Leave the new mesh
untextured: a Hunyuan3D texture on a TRELLIS shape still carries the exclusion.
:::

## The licences of the tools themselves

This is a separate question from the model weights, and easy to mix up with them.

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
Both were found by reading the licence files on disk, not by trusting upstream
project descriptions.

**UniRig is GPL-3.0, not MIT.** Its licence file is 674 lines of unmodified
GPLv3, and nothing in the pack adds "or any later version", so treat it as
GPL-3.0-only. It doesn't restrict your game assets. It doesn't reach this
repository's code either: that code drives ComfyUI over HTTP and imports nothing
from the pack. It does matter if you ever copy (vendor) or link UniRig's code.

**TripoSG's licence in this pack is unresolved.** Upstream TripoSG is MIT, but
the licence file in `Gen_3D_Modules/TripoSG/` is the Tencent Hunyuan FlashVDM
Community License. It carries the same EU, UK and South Korea exclusion as the
Hunyuan licences, and the module does contain FlashVDM code paths. The files
alone cannot tell you whether that licence governs the code or was copied in by
mistake.

Until the pack author settles it, don't treat TripoSG in this install as safe for
those regions. TRELLIS (MIT) is the clean choice for anything shipping there.
`img2mesh_trellis.json` ships and has been run end to end, and it removes the
background itself, so it needs no cut-out.
[Details, and the second TRELLIS branch that is still unwired](/guide/trellis).
:::

## A route with the fewest conditions

If you would rather track as little of this as possible:

**Qwen-Image or SDXL, then TRELLIS, then decimate, then mesh2motion, then its CC0
clips.**

Qwen-Image is Apache-2.0, TRELLIS is MIT, and the clips are CC0. No territory
clause, no revenue cap, no user threshold on any of them.

This route ends with an untextured mesh. The only texture graph that ships,
`mesh_texture_hunyuan3d21.json`, runs Hunyuan3D 2.1 and brings the territory
clause back. The plain TRELLIS branch returns a mesh with a colour texture and no
territory clause, but no graph ships for it yet.
[TRELLIS](/guide/trellis#plain-trellis-weights-present-wiring-awkward) lists what
wiring it would take.

Note what this route deliberately avoids and why: Hunyuan3D texturing because of
its territory clause, TripoSG because of the unresolved licence file above (it
also does not currently produce usable meshes here), and UniRig because it is
GPL-3.0. The GPL does not restrict the assets you generate
with it, so UniRig is fine for rigging things you ship. It is called out only so
the choice is a choice.

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
already meets the source duty, what needs a source offer, the AGPL question that
hosting raises, and what could not be determined.

## Hunyuan3D is kept here on purpose

It stays in this setup deliberately. It produces the best meshes of anything here,
and its texture graph is the only one that ships. The territory clause is a
known, accepted condition rather than an oversight. It is not the walkthrough's
shape generator. The walkthrough's texture step and batch script, the
[textures](/guide/textures) page, the generator table in
[meshes](/guide/meshes#which-generator) and the asset pipeline skill each repeat
the licence caveat where they run it, so the choice is in front of you when you
make it.
