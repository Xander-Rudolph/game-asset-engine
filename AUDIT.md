# Documentation audit, 2026-09-10

Two audits ran against this repo.

**One over the game repo this pipeline was built for** — `/lordsofmagic`'s
`CLAUDE.md`, the art sections of `DESIGN.md`, the module docstrings of fourteen
`tool/` scripts, every workflow `_comment`, and the git history. Its findings
were cross-checked by a second pass that re-read the files before reporting, so
they carry evidence lines.

**One over 520 MB of Claude Code session transcripts** from four related
projects, distilled to the 144 paragraphs that state something learned the hard
way rather than something done. Much of that never reached any file.

97 lessons were found to be already covered here. What follows is what was not.

---

## Read this one first

**The face budget the documentation teaches is not the one the graphs use.**

Every image-to-mesh graph, and the rigging step, ships `target: 48000`:

| graph | target |
|---|---|
| `img2mesh_hunyuan3d21` | 48000 |
| `img2mesh_triposg` | 48000 |
| `img2mesh_triposr` | 48000 |
| `txt2mesh_qwen_hunyuan3d21` | 48000 |
| `txt2mesh_sdxl_hunyuan3d21` | 48000 |
| `mesh_rig_unirig` | 48000 (`target_face_count`) |

Ten places across seven documentation files say **18,000**, and three of them
build an argument on it that inverts once the real number is known:

- `docs/guide/meshes.md:55` — "18,000 is chosen to sit under the rigger's own
  budget, which is 48,000 &hellip; Staying under it means your geometry passes
  through untouched." They are **equal**. That is the boundary case, not the
  safe case.
- `skills/mesh-budget/SKILL.md:69` — "safely under the rigger's ceiling". It
  **is** the ceiling.
- `docs/guide/index.md:44` — offered as the flagship example under *the design
  rule behind every default*.

No document anywhere states 48,000 as a graph target. A reader plans a budget
chain that does not exist, and is told their mesh reaches the rigger untouched
when it arrives exactly at the ceiling.

**This needs a decision, not an edit.** Either the graphs come down to 18,000 to
match the reasoning the docs give — which changes what everyone's pipeline
produces — or the docs come up to 48,000 and the "sits under the rigger's
budget" argument is rewritten, because at 48,000 it is not true. Whichever way
it goes, the mesh target and the rig target are deliberately held equal so the
skeleton is solved against the decimation that actually happened, so **changing
one means changing the other**. That rule is currently written down nowhere.

Left alone deliberately: making this call is not an auditor's job.

---

## Findings from the game repo

### The docs say the face budget is 18,000; every shipped graph decimates to 48,000

**high** &middot; belongs in `docs/guide/meshes.md:47,55; docs/guide/decimation.md:128,147; docs/guide/rigging.md:92; docs/guide/index.md:44; docs/guide/textures.md:50; skills/mesh-budget/SKILL.md:69 — plus a new note stating the change-both-together rule`

VERIFIED, and worse than the auditor stated. All six mesh graphs carry "target": 48000 and mesh_rig_unirig.json carries "target_face_count": 48000 — and they have since the repo's first commit (c56cc37), so this is not drift, the prose was never true here. Nine "18,000" claims sit across six files, and three of them are arguments rather than numbers, so they are wrong twice over: meshes.md:55 "18,000 is chosen to sit under the rigger's own budget, which is 48,000... Staying under it means your geometry passes through untouched" (they are EQUAL, which is the boundary case, not the safe case); mesh-budget/SKILL.md:69 "safely under the rigger's ceiling"; index.md:44 makes it the flagship example of a measured default, in the section titled 'The design rule behind every default'. decimation.md:128 tabulates 18,000 as 'Every image to mesh graph, and the rigging step'. textures.md:50 and decimation.md:147 both compute downstream consequences from it. Confirmed by grep that NO doc anywhere states 48,000 as a graph target. Also missing is the rule the numbers imply: the mesh target and the rig target are deliberately held equal so the skeleton is solved against the mesh decimation actually produced, so changing either means changing both (--set target=NNNN plus the rigger's). A reader plans a budget chain that does not exist and is told their mesh passes through untouched when it is exactly at the ceiling.

