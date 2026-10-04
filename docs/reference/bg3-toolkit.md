# Baldur's Gate 3 Toolkit

::: tip Status: researched on 2026-10-03, projection script built and run on a stand-in
What this pipeline's output would have to become to ship as a character mod through Larian's official Toolkit and in-game Mod Manager, and what the terms allow. Read: the game EULA, the BG3 Fan Content Terms, the older Modding Terms, Larian's forum guidelines, mod.io's terms and acceptable use policy, the official wiki page by page (as raw wikitext), LSLib's source and release archive, the Blender exporter's source, and Hunyuan3D 2.1's licence text. Run: `scripts/bg3_project.py` on a stand-in base made from this repo's own meshes, in the container's Blender on the CPU; LSLib's `Divine --help` under a user-local .NET 8 runtime on this host. Not run: the Toolkit, Divine against the game's files, any import into the Toolkit, any publish. The claims are in [research/claims/bg3-toolkit.json](https://github.com/Xander-Rudolph/game-asset-engine/blob/main/research/claims/bg3-toolkit.json) on GitHub.
:::

## The short answer

- **The generated mesh never enters the game.** BG3 animates characters on Larian's own skeletons, with Larian's topology, UVs and material layout, and the wiki's contract for a mesh is topological: clean loops, the naked body's topology under anything skin-tight, identical vertex order across race variants. <!-- BG3-016 BG3-018 --> A TRELLIS or Hunyuan3D mesh is triangle soup with its own atlas, so it serves as a **shape and colour source**: Larian's base mesh is deformed onto it in Blender, keeping its own vertices, weights and UVs, and the colour is baked across. `scripts/bg3_project.py` does that and writes the three maps BG3 materials expect. <!-- BG3-021 BG3-033 -->
- **Armour and body meshes enter the Toolkit as `.gr2`; only hair is shown importing from `.fbx`.** The GR2 is written by LSLib's Divine from a glTF or Collada file made with Norbyte's Blender exporter. <!-- BG3-014 BG3-015 BG3-027 BG3-028 -->
- **Everything runs on this Linux host.** The Toolkit is installed here through Steam (Proton), Divine starts under a user-local .NET 8 runtime, and the container's Blender does the projection and bakes. Larian's own pages say Windows only; Steam Play is the difference. Whether the Toolkit itself runs to the point of importing a model was not checked here. <!-- BG3-009 BG3-027 -->
- **A published mod is worldwide, so Hunyuan3D is out of it.** The publish step grants Larian and mod.io worldwide distribution, Larian lists PC, Mac, Xbox and PS5 for the game and the Mod Manager offers the author platform opt-ins but no region control, and Hunyuan3D 2.1's licence forbids displaying its Output outside a territory that excludes the EU, the UK and South Korea. The clean route is a Qwen-Image concept, a TRELLIS shape (MIT) and a colour from anything but the Hunyuan3D texture stage. <!-- BG3-002 BG3-006 BG3-011 BG3-012 BG3-013 -->
- **Mods are free, yours only where original, and Larian's where derived from the game.** No selling; donations and public commissions are the exceptions the Wizards policy allows. No document on the official route mentions AI-made assets. <!-- BG3-002 BG3-003 BG3-005 BG3-032 -->
- **Heads are undocumented.** The wiki covers armour, weapons, hair and beards; nothing on making or importing a head, its facial rig, morphs or neck seam. Ship a body first and keep Larian's heads, where the character creator's aging and skin options live. <!-- BG3-020 -->

## What the game wants

