# Hair and beard meshes

::: tip Status: researched and checked on 2026-09-23
The owner called off procedural hair on 2026-09-23 and asked for ready-made meshes instead: "go with hair objs instead. same with beards". This page is the first search, for basic male hair and beards. Store pages, licence texts and repository indexes were read on 2026-09-23. Each claim was then read again by a second pass, and every licence claim was also checked for drift against dated snapshots. Free CC0 and CC BY files that could be downloaded were measured on this host with `python3`, and those figures are marked as measured. Nothing was bought, and nothing has been fitted to a figure or rendered. Daz's store was not read, because its Terms of Service forbid automated access. The verified claims behind this page are in [research/claims/hair-meshes.json](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/claims/hair-meshes.json).
:::

Why the procedural route stopped, and what card hair is, are in [hair cards](/reference/hair-cards). What whole characters cost is in [character asset costs](/reference/character-assets). This page asks which hair and beard meshes, free or bought, may go on a figure in this pipeline and ship.

## The answer in brief

- **MakeHuman's own short cuts are the safest free start.** Its system pack's short01, short02 and short04 are CC0 by pack page and file header alike <!-- HAIR-137 -->, and they are already extracted in `input/_devtools/makehuman/hair/` <!-- HAIR-158 -->.
- **Quaternius has a matched stylised set.** Its Universal Base Characters Standard tier is CC0 in the zip, on itch.io and on the pack page, with a buzz cut, a parted cut, long hair and a beard. <!-- HM-007 --> Quaternius's site now also shows a newer Quaternius Asset License, so keep the zip's licence file with the download. <!-- HM-007 -->
- **Free beards are few.** The CC0 ones are MakeHuman's Viking beard, Viking moustache and Faun beard. <!-- HM-003 --> WojackOWL's beard, goatees, moustaches and mutton chops are CC BY and need a credit. <!-- HM-004 -->
- **Labels lie.** Several MakeHuman items labelled CC0 or CC BY carry an AGPL3 header in the file itself. <!-- HM-002 --> Sketchfab's "free" hair includes rips from games, and every source searched has fan art of film and game characters. <!-- HM-006, HM-009, HM-031, HM-032 -->
- **Paid packs cost US$8 to US$30 a style.** The cheapest clean set is a six-style kitbash of solid meshes with a beard and a moustache, at US$8.00 on Gumroad or US$14.99 on TurboSquid. <!-- HM-022 -->
- **Each store's licence sets what may ship.** Fab and CGTrader require that players cannot extract the files; TurboSquid and Blendkit require a proprietary or packed format; ArtStation's Standard tier stops at 2,000 sales. <!-- HM-013, HM-014, HM-017, HM-018, HM-021 -->
- **Nothing free covers a man bun or stubble.** <!-- HM-034 -->

## The shortlist

Triangle counts marked measured come from the downloaded files, triangulated and counted with the host `python3` on 2026-09-23. The rest are the sellers' own figures.

### Hair

| Style | Free | Paid |
|---|---|---|
| Buzz or fade | Quaternius Hair_Buzzed, CC0, 830 triangles measured, solid <!-- HM-007 -->; WojackOWL Low Taper Fade V2, CC BY, 3,096 measured, cards <!-- HM-004 --> | KhitrovArt Buzz Cut Fade, US$19.99 Personal, US$29.99 Professional, 29,502 triangles <!-- HM-024 --> |
| Short or classic | MakeHuman short01, short02, short04, CC0, 3,678, 3,344 and 1,050 measured, cards <!-- HAIR-137 --> | allpolovinkina's kitbash, six short styles, US$8.00 or US$14.99 <!-- HM-022 -->; Zatorska Style M01, US$15.00 Standard, fits Genesis 8 male <!-- HM-023 --> |
| Side part | Quaternius Hair_SimpleParted, CC0, 1,301 measured <!-- HM-007 --> | NoEdge Classic Side Part, US$18.99 Personal <!-- HM-026 --> |
| Medium | WojackOWL Short Hair B, CC BY, 10,544 measured <!-- HM-004 --> | TEAM FROM EARTH middle length with short beard, US$10.49 Standard <!-- HM-029 --> |
| Long, ponytail, man bun | Quaternius Hair_Long, CC0, 2,906 measured <!-- HM-007 --> | NoEdge long, ponytail and man bun, US$18.99 each <!-- HM-026 --> |

### Beards

