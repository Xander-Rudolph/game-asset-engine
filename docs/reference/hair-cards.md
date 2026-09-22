# Hair cards, grown rather than licensed

::: tip Status: researched on 2026-09-22, five experiments run the same day, and the hybrid design built the same day
Nine research passes read the web on 2026-09-22: how production hair-card assets are built, how stylised games build hair, how cards are shaded, the published card generators and their licences, texture atlases, the scalp cap, free hair assets and their licences, what Blender 4.5 can do headlessly, and the geometry of a card layout as an algorithm. 240 claims came back; the duplicates were folded and every load-bearing or licence claim was then checked twice by independent readers told to refute it. Three redesigns of `scripts/make_hair.py` were written from the checked claims and scored by two judges, and a critic listed what is still missing. The register is [research/claims/hair-cards.json](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/claims/hair-cards.json) on GitHub: 152 claims, 21 confirmed, 32 corrected to a narrower wording, 1 unsettled, 98 minor and unchecked.

Run, not read: five experiments in the container's Blender 4.5.9 (Cycles on the RTX 4070 Ti SUPER) on hair the old `scripts/make_hair.py` wrote that day, driven by an ad hoc script kept at `output/hair/_exp/render_exp.py` on this machine, and two prototype probes the design passes left behind, copied to `output/hair_probe_hybrid/` and `output/hair_probe_blender/`. Every number below that carries no claim id was measured that way and says so. The hybrid design under [What to build](#what-to-build) was then built the same day as `scripts/make_hair.py` and `scripts/bake_hair.py`; [What was built](#what-was-built) says which steps landed and what each measured, and the [script reference](/reference/scripts#make-hair-py) and the [guide](/guide/daz-figures#hair-that-is-not-a-daz-product) describe them.
:::