| Layer | What the wiki says | Source |
|---|---|---|
| Format | Armour and weapons: "it must be in the .gr2 file format ... and should already contain skinning"; hair: ".gr2 or .fbx format", and an .fbx opens the Visual Importer | Adding Armour, Creating Weapons, Hair and Beards: Assets <!-- BG3-014 BG3-015 --> |
| Geometry | No numbers anywhere: no units, scale, axis, budget, LOD count or UV rule. "Try to create as clean a topology as possible", "Minimise triangulated areas", no n-gons or spirals, the naked body's topology under skin-tight armour, and the same vertex order across race versions | Creating Armour <!-- BG3-016 --> |
| Skeleton | None named for the body, no bone list; rigs appear only by name, HUM_M retargeted to DWR_F and the like. Hair instead binds to named `Socket_Hair_*` joints of a provided hair skeleton and snaps across races with "Needs Skeleton Remap" | Creating Shortnames, Skinning and Snapping <!-- BG3-018 BG3-019 --> |
| Reference bodies | Larian's own downloads: `HUM_F_NKD_Mesh_Limits.fbx`, `HUM_M_NKD_Mesh_Limits.fbx` and `BG3_Armor_Limit_Guides.zip` for the other races, plus a helmet-hair and a weapon reference; whether they carry a skeleton is not known, none was opened | Creating Armour, Helmet Hair, Creating Weapons <!-- BG3-017 --> |
| Textures | `.tga` to author, `.dds` to import. BM (base colour, alpha for opacity), NM, PM packed R metalness, G roughness, B ambient occlusion, MSK or MSKcloth for dye regions, optional GM. BM, NM and PM go in together as one Virtual Texture | Creating Armour, Adding Armour <!-- BG3-021 --> |
| Materials | Made from a base-game MaterialResource with "Create New Material Only..." (no new shaders, or the mod cannot be curated for consoles), textures plugged in with the arrow button, assigned in Edit Visual; Slot ID, vertex-colour masking, tags and mask slots on the VisualResource | Adding Armour, Reusing Base Game Shaders <!-- BG3-022 --> |
| Bodies | `BodyType` Male or Female, `BodyShape` Standard or Strong, per race; the hair pages group gnomes, dwarves and halflings as the small races. Armour need not cover every race: fallbacks per race and gender, with elves, half-elves and tieflings inheriting the human entry | Character Creation, Hair and Beards: Assets, Adding Armour <!-- BG3-023 --> |
| Base assets | The wiki names no extraction tool; its route is the Resource Manager's "Override in the Active Mod...", which copies a resource's Source File, a `.gr2` for armour, into the mod | Overriding Resources <!-- BG3-024 --> |

Non-binary is a character-creation identity choice, not a third body: a halfling body mod is a female body and a male body (and Strong variants if wanted), each projected onto its own Larian base. <!-- BG3-023 -->

## The route, step by step

1. **Get the base mesh out.** Either in the Toolkit, "Override in the Active Mod..." on the body VisualResource, which puts its `.gr2` in your mod's Data folder, or with Divine straight from `Models.pak`: `dotnet Divine.dll -g bg3 -a list-package -s Models.pak`, then `extract-single-file` and `convert-model -i gr2 -o glb`. Divine needs .NET 8 (the host has 6; a user-local runtime from Microsoft's `dotnet-install.sh` into `~/.dotnet` was enough for it to start) and, for the game's compressed GR2 files, `granny2.dll` from the release zip through its native layer, which is a Windows library; whether that read works on Linux was not tested, because running the downloaded binary against the game's files was outside this session's permissions. <!-- BG3-024 BG3-026 BG3-027 --> Keep what comes out under `MODELS_DIR/bg3_library/`, outside the repository, as the Daz library is kept. <!-- BG3-034 -->
2. **Make the shape.** Concept with Qwen-Image, shape with TRELLIS, as [the pipeline](/guide/asset-workflow) does. Ask for the pose the base has, arms clear of the body and feet apart, or the wrap folds limbs onto the wrong surface. Keep Hunyuan3D out of anything that will be published. <!-- BG3-013 -->
3. **Project.** `scripts/bg3_project.py BASE.glb SOURCE.glb --out output/bg3/<name>` aligns the source to the base by height and footprint, deforms the base onto it with a Shrinkwrap masked by `--lock` groups (eyes, mouth, neck seam), smooths, bakes the source's colour onto the base's UVs as BM, bakes tangent normals as NM and ambient occlusion into PM's blue channel with flat metal and roughness, and writes the deformed base with its armature as glTF and FBX plus a JSON record with the share of texels no ray reached. The base's weights never changed, so nothing is transferred. <!-- BG3-033 -->
4. **Dress the maps.** Convert the three TGAs to DDS (nothing in the image writes DDS; the Toolkit converts BM, NM and PM into one Virtual Texture on import), add an MSK if the body is to be dyeable. <!-- BG3-021 -->
5. **Export GR2.** Open the glTF in Blender with Norbyte's exporter installed (GPL-3.0-or-later, Blender 3.6 and later, glTF in 4.5 and 5.0, Collada only to 4.5), export with its Y-up rotation and LOD and flag settings, and run Divine `convert-model -i glb -o gr2` yourself: the exporter's own GR2 button shells out to `divine.exe` in a way that does not start a program on Linux. <!-- BG3-027 BG3-028 -->
6. **Import and wire.** Source Asset Data Path, Add Resource, Model; Slot ID Body; material from a base-game one; Edit Visual; then the character-creation tables for the race. <!-- BG3-022 BG3-023 -->
7. **Publish.** Publish Local for a `.pak` to test; Publish to mod.io after accepting Larian's and mod.io's terms; wait for the automated scan; Go live. Console curation is opt-in and re-tested on every update. <!-- BG3-008 BG3-010 -->

