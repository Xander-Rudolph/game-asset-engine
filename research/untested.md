# Untested and undecided

This lists what was built on the `research/sfm-lipsync-daz` branch (2026-09-15 to 2026-09-18) but not tested for real, and the decisions left to the owner. Remove an item when it is tested or decided, and say what settled it in the commit.

## Owner decisions

Where CLAUDE.md's Owner decisions line names one, update it too.

| Decision | Options | Where it bites |
|---|---|---|
| Face budget | 18,000 or 48,000 | Docs and the mesh-budget skill against the seven mesh graphs. Then `scripts/build_presets.py --check` and `scripts/api_to_ui.py` |
| Meshy MCP server in `.mcp.json` | Keep, opt-in, or user scope and pinned | It starts unpinned for every installer. `meshy_output/` is not gitignored |
| Port 8188 bind | Every interface, or `127.0.0.1` | `docker-compose.yml:14`, `:88`. Anyone on the network can queue jobs and change node packs |
| ImageDream `commercial` flag | `yes` or `conditional (...)` | No OpenRAIL text found, and the SD 2.1 base page gave HTTP 401 |
| Daz EULA read date | The owner reads and records it | `86958.json` has `eula_read` null. `scripts/daz_library.py licence 86958 --eula-read YYYY-MM-DD` |
| Claude reading a Daz render | Allow, or keep refusing | The EULA's AI clause names chat models. `daz-genesis.md:451`, daz-figure steps 8 and 9, `daz_import_probe.py:341`. The 2026-09-18 sheets were deleted in that day's cleanup, so judging them needs a rebuild first |
| What `cleanup.py` protects | Settled 2026-09-18: music, icons, scenery, ground, lipsync and mpfb are protected; `output/daz`, `face_rig`, `mesh` and the `_` folders are not, and were deleted in that cleanup | `scripts/cleanup.py` lists both sets |
| Ground texture size | 1024 or 512 | `skills/ground-texture/SKILL.md:21` and `:31` |
| AGPL for a hosted image | Analyse it, or keep the warning | `docs/guide/redistributing.md` |
| TripoSG and TripoSR graphs | Keep or remove | `meshes.md` says neither works as shipped |
| Daz guards, What to build item 6 | `keep` licence override, `sources.json` licence fields, `run_workflow.py` refusal | Nothing stops a Daz render reaching TRELLIS. Refuse before `upload_image`, which runs even on `--dry-run` |

## Lip sync

- **Rhubarb in the container.** `doctor.py` checks files, not that the binary starts. Copy `tools/rhubarb` under `output/`, run `ldd` and `--version` via `docker exec`, and make doctor run `--version`. Cost: seconds.
- **The speech gate beyond one speaker.** Its thresholds rest on one speaker's lines, noise and two music clips, so real lines may be refused. Run `scripts/lipsync_cues.py <line> --text-file <line>.txt --force` on another speaker, a held vowel, TTS, music under speech, `-r phonetic` non-English, and MP3, Opus, M4A and AAC. Cost: minutes of CPU.
- **Thread non-determinism.** Quoted figures may not reproduce: runs give 85 or 87 cues on line 0001, the only one measured. Run `rhubarb -f json` ten times per line. Cost: minutes of CPU.
- **A person watching the sync.** Only frame order and labels were checked. Preview `share`, `midpoint` and `--text-only` timelines with `scripts/preview_lipsync.py`. Cost: needs the owner.

## Mouth sets

- **Other portraits and seeds.** The measured settings come from one portrait at seed 0. Run `scripts/make_mouths.py <portrait> --box X,Y,W,H --shapes XABCDEF --seed 1` on a new face and a 341x341 RGBA, then `scripts/compose_mouths.py --check`. Cost: a GPU job, about 23 min a set.
- **Weak shapes.** G and H play as A and C, and A matches X, so an "oh" gapes. Try a third wording and `--denoise 1.0` on `--shapes GH`. Cost: a GPU job.
- **Portrait sizes whose margin is an exact half-pixel.** `kept_region` rounds halves to the even margin; the node itself was measured going both ways on 14 probed sizes and matched that rule on 5, so no whole-number rule can follow it. When it parts, the piece is a pixel out in the margin and two in the side, which displaces an edit by 1.00 px at the frame's edges and 0.00 px at its centre. `halving_is_a_tie` names those sizes, 6,656 of the 525,625 whole portrait sizes from 300 to 1024 in both directions (1.27 per cent), and `to_portrait_frame` warns when one is used. Settle it by probing more sizes, or by avoiding them in `make_mouths.py`. Cost: a GPU job to probe, minutes to decide.
- **`make_mouths.py` failure paths.** `--timeout`, `--retries` and `--max-wait` never fired, and the crop pre-check ran only in comfyui-packaged, so a stuck job could hang the server. Try `--timeout 30`, `--max-wait 5` beside a Blender job, and `--dry-run` with `ASSET_ENGINE_CONTAINER=comfyui`. Cost: a GPU job.