| Style | Free | Paid |
|---|---|---|
| Full | MakeHuman Beard Viking, CC0, 5,682 measured, style not described by its source <!-- HM-003 -->; Quaternius Hair_Beard, CC0, 1,034 measured <!-- HM-007 -->; Elvaerwyn's Scruffy Beard1, CC BY, 792 measured <!-- HM-004 --> | Verta 3D beard and moustache v5, US$35.00 for commercial use <!-- HM-028 --> |
| Short boxed | WojackOWL Beard, CC BY, 8,932 measured <!-- HM-004 --> | None found as cards outside MetaHuman grooms <!-- HM-016 --> |
| Goatee | WojackOWL Goatee and Goatee Long, CC BY, 414 and 624 measured <!-- HM-004 --> | KhitrovArt goatees, from US$9.99 <!-- HM-025 --> |
| Moustache | MakeHuman Moustache Viking, CC0, 1,364 measured <!-- HM-003 -->; WojackOWL light and thick, CC BY, 368 and 3,472 measured <!-- HM-004 --> | In the US$8.00 kitbash <!-- HM-022 --> |
| Sideburns | WojackOWL Mutton Chops, CC BY, 10,060 measured <!-- HM-004 --> | None found |
| Stubble | None: usually a skin texture, not a mesh <!-- HM-034 --> | MetaHuman grooms only <!-- HM-034 --> |

A free way to try card hair end to end: hamza khaloui's hair, beard and moustache set is free at Fab's Personal tier and US$9.99 Professional. <!-- HM-027 --> Fab's Personal tier is only for buyers under US$100,000 of revenue in the last 12 months. <!-- HM-015 -->

## Free sources

**MakeHuman.** Its community index lists 106 hair and 18 facial hair items, about 20 of them male, and needs no account to download. <!-- HM-001 --> The system pack's ten styles are CC0 <!-- HAIR-137 -->. Measured on 2026-09-23, they are alpha cards with 2048 RGBA diffuse maps, in decimetres, Y up and facing +Z, and each needs its `.mhclo` offsets applied to sit on a body <!-- HAIR-159 -->.

**Labels and headers disagree.** Several items labelled CC0 or CC BY carry an AGPL3 header, among them mhair02, a clean short classic cut labelled CC0. <!-- HM-002 --> MakeHuman's licence page says "All core assets are shared under Creative Commons, CC0", but whether that covers those items was not established. <!-- HM-002 --> Read the `.mhclo` header before using any item.

**WojackOWL's uploads are CC BY**, with no version stated, and need a credit. <!-- HM-004 --> Where its textures came from is an open question: the files carry Blender render stamps naming the uploader's own project, and whether a third-party tool or source went into them was not established. <!-- HM-005 -->

**Quaternius.** The Standard tier's hair is solid, opaque and stylised, skinned to the Head bone, in metres, measured on 2026-09-23. It is CC0 on every page read, but the site's new Quaternius Asset License says the version in effect when you obtained the assets governs. <!-- HM-007 -->

**Sketchfab.** Seventeen hair and beard searches found no CC0 hair or beard asset, but hundreds of CC BY results, 3,495 distinct in all. <!-- HM-008 --> The "free" packs include rips credited to Capcom and Zepeto, and a CC BY label does not show the uploader held the rights. <!-- HM-009 --> Its larger free collections ship without textures. <!-- HM-010 -->

**Elsewhere.** OpenGameArt has Micket's three low-poly male styles and Tiko's CC0 dreads <!-- HAIR-142 -->. <!-- HM-011 --> Poly Haven has no hair, and Blender Studio has no standalone hair asset. <!-- HM-011 --> Blendkit, formerly BlenderKit, has a free "Short hair card" under its Royalty Free licence, and its FAQ says games may use its models "if these can't be extracted by the users in an easy way". <!-- HM-012, HM-013 -->

## Paid sources

- **ArtStation.** Male hair runs US$9.50 to US$15.00 at the Standard tier. <!-- HM-021, HM-023, HM-028 --> The Standard tier covers "one commercial Work" up to 2,000 sales or 20,000 monthly views, but some sellers label it "For Personal Use", and no source says whether that label overrides the EULA. <!-- HM-021 -->
- **Fab.** NoEdge's male cards are US$18.99 each, in OBJ, FBX, Maya and .blend. <!-- HM-026 --> Most free hair and many beards on Fab are MetaHuman strand grooms that work only in Unreal. <!-- HM-016 -->
- **TurboSquid and CGTrader.** Single styles run US$9.99 to US$30.00. <!-- HM-035 -->
- **Superhive and Gumroad.** Superhive's licence has no games clause, and Gumroad has no licence of its own, so a seller's option label is all there is. <!-- HM-019, HM-020 -->
- **Genesis 9 hair from RenderHub and Renderosity** is Daz strand hair, US$11.00 to US$15.99, and converting it to a mesh was not tested. <!-- HM-030 --> Daz's own Genesis 9 hair appears in search results as dForce strand hair, not read on Daz's page. <!-- HM-037 -->
- **Larger packs** cost US$9.99 for ten stylised styles up to US$129.99 for 23 realistic ones. <!-- HM-036 -->

