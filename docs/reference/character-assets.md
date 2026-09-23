# Character asset costs

::: tip Status: researched and checked on 2026-09-23
Everything on this page was read, not run, apart from two measurements, which are marked. Prices, counts and licence terms were read on 2026-09-23 from store pages, the stores' own public search feeds and licence pages. Each claim a conclusion rests on was then read again by a second pass, and licence claims were also checked for drift against dated snapshots. Daz's own store was not read: its Terms of Service forbid automated access. Every Daz store price here comes from a search result and is marked unverifiable. Prices change daily, and totals are sums of listed prices, not checkout quotes. Nothing was bought. The verified claims behind this page are in [research/claims/character-assets.json](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/claims/character-assets.json).
:::

Which character ecosystems are worth keeping, if the aim is to keep costs down? This page prices the same small fantasy cast in each ecosystem: four humans, two lizardfolk and a dragon, each with an outfit and hair. It covers base figures, complete characters, clothing and armour, hair and beards, and non-human figures. The licence rules behind each tool are in [commercial character tools](/reference/character-tools) and the [DAZ Genesis note](/reference/daz-genesis#licences).

## The answer in brief

- **The free and open route costs nothing and may ship as 3D.** Quaternius's CC0 base characters, outfits and hair, OpenGameArt's CC BY reptile and Quaternius's CC0 dragon make the whole cast for US$0, or US$39.99 with Quaternius's paid Source tiers. <!-- CAS-043 --> The styles do not match across sellers, and only MPFB2 has facial shapes. <!-- CAS-043 -->
- **Autodesk Character Generator cannot finish the cast.** It makes humans only, and its cheapest entry, a Mudbox subscription, ends sale on 7 November 2026, after which the entry cost is about US$2,010 a year. <!-- CAS-027, CAS-028, CAS-029 -->
- **Reallusion is the cheapest paid route that can complete the cast,** at US$277 at list or US$205.80 with September's offer, but it needs Windows, its dragons are iClone props rather than Character Creator figures, and none of its content may go near an AI stage. <!-- CAS-015, CAS-019 -->
- **Daz has the widest catalogue but no priced reptile or dragon.** Its humans, outfits and hair come cheap, but the two "reptile" and "dragon" items first found are a human woman and a costume. <!-- CAS-001, CAS-009 -->
- **Poser costs about US$397 and may not ship as 3D.** Most of its fantasy items carry only the Standard licence. <!-- CAS-026 -->
- **ZBrush with bought base meshes costs about US$535 to US$810** plus the retopology, UV, texturing and rigging labour, and its 3D may ship within ArtStation's licence terms. <!-- CAS-035, CAS-033 -->

## One cast, priced six ways

The cast is four humans, two lizardfolk and one dragon, each with an outfit and hair. Totals are sums of prices read on 2026-09-23.

| Route | Total | Completes the cast? | 3D in a game build | Runs on this Linux host |
|---|---|---|---|---|
| Free and open | US$0; US$39.99 with Source tiers <!-- CAS-043 --> | Yes <!-- CAS-043 --> | Yes, with a CC BY credit for the reptile <!-- CAS-039, CAS-043 --> | Yes: plain glTF and FBX |
| Reallusion | US$277 list, US$205.80 on offer, including a year of Character Creator 365 <!-- CAS-019 --> | Yes, if the iClone dragon animates without iClone 8 <!-- CAS-015, CAS-019 --> | Only in a proprietary format, and never near an AI stage <!-- CHT-001, CHT-004 --> | No: Windows only <!-- CHT-025 --> |
| Daz and Genesis stores | About US$80 priced, plus unknown lizardfolk and dragon <!-- CAS-009 --> | No priced lizardfolk or dragon <!-- CAS-009 --> | Needs an Interactive License per product <!-- DAZ-003 --> | Import only, through Diffeomorphic <!-- DAZ-035 --> |
| Poser and Renderosity | US$397.17 list <!-- CAS-026 --> | Yes <!-- CAS-026 --> | No: most items are Standard only <!-- CAS-026 --> | No: Windows only <!-- CHT-056 --> |
| Autodesk Character Generator | US$105 a year, about US$2,010 after 7 November 2026 <!-- CAS-027, CAS-029 --> | No: humans only <!-- CAS-029 --> | Forum posts only <!-- CHT-033 --> | Web service |
| ZBrush and ArtStation | US$534.97 to US$809.97, plus labour <!-- CAS-035 --> | Yes <!-- CAS-035 --> | Yes, within ArtStation's sales cap or with Extended <!-- CAS-033 --> | No: Windows, macOS and iPadOS <!-- CHT-044 --> |

## Free and open

- **Humans.** Quaternius's Universal Base Characters are free in their Standard tier with 5 hairstyles and a beard, and US$19.99 or more for Source with 20 hairstyles; the matching Modular Character Outfits Fantasy has 12 outfits. <!-- CAS-036 --> The Standard zip holds two bodies, so four humans means reusing them. <!-- CAS-043 --> KayKit's monthly series sells 14 or 15 rigged CC0 characters for US$19.99 each, orcs and a Black Knight among them. <!-- CAS-036 -->
- **MakeHuman.** The community repository holds 3,421 assets, including 1,360 clothes, 89 of them uniforms or armour, and 106 hair items, each under CC0 or CC BY. <!-- CAS-041 --> The system assets pack is all CC0 with 10 hair styles, Hair 01 and the Bodyparts 05 beards are CC0, and Hair 02, Hair 03 and the Bodyparts 06 beards are CC BY. <!-- CAS-037 --> Bodyparts 03 adds CC BY tails and wings, a dragon wing among them. <!-- CAS-037 --> No lizard target was found; the CC BY snake and reptile targets include two that say they are based on Disney's Kaa, and the CC0 Suits 02 pack has three items named after existing fictional characters, so check a name before shipping. <!-- CAS-037 -->
- **Dragons.** Quaternius's Ultimate Monsters page says "License CC0". <!-- CAS-038 --> Measured on 2026-09-23 by parsing its glTFs with Python: Dragon_Evolved has 46 joints including wings, Dragon has 13, each has 8 animations, and neither has a morph target. <!-- CAS-038 --> The pack's licence file reads "CC0 1.0 Universal" under a header naming a different pack, a copy-paste slip. <!-- CAS-038 -->
- **Lizardfolk.** No free CC0 rigged lizardfolk was found in eight sources. <!-- CAS-039 --> The nearest free one is OpenGameArt's "Rigged, textured Reptile", under CC BY 3.0 among other licences, with a required link to opengameart.org in the credit. <!-- CAS-039 --> OpenGameArt also has a CC0 rigged, animated snake. <!-- CAS-039 -->
- **Sketchfab.** Its search finds far more under CC BY than CC0: 7,159 distinct downloadable dragons against 56 CC0, and 503 lizardmen, 437 of them animated, against none. <!-- CAS-040 --> The CC0 hits are mostly museum scans and real animals, and CC BY results include fan art of other companies' characters, which CC BY does not clear. <!-- CAS-040 -->
- **Paid tiers.** Quaternius's Patreon is US$10 a month for one Source key a month, the Complete KayKit Collection US$150 or more, and Blender Studio US$17 a month. <!-- CAS-042 -->

## Daz and the Genesis stores

The Genesis 9 base is free, with base clothing, a Pixie hair and eight skins. <!-- CAS-001, DAZ-048 --> Renderosity lists 457 Genesis 9 characters, 1,010 clothing items and 389 hair items. <!-- CAS-001 --> RenderHub and Renderosity sell Genesis 9 characters, outfits and hair from US$9.00 on sale to US$25.00 at list. <!-- CAS-003 -->

Every Daz store price comes from search results, not Daz's page. <!-- CAS-002, CAS-004, CAS-006 --> They show Drakarae, a reptilian Genesis 9 figure with a tail, at US$25.99, orcs and goblins with no price found, and DAZ Dragon 3, a separate quadruped figure. <!-- CAS-004 --> Daz+ shows as US$8.99 a month or US$69 a year. <!-- CAS-006 --> Daz ran sales of about 30% to 50% in late 2025. <!-- CAS-007 -->

Shipping 3D needs an Interactive License per product, US$35 to US$50 on the products checked, and licence add-ons take no discount. <!-- DAZ-003, DAZ-048, DAZ-053 --> RenderHub's Extended Use License allows commercial games, but only as "part of a larger Creation", and bars competing with the original. <!-- CAS-008 --> The owner's shopping list names 41 Daz products: 25 outfits or armour sets, 12 weapons, props or accessories, three character bundles and a lich visage, 29 of them for Genesis 9. <!-- CAS-010 -->

## Reallusion

Character Creator 5 is US$299.00 perpetual or US$99 a year as Character Creator 365. <!-- CAS-011 --> PRIME, at US$99 a year for 15% off, pays back only above about US$660 of purchases a year. <!-- CAS-011 --> In September 2026, 455 of 489 hair items and 2,352 of 2,430 outfits were 30% off. <!-- CAS-011 -->

- **Characters.** Orc Warrior is US$59.00 and the Fantasy Creatures morph pack US$45.00; ActorCore's medieval actors are US$30.00 each. <!-- CAS-012 -->
- **Armour.** The Modular Medieval Knight Bundle is US$80.00, built around the CC3+ male base. <!-- CAS-013 --> The median CC outfit lists at US$19.50, and none is free. <!-- CAS-013 -->
- **Hair.** CC hair lists from US$6.00 to US$923.00, median US$18.99, and none is free. <!-- CAS-014 -->
- **Non-human.** HD Alien Mixer Lizard Alien is US$49.00. <!-- CAS-015 --> The dragon packs, US$49.00 and US$75.00, are iClone props, not Character Creator figures. <!-- CAS-015 --> Reallusion staff say AccuRIG is for "human and other types of bipedal characters" and Character Creator "can't rig quadruped or non bipedal characters". <!-- CAS-016 -->
- **iContent** costs "30 percent of the Standard License" but is sold only inside the apps and may not be exported. <!-- CAS-018 -->
- **Catalogue.** The Content Store holds 4,469 Character Creator items, and searches find 56 dragons and 9 lizards. <!-- CAS-017 -->

## Poser and Renderosity

Poser 14 is US$175.00. <!-- CHT-056 --> La Femme 1 Pro and L'Homme 1 Pro are US$29.95 each, and many add-ons require them. <!-- CAS-020 --> Renderosity lists 1,466 products for La Femme 1 but only 37 for L'Homme 2, and fantasy searches are thin. <!-- CAS-024, CAS-021 -->

Non-human options are better here than for Genesis: LaReptile gives lizardfolk morphs and skins for US$16.95, and Poser dragons such as Lindwurm III cost US$10.00. <!-- CAS-022 --> Prime membership is US$39.95 a year, with member discounts of 40% to 70% and sales running continuously. <!-- CAS-025 --> Where a product offers the Extended licence it cost three times the Standard list price on all eight pages read, and it ignores sale prices. <!-- CAS-023 -->

## Autodesk Character Generator

Its catalogue has "over 100 body types, outfits, hairstyles, and physical attributes", in three styles, one of them "Gorn, with exotic or fantastical body types". <!-- CAS-028 --> No fantasy outfit, beard, reptile or dragon option was found. <!-- CAS-028 --> Mudbox, US$105 a year, is the cheapest entry; its one-year and monthly subscriptions end sale on 7 November 2026, and Maya is then US$2,010 a year. <!-- CAS-027 --> The service's licence gap is in [commercial character tools](/reference/character-tools#autodesk-character-generator).

## ZBrush and ArtStation

ZBrush bundles human and animal Mannequins and a 100-project ZeeZoo of animals and birds, but no dragon or reptile, and no character preset library. <!-- CAS-030 --> ArtStation searches find 5,481 human base meshes, 188 dragon base meshes and 1 lizardman base mesh. <!-- CAS-030 -->

Base meshes cost from US$5.00 to US$25.00, and hair and beard cards from US$0.00 to US$10.49. <!-- CAS-031 --> A rigged Kobold / Lizardman costs US$39.99, Extended only. <!-- CAS-032 --> ArtStation's Standard licence allows one commercial work up to 2,000 sales; Extended removes the cap, at a price each seller sets, from 3 to 12 times Standard on the pages read. <!-- CAS-033, CAS-034 -->

## Non-human options side by side

| Route | Lizardfolk | Snake | Dragon |
|---|---|---|---|
| Free and open | OpenGameArt reptile, CC BY 3.0 <!-- CAS-039 --> | OpenGameArt snake, CC0, rigged <!-- CAS-039 --> | Quaternius, CC0, 46 joints, 8 animations <!-- CAS-038 --> |
| Daz | Drakarae, US$25.99, unverifiable <!-- CAS-004 --> | Not found | DAZ Dragon 3, price unverifiable <!-- CAS-004 --> |
| Reallusion | Lizard Alien, US$49.00 <!-- CAS-015 --> | Not found | iClone prop packs, US$49.00 and US$75.00 <!-- CAS-015 --> |
| Poser | LaReptile, US$16.95 <!-- CAS-022 --> | Snake Man, US$16.99 <!-- CAS-022 --> | Lindwurm III, US$10.00 <!-- CAS-022 --> |
| Autodesk | None <!-- CAS-028 --> | None <!-- CAS-028 --> | None <!-- CAS-028 --> |
| ArtStation | Kobold / Lizardman, US$39.99 <!-- CAS-032 --> | Not searched | Dragon + Wyvern base meshes, US$15.00 to US$90.00 <!-- CAS-034 --> |

## Licences

| Route | Renders or sprites | 3D in a game build | AI |
|---|---|---|---|
| CC0 | Yes <!-- CAS-043 --> | Yes <!-- CAS-043 --> | Not checked |
| CC BY | Yes, with credit <!-- CAS-039 --> | Yes, with credit <!-- CAS-039, CAS-043 --> | Not checked; fan art of others' characters is not cleared <!-- CAS-040 --> |
| Daz | Yes <!-- DAZ-001 --> | Interactive License per product <!-- DAZ-003 --> | Barred <!-- DAZ-007 --> |
| RenderHub Extended | Yes, commercial use <!-- CAS-008 --> | Only as part of a larger work; no extraction protection required <!-- CAS-008 --> | No clause <!-- CAS-008 --> |
| Reallusion Standard | Yes <!-- CHT-003 --> | Proprietary formats only <!-- CHT-004 --> | Barred <!-- CHT-001 --> |
| Renderosity | Standard, yes <!-- CHT-054 --> | Extended only, with encryption, at 3x <!-- CHT-054, CAS-023 --> | No clause <!-- CHT-054 --> |
| ArtStation | Yes, in films, videos and games <!-- CAS-033 --> | Standard up to 2,000 sales; Extended unlimited <!-- CAS-033 --> | No buyer ban <!-- CAS-033 --> |

## What not to do

- **Do not take a store's word for what a product is.** Two items first found for this cast as a reptile and a dragon were a human woman and a cosplay costume. <!-- CAS-009 -->
- **Do not assume a CC BY or CC0 model is clear.** The licence covers the author's own work, not someone else's character, and both Sketchfab and the MakeHuman repository hold models of existing characters. <!-- CAS-040, CAS-037 -->
- **Do not buy a Personal Use Only item for the game.** One Genesis hair product on RenderHub is licensed for non-commercial use only. <!-- CAS-009, CAS-003 -->
- **Do not count on the Character Generator route past 7 November 2026** without budgeting for Maya. <!-- CAS-027 -->
- **Never fetch Daz store pages with a tool.** Read prices in a browser.

## What to build

1. **Import the free cast in the container.** Quaternius's base characters and dragon and OpenGameArt's reptile are glTF or FBX, so they can go straight through `scripts/render_sheet.py`. None has been rendered here yet.
2. **Match their style.** The three sources do not match; a shared material or palette pass is the cheapest fix.
3. **Price the owner's Daz list by hand.** Only a browser read can give those prices. <!-- CAS-010 -->

## Honest uncertainty

- **Daz prices and memberships.** Every Daz store figure is unverifiable here. <!-- CAS-002, CAS-004, CAS-006 -->
- **Whether Reallusion's iClone dragons animate in Character Creator 5 without iClone 8.** <!-- CAS-015 -->
- **Whether Autodesk Flex tokens unlock Character Generator** after the Mudbox subscriptions end. <!-- CAS-027 -->
- **Prices move daily.** Every sale price on this page was read on 2026-09-23, and several sales end within a week.

## Sources worth reading

- [Quaternius](https://quaternius.com/), [KayKit](https://kaylousberg.itch.io/), [OpenGameArt](https://opengameart.org/) and the [MakeHuman asset repository](http://www.makehumancommunity.org/). <!-- CAS-036, CAS-038, CAS-039, CAS-041 -->
- [Reallusion Content Store](https://www.reallusion.com/contentstore/) and [Marketplace](https://marketplace.reallusion.com/). <!-- CAS-017 -->
- [Renderosity Marketplace](https://www.renderosity.com/marketplace) and [RenderHub's licensing](https://www.renderhub.com/info/3d-content-licensing). <!-- CAS-008, CAS-024 -->
- [ArtStation Marketplace EULA](https://www.artstation.com/marketplace-product-eula). <!-- CAS-033 -->
- Autodesk's [Mudbox](https://www.autodesk.com/products/mudbox/overview) and [Character Generator](https://charactergenerator.autodesk.com/). <!-- CAS-027, CAS-028 -->
