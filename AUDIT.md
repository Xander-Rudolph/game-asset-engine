# Documentation audit, 2026-09-10

Two audits ran against this repo: one over the Athanor game repo that this
pipeline was built for (`CLAUDE.md`, `DESIGN.md`, fourteen `tool/` script
docstrings, every workflow `_comment`, and the git history), and one over
**520 MB of Claude Code session transcripts** from four related projects,
distilled to the 144 paragraphs that state something learned the hard way.

97 lessons were already covered here. What follows is what was not.

Entries marked **fixed** were dealt with on the day; the rest are a backlog,
ranked by how much pain not knowing them causes.

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