## Render and faces

- **The Cycles path beyond the default camera and lights.** Cycles became `render_sheet.py`'s default on 2026-09-18, but every Cycles sheet so far is the default orthographic isometric framing at `--key 1.6` and `--ambient 0.22`. `--persp`, `--span`, `--flat` and non-default `--key` or `--ambient` have only ever been drawn by EEVEE, and the occlusion Cycles adds is exactly the thing a different camera or a stronger sun would change. Render one model through each flag on both engines and compare the lit surface and the alpha edge. Cost: minutes of GPU.
- **The adaptive sampling threshold, which is what really stops Cycles.** `--samples` is only a ceiling. `scene.cycles.adaptive_threshold` is 0.01 at factory settings, `use_adaptive_sampling` True and `adaptive_min_samples` 0 (read from bpy 4.5.9 in comfyui-packaged after `wm.read_factory_settings`, 2026-09-18), and `render_sheet.py` never sets any of the three, so the 128 sample default was chosen against a knob nobody has turned. Sweep the threshold at a fixed `--samples 128` on a 128 px cell, against the 2048 sample reference the sample sweep used, and say whether the knee moves. Cost: minutes of GPU.
- **`--denoise` below 64 samples.** Its `--help` says denoising is worth turning on below 64 samples, but the only measurement behind it is at 128, where it cost about 60 per cent more per cell and moved the lit surface by under a level in 255. Render 16, 32 and 64 samples with and without it and check the claim or cut it. Cost: minutes of GPU.
- **The wait before a Cycles render.** No run on record has printed its `waiting:` line, so `wait_for_machine` has never polled, and `--max-wait`, `--no-wait` and the unreadable-`docker top` path are all unexercised. Start a sheet beside a queued ComfyUI job, then again with `--max-wait 5`, and with `ASSET_ENGINE_CONTAINER` set to a container that is not running. Cost: seconds, plus a GPU job to queue.
- **A whole set re-rendered on Cycles.** The 11 per cent figure for mixing engines comes from one figure, and nothing in `output/sheets/` has been redrawn: all 71 files there were written before the default changed, so all of them are EEVEE (`find output/sheets -type f`, 2026-09-18). Re-render one set whole, then look at it as an atlas. Cost: minutes of GPU, then the owner.
- **A face-only row on Cycles, against `sheet_check.py`'s 8 level floor.** Two identical rows on Cycles changed 0 px (`render_sheet.py output/assets/alchemist_warrior/rig.fbx --poses frames:1,1 --angles 2 --size 128 --check`, 2026-09-18), so the floor is not swamped by path tracing noise, but the other half, how far a jaw or viseme row moves pixels on Cycles, was measured only on EEVEE. Render the MPFB viseme row on both engines at 128 px and compare. Cost: minutes.
- **`render_sheet.py` on awkward inputs.** Untried types may still end in a traceback. Try a float into an int prop, Basis in `@shape_keys`, linked collections, two view layers and light probes. Cost: minutes of CPU.
- **`face_rig.py` on other rigs.** Only articulationxl and MPFB rigs at scale 1 were jawed, so others may fail silently. `scripts/face_rig.py add-jaw input/3d/mixamo.fbx` with each `--front`, and `transfer-shapes` with `.obj` and `.glb` templates onto a 0.01 armature. Cost: minutes of CPU.
- **SIGALRM in the other scripts.** A leaked Blender holds RAM in a container OOM-killed before. Run `face_rig.py`, `bone_roles.py`, `normalise_mesh.py`, `transfer_weights.py` and `decimation_report.py` with `--timeout 1`, then `docker top` must show no `python3 -c`. Cost: seconds each.
- **A jaw and a role walk together.** A user following both guides cannot map a jawed `.blend`. `add-jaw --out alch_jaw.fbx`, `map`, compile `walk.json`, add a jaw rotate after compiling, then `scripts/render_sheet.py --check`. Cost: minutes of CPU.

