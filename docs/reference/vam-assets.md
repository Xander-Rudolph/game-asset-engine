# Virt-A-Mate hair packages, read and fitted to Genesis 9

::: tip Status: researched on 2026-09-23, everything below run or read the same day except one measurement carried over from 2026-09-22
Run, in the container's Blender 4.5.9 (`comfyui-packaged`) with numpy and scipy 1.15.0, and on the host `python3` for the package reader: six `.var` packages were parsed, their guides fitted to a Genesis 9 figure, and the clipping, the fixes and the settle measured. Read and not run: the `.vab` layout, which was worked out from the reader in the third-party yass3d/vkit repository. Nothing proposed here is built into `scripts/`: the code that produced these numbers is experimental and lives under `output/hair/_exp/`. No package, and nothing extracted from one, is in the repo. One number is older than the rest: the skull sphere of VAM-023 was measured on 2026-09-22 and was not re-measured here. The register is [research/claims/vam-assets.json](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/claims/vam-assets.json) on GitHub.
:::

Virt-A-Mate (VaM) has a large library of free, creator-made hair and beard packages, and its figure is Daz Genesis 2. This note is what a package holds, how its binary reads, what it takes to move a Genesis 2 groom onto Genesis 9, what still goes wrong, and why none of it can ship as 3D data. It sits next to [Hair cards](/reference/hair-cards), which is about growing hair the repo owns, and [DAZ Genesis](/reference/daz-genesis), which is where the figure comes from.

## The answer in brief

- **A `.var` is a zip, and its hair is a triple of files per item.** `meta.json` carries `licenseType`, `creatorName`, `packageName` and a `dependencies` map, and each item is a `.vab` binary, a `.vaj` of physics parameters and a `.vam`, under `Custom/Hair/<Male|Female>/<creator>/<item>/`. <!-- VAM-001, VAM-003 -->
- **The `.vab` is readable.** It stores guide curves as absolute world positions in metres, one slot per scalp vertex. The layout was worked out by reading yass3d/vkit, which is MIT or Apache-2.0, read and not run, with no code copied, and then confirmed by parsing six packages. <!-- VAM-005, VAM-007 -->
- **The Genesis 2 head is the same size as the Genesis 9 head and sits about 7 cm higher.** The fit that works is a landmark fit spanning the whole head: scale 0.9899 and offset (0, -0.30, -6.92) cm, residuals 1.68, 2.03, 1.97 and 2.23 cm over four landmarks. Two earlier approaches, a sphere through the hair roots and ICP of the embedded scalp mesh, were discarded on measurement, because both tried to explain that 7 cm with a change of scale. <!-- VAM-017, VAM-018, VAM-020 -->
- **The transform belongs to the creator's authoring figure, not to the package.** Four `scooped` packages put their moustache root centroids within 4 mm of one another, so one transform serves all five. <!-- VAM-021 -->
- **A beard authored to wrap tightly round the mouth cannot be rescued by a transform.** On the Viking beard, 50.3% of moustache strands and 70.7% of chin strands point into the skin after the fit and a root snap, and the corrections the two parts need are in opposite vertical directions. Eight fixes were measured; the one the owner accepted was to pick a beard that does not wrap the mouth. <!-- VAM-024, VAM-025, VAM-027 -->
- **Imported guides must skip clumping.** They carry no `surface_uv_coordinate` attribute, so `Create Guide Index Map` puts every curve at UV (0, 0) and `Clump Hair Curves` pulls the whole head into a single spike. <!-- VAM-032 -->
- **The licence position is the part to get right.** All six packages declare `licenseType` **CC BY**, which covers the strand shapes the creator authored and requires attribution. It cannot cover VaM's own built-in scalps, nor the `DAZMesh` block a `CustomScalp` item embeds, which is reported to be Daz Genesis 2 derived geometry. A VaM-derived asset therefore cannot ship as 3D data on the creator's licence alone. <!-- VAM-002, VAM-009, VAM-035 -->

## Where the packages came from

The owner downloaded six `.var` packages from hub.virtamate.com in a browser, by hand. Nothing was scripted against the Hub, no package was fetched by tool, and no package is in the repo: the files stayed in `~/Downloads`. The Hub's hairstyle listing was read with curl (HTTP 200, consent cookie `vamhubconsent=yes`) to find candidates, and reading listing pages is all that was done there. <!-- VAM-037 -->

The six are `scooped.Clean_Cut.2.var`, `scooped.Viking_Hair.1.var`, `scooped.Lumberjack_Beard.1.var`, `scooped.Smart_Goatee.1.var`, `scooped.Crew_Cut.1.var` and `verytoxic.Boss_Fades.2.var`. Five are by `scooped` and one by `verytoxic`. <!-- VAM-002 -->