*Evidence:* grep -o '"target"' workflows/api/*.json -> 48000 in all five image-to-mesh graphs; mesh_rig_unirig.json:36 target_face_count 48000; git log shows the value unchanged since the repo's first commit; nine '18,000' claims across six doc files; zero doc hits for '48,000 faces' as a graph target

### render_sheet.py fits every model to its own bounding box, and both facings.md and the script's own --help claim the opposite

**high** &middot; belongs in `docs/guide/facings.md ('Why the renders look consistent', beside 'Feet on the floor, not centre on the floor'); a --span/--fit flag in scripts/render_sheet.py and its --persp/--zoom help text; skills/pose-sheet/SKILL.md rules`

MERGES candidates 1, 24 and 71 — three auditors found the same defect. VERIFIED in code: render_sheet.py:114 `size = max((hi - lo)[i] for i in range(3))` is THIS mesh's own largest extent, and :133 `cam_data.ortho_scale = size * cfg["zoom"]`, then :121 anchors feet on the floor. A dagger and a golem therefore fill their cells identically. There is no --span/--fit/--world-span flag anywhere in the argparse block. The documentation states the inverse as a feature in two places: facings.md:166-168 'Orthographic by default. This is what makes two assets rendered on different days share a scale' — true of the projection, false of the framing, since the ortho scale is recomputed per model; and render_sheet.py:281 itself, where --persp's help reads 'default is orthographic, which is what keeps sprite scale consistent between assets'. So a reader who checks the tool's own help gets the same wrong answer twice. Both modes are legitimate and the docs should name which is which: a fixed world span for a set that must share scale (so a golem looms over a homunculus), per-model fit for inspecting a prop alone. The exception is worth stating too — a model baked alone as an inventory icon SHOULD be fitted to its own extent, or a flask at a fifth of a figure's height becomes a speck; a model held by a figure must keep the figure's span. Anyone baking a unit set gets every creature the same size on the map and hunts the bug in their engine.

*Evidence:* scripts/render_sheet.py:114 and :133 (per-model ortho scale); :281 --persp help claims cross-asset consistency; docs/guide/facings.md:166-168 states the same wrong claim; no scale/span flag in argparse (lines 260-290)

### TripoSG needs an RGBA cut-out, and the flagship walkthrough feeds it a grey-background render

**high** &middot; belongs in `docs/guide/first-asset.md step 2; docs/guide/meshes.md ('Which generator' table); docs/reference/workflows.md's TripoSG row; a _comment in workflows/api/img2mesh_triposg.json`

VERIFIED, and the contradiction is three-against-one. skills/asset-pipeline/SKILL.md:105 says TripoSG 'Needs a cut out image.' Every guide surface omits it: docs/guide/meshes.md's generator table gives TripoSG only 'Clean watertight shapes, fast. MIT upstream, but the copy in this pack ships a territory-limited licence file'; docs/reference/workflows.md:56 gives 'Clean watertight shapes. Licence caveat in the licensing guide'; and docs/guide/first-asset.md:33-37 — the repo's flagship walkthrough — pipes step 1's plain grey-background Qwen render (output/concept/golem_00001_.png) straight into img2mesh_triposg.json. Only TripoSR's row carries the warning, in both tables. Confirmed against the graph: img2mesh_triposg.json is LoadImage -> Load Diffusers Pipeline -> TripoSG I23D -> Decimate -> Save, with no background-removal node, and — unlike every other graph in the repo — no `_comment` key at all (json.load returns None for it), so the requirement is not recoverable from the file either. The contrast that makes it land is also missing: Hunyuan3D ShapeGen removes the background internally, which is stated in its own _comment, and that is exactly why the licence-driven swap the docs actively recommend (Hunyuan -> TripoSG for worldwide shipping) is precisely when this bites. Compounding it, no script in scripts/ removes a background — cut_icon.py is a flat-background flood-fill icon cutter, not documented for this — so even a reader who knows has no documented way to make the cut-out.

*Evidence:* img2mesh_triposg.json has no _comment and no rembg/background node; first-asset.md:33-37 feeds a plain render; meshes.md and workflows.md tables carry the caveat for TripoSR only; skills/asset-pipeline/SKILL.md:105 says the opposite of both tables

### Decimate Mesh's face target was silently ignored by an argument-order bug, and decimation.md blames boundary edges for every miss

**high** &middot; belongs in `docs/guide/decimation.md ('A budget below the floor is silently ignored' — add as a second cause with the direction that distinguishes them); docs/reference/scripts.md and docs/reference/docker.md (what patch_nodes.py actually fixes)`

VERIFIED. decimation.md:96-105 gives boundary edges as the SOLE cause of a face count that does not land ('The cause is boundary edges... If your face counts are not landing where you asked, this is why'), and mesh-budget/SKILL.md teaches the same one cause. The other cause is documented only inside scripts/patch_nodes.py:47-59: 3D-Pack's nodes.py calls decimate_mesh(verts, faces, target, remesh, optimalplacement) positionally into a signature of (verts, faces, target, backend, remesh, optimalplacement), so `remesh` lands in `backend` and `optimalplacement` lands in `remesh`; quadric decimation hits the target, then the mis-bound remesh triggers isotropic remeshing at targetlen 1% and puts the faces straight back. The comment records 'Asking for 18000 gave 48491'. This repo's own graphs are all exposed: every one of the five mesh graphs ships remesh:false + optimalplacement:true, which is exactly the pair that mis-binds. The two causes are distinguishable by direction — boundary edges leave you ABOVE target with the produced count stable across requests, the arg-order bug leaves you at roughly the rigger's ceiling — and the guide gives no way to tell them apart. A user on a freshly cloned (unpatched) node tree sees a budget that does nothing and is pointed at the wrong diagnosis by the guide's own warning box.

*Evidence:* scripts/patch_nodes.py:47-59 carries the full explanation; all five mesh graphs ship remesh:false + optimalplacement:true; decimation.md:96-105 gives boundary edges as the only cause; docs/reference/scripts.md:13 describes patch_nodes.py in one line

### Nothing normalises a mesh to a target world size, and an oversized export reads as a camera bug

**high** &middot; belongs in `docs/guide/meshes.md (a new 'Scale: every asset arrives at the same size' section), a scale step in scripts/, and a line in docs/guide/first-asset.md`

MERGES candidates 23 and 77. VERIFIED: no script in scripts/ scales a mesh to a target height, cleanup.py and asset_to_mesh.sh copy the mesh through untouched, and the only 'normalis' hits in the whole doc set are docs/guide/rigging.md:123, docs/reference/scripts.md:76 and skills/mesh-budget/SKILL.md:129 — all three about the RIGGER normalising its output into a unit box as a reason weight transfer needs alignment, never as an import rule for a mesh going into an engine. Image-to-3D output arrives at whatever size the generator chose, and a renderer that draws every figure against a fixed world span therefore renders it half again too big with its head off the top of the frame. The source note is blunt that this 'reads as a camera bug and is really a units mismatch'. What is needed: a stated house scale, a normalise-on-export step (or at minimum the Blender snippet), and the rule that every figure in a set arrives at the same height centred on the floor — which is also what makes a single hand-authored attachment hold point reusable. SCEPTICAL NOTE: the two auditors give different constants (1.98 units against a 1.15 target vs ~1.9 against a 1.30 world span), and render_sheet.py's unrelated `--zoom` default is also 1.15, so at least one auditor may have conflated the zoom multiplier with a world height. Write the rule; do not transcribe the numbers without re-measuring.

*Evidence:* No script scales a mesh; grep 'normalis' across docs/ and skills/ returns only rigging.md:123, scripts.md:76 and mesh-budget/SKILL.md:129, all about weight-transfer alignment; auditors' constants disagree (1.15 vs 1.30)

### Buildings are sized by footprint, not height, and must be framed by their ground patch

**high** &middot; belongs in `a new docs/guide/buildings.md or a 'Framing buildings' section in docs/guide/facings.md, cross-linked from docs/guide/meshes.md's scale section; a ground-patch fit mode in scripts/render_sheet.py`

MERGES candidates 2, 25 and 74. VERIFIED absent: grep for 'footprint' across docs/, skills/, scripts/ and README.md returns ZERO hits; the single 'ground patch' hit (ground-and-relief.md:210) is about terrain relief and unrelated to framing. The repo treats buildings as a first-class subject — preset_concept_building.json, a landscape 1472x1104 canvas in concept-art.md, a whole prompts/buildings/ folder — and then abandons the reader at the bake. Two connected rules are missing. (1) Sizing: a figure is sized by how tall it stands, a building by the tile it sits on, so footprint takes precedence over height for anything tile-bound; height-normalising a squat wide diorama let a village overhang its tile by a fifth in both directions and read as a plate dropped on the map. (2) Framing: fitted to its own extent, a building's on-screen footprint becomes a function of how tall it is — measured across twelve buildings, bases covered 0.91 to 1.06 of a tile with the base centre landing between 0.54 and 0.75 down a frame the map places by a single fixed anchor of 0.70. That spread is the gap under a village and the overhang on a barracks, and no per-building tuning fixes it because the error is in the framing. Frame by the ground patch and the base is the tile by construction. Two corollaries: pin the world origin (the middle of the footprint) to a fixed spot in the sprite rather than centring on the bounding box; and a structure's frame must be taller than it is wide (the tallest hold needed 0.67 of the frame above the base centre and 0.21 below), because a square frame slices the spire. Same root cause as the per-model auto-fit gap, different remedy — and this one spoils a whole set of buildings at once.

*Evidence:* Zero hits for 'footprint' anywhere in docs/, skills/, scripts/ or README.md; the one 'ground patch' hit is ground-and-relief.md:210 about relief; render_sheet.py:106-121 frames by bbox with feet on floor; preset_concept_building.json and prompts/buildings/ ship the building path

### Meshy Pro ownership is conditional, and the repo wires up the MCP server without saying so

**high** &middot; belongs in `docs/guide/licensing.md (a 'Hosted services' section alongside the model licences), cross-linked from the MCP block at docs/reference/skills.md:57-82`

MERGES candidates 3 and 73 (three auditors, and AUDIT.md's own entry agrees). VERIFIED: .mcp.json ships the Meshy MCP server, README.md:101 documents the key, and docs/reference/skills.md:57-82 discusses it for two paragraphs — covering only key handling and that exports are photogrammetry scale. docs/guide/licensing.md has eleven sections covering Hunyuan3D 2/2.1, StableFast3D, RMBG-1.4, SDXL/SD1.5, the animation sources, the tools' own licences and the container image, and has NO Meshy entry; CREDITS.md has none either. The terms are conditional in two ways that are easy to trip: Pro grants ownership with no attribution only while generations stay OUT of the Meshy Community gallery, and only while the INPUTS are clean — a screenshot, sprite rip or piece of box art fed in as a reference image voids the ownership Pro grants and walks an IP problem into the asset tree. That second condition is the live risk for exactly this repo's audience, because the care taken to use no assets from an original has to extend to what gets fed to the generator. Free-plan generations are CC BY 4.0, non-exclusive and oblige a credit line, so they must never be mixed into a set assumed to be Pro-owned; if a model's origin is uncertain, regenerate on the Pro account rather than guess. A hosted service is precisely where a reader stops thinking about licences because they paid for it, and given how carefully licensing.md handles Hunyuan's territory clause, the silence on the one hosted service the repo actively configures is the conspicuous hole.

*Evidence:* grep 'meshy' hits only docs/reference/skills.md:57-82 and README.md:101; docs/guide/licensing.md's eleven headings contain no Meshy entry; .mcp.json configures the server

### Hunyuan TexGen needs a C++ extension compiled from source, or texturing dies ~40s in with a bare NameError

**high** &middot; belongs in `docs/reference/docker.md ('Node packs', beside the pixi-environment explanation) and a new entry in docs/guide/troubleshooting.md`

VERIFIED absent from every doc. grep for 'mesh_inpaint', 'meshVerticeInpaint' and 'pybind' across docs/, skills/ and README.md returns nothing; the explanation exists only in scripts/postinstall.sh:52-65 and a check in scripts/publish_image.sh:58-59. The extension ships as source only; MeshRender.py's bare except swallows the ImportError, prints a warning, and leaves meshVerticeInpaint undefined, so a texture run fails partway through with `NameError: name 'meshVerticeInpaint' is not defined`. docs/reference/docker.md explains why postinstall.sh has to run inside the running container, but only for the rigging pack's pixi environment — it never says the Hunyuan extension is the other thing that must be built there, and for the same bind-mount reason. docs/guide/troubleshooting.md's sixteen entries include no NameError entry. Anyone on the `comfy` (source) profile who skips or interrupts postinstall gets a texture stage that fails cryptically after 40 seconds every time, with a message that names nothing searchable in the docs.

*Evidence:* grep -ri 'mesh_inpaint|meshVerticeInpaint|pybind' over docs/, skills/ and README.md returns nothing; scripts/postinstall.sh:52-65 carries the full rationale; troubleshooting.md has no NameError entry

### animation.md's 'Frames as models' cites pose_frames.py, which does not exist in the repo — and the section omits every rule that makes the pattern shippable

**high** &middot; belongs in `docs/guide/animation.md ('Frames as models, not as a sheet' and the rotation-convention danger block); a per-frame row in docs/guide/decimation.md's budget table; either ship scripts/pose_frames.py or qualify the reference as rigging.md:178 does`

MERGES candidates 89, 29, 30 and 46. VERIFIED HARD: docs/guide/animation.md:79 says '`pose_frames.py`, the tool that bakes frames out as models, applies them in world space' with no qualifier, and `ls scripts/` shows no such file. The whole 'Two tools, two rotation conventions' danger block — the page's most emphatic warning, flagged 'read it twice' — is therefore about a tool the reader cannot run, which also makes candidate 46's implementation notes (parents-first by depth, rotate about the bone's own head) moot until the tool ships. Note rigging.md:178 handles the same situation honestly, naming `tool/make_cycles.py in the game repo`; animation.md does not. Four rules are also missing from 'Frames as models, not as a sheet' (animation.md:144-155), which currently covers only posed-models-vs-sheets and texture sharing: (1) a posed cycle frame is normalised on HEIGHT ONLY, never re-centred, because centring each frame cancels the rise and fall the stride is made of — and with no normalisation at all the figure swells mid-stride; (2) the pose must be baked into geometry through the evaluated depsgraph before export, because an OBJ carries no skeleton; (3) cycle frames want roughly a third of the resting figure's budget (4,000 against 12,000) because a frame is seen at ~34px and a set is units x frames — at 12k each, 4 units x 11 frames is ~60MB of web build for detail nobody can see, and decimation.md's budget table (lines 125-130) has no per-frame row; (4) a build carrying no such frame must fall back to the RESTING figure, which is what lets a half-finished animation set ship — a missing frame degrades to a translate and a colour flash rather than a hole in the line. poses/ already carries files in exactly the naming shape that lookup needs (unit_warrior_attack.json).

*Evidence:* docs/guide/animation.md:79 references pose_frames.py; ls scripts/ has no such file; decimation.md:125-130 budget table has no animation row; animation.md:144-155 names no face count, no normalisation rule and no fallback

### A preview or screenshot harness must run the app's real startup, or it produces a confident, plausible, wrong picture

**high** &middot; belongs in `a new docs/guide/verifying.md, or a 'Look at it' section in docs/guide/first-asset.md, plus the Rules block of skills/asset-pipeline/SKILL.md`

MERGES candidates 4 and 87. VERIFIED absent: grep for 'harness' across docs/, skills/ and README.md returns ZERO hits, and 'screenshot' returns one incidental mention at ground-and-relief.md:336. The repo's entire verification story is 'render it and look at it' — meshes.md:114, facings.md:116, textures.md's 'Judging a texture', pose-sheet/SKILL.md, ground-texture/SKILL.md — which is right, and this is the one failure mode that defeats looking. A harness that builds a screen directly and skips the awaited startup that fills the asset caches renders nothing procedural and reads NO ground material, so a world map draws as flat grey diamonds with no terrain, a table draws no figure, and a paper doll draws a blocky primitive. Twenty-three shipped guide screenshots had that fault; each looked perfectly plausible on its own and it only showed against the running game. Three separate harnesses had the identical hole. The rule — a preview entrypoint must start the way the real entrypoint starts, and every harness shot must be compared against the running app before it is believed — is the most transferable verification lesson in the whole candidate set, and it is directly relevant here because render_sheet.py IS such a harness and the repo's closing instruction on nearly every page is 'look at it'.

*Evidence:* Zero hits for 'harness' anywhere in docs/, skills/ or README.md; one incidental 'screenshot' at ground-and-relief.md:336; 'look at it' is the closing instruction of meshes.md, facings.md, textures.md and two skills

### Multi-subject contact sheets: welded with no groups, the plane must be measured, and the order is not the reference image's

**medium** &middot; belongs in `docs/guide/meshes.md (a new 'Sheets of several subjects' section) or a new docs/guide/importing-scans.md; a scripts/split_sheet.py entry in docs/reference/scripts.md; a pointer from the Meshy block at docs/reference/skills.md:80`

MERGES candidates 7, 26, 27, 75, 92 and 79 — four auditors converged here. VERIFIED absent: grep for 'contact sheet', 'connected component', 'split_sheet', 'atlas' and 'min-faces' across docs/, skills/ and scripts/ returns nothing, and scripts/ has no sheet-splitting tool. docs/reference/skills.md:80-82 warns that Meshy exports are photogrammetry scale and points at decimation, but says nothing about sheets — which is how a hosted service returns a SET. The traps, in the order they bite: a sheet arrives as ONE welded object (a dozen subjects, ~3M faces, not a single o/g group), so connected components are the only knife, and it works because the bodies never touch; which plane the sheet lies in must be MEASURED, not assumed — one sheet stands up in XY and the next lies flat in XZ, and picking wrong silently MISLABELS every subject (the axis whose centroids barely spread is the normal; the row axis is the one falling into the fewest clean bands); rows are found by CLUSTERING, never a fixed grid, because sheets are unevenly filled (one ran 4, 3, then 5) and a fixed grid mislabels everything after the first short row; pre-decimate the whole sheet BEFORE splitting, because collapsing 3M faces is far slower than collapsing the budget you want and 'the collapse never welds two bodies that were never touching'; a 220-face scan shard counts as a subject and shifts every later name, hence a min-faces floor and a warn-not-proceed on a component/name count mismatch; and even with the plane right, the 3D order need NOT match the reference PNG, so emit positional names, render, and read the mapping off by eye, per sheet. Two consumption-side companions: save split subjects with textures OFF, because every subject indexes the same shared atlas and writing it per subject produces eight copies of a 5MB PNG (so any previewer needs a prefix-to-atlas table); and name each single for the key the ENGINE looks up, not for what it depicts, or it renders a silent fallback. Finally, a reference sheet drawing twelve subjects does not guarantee twelve bodies in the export — one can come back fused or absent, so a count mismatch is the first thing a user hits and it looks like a tool bug.

*Evidence:* grep 'contact sheet|connected component|split_sheet|atlas|min-faces' across docs/, skills/ and scripts/ returns nothing; no sheet-splitting tool in scripts/; docs/reference/skills.md:80-82 covers export size only

### make_seamless.py warns that a texture is too flat and offers no remedy, and the remedy the docs imply cannot succeed

**medium** &middot; belongs in `docs/guide/terrain.md ('Size and contrast', and beside 'The ratio lies about smooth textures'); docs/guide/ground-and-relief.md ('Measure the texture'); an amplify (and optionally a --procedural) mode in scripts/make_seamless.py`

VERIFIED. scripts/make_seamless.py:205-207 prints '! very flat — a texture this even reads as a painted rectangle at map scale' when g.std() < 8, and terrain.md:56-70 documents the measurement and the warning. Neither the tool nor any doc offers a fix, so the reader gets a warning and a dead end — and the fix the page implies (re-pick the texture, terrain.md:61-70) is advice that cannot work for the cases that trigger it: the best sand on ambientCG measures ~3.5 and clean snow ~2.0, so a punchier source does not exist. The variation is real, just compressed into a dozen grey levels. What is missing is that the fix is to amplify the LOCAL variation up to std ~13-15 while leaving the average colour alone — an operation on the image, not a different image. grep for 'amplif' and 'local variation' across docs/, skills/ and scripts/ returns zero hits. Related and equally absent: for a surface that is genuinely uniform and near-featureless, a procedural tile beats a diffused one and sidesteps make_seamless.py entirely — band-limited noise summed in the frequency domain on a periodic grid wraps EXACTLY by construction, no seam repair needed. That is worth naming because prompts/ground/water.txt ships and terrain.md:146-154 uses a water texture as its case study for the ratio lying, which implies water came out of the generator; open water has no photographic albedo (it is a shader effect), so the honest answer is that it did not.

*Evidence:* scripts/make_seamless.py:205-207 warns at g.std() < 8 with no fix; zero hits for 'amplif', 'local variation', 'band-limit', 'frequency domain' or 'procedur' anywhere in docs/, skills/ or scripts/; prompts/ground/water.txt exists

### The two-pass realism route is documented nowhere in the guide — and AUDIT.md records it as fixed when it is not

**medium** &middot; belongs in `docs/guide/concept-art.md (a section after 'Simplifying art you already have'), the denoise band in docs/reference/workflows.md's img_refine_sdxl row, and skills/concept-edit/SKILL.md`

MERGES candidates 18 and 56, with a correction worth flagging. VERIFIED: grep for 'refine' and 'realism' across docs/guide/ returns ZERO hits. prompts/realism_pass.txt ships a fully-formed corrective second pass and no doc, skill or script mentions it. img_refine_sdxl.json appears exactly once in the whole doc set, as one row in docs/reference/workflows.md:51 reading 'Refine pass over an image'. Everything that makes it usable lives only in the graph's own _comment: it is a low-denoise img2img whose only job is re-rendering surfaces more realistically WITHOUT changing the design, run AFTER img_edit_qwen has simplified (one job per pass beats one prompt doing both); denoise is the whole control, 0.25-0.35 adds material detail and keeps the design, above ~0.5 SDXL starts reinventing shapes; and the CivitAI realism checkpoints present on the machine are deliberately NOT used because their licensing is unclear and this pipeline ships game assets — exactly the thing a user will otherwise 'improve' by swapping in a downloaded checkpoint. This is the other half of a pattern concept-art.md tells only half of: hero concepts arrive too noisy, the simplify pass fixes that, and the simplify pass then flattens them toward plastic — which is why both simplify prompts spend their last paragraph insisting the result must not become flat vector art, a cartoon, a clay render or 'untextured grey or brown plastic'. IMPORTANT: the repo's own AUDIT.md marks this entry 'fixed 2026-09-10'. It is not fixed — concept-art.md's headings run straight from 'Simplifying art you already have' to 'Denoise behaves like a cliff' to 'Naming outputs' with no refine section. Do not trust that fixed marker.

*Evidence:* grep 'refine|realism' across docs/guide/ returns zero hits; prompts/realism_pass.txt exists unreferenced; workflows/api/img_refine_sdxl.json:2 _comment carries the whole rationale; AUDIT.md line 14 marks this 'fixed 2026-09-10' incorrectly

### The two host-side scripts tell you to run a pip command that modern Debian/Ubuntu/Kali refuses

**medium** &middot; belongs in `docs/guide/install.md (a 'Host-side tools' section), the error strings in scripts/make_seamless.py:39 and scripts/cut_icon.py:31, and a host-import check in scripts/doctor.py`

VERIFIED, and it is a first-run wall on this very box. make_seamless.py:39 and cut_icon.py:31 both exit with 'needs Pillow: pip install --user Pillow'. Both run on the HOST, not in the container, and both need numpy and Pillow. On a current Debian/Ubuntu/Kali box that command fails outright with externally-managed-environment (PEP 668) — so the tool's own remediation message is the thing that does not work, which is exactly the confusing early failure doctor.py exists to prevent. Confirmed that doctor.py has no host-import check at all: its imports are stdlib only (argparse, json, os, shutil, subprocess, sys, time, urllib, pathlib) and its checks cover the container, the server and bpy-in-the-container. docs/guide/install.md's seven sections cover the prebuilt image, weights, building from source, user ids and publishing, with no 'host-side tools' section; the only mention of the dependency anywhere is skills/ground-texture/SKILL.md:17 in passing, with no way to satisfy it. The working recipe is a venv (python3 -m venv ~/.venvs/asset; ~/.venvs/asset/bin/pip install numpy Pillow) and running the host scripts with that interpreter.

*Evidence:* scripts/make_seamless.py:39 and scripts/cut_icon.py:31 both print 'pip install --user Pillow', blocked under PEP 668; doctor.py imports stdlib only and checks no host packages; install.md has no host-tools section; only mention is skills/ground-texture/SKILL.md:17

### auto_cleanup=False is deliberate — with it true, only the FIRST Hunyuan run succeeds

**medium** &middot; belongs in `docs/guide/textures.md and docs/guide/meshes.md (the memory/staging sections), plus docs/guide/troubleshooting.md's 'Out of memory during mesh generation'`

VERIFIED. grep for 'auto_cleanup' across docs/ and skills/ returns nothing; the explanation lives only in the three graphs' own _comment fields (img2mesh_hunyuan3d21.json:2, txt2mesh_qwen_hunyuan3d21.json, txt2mesh_sdxl_hunyuan3d21.json) and a passing line in scripts/asset_to_mesh.sh:8. With auto_cleanup true the ShapeGen node frees the pipeline after the run, but ComfyUI caches the loader node's output, so every later run operates on the gutted cached object and dies with "'Hunyuan3DDiTFlowMatchingPipeline' object has no attribute 'scheduler'". Keeping the pipeline resident costs VRAM, and the accepted trade is to let ComfyUI evict it. This matters because it is the direct cause of the staged batching that three separate guide pages describe at length — meshes.md's 'Memory, and why batches are staged', textures.md's 'Memory, and why texture runs are batched separately', and troubleshooting.md's OOM entry — and none of them connects it. A reader troubleshooting memory opens the graph, sees a cleanup switch turned off, and has no doc telling them why turning it on makes things categorically worse rather than merely slower.

*Evidence:* Zero 'auto_cleanup' hits in docs/ or skills/; workflows/api/img2mesh_hunyuan3d21.json:2 _comment carries it; three guide sections discuss the resident-pipeline OOM without naming the cause

### Naming a forbidden thing in the positive prompt summons it

**medium** &middot; belongs in `docs/guide/concept-art.md ('What a good prompt for this pipeline says', as a fifth rule), and a line in skills/asset-pipeline/SKILL.md's stage 1 rules`

VERIFIED. docs/guide/concept-art.md:68-107 gets close and stops short. It lists four things every subject prompt states, prints the house negative in full, and adds 'The ragged and cluttered words are there for a reason. Generators love to add torn hems and hanging trinkets' — but never states the counter-intuitive rule that produced that split: writing 'no ragged tatters, no tears, no frayed edges' in the POSITIVE prompt produced a more tattered coat every time. The working structure is the actionable half and is missing entirely: the positive describes what the thing should BE ('a smooth even curved hem, pristine, freshly tailored'), and the negative file carries everything it must not be. Without it, the natural reading of the page is that the negative list is optional decoration, and a user writing their own subject prompt does the thing that reliably backfires. It matters more here than in a generic prompting guide for a specific structural reason: the same page (concept-art.md:15-27) tells readers the fast graph ignores negative prompts entirely, which actively invites moving prohibitions into the positive. AUDIT.md line 252 independently records this as missing.

*Evidence:* concept-art.md:68-107 lists four rules and prints the negative with its rationale, never the positive-prompt inversion; concept-art.md:15-27 tells readers the fast graph ignores negatives; prompts/lords/_negative.txt is the shipped example; AUDIT.md:252 agrees

### What patch_nodes.py actually fixes, why it targets the host clone, and that a git pull silently un-fixes it

**medium** &middot; belongs in `docs/reference/docker.md ('Node packs' — what the patches fix and why they live on the host) and an expanded entry in docs/reference/scripts.md; the trust_remote_code error string in docs/guide/troubleshooting.md`

MERGES candidates 57 and 62. VERIFIED: docs/reference/scripts.md:13 is the entire coverage — 'Compatibility patches to the cloned node sources. --check verifies them.' The reasoning is fully written in scripts/patch_nodes.py:1-27 and never reaches a doc: custom_nodes/ is a bind mount, so the HOST copy is the one ComfyUI actually imports under the comfy profile and anything the image did to its own copy is hidden — which is the same bind-mount-replaces-a-path rule the docs teach well elsewhere, applied to a case they never connect. Also missing: the patches are idempotent and setup.sh re-runs them after every clone or pull, so a `git pull` in custom_nodes silently un-fixes the whole stack until you re-run it; `--check` exits 1 on anything unapplied; and COMFY_CUSTOM_NODES overrides the location, which is how the baked image applies the same patches at /app/custom_nodes. One of the four patches is trust_remote_code=True for Hunyuan TexGen's paint pipeline (patch_nodes.py:60-69): TexGen loads its pipeline from custom code inside the node tree, and current diffusers refuses to execute that without an explicit opt-in, raising `ValueError: ... contains custom code in pipeline.py which must be executed`. The code is the node pack's own and already on disk, so the opt-in is the intended path rather than a risk to weigh — worth saying, because a reader who hits that error and hesitates at the words 'trust remote code' has nothing in the docs telling them it is expected here.

*Evidence:* docs/reference/scripts.md:13 is one line; scripts/patch_nodes.py:1-27 carries the bind-mount and idempotence rationale; :60-69 carries the trust_remote_code patch and its ValueError; zero 'trust_remote_code' hits in docs/ or skills/

### Do not add --lowvram, and the docs' most-discussed failure is the one that provokes it

**medium** &middot; belongs in `docs/reference/docker.md (Profiles, or a short 'Why there is no VRAM flag' note), cross-linked from docs/guide/troubleshooting.md's OOM entry`

VERIFIED. grep -ri 'lowvram' over docs/, skills/ and README.md returns ZERO hits; the rationale exists only as a comment at docker-compose.yml:51-54. Three separate pages walk a reader through GPU OOM at length — meshes.md's 'Memory, and why batches are staged', textures.md's 'Memory, and why texture runs are batched separately', and troubleshooting.md's 'Out of memory during mesh generation' — without ever saying not to reach for the obvious flag. 3D-Pack keeps several pipelines resident and lowvram thrashes them, and current ComfyUI no longer accepts an explicit --normalvram, so the correct state is no VRAM flag at all. A reader hitting the documented OOM will edit the compose `command:` line, make throughput far worse, and have no way to know that the ABSENCE of a flag was a deliberate decision rather than an oversight — which is exactly the kind of thing a config file cannot tell you.

*Evidence:* docker-compose.yml:51-54 carries the rationale; zero occurrences of 'lowvram' anywhere in docs/, skills/ or README.md; three guide sections document the OOM that provokes it

### Leave COMFY_ENV_ISOLATE on — turning it off is the tempting fix for a documented annoyance and breaks UniRig with an Embree symbol error

**medium** &middot; belongs in `docs/reference/docker.md (Node packs / Environment table) and a line in docs/guide/troubleshooting.md's value_not_in_list entry`

VERIFIED. grep for COMFY_ENV_ISOLATE, Embree and rtcGet across docs/ and skills/ returns nothing; the rationale is a comment at docker-compose.yml:20-25. docs/guide/rigging.md's 'Two batch scripting traps' and docs/guide/troubleshooting.md's 'A new mesh is rejected with value_not_in_list' both explain the snapshotted file list and the copy-over-a-known-slot workaround well. Neither mentions the environment variable that appears to cure it: setting COMFY_ENV_ISOLATE=0 makes UniRigLoadMesh re-scan input/3d per request — solving exactly the problem those two pages describe — but then UniRig imports into the main environment, picks up its bpy 4.5.9, and dies with `undefined symbol: rtcGetSceneTraversable`. The pixi env ships a bpy built to match. A reader who finds the variable while working around a documented annoyance trades a known workaround for an ABI error with no search term attached to it in any doc.

*Evidence:* docker-compose.yml:20-25 carries it; zero hits for COMFY_ENV_ISOLATE, Embree or rtcGet across docs/ and skills/; rigging.md:180-190 and troubleshooting.md:99 describe the problem it appears to solve

### UniRig's isolated pixi env resolves comfy-kitchen to latest and then registers ZERO nodes, silently

**medium** &middot; belongs in `docs/reference/docker.md (name the package in 'The chain', add the isolated-env case under 'Node packs') and a symptom entry in docs/guide/troubleshooting.md`

VERIFIED. docs/reference/docker.md:26-38 covers the torch-2.6-vs-PEP-585 wall for the MAIN environment well and explains the ComfyUI v0.30.2 pin, but never names the package — grep for 'comfy-kitchen' across docs/ returns nothing — and does not mention that the isolated pixi environment hits the same wall independently and fails DIFFERENTLY. There, the env correctly inherits torch 2.6 but resolves comfy-kitchen to latest, which needs torch >= 2.7; the two disagree, UniRig logs the ValueError and carries on, and the pack contributes no nodes at all with no visible error. scripts/postinstall.sh:38-47 pins comfy-kitchen==0.2.26 inside the isolated env and verifies the import. Someone whose rigging nodes simply are not there gets no clue from troubleshooting.md's 'A node pack did not load', because the startup log shows a caught-and-continued ValueError rather than a traceback. NOTE: the repo's own AUDIT.md (line 22, still open) records a worse form of this — postinstall.sh is hard-wired to the source profile and nothing applies the pin on the packaged profile at all, which is the path README.md calls the whole install. Document the symptom and the version together.

*Evidence:* scripts/postinstall.sh:38-47 pins 0.2.26; docker.md:26-38 describes the wall without naming comfy-kitchen or the isolated env's variant; AUDIT.md:22 records the packaged-profile hole as still open

### Mount UniRig's whole HOME, not just .ce — --force-recreate wipes the pixi binary

**medium** &middot; belongs in `docs/reference/docker.md (a volumes section alongside Environment)`

VERIFIED. docs/reference/docker.md's Environment table lists MODELS_DIR, PUID/PGID, COMFY_URL, HF_TOKEN and ATHANOR_FETCH_MODELS and has no volume guidance at all; grep for 'pixi', '.ce' and '.home' across docs/ and skills/ returns nothing. comfy-env spreads itself across $HOME/.ce (the pixi ENVIRONMENT, ~10GB) and $HOME/.pixi (the pixi BINARY that runs it), which is recorded only at docker-compose.yml:31-39. Mounting only .ce survives a restart but not a `docker compose up --force-recreate`, which wipes .pixi and fails with `FileNotFoundError: /app/.home/.pixi/bin/pixi`. It must also stay OUTSIDE custom_nodes/, where ComfyUI would try to import it. This matters because docs/guide/install.md tells readers to run `docker compose --profile comfy up -d` and describes setup.sh as safe to re-run, so reaching for --force-recreate is a normal troubleshooting move; the failure then presents as a broken rigging pack and costs an 11GB rebuild.

*Evidence:* docker-compose.yml:31-39 carries the comment; zero occurrences of 'pixi', '.ce' or '.home' in docs/ or skills/; docker.md's Environment table has no volume rows

### The 1024px recommendation is stated in three places and was measured and abandoned

**medium** &middot; belongs in `docs/guide/terrain.md:58,87 ('Size and contrast', 'Scale is set by how big things should look'); docs/guide/ground-and-relief.md:105; skills/ground-texture/SKILL.md:21 and its example commands`

VERIFIED as a three-way repetition, and corroborated by the repo's own audit. terrain.md:58 ('Generate at 1024 pixels, not 512'), terrain.md:87 ('1024 pixels rather than 512, and let the size of things in the picture choose the repeat'), ground-and-relief.md:105-106 ('Pay for the texel density with resolution instead — the materials are 1024px, not 512') and skills/ground-texture/SKILL.md:21 (a whole section headed '1. Generate at 1024, not 512') all prescribe it, and terrain.md:16 and SKILL.md:56 both put --size 1024 in the copy-paste commands. The source project reverted that decision: a 1024px texture squeezed into 192 device pixels is a five-to-one minification, which is what made everything soft; resolution buys sharpness only up to roughly one texel per screen pixel and nothing beyond. The set went back to 512px at 4 tiles per repeat (256 device pixels against 512 texels) and the materials then weighed about a quarter of what they had (~625KB down to ~195KB each). The repeat-count half of the lesson is documented well; the resolution half currently teaches a number that was measured and abandoned, and it quadruples the bytes shipped in a web bundle for no visible gain. AUDIT.md line 236 records the same finding independently ('the measured settle was 512px at four tiles per repeat'), which is the strongest corroboration available inside this repo — but re-measure before rewriting four places.

*Evidence:* terrain.md:58,87, ground-and-relief.md:105-106 and skills/ground-texture/SKILL.md:21 all prescribe 1024 over 512; AUDIT.md:236 records the measured settle as 512px at four tiles per repeat

### For a flat-shaded or 2D renderer, ship the albedo only — the other maps have nothing to light

**medium** &middot; belongs in `docs/guide/textures.md ('What comes out' — a 'Which maps you actually need' note); docs/guide/terrain.md (what to ship); docs/guide/meshes.md#file-formats`

MERGES candidates 5 and 80. VERIFIED: textures.md:33-36 says 'You get a textured .glb and a set of maps. The maps are colour, metal and roughness', meshes.md's OBJ tip lists golem_albedo.png, golem_metallic.png and golem_roughness.png and says 'Keep those files together', and cleanup.py's `keep --textures` preserves all of them — unconditionally, with no note that a target might want fewer. Nothing anywhere says that a renderer drawing flat 2D diamonds or flat-shaded meshes has no surface for a normal, roughness or AO map to modulate, so the Color map alone is enough, and the smallest resolution that still reads at map zoom is the right choice because every byte ships in the web bundle and in all three APKs (nine terrains at 512px totalled 536KB shipping colour only). Downloaded PBR material sets hand over four maps when one is wanted. The companion fact is also absent: a flat-shaded path wants geometry plus ONE colour per material (positions quantised to millimetres as int16, one Kd per material out of the MTL) with no UVs and no texture sampling at all — a materially different export from the textured .glb this pipeline treats as the finished article. This matters because docs/guide/index.md's audience section explicitly includes 2D and isometric targets.

*Evidence:* textures.md:33-36 and meshes.md's OBJ tip preserve all three maps unconditionally; zero occurrences of 'normal map', 'roughness map' or 'AO' in terrain.md; cleanup.py keeps textures wholesale

### A generated texture carries its own baked light, and the flat-material shading curve crushes it to mud

**medium** &middot; belongs in `docs/guide/textures.md (beside 'Flat lighting baked into the colour'); docs/guide/facings.md ('Why the renders look consistent'); docs/reference/scripts.md's render_sheet.py block`

MERGES candidates 6, 43 and 90. VERIFIED: textures.md:101-103 names the problem from the prompt side ONLY — 'Flat lighting baked into the colour. If your engine lights the model itself, painted shadows fight the engine's lighting. Ask for even lighting in the concept prompt.' The renderer-side half is missing everywhere: a shading curve that suits multiplying a bright flat material colour (0.25..1.35) destroys a photographic or generated texture that already carries light and albedo, so a textured path must COMPRESS its range toward 1.0 — keeping the directional cue and letting the texture carry the rest (lit = 1.0 + (light - 1.0) * 0.45). It is also why a preview tool should be lit more gently than the game. Practically this is the guidance behind render_sheet.py's --key and --ambient, which docs/reference/scripts.md:48-52 lists as bare flags with no advice on when to move them, and which default to a fixed --key 1.6 with no textured/untextured distinction. Worth pairing with the general principle that a preview tool is only trustworthy when it lifts the camera, the fit, the lighting and the sprite size DIRECTLY out of the game's renderer rather than approximating them — approximations drift, and one preview bench kept its own copy of the model-to-atlas mapping and fell two prefixes behind, costing a failed fetch per building. Without this, someone who follows the pipeline to a textured mesh and drops it into a shaded renderer gets mud and blames the texture stage.

*Evidence:* textures.md:101-103 gives only the prompt-side fix; docs/reference/scripts.md:48-52 lists --key/--ambient with no guidance; render_sheet.py:277-285 defaults --key 1.6 with no textured distinction; zero hits for 'baked light', 'lighting curve' or 'compress' in docs/guide

### The asset filename IS the convention, and a near miss fails in silence

**medium** &middot; belongs in `docs/guide/terrain.md (naming), a new docs/guide/integrating.md referenced from docs/guide/cleanup.md and docs/guide/first-asset.md, and skills/asset-cleanup/SKILL.md rules`

MERGES candidates 8 and 78. VERIFIED: terrain.md:15-17 and skills/ground-texture/SKILL.md:56,120 tell you to write output/materials/plains.jpg and forest.jpg, and concept-art.md:137 covers naming outputs after the source file — but nothing covers the handoff into a consuming engine's lookup, and docs/guide/first-asset.md ends at step 7 (cleanup.py keep) with no 'move it into your game' step at all. In a consuming engine the FILE NAME is usually the whole convention: grass.jpg where the code wants plains.jpg, or Plains.jpg where it wants lowercase, looks perfectly reasonable, matches nothing, and is ignored in SILENCE while the map goes on drawing its generated fallback with no error anywhere. The general form is stronger and also absent: every missed asset in the source project was two lists of names drifting apart, none of which could fail loudly — so name each shipped asset in ONE place, make the matcher its own tested function, and add a test that walks that list against the bundle. The same failure recurred inside the code when a preview bench kept its own copy of the model-to-atlas mapping. This is the bridge between 'the pipeline produced a file' and 'the game actually draws it', and the repo currently stops one step short of it. (AUDIT.md:292 records a related idea — a test deriving the expected asset set from the code's own enums — so this is corroborated internally.)

*Evidence:* first-asset.md ends at step 7 (cleanup) with no integration step; concept-art.md:137 covers output naming only; terrain.md:15-17 and ground-texture/SKILL.md:56 give filenames with no convention warning; AUDIT.md:292 records the enum-derived test idea

### cut_icon.py takes the MEDIAN of the four corners, and icons.md explains neither that nor any of the tool's flags

**medium** &middot; belongs in `docs/guide/icons.md ('Generate on a flat background on purpose', and a 'When the whole frame survives' note naming --tol and the coverage report)`

MERGES candidates 17, 41 and 83 — three auditors. VERIFIED: the reasoning is fully written at scripts/cut_icon.py:110-120 ('The MEDIAN of the corners, not the mean') and the tool reports ink coverage at :183, but grep for 'median' and 'ink coverage' across docs/ returns nothing. docs/guide/icons.md:11-19 says only 'The four corners are background by construction, so the fill starts there and spreads while the colour stays close', and the page names no flags at all — --tol is never mentioned. So a reader whose whole frame survives as a grey box around the icon has no route to the diagnosis: one corner is often not background at all (a glow thrown by the subject reaches into it), the outlier drags a mean reference off the real grey, and the cut then fails at EVERY tolerance — and that tolerance-independence is exactly what makes it look as though the picture rather than the fill is wrong. A median over four samples ignores one bad corner. The companion habit belongs with it: the tool prints ink coverage precisely so a survived background is loud rather than noticed by eye three assets later, and the guide should say to read it (under ~5% means raise --tol, over ~92% means lower it). This is the cheapest fix in the whole list — the text already exists in the file.

*Evidence:* scripts/cut_icon.py:110-120 carries the full explanation and :183 prints ink coverage; docs/guide/icons.md:11-19 covers the corner fill without it and the page names no flags anywhere

### diso must be built with FORCE_CUDA=1, because BuildKit gives the build no GPU and install.py swallows the failure

**medium** &middot; belongs in `docs/reference/docker.md (the build-traps section alongside the BuildKit-context note)`

VERIFIED absent from docs. grep for 'diso', 'FORCE_CUDA', 'MAX_JOBS' and 'TORCH_CUDA_ARCH_LIST' across docs/, skills/ and README.md returns nothing; the only trace is a comment at scripts/publish_image.sh:42. BuildKit does not run build steps under the daemon's nvidia runtime, so torch.cuda.is_available() is false during `docker build`; diso's setup.py falls back to a CppExtension with the .cu sources dropped and fails with 'No CUDA runtime is found'. install.py swallows that, so the image builds green and looks fine until TripoSG's unconditional `import diso` takes the whole node pack down at runtime — which the reader experiences as 'node packs not loaded' with no build-time signal at all. Also missing: MAX_JOBS must be capped, because unbounded nvcc runs one job per core (28 here) and CUDA template instantiation exhausts 31GB of RAM. docs/reference/docker.md is otherwise a good page on the version chain and its build-traps section (BuildKit context snapshot, named volume vs bind mount) is the obvious home for both.

*Evidence:* grep -ri 'diso|FORCE_CUDA|MAX_JOBS|TORCH_CUDA_ARCH_LIST' over docs/, skills/ and README.md returns nothing; scripts/publish_image.sh:42 is the only mention; docker.md:101-111 has the build-traps section with no entry for it

### Carried pieces must live in the figure's 3D space, and hold points are authored once against a normalised height

**medium** &middot; belongs in `docs/guide/facings.md (a 'Held items and attachments' section) or the new buildings/integration page, cross-linked from docs/guide/animation.md`

MERGES candidates 15, 94 and 95. VERIFIED absent: grep for 'weapon', 'carried', 'attachment', 'occlu', 'depth sort' and 'hold point' across docs/, skills/ and README.md returns nothing. animation.md:144-155 covers posed models vs sheets well and stops before equipment. The failure that makes people rebuild the feature: a carried piece drawn as a 2D overlay can be positioned but can never be OCCLUDED — a sword on a soldier turned away still paints in front of their back at every offset, and there is no 2D fix, because layer order is fixed and a sprite has no depth for a blade to go behind. Posed in the figure's own 3D space and merged into the same depth sort, it is hidden exactly as far as the body is, and it gets rotation for free: the piece is transformed before the figure's yaw, so ONE description serves all four facings. Because one textured draw samples one image and a figure and a blade come from different atlases, the sorted triangles are walked and flushed whenever the atlas changes — depth order survives across meshes at the cost of one draw call per switch. The authoring half ties back to the scale gap: normalise every human figure to a common height and the hand position is hand-authored ONCE, in 3D, instead of once per facing per figure. Y is measured from the MIDDLE of the figure, which is why a hand sits below centre and a long weapon's own centre lower still — get that wrong and the weapon's point rides up past the head. Offsets are per item TYPE (a greatblade is nearly as tall as its owner, a dagger hangs low); the off hand is mirrored. Anyone building a unit set with swappable weapons out of this pipeline hits this immediately.

*Evidence:* Zero hits for 'weapon', 'carried', 'attachment', 'occlu', 'depth sort' or 'hold point' anywhere in docs/, skills/ or README.md; animation.md:144-155 covers posed models without equipment

### Judge the terrain SET on the grid, not each texture alone

**medium** &middot; belongs in `docs/guide/terrain.md (a 'Judging the set, not the texture' section) and the Rules block of skills/ground-texture/SKILL.md`

MERGES candidates 84 and the set-level half of 9. VERIFIED: skills/ground-texture/SKILL.md:81-97 checks ONE texture tiled 3x3 and looks for recognisable repeats, and terrain.md judges a texture on its own merits — seam score, contrast std, tiled preview. The set-level criterion is missing everywhere: nine terrains that cannot be confused for one another is the whole job, and the individual photographs are largely interchangeable. Three of nine terrain materials had to be picked TWICE because, rendered on the isometric grid at game scale, 'broken' read as snow, highlands read as moss rather than rock, and swamp was indistinguishable from forest. None of those failures is visible in a single-texture tiled preview; the check is to render the whole set on the grid together. The skill's 'Rules' block is the natural home, since it already carries 'Never hand over a texture you have not seen tiled' — the missing sibling is 'never hand over a set you have not seen side by side on the grid'.

*Evidence:* skills/ground-texture/SKILL.md:81-97 checks a single texture tiled; its Rules block ends at 'Never hand over a texture you have not seen tiled'; no doc anywhere mentions comparing terrains against each other

### Golden and snapshot tests are useless for anything with art in it — measure geometry instead

**medium** &middot; belongs in `a new docs/guide/verifying.md (alongside the harness-startup rule) or an addition to docs/guide/ground-and-relief.md Part 4`

VERIFIED: grep for 'golden' across docs/guide and skills/ returns only an unrelated prompt file about wheat. ground-and-relief.md:334-362 has a genuinely good testing section, but it is entirely about terrain arithmetic — assertions on heights, steps and seams. The art-testing rule is absent: an image asset decodes to nothing in a widget or unit test, so a golden of an asset-backed screen comes back blank and proves nothing while the suite stays green. Measuring rectangles directly is real, and it is what caught a 15px misalignment that three 'almost there' rounds of eyeballing could not. This belongs in the same place as the harness-startup rule, because both are ways a verification step can report success while testing nothing — the same failure shape the guides already warn about at every generation stage. Anyone integrating this pipeline's output will reach for golden tests first, get a passing suite, and lose the afternoon.

*Evidence:* grep 'golden' across docs/guide and skills/ returns only prompts/ground text about wheat; ground-and-relief.md:334-362 covers geometric assertions only

### Export axis conventions and mesh joining are never stated, though the docs recommend OBJ for downstream tools

**medium** &middot; belongs in `docs/guide/meshes.md ('File formats' / a short 'Getting it into your engine' section)`

MERGES candidates 28 and 21/96's loader half. VERIFIED: grep for 'z-up', 'up_axis' and 'forward_axis' across docs/, skills/ and README.md returns nothing. docs/guide/meshes.md:68-96 compares what each format can CARRY (geometry, UVs, textures, vertex colours, skeleton, file count) and never states what orientation it is written in. Two facts belong there. (1) A glTF scene often arrives split into several mesh objects, and many engine-side OBJ readers take only the first, so the export path must select every MESH, make one active, and join before decimating — and height is measured on Z inside Blender while the exported OBJ is written forward -Z / up Y, which is where a model that arrives lying on its face or mirrored comes from. meshes.md names the multi-shell distinction ('Watertight versus multi part') without connecting it to the join-before-export rule. (2) For anyone writing their own loader — which meshes.md actively encourages by recommending .obj 'when a tool downstream wants it' — OBJ shares positions between faces but lets each face corner pick its own texture coordinate, and a GPU vertex is one position AND one uv, so corners must be re-emitted as UNIQUE vertices rather than indexed. That also gives flat shading somewhere to put a per-face colour. An indexed load produces a model that renders with the texture scrambled and no error. A useful corollary: affine UV interpolation across a triangle is exact rather than approximate under an orthographic camera, because there is no perspective divide to correct.

*Evidence:* Zero hits for 'z-up', 'up_axis', 'forward_axis' or 'unique vert' across docs/, skills/ and README.md; meshes.md:68-96 compares format capability only and recommends .obj for downstream tools

### Deriving limbs from an unnamed skeleton has two specific traps, and both pages recommend doing it without them

**medium** &middot; belongs in `docs/guide/rigging.md ('Bone names are not human readable', after the geometry paragraph) and docs/guide/animation.md ('Deriving cycles automatically')`

VERIFIED. docs/guide/rigging.md:178-181 and docs/guide/animation.md:134-142 both recommend working the limbs out from the skeleton's own geometry, each in a single sentence ('the root is the bone with no parent, the legs are the two chains descending furthest below it, the spine is the chain that rises, and the arms are the two chains branching off near the top'), and both stop there. Two failures cost the original a round trip each and neither is recorded. (1) Following the longest child at every step is right for a LIMB, because it skips digits — and it walks straight out an ARM when tracing the spine, because an arm is longer than a neck; the fork that should have given the two arms then produced one arm and the head. The spine must instead follow the child that stays closest to the body's centre line. (2) Picking the two arms by sorting the shoulder fork's children by x picked the HEAD, which sits between them — take the EXTREMES of the sort, not the first two. Both pages tell the reader to copy an approach whose two sharp edges are undocumented, and this is compounded by the fact that the tool both cite (tool/make_cycles.py) lives in another repo, so the reader has to reimplement rather than read.

*Evidence:* docs/guide/rigging.md:178-181 and docs/guide/animation.md:134-142 each describe the method in one sentence with no failure modes; the referenced tool/make_cycles.py is in the game repo, not here

### Redo a whole set at one quality — one model left at the old pass shows against the new ones

**medium** &middot; belongs in `docs/guide/decimation.md ('Budgets in this pipeline', after the budget table) and the Rules block of skills/mesh-budget/SKILL.md`

VERIFIED absent: no occurrence of 'uniform', 'same quality', 'whole set' or 'mixed' in decimation.md or skills/mesh-budget/SKILL.md. Nothing in the repo warns that quality is judged WITHIN a row rather than against an absolute. One figure left at a 4k-face decimation while everything around it had been redone at 12k was visibly wrong on screen beside its neighbours, and a mixed-quality set reads worse than a uniformly lower-quality one. This is directly actionable given how careful decimation.md's budget tables are: the tables let you pick a good number per model, and the missing rule is that you must then apply it to every model in the same row. It is also the argument for re-running a whole set after changing a budget rather than patching one asset — which is a real cost decision the budget tables currently invite the reader to make wrongly.

*Evidence:* Zero occurrences of 'uniform', 'same quality', 'whole set' or 'mixed' in docs/guide/decimation.md or skills/mesh-budget/SKILL.md; the budget table at decimation.md:125-130 is per-model with no set-level rule

### Cutting a device out of painted background: two masks, a premultiplied pyramid fill, and a global checkerboard key

**medium** &middot; belongs in `a new docs/guide/ui-art.md, cross-linked from docs/guide/icons.md ('Art that is not on a flat background'), plus a scripts/split_ui_art.py alongside scripts/cut_icon.py`

MERGES candidates 13, 33, 34, 35, 36, 37, 38, 97, 98, 99 and 100 — a large cluster from two auditors, all verified absent (zero hits for 'checker', 'premultipl', 'push-pull', 'pyramid', 'saturation', 'niche', 'least squares' or 'BoxFit' anywhere in docs/, skills/ or README.md). scripts/cut_icon.py handles exactly ONE case — a subject on a flat GENERATED background — and icons.md stops there. Four harder cases are undocumented and unsupported. (a) TWO masks: a device painted INTO a background needs a TIGHT key for what you lift (saturation, when gold and emerald are the only saturated things on the page) and a GENEROUS disc for what you erase, because the painting carries faint outer rings and a shadow too pale for any saturation test — leave them and you get a ghost, widen the key to catch them and you eat the paper's shading and get a grey halo. No single threshold does both. Two tempting additions are wrong: a darkness test also catches the device's shadow and the page vignette, which then join the device as one enormous component and drag a continent of parchment into the cut-out; and filling holes in the mask closes the ring's interior and carries a disc of background along. Despeckling is still needed. (b) PYRAMID FILL: halve, fill from the level above, blend back up, carrying colour PREMULTIPLIED by weight and normalising only on read-back — reading a premultiplied level as a colour fills the hole with black, which is what the first draft did. The result comes back lumpy and every lump reads as a stain, so blur it at a fraction of the hole radius. Only viable because the surface is low-frequency; useless on foliage. (c) PAINTED CHECKERBOARD: an image exported as 'transparent' often arrives as RGB with the checker rendered into the pixels (two near-neutral greys at 254 and 230), and it must be keyed GLOBALLY with both a neutrality test (max-min < 12) and a level test — a border flood fill leaves a chequered window in the MIDDLE of the device, because the gaps between a ring and the diamond inside it are exactly where you see through, and a level-only key eats pale gold highlights. This is the trap where reaching for icons.md's documented edge-touching-island rule produces a visibly broken result. (d) DON'T BAKE IT IN: a device painted into a menu background cannot be moved, resized or reused, and the obvious lever is inert for a measured reason — BoxFit.cover fits a 1.788 painting into a 1.4 window BY HEIGHT, so a vertical alignment has no slack and changing it moves nothing. Generate the plate, then split it into layers. Removing a painted element needs a per-region threshold against each alcove's own light (70th percentile of luminance x 0.62), a least-squares quadratic surface fit per channel to fill (blur-fill smears and reads as a stain; borrowed residuals come out as salt and pepper because they hold painted streaks, not grain), and a feathered seam.

*Evidence:* scripts/ has cut_icon.py only, documented for flat generated backgrounds; zero hits for 'checker', 'premultipl', 'push-pull', 'pyramid', 'saturation', 'niche', 'least squares' or 'BoxFit' across docs/, skills/ and README.md; icons.md:31-42 presents edge-touching islands as the only fill exception

### run_workflow.py's output report is an mtime sweep, because Save 3D Mesh records nothing in the API history

**medium** &middot; belongs in `docs/reference/scripts.md (the run_workflow.py block) or docs/reference/workflows.md ('Running one')`

VERIFIED. scripts/run_workflow.py:185-196 sweeps output/ for files with mtime >= queue time and prints '(workflow produced no file outputs)' when it finds none — then returns 0. The reason is a good inline comment: Comfy3D's Save 3D Mesh is an OUTPUT_NODE that returns the path as a STRING and never populates `ui`, so /history carries no outputs for a mesh workflow. No doc says any of this: docs/reference/scripts.md:22 describes run_workflow.py as 'Queue a graph, wait, report the outputs', which reads as though the API reports them, and grep for 'OUTPUT_NODE' or '/history' across docs/ returns nothing. This matters for two audiences the docs explicitly cultivate: anyone writing their own automation over these graphs (meshes.md and first-asset.md both encourage custom batch loops) will poll /history, see no outputs at all for a mesh workflow, and conclude the run failed; and anyone debugging why run_workflow.py reported an unexpected file needs to know the report is an mtime sweep over the whole output tree, not an authoritative list. Note the exit-code half is already tracked in AUDIT.md's batch-driver entry.

*Evidence:* scripts/run_workflow.py:185-196 implements the mtime sweep and returns 0 on no outputs; docs/reference/scripts.md:22 says only 'report the outputs'; zero hits for 'OUTPUT_NODE' or '/history' in docs/

### Automated framing on painted art fails often enough to need an eye, and a cover fit needs an aspect guard

**medium** &middot; belongs in `docs/guide/icons.md (a 'Portraits and art in fixed boxes' section) or a new docs/guide/placing-art.md`

MERGES candidates 11, 19, 85 and 105. VERIFIED absent: zero hits for 'BoxFit', 'aspect', 'IHDR', 'portrait crop' or 'avatar' guidance anywhere in docs/guide or skills/. The pipeline emits fixed 1104x1472 portraits and 1024x1024 icons (workflows.md:19-23) that land in fixed UI boxes, and nothing warns about either half of what follows. (1) The silent crop flip: measured across 28 painted portraits against 30x38 and 42x54 boxes, every source was narrower than its box, so a cover fit scaled by width, the overflow went vertical, and the face was always whole — safety that was completely unguarded and invisible in the PNG. A portrait WIDER than the box's aspect (0.778 there) flips cover to scale by height, and since these figures fill 97-100% of their canvas width the horizontal crop takes the face itself. The cheap guard reads width and height straight out of the PNG IHDR chunk with no decode, so it runs under any test binding and names the offending file and its aspect. (2) The honest limit of automation, which is unusual enough to be worth writing down in a repo whose instinct is 'measure it': apparent face width across those 28 heads varied by about 40%, so neighbours look unevenly framed, and automated head-finding got 6 of the 28 badly wrong (two came back as all head). Every centre-of-mass rule tried called one plainly off-centre figure centred — and BY MASS he is, because he stands turned with a torch held out, so the middle of the picture is not the middle of the man. That table is hand-authored on purpose, and saying so saves a day of tuning a heuristic that cannot work. (3) Never size a UI slot off the pixel dimensions of today's art: one screen hard-coded 278x426 because that was the portrait's size at the time, and the two other sprites that can land in that slot would have been stretched. Read the image's own dimensions.

*Evidence:* Zero hits for 'BoxFit', 'aspect', 'IHDR' or portrait-crop guidance in docs/guide or skills/; concept presets emit fixed 1104x1472 and 1024x1024 canvases (docs/reference/workflows.md:19-23); render_sheet.py:106-120 is automation-first with no caveat

### File size on the way out: strip vn, round to four decimals, and commit the decimated output rather than the raw exports

**medium** &middot; belongs in `docs/guide/decimation.md (a 'Preparing output for a game repo' section) and docs/guide/cleanup.md ('What crosses into your game repo'); skills/asset-cleanup/SKILL.md rules`

MERGES candidates 16, 44, 91, 102 and 82. VERIFIED: docs/guide/meshes.md:68-96 compares what each format can CARRY and says nothing about what they COST; grep for 'decimal', 'precision', 'file size', 'vn ' and 'normals' across docs/ and skills/ returns nothing relevant; and docs/guide/cleanup.md covers curation within output/ (copy-not-move, sources.json, two deletion levels) but never what crosses into a project's git history. Four connected facts. (1) Blender writes six decimals to OBJ, which roughly triples the file for no visible gain when the asset bakes to a 128px sprite off a 1024px atlas — four decimals (five for UVs) is finer than a texel either way. (2) Shipped OBJs should drop `vn` lines when the draw path computes flat normals itself from the triangle. Together these roughly HALVE the files, which across a full set is tens of megabytes in a web bundle — a strange silence in a repo that measures everything else. (3) Commit the decimated output, not the raw exports: hosted exports run 80-110MB apiece, ten of them is a gigabyte in every clone, and they hold the INPUT to a step that has already run and that nothing in any build reads. Contact sheets go the same way, since every subject already exists as its own file — with the honest exception that a sheet must be kept when some of its singles are missing from the working tree, because for those subjects the sheet is the only copy on disk. Committing derived meshes at all is the deliberate part: the tool is reproducible but slow (forty minutes of decimation). (4) The subtler companion: once a tool exists that cuts, keys or composites art, the shipped file becomes that tool's OUTPUT and is no longer the source, so the source art must stop being gitignored — it is the only copy the tool can be re-run against, and pointing the tool at the shipped file re-keys a device that is no longer in it.

*Evidence:* docs/guide/meshes.md:68-96 compares capability only; zero hits for 'decimal', 'precision' or 'vn ' in docs/; docs/guide/cleanup.md and skills/asset-cleanup/SKILL.md:92-93 stop at 'copy them into the project proper when they are final'

### The version chain stops one link short: transformers, diffusers and huggingface-hub must be pinned as a coherent set, and one bad import fails the ENTIRE 3D-Pack

**low** &middot; belongs in `docs/reference/docker.md ('The chain' as a fourth link, 'Node packs', and 'Publishing the image'); docs/guide/troubleshooting.md ('A node pack did not load' — add the all-or-nothing import cause)`

MERGES candidates 61, 64, 65, 63 and 66. docs/reference/docker.md's 'The chain' runs host driver -> CUDA -> Python/torch -> ComfyUI version and stops. Partially covered: docker.md:35 does say 'The last version of that dependency which runs on torch 2.6 is pinned in the constraints file alongside torch, so nothing can bump it back', which is the mechanism in essence — so candidate 65 is the weakest of this group. What is genuinely missing: (a) the fourth link, that left to resolve freely pip installs transformers 5.x (which calls safe_open(..., backend=), an API in no safetensors release, and dies loading any diffusers pipeline) and diffusers 0.40 (which needs huggingface-hub >= 1.23 while transformers 4.x caps it below 1.0) — so a reader following the page's own 'How to escape the pin' advice, or adding a node pack that pulls a newer transformers, breaks diffusers with an error that points at safetensors rather than at the pin; (b) that a SINGLE ImportError anywhere takes down every algorithm in 3D-Pack, which is the cause that makes troubleshooting.md's 'A node pack did not load' log line make sense — patch_nodes.py:31-46 records two instances (Era3D's removed CLIPFeatureExtractor alias, Stable3DGen's moved ControlNetOutput) and gpytoolbox 0.3.0's np.Inf is a third, reached transitively through StableFast3D; a reader who finds a traceback naming gpytoolbox or Era3D, packs they have never used, has no reason to think it explains why TripoSG is missing; (c) the build-time canary technique — StableFast3D is imported unconditionally by nodes.py and drags in gpytoolbox, so importing it during the build turns a fragile chain into a red build rather than a missing node category found in the browser hours later (and the full nodes.py cannot be imported at build time because it wants ComfyUI's folder_paths, which exists only once the server runs); (d) two apt/wheel traps — python3-blinker lands in /usr/lib/python3/dist-packages which deadsnakes' 3.11 still has on sys.path and pip refuses to uninstall it, and --ignore-installed is NOT the fix because it takes no argument and re-resolves torch from scratch, undoing the constraint pin; and bpy 4.5.9 is the last release with a cp311 wheel, which install.md mentions only as a version string in sample doctor output with no hint that it is a ceiling.

*Evidence:* docker.md:26-38 stops at the ComfyUI pin; Dockerfile:66-74 pins transformers/diffusers/gpytoolbox/comfy-kitchen; scripts/patch_nodes.py:31-46 records two whole-pack ImportErrors; zero hits for 'blinker', 'basicsr' or a build-time canary in docs/; docker.md:35 already covers the constraints mechanism, so 65 is largely redundant

### The browser verification loop: fixed seeds, browser furniture, and three headless routes that return empty frames

**low** &middot; belongs in `the new docs/guide/verifying.md, alongside the harness-startup rule`

MERGES candidates 22, 88, 45, 106, 107 and 108. VERIFIED: zero hits for 'CDP', 'chrome', 'swiftshader' or 'headless' anywhere in docs/ or skills/. Framework-specific and therefore the lowest-value of the verification cluster, but the shape transfers and 'look at it in the game' is the repo's own closing instruction on almost every page. Three ways of screenshotting a GPU-canvas app all fail SILENTLY, each costing a round trip: an out-of-process browser-automation MCP whose screenshots never land on the local filesystem; a system playwright package whose node driver will not start ('Connection closed while reading from the driver'); and `--headless --screenshot`, which returns an empty frame with or without a virtual-time budget, because the canvas needs real time and a real GL context. What works is driving the browser over CDP with swiftshader for the context, --remote-allow-origins=* (or Chrome refuses its own socket), and a WALL-CLOCK wait. Four companions: shoot against a FIXED SEED and boot straight onto a NAMED screen, because where the scene is random per launch a click flow aims at a state that will not come back, and a set of hand-taken shots drifts for exactly that reason (ground-and-relief.md:357-362 already has the throwaway-entrypoint half, which is why this is thin rather than absent — clicking to raise a panel missed four times in six, and a miss still writes a perfectly good screenshot of the wrong thing with nothing in the run to say so); shoot OVERSIZED and crop, because the browser's own chrome eats ~143px; give a slow click its own settle override rather than raising a global settle that is then paid after every other click; and re-shoot on a schedule rather than on suspicion, because the re-shoot is what catches regressions nothing else does (one screen still drawing the old primitive figure; a card at a fixed offset now landing on another element). Once assets are integrated, the engine's own viewer beats any external previewer — the previewer's job is specifically pre-integration, judging a decimation and a texture size before paying for the pipeline that would ship them.

*Evidence:* Zero occurrences of 'CDP', 'chrome', 'swiftshader' or 'headless' in docs/ or skills/; docs/guide/ground-and-relief.md:357-362 carries the throwaway-entrypoint half for terrain only

### Bake sprites lazily, load heavy meshes asynchronously, and hold the space rather than swapping a placeholder

**low** &middot; belongs in `a new docs/guide/integrating.md, or notes in docs/guide/facings.md#eight-facings and the 'Sizes' table`

MERGES candidates 20, 103, 104 and 12. Consumption-side, but a direct consequence of what this pipeline emits and what facings.md tells people to render. facings.md:124-132 covers the STORAGE cost of eight facings ('four times the storage of four facings once you multiply by animation frames and team colours') and never the STARTUP cost: four quarter-turns times nine banners is four times the startup rasterisation, and a startup bake blocks the first frame; thirty-one 12,000-triangle meshes with 2048px atlases would put seconds in front of it. So bake only the primary pose at startup, draw the other quarters on first use into a second cache dropped whole past a ceiling (~240 images; a screen's worth is a few dozen and refills in milliseconds), and load meshes asynchronously — the first ask returns null, a placeholder draws, and a revision notifier replaces it a frame or two later. Two silent failures both present as 'my models never appear': the manifest loader that decides which models exist never being called from the app's entry point, so the set is always empty and every lookup quietly returns null; and any painter that does not take the bake revision as its repaint signal, which goes on drawing the placeholder until something unrelated dirties it. The policy half: where a scan is known to exist, HOLD the space rather than swapping a primitive in front of the player — a swap reads as the wrong unit flickering into the right one, and a beat of empty ground is quieter. The primitive still draws where no scan exists at all, which keeps a build shipped without the models folder unchanged. Related and cheap: do not upscale a baked sprite for a close-up — an intro drew a building 880 units across from a 128px sprite, an eightfold blow-up that goes to mush; re-render the subject at the size the shot needs, resolving the shared atlas the way the game does and writing RGBA from the depth buffer's coverage so the figure composites over a scene. render_sheet.py:158 already sets film_transparent = True and no doc mentions it.

*Evidence:* docs/guide/facings.md:124-132 covers storage cost only; scripts/render_sheet.py:158 sets film_transparent with no doc mention; zero relevant hits for 'lazil', 'startup bake', 'manifest', 'revision' or 'placeholder' in docs/

### Small workflow-authoring and format facts that live only in _comment fields

**low** &middot; belongs in `docs/reference/workflows.md (Qwen and mesh_render_sprites rows, txt2mesh caveat); docs/guide/textures.md opening; docs/guide/icons.md (lettering, launcher icons, formats); docs/guide/ground-and-relief.md Part 2; docs/reference/docker.md ('Publishing the image')`

MERGES candidates 68, 69, 67, 70, 86, 93, 42, 101, 39 and 109 — the genuinely low tail, all verified absent from docs/ but most already one file-open away. (a) Qwen text-to-image needs EmptySD3LatentImage; a plain EmptyLatentImage is a real node with real inputs, so the graph VALIDATES and then produces nothing usable — validate_workflows.py will not catch it, and zero 'SD3' hits exist in docs/. (b) Mesh Orbit Renderer's second output is a MASK, which SaveImage will not take, so MaskToImage sits between them (mesh_render_sprites.json nodes 5-6); and Stack Orbit Camera Poses clamps azimuth to [-180,180], which is why that graph reads -135..180 rather than 45..360 — facings.md explains the 45-degree start thoroughly and a reader comparing it against the graph finds numbers that do not obviously match. (c) ShapeGen and TexGen cannot share one graph on a 16GB card, which is WHY mesh_texture_hunyuan3d21.json takes a mesh path rather than a wired mesh — the practice is documented in three places, only the rationale and its two payoffs are missing (a failed texture pass never costs you the geometry; any generator's mesh can be textured by it, which is what lets a worldwide-shipping TripoSG shape be textured or not). (d) The end-to-end txt2mesh graphs generate the mesh whether or not the concept was worth it, and a bad concept is the usual reason a mesh comes out as twenty disconnected pieces; the cheaper path is txt2img_qwen_fast to find the picture then img2mesh on the one you like — largely mitigated by skills/asset-pipeline/SKILL.md's one-stage-per-turn gating, so this is a missing pointer rather than a missing idea. (e) 2D format choice is uncovered outside ground textures: a menu painting went 2.5MB of PNG to 328KB as a progressive JPEG, and an edge fade baked into a file costs an alpha channel which costs a PNG — three megabytes of grain against four hundred kilobytes of JPEG — so do the fade in the widget; alpha is the expensive decision, not resolution. (f) Keying LETTERING off white fails differently from icons: a border flood fill leaves letterform counters (the bowls of an A, an a, both o's) opaque, and the rule that works is clearing every sizeable white REGION regardless of connectivity, since size is exactly what separates a counter from a specular highlight — a reader will reach for icons.md's edge-touching-island rule, which is the wrong tool. (g) Launcher and web icons are a separate job: render from vectors at 8x supersample, and give the mark a different fraction of the square per target because each launcher applies its own mask (0.80 Android mipmaps, 0.84 web, 0.62 maskable safe zone, 0.96 a 32px favicon). (h) A painted isometric block is taller than its top face, so centring it on the tile sinks every tile half a wall into the ground; the anchor must be MEASURED per block as the widest opaque row (a 2:1 block is at its widest exactly at the diamond's waist) and the anchors genuinely vary, so a constant cannot work — a fallback only, since ground-and-relief.md argues persuasively against per-tile blocks. (i) A destructive tool over a lossy file must run exactly once and never point at its own output — speculative here, since no such tool ships. (j) .dockerignore's own reasoning (12GB context down to 18MB, dominated by the 11GB pixi env) is excellent in the file and absent from docker.md's build-traps section.

*Evidence:* Zero hits for 'EmptySD3', 'MaskToImage', 'dockerignore', 'maskable', 'favicon' or 'checkerboard' in docs/; workflows/api/txt2img_qwen.json:2, mesh_render_sprites.json:2 and mesh_texture_hunyuan3d21.json:2 _comments carry (a)(b)(c); .dockerignore:1-5 carries (j); '16GB' appears in docs/ and skills/ only in concept-edit/SKILL.md

---

## Findings from the session transcripts

### The two-pass route — simplify with Qwen edit, then re-render with SDXL — is documented nowhere but one workflow comment

**high** &middot; **fixed 2026-09-10** &middot; belongs in `docs/guide/concept-art.md (a section after "Simplifying art you already have"), and skills/concept-edit/SKILL.md`

prompts/realism_pass.txt and workflows/api/img_refine_sdxl.json both exist, but no guide page teaches the route. docs/guide/concept-art.md's workflow table lists only four graphs and stops at the simplify pass; docs/reference/workflows.md gives img_refine_sdxl.json one row, "Refine pass over an image". The lessons missing from the prose: (1) one job per pass beats one prompt doing both — asking Qwen-Image-Edit to simplify AND re-render realistically in a single prompt was worse than two passes, and that, not wording, is what moved the needle; (2) "photorealistic" alone was only a modest gain and true photorealism is not reachable through this model at all, because Qwen-Image-Edit's prior is illustrative and no amount of prompt wording overrides it — the same shape as "NOT cartoon" failing at denoise 1.0; (3) the way out is a different model for the render pass — SDXL base as a low-denoise refiner, where denoise is the whole control: 0.25-0.35 adds material detail and keeps the design, above ~0.5 SDXL starts reinventing shapes; (4) the CivitAI realism checkpoints sitting on this box (cyberrealistic, intorealism and the rest) are deliberately not used — NSFW-oriented with unclear licensing, wrong for a pipeline that ships game assets, where SDXL base is CreativeML OpenRAIL++-M and commercially clear.

> "photorealistic" alone was a modest gain, and true photorealism isn't reachable here. The edit model's prior is illustrative, and no amount of prompt wording overrides it … What actually moved the needle was giving the model one job per pass instead of two.

### The packaged profile never pins comfy-kitchen inside UniRig's pixi env, so UniRig can register ZERO nodes

**high** &middot; belongs in `scripts/postinstall.sh (make it work for the packaged container too), plus a symptom entry in docs/guide/troubleshooting.md and a line in docs/reference/docker.md under "Node packs"`

UniRig's isolated comfy-env/pixi environment resolves comfy-kitchen to latest (0.2.33 at the time), which needs torch >= 2.7 — the same PEP 585 wall the main env hit, now inside the isolated one. The pixi env inherits torch 2.6, the two disagree, and UniRig logs the ValueError and carries on registering ZERO nodes. Fix: pin comfy-kitchen==0.2.26 in the pixi env. scripts/postinstall.sh does exactly this (lines 38-48), but it is hard-wired to the source profile — it runs `docker compose --profile comfy ps/exec` against SVC=comfyui and exits 1 if that container is not running, and it guards on the host path `.comfy-env/envs/unirig-nodes/.pixi/envs/default`. In the packaged profile the pixi env is built on first use inside the `unirig-home` NAMED VOLUME (docker-compose.yml 89-92), scripts/entrypoint.sh only seeds mounts and reports weights, and nothing anywhere applies the pin. So the published-image path — the one the README calls the whole install — can silently come up with no rigging nodes, and doctor.py will say `node packs  not loaded: ComfyUI-UniRig` with no hint at the cause. Either make postinstall.sh profile-aware (`docker exec comfyui-packaged $UNIRIG_ENV/bin/python -m pip install 'comfy-kitchen==0.2.26'`) or have entrypoint.sh apply it after the env builds, and document the symptom.

> UniRig registered **0** nodes | pixi env resolved `comfy-kitchen` to 0.2.33, which needs torch ≥2.7 — the same wall as the main env, now inside the isolated one | pin 0.2.26 in the pixi env

### ComfyUI dies mid-generation with RemoteDisconnected and the container restarts itself — a batch silently produces nothing and still reports ok

**high** &middot; **fixed 2026-09-10** &middot; found independently by 5 auditors &middot; belongs in `/asset-engine/docs/guide/troubleshooting.md (new entry); the retry loop itself in /asset-engine/scripts/generate_concepts.sh, generate_lords.sh and simplify_concepts.sh; a non-zero exit for "produced no file outputs" in /asset-engine/scripts/run_workflow.py`

During an icon batch, ComfyUI repeatedly died mid-generation (`RemoteDisconnected` / connection reset) and the container restarted itself; the batch driver printed each name as it went while the server had already gone, and 11 icons silently produced nothing on the first pass. The fix that got them all: a retry loop that checks the server is answering BEFORE each attempt, restarts it when it is not, and gives three tries per item; generating in smaller batches also avoids it. No batch driver here does this — `generate_concepts.sh`, `generate_lords.sh` and `simplify_concepts.sh` each call `run_workflow.py` once per item and print ok/FAILED with no pre-flight check, no retry, no verification a file appeared. Two structural holes make the silent-success mode reachable in this repo as written: `report()` in `scripts/run_workflow.py` prints "(workflow produced no file outputs)" and still returns 0, so the shell driver prints `ok` for a run that made nothing; and `wait_for()` polls `/history/<id>` forever, so a server that restarts and comes back with an empty history hangs the batch rather than failing it. `docs/guide/troubleshooting.md` mentions neither `RemoteDisconnected` nor a self-restarting container.

> ComfyUI keeps dying mid-generation — `RemoteDisconnected` / connection reset, then the container restarts itself. That's why 11 icons silently produced nothing earlier: the batch reported each name but the server had already gone. It's now on a retry loop that checks the server is answering before each attempt and restarts it when it isn't, three tries per icon.

### img_edit_qwen.json's _comment recommends the denoise band that was measured to do nothing

**high** &middot; **fixed 2026-09-10** &middot; found independently by 2 auditors &middot; belongs in `workflows/api/img_edit_qwen.json (`_comment`); regenerate workflows/default/workflows/img_edit_qwen.json with scripts/api_to_ui.py`

The `_comment` in workflows/api/img_edit_qwen.json (and therefore the Note in the regenerated workflows/default/workflows/img_edit_qwen.json) says: "Lower it to preserve the source's rendering while still applying the edit: ~0.8 for a small swap, ~0.5-0.65 to restyle or simplify while keeping the painterly surface." The measured ladder contradicts that half of it directly: edit_00006_ at denoise 0.55 came back near-identical to the source and barely simplified, edit_00007_ at 0.70 was still very close to the source, 0.85 (edit_00008_) was the first that genuinely simplified while keeping the painterly rendering, 0.93 (edit_00009_) was game-ready, 1.0 was flat vector cartoon. Every other place in the repo carries the correct band (docs/guide/concept-art.md's table, scripts/simplify_concepts.sh's header, preset_simplify_concept.json's _comment), and the editor Note stacked on top of this same file even says "Below about 0.75 nothing moves" — the file contradicts itself. Change 0.5-0.65 to 0.85 for a restyle/simplify and 0.93 to push to clean game-ready forms; each wrong attempt is a 130s round trip that reads as a prompt failure rather than a setting one.

> **denoise 0.55** — near-identical to source, barely simplified … **denoise 0.85** — painterly kept, genuinely simplified

### Meshy's ownership grant is conditional — publishing to the Community gallery and dirty reference images both void it

**high** &middot; found independently by 3 auditors &middot; belongs in `/asset-engine/docs/guide/licensing.md (a Meshy section, alongside the model licences), cross-linked from the MCP section of /asset-engine/docs/reference/skills.md`

The repo ships a Meshy MCP server in `.mcp.json` and documents the API key and the ~2M-triangle export size, but never states the terms under which you own a Meshy mesh. Two conditions: (1) Meshy Pro grants ownership of generated assets "provided you do not publish them publicly to the Meshy Community" — stay private and it is a non-issue, publish to the gallery and the grant lapses; (2) that ownership is equally conditional on clean inputs, so a screenshot, sprite rip or piece of box art used as a reference image voids the ownership Pro grants AND walks an IP problem into the asset tree. The second is the live risk for anyone cloning an existing game's mechanics: the care taken to use no assets from the original has to extend to what gets fed to the generator as a reference. `docs/guide/licensing.md` covers Hunyuan3D/StableFast3D/RMBG in detail and does not mention Meshy at all; `docs/reference/skills.md:67-81` covers only key handling and triangle counts. A hosted service is exactly where a reader stops thinking about licences because they paid for it.

> ownership holds "provided you do not publish them publicly to the Meshy Community." Stay private and it's a non-issue. ... Pro's ownership is equally conditional on clean inputs ... a screenshot, sprite rip, or box art used as a reference image would void the ownership Pro grants *and* walk an IP problem into the tree. Worth having written next to the licence.

### Nothing holds numpy above rembg's floor after the gpytoolbox fix — scs walks it back to 2.2.6 and rembg needs >= 2.3.0

**high** &middot; belongs in `Dockerfile (the constraints heredoc at 66-74 and the canary at 260-264), and a line in docs/reference/docker.md's version chain`

The gpytoolbox trap is documented (Dockerfile 142-149: 0.3.0 calls np.Inf, one AttributeError fails the whole node pack, so install `--no-deps gpytoolbox==0.3.7` plus `scs`). The follow-on is not. The fix was verified live in the container at numpy 2.4.6, but the built image came out at numpy 2.2.6 — something in that layer, most likely `scs` pulling its own numpy, walked it back — and rembg declares `numpy>=2.3.0`. rembg's u2net is what removes the background inside Hunyuan3D and TripoSG, so if it is actually broken the image-to-mesh path is broken at its first step, silently. Two holes make it possible: /etc/pip-constraints.txt (Dockerfile 66-74) pins torch, torchvision, torchaudio, xformers, comfy-kitchen, gpytoolbox, transformers and diffusers but has no numpy line; and the 3D-Pack canary at Dockerfile 260-264 prints `numpy.__version__` without asserting it, and never imports rembg. Add `numpy>=2.3` to the constraints file and assert it (plus `import rembg`) in the canary so a downgrade turns into a red build instead of a broken first step.

> numpy came out at 2.2.6, not the 2.4.6 I verified against. Something in that layer — most likely `scs` pulling its own numpy — walked it back, and rembg declares `numpy>=2.3.0`

### Host RAM, not VRAM, is what actually kills a run - and octree resolution is the knob

**high** &middot; found independently by 2 auditors &middot; belongs in `docs/guide/troubleshooting.md (a second OOM section), README.md and docs/guide/install.md requirements`

troubleshooting.md's OOM section is entirely about VRAM staging. Measured on a 31GB box with an RTX 4070 (16GB): a generation transiently reaches ~25GB RSS with available RAM dipping to ~2GB, and the Linux OOM killer took the server with `Killed process 842151 (python) anon-rss:23735028kB`. Low-VRAM offload does not remove the pressure, it moves it - it parked 23.7GB of paint-model weights in host RAM on a box already 24GB deep into swap. Settings decide it: 50 steps at octree 340 is much heavier than 30 steps at octree 256, which is exactly why one person's run died where another's identical-looking test passed; lowering octree resolution back toward 256 cuts the peak noticeably. Practical advice from the corpus: close Docker/browsers before a 14-image batch. Related and unstated: /tmp is a 16GB tmpfs, so intermediates cached there cost RAM and fill silently (it reached 15GB and caused phantom test failures that moved between runs). The README's requirements name a 12GB GPU, 200GB of disk and 27GB for the image, and no host RAM figure at all.

> the failure mode on this box is host RAM, not VRAM - a generation transiently hits ~25 GB of 31 GB, which is what got the server OOM-killed earlier

### The TexGen graph ships the exact settings that OOM (8 views / 768px), while the docs claim its defaults are 6 / 512

**high** &middot; **fixed 2026-09-10** &middot; found independently by 3 auditors &middot; belongs in `workflows/api/mesh_texture_hunyuan3d21.json (node inputs + _comment), docs/guide/textures.md "Settings that matter", skills/asset-pipeline/SKILL.md, scripts/api_to_ui.py Note for mesh_texture_hunyuan3d21`

workflows/api/mesh_texture_hunyuan3d21.json node "2" ([Comfy3D] Load Hunyuan3D 21 TexGen Pipeline) has "max_num_view": 8, "resolution": 768 baked in. Those are the values that were measured to OOM on the 16GB card; 6 and 512 are what works. Every documented invocation silently papers over it by passing --set "TexGen Pipeline.max_num_view=6" --set "TexGen Pipeline.resolution=512" (docs/guide/textures.md, docs/guide/first-asset.md, scripts/asset_to_mesh.sh), and docs/guide/textures.md then prints a settings table headed "Default here | 6 | 512", which is not what the file contains. Anyone who opens the graph in the ComfyUI sidebar and presses Queue - the whole point of the editor conversion - gets 8/768 and an out-of-memory failure, and skills/asset-pipeline/SKILL.md lists the workflow (line 107) with no settings at all so an agent driving the skill does the same. Either change the stored inputs to 6/512, or say in the _comment and the api_to_ui Note that the shipped 8/768 defaults OOM at 16GB and must be dialled down.

> TexGen needs `max_num_view=6, resolution=512`; the defaults (8/768) OOM.

### cumm 0.8.2 in the pixi env produces ~100 nvrtc compile errors; the working pair is cumm-cu124 0.7.11 + spconv-cu124 2.3.8

**high** &middot; belongs in `scripts/postinstall.sh (alongside the comfy-kitchen pin) and docs/guide/troubleshooting.md`

One of the five UniRig bring-up failures, and the only one with no trace anywhere in /asset-engine. Rigging died with roughly 100 nvrtc compile errors because the isolated pixi env had resolved `cumm 0.8.2`; the pair that actually works is `cumm-cu124 0.7.11` + `spconv-cu124 2.3.8`, i.e. aligned to the versions the main environment already has. Nothing in the repo mentions cumm at all (grep for cumm/nvrtc across Dockerfile, docker-compose.yml, scripts/ and docs/ returns nothing); the only spconv reference is the Dockerfile's `sed -i 's/^spconv-cu126$/spconv-cu124/' requirements.txt` (line 136) and rig_units.sh's note that spconv 2.3.8 has no bf16 kernels. The related dependent lesson IS covered (precision fp16 not auto, rigging.md and troubleshooting.md), which makes the missing one look deliberate rather than forgotten. Belongs next to the comfy-kitchen pin, since both are "the pixi env resolved something the main env had already settled".

> 100 nvrtc compile errors | pixi env had `cumm 0.8.2`; the working pair is `cumm-cu124 0.7.11` + `spconv-cu124 2.3.8` | align to the main env's versions

### FLUX.1-dev and Krea [dev] are non-commercial (license:other) and are deliberately absent from this stack

**high** &middot; belongs in `/asset-engine/docs/guide/licensing.md (a "models deliberately not here" section) and the one-line licence list in /asset-engine/docs/reference/models.md`

`docs/guide/licensing.md` enumerates "the three that are not MIT or Apache" (Hunyuan3D, StableFast3D, RMBG-1.4) and `models.json` has no FLUX group at all, so a reader concludes anything else they bolt on is clear. FLUX.1 [dev] and FLUX.1 Krea [dev] are the quality leaders among open image models and are out on licence — `license:other`, non-commercial — which is not a close call for anyone shipping a paid game with ads and an IAP. It bites specifically because `checkpoints/Flux/flux1-dev-fp8.safetensors` (17GB) is a common thing to already have on disk, alongside `clip/clip_l.safetensors` and `clip/t5xxl_fp16.safetensors` — everything FLUX needs except the model — so plugging it in costs nothing and looks like a free upgrade. The FLUX that IS shippable is FLUX.1-schnell: Apache-2.0, 4 steps, very fast, ungated via `Comfy-Org/flux1-schnell`. Worth stating both, since "FLUX" is one word to a reader and two licences in practice.

> `checkpoints/Flux/flux1-dev-fp8.safetensors` (17GB) — **but FLUX.1-dev is `license:other`, non-commercial.** Given everything we established about shipping assets, I'd not build the pipeline on it.

### The concept-edit skill never mentions denoise, the one setting that decides whether the edit works

**high** &middot; **fixed 2026-09-10** &middot; belongs in `skills/concept-edit/SKILL.md (a new "Denoise is the control, not the prompt" section)`

grep -c denoise skills/concept-edit/SKILL.md returns 0. The skill has a long prompt-craft section (name the side by position, be explicit about singular, end with a keep-list) and a "Why 20 steps and not the Lightning LoRA" section, but not one word about the setting that was established as the actual control. The finding it is missing: at denoise 1.0 the model re-diffuses everything and its own style prior wins, and no negative phrasing in the prompt overrides it - "NOT cartoon, NOT flat plastic, NOT a clay render" was written three different ways at 1.0 and returned flat cartoon every time. An agent following this skill will add more prompt words, which is the documented failure. Carry the measured ladder across from docs/guide/concept-art.md: 0.55 and 0.70 near-identical to source, 0.85 painterly kept and clutter genuinely cut, 0.93 clean game-ready forms, 0.97 already flat vector on busy sources, 1.0 flat vector always.

> Negative phrasing in an edit prompt is weak; the sampler setting is the actual control. That's now documented in the workflow and I'll add it to the `concept-edit` skill.

### The UV atlas shatters on a dense mesh, and the result reads as confetti

**high** &middot; belongs in `docs/guide/textures.md ('Judging a texture' list), with a pointer from docs/guide/decimation.md#texturing-undoes-your-decimation`

The single most expensive texture failure in the corpus, and it is absent from docs/guide/textures.md. Auto-unwrapping a ~60,000-face organic mesh shatters it into thousands of tiny charts: each island gets a handful of pixels, every island boundary is a seam, and the multiview bake disagrees across neighbouring islands. You get recognisable fragments (plates, spines) surrounded by noise and inpainted filler. It is the UV unwrap, not the paint model - so more views or a bigger resolution will not fix it. It gets worse with density: `--no-reduce` at octree 384 means texturing a ~700k-face mesh. The lever is fewer faces BEFORE texturing, plus more camera views. Note this sits in direct tension with the repo's current standing advice ('Decimate after texturing, not before'), which is right about face counts and wrong about a dense input - both halves need stating together.

> The problem is the UV unwrap, not the paint model. Auto-unwrapping a 60,000-face organic mesh shatters it into thousands of tiny charts

### Height normalisation: the game has a scale convention and the mesh does not

**high** &middot; belongs in `docs/guide/meshes.md (a new 'handing the mesh to a game' section), cross-linked from skills/asset-pipeline/SKILL.md stage 3 and docs/guide/first-asset.md step 7`

Nothing in /asset-engine tells you to normalise a finished model's height before handing it to an engine. A converter shipped models 1.98 units tall when the game's convention is exactly 1.150 units, centred on y=0 - confirmed across lord_salt, lord_panacea, unit_rogue and homunculus_a. A figure 1.7x too tall overflowed its sprite canvas: heads cropped in the portrait chips, and the Sulfur Lord towering over the Grand Athanor. The fix is to normalise height and centre on the origin at export, then verify every converted model reports the same height (all 12 were re-converted and verified at 1.150). What makes this expensive to find is that render_sheet.py already 'normalise[s] into a unit box centred on the origin' for rendering, so every sheet looks correct while the shipped model is wrong - the error is invisible in exactly the artefact the docs tell you to check.

> My converter shipped models 1.98 units tall when the game's convention is exactly 1.150, centred on y=0 ... A figure 1.7x too tall overflowed its sprite canvas, which is why heads were cropped in the portrait chips

### Buildings inherit a diorama base plate from the concept art; frame them by their ground footprint

**high** &middot; belongs in `docs/guide/meshes.md (handing the mesh to a game), and a caution in docs/reference/workflows.md next to preset_concept_building.json`

Isometric building concepts are painted as dioramas on a plinth (preset_concept_building.json literally prompts for 'a small self-contained diorama'), and the generated mesh inherits that plate - which double-draws against ground the game's tiles already provide. Bounding-box normalisation is the wrong fix for a building. What worked: take the vertices in the lowest 6% of the mesh, scale that patch to exactly one tile (buildingPlateCover = isoTileW / buildingDrawSize) and put its centre on the anchor; grow the sprite frame taller than wide to hold spires (buildingSpritePxTall = 224 against a 64px-wide tile); and make the map's destination rect follow the sprite's own aspect, or square procedural fallbacks come out distorted. A test measured all twelve building meshes against the frame - the base spans the tile by construction and nothing overruns its headroom.

> they carry the diorama base plate from the concept art, which the game's tiles already provide ... takes the vertices in the lowest 6% of the mesh, scales that patch to exactly one tile

### The one-queue txt2mesh graphs OOM on a 16GB card

**high** &middot; **fixed 2026-09-10** &middot; belongs in `workflows/api/txt2mesh_sdxl_hunyuan3d21.json and txt2mesh_qwen_hunyuan3d21.json _comment, docs/reference/workflows.md base-graph table, docs/guide/meshes.md generator table`

The repo ships txt2mesh_sdxl_hunyuan3d21.json and txt2mesh_qwen_hunyuan3d21.json, and describes them as 'The same, the older way' and 'Convenient but committing'. The measured result is stronger than that: the combined SDXL+Hunyuan graph was tested and OOMs on a 16GB card, because SDXL and the Hunyuan pipeline cannot both be resident - the two-step path is what actually works, and it is what the skill does anyway. mesh_texture_hunyuan3d21.json's _comment already records the sibling case ('loading ShapeGen and TexGen in one graph exceeds 16GB VRAM'), so the same warning is simply missing from the two graphs where it was actually measured. The Qwen variant is the more likely trap now, since its fp8 UNet is 19GB and already offloads constantly on 16GB by itself.

> I tested the combined `txt2mesh_sdxl_hunyuan3d21.json` and it **OOMs on your 16GB card**: SDXL and the Hunyuan pipeline can't both be resident.

### TripoSG is shape-only: it returns vertex colours, not a texture map - so the MIT route ships untextured

**high** &middot; **fixed 2026-09-10** &middot; belongs in `docs/guide/meshes.md generator table and docs/guide/licensing.md#a-route-with-no-conditions-at-all`

meshes.md sells TripoSG as 'Clean watertight shapes. MIT, ships anywhere. The safe default' and never says it produces no texture map. Verified in the corpus: a TripoSG salamander came out at 2,500 faces, untextured, returning vertex colours rather than a texture map. The consequence is bigger than the fact: licensing.md's 'route with no conditions at all' is 'Qwen-Image or SDXL, then TripoSG or TripoSR, then decimate, then UniRig or mesh2motion, then CC0 clips' - a chain with no texture stage in it, because the only texture generator in the stack is Hunyuan3D TexGen, which carries the EU/UK/South Korea clause. A reader following the clean route will get to the end and find a grey model, or unknowingly reintroduce the territorial licence at the texture step.

> TripoSG is shape-only, it returns vertex colours rather than a texture map

### Deriving the spine from skeleton geometry: an arm is longer than a neck

**high** &middot; belongs in `docs/guide/rigging.md#bone-names-are-not-human-readable and docs/guide/animation.md#deriving-cycles-automatically`

rigging.md and animation.md both give the derivation heuristic as 'the spine is the chain that rises, and the arms are the two chains branching off near the top'. That is precisely the rule that failed: the first attempt followed an *arm* as the spine, because an arm is longer than a neck. The working rule is to follow whichever child stays nearest the centre line. The rest of the derivation that did work: the root is the bone with no parent, the legs are the two chains descending furthest, the arms are the two branches running outward. It is necessary because bone counts differ per figure (47 for the warrior, 28 for an earlier rig) and every name is bone_N. The repo currently documents the broken version of the heuristic as if it were the answer.

> First attempt followed an *arm* as the spine, because an arm is longer than a neck; now it follows whichever child stays nearest the centre line.

### POST /free between the image stage and the mesh stage — the half of /free that does work

**high** &middot; belongs in `scripts/run_workflow.py (a --free flag and its docstring), skills/asset-pipeline/SKILL.md stage 2, docs/guide/troubleshooting.md 'Out of memory during mesh generation'`

Generating concepts leaves the 19GB Qwen models resident, and the ShapeGen run that follows OOMs. ComfyUI's `/free` endpoint exists for exactly this and does release ComfyUI-managed diffusion models — after calling it only 5178 MiB remained held (that residue being 3D-Pack's own cache, which is the part /free cannot reach). The repo records only the negative half: scripts/asset_to_mesh.sh says 'POST /free does not release them', and no script or skill ever calls /free. Nothing tells an agent following skills/asset-pipeline/SKILL.md — which walks concept, then mesh, in one session on one server — to free the image model before stage 2. Add a `--free` flag (or an automatic free) to scripts/run_workflow.py and a line to the skill.

> OOM — the 19GB Qwen models were still resident from generating the lords. ComfyUI has a `/free` endpoint for exactly this; wiring it into the pipeline rather than restarting by hand

### Re-probe the swing axis on every new rig - and poses/_axis_probe.json is never mentioned

**high** &middot; belongs in `docs/guide/animation.md#which-axis-does-what and skills/pose-sheet/SKILL.md step 3`

animation.md and pose-sheet/SKILL.md state 'X bends forward and back, Z splays, Y twists' as settled fact, qualified only in a danger box ('It was X on one model here and Z on another'). What the corpus shows is a workflow: render a deliberate probe sheet on each new rig BEFORE authoring anything, because carrying the last rig's axes over produced a walk where 'frame 2 is sprawled, not walking' - a confident, well-rendered, wrong cycle. The repo already ships the probe file (poses/_axis_probe.json: a rest frame, bone_20 at [35,0,0], bone_20 at [0,0,35], bone_14 at [-60,0,0], bone_2 at [25,0,0]) and it is referenced in no document, no skill and no script - grep for 'axis_probe' across the repo returns nothing.

> Probing which axis actually swings a leg on *this* rig, rather than assuming the axes from the earlier 28-bone one

### The Hunyuan shape workflow's _comment states the opposite of what was measured

**high** &middot; **fixed 2026-09-10** &middot; belongs in `workflows/api/img2mesh_hunyuan3d21.json and workflows/api/txt2mesh_sdxl_hunyuan3d21.json, the closing sentence of each "_comment"`

workflows/api/img2mesh_hunyuan3d21.json and txt2mesh_sdxl_hunyuan3d21.json both end their _comment with 'Keeping the pipeline resident costs VRAM; ComfyUI evicts it when it needs to.' It does not. 3D-Pack keeps its pipelines in its own cache outside ComfyUI's model management, which is precisely why 5178 MiB stayed held after /free and why asset_to_mesh.sh has to restart the container twice per batch. The file the reader is most likely to open contradicts the script header that got it right, and the reassuring version is the wrong one — it invites exactly the interleaved shape/texture loop the rest of the docs forbid.

> 5178 MiB still held after `/free` — because **3D-Pack keeps its pipelines in its own cache, outside ComfyUI's model management**, so `/free` can't reach them. And `auto_cleanup: false` ... means they're never released.

### Requirements say 12GB; every measured failure is on a 16GB card

**high** &middot; **fixed 2026-09-10** &middot; belongs in `README.md Requirements, scripts/doctor.py check_gpu() warn string, docs/guide/install.md`

README.md:148 says 'A CUDA GPU with 12GB or more', and scripts/doctor.py:111 repeats 'mesh generation needs a CUDA GPU with 12GB or more'. The entire pipeline was developed and every OOM measured on an RTX 4070 16GB (15.7GB usable) with 31GB of host RAM, and the shipped defaults still OOM there — the LoRA dequantize spike, TexGen at 8/768, both pipelines in one graph, a 19GB Qwen model that offloads constantly. A 12GB card is not a tested configuration and would fail at more places, not fewer. The docs should name the reference machine so every number in them is anchored, and state 16GB as the tested floor.

> GPU is an RTX 4070 (16GB) with ~5.8GB currently free ... peak VRAM 12.1 GB of 15.7

### The two end-to-end txt2mesh graphs OOM on 16GB and are listed with no memory caveat

**high** &middot; **fixed 2026-09-10** &middot; belongs in `workflows/api/txt2mesh_qwen_hunyuan3d21.json and txt2mesh_sdxl_hunyuan3d21.json "_comment", the matching NOTES entries in scripts/api_to_ui.py, and the base-graph table in docs/reference/workflows.md`

txt2mesh_sdxl_hunyuan3d21.json was tested end to end and OOMs on a 16GB card: SDXL and the Hunyuan pipeline cannot both be resident. txt2mesh_qwen_hunyuan3d21.json is the same shape with a 19GB model instead of a 7GB one. docs/reference/workflows.md lists both in its base-graph table ('Prompt to concept to mesh in one queue'), and both _comments argue against them only on workflow-economy grounds ('convenient but committing', 'kept for comparison') — neither says they will not fit. The two-step path is not merely tidier; on this hardware it is the only one that completes.

> I tested the combined `txt2mesh_sdxl_hunyuan3d21.json` and it **OOMs on your 16GB card**: SDXL and the Hunyuan pipeline can't both be resident. The two-step path is what actually works

### Normalise characters, but not creatures, buildings or weapons - and record which is which

**high** &middot; belongs in `docs/guide/meshes.md, same section as the height convention; worth a line in skills/asset-cleanup/SKILL.md so sources.json records it`

The other half of the height-normalisation rule, and the half that is destructive if you get it backwards: normalising every asset flattens the relative scale that makes a bestiary read. In the shipped set, units and lords are height-normalised; creatures, buildings and weapons keep their sheet scale 'so a chimera still looms over a salamander'. The convention has to be written down per folder next to the assets, because nothing in a .glb says which rule was applied to it, and a later batch re-convert will silently apply the wrong one.

> which folders are height-normalised and which keep sheet scale. Creatures, buildings and weapons keep theirs so a chimera still looms over a salamander

### docs/guide/icons.md carries no icon prompt and no icon negative

**medium** &middot; belongs in `docs/guide/icons.md (a "Writing an icon prompt" section, the way terrain.md has one)`

The page covers cutting (flood fill from the corners, drop islands touching the canvas edge, feather the alpha, trim to ink then pad) and where to stop, but shows no prompt at all — and the cutting rules are only safe because of what the prompt guarantees. The recipe exists but only in scripts/build_presets.py's `fallback_style["icons"]` and in the 57 files under prompts/icons/: "One object only, centred in the frame with clear space around it, seen straight on. Painted storybook illustration with clean readable shapes and a bold silhouette, warm even lighting from the upper left, no cast shadow. Flat plain mid-grey background, empty." Also unstated in the docs: the icons folder deliberately ships no _style.txt (the look is stated once in build_presets.py and every prompt repeats it inline), the canvas is 1024x1024 square, icons read at 20px want "a bold dark silhouette, strong contrast, thick forms that hold at small sizes" (prompts/icons/vigour.txt), and the negative is its own list unlike the character one — photograph, photorealistic, 3d render, glossy plastic, drop shadow, cast shadow, ground plane, table, hand, person, text, letters, numbers, watermark, ui frame, button, border, circle badge, multiple objects, gradient background, vignette, blurry, cropped, cut off.

> the rule that works is dropping islands that touch the canvas edge, since the prompt puts the subject centred with clear space and it never does

### octree_resolution, steps and guidance_scale on the shape node are unexplained, and raising octree is what tips a run into OOM

**medium** &middot; **fixed 2026-09-10** &middot; found independently by 2 auditors &middot; belongs in `workflows/api/img2mesh_hunyuan3d21.json _comment (and img2mesh_triposg.json, which has none), docs/guide/meshes.md "Face budgets" or a short settings table`

img2mesh_hunyuan3d21.json ships steps: 30, guidance_scale: 7.5, octree_resolution: 256 and its _comment covers only the licence and auto_cleanup; txt2mesh_qwen_hunyuan3d21.json and txt2mesh_sdxl_hunyuan3d21.json carry the same values; img2mesh_triposg.json has guidance_scale 7.0, num_inference_steps 50 and flash/hierarchical/dense octree depths of 9/9/8 with no _comment at all. Nothing in docs/ or skills/ mentions octree_resolution. The measured cost, on the same weights on this box: 30 steps at octree 256 is ~20s at 5.6 GB peak VRAM; at 50 steps and octree 340 a run peaks at 12.1 GB of 15.7 GB with transient host RSS around 25 GB of 31 GB; octree 384 without decimation means texturing a ~700k-face mesh and takes several minutes each. The person who raised octree from 256 to 340 is exactly the person whose run then failed where the tested one passed, and lowering it back toward 256 "cuts the peak noticeably". Worth adding that the tight resource on a 31 GB box is host RAM, not VRAM - the first outage was the Linux OOM killer, "Killed process 842151 (python) anon-rss:23735028kB". (These numbers were taken on the standalone Hunyuan3D-2 app; the parameter and the model are the same, so flag the provenance if you carry them over.)

> Your settings - 50 steps, octree **340** - are heavier than the 256 I first tested with, which is why it failed for you where my test passed.

### setup.sh clones the node packs at whatever their default branch is today, while the image pins four exact commits

**medium** &middot; belongs in `scripts/setup.sh (lines 19-53) and docs/guide/install.md "Building from source"`

The Dockerfile pins COMFY3D_REF=9e8096e50c5bcf35e1f3e34c6ae06216101f8a11, UNIRIG_REF=69ee59dc459d2da7cb0291930c1f944886c31d7c, CAMERAPACK_REF=a58268fe5261d07ffeb93de26cc0d2558a5c0110 and MESH2MOTION_REF=11fe6b7aaa5eac60afa3d726389cd9dd870ed1f6, precisely because "main is a moving target and an image that builds differently on Tuesday is not a package", and both the Dockerfile (110-120) and docs/reference/docker.md (69-74) warn that drift between the image's compiled dependencies and the host's source is an ImportError with no obvious cause. But scripts/setup.sh — the documented way to build from source — sets `COMFY3D_REF="${COMFY3D_REF:-main}"` at line 22 and then never uses it: the clone loop at lines 45-53 does `git clone --depth 1 "$url" "$dir"` with no checkout for any of the four packs (and a depth-1 clone could not check out an arbitrary commit anyway). So the `comfy` profile reproduces exactly the state the image exists to end, and the comment claiming the ref is kept in step is not true of the code. Either carry the four refs in setup.sh and do a real fetch+checkout, or say plainly in install.md that building from source tracks upstream HEAD and the pinned set exists only in the image.

### On the packaged profile api_to_ui.py writes to a folder the server does not read

**medium** &middot; belongs in `docs/reference/workflows.md "Editing graphs in the ComfyUI editor", docs/guide/troubleshooting.md, scripts/api_to_ui.py docstring`

docs/reference/workflows.md states flatly: "They then appear in the sidebar under Workflows, because the compose file mounts workflows/ as ComfyUI's user directory." That is true only of the comfy and comfy-local profiles, where docker-compose.yml has ./workflows:/app/user. The packaged profile - the README quick start, docker compose --profile packaged up -d - mounts the named volume comfy-user:/app/user instead and deliberately mounts no source, so a graph regenerated by scripts/api_to_ui.py into ./workflows/default/workflows/ on the host never reaches the running server. Worse, scripts/entrypoint.sh only copies a seed workflow when no file of that name is already there ([ -e "/app/user/default/workflows/$(basename "$f")" ] && continue), so recreating the container will not pick up an edited graph either. docs/reference/docker.md explains the named-volume mechanics but never draws this conclusion, and docs/guide/troubleshooting.md's "A workflow edited in the editor behaves differently from the file" sends the reader to api_to_ui.py without saying which profile that works on. The silent-no-op shape of this is the same trap the repo already warns about for bind mounts.

> converts the API graphs into the editor's own format and writes them to `workflows/default/workflows/`, which the compose file already mounts at `/app/user`

### HiDream was evaluated as the Qwen alternative and rejected — record why, and the one lead worth a bake-off

**medium** &middot; belongs in `/asset-engine/docs/reference/models.md (why the concept generator is Qwen), with the licence half in /asset-engine/docs/guide/licensing.md`

The docs justify Qwen-Image as the default on licence (Apache-2.0) and prompt adherence, but not against the obvious commercially-clean alternative, so the evaluation invites repeating. What the sweep found: HiDream-I1 is MIT and commercially clean — the Llama-3.1 text-encoder terms do not bite, because you are neither distributing nor training on the Materials, and the EU restriction people half-remember is a Llama 3.2 *vision* clause, not 3.1. It was still rejected: the same architectural bet as Qwen (an instruction-tuned LLM as text encoder), older, heavier, a dead LoRA/ControlNet ecosystem, and independent 2026 comparisons put Qwen ahead on prompt following. Decisive for this pipeline: its distilled variants run at cfg 1.0, where the negative prompt is inert — and the negative prompt is most of how a plain background and clean silhouette get enforced here (the same trap already documented for `txt2img_qwen_fast`). The one genuine lead: HiDream-O1-Image, 8B, MIT, fp8 at 8GB — small enough to be actually resident on a 16GB card rather than offloading, a different proposition from I1 and worth a real bake-off rather than a blind switch.

> **HiDream-I1** is MIT and commercially clean (the Llama-3.1 encoder's terms don't bite ... the EU restriction people remember is a Llama *3.2* vision clause) ... Its distilled variants run at cfg 1.0, so the negative prompt is inert, and the negative prompt is most of how you enforce a plain background and clean silhouette.

### The ground docs still say the shipped materials are 1024px, but the measured settle was 512px at four tiles per repeat

**medium** &middot; belongs in `docs/guide/terrain.md ("Scale is set by how big things in the texture should look") and docs/guide/ground-and-relief.md (the same section); consider a note on scripts/make_seamless.py's --size`

docs/guide/terrain.md ("Pay for texel density with resolution instead, which is why the materials are 1024 pixels rather than 512") and docs/guide/ground-and-relief.md ("the materials are 1024px, not 512") both assert a size the final measurement walked back. The arithmetic they teach argues against them: at four tiles per repeat a repeat spans about 256 device pixels, so 512 texels is already about one texel per pixel and 1024 buys nothing — the set weighed 5.0 MB at 1024 and 1.6 MB at 512 with scale and detail both reading correctly. The missing rule is the general one: feature size is the texture's own proportions times the repeat, resolution only buys sharpness and only up to roughly one texel per pixel, so match the material size to the repeat. The intermediate failure is worth keeping too — three tiles per repeat squeezed a 1024px texture into 192 device pixels, a 5:1 minification that made everything soft: "the bottom is smoother, not finer", features shrink and the detail goes with them. Generating at 1024 (and make_seamless.py's `--size 1024` default) is still right; shipping at 1024 is what is not.

> Four tiles per repeat with 512px textures gives 256 device pixels against 512 texels: scale reads right, detail survives, and the materials now weigh **1.6 MB instead of 5.0 MB**.

### docs/reference/docker.md's "chain" omits five of the eight constraint pins and every error string that names them

**medium** &middot; belongs in `docs/reference/docker.md`

The reference page explains driver -> CUDA 12.4 -> py3.11/torch 2.6.0 -> ComfyUI v0.30.2 -> comfy-kitchen, and quotes the `infer_schema(func): Parameter kernel_size has unsupported type list[int]` failure. It stops there. The constraints file it points at also pins gpytoolbox==0.3.7, transformers==4.57.6 and diffusers==0.38.0 (plus the loose `huggingface-hub>=0.36,<1.0` alongside), and each has a specific failure behind it that only exists as a Dockerfile comment: gpytoolbox 0.3.0 calls `np.Inf`, removed in NumPy 2.0, and that one AttributeError fails the import of the ENTIRE node pack, not just StableFast3D; free resolution installs transformers 5.x, which calls `safe_open(..., backend=)` — an API in no safetensors release — and dies loading any diffusers pipeline; diffusers 0.40 wants huggingface-hub >= 1.23 while transformers 4.x caps it below 1.0. A reader who only has the docs site (and the site is what README points at) will `pip install -U transformers` inside the container and lose an afternoon. A table of every pinned line with its one-sentence reason and its exact error would close it.

> transformers 5.16 is calling a `safetensors` API that doesn't exist in any release. Pinning transformers to 4.x — which also satisfies ComfyUI's `>=4.50.3`

### "Naming a thing in the positive prompt summons it" never reaches the guide or the skills

**medium** &middot; belongs in `docs/guide/concept-art.md ("What a good prompt for this pipeline says"), skills/asset-pipeline/SKILL.md (stage 1 rules)`

The rule lives only in scripts/generate_lords.sh's header comment and in the Note text hard-coded in scripts/api_to_ui.py (which surfaces in the ComfyUI editor). docs/guide/concept-art.md's "What a good prompt for this pipeline says" lists four things and never states it; skills/asset-pipeline/SKILL.md's three load-bearing rules do not include it either. The evidence is specific: writing "no ragged tatters, no tears, no frayed threads" in the positive prompt produced a MORE tattered coat than saying nothing at all, across repeated attempts. The fix has two halves, both worth stating: describe the wanted state positively (prompts/lords/_style.txt's "a long coat or robe of large flat panels ending in a smooth even curved hem… The costume is pristine, freshly tailored and immaculate, as if newly made"), and put the forbidden words only in the negative — which forces txt2img_qwen.json at 20 steps and cfg 4.0, since txt2img_qwen_fast.json runs at cfg 1.0 where the negative box is inert. That is 130s per image instead of 33s, and the corpus records it as worth it.

> Adding "no tears, no rips, no frayed threads" made it *more* tattered — naming a concept summons it regardless of the negation.

### Atlases: how many models share a sheet, at what resolution, and when it stops holding

**medium** &middot; belongs in `docs/guide/textures.md (a new 'atlases and sharing' section), cross-referenced from docs/guide/decimation.md#budgets-in-this-pipeline`

The word 'atlas' does not appear anywhere in /asset-engine outside cut_icon.py's flood-fill islands, yet atlas policy is what decides whether a batch of assets is 400KB or 20MB. Real measured numbers from a shipped set: 8 lords at ~6k faces sharing one 1024px atlas (442KB) gives each roughly a quarter of that in effective resolution - it holds up at 300px on screen and would want 2048 if a lord were ever drawn larger. Per-figure atlases were 12k faces against 1024px each. A basilisk at 8,058 triangles carried its own 2048px atlas. The whole set, by category: units 4 at 12k with one 512px each; creatures 5 at ~12k sharing one; homunculi 3 at 12k sharing one; buildings 7 at ~12k sharing one; weapons 7 at 8k sharing one; lords 8 at 6k sharing one. Also worth recording: shared-atlas OBJs ship with no .mtl files (UV reference only), and a loader has to resolve the shared sheet by convention because most models have no texture of their own name.

> all eight share a single 1024px atlas (442 KB), so each Lord gets roughly a quarter of that in effective resolution. It holds up at 300px here, but if the unit sheet ever shows a Lord larger, that atlas will want to be 2048.

### "Simplify" alone reads as "delete": the guide teaches the denoise number but not the prompt shape

**medium** &middot; **fixed 2026-09-10** &middot; belongs in `docs/guide/concept-art.md ("Simplifying art you already have"), skills/concept-edit/SKILL.md`

docs/guide/concept-art.md's simplify section gives the denoise cliff table and nothing about how to write the instruction, so the first failure mode looks like a denoise problem and is not one. Pass 1 of the unit simplify stripped the character to featureless brown clay; what recovered it was naming the keeps explicitly — the glowing purple orb in its brass ring as the focal point, warm aged brass and gold, deep purple cloth, brown leather gloves and boots NOT grey, the same face, hair, pose and plain light grey background — plus an explicit floor ("do NOT become flat untextured plastic, NOT a smooth grey toy, NOT cartoon, NOT a clay render"). The repo's own prompts already encode the working shape as three labelled blocks — REMOVE / SIMPLIFY / KEEP (prompts/lord_simplify.txt) — and that shape is the lesson: an edit prompt that only says what to remove gets read as permission to remove everything, including the rendering itself.

> **"simplify" alone reads as "delete"**. It stripped the character to featureless brown clay. Only naming the keeps explicitly — orb, brass, palette, material contrast — and adding negative instructions ("do not flatten into plain untextured plastic") pulled it back.

### Nothing warns that the building style's diorama base plate becomes geometry you then have to crop

**medium** &middot; belongs in `docs/guide/concept-art.md ("Shape of the canvas" / the building style) and/or docs/guide/meshes.md`

prompts/buildings/_style.txt asks for "a small self-contained diorama seen from above at a 45 degree angle… stone foundations", and docs/guide/concept-art.md endorses the landscape canvas for it (1472x1104) without saying what the plate costs downstream. In the project this came from, the generated buildings arrived in-game standing on the concept's diorama base plate, on top of the ground tiles the engine already draws, and it had to be fixed after the fact in engine code — taking the vertices in the lowest 6% of the mesh, scaling that patch to exactly one tile, and anchoring its centre, with a taller-than-wide sprite frame (224px) to hold the spires. The rule to state in the concept guide: whatever the subject stands on in the picture is reconstructed as mesh, so either prompt it away (no base, no plinth, no ground patch) or plan to frame it, and decide before you generate twelve buildings.

> they carry the **diorama base plate** from the concept art, which the game's tiles already provide

### Nothing covers preparing existing artwork as an input: crop to one object, crop the labels off

**medium** &middot; found independently by 2 auditors &middot; belongs in `docs/guide/concept-art.md (a short "Using art you already have" section) or docs/guide/meshes.md`

skills/asset-pipeline/SKILL.md warns that "two figures make one fused blob" about images the pipeline itself generated, and the negatives carry "multiple figures"/"multiple objects", but no page covers feeding in art you already have. Two concrete traps: a reference sheet holding many objects (swords, shields, a potion on one page) produces a muddled blob from the mesh generators regardless of memory or settings, because the model expects a single centred object — crop to one item first; and labelled sheets carry text into the reconstruction, so the banners on a hero sheet (PANACEA, AETHER, MERCURY, AURUM, SALT, VITRIOL, ENTROPY, SULFUR) must be cropped off before the crop is used. This is the input-side half of the rule concept-art.md already states for generation ("a cropped figure becomes a cropped mesh").

> Your input image is a **sheet of many objects** (swords, shields, potion). The model expects a single centered object, so that prompt will produce a muddled blob regardless of memory. Crop to one item for a clean result.

### A test that derives the expected asset set from the code's own enums

**medium** &middot; belongs in `docs/guide/animation.md (end), or the same 'handing the mesh to a game' section as height normalisation`

The docs stop at 'render the sheet and look at it', with no coverage story for a set of assets. What caught the real misses was a test that derives the expected set from the enums and checks the bundle: every unit class, every non-NPC guild, every creature kind and every non-retired building type has a mesh; every unit class has every cycle at the panel count the painter actually draws (so a declared cycle cannot ship unposed); every lord has a portrait; every intro plate exists. A new enum member then fails a test instead of silently drawing the fallback. The reason it matters is that missing art is never a crash - a missing render 'silently falls back to the 128px sprite and just looks like mush', which is exactly the failure a human reviewer skims past.

> every `UnitClass`, non-NPC `Guild`, `CreatureKind` and non-retired `BuildingType` has a mesh; every unit class has every cycle at the panel count the painter draws ... so a declared cycle can't ship unposed

### `docker image prune -a` deletes the tagged athanor-comfy image — 26-27GB back over the wire

**medium** &middot; found independently by 2 auditors &middot; belongs in `docs/guide/cleanup.md, and a line in skills/asset-cleanup/SKILL.md`

`docker image prune -a` removes anything not used by a running container, which includes the tagged `ghcr.io/athanorgames/athanor-comfy:0.1.0` and `:latest`. They pull back from GHCR, but that is a 26-27GB download (and a local rebuild is an hour of CUDA layers). Prune by repository instead when clearing build clutter. The repo tells people to free space — skills/asset-cleanup/SKILL.md and docs/guide/cleanup.md are entirely about sweeping intermediates — without ever warning that the ordinary Docker space-reclaiming command is the expensive one here. The image size is stated in three places (README "27GB for the image", docs/reference/docker.md "27.5GB", publish_image.sh "26GB"), so the cost of losing it is already established; only the trigger is missing.

> Note that `image prune -a` also removes the tagged `athanor-comfy:0.1.0` and `latest` images. They are on GHCR so they pull back, but a rebuild locally is 26G of download.

### Every generation failing with "can't convert cuda:0 device type tensor to numpy" while 7GB of VRAM is held with nothing queued — restart the container

**medium** &middot; **fixed 2026-09-10** &middot; found independently by 4 auditors &middot; belongs in `docs/guide/troubleshooting.md`

Seen live: ComfyUI failed every generation with `can't convert cuda:0 device type tensor to numpy`, raised from its quantised-loading path, while holding 7 GB of VRAM with an empty queue. A container restart cleared it; the root cause was never established, and it is explicitly the first thing to try if it recurs. Worth recording precisely because it looks like a broken workflow or a bad checkpoint — the error names numpy, so a reader will go hunting through the numpy/gpytoolbox pins that this repo documents at length, which is the wrong tree. Not present anywhere in /asset-engine (grep for "device type tensor" returns nothing); troubleshooting.md's only restart advice is for the shape/texture VRAM staging problem, which has a different symptom.

> ComfyUI was failing every generation with `can't convert cuda:0 device type tensor to numpy` in its quantised-loading path, holding 7 GB of VRAM with nothing queued. A container restart cleared it. I don't know the root cause; if it recurs, that's the first thing to try.

### txt2mesh_sdxl_hunyuan3d21.json OOMs on a 16GB card and nothing says so

**medium** &middot; **fixed 2026-09-10** &middot; belongs in `workflows/api/txt2mesh_sdxl_hunyuan3d21.json _comment, scripts/api_to_ui.py Note for txt2mesh_sdxl_hunyuan3d21, docs/reference/workflows.md base-graph table`

The combined SDXL-plus-Hunyuan graph was tested and OOMs on a 16GB card: SDXL and the Hunyuan pipeline cannot both be resident. Its _comment is a verbatim copy of img2mesh_hunyuan3d21.json's licence and auto_cleanup text with nothing about memory; docs/reference/workflows.md lists it as "The same, the older way"; the api_to_ui Note says only "Kept for comparison. SDXL base is a photo model ... Prefer txt2mesh_qwen_hunyuan3d21." A user picks it for the reason given (prompt quality) and hits a memory failure instead. Note the distinction that makes this non-obvious: txt2mesh_qwen_hunyuan3d21.json is recommended and does work in one queue, so "one-queue graphs are fine" is the reasonable inference from the docs and it is wrong for this file.

> I tested the combined `txt2mesh_sdxl_hunyuan3d21.json` and it **OOMs on your 16GB card**: SDXL and the Hunyuan pipeline can't both be resident.

### Measured stage timings and peak VRAM for the mesh stages

**medium** &middot; belongs in `docs/guide/meshes.md generator table, and docs/guide/textures.md`

The generator table in meshes.md carries no timing or memory figures at all, and the README's flow diagram says only '3D shape ... about a minute'. Measured on an RTX 4070 (16GB): shape (Hunyuan3D DiT v2-0, 30 steps, octree 256) 20s at 5.6GB peak VRAM; texture (paint v2-0-turbo, 2048 square map) 92s at 10.4GB peak; a full textured-shape run 53s end to end once the staging was fixed. At the heavier settings (50 steps, octree 340) a 3-run soak averaged ~70s each - shape ~40s, texture ~15s - at 12.1GB of 15.7GB peak, with host RSS falling back to ~19-21GB between runs. TripoSR is ~10s on a 4070 Ti Super (already in its _comment). These are the numbers that let someone size a batch instead of discovering the ceiling halfway through one.

> | shape (DiT v2-0, 30 steps, octree 256) | 20 s | 5.6 GB |\n| texture (paint v2-0-turbo, 2048² map) | 92 s | 10.4 GB |

### mesh_rig_unirig.json's _comment tells you to restart the container, which does not work

**medium** &middot; belongs in `workflows/api/mesh_rig_unirig.json _comment (make it match docs/guide/rigging.md "The file list is snapshotted")`

The _comment says: "UniRigLoadMesh lists only files that existed when the container STARTED - comfy-env's isolated worker snapshots the node schema - so: copy your mesh into input/3d/, restart the container, then run. A file added afterwards is rejected with 'value_not_in_list'." The observed behaviour is that the list survives restarts, which is why the working method is to load through a slot that is already in the list. docs/guide/rigging.md and docs/guide/troubleshooting.md both say this correctly ("restarting the container does not refresh it"), so the file that a user is most likely to read while the failure is in front of them is the one that is wrong, and following it costs a container restart plus a second failed run.

> The rig list is frozen at container start and survives restarts, so new meshes are rejected. Each unit is loaded through a slot that *is* in the list - the node reads the file at run time.

### trimesh: the paint pipeline returns a SimpleMaterial with .image, not .baseColorTexture

**medium** &middot; belongs in `docs/guide/textures.md ('What comes out'), or as a docstring note wherever the repo documents reading maps back out of a textured mesh`

Anyone writing the atlas-extraction half of this pipeline hits this, and it bit twice in one session. The Hunyuan paint pipeline hands back a `SimpleMaterial`, which exposes `.image`; code reading `.baseColorTexture` crashes on it. The reason it survives testing is specific and worth stating: an offline test that loads from an already-exported GLB passes, because trimesh converts a GLB's material to PBR on load - so the attribute exists in the test and not in the live pipeline object. The failure is also expensive rather than cosmetic: the first bake's GLB was written and then saving its atlas crashed before the second trial ran, so a batch loses the runs after it, not just the map.

> the pipeline returns a `SimpleMaterial`, which exposes `.image`, not `.baseColorTexture` — my offline test passed only because it loaded from an exported GLB, which trimesh converts to PBR

### No measured VRAM or time budget per stage anywhere in the repo

**medium** &middot; belongs in `a 'What fits on the card' table in docs/guide/meshes.md, cross-referenced from docs/reference/models.md`

The measured figures: shape (DiT v2-0, 30 steps, octree 256) 20s at 5.6GB peak; texture (paint v2-0-turbo, 2048² map) 92s at 10.4GB peak; both pipelines resident is ~9GB of weights before activations, which is why whichever stage ran second hit the ceiling; a verified 3-run soak at 50 steps / octree 340 peaked at 12.1GB of 15.7GB, ~70s per asset (shape ~40s, texture ~15s). The OOM itself lands as a 384MB allocation failing inside diffusers/models/resnet.py with ~13.5GB already committed. The docs give times for the image workflows (~30s / ~130s / ~50s) and no VRAM number for anything, so there is no way to reason about whether a change will fit before running it.

> | shape (DiT v2-0, 30 steps, octree 256) | 20 s | 5.6 GB |
| texture (paint v2-0-turbo, 2048² map) | 92 s | 10.4 GB |

### The order of magnitude a scanned or hosted-generator asset has to come down by

**medium** &middot; belongs in `docs/guide/decimation.md (alongside the measured tables), referenced from docs/reference/skills.md Meshy note`

decimation.md measures a 40k generated mesh and a 642k scan, but never states the full bundle-level reduction, which is the number that makes the case. One asset went from 1,951,602 faces to 4,000; its OBJ from 192MB to 0.59MB; its texture from 4096px / 24MB to 512px / 67KB. That is roughly 500:1 on geometry and 350:1 on texture bytes. It pairs directly with the existing Meshy note ('exports are photogrammetry scale, often around two million triangles'), which currently ends by pointing at decimation.md without saying what the destination looks like.

> | Faces | 1,951,602 | **4,000** | / | OBJ | 192 MB | **0.59 MB** | / | Texture | 4096px / 24 MB | **512px / 67 KB** |

### doctor.py never asks how much of the card is actually free

**medium** &middot; belongs in `scripts/doctor.py check_gpu(), and the sample output block in docs/guide/install.md`

check_gpu() in scripts/doctor.py only asks whether Docker has the nvidia runtime registered. On the reference box another Python process was holding 9GB, leaving ~5.8GB free of 16GB — enough for the health check to say 'Ready' and for the first mesh run to OOM. A one-line `nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader` in the report, warning when free VRAM is under about 12GB, turns a mystifying OOM into a named cause before anything is queued. The same check should note free host RAM, which is the tighter of the two.

> GPU is an RTX 4070 (16GB) with ~5.8GB currently free — another python process is holding 9GB.

### Extra texture views must be multiples of 30 degrees - the model indexes its camera embedding by azim // 30

**medium** &middot; **fixed 2026-09-10** &middot; belongs in `docs/guide/textures.md 'Settings that matter', and the workflows/api/mesh_texture_hunyuan3d21.json _comment`

textures.md offers max_num_view as a free dial ('A tall thin subject benefits from more'), with no mention that the view azimuths are quantised. The paint model indexes its camera embedding by `azim // 30`, so views placed at anything other than multiples of 30 degrees are silently attributed to the wrong camera and the projections disagree where they overlap. This is the lever that was identified for fixing shattered/confetti texturing (fewer faces plus more views), so it belongs next to that fix rather than as a footnote.

> more camera views (multiples of 30° only — the model indexes its camera embedding by `azim // 30`)

### Why the 20-step Qwen graph takes 130s: a 19GB model on a 16GB card offloads constantly

**medium** &middot; belongs in `the workflow table in docs/guide/concept-art.md, and the `qwen` group row in docs/reference/models.md`

docs/guide/concept-art.md and docs/reference/workflows.md give the times (~30s fast, ~130s full) as if they were properties of the workflows. They are properties of this card: Qwen-Image fp8 is 19GB against 16GB of VRAM, so it offloads on every step. The Lightning route was measured at 131s -> 33s. Without the cause recorded, nobody can tell that the same graph on a 24GB card is a different proposition, or that the gap is memory rather than the 20 steps.

> Qwen is 130–140s per image, because a 19GB fp8 model offloads constantly on a 16GB card.

### After a push, check both tags actually landed — compose defaults to :latest

**low** &middot; found independently by 2 auditors &middot; belongs in `/asset-engine/docs/reference/docker.md, "Publishing the image"`

`publish_image.sh` tags and pushes both `:$VERSION` and `:latest`, so this is designed out of the happy path, but the failure it was designed against is worth stating: a version pushed by hand rather than through the script leaves `:latest` missing, and because `docker-compose.yml:73` defaults to `ghcr.io/athanorgames/athanor-comfy:latest`, the documented one-line install `docker compose --profile packaged up -d` then fails to pull for everyone. It happened: `0.1.0` went up at 19:05 UTC, digest `sha256:1b00af0f…`, with no `:latest` behind it. The practice is the same one the parent project learned about releases — a successful push is not a successful publish; look at the package page (or `docker manifest inspect`) and confirm both tags resolve to the same digest. The script's closing echo also notes the package starts PRIVATE and must be made public on the package page to be pullable without a token; that fact never reaches `docs/reference/docker.md` or `docs/guide/install.md`, where someone hitting an unauthorised pull would look.

> What was genuinely missing is `:latest`, because I pushed `0.1.0` by hand in the background rather than through `publish_image.sh`, which pushes both — and the compose file defaults to `:latest`, so `docker compose --profile packaged up -d` would have failed to pull.

### Curation should keep the instructive failures, named, next to the keepers

**low** &middot; **fixed 2026-09-10** &middot; belongs in `/asset-engine/docs/guide/cleanup.md`

`docs/guide/cleanup.md` teaches curate-the-keepers-and-sweep-the-rest, which is right for by-products but throws away the evidence for a setting. In practice the failures were kept deliberately, in named folders: `output/simplified/_weak_lords/` held the two failed 0.85 lord edits, kept purely so the 0.93 result could be compared against them; `output/lords_scratch/` held every raw generation including `aether_v1`/`aether_v2`, the two failures that taught the negative-prompt lesson. When the whole pipeline is settings that behave as cliffs (denoise 0.85 vs 0.93 vs 0.97), the rejected image at the neighbouring setting is what makes the chosen number defensible six weeks later — and `sources.json` records the path, not the picture. Worth one line saying an underscore-prefixed comparison folder is a legitimate keep, not scratch.

> `output/simplified/_weak_lords/` — the two failed 0.85 lord edits, kept for comparison; `output/lords_scratch/` — all raw generations including `aether_v1`/`v2`, the two failures that taught the negative-prompt lesson

### The CivitAI realism checkpoints are excluded on licensing grounds — say so on the licensing page, not only in a workflow comment

**low** &middot; belongs in `/asset-engine/docs/guide/licensing.md (a line under the SDXL section)`

Materially thinner rather than missing. The exclusion is recorded in the `_comment` of `workflows/api/img_refine_sdxl.json` ("the CivitAI realism checkpoints on this machine are NOT used here - their licensing is unclear and this pipeline ships game assets"), which is the last place a person deciding what to download will look, and it omits the specifics: the checkpoints in question were named ones — `cyberrealistic`, `intorealism` and the rest — CivitAI NSFW-oriented models with unclear licensing, wrong for a pipeline that ships game assets, and the deliberate substitute is SDXL base, which is OpenRAIL++ and commercially clear. `docs/guide/licensing.md` covers SDXL's OpenRAIL-M but never warns about the community-checkpoint route, which is the single most tempting quality upgrade a reader will reach for.

> **I deliberately didn't use the realism checkpoints on this box.** `cyberrealistic`, `intorealism` and the rest are CivitAI NSFW-oriented models with unclear licensing — wrong for a pipeline that ships game assets ... SDXL base is OpenRAIL++ and commercially clear.

### "Write sentences, not tag soup" is in the skill and the editor Note but not in the concept-art guide

**low** &middot; belongs in `docs/guide/concept-art.md ("What a good prompt for this pipeline says")`

skills/asset-pipeline/SKILL.md says it ("Write full sentences, not comma separated tags. Qwen is a text model. Tag soup wastes its strength, and SDXL habits produce worse results here") and so does the Note built by scripts/api_to_ui.py, but docs/guide/concept-art.md — the page a person reads to learn prompt writing — never mentions it, even though its own worked example is written in sentences. Worth carrying the same two supporting facts the skill has: Qwen holds a seven-clause description at once where SDXL base drops most of a long brief and renders a person in a costume photographed in a studio; and the canvas sizes that go with it (1328x1328 is Qwen's native 1:1 and fine for a prop, 1664x928 its 16:9, 1104x1472 the 3:4 default because a square crops a standing figure at mid-thigh).

> Write SENTENCES, not comma-separated tags.  Qwen is a text model and tag soup wastes it.

### /tmp is a 16GB tmpfs on this class of box — cached intermediates cost RAM and fill it silently

**low** &middot; belongs in `docs/guide/cleanup.md, and a note in scripts/decimation_report.py where it writes to /tmp`

On the build box /tmp is a 16 GB tmpfs, so anything cached there is charged against the 31 GB of host RAM rather than disk, and it fills without a disk-space warning. It reached 15 GB of generated meshes and intermediates and was silently breaking the game's `flutter test` with phantom failures that appeared to move between tests; sweeping it took /tmp from 15 GB to 248 KB. This matters here because host RAM is already the tight resource during generation (transient peaks near 25 GB of 31 GB, with the kernel OOM killer having taken the server down once), and because scripts/decimation_report.py writes its render probes to /tmp (lines 208, 229). Nothing in the repo mentions tmpfs; docs/guide/cleanup.md covers output/ and logs/ only.

> `/tmp` is a **16 GB tmpfs**, so anything cached there costs RAM and can fill silently. That's what was breaking `flutter test` with phantom failures that moved between runs.

### A generator installed by hand needs its own venv — TripoSG's requirements.txt pins numpy==1.22.3

**low** &middot; belongs in `docs/reference/docker.md (alongside the constraints table)`

TripoSG's `requirements.txt` pins `numpy==1.22.3`, which would have destroyed the working Hunyuan environment, so it was installed into a separate venv. Mostly historical inside the image, where TripoSG arrives through 3D-Pack under the shared constraints file — but it is the general rule the whole numpy/gpytoolbox/rembg episode is an instance of, and the repo's docs invite people to add generators (workflows/api/img2mesh_triposg.json ships as a first-class path). Worth one line wherever the constraints file is explained: a generator's own requirements.txt is not safe to run against this environment; give it a venv, or add its pins to /etc/pip-constraints.txt and rebuild.

> `requirements.txt` pins `numpy==1.22.3`, which would break the working Hunyuan environment — so a separate venv.

### Some features are load-bearing in a source image and no restyle removes them

**low** &middot; **fixed 2026-09-10** &middot; belongs in `skills/concept-edit/SKILL.md ("Rules that matter"), docs/guide/concept-art.md`

Neither docs/guide/concept-art.md nor skills/concept-edit/SKILL.md says that a restyle can fail on one element indefinitely. The ragged tabard hem survived five attempts, and the ragged coat tail survived all three passes at both 0.85 and 0.93, because it is deeply baked into the source image. The rule to record: when a feature survives two passes, stop raising denoise — a higher denoise flattens the whole picture before it removes that one thing. Run a targeted second pass at low denoise naming only that element, which is a small local change rather than a restyle, and describe the wanted replacement positively ("a straight clean hem") rather than negating the thing.

> Both still keep the ragged tabard hem, which I've now failed to remove across five attempts — it's clearly load-bearing in the source image.

### The free-memory endpoint is described but never named, and no script calls it

**low** &middot; belongs in `docs/guide/meshes.md and docs/guide/textures.md ("Memory, and why batches are staged")`

docs/guide/meshes.md, docs/guide/textures.md and docs/guide/troubleshooting.md all say "a request to free memory does not release it" without naming ComfyUI's POST /free, and no script in scripts/ actually calls it (only scripts/asset_to_mesh.sh's header mentions it, as "POST /free"). Naming it in the guide is worth one line, because /free does work for ComfyUI-managed models - it is what clears the 19GB Qwen weights left resident after a concept batch before a mesh run - and only fails to reach the 3D pack's own pipelines, where 5178 MiB stayed held after the call. As written, a reader concludes freeing memory never works and restarts for both cases.

> 5178 MiB still held after `/free` - because **3D-Pack keeps its pipelines in its own cache, outside ComfyUI's model management**, so `/free` can't reach them.

### Offload modes move the shortage from VRAM to host RAM rather than removing it

**low** &middot; belongs in `the comment above the command line in docker-compose.yml, and docs/reference/docker.md`

docker-compose.yml declines `--lowvram` for one reason ('3D-Pack keeps several pipelines resident and lowvram thrashes them'), but there is a second and harsher one: offload parks weights in system RAM. `--low_vram_mode` on the standalone Hunyuan app did fix the CUDA OOM and immediately put 23.7GB of anonymous RSS on a 31GB box with swap 24GB deep, and the kernel killed it. Offload also is not free even when it works — texture generation still needed ~6-7GB of headroom on the card. Worth stating wherever someone reaching for a low-VRAM flag will look, because on a 31GB host it converts a recoverable CUDA error into a process kill.

> `--low_vram_mode` fixed the VRAM OOM by parking the paint model weights in **system RAM** — which moved the pressure onto RAM, and something under containerd pushed it over

### A model small enough to stay resident in 16GB is a live option nobody wrote down

**low** &middot; belongs in `docs/reference/models.md, as a note on choosing a concept model for a 16GB card`

The model survey that settled on Qwen turned up one lead specifically on the residency axis: HiDream-O1-Image, 8B, MIT, fp8 at about 8GB — small enough to be actually resident in 16GB rather than swapping, which is a different proposition from HiDream-I1 and from Qwen's 19GB. It was flagged as worth a real bake-off rather than a blind switch. FLUX.1-dev and Krea-dev are the quality leaders and are out on licence (non-commercial), so they are not the escape route. docs/reference/models.md lists sizes but never mentions residency, and neither FLUX nor HiDream appears anywhere in the repo.

> **HiDream-O1-Image**, 8B, MIT, fp8 at 8 GB — small enough to be *actually resident* in 16 GB rather than swapping. That's a different proposition from I1 and worth a real bake-off, not a blind switch.

### An interactive mesh browser is the geometry check a still sheet cannot be

**low** &middot; belongs in `docs/reference/scripts.md ('Looking at results'), as a suggested addition next to render_sheet.py`

The repo's only geometry QA is render_sheet.py, which produces stills. What actually caught problems across a 61-mesh set was a browser viewer serving every OBJ and textured GLB with orbit and zoom, wireframe and clay modes, and - the load-bearing part - per-mesh triangle count, material swatches and world-unit dimensions displayed next to each model. The world-unit dimensions column is what makes a scale error visible at a glance, which is exactly the class of bug (1.98 units against a 1.150 convention) that four rendered stills hid completely.

> all 61 OBJs, orbit to spin, scroll to zoom, wireframe toggle, and per-mesh triangle count, material swatches and world-unit dimensions

### A second generator needs its own environment: TripoSG pins numpy==1.22.3

**low** &middot; belongs in `docs/reference/docker.md, in whatever section covers adding a node pack or generator`

The packaged image sidesteps this, but anyone adding a generator to the stack hits it, and the corpus has the exact pin: TripoSG's requirements.txt pins numpy==1.22.3, which would break a working Hunyuan3D environment - so it went in a separate venv. This is the same shape as the gpytoolbox/scs/numpy conflict the Dockerfile already fights, and the rule ('a generator that pins an old numpy gets its own environment, never the shared one') is worth stating once for people extending the image rather than only encoding it in pins.

> its `requirements.txt` pins `numpy==1.22.3`, which would have broken the working Hunyuan environment

### Raising max_num_view is constrained to multiples of 30 degrees

**low** &middot; **fixed 2026-09-10** &middot; belongs in `docs/guide/textures.md "Settings that matter"`

docs/guide/textures.md invites tuning the view count ("A tall thin subject benefits from more") and says only that more views "sometimes helps, and sometimes makes it worse by adding more meetings". The hard constraint is missing: the paint model indexes its camera embedding by azim // 30, so extra camera views are only meaningful at multiples of 30 degrees. Anyone raising max_num_view to a count that does not divide the circle into 30-degree steps is adding views the embedding cannot distinguish.

> Fewer faces before texturing plus more camera views (multiples of 30° only - the model indexes its camera embedding by `azim // 30`) is the untested lever.

### /tmp is a 16GB tmpfs on this box, so caching there spends RAM

**low** &middot; belongs in `scripts/decimation_report.py (write under output/ instead), and a note in docs/guide/troubleshooting.md next to the host-RAM entry`

On the reference machine /tmp is a 16GB tmpfs: anything written there costs host RAM — the resource that is already tight — and fills silently. It reached 15GB once and was producing phantom failures elsewhere on the machine that moved between runs; clearing it took /tmp from 15GB to 248KB. scripts/decimation_report.py writes every render it makes to /tmp (`/tmp/dec_ref.png`, `/tmp/dec_{target}.png`), which is a sweep across many face budgets on a machine where RAM is the binding constraint.

> `/tmp` is a **16 GB tmpfs**, so anything cached there costs RAM and can fill silently.

### weight_dtype=fp8_e4m3fn does not avoid the LoRA dequantize spike

**low** &middot; belongs in `workflows/api/txt2img_qwen_fast.json "_comment" and the 'Why 20 steps and not the Lightning LoRA' section of skills/concept-edit/SKILL.md`

The repo records the LoRA-on-fp8 OOM and the pre-merged checkpoint that solves it, but not the obvious workaround that was tried first and failed: setting `weight_dtype=fp8_e4m3fn` on the loader made no difference — the LoRA route OOM'd every time regardless. Recording the dead end is what stops the next person spending the round trip on it, and it is the reason a pre-merged checkpoint (rather than a loader setting) is the only fix for the edit model, which has no pre-merged variant.

> The LoRA route **OOM'd every time** — ComfyUI dequantizes the fp8 base to patch a bf16 LoRA, and that spike doesn't fit in 16GB. Setting `weight_dtype=fp8_e4m3fn` didn't help either.