## Bone roles

- **Roles on other rigs.** Neck and head could swap silently: the 0.25 head weight rests on seven rigs, and T-pose hands swing 0.051 of height, not 0.153. `scripts/bone_roles.py map` a mesh2motion, hip, unweighted and turned rig, and render a Mixamo walk. Cost: minutes of CPU.
- **`@shape_keys` and grounded feet.** No test rig had shape keys, and contact frames leave bone ends up to 0.100 above the floor. Render a compiled `@shape_keys` row on `human_game_engine.glb`, and `probe unit_warrior_walk.json --frame 1`. Cost: minutes of CPU.
- **The least rotation that shows.** `idle.json`'s "about 10 degrees" has no run, and `sheet_check.py` now passes shading-only changes. Render chest turns of 3, 5, 10 and 15 degrees at `--size 220 --check`, then cite or cut. Cost: minutes of CPU.

## MPFB

- **Other face packs, and skin.** visemes01 and faceunits01 never loaded, and every render is clay. Add `build --face-targets`, pinned system assets (CC0, 267 MB) and `render --materials` first. Cost: code, a download, minutes of CPU.
- **Licence records.** The face packs' CC0 and the extension's SPDX are in no register. Run licence-audit and add claims beside DAZ-093 and DAZ-095. Cost: minutes.
- **`mpfb_probe.py` guards.** `--name ../x` escapes `output/mpfb/`, and `wait_for_idle` ignores pending jobs. After a fix, `render --name ../x` must exit 2. Cost: seconds.

## Daz