## What a package holds

A `.var` is a zip. `meta.json` carries `licenseType`, `creatorName`, `packageName` and a `dependencies` map, which is empty in all six. <!-- VAM-001 --> A hair item is a triple under `Custom/Hair/<Male|Female>/<creator>/<item>/`: `<name>.vab` (binary), `<name>.vaj` (JSON), `<name>.vam` (JSON), plus colour presets under `Presets/*.vap`. <!-- VAM-003 --> One package can hold several items: `scooped.Viking_Hair.1.var` has 84 entries and two items, "Viking Beard" and "Viking Hawk", of three parts each. <!-- VAM-004 -->

### The `.vab` binary layout

The layout was worked out by reading the reader in yass3d/vkit (`native/vkit_core/src/vam/hair.rs`, lines 1942 to 2141 and 1851 to 1900). That project is MIT or Apache-2.0. It was **read, not run, and no code was copied**: the reader used here is a fresh implementation of the layout that source describes, and it was then confirmed by parsing the six packages. <!-- VAM-005 -->

- Strings are .NET `BinaryWriter` strings: a 7-bit encoded length prefix, then UTF-8. Integers are little-endian `i32`, and positions are little-endian `f32` in metres. <!-- VAM-006 -->
- The order is `"DynamicStore"`, a version, optional component blocks, then the marker string `"RuntimeHairGeometryCreator"`, a schema string (`"1.0"` or `"1.1"`), the scalp provider name, an `i32` segment count, an `f32` segment length in metres, a scalp mask name, an `i32` scalp vertex count, one byte per scalp vertex (the mask), an `i32` guide count, then per slot: a `u32` scalp vertex index, an `i32` point count, then that many `x, y, z` triples. <!-- VAM-007 -->
- A slot is written for **every** scalp vertex, and a masked-off vertex has 0 points. The reader here skips any slot with fewer than 2 points. <!-- VAM-008 -->
- A `CustomScalp` item carries a `DAZMesh` block **before** the hair section: the string `"DAZMesh"`, a version, four group name strings, an `i32` vertex count, then `x, y, z` triples in metres. <!-- VAM-009 -->

Measured by parsing the six packages on 2026-09-23:

| Package | Parts, with guides read | Provider | Points per guide | Segment length |
|---|---|---|---|---|
| Clean Cut | cleantop 376, cleanleft 205, cleanright 157 (738) | SoleilScalp | 5 | 0.02 m |
| Viking Hawk | vikingtop 252, vikinghawk 252, vikingfringe 24 | UdaneScalp | 30 | 0.0061 / 0.0042 m |
| Viking Beard | vikingbeard 932, vikingchin 123, vikingstache 193 | CustomScalp | 25 | 0.0023 / 0.0100 m |
| Lumberjack | lumberchin 947, lumberscruff 236, lumberstache 232 | CustomScalp | 13 / 5 / 13 | |
| Smart Goatee | smgoatchin 154, smgoatpatch 29, smgoatstache 170 | CustomScalp | 20 | |
| Crew Cut | crewstache 213, crewstub 1150, crewtop 745 | CustomScalp | 9 / 4 / 4 | |

<!-- VAM-010 -->

Four things that table does not show. `cleantop.vab` reports 922 scalp vertices of which 546 are active. <!-- VAM-011 --> `vikinghawk.vab` and `vikingtop.vab` are both 195,637 bytes and give identical root statistics (252 guides, the same centroid), so they are duplicates of one another. <!-- VAM-012 --> The first hair `.vab` read from `verytoxic.Boss_Fades.2.var` has **no** guide with two or more points, because every scalp slot is empty; the reader reports that rather than failing. <!-- VAM-013 --> And the `DAZMesh` block in the three Viking Beard `.vab` files begins at byte 18 and holds **1,699 vertices**, with group names `["scalp", "scalp", "geometry", "geometry"]`; in the repo's Blender frame its bounding box is x plus or minus 7.59 cm, y -9.79 to 5.20 cm, z 149.28 to 171.08 cm. <!-- VAM-014 -->

### The `.vaj` physics storables

