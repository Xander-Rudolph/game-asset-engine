# Licensing

If you are making a game to sell, this is the page that matters. Three separate
questions: the animations you apply, the models that generate the mesh, and the
software those models run through. Music has [its own section](#music-and-sound).

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

## Music and sound

This repository makes music with ACE-Step 1.5, whose weights are MIT
([Music](/guide/music)). The question still comes up whenever a soundtrack
comes from anywhere else, and the best-known open model is the one to avoid.

### MusicGen: the weights are non-commercial

Meta's MusicGen comes under two licences. The
[code](https://github.com/facebookresearch/audiocraft/blob/main/LICENSE) is MIT.
The [weights](https://github.com/facebookresearch/audiocraft/blob/main/LICENSE_weights)
are **Attribution-NonCommercial 4.0 (CC BY-NC 4.0)**, and every MusicGen
checkpoint on Hugging Face carries the same tag, small, large, melody and stereo
alike ([for example](https://huggingface.co/facebook/musicgen-large)). Loading
them through `transformers`, which is Apache-2.0, does not change the licence of
the weights. MAGNeT, from the same repository, is non-commercial as well.

The licence allows use "for NonCommercial purposes only". Asked for a commercial
licence, a contributor to the repository answered: "This is not possible, as mentioned by
@rsxdalv the rights were negociated for a research purpose"
([issue #198](https://github.com/facebookresearch/audiocraft/issues/198)). The
model was trained on music licensed from Shutterstock, Pond5 and Meta's own
collection, and those rights were negotiated for research.

::: danger Unsettled is not the same as allowed
Neither the licence nor the model card mentions generated audio, and the same
issue thread argues both ways about whether the non-commercial term reaches it.
Nobody has settled it. Don't ship MusicGen tracks in something you sell. If one
has already shipped, at least don't credit it as licence-free.
:::

### What a commercial project can use instead

Checked against the linked licences and terms on 2026-09-14. Terms change, so
check again before relying on one.

| Option | Licence or terms | In a game you sell |
|---|---|---|
| [ACE-Step v1](https://huggingface.co/ACE-Step/ACE-Step-v1-3.5B) | Apache-2.0 | Allowed |
| [ACE-Step 1.5](https://huggingface.co/ACE-Step/Ace-Step1.5) | MIT, and its model card says the generated music may be used commercially | Allowed |
| [Stable Audio Open 1.0](https://huggingface.co/stabilityai/stable-audio-open-1.0) | [Stability AI Community License](https://stability.ai/community-license-agreement), gated download | Allowed below US$1M total annual revenue, with registration and attribution terms |
| [YuE v1](https://github.com/multimodal-art-projection/YuE/tree/YuE-v1) | Apache-2.0 | Allowed. YuE2, now on the same repository's main branch, is CC BY-NC 4.0 and is not |
| [AudioLDM 2](https://huggingface.co/cvssp/audioldm2) | CC BY-NC-SA 4.0 | Not allowed |
| [Suno](https://suno.com/terms) | Service terms | Paid plans only, for tracks downloaded under them |
| [Udio](https://www.udio.com/terms-of-service) | Service terms | Not allowed on any plan |
| [ElevenLabs Music](https://elevenlabs.io/eleven-music-model-specific-terms) | Service terms | Excludes "Studio Games", roughly a game that earns money and is on more than one platform, except on its Enterprise Music plan |

**ACE-Step 1.5 is the one this repository uses.** It runs on ComfyUI's own nodes,
and its weights, a graph and a loop tool ship here: see [Music](/guide/music).

### Or don't generate it

- [OpenGameArt's music, filtered to CC0](https://opengameart.org/art-search-advanced?field_art_type_tid%5B%5D=12&field_art_licenses_tid%5B%5D=4)
  needs no credit. Its CC-BY and OGA-BY tracks need one.
- [Kenney's Music Jingles](https://kenney.nl/assets/music-jingles) are CC0.
- [incompetech](https://incompetech.com/music/royalty-free/licenses/) is CC BY 4.0
  and needs a credit, or a paid licence that drops it.
- FreePD, often recommended, has closed.

Whichever you choose, write down where each track came from and under what
licence, next to the file. This section exists because a soundtrack made with
MusicGen was credited as licence-free.

## Researched, not shipped

Three research notes check licences for things this pipeline does not do yet.
Each is dated and links the text it read.

- **Voice lines.** Several open text-to-speech models pair permissive code with
  weights or training data that bar commercial use, XTTS-v2 and Piper's lessac
  voice among them. [Lip sync](/reference/lip-sync#text-to-speech-whose-lines-may-ship)
  sorts them into allowed, allowed with conditions, not allowed and unsettled.
- **DAZ Genesis figures.** Sprites and portraits rendered from them may ship
  under the standard Daz EULA. The mesh, rig or morphs inside a build need an
  Interactive License for each product, and the EULA's AI clause puts feeding
  Daz content to this pipeline's models in doubt
  ([DAZ Genesis](/reference/daz-genesis#licences)).
- **Source engine tools.** None is in the image. The Source SDK code may be used
  only to develop a Source 1 mod of a Valve game, and content made with Valve's
  developer tools, such as studiomdl, is non-commercial by default
  ([Source Filmmaker](/reference/source-filmmaker#licences-copy-learn-from-never-vendor)).

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
| nvdiffrast 0.3.3 | **NVIDIA Source Code License, research and evaluation use only** |
| diff-gaussian-rasterization | **Inria Gaussian-Splatting License, research and evaluation use only** |

::: danger Two rasterisers in the image are research-only
3D texturing code leans on a few compiled rasterisers, and two in this image
forbid commercial use outright: `nvdiffrast` and `diff_gaussian_rasterization`.
Unlike the GPL rows above, these limit what you may *use* the software for, not
what you may do with its code. Plain TRELLIS bakes its colour texture through
both, which is why that texture is no clean replacement for Hunyuan3D's paint
([the run and the licence text](/guide/trellis#why-the-colour-is-research-only)).
Its mesh decoder's vertex colours, baked in Blender instead, load neither
([the vertex-colour route](/guide/trellis#the-vertex-colour-route-licence-clean-and-just-as-dark)).
Before trusting any texturing route, read the licence file of every rasteriser
it imports, not just the model card.
:::

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
those regions. TRELLIS (MIT) is the clean choice for a shape shipping there.
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
clause back. The plain TRELLIS branch does return a coloured mesh with no
territory clause, but it bakes that colour through two research-only
rasterisers, so it is no way round the clause for anything you sell
([TRELLIS](/guide/trellis#plain-trellis-was-run-the-colour-works-and-its-licence-does-not)).

The one texture route with no conditions is TRELLIS's own vertex colours,
baked in Blender: a run with both research-only rasterisers blocked finished
cleanly, and the FlexiCubes code it builds meshes with is Apache-2.0. It is a
tested method, not a shipped graph yet, and its colour comes out dark enough
to need matching to the concept afterwards
([the numbers](/guide/trellis#the-vertex-colour-route-licence-clean-and-just-as-dark)).

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

## Meshy, the hosted service the plugin wires in

The plugin's `.mcp.json` configures Meshy's MCP server
(`@meshy-ai/meshy-mcp-server`), which calls Meshy with your `MESHY_API_KEY`. A
Meshy mesh comes under Meshy's service terms, not a model licence, and the
terms depend on your plan and on what you do with the result.

Read on 2026-09-16: Meshy's [Terms of Service](https://www.meshy.ai/terms-of-use)
and the FAQ on its [pricing page](https://www.meshy.ai/pricing). The terms page
was headed "Last Updated: September 19, 2026", three days after that read, and
says changes "take effect on the date indicated as 'Last Updated'". Read both
pages again before relying on this.

| Case | What the page says |
|---|---|
| Free plan | Terms 3.2: Meshy "owns all right, title, and interest, including all intellectual property rights, in and to the AI Customer Output" and licenses it to you under CC BY 4.0, so you "can share and adapt the assets for any purpose, even commercially, as long as Free Customer provides appropriate credit to Provider" |
| Paid plan | Pricing FAQ: "If you are on a premium plan, you own all assets you create with Meshy." Terms 3.2 gives paid plans "the option to keep their User Content private" and does not say who owns their output |
| Released to the Meshy Community page | Terms 3.3: "such output is licensed under the Creative Commons Zero (CC0) 1.0 Universal Public Domain Dedication license" |
| Reference images and other input | Terms 2.2: you warrant "that you have all rights, licenses, and permissions needed to input such Customer Input into the Service". Pricing FAQ: you own the assets "provided that you have used materials that do not violate the copyrights of others in the process of generating your model" |

Four more lines in the terms bear on a game pipeline:

- **AI markers.** Terms 2.4: the service "may include machine-readable metadata,
  digital watermarks, or other identifiers in Customer Output", and "You agree
  not to remove, alter, disable, or otherwise tamper with such identifiers".
  Whether a Meshy export carries any, and whether this pipeline's decimate and
  export steps keep them, was not checked.
- **API output is deleted.** Terms 2.5: output "generated by Customers using the
  APIs, other than Enterprise Customers, will be deleted three (3) days after it
  is generated". The MCP server uses the API, so download what you keep.
- **Training.** Terms 2.9: "Meshy may use Customer Inputs and Customer Outputs
  from non Enterprise Customers" to "train, validate, test, or improve
  Services". The pricing FAQ says the opposite: "We will NOT share your data or
  use it for any training purpose without your consent." The terms say that
  they, with any Order, DPA and the Privacy Policy, "form the entire agreement
  between you and Meshy". The Privacy Policy was not read. Think about this
  before sending unreleased concept art.
- **Competing models.** Terms 2.6 bars using "generated digital assets to train,
  develop, or improve AI models that are competitive with Meshy".

So, per mesh: record the plan it was made on in `sources.json`. A free-plan
mesh comes under CC BY 4.0 and needs a credit to Meshy, while the FAQ calls a
paid-plan mesh "exclusively yours". Don't release a mesh to the Community page
if you mean to keep it to yourself, because it goes out under CC0. Feed Meshy
only images you have the rights to, such as concepts made in this pipeline
under the licences above.

## Kept out on purpose

Image models that are easy to plug in here, and that this repository does not
use. Checked on 2026-09-16.

**FLUX.1 [dev] and FLUX.1 Krea [dev].** The
[FLUX.1 [dev] Non-Commercial License v1.1.1](https://raw.githubusercontent.com/black-forest-labs/flux/main/model_licenses/LICENSE-FLUX1-dev)
grants use of the model "solely for your Non-Commercial Purposes", and says
that "use (a) for revenue-generating activity, (b) in direct interactions with
or that has impact on end users ... is not a Non-Commercial Purpose". Section
4(a) goes further: you will not use the model "(or any Derivative thereof, or
any data produced by the FLUX.1 [dev] Model), in whole or in part, (i) for any
commercial or production purposes". Its outputs clause says "You may use Output
for any purpose (including for commercial purposes), except as expressly
prohibited herein", and 4(a) names data produced by the model. The
[Krea [dev] model card](https://huggingface.co/black-forest-labs/FLUX.1-Krea-dev)
names the licence `flux-1-dev-non-commercial-license`, and its download gate
asks you to agree to the "FluxDev Non-Commercial License Agreement". Neither
belongs in a pipeline for a game you sell.

**Community checkpoints from CivitAI.** There is no one licence to quote. The
realism checkpoints that were on the development machine are not used, and
`img_refine_sdxl.json` records why: "their licensing is unclear and this
pipeline ships game assets". Their licence terms were not read. The refine pass
uses SDXL base instead ([concept art](/guide/concept-art#a-second-pass-for-materials)).

## Hunyuan3D is kept here on purpose

It stays in this setup deliberately. It produces the best meshes of anything here,
and its texture graph is the only one that ships. The territory clause is a
known, accepted condition rather than an oversight. It is not the walkthrough's
shape generator. The walkthrough's texture step and batch script, the
[textures](/guide/textures) page, the generator table in
[meshes](/guide/meshes#which-generator) and the asset pipeline skill each repeat
the licence caveat where they run it, so the choice is in front of you when you
make it.