- **Genesis 8, 8.1 and other products.** Genesis 8 statements are unmeasured, and every count rests on SKU 86958. Once downloaded: `scripts/daz_library.py install`, `scripts/daz_inventory.py /models/daz_library` (not `$MODELS_DIR`), `build --figure '<G8 .duf>'`. Cost: downloads, minutes of CPU.
- **A `.dbz` import.** Without one, two `_HD3` morphs logged Missing geonode, and on 2026-09-18 the clothes got 0 shape keys, so a character dial carries an outfit rigidly (57.25 mm) instead of reshaping it. `scene --fit DBZFILE` exits 1 at the figure import. The owner exports `Genesis 9.dbz` from Daz Studio beside each `.duf`; compare `scene --fit DBZFILE` with `g9_dressed_scene.json`. Cost: needs the owner and Daz Studio.
- **A hand-built shape transfer for the clothes.** The only alternative to a `.dbz` here. Not tried, not designed: Blender's own Surface Deform or a Data Transfer modifier from the body to each garment, then compare a dialled figure's outfit against its 57.25 mm rigid follow. Cost: code, minutes of CPU.
- **The rest of the library.** One preset of 6, two clothing items of 40, one hair of 27 and one pose of 87 were run, and no geograft or Toon figure. Run `scene` with another preset, a long garment and a seated pose. Cost: seconds of CPU each.
- **The morph sets nothing called.** `--morphs` accepts `anime` and `facsdetails`, and `bpy.ops.daz.import_standard_morphs()` was never called at all. Run `scene --morphs anime,facsdetails` and read the property counts. Cost: seconds.
- **dForce.** The pixie hair's 236,136 strand vertices follow no bone, draw 0 pixels and were never simulated, so hair only reads as its 1085-vertex cap. Decide whether to simulate, weight the strands to the head, or tell users to pick capped hair. Cost: needs a decision, then minutes of CPU.
- **A sheet with the Daz materials, cheaper than 64 EEVEE samples.** At the EEVEE default of 64, which was `render_sheet.py`'s default until 2026-09-18, the dressed figure came to 26.2 s a sample, no cell finished before the 1500 s alarm, and four cells at 128 px would be about 1.9 hours. Neither of the two ways out was tried: `scripts/render_sheet.py output/daz/g9_dressed_nosubsurf.blend --size 128 --engine eevee --samples 8`, and the same without `--engine eevee`, which now path traces on the card instead of rasterising on the CPU. Time both, then say what a materials sheet costs instead of offering clay by default. A Genesis figure has never been rendered on Cycles at all, in clay or with materials. Cost: minutes to hours of CPU.
- **A portrait through `render_sheet.py`.** It frames the whole subject, and lowering `--zoom` tightens the frame on the subject's centre, which on a standing figure is the waist, so every portrait here comes from the probe's own renderer. A head-aim option or a fixed camera does not exist. Cost: code.
- **These sheets beside a pipeline sprite.** Coverage and cell geometry were measured so they can be compared, but no side by side against a sheet in `output/sheets/` was run. Cost: needs the owner.
- **Gzip `.dsf` and `.duf`.** The note says Daz Studio writes gzip, but none of SKU 86958's 3847 files is, and a corrupt one raises `zlib.error`. Gzip `Genesis9.dsf` for `daz_inventory.py`, and `Genesis 9.duf` in a relative-linked `/models/daz_gz` for `build --library`. Cost: minutes of CPU.
- **`daz_library.py` for real.** Fixes ran on one part in a throwaway library, `save_record` keeps old licence keys, and a `.daz_library` symlink is followed. With `--library /tmp/dazlib`: install three zips, `verify --crc`, `uninstall --part 02`, reinstall, race two installs, fill a tmpfs. Cost: minutes.
- **`daz_import_probe.py` beyond one run.** Render numbers come from one option set, `DEFAULT_LIBRARY` ignores MODELS_DIR, and the host-side kill never fired. `build` with `--material-method BSDF` and `FBX_COMPATIBLE`, a Toon figure, Basic Wear (76 case-only references) and a wrong `--content-dir`; `pkill -STOP -f scripts/render_sheet.py` during `render --timeout 120`. The 2026-09-18 subcommands add their own: `scene --no-transfer`, `--set-dressed` with two dials, `--custom-bodypart Face`, a `--wear` path that does not resolve, and `verify --rig`/`--props` given by hand were none of them run. Cost: minutes of CPU each.
- **A person judging renders.** The only by-eye reading is Claude's, on clay, and no Genesis sheet has ever been opened by a person. The 2026-09-18 sheets were deleted in that day's cleanup, so this needs a rebuild: `scripts/daz_import_probe.py build --facs --subdivision off`, then `scene` for a dressed figure, then the clay and materials renders, and the owner opens them. Cost: needs the owner, about 25 min of CPU.
- **Exported visemes.** A game needs baked shapes, but the visemes are driver-driven. Not built: set each `facs_ctrl_v*`, `shape_key_add(from_mix=True)`, export glTF with morphs. Lip-sync's Genesis column can use `@props` now. Cost: minutes of CPU, once written.
- **The `cleanup.py` guard on a case-insensitive disk.** It ran only on Linux copies. On macOS or `chattr +F` ext4, `scripts/cleanup.py keep _test --concept <image> --model output/Daz/g9_cage.blend`. Cost: seconds.

## The MCP server

Built 2026-09-19 in `mcp/`: 23 tools over the protocol, 24 self-test checks, and Claude Code CLI 2.1.278 connected, called tools and shut it down cleanly.

- **Tools mapped from `--help` but never run through the server.** An argument named wrongly fails only when someone calls it: `bone_roles_map`, `bone_roles_compile`, `face_rig_add_jaw`, `decimation_report`, `normalise_mesh` and all three lip sync tools. Of the Blender group only `render_sprite_sheet` has run. Call each once through `python3 mcp/client_probe.py` or a client. Cost: minutes of CPU.
- **`run_graph` has never queued a real job.** Only `--dry-run`, so its wall-clock behaviour and the files it reports after a generation are unverified. `interrupt_job` and `free_models` were never run either, because both reach a shared server. Cost: a GPU job, and a moment when nobody else is using the card.
- **The compose service has never been started.** `docker compose --profile mcp config` resolves and the same flags were proved through `docker run`, but `init: true`, `restart: unless-stopped` and the compose-built image tag are read and not run. Cost: seconds, when the pipeline is idle.
- **HTTP mode has only been driven on the loopback.** No TLS reverse proxy, and the server has no authentication of its own, so it must not leave localhost until that is settled. Cost: an afternoon, plus a decision about who may reach it.
- **One client, one architecture.** Only Claude Code 2.1.278, only amd64. The idle timeout and `MCP_TIMEOUT` were not exercised, and `server/discover` was answered only to a hand-written client.
- **`bash` and `curl` are in the image for the shell scripts, and no tool that uses one has run.** Cost: minutes.
- **`DOCKER_GID` defaults to 126,** which is this host's socket group. On another machine the socket is a different group and the container cannot reach the daemon until `.env` says so.