## Licences

| Source | Renders or sprites | 3D in a game build | Credit | AI |
|---|---|---|---|---|
| CC0 (MakeHuman, Quaternius) | Yes | Yes | No | Not checked |
| CC BY (WojackOWL, Elvaerwyn, Sketchfab) | Yes, with credit <!-- HM-004 --> | Yes, with credit <!-- HM-004 --> | Yes <!-- HM-004 --> | Not checked |
| Fab | Yes <!-- HM-014 --> | Yes, if players cannot extract it <!-- HM-014 --> | Not required, per the non-binding summary <!-- HM-014 --> | NoAI listings barred from generative AI <!-- HM-014 --> |
| ArtStation | Yes <!-- CAS-033 --> | Standard up to 2,000 sales; Extended unlimited; no format rule <!-- HM-021 --> | Not checked | Sellers tag AI-made products; no buyer ban <!-- CAS-033 --> |
| TurboSquid | Not checked | Only in a proprietary format; plain glTF or OBJ breaches it <!-- HM-017 --> | Not checked | Renders not for machine learning <!-- HM-017 --> |
| CGTrader | Yes <!-- HM-018 --> | Only with measures that stop players reaching the files <!-- HM-018 --> | Not checked | Buyers now get the "No AI" licence <!-- HM-018 --> |
| Blendkit (BlenderKit) | Yes <!-- HM-013 --> | Only packed so it cannot be opened or separated <!-- HM-013 --> | Not required <!-- HM-013 --> | No clause found <!-- HM-013 --> |
| Superhive, Gumroad | Unclear | Unclear <!-- HM-019, HM-020 --> | Unclear | Unclear |

The CC0 and CC BY rows restate what those licences are. The AGPL3 headers above are why each file's own header must be read first. <!-- HM-002 -->

## What not to do

- **Do not trust a label over a file header.** MakeHuman's repository and its files disagree on several items. <!-- HM-002 -->
- **Do not use fan art or rips.** Iroh's and Superman's hairstyles on MakeHuman, Jack Sparrow's beard on ArtStation and Sketchfab, and game rips on Sketchfab are not cleared by their labels. <!-- HM-006, HM-009, HM-031 --> A Fab groom titled "Elvis Hair" carries a real person's name, and its seller limits it to cinematics. <!-- HM-033 --> Hair 05 is labelled CC0, but its source page is gone and a 2020 comment there says it was "taken from a game called Sudden Attack", which was not verified either way. <!-- HM-003 -->
- **Do not ship TurboSquid or Blendkit hair as plain OBJ or glTF.** <!-- HM-013, HM-017 -->
- **Do not buy a MetaHuman groom for this pipeline.** It works only in Unreal. <!-- HM-016 -->
- **Never fetch Daz's store with a tool.**

## What to build

1. **A fitting step for MakeHuman hair on Genesis 9.** Apply each `.mhclo`'s offsets, fit on the body faces only, and stop the fringe cutting into the forehead, which a shrinkwrapped donor head would do <!-- HAIR-159 --> (`research/untested.md`).
2. **Render the free shortlist on one figure,** short02, Quaternius's buzz and parted cuts, the Viking beard and WojackOWL's goatee, and judge them by eye.
3. **Buy one paid set to test cards end to end,** such as the free-at-Personal hamza khaloui set, if the owner qualifies for Fab's Personal tier. <!-- HM-015, HM-027 -->

## Honest uncertainty

- **mhair02 and the other AGPL3-headed items.** Whether MakeHuman's "core assets are CC0" statement covers them was not established. <!-- HM-002 -->
- **WojackOWL's texture source.** <!-- HM-005 -->
- **Which Quaternius text governs a new download.** <!-- HM-007 -->
- **Whether an ArtStation seller's "For Personal Use" label overrides the EULA's Standard tier.** <!-- HM-021 -->
- **Whether Superhive or Gumroad sellers allow 3D in a game build.** <!-- HM-019, HM-020 -->

## Sources worth reading

- [MakeHuman asset repository](http://www.makehumancommunity.org/) and its licence FAQ. <!-- HM-001, HM-002 -->
- [Quaternius Universal Base Characters](https://quaternius.com/) and the Quaternius Asset License. <!-- HM-007 -->
- [Fab End User License Agreement](https://www.fab.com/eula). <!-- HM-014 -->
- [TurboSquid 3D Model License](https://blog.turbosquid.com/turbosquid-3d-model-license/), [CGTrader terms](https://www.cgtrader.com/pages/terms-and-conditions) and the [ArtStation Marketplace EULA](https://www.artstation.com/marketplace-product-eula). <!-- HM-017, HM-018, HM-021 -->