The `.vaj` carries a `Sim` storable whose ids are VaM's own hair physics parameters. Read verbatim from the packages: `cleanleft` has rootRigidity 0.2, mainRigidity 0.01, tipRigidity 0, rigidityRolloffPower 8, drag 0.1, gravityMultiplier 1, weight 1.5, iterations 2, cling 0.5, clingRolloff 1, snap 0.2, bendResistance 0.2, collisionRadius 0.001, collisionRadiusRoot 0.001, friction 0.2, simulationEnabled false, collisionEnabled false, usePaintedRigidity true. `vikingtop` has rootRigidity 0.2, mainRigidity 0.6, tipRigidity 0.0797, rigidityRolloffPower 8, simulationEnabled true. `vikingchin` has rootRigidity 0.4997, mainRigidity 0.5003, tipRigidity 0.5. <!-- VAM-015 -->

### Units and axes

VaM is Unity: metres, +Y up, +Z the face. The repo's Blender frame is +Z up with the figure facing -Y, so the mapping is `(x, y, z)_unity -> (x, -z, y)_blender`. Guide points are **absolute world positions** on a standing figure, not offsets from the root. <!-- VAM-016 -->

## Fitting Genesis 2 hair to Genesis 9

Three approaches were tried, and the first two were discarded on measurement.

**A sphere through the hair roots.** On the Viking package it fits at radius 10.39 cm against this figure's 8.26 cm skull sphere, so scale 0.795. It fits the hair, not the head, and shrank everything by 20% about the wrong centre. <!-- VAM-017, VAM-023 -->

**ICP of the embedded scalp mesh to the skin.** A free similarity converged to a 4.7 mm mean surface residual but slid 7.7 cm up the forehead and put the beard over the eyes. Constrained to scale and offset only, on head skin only, with the closest 70% of correspondences kept, it still left the moustache 6.06 cm too high. A smooth cranium gives a low residual almost anywhere, so the fit is not determined. <!-- VAM-018 -->

**Landmark pairs.** This is what works, with two cautions measured on the way. Bone joint positions are the wrong landmarks: they sit inside the skull, about 1.5 cm behind the skin, and fitting to them parks roots at bone depth. And a lip-and-chin pair alone is a 3.2 cm baseline, which swung the fitted scale from 0.678 to 1.148 depending on which other landmark was added. <!-- VAM-019 --> The working set spans the whole head: the moustache root centroid to the lip skin, the beard roots' left and right deciles to the two ear regions, and the hair part's top decile to the crown. <!-- VAM-020 -->

**The result, fitted on the Viking package: scale 0.9899, offset (0, -0.30, -6.92) cm, residuals 1.68, 2.03, 1.97 and 2.23 cm over the four landmarks.** With it the hawk roots top out at 170.9 cm against this figure's crown at 169.9 cm. <!-- VAM-020 --> Read physically, the VaM figure's head is the same size as Genesis 9's and sits about 7 cm higher, and every earlier fit was wrong because it tried to explain that 7 cm with a change of scale.

The transform belongs to the creator's authoring figure, not to the package. The moustache root centroids of Viking (162.37), Lumberjack (162.41), Smart Goatee (162.60) and Crew Cut (162.44), in Blender z centimetres, agree within 4 mm, so one transform serves all five `scooped` packages. <!-- VAM-021 -->

### The landmarks on Genesis 9

Skin surface, not bone, in world centimetres, on the figure in `output/daz/s_base2.blend`: nose tip (0, -11.84, 155.69); philtrum (0.39, -10.53, 153.43); upper lip skin (0, -10.68, 152.94); lower lip skin (0, -10.40, 151.79); chin front (0, -9.77, 149.98); right ear region (7.21, 0.40, 156.97); crown (0, 0.54, 169.88); highest skin vertex 170.02. The mouth band is x plus or minus 3.51 cm, so 7.02 cm wide, and the lower face x plus or minus 6.64 cm, so 13.28 cm wide. For contrast, the bone heads: `lipuppermiddle` (0, -9.84, 153.0) and `chin` (0, -8.29, 149.28). <!-- VAM-022 --> The skull sphere that `daz_import_probe.py scene --wear-obj` fits is radius 8.26 cm centred 162.1 cm up, measured on 2026-09-22 and not re-measured in this session. <!-- VAM-023 -->

## Why an imported beard clips

Measured after the transform and after snapping every root to the nearest skin point.

- **50.3%** of Viking moustache strands and **70.7%** of chin strands point into the skin, meaning a negative angle between the first segment and the skin normal. 35.8% and 33.3% respectively have a point more than 2 mm deep. The cheek part is much better at 19.0%. <!-- VAM-024 -->
- The moustache roots sit **1.56 cm behind** the lip surface and 0.62 cm above it; the chin roots **1.44 cm behind** theirs and 0.93 cm below. The vertical corrections are in opposite directions, so a single uniform nudge cannot fix both. <!-- VAM-025 -->
- Width is not the problem. The moustache is 7.56 cm wide against the figure's 7.02 cm mouth band, 7% out, and the beard is 8% out against the lower face. <!-- VAM-026 -->