## What was run

On 2026-10-03, on the reference machine, in the container's Blender 4.5.9 on the CPU, with no Larian file involved: `transfer_weights.py` put the alchemist warrior's 28-bone UniRig skeleton onto its textured 39,986-face mesh to make a stand-in base with UVs and weights; `bg3_project.py` then deformed that base onto the basilisk's textured mesh and baked its colour, normals and AO at 1024 px in 3.4 s, keeping all 28 groups and bones. The shapes were deliberately unalike, mean vertex move 0.159 of a 2.0 height, and the bakes showed it: large unreached regions in the normal map, so the script now reports the share of texels no ray reached and defaults to a longer ray. A matched pair, a halfling body onto a halfling shape, has not been run; it waits on a base mesh.

Also on 2026-10-03: three halfling shapes were made for this target through the pipeline, `output/mesh/halfling_nimble.glb`, `halfling_m.glb` and `halfling_f.glb`, 48,000 triangles each from TRELLIS, from Qwen-Image concepts approved by the owner.

## Licences

Read on 2026-10-03, by layer. Every clause is quoted in the register.

- **The game and the Toolkit.** The EULA forbids derivative works and modifying game files except as authorised, and sends fan work to the BG3 Fan Content Terms. <!-- BG3-001 --> Those terms (31 July 2025) license the Toolkit "solely for the purpose of creating Mods", take an irrevocable worldwide licence over anything you share, incorporate the Wizards Fan Content Policy, and route publishing through mod.io. <!-- BG3-002 --> The older Modding Terms (May 2024), still served, say a mod is yours only where original and Larian's where derived from the game, that every element must be your work or permitted, and that breach ends your licence to the game. <!-- BG3-003 --> Larian's general Fan Content Policy carries the one AI clause, "Do not prompt or train generative AI tools using Larian Studios IP", and says it does not apply to BG3. <!-- BG3-004 -->
- **Wizards of the Coast.** Fan content is free; sponsorship, advertising and donations are allowed; no Wizards IP in other games. <!-- BG3-005 -->
- **mod.io.** A perpetual worldwide licence to mod.io and Larian, UGC made public through the API, your warranty that you hold the rights, removal at Larian's discretion first. The terms' date is unsettled in the register: a browser render showed "Last updated: Sep 2, 2024", and the static document the page renders prints no date. <!-- BG3-006 BG3-007 -->
- **The AI models.** Hunyuan3D 2.1: "You must not use, reproduce, modify, distribute, or display the Tencent Hunyuan 3D 2.1 Works, Output or results of the Tencent Hunyuan 3D 2.1 Works outside the Territory." <!-- BG3-012 --> TRELLIS MIT and Qwen-Image Apache-2.0, as [licensing](/guide/licensing) records.
- **The tools.** LSLib code MIT; its release zip bundles `granny2.dll`, RAD Game Tools, all rights reserved, with no licence text, and PhysX 4.1.2, BSD-3-Clause. <!-- BG3-025 BG3-026 --> Norbyte's Blender exporter GPL-3.0-or-later by manifest and LICENSE, GPL-2.0-or-later by file headers, with Godot ancestry. <!-- BG3-028 --> The Modder's Multitool is "source available, not open source", redistribution and modification prohibited, and Windows. <!-- BG3-029 --> BG3ModManager MIT, Windows. <!-- BG3-030 --> Nexus Mods requires AI tags on the community route. <!-- BG3-031 -->
- **Larian content in this repo.** None, ever: meshes, textures and anything converted from GR2 stay outside the repository, nothing extracted or exported from the game is committed, and Larian content goes into no AI stage. <!-- BG3-034 -->