`scripts/make_hair.py` grows hair the repo owns, as ribbon cards with a diffuse and an opacity atlas, and `scripts/daz_import_probe.py scene --wear-obj` places the result on a Genesis 9 head ([the guide](/guide/daz-figures#hair-that-is-not-a-daz-product)). On 2026-09-22 the owner looked at six styles on the figure and kept one: a 5 cm crop, which "needs a scalp texture". The long styles read as stringy strips. This note is what was read and measured before touching the generator again.

## The answer in brief

- **The generator's faces are wound into the head, and that one bug was most of what looked wrong.** Measured on 2026-09-22 with `output/hair/_exp/render_exp.py`: the default bob rendered alone at mean luma 30.5, and the same file with every triangle's winding reversed at **167.9**, five and a half times as bright, with no other change. The "cylindrical normals" result recorded the day before, 3.12 times as bright, was a partial workaround for inverted faces, not the cause. With the winding fixed the four normal schemes sit within 7 percent of each other.
- **Neither density nor transparent bounces made the "black mass".** The 8.8-layer hair rendered at luma 27.1 with Cycles' default of 8 transparent bounces and 27.3 at 64; with its winding fixed it rendered at 151.6, as bright as the 3.2-layer bob. The layers number stays a budget guard and nothing more.
- **Every published card workflow is a layer stack over a scalp cap**, thick to thin outward: a cap mesh with its own darker texture, an opaque base layer that covers the scalp, one or two breakup layers of less opaque cards, hairline transition cards, then flyaways. <!-- HAIR-001, HAIR-008, HAIR-044 --> The generator has one population of equal cards and no cap, which is why skin shows through the crop.
- **A card is one lock, not one strand.** Production tools cluster strands and fit one card per cluster, deriving the card's width from the cluster's spread. <!-- HAIR-087, HAIR-101, HAIR-117 --> Artists place cards in clusters of two to five, most often three, in a tent. <!-- HAIR-002 -->
- **The stylised look is opaque shaped geometry, not alpha cards.** The CC0 VRoid sample's hair is 108 primitives, 52 of them closed lens-shaped shells, whose textures have alpha 255 at every pixel. <!-- HAIR-150 --> The ZBrush stylised write-ups block the volume first and cut it into chunks. <!-- HAIR-022 --> The hybrid prototype's lens shells read as chunky locks where the same guides as strips read as spaghetti (`output/hair_probe_hybrid/B_lens.png` against `B_cards.png`, viewed).
- **Budgets:** 4k to 20k triangles for a game hair, 200 to 400 cards for a realistic style, 3 to 5 segments per card unless it curves. <!-- HAIR-016, HAIR-019 --> The current 320 cards of 14 segments are inside the count and wasteful on segments.
- **Two CC0 sources can stand in for the atlas and as reference:** MakeHuman's system hair pack, ten OBJ-and-PNG styles released as CC0 in 2020, <!-- HAIR-137 --> and OwlishMedia's 85 hair alpha masks at 2048 px. <!-- HAIR-148 --> Blender's bundled hair node groups are CC0 by their in-file licence field, unsettled only because Blender's other demo files are not. <!-- HAIR-138 -->
- **Recommended:** the hybrid redesign, [below](#what-to-build). numpy keeps the layout it already knows and grows guide curves in layers plus a cap; headless Blender turns the base layer into closed lens shells, renders a real-strand atlas and transfers normals from a dome. Both judges chose it over a numpy-only rewrite and a Blender-only rewrite.

## What was measured here before anything was read

All on 2026-09-22, Cycles on the GPU at 128 samples, one sun at 5.5 from the camera side 45 degrees up, a white world at 1.5, the hair alone in frame at 600 px, luma taken over drawn pixels as sRGB bytes. The script is `output/hair/_exp/render_exp.py`; the meshes were written by `scripts/make_hair.py` at commit `1fdbb72` into `output/hair/_exp/` and edited as text.

| Mesh | Change | Mean luma |
|---|---|---|
| bob, 320 cards, 3.2 layers | as written, 62 degree edge normals, no shadow casting | 30.5 |
| bob | every face's second and third corner swapped, so the geometric normal agrees with the written normal | **167.9** with flat sheet normals; 156.4 with the 62 degree tilt; 163.3 with dome normals from the scalp centre; 164.0 with a 50/50 blend |
| bob, winding fixed | shadow casting on | 149.0 flat, 138.4 tilted |
| dense, 1,400 cards of 0.9 cm, 8.8 layers | as written, 8 transparent bounces | 27.1 |
| dense | 64 transparent bounces | 27.3 |
| dense, winding fixed | no shadow casting | 151.6; 126.8 with shadows on |
| bob, as written | dome normals instead of the tilt | 12.7; blend 13.8 |

What that says. `ribbon()` in `scripts/make_hair.py` computes the card normal as `cross(side, tangent)` and `build()` emits the triangles `(a, b, d), (a, d, c)` with `a` on the plus side, whose geometric normal is the opposite vector. Blender's OBJ importer keeps the written normals as custom normals (measured: a `custom_normal` attribute on import, and 100 percent of corner normals more than 20 degrees from their face normal, median 118 degrees) <!-- HAIR-080 --> and Cycles shades a backfacing hit with a flipped normal, so every card was lit as if from inside the head. The 62 degree tilt happened to turn part of each card back towards the light, which is where its 3.12 came from. The same inverted winding is why the dome normals measured worse than the tilt on the unfixed mesh and equal on the fixed one, and why self-shadowing cost a third of the light before and 11 percent after.

An engine that culls back faces, which is the default in every real-time renderer the read sources describe, would have drawn nothing at all from this file. That is the first thing the redesign fixes, and it is one line.

## How production card hair is built

### The layer stack

Card hair is built in layers from the scalp outward, thick to thin: an opaque base layer that covers the scalp completely, then one or more breakup layers of progressively less opaque cards, then transitional hairline cards and flyaways. <!-- HAIR-001 --> Reallusion's production guide says the same from the tool side: cards must originate from the scalp, neither floating above it nor pushed into it, and the hair should be divided into three levels or more of dense, abundant and sparse cards. <!-- HAIR-044 --> Width is constant within a layer and wider nearer the scalp, thinner low-density cards on top, so cards can swap atlas slots without changing their rendered thickness; no source gives a width in centimetres. <!-- HAIR-013 -->

Cards are placed in clusters: three to five in a tent shape, most often three, the card at the base the most opaque and the two on top slightly more transparent, with near single hairs as a flyaway layer. <!-- HAIR-002 -->

### The scalp cap

Every workflow read has a hair cap under the cards, either a separate piece of geometry or hair painted straight onto the head, and short male hair is the case that cannot do without one; the transition from cap to cards is planned with low-density cards. <!-- HAIR-008 --> Reallusion makes the cap by copying or extracting the head's own scalp faces and scaling them outward. <!-- HAIR-036 --> Its texture rules: the scalp diffuse is darker than the strip diffuse so it reads as occluded hair, but not so dark that the hairline segments sharply; the scalp opacity has slightly blurred edges to blend into the head; the specular map carries the same cut-out as the opacity. <!-- HAIR-047 --> It names two uses, gap fillers that only fill sparse areas and need only opacity and diffuse, and exposed scalp for buzz cuts and partings, which is the owner's crop. <!-- HAIR-048 --> One documented way to make the cap texture is a bake of short grown hair onto the low-poly cap, giving alpha, normal, occlusion, depth, id and root maps. <!-- HAIR-050 --> The Blender prototype did exactly that in the container in 0.76 s (`output/hair_probe_blender/cap_diffuse.png`, viewed: an even fuzz of hair-coloured strokes with no bare texels), and MPFB2's own bake operator does it through a Ray Portal BSDF on the card so the bake sees the strands behind it (read from `input/_devtools/mpfb2/ext/mpfb/ui/haireditorpanel/operators/bake_hair_operator.py`).

### A card is a cluster

The two published automatic card extractors both cluster strands with k-means and fit one card per cluster. Strands2Cards clusters on root position plus a PCA projection of the strand shape, and the cluster count is the polygon budget. <!-- HAIR-087 --> The arXiv 2505.18805 extractor clusters on a sample-wise shape metric, frames each card along the cluster's mean strand with Bishop rotation-minimising frames, and sets the half-width at each sample from the members' spread. <!-- HAIR-101 --> Blender's Clump Hair Curves and Houdini's clump node do the same thing on strands rather than cards: pick centre curves at a minimum spacing, assign every curve to its nearest centre, pull it in by a factor shaped root to tip, and spread the tips. <!-- HAIR-117 --> Root distribution in Blender is density-driven Poisson disk sampling scaled by a density mask or a mask texture in the surface's UV space. <!-- HAIR-118 -->

Hair direction by scalp region, from two clinical sources in words without numbers: forward at the frontal hairline with lateral fanning towards the parting, forward on the mid-scalp, a whorl at the crown, backward and downward at the temples, down towards the ear on the sides, down to the nape at the back. <!-- HAIR-106 --> Exit angles in degrees were found on one clinic page only and are not claimed.

### Segments and budgets

A card needs three to five segments along its length unless it curves, and edges should be added only where bending demands them. <!-- HAIR-019 --> Game hair sits in 4k to 20k triangles, manual placement under 10k, and a realistic card style is 200 to 400 planes. <!-- HAIR-016 -->

### The atlas

Published sheets hold a small set of strand variations graded by density, and the counts differ by artist: three islands (full, medium, sparse) to six or nine. <!-- HAIR-017 --> MetaHuman's layout, which the arXiv extractor follows, is 2048 by 2048 holding 32 slots of 512 by 256; long-hair artists lay a 2:1 sheet out with density falling across it. <!-- HAIR-018 --> Every slot is drawn straight, with the curvature in the card mesh. <!-- HAIR-052 --> Reallusion's shader wants strands 2 px or wider, islands 10 to 20 px apart and 32 px of padding, <!-- HAIR-062 --> and colour must be dilated past the alpha edge or filtering pulls the background into strand edges. <!-- HAIR-054 --> Box-filtered alpha mips thin cards with distance; the fix is per-mip coverage preservation, which Unity exposes as a checkbox. <!-- HAIR-055 --> None of that was measured here: whether Cycles mipmaps the atlas at this pipeline's render distances is one of the open checks.

The Blender prototype rendered a real-strand atlas from 127 Cycles hair curves in 0.29 s per pass at 2048 by 1024, eight slots with mean alpha falling 0.395, 0.298, 0.217, 0.160, 0.110, 0.059, 0.028, 0.015 across the sheet, diffuse, root and id passes from one draw (`output/hair_probe_hybrid/report.json`, `output/hair_probe_blender/atlas_combined.png`, viewed). That is the density ladder the sources describe, and nothing in `make_hair.py`'s cosine-stroke painter matches it.

### Normals and shading

Flat card normals are replaced by normals transferred from the head, a proxy mesh or an enclosing sphere, by script in Maya and 3ds Max and by the Data Transfer modifier in Blender. <!-- HAIR-020, HAIR-066 --> Measured here, on the winding-fixed bob, dome normals and flat normals are within 3 percent of each other under a Principled BSDF and a sun; the dome render is the one that shades as a single volume, which is the look the transfer is done for, and the difference is not in the mean. Kajiya-Kay lights hair from the strand tangent rather than a normal, and Scheuermann's card shader shifts two highlights along it; <!-- HAIR-082 --> under such a shader the normal matters less again. Since Blender 4.2 EEVEE has Dithered and Blended render methods, and Blended sorts per object by origin only, <!-- HAIR-070 --> so layers meant to blend must be separate objects or dithered. Cycles caps transparent bounces at 8 by default, up to 1,024; <!-- HAIR-071 --> measured above, that cap was not what darkened the dense hair.

## The stylised case

Three ZBrush stylised-hair write-ups agree on getting the big shapes right before any detail; one gives the full sequence, volume, chunks, flow, crevices, strands. <!-- HAIR-022 --> The CC0 VRoid sample is the only stylised construction that was measured: 108 glTF primitives, 56 open strips three vertices wide and 52 closed lens-shaped shells up to about 1.8 cm thick, 12,384 triangles, two double-sided materials whose 512 by 1024 textures have alpha 255 at every pixel. <!-- HAIR-150 --> The anime look is opaque shaped geometry with painted colour, not alpha cut-outs. No primary breakdown of Arcane, Overwatch, Fortnite, Genshin, Sea of Thieves or Zelda hair was found under any lens; that is recorded as a gap, not filled with a guess.

The hybrid design prototyped both constructions from the same guides on a sphere: closed lens shells (66 faces each at an 8-point profile, manifold) and open strips (8 faces each). The shells read as chunky locks and the strips as strips (`output/hair_probe_hybrid/B_lens.png`, `B_cards.png`, viewed). That, plus the VRoid measurement, is why the recommendation below puts an opaque shell layer under the cards for the stylised look.

## Licences

### Tools, code and node groups

- **Blender** is GPL, and blender.org states that what you create with Blender is your sole property, so hair meshes made by running it and its bundled node groups may ship, while any distributed Python must be GPL-compatible (checked 2026-09-22). <!-- HAIR-090 --> The repo runs Blender and vendors nothing; whether its own `bpy` driver scripts count as distributed add-ons is for the owner and the `licence-audit` skill.
- **Blender's bundled hair node groups** carry `CC0 - Public Domain` in each asset's licence field with copyright Blender Foundation, and the blender-assets repository's LICENSE and README say CC0; Blender's demo files are CC-BY and CC-BY-SA, which is why the claim is unsettled rather than confirmed. <!-- HAIR-138 -->
- **AMD TressFX** is MIT, and its follow-hair generation is readable reference code. <!-- HAIR-092 -->
- **Strands2Cards** has no licence file and GitHub reports none, so it is all rights reserved: readable for parameter values, nothing copied. <!-- HAIR-100 -->
- **GBH Tool** is a GPL Blender add-on that makes cards and renders passes through a camera, not a bake. <!-- HAIR-099 -->
- **Hair Meshes** (Yuksel 2009) is patented and asks every user to contact the author. <!-- HAIR-098 --> The shell construction recommended below is a closed profile swept along a guide, which the VRoid sample shows is ordinary practice; nothing traces strands through a mesh topology.
- **MPFB2** is GPL-3.0-or-later and runs in this container already ([DAZ Genesis](/reference/daz-genesis#makehuman-and-mpfb2)); its hair editor is a 2025 university extension whose card generator instances a 3 by 3 grid along each curve and whose real route loads pre-made cards from a `hair.blend` pack that is not on this machine and carries no licence statement (read from `input/_devtools/mpfb2/ext/mpfb/ui/haireditorpanel/` on 2026-09-22).

### Content and assets

- **MakeHuman's system hair pack** (afro01, bob01, bob02, braid01, long01, ponytail01, short01 to short04) is CC0: every header says so and the pack page lists CC0 for every row. The community `hair01` pack is labelled CC0 by its pack page but its own headers contradict that for several assets, one of which is CC-BY at best. <!-- HAIR-137 --> A separate mirror of older MakeHuman assets is AGPL. <!-- HAIR-043 --> Only the system pack is clean.
- **OwlishMedia's Hair Alphas For Days** on OpenGameArt is CC0: 85 masks at 2048 px, RGB and RGBA. <!-- HAIR-148 -->
- **VRoid Studio** hair you make is yours, pixiv's base content is not CC0, and building an application that outputs VRoid-made meshes needs a pixiv licence; the `HairSample_Female.vrm` on OpenGameArt carries CC0 in its own VRM metadata. <!-- HAIR-147 --> A measurement reference, not a source of geometry for this repo.
- **Quaternius** now publishes the Quaternius Asset License v1.0 (2026-08-28), which bars redistributing assets as assets however modified, while the Universal Base Characters pages still say CC0. <!-- HAIR-146 --> That agrees with the [DAZ Genesis note's](/reference/daz-genesis#the-others-briefly) reading and is recorded there as re-checked. No Quaternius hair enters the repo.
- **Kenney and KayKit** are CC0 and ship no hair meshes. <!-- HAIR-141 -->

### Generated output

Hair written by `scripts/make_hair.py` is the repo's own. Hair grown by running Blender's node groups is the repo's own by Blender's licence page. <!-- HAIR-090 --> A cap shrinkwrapped to a Genesis 9 head would be geometry shaped by Daz data, which `CLAUDE.md` bars from the repo; the design below keeps the cap on the repo's own sphere and lets `--wear-obj`'s declip do the fitting at render time, which never writes Daz-shaped geometry anywhere but the gitignored `output/daz/`.

## What not to do

- **Do not ship the current OBJ to any engine.** Its faces are wound into the head. Cycles hid it; a back-face-culling renderer would draw nothing.
- **Do not tune colours, tilts or lights to fix a dark render** until the winding, the shadow casting and the layer structure are right. Every one of the 2026-09-22 colour changes was chasing the winding bug.
- **Do not grow one strand per card.** A card is a cluster. <!-- HAIR-087, HAIR-101 -->
- **Do not use one card population.** Base, breakup, hairline, flyaway, each with its own width, offset and atlas band, over a cap. <!-- HAIR-001, HAIR-044 -->
- **Do not make the stylised look out of alpha strips.** It is opaque shaped geometry. <!-- HAIR-150, HAIR-022 -->
- **Do not copy from Strands2Cards, Hair Meshes, GBH Tool or the MakeHuman community pack.** <!-- HAIR-100, HAIR-098, HAIR-099, HAIR-137 -->
- **Do not shrinkwrap anything to the Daz head and keep it.**

## What to build

The hybrid redesign, as scored by both judges. numpy keeps what it already does well and Blender does what numpy cannot.

1. **Fix the winding** in `build()`: emit `(a, d, b), (a, c, d)`, and have the report print the signed dot of face normal against the radial so it can never regress. Re-measure findings (a) and (b) with the instrument in `output/hair/_exp/render_exp.py` and replace the numbers in the guide, the reference and the skill.
2. **Layers, not a population.** `LAYERS`: cap, base, breakup, hairline, flyaway, each with its own count, width, offset from the scalp, segment count and atlas band, written inside-to-outside in one OBJ under one `usemtl` per layer. <!-- HAIR-001, HAIR-013, HAIR-044 --> Segments 4 to 6 on straight cards, more only on curls. <!-- HAIR-019 -->
3. **A scalp cap mesh** on the repo's own sphere at the cling radius, bounded by the hairline, with a single pole vertex, its own UV, and two textures: a darker hair-colour base with follicle strokes for exposed scalp, and an opacity that blurs at the hairline. <!-- HAIR-008, HAIR-047, HAIR-048 --> Optionally the Blender fuzz bake for crops.
4. **Guides and clusters.** Poisson-disk roots with a density mask thinned at the front, <!-- HAIR-118 --> a flow field with a crown whorl and the parting as a discontinuity, <!-- HAIR-106 --> guide strands pulled towards cluster centres with a root-to-tip shape and tip spread, <!-- HAIR-117 --> card width from the cluster's spread. <!-- HAIR-101 --> Three-card tents on the breakup layer. <!-- HAIR-002 -->
5. **Opaque lens shells for the base layer of the stylised look**, swept in Blender along the numpy guides with a closed profile and end caps, the construction the VRoid sample and the prototype show; <!-- HAIR-150 --> alpha strips stay for the realistic look and for the outer layers.
6. **A rendered atlas** from Cycles hair curves in Blender: a 2:1 sheet with density falling across it, diffuse, root and id passes from one draw, colour dilated under alpha, strands 2 px or wider. <!-- HAIR-018, HAIR-052, HAIR-054, HAIR-062 -->
7. **Normals** from a dome for the base layer, blended towards the card frame for the outer layers, set in numpy as the direction from the scalp centre or in Blender by Data Transfer; the report prints the mean dot against the radial after the OBJ round trip. <!-- HAIR-020, HAIR-066 -->
8. **Render side:** keep `--obj-no-shadow`, set the card material to dithered for EEVEE, <!-- HAIR-070 --> and leave transparent bounces at 8, which the measurement above shows is enough.
9. **Judge by looking**, now that the owner allows it: the base layer alone must show no scalp from front, sides, top and back before the breakup layer goes on. <!-- HAIR-013 -->

What each step costs and what it touches is in the three design records inside the workflow result; the hybrid one is a few hundred lines in `make_hair.py` and a new container-side `hair_bake.py` of about the same size, run the way `daz_import_probe.py` runs Blender.

## What was built

The same day, as `scripts/make_hair.py` (numpy, the layout) and `scripts/bake_hair.py` (Blender, the geometry and the atlas), against a written contract between the two. Measured on 2026-09-22, the default brown bob:

1. **Winding fixed.** Every face's normal against the radial: cap +1.000, shells +0.917, cards +0.940, printed on every run.
2. **Four layers over a cap.** 90 shells, 150 breakup cards in 50 tents, 40 hairline cards, 30 flyaways, 14 locks; 14,436 baked triangles.
3. **The cap**, 1,296 triangles at 0.15 cm with a follicle diffuse and a rim-blurred opacity.
4. **Poisson roots, a whorl, a parting, clusters.** Nearest-neighbour spacing 2.169 cm at a coefficient of variation of 0.162 against the Fibonacci spiral's 2.085 cm and 0.363.
5. **Lens shells**, closed and manifold, 8-point profile at 0.12 of the width, all with positive signed volume.
6. **A rendered atlas**: 127 Cycles strands in three passes of about 0.35 s, slot mean alphas 0.380 down to 0.009, colour dilated 32 px.
7. **Normals**: shells split at the 60 degree crease and mixed half way to a dome's; corner normals survive the OBJ round trip at a dot of 0.9979 on the unsplit mesh.
8. **Render side unchanged** but for the card material set to dithered.
9. **Judged by looking**: six styles on Genesis 9 at three angles, `output/daz/hair_styles_sheet.png`.

Four things the build found that the research had not said, each measured on the bob before it was changed: a flat shell colour reads as beige plastic, so shells wear the atlas's base slot; laying `u` straight round a closed profile puts only the slot's edge quarters on the outward face and every shell wore a dark band down each flank, checked by the outward face sitting 0.63 cm further from the head centre than the back; smooth shading across the lens crease smears it into a dark band at any dome mix; and a 12-point profile doubled the shell triangles (20,196 on the bob, 37,776 on the curls). The whole pipeline, six styles generated, baked, placed and rendered, took 73 s wall. What is still untested is in `research/untested.md`.

## Honest uncertainty

- **Nothing stylised was found at its source.** No breakdown from Riot, Blizzard, Epic, miHoYo, Rare, Nintendo or Fortiche was reachable; the stylised construction rests on one CC0 VRoid file and three ZBrush tutorials. <!-- HAIR-150, HAIR-022 -->
- **No source gives a card width, a layer offset or a whorl position in centimetres.** Every such number in the design records is marked as a guess.
- **The exit angles by scalp region come from one clinic page.** <!-- HAIR-106 -->
- **The measurements are one light, one framing, Cycles only.** `daz_import_probe.py render` pins EEVEE Next, which sorts blended surfaces per object; <!-- HAIR-070 --> nothing here was rendered in EEVEE.
- **Whether the repo's own `bpy` scripts must be GPL** is a licence question for the owner. <!-- HAIR-090 -->
- **The Blender node groups' CC0** rests on their in-file licence field and the assets repository, against demo files licensed otherwise. <!-- HAIR-138 -->
- **The MakeHuman community pack** is labelled CC0 by its page and contradicted by its own headers. <!-- HAIR-137 --> Only the system pack is relied on.
- **The 'reads as hair' criterion is still an eye.** The arXiv extractor scores cards against strand renders with PSNR and LPIPS; <!-- HAIR-101 --> the repo could score its cards against a Cycles render of hair curves grown from the same guides, and has not.

## Sources worth reading

- Polycount, "hair cards layering" threads and the HairTechnique wiki page, for the layer stack and the cap. <!-- HAIR-001, HAIR-008, HAIR-020 -->
- Reallusion, Character Creator 3.4 Hair Mesh Production and hair shader pages, the only vendor documentation with numbers. <!-- HAIR-036, HAIR-044, HAIR-047, HAIR-048, HAIR-062 -->
- Zatorska on ArtStation, on layer width, budgets and the cap bake. <!-- HAIR-013, HAIR-016, HAIR-050 -->
- Tojo et al., Strands2Cards, SIGGRAPH Asia 2025, and its unlicensed code. <!-- HAIR-087, HAIR-052, HAIR-100 -->
- Zheng et al., arXiv 2505.18805, card extraction with differentiable rendering. <!-- HAIR-101, HAIR-018 -->
- Blender 4.5 manual and source: Data Transfer, Curve to Mesh, Set Curve Normal, the OBJ importer, Cycles bounces, EEVEE render methods. <!-- HAIR-066, HAIR-133, HAIR-080, HAIR-071, HAIR-070 -->
- Kajiya and Kay 1989 and Scheuermann's GDC 2004 slides, for tangent shading. <!-- HAIR-082 -->
- The MakeHuman system asset pack and OwlishMedia's alphas, both CC0. <!-- HAIR-137, HAIR-148 -->
- The VRoid CC0 sample, as the one measured piece of stylised hair. <!-- HAIR-150 -->