## The fixes, and what each measured

All on the Viking beard unless the row says otherwise. "Inside" is the share of strand points that end up inside the skin after the declip pass.

| Fix | Measured | Outcome |
|---|---|---|
| uniform nudge about the lip, scale 1.03 and 3 mm | 10.2% inside | owner preferred its look |
| the same, scale 1.06 and 6 mm | 7.5% inside | |
| the same, scale 1.10 and 10 mm | 3.3% inside | cleared the lip, but the owner preferred the smaller one |
| per-part offsets, each part to its own landmark | moustache 0.1%, chin 3.7%, cheek 4.7% | rejected: it closed the mouth |
| forward-only per part, moustache 15.6 mm, chin 14.4 mm, cheek 8 mm | moustache 0.5%, chin 2.2% | rejected: the owner still preferred the uniform nudge |
| rotate every in-pointing strand to a minimum exit angle: 12, 20, 28 degrees | rotated 25.2%, 34.2%, 41.4% of strands; whole beard 8.5%, 8.0%, 7.4% inside | rejected: it breaks the combing and reads scruffy |
| local ellipsoidal flex at the mouth, centre (0, -10.2, 152.15) cm, radii 4.8 by 3.8 by 3.2 cm, pushed along the skin normal weighted by a smoothstep | moved 6,122 points, 20.4% of the beard; mouth-region clipping 6.69% to 5.42% at a 7 mm push | rejected by the owner |
| **choose a beard that does not wrap the mouth** | Lumberjack at 0 mm 12.2% inside, **4 mm 9.2%**, 8 mm 7.1% | accepted |

<!-- VAM-027 -->

The conclusion the owner reached is the one to write down: a beard authored to wrap tightly round the mouth cannot be rescued by a transform, so pick a looser beard. <!-- VAM-028 --> One implementation note from the same work: a translation only sticks when the root snap is turned off, because snapping pulls every root back to the nearest skin point and cancels it. <!-- VAM-029 -->

## The settle, and the clump spike

VaM stores the **styled** state and simulates from it in game, so imported guides stand where the creator left them and do not drape until a solver runs. <!-- VAM-030 --> Running the repo's position-based settle from the authored pose, with the part's own storables, makes it fall: the package's `rigidityRolloffPower` of 8 leaves only the first three points of a 24-point strand rigid, and 200 frames of gravity flattened the top, while rolloff 2 with mainRigidity 0.75 keeps the crown and lets the ends drape. <!-- VAM-031 -->

**Imported guides must skip clumping.** They have no `surface_uv_coordinate` attribute, so `Create Guide Index Map` puts every curve at UV (0, 0) and `Clump Hair Curves` pulls the whole head into a single spike. <!-- VAM-032 -->

## What was kept

Three scenes, all in the gitignored `output/daz/`, none of them committed. <!-- VAM-033 -->

- `s_viking.blend` and `s_viking_head.png`: the Viking hawk plus the Viking beard on the uniform nudge the owner chose (scale 1.03, 3 mm). Hawk 4,005 curves at 6.2% inside; beard 13,728 curves at 10.2% inside.
- `s_vhawk_lumber.blend` and `s_vhawk_lumber_head.png`: the Viking hawk plus the Lumberjack chin and moustache shifted 4 mm forward. Hawk 4,005 curves, beard 12,969 curves at 9.2% inside. The Lumberjack `scruff` part, neck stubble of 236 guides at 0.81 cm, was dropped as too sparse to read.
- `s_vam_head.png`: Clean Cut alone, 738 guides to 11,070 curves.

The Smart Goatee was rejected: 353 guides over the chin and lip against Lumberjack's 1,179, and its `smgoatpatch` part is 29 guides, so at the same fill it reads as a sketch rather than a groom. A forward shift improved it, from 23.2% inside at 0 mm to 21.2% at 8 mm, but did not make it usable. <!-- VAM-034 -->

## Licences

### Content and assets, read 2026-09-23

All six packages declare `licenseType` **CC BY** in their `meta.json`, and none is CC0. <!-- VAM-002 --> That is what the packages themselves state; it was read from the files, and the CC BY text has not been through the two-lens check that the `licence-audit` skill and `research/README.md` require, so the reading below is deliberately the conservative one.