## What not to do

- Do not import a TRELLIS or Hunyuan3D mesh into the Toolkit as a body; project onto Larian's base instead. <!-- BG3-016 BG3-018 -->
- Do not publish anything that passed through Hunyuan3D, shape or texture. <!-- BG3-012 BG3-013 -->
- Do not sell or paywall the mod, or ship it with new shader files if consoles matter. <!-- BG3-003 BG3-005 BG3-022 -->
- Do not put a Larian mesh, a converted GR2 or a baked map of Larian's textures in the repository, the image or an AI stage. <!-- BG3-034 -->
- Do not redistribute LSLib's release zip; fetch it. <!-- BG3-026 -->
- Do not read the Blender exporter's GR2 button as working on Linux; call Divine yourself. <!-- BG3-028 -->

## What to build

1. Extract the halfling female and male Standard body `.gr2` files and convert them to glTF with Divine on this host, into `MODELS_DIR/bg3_library/`; if the compressed GR2 read fails natively, run Divine under Wine or the Toolkit's Proton prefix.
2. Run `bg3_project.py` on each with the matching halfling shape, locking the neck seam, and judge the unreached share and the result in Blender.
3. Add an `output/bg3/` guard to `cleanup.py keep`, as it has for `output/daz/`.
4. A DDS writer step, and an MSK map, for the Toolkit import.
5. Try the import through the Toolkit under Proton, then Publish Local, and record what happened.
6. A `--base` option on the pipeline's graph is not possible: the projection needs Blender, which no ComfyUI node in the image runs; the script is the stage.

## Honest uncertainty

- Whether the Toolkit under Proton imports a model and publishes is unverified here; Larian says Windows only. <!-- BG3-009 -->
- Whether Divine reads the game's compressed GR2 on Linux is untested; it needs `granny2.dll` through a Windows native library. <!-- BG3-026 BG3-027 -->
- Which Larian document the Toolkit's authentication wizard presents could not be read; the Fan Content Terms and the Modding Terms disagree on nothing substantive but differ in detail. <!-- BG3-002 BG3-003 -->
- No document answers whether projecting an AI shape onto Larian's mesh is "prompt ... generative AI tools using Larian Studios IP". <!-- BG3-032 -->
- The wiki calls itself unreviewed by Larian, and the 17 pages read here were all last edited by one user. <!-- BG3-014 -->
- The reference FBX downloads and Larian's body skeletons were not opened; bone names, units and axes are unknown. <!-- BG3-017 -->
- The matched projection, halfling onto halfling, has not been run.

## Sources worth reading

- [BG3 Fan Content Terms](https://baldursgate3.game/bg3-fan-content-terms/), [Modding Terms PDF](https://baldursgate3.game/mods/Larian_BG3_Modding_Terms.pdf), [Larian Fan Content Policy](https://larian.com/fan-content-policy), [Wizards Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy), [mod.io terms](https://mod.io/terms), [Modding: Guidelines & FAQ](https://forums.larian.com/ubbthreads.php?ubb=showflat&Number=948625)
- The wiki: [Adding Armour](https://docs.baldursgate3.game/Adding_Armour), [Creating Armour](https://docs.baldursgate3.game/index.php?title=Creating_Armour), [Hair and Beards: Assets](https://docs.baldursgate3.game/index.php?title=Hair_and_Beards:_Assets), [Skinning and Snapping](https://docs.baldursgate3.game/index.php?title=Hair_and_Beards:_Skinning_and_Snapping), [Publishing a Mod](https://docs.baldursgate3.game/Getting_Started:_Publishing_a_Mod), [Reusing Base Game Shaders](https://docs.baldursgate3.game/index.php?title=Reusing_Base_Game_Shaders)
- [LSLib](https://github.com/Norbyte/lslib) and its releases, [dos2de_collada_exporter](https://github.com/Norbyte/dos2de_collada_exporter), [Hunyuan3D 2.1 licence](https://huggingface.co/tencent/Hunyuan3D-2.1/raw/main/LICENSE)
