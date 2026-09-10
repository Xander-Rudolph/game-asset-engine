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
| Ship in a build sold or distributed worldwide | **TripoSG** or **TRELLIS**, both MIT |
| Ship only outside the EU, UK and South Korea | Hunyuan3D is fine |
| Never ship: concept, blockout, prototype, look development | Hunyuan3D, freely |

A storefront that sells worldwide reaches all three excluded regions. Steam, itch,
Google Play and the App Store all do.

::: tip Record which generator made which asset
The territory question is unanswerable after the fact otherwise. `sources.json`
in each curated asset folder is the place for it.

If a Hunyuan3D mesh later needs to ship worldwide, the fix is to regenerate it
from the same concept image through TripoSG. That only works if the concept image
still exists, which is why they are kept rather than swept.
:::

## A route with no conditions at all

If you would rather not track any of this:

**Qwen-Image or SDXL, then TripoSG or TripoSR, then decimate, then UniRig or
mesh2motion, then CC0 clips.**

Every link in that chain is MIT, CC0 or OpenRAIL. No territory clause, no revenue
cap, no user threshold. It is the default in this repo's first asset walkthrough
for that reason.

## Hunyuan3D is kept here on purpose

It stays in this setup deliberately. It produces the best meshes of anything here
and the territory clause is a known, accepted condition rather than an oversight.
It is not the default in the walkthrough, and the licence caveat is repeated on
every page that mentions it, so the choice is always in front of you.