- A creator's CC BY covers the **strand shapes they authored**, and requires attribution. <!-- VAM-002 -->
- It **cannot cover the scalp the roots index into**. The built-in providers named in these packages, `SoleilScalp` and `UdaneScalp`, are VaM's own, and a `CustomScalp` item embeds a `DAZMesh` block, which is not the creator's authored strand shapes and is reported to be Daz Genesis 2 derived geometry. <!-- VAM-009, VAM-010, VAM-014, VAM-035 -->
- Therefore a VaM-derived asset **cannot ship as 3D data** on the creator's licence alone. <!-- VAM-035 --> Renders are a separate question, and they are governed by the repo's existing Daz rules in [DAZ Genesis](/reference/daz-genesis).

### Code

The `.vab` layout came from reading yass3d/vkit, which is MIT or Apache-2.0. It was read and not run, and no code was copied: the reader here is a fresh implementation of the described layout. <!-- VAM-005 -->

### Generated output

Nothing generated from a package leaves `output/daz/` or `output/hair/_exp/`, both gitignored. In this session the `DAZMesh` block was read into memory only, to try a fit, and nothing from it was written to the repo. <!-- VAM-036 -->

## What not to do

- **Do not ship a VaM-derived groom as 3D data.** The strand shapes are CC BY, the scalp under them is not the creator's to license. <!-- VAM-035 -->
- **Do not fit by a sphere through the hair roots, or by ICP against a cranium.** Both were measured and both are wrong, because the difference between the figures is a 7 cm offset and not a scale. <!-- VAM-017, VAM-018 -->
- **Do not fit to bone joints.** They sit about 1.5 cm behind the skin and park the roots at bone depth. <!-- VAM-019 -->
- **Do not fit on a short baseline.** Lip and chin alone span 3.2 cm and swung the fitted scale from 0.678 to 1.148. <!-- VAM-019 -->
- **Do not try to rescue a beard that wraps the mouth.** Eight fixes were measured and the only accepted one was a different beard. <!-- VAM-027, VAM-028 -->
- **Do not run the clump nodes on imported guides.** <!-- VAM-032 -->
- **Do not leave the root snap on when a part is translated**, or the translation is cancelled. <!-- VAM-029 -->

## What to build

Nothing from this work is in `scripts/`, and on the licence reading above none of it can become a shipped asset path. What it is good for is reference and measurement: the fitted transform, the landmark set, the clipping shares and the settle parameters are numbers a procedural generator can be judged against. The lessons that carry over to `scripts/make_hair.py` and the [hair cards](/reference/hair-cards#what-to-build) design are the ones the packages made explicit: a groom is authored against one figure and does not transfer by scale; a beard's parts need their own placement rather than one offset, because the moustache and chin corrections point in opposite directions; <!-- VAM-025 --> and a settle needs a rolloff far lower than the 8 these packages ship if the crown is to survive 200 frames of gravity. <!-- VAM-031 -->

## Honest uncertainty

- **The CC BY reading has not been checked against the licence text in this session.** It rests on the `licenseType` field in each package's `meta.json` and on the conservative conclusion drawn from it. Before any of it is relied on beyond "do not ship", it needs the `licence-audit` two-lens check. <!-- VAM-002, VAM-035 -->
- **That the `DAZMesh` block is Daz Genesis 2 derived geometry is reported, not independently checked here.** What was measured is the block itself: 1,699 vertices from byte 18, with group names `["scalp", "scalp", "geometry", "geometry"]`. The licence conclusion does not depend on the Genesis 2 attribution, only on the block not being the creator's authored strand shapes. <!-- VAM-014 -->
- **The `.vab` layout rests on one third-party reader plus six packages.** There is no published specification, and no VaM version other than what these six files were written by was tested. <!-- VAM-005 -->
- **One package would not read at all.** Every scalp slot in the first hair `.vab` of `verytoxic.Boss_Fades.2.var` is empty, and why was not established. <!-- VAM-013 -->
- **The transform was fitted on one package and checked against four.** All five are by the same creator, so it is one authoring figure, not a general Genesis 2 to Genesis 9 transform. <!-- VAM-021 -->
- **Clipping was judged by the share of points inside the skin and by looking.** No engine-side test was run, and no shipping asset was produced, so the shares are a relative score and nothing more. <!-- VAM-024, VAM-027 -->

## Sources worth reading

- yass3d/vkit, `native/vkit_core/src/vam/hair.rs`, MIT or Apache-2.0, for the `.vab` layout. Read, not run. <!-- VAM-005 -->
- The packages' own `meta.json` and `.vaj` files, which are the only statement of their licence and physics parameters. <!-- VAM-002, VAM-015 -->
- [DAZ Genesis](/reference/daz-genesis), for the figure the fit targets and for the rules that govern what may be rendered from `output/daz/`.
- [Hair cards](/reference/hair-cards), for the generator these measurements feed back into.