## Pipeline scripts

- **`fetch_tools.py` on a real drop.** Resume was simulated locally, so a real drop may corrupt the `.part`. Kill `--download rhubarb` from a scratch copy with `timeout 3`, and rerun. Cost: seconds and a download.
- **Queue controls and restarts, live.** Only stubs were used, and a mistake ends someone else's job. In a reserved window, try `scripts/run_workflow.py --delete`, `--interrupt` and `--free`, and `scripts/asset_to_mesh.sh` with a job queued. Cost: needs the owner, GPU jobs, a restart.
- **`cleanup.py keep` on the real tree.** Provenance rows ran only in scratch trees. `scripts/cleanup.py keep <name> --concept <png> --source Qwen/Qwen-Image --licence Apache-2.0`, then read `sources.json`. Cost: seconds.
- **Unfilled `<<< ... >>>` slots.** `run_workflow.py` warns, then queues the placeholder. `--dry-run` a preset with `--subject` alone, then decide: refuse or strip. Cost: seconds.
- **Deprecated `SaveAudio` in `txt2music_acestep15.json`.** An update may remove it and break the music graph. Swap the node and run `scripts/api_to_ui.py`. Cost: seconds.
- **Two claims with no run.** The concept-edit skill says about 130 s where `concept-art.md:13` says about 90 s, and UniRig leaving long creatures under 2.0 units was read from code. Time one `img_edit_qwen` edit; rig `beast_chimera.glb`, then `scripts/normalise_mesh.py <fbx> --height 2.0 --check`. Cost: GPU jobs.

## Docs and skills

- **The Daz register.** It contradicts itself: DAZ-079 says 138 bones and DAZ-080 143, DAZ-049's 753 maps are 762 on disk, DAZ-086's counts differ and DAZ-091 is unchecked. Update it from the runs, then `npm run docs:build`. Cost: minutes.
- **Sentences stronger than their claims.** These outrun their registers: "Renders may ship" (daz-figure, `README.md:193`), `lip-sync.md:375`, `source-filmmaker.md:248` and `:288`, and `licensing.md:404`. Reword each to its claim. Cost: minutes.
- **Two review fixes.** Users could end others' jobs or strip notices: the Hunyuan3D `_comment` advises a restart with no `/queue` check, and `redistributing.md` omits condition (c) for nvdiffrast and Gaussian-Splatting. Add both, then `scripts/api_to_ui.py --check`. Cost: minutes.
- **`sheet_check.py`'s clipping hint points the wrong way.** `scripts/sheet_check.py:143` ends its clipping finding `Lower --zoom or raise --size`, but `scripts/render_sheet.py:382` sets `cam_data.ortho_scale = size * zoom`, so lowering `--zoom` clips harder and `--size` only changes the pixel count: on the dressed figure 220 px clipped by 9 pixels where 128 px clipped by 7, and `--zoom 1.35` is what cleared it. Reword the string to raise `--zoom`, then `scripts/render_sheet.py --check` on a deliberately clipped sheet. The docs that quote the finding already say the hint is wrong. Cost: minutes.
- **Meshy AI identifiers, its Privacy Policy, FLUX.1 schnell.** None was checked, yet `AUDIT.md:478` suggests schnell as the shippable FLUX. Dump a Meshy glTF's `extras` before and after `normalise_mesh.py`; licence-audit the rest. Cost: minutes, a Meshy account.
- **The `daz-figure` description against what it now does.** Its stages 4 to 7 dial, dress and pose a figure, but the frontmatter description and the five rows that describe it (`README.md:134` and `:193`, `docs/guide/claude.md:99` and `:202`, `docs/reference/skills.md:28`) still say only install, import and render the visemes, so "put an outfit on my Daz figure" may not reach it. Widening the description costs always-on tokens: measure with `claude --plugin-dir . plugin details game-asset-engine` before and after, then update every row. Cost: minutes.
- **Maintainer skills in a fresh session.** They help only if they load. Ask `claude` "I added a model to models.json, land it", and test licence-audit's import-blocking recipe in a fresh `docker exec` process. Cost: minutes.
