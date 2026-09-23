# Commercial character tools

::: tip Status: researched and checked on 2026-09-23
Everything on this page was read, not run. Nothing was installed, downloaded from a store or tested on this host: no Character Creator, iClone, Poser, ZBrush or Autodesk Character Generator, and none of their content. The licence texts, product pages, knowledge base articles, manuals and forum posts were read on 2026-09-23. Older texts came from Wayback Machine captures, and the Poser 14 EULA from inside its installer. Each licence claim was then read again from its primary text by a second pass, with a drift check against dated snapshots. Nothing proposed under [What to build](#what-to-build) is built. The verified claims behind this page are in [research/claims/character-tools.json](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/claims/character-tools.json).
:::

The [DAZ Genesis note](/reference/daz-genesis) weighed Daz, MakeHuman, VRoid, MetaHuman and a first look at Character Creator 5 as human bases for the sprite pipeline. This page takes the commercial tools further: Reallusion's Character Creator 5 and 3 and iClone 7, Autodesk Character Generator, Poser 14 and ZBrush. The questions are the same. What may a game sold worldwide ship? Can the content go near the pipeline's AI stages? Does the tool run on this Linux host? Mouth shapes and visemes are covered in [lip sync](/reference/lip-sync), and hair the repo owns outright in [hair cards](/reference/hair-cards). What each ecosystem's clothing, hair and non-human figures cost is in [character asset costs](/reference/character-assets).

## The answer in brief

- **Reallusion content must stay out of every AI stage.** The Content EULA bars Content and its derivatives "For machine learning, AI training, or AI-generated output", and only an Enterprise licence lifts it. <!-- CHT-001, CHT-007 --> Characters built on the Character Creator base carry their own ban on "AI training, machine learning, or synthetic data generation". <!-- CHT-002 --> That rules out a Qwen-Image restyle, a TRELLIS mesh or any other ComfyUI stage fed from Reallusion content, the same line the Daz note draws. <!-- CHT-001 -->
- **Reallusion renders may ship; its 3D data may ship with conditions.** The Standard licence grants imagery use that "includes using the Content in ... games", and separately grants use "in commercial games, AR/VR projects and interactive services". <!-- CHT-003 --> But shipped 3D models must be "contained in proprietary formats so that they cannot be opened or imported into a publicly available software application", and a restriction on "embedded content within applications or online services" sits against the game grant. <!-- CHT-004 --> Reallusion's visible FAQ says plainly that purchased content may be used "for distributing your game title", though the FAQ does not bind. <!-- CHT-071 -->
- **The free CC base characters are the one Reallusion asset this host can use without Windows.** Five rigged bases in FBX, OBJ and ZBrush formats, with UDIM textures and 150 or more facial morphs, are free with a Reallusion account for commercial use including games. <!-- CHT-008, CHT-009 --> They are the CC3+ base that Character Creator 5 still builds on. <!-- CHT-061 -->
- **Autodesk Character Generator has no clear licence for its output.** No current Autodesk terms page names the service, and the General Terms assign no ownership of Output. <!-- CHT-031 --> The only explicit permission for games is in forum posts, none shown to be from Autodesk staff. <!-- CHT-033 -->
- **Poser's 3D data is mostly Restricted Content, and its two Poser 14 EULA texts differ.** <!-- CHT-050, CHT-051 --> No Poser EULA has an AI clause. <!-- CHT-053 -->
- **ZBrush is a sculpting tool, not a content source.** Your own sculpts are yours to use on a paid plan, and the one AI clause bars training a model that does what ZBrush does. <!-- CHT-040, CHT-041 -->
- **None of these tools runs on Linux.** Reallusion's current products and Poser 14 are Windows only, ZBrush runs on Windows, macOS and iPadOS, and Character Generator is a web service reached through an Autodesk subscription. <!-- CHT-025, CHT-056, CHT-044, CHT-030 -->

## Character Creator 5

Character Creator 5 needs Windows 11 or 10 and 8 GB of video memory. <!-- CHT-010 --> Its latest release is v5.13, dated 1 September 2026. <!-- CHT-011 --> The 30 day trial allows 30 exports to FBX, OBJ or USD and caps images at 800x600. <!-- CHT-010 --> It may not be used commercially: the download page marks "Commercial Use" as not included for the trial, and the Software EULA grants rights only for software "purchased under a perpetual license or used under an active subscription license". <!-- CHT-068 --> Price and subscription terms are in the [DAZ Genesis note](/reference/daz-genesis#other-character-bases-compared).

Two agreements govern it, and they are separate. The Software EULA covers the tool and anything built on its base mesh. The Content EULA covers every asset from Reallusion's stores, ActorCore included. <!-- CHT-002, CHT-013 -->

**The base-model grant is narrow.** The Software EULA says the "unique topology and character rigs" of a CC Avatar "are the property of Reallusion". <!-- CHT-002 --> It grants commercial use, games included, only for an "Original Character Creation": a character made "without using any content from Reallusion or its developers, including models, morphs, textures, hair, and outfit assets". <!-- CHT-002 --> A character dressed in bundled skin, hair or clothes falls under the Content EULA instead. Even an original character may not go into a character generation system, a character-generating business or a marketplace, or into AI training. <!-- CHT-002 -->

**Lapsed plans lock files.** When a Content One-Year Plan ends, files saved in Reallusion's own format "revert to Trial Content" and "cannot be exported". <!-- CHT-005 --> A lapsed software subscription does not touch outputs "lawfully generated during an active subscription period". <!-- CHT-005 --> Export everything while the plan is live.

**Free content.** Beyond the five bases, Character Creator 5 offers a Free Resource Pack of "CC5 HD assets, including complete projects, ready-to-use assets, ActorMIXER content, and lighting presets" through its in-app content manager. <!-- CHT-012 --> No Reallusion page read names its licence. The pack is Reallusion's embedded content, and the only answer on embedded content, that it carries a Standard licence or Extended for CC Components, covered iClone 8 and Character Creator 4 and is now withdrawn from the page. <!-- CHT-066 --> iContent, the render-only tier, is sold only inside the apps. <!-- CHT-066 --> ActorCore gives "3 actors and 32 motions free when you sign up, and free content every month". <!-- CHT-014 --> The two free ActorCore items opened each showed "Standard License: $0.00", but the free listing also holds paid items discounted to nothing. <!-- CHT-067 --> AccuRIG is a free auto-rigger for Windows only, and since version 1.3.6 it asks for a login when it starts. <!-- CHT-014 --> Reallusion's AI Studio is governed by a third agreement: Starter output is "non-commercial use only", and Free Plan output is public by default. <!-- CHT-016 -->

**Into Blender.** The CC/iC Blender Tools add-on is GPL-3.0 (code), with release 2_4_3 on 2026-08-09, and its README names Character Creator 3, 4 and 5. <!-- CHT-015 --> Its companion bake add-on has had no release since 2022-11-26. <!-- CHT-015 --> Under CLAUDE.md's rules it is linked, never vendored.

## Character Creator 3

Character Creator 3 is legacy. Its last release is v3.44, "released on Nov 15th, 2021", the store no longer sells it, and its online manual now returns a "Page Not Found" body. <!-- CHT-060 --> From version 3.1 its FBX export needed 3DXchange Pipeline, and it syncs characters only with iClone 7. <!-- CHT-065 -->

**The same base as today's.** CC3+ was introduced in version 3.3, and the free base download is that base. <!-- CHT-061 --> Reallusion says "CC5 HD characters are built on CC3+ base topologies with added subdivisions". <!-- CHT-061 --> CC3+ has 100 bones and 17,683 polygons across all elements; the Game Base has 72 bones. <!-- CHT-061 -->

**A face rig worth knowing.** Version 3.4 added ExpressionPlus: "63 custom blendshapes (52 Apple ARKit blendshapes and 11 tongues)", applied by default to CC3+ characters from then on. <!-- CHT-064 --> This checks the claim the DAZ Genesis register carries as DAZ-107, unchecked there. <!-- CHT-064 --> [Lip sync](/reference/lip-sync#mouth-shape-sets) compares the ARKit set with the other mouth-shape sets.

**Which terms apply is an open question.** The CC3-era Software EULA, dated 30 April 2019 and 1 January 2021, said "Publishing Reallusion content in games or interactive installations is authorized". <!-- CHT-062 --> It said you "may not do the following applications unless getting explicit permission from Reallusion": repurpose the base topology into other 3D formats, distribute or sell it, or build another character generation system from it. <!-- CHT-062 --> It had no AI clause, no Original Character Creation test and no modification clause. <!-- CHT-062 --> Whether today's terms reach a CC3 licence is open, below. <!-- CHT-006 --> One older rule has gone: the 2021 Content EULA kept Reallusion textures "only allowed to be used inside REALLUSION softwares", and that clause is absent from the current text. <!-- CHT-063 -->

## iClone 7

iClone 7 is legacy as well: the knowledge base files it under "iClone 7 (Legacy)", the store lists only iClone 8, and Reallusion keeps re-downloads for "the latest three versions". <!-- CHT-020 --> No statement on whether its activation still works was found. <!-- CHT-020 --> Its FBX export needed 3DXchange 7 Pipeline, and 3DXchange is discontinued. <!-- CHT-021 --> Its manual lists Windows 10, 8 and 7 SP1. <!-- CHT-025 -->

Before 27 July 2022, exporting Reallusion content needed an Export License and game use needed a free Mass Distribution Rights registration. <!-- CHT-023 --> The policy page's visible FAQ now says "All Standard Licenses, regardless of when they were purchased, are covered under the new Standard License policy." <!-- CHT-023 --> The older answers about Export Licenses and Mass Distribution Rights remain only in markup hidden from readers. <!-- CHT-023 --> The iClone 7-era EULA is the same 2019 and 2021 text, with the same conditional prohibition and no AI clause. <!-- CHT-022 -->

## Autodesk Character Generator

Character Generator is reached only through a Maya, Maya LT, 3ds Max, MotionBuilder, Mudbox or Media & Entertainment Collection subscription. <!-- CHT-030 --> Standalone subscriptions ended on 7 August 2021, and Maya LT stopped selling on 7 December 2022. <!-- CHT-030 --> An FAQ of 10 February 2022 announced a move to Autodesk Forge without migrating earlier assets, and that premium characters would no longer cost cloud credits. <!-- CHT-030 --> It is online, and Autodesk's status page lists it as "Operational". <!-- CHT-070 --> But a forum thread of 6 July 2025 reports "Characters no longer have a rigged skeleton, just locators", later replies report the same, and none is from Autodesk staff. <!-- CHT-070 --> Whether generation works today was not tested. <!-- CHT-070, CHT-038 -->

It downloads generic FBX, Maya `.mb`, 3ds Max FBX or Unity FBX, at four poly resolutions, with facial blend shapes, a facial bone rig for Maya, or neither. <!-- CHT-037 -->

**The licence is a gap.** No current terms page names Character Generator. <!-- CHT-031 --> The General Terms of 30 March 2026 assign no ownership of "Output", and reserve to Autodesk material "made available to You by Autodesk" and "any materials ... derived from" it. <!-- CHT-031 --> A 2013 service agreement says "Autodesk does not own Your Content", but no page says whether it still applies. <!-- CHT-032 --> On expiry, the General Terms tell you to "uninstall any and all copies of materials related to such Offering", without saying whether downloaded characters count. <!-- CHT-036 --> Education output carries its own limits. <!-- CHT-035 -->

**Only forum posts permit game use.** Neither the 2013 service terms nor the current General or Special Terms grants commercial or game use of the output. <!-- CHT-033 --> Three forum posts do. A 2014 post says "You can use the characters you generate commercially; whether it is for a game ...", and a 2016 post says use is unrestricted "as long as you do not redistribute the DNA data file"; neither author is shown to be Autodesk staff. <!-- CHT-033 --> A third poster, who signs as "not an Autodesk Employee", wrote in 2016 that a commercial user "can use any asset you created in any game you develop". <!-- CHT-033 -->

**AI.** The Acceptable Use Policy bars using an Offering to "replicate the functionality of any Offering, including through training of any machine learning or artificial intelligence algorithm or model". <!-- CHT-034 --> It does not name renders fed to image models. <!-- CHT-034 -->

## Poser 14

Poser 14 is Windows only, costs US$175.00, and exports OBJ, FBX, COLLADA and glTF. <!-- CHT-056 --> A Blender add-on that cleans up its FBX exports declares GPL-3.0-or-later in its manifest, with no licence file. <!-- CHT-057 -->

**Almost everything is Restricted Content.** Every Poser EULA read names as Unrestricted only "low res male, low res female, medium res male, medium res female" and their textures. <!-- CHT-050 --> The manual texts class the rest as Restricted Content or a Vendor Resource; the installer text makes everything else Restricted while still giving Vendor Resources extra rights. <!-- CHT-050 --> The game clause's wording also differs between the two, and "Program Export File Formats" is defined in neither. <!-- CHT-052 -->

**Two EULA texts, and no word on which governs.** The installer's EULA lists eight figures as Vendor Resources, Pauline, Pauline Casual, Paul, Paul Casual and four La Femme and L'Homme bases, that may be exported "for inclusion in game engines", but only as derivative works "for use in the Program", and adds a ban on anything that "competes directly with Company base figures". <!-- CHT-051 --> The manual page has neither addition, and neither text says which governs. <!-- CHT-051 --> La Femme 2 Pro and L'Homme 2 Pro say their textures, shaders and morphs are merchant resources, "While the base mesh is not". <!-- CHT-055 -->

**Renderosity content.** The Standard License allows "2D rendered images for games or backgrounds" and bars real-time games "where the Product files are distributed". <!-- CHT-054 --> The Extended License, where a product has one, allows a game build "provided there is encryption protection". <!-- CHT-054 --> Neither has an AI clause, and neither does any Poser EULA. <!-- CHT-053, CHT-054 -->

## ZBrush

ZBrush 2026.2.1 runs on Windows, macOS and iPadOS, with no Linux build listed. <!-- CHT-044 --> It exports OBJ, FBX, USD meshes and several print formats, but no glTF, and no page read says it exports a game skeleton. <!-- CHT-044 --> It costs US$399.00 a year, and a ZBrushCentral post of 30 July 2026 says the current Maxon App "is completely busted in Wine". <!-- CHT-045 -->

Maxon's EULA claims no licence to what you make and puts no commercial limit on a paid subscription. <!-- CHT-040 --> Education and trial licences may not be used commercially. <!-- CHT-040 --> Section 10.4 bars using the Software, its files or "data or other information obtained or generated from the Software" to train an AI system "that simulates or performs a function similar to any function incorporated in the Software". <!-- CHT-041 --> Bundled Capsules may ship inside your own work, provided their value is not "the primary value" and they cannot be extracted as stand-alone files. <!-- CHT-042 --> No licence covering other bundled Lightbox content, such as the Mannequins, was found. <!-- CHT-042 --> The free iPad plan is "intended for learning and exploration", and no page says whether it allows commercial use. <!-- CHT-043 -->

## Licences: read each one before you ship

Every row was read on 2026-09-23. Code, content and output are kept apart.

| Tool | Tool terms (code) | Content | 3D data in a build | Renders in a game | AI |
|---|---|---|---|---|---|
| Character Creator 5 | Software EULA, 2026-05-25; base topology and rigs stay Reallusion's <!-- CHT-002 --> | Content EULA, 2025-08-01, Standard licence <!-- CHT-003 --> | Allowed, but only in proprietary formats no public app can open; the embedded-content restriction is an open question <!-- CHT-004 --> | Yes <!-- CHT-003 --> | Barred for content and for base-derived characters; Enterprise only <!-- CHT-001, CHT-002, CHT-007 --> |
| Free CC base characters | Software EULA section 5 <!-- CHT-008 --> | The base itself; bundled skins and outfits are Content <!-- CHT-002 --> | Commercial use including games, under section 5's limits <!-- CHT-002, CHT-008 --> | Yes <!-- CHT-008 --> | Barred <!-- CHT-002 --> |
| Character Creator 3, iClone 7 | 2019 and 2021 EULAs; whether today's reach them is an open question <!-- CHT-006, CHT-022, CHT-062 --> | Old Export License folded into Standard <!-- CHT-023 --> | Open: the old texts allowed games, the current ones add conditions <!-- CHT-022, CHT-062, CHT-004 --> | Yes, under the current Standard licence <!-- CHT-003 --> | The current texts bar it <!-- CHT-001 --> |
| Autodesk Character Generator | Autodesk General Terms, 2026-03-30; no service terms found <!-- CHT-031 --> | Premade parts reserved to Autodesk; ownership of Output unassigned <!-- CHT-031 --> | Forum posts only <!-- CHT-033 --> | Forum posts only <!-- CHT-033 --> | Bars training to replicate an Offering <!-- CHT-034 --> |
| Poser 14 | Poser EULA, two differing texts <!-- CHT-051 --> | Restricted, apart from four legacy figures <!-- CHT-050 --> | Vendor Resource figures only, and the two texts differ <!-- CHT-051 --> | Renderosity Standard licence: yes <!-- CHT-054 --> | No clause <!-- CHT-053 --> |
| ZBrush | Maxon EULA, April 2026 <!-- CHT-040 --> | Capsules under conditions; other bundled meshes unclear <!-- CHT-042 --> | Your own sculpts, yes <!-- CHT-040 --> | Yes <!-- CHT-040 --> | Bars training a model that does what ZBrush does <!-- CHT-041 --> |

## What not to do

- **Never feed Reallusion content to an AI stage.** No render, mesh or texture from Character Creator, iClone or ActorCore goes into Qwen-Image, TRELLIS, Hunyuan3D or any other model. <!-- CHT-001, CHT-002, CHT-013 -->
- **Never ship a Reallusion model as a loose FBX, OBJ or glTF.** The Content EULA wants it in a format no public app can open. <!-- CHT-004 -->
- **Never commit third-party character content.** CLAUDE.md forbids licence-restricted content in the repo; keep downloads outside it, as `daz_library.py` does for Daz.
- **Never build a character creator on Reallusion content.** It needs an Enterprise licence. <!-- CHT-002, CHT-007 -->
- **Do not treat a forum answer as a licence.** Character Generator's only game permission is forum posts. <!-- CHT-033 -->
- **Do not let a Reallusion content plan lapse with work unexported.** <!-- CHT-005 -->

## What to build

1. **Import the free CC3+ base in the container.** The owner downloads the five bases with their own Reallusion account. A probe then imports the FBX in the container's `bpy`, lists the bones and shape keys, and renders a clay sheet. Nothing enters an AI stage. <!-- CHT-008, CHT-009 -->
2. **Map the ExpressionPlus shapes to the repo's mouth set**, once item 1 shows what names the free FBX actually carries. <!-- CHT-064 -->
3. **No guard for Reallusion content.** The owner decided on 2026-09-23 to build no AI guards unless something requires them. These licences bar the use itself and require no tooling, so the rule lives in the `character-source` skill.
4. **Ask Reallusion and Bondware in writing.** Reallusion: whether the embedded-content restriction covers a character in a game build, given that its FAQ says yes, and whether the 2026 terms reach a CC3 or iClone 7 licence. Bondware: which Poser 14 EULA text governs.

## Honest uncertainty

- **Whether today's Reallusion terms reach CC3 and iClone 7.** Both current EULAs say the newest text supersedes earlier ones. <!-- CHT-006 --> But the Software EULA's scope, products "currently provided or may be provided in the future", is absent from its October 2025 text and present in its January 2026 text, and neither EULA names discontinued versions, to include or to exclude them. <!-- CHT-006 --> Whether that binds someone who bought a perpetual licence in 2019 and never accepted the newer text is a legal question these texts do not answer.
- **The embedded-content restriction.** It sits against the Standard licence's game grant, as the DAZ Genesis note records. <!-- CHT-004 --> Reallusion's visible FAQ answers "Can I use my purchased content for game production and distributing my game title?" with "Yes", which favours the game grant, but the FAQ is not the binding text. <!-- CHT-071 -->
- **Whether the free CC base passes its own licence.** Reallusion's FAQ for the free base says "Your derivative characters are fully yours" and "the only restriction is redistributing the unmodified base files themselves". <!-- CHT-069 --> The binding Software EULA grants commercial use only to characters made "without using any content from Reallusion or its developers, including models", with four restrictions, and the policy FAQ bars the base from any character generation system. <!-- CHT-069, CHT-002 --> The FAQ is not the binding text, and the two disagree. <!-- CHT-069 -->
- **Which Poser 14 EULA text governs.** <!-- CHT-051 -->
- **What Autodesk permits for Character Generator output.** <!-- CHT-031, CHT-033 -->
- **Whether a Reallusion render may be a model's input.** The clause bars use "For machine learning, AI training, or AI-generated output". A render used as a reference image plausibly falls under it, but no Reallusion text names that case. <!-- CHT-001 -->

## Sources worth reading

- Reallusion: [Content EULA](https://www.reallusion.com/Content/EULA/EULA.htm), [Software EULA](https://www.reallusion.com/Content/EULA/AP/EULA_AP.htm), [Content License Policy](https://www.reallusion.com/license/content.html), [AI Service EULA](https://www.reallusion.com/Content/EULA/AI-Service.htm), [free CC base characters](https://www.reallusion.com/character-creator/free-3d-character-base.html) and [release history](https://www.reallusion.com/character-creator/cc-version-history.html). <!-- CHT-001, CHT-002, CHT-008, CHT-060 -->
- [CC/iC Blender Tools](https://github.com/soupday/cc_blender_tools). <!-- CHT-015 -->
- Autodesk: [General Terms](https://www.autodesk.com/company/terms-of-use/en/general-terms), [Acceptable Use Policy](https://www.autodesk.com/company/terms-of-use/en/acceptable-use) and the [Character Generator FAQ](https://www.autodesk.com/support/technical/article/caas/tsarticles/ts/1M8HMZJKuBRw9cnzLLza5l.html). <!-- CHT-030, CHT-031, CHT-034 -->
- Poser: [Poser 14 EULA](https://www.posersoftware.com/documentation/14/HTML/poser-end-user-license-agreement-eula.html), and Renderosity's [Standard](https://www.renderosity.com/standard-license) and [Extended](https://www.renderosity.com/extended-license) licences. <!-- CHT-051, CHT-054 -->
- Maxon: [EULA](https://www.maxon.net/en/legal/eula). <!-- CHT-040 -->
