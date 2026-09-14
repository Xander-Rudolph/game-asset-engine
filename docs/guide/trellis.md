# TRELLIS

TRELLIS is MIT and carries no territorial clause, which makes it the choice for
a **shape** shipping into the EU, UK or South Korea. See
[licensing](/guide/licensing).

::: danger Its colour texture is another matter
The plain branch can return a coloured mesh, and it was run to find out whether
that texture could replace Hunyuan3D's paint. It can't in anything you sell: the
texture is baked through two libraries licensed for research and evaluation use
only. [What was run, what came out, and the licence text](#plain-trellis-was-run-the-colour-works-and-its-licence-does-not).
:::

```sh
scripts/fetch_models.py --download --group trellis
scripts/run_workflow.py workflows/api/img2mesh_trellis.json \
    --image input/concept.png --set 'save_path=mesh/asset.glb'
```

`img2mesh_trellis.json` uses the StableGen branch (Stable3DGen weights). It has
been run end to end: a 1104x1472 character concept on a plain grey background
produced a clean 48,000-face mesh in 29 seconds, with the background removed
automatically.

::: tip No cut-out needed
Beyond the licence, this is the practical advantage. The pipeline runs rembg
with the u2net model itself, so a plain grey background concept works directly.

TripoSG has no background removal step, but that is not the reason to pass it
over. In this install it does not produce usable meshes at all. A plain grey
background, a white one, a transparent cut-out, square framing and the non-flash
decoder all gave the same result: a cage of disconnected fragments instead of
the subject. TRELLIS made a clean, recognisable figure from the same grey
concept.
:::

The rest of this page is why there are two TRELLIS branches, why only one of
them ships as a graph, and what the other would need.

## Two TRELLIS branches that can't mix

Four nodes are registered, but they form two separate chains. They use different
pipeline types, so you can't mix parts of one with parts of the other.

| Branch | Loader | Generator | Pipeline type |
|---|---|---|---|
| Plain TRELLIS | `[Comfy3D] Load Trellis Structured 3D Latents Models` | `[Comfy3D] Trellis Structured 3D Latents Models` | `TRELLIS_PIPE` |
| StableGen | `[Comfy3D] Load StableGen Trellis Pipeline` | `[Comfy3D] StableGen Trellis Image To 3D` | `DIFFUSERS_PIPE` |

::: danger The type check won't protect you on the StableGen branch
`TRELLIS_PIPE` has exactly one producer, so on the plain branch ComfyUI rejects
wrong wiring before anything runs.

`DIFFUSERS_PIPE` is generic and has **fourteen** producers, including the TripoSG
and Hunyuan loaders. ComfyUI will let you wire a TripoSG pipeline into
`StableGen Trellis Image To 3D`, and the graph then fails when it runs instead of
being rejected when you queue it.
:::

## Which branch to choose

StableGen is the one that ships. The plain branch is not wired up, for the
reasons below.

### Plain TRELLIS: weights present, wiring awkward

The 3.1GB of weights are already on disk, and `fetch_models.py` reports the group
complete. Three things still stand between that and a working graph.

**The default `repo_id` ignores the weights you already have.** The loader passes
`repo_id` straight through, and the check for a local path is
`os.path.exists(f"{path}/pipeline.json")`. ComfyUI's working directory is `/app`,
so the default `jetx/TRELLIS-image-large` resolves to
`/app/jetx/TRELLIS-image-large/pipeline.json`, which does not exist. It then falls
through to a fresh Hugging Face download of the same 3.1GB you have.

Set `repo_id` to the absolute in-container path instead:

```
/app/custom_nodes/ComfyUI-3D-Pack/Checkpoints/Diffusers/jetx/TRELLIS-image-large
```

**Its image encoder is not the one in `models.json`.** The pipeline calls
`torch.hub.load('facebookresearch/dinov2', 'dinov2_vitl14_reg')`, which clones a
GitHub repo and pulls about 1.2GB into the torch hub cache. The `facebook/dinov2-large`
entry that `models.json` fetches is in Hugging Face transformers layout, is a
different variant with no registers, and **nothing in the pack loads it**. That
2.3GB is currently downloaded and unused. See
[the manifest bug](#the-manifest-and-what-was-wrong-with-it) below.

**`reference_mask` is a required socket with no producer in the house pattern.**
Every other image-to-mesh graph here feeds a `LoadImage` straight into the
generator. That cannot work here, and it fails twice over:

- On an image with no alpha, `LoadImage` returns a zeros mask shaped `[1,64,64]`
  against a `[1,512,512,3]` image, and the consumer raises
  `IndexError: The shape of the mask [1, 64, 64] ... does not match`.
- Even with a proper RGBA cut-out, the polarity is inverted. `LoadImage` returns
  `1.0 - alpha`, so the mask reads 0 on your subject and 1 on the background,
  while the consumer uses the mask **as** the alpha channel and zeroes anything
  below 0.1. Wired directly, it erases the subject and keeps the background.

So the plain branch needs an `InvertMask` between `LoadImage` slot 1 and
`reference_mask`, and it needs a cut-out to begin with. The obvious in-graph
routes to one do not work here. `LoadBackgroundRemovalModel` is registered but
its model list is empty, so `RemoveBackground` has nothing to feed it.
`Multi Background Remover` outputs a `LIST` for the multiview Hunyuan3D 2 nodes,
not an image. The Bria and Recraft background removers are online services.

**Do not put `Decimate Mesh` after it.** This generator returns a *textured* mesh,
carrying UV coordinates and an albedo. The decimation node reassigns only vertices
and faces, leaving the UV arrays pointing at the old topology. TripoSG and
Hunyuan3D are safe to decimate only because they return geometry with no UVs at
all. TRELLIS also simplifies internally already. Go straight to `Save 3D Mesh`.

### StableGen: this is the one that ships

It fits the house pattern exactly. Five nodes, no mask handling, and it is safe
to decimate because it returns geometry without UVs.

Its weights used to be the blocker: the loader wants four `.safetensors` under
`Stable3DGen/trellis/trellis-normal-v0-1` and only the four matching `.json`
configs shipped, 100K in total. Both those weights and the `.pth` DINOv2 it
wants are now declared in `models.json`, so `--group trellis` fetches them.

One measured detail that matters if you change the numbers: **`mesh_simplify` is
a keep ratio, not a removal ratio.** At its default of 0.95 it keeps 95% of the
faces, so it barely simplifies and the `Decimate` node is what actually meets a
budget. A run at the shipped settings came out at exactly 48,000 faces, which is
Decimate's target rather than anything TRELLIS chose.

StableGen applies an axis transform that the plain branch does not, which looked
like a reason to expect disagreement with the other generators. **Measured, it is
not.** The same concept was put through this graph and through
`img2mesh_hunyuan3d21.json`, both rendered at 45/135/225/315, and every facing
matched: comparing each TRELLIS cell against each Hunyuan cell, the aligned
pairing scores a mean silhouette IoU of 0.823 against 0.65 to 0.68 for every
90-degree rotation of the mapping. The transform brings this branch into the same
frame as the others rather than out of it.

## The wiring

The StableGen half is what `img2mesh_trellis.json` ships and has been run. The
plain half is derived from the node definitions and has not.

**Plain TRELLIS**, five nodes plus an inverter, NOT SHIPPED:

```
LoadImage (RGBA cut-out)
  ├── IMAGE slot 0 ──────────────────► Trellis Structured 3D Latents Models.reference_image
  └── MASK  slot 1 ──► InvertMask ───► Trellis Structured 3D Latents Models.reference_mask

Load Trellis Structured 3D Latents Models   (repo_id = the absolute path above)
  └── TRELLIS_PIPE ──────────────────► Trellis Structured 3D Latents Models.trellis_pipe

Trellis Structured 3D Latents Models
  └── MESH ──────────────────────────► Save 3D Mesh          (NO Decimate)
```

Its other inputs: `seed`, `sparse_structure_guidance_scale` (7.5),
`sparse_structure_sample_steps` (12), `structured_latent_guidance_scale` (3.0),
`structured_latent_sample_steps` (12).

**StableGen**, matching the house pattern, and what ships:

```
LoadImage ──► StableGen Trellis Image To 3D.images     (no mask needed)
Load StableGen Trellis Pipeline ──► DIFFUSERS_PIPE ──► .trellis_pipe
StableGen Trellis Image To 3D ──► MESH ──► Decimate Mesh ──► Save 3D Mesh
```

Its loader takes `model_name` (`trellis-normal-v0-1`), `dinov2_model`
(`dinov2_vitl14_reg`), `use_fp16`, `attn_backend` (`xformers`, `naive` or `sdpa`
in this install; flash attention is absent), `sparse_backend`, `spconv_algo` and
`smooth_k`. The combos carry no default, so a graph must state a value.

The generator takes `mode` (`single` or `multi`), `seed`, `ss_guidance_strength`
(7.5), `ss_sampling_steps` (12), `slat_guidance_strength` (3.0),
`slat_sampling_steps` (12) and `mesh_simplify` (0.95, range 0.9 to 1.0).

## Plain TRELLIS was run: the colour works, and its licence does not

The plain branch was run on a character concept, a warrior on a light grey
background, to find out whether its colour texture could replace Hunyuan3D
2.1's. Hunyuan3D's territory clause is the reason to look.

### Two things in this install stop it running

Neither is part of the wiring above, and both fail after the model has loaded.

- **The image encoder comes from a moving branch.** The pipeline fetches DINOv2
  with `torch.hub.load('facebookresearch/dinov2', ...)`, which takes the
  repository's `main` branch. Its current `hubconf.py` imports
  `dinov2.hub.cell_dino`, and inside the ComfyUI process that import fails with
  `No module named 'dinov2.hub.cell_dino'`. The same file imports cleanly in a
  fresh Python process. The 3D pack vendors older copies of `dinov2` that lack
  `cell_dino`, and one of them being importable in the ComfyUI process is the
  likely cause. That part is inferred, not traced.
- **`utils3d` changed its API underneath it.** The pack installs `utils3d` from
  the head of its repository, which is version 1.7 here. That version no longer
  has `utils3d.torch.perspective_from_fov_xy` or several other functions
  TRELLIS's post-processing calls, so a run gets through sampling and then fails
  while filling holes. The older commit
  `9a4eb15e4021b67b12c460c7057d642626897ec8`, which TRELLIS's own setup script
  installs, still has them all. Installing it over the image's copy would break
  anything else that expects 1.7.

What worked was a separate Python process inside the container. The pinned
`utils3d` was installed into a private folder with `pip install --no-deps
--target` and put first on the path, and the process called the same pipeline
and post-processing the node calls. That avoids both problems without touching
the ComfyUI process. The concept went in as a plain RGB image, so TRELLIS cut the
subject out itself with rembg; no cut-out was needed.

### What came out

On a 16GB card:

| | Measured |
|---|---|
| Time | 28 s to load the pipeline and sample, 57 s to a saved `.glb` |
| Mesh | 16,057 faces with UVs and a 1024px colour texture |
| Facing | The same as Hunyuan3D 2.1's mesh of the same concept: mean silhouette IoU 0.868 with the facings aligned, against 0.68 for each 90-degree rotation |
| Size | Silhouettes 1 to 4% larger than Hunyuan3D's at each facing, both normalised to the same height |
| Decimation | Blender took it to 12,000 faces and re-baked the texture intact: its mean brightness was identical before and after |

That decimation result doesn't contradict the warning above. It is ComfyUI's
`Decimate Mesh` node that scrambles UVs. A Blender decimate that re-bakes the
texture onto the result does not.

The colour is the weak part. Mean brightness (luma) and colourfulness (chroma,
the largest channel minus the smallest), over each texture's used pixels:

| | Luma | Chroma |
|---|---|---|
| The concept, cut out | 51.7 | 29.1 |
| Hunyuan3D 2.1's texture | 56.8 | 36.6 |
| Plain TRELLIS's texture | 31.1 | 15.7 |

TRELLIS's texture came out 40% darker than the concept with about half its
colour, and a figure drawn with it read brown where the concept is brass. Those
numbers were measured on the texture inside TRELLIS's own `.glb`, before any
conversion, so the loss is TRELLIS's own; which step causes it was not traced.
The back of the cloak, which the concept never shows, came out a washed-out
grey-white. Hunyuan3D also invented a paler back, less starkly.

### Why the colour is research-only

TRELLIS does not predict the texture onto the mesh directly. It renders its
Gaussian appearance model from 100 views and bakes those renders onto the UVs,
and two of the libraries that do that are licensed for research only. Both
licence files are in the image:

- **`diff_gaussian_rasterization`** renders the views. Its `LICENSE.md` is the
  Inria and Max Planck Institute "Gaussian-Splatting License". It says the
  software "may be used 'non-commercially', i.e., for research and/or evaluation
  purposes only", and: "THE USER CANNOT USE, EXPLOIT OR DISTRIBUTE THE SOFTWARE
  FOR COMMERCIAL PURPOSES WITHOUT PRIOR AND EXPLICIT CONSENT OF LICENSORS."
- **`nvdiffrast`** 0.3.3 rasterises the bake. Its `LICENSE.txt` is the NVIDIA
  Source Code License (1-Way Commercial). Section 3.3 says "The Work and any
  derivative works thereof only may be used or intended for use
  non-commercially", where non-commercially "means for research or evaluation
  purposes only and not for any direct or indirect monetary gain". Only NVIDIA
  may use it commercially, which is what "1-Way" means.

These limit **what you use the software for**, not who owns what it makes.
Running them to make art for a game that earns money is the use they rule out.
That is a tighter limit than Hunyuan3D's: its territory clause leaves the rest
of the world open, and these close all of it. None of this is legal advice.

::: tip The shape branch uses neither
`img2mesh_trellis.json` (StableGen) asks the pipeline for `formats=["mesh"]` and
simplifies with trimesh. A trace of that code path found no call into either
library: nothing in the Stable3DGen module imports its one `nvdiffrast` file
(`trellis/utils/_rasterization.py`), and nothing there imports the rendering or
post-processing utilities. That is a reading of the code, not a runtime check.
:::

### A lead that has not been tested

TRELLIS's mesh decoder predicts colour at the vertices as well: its config
(`slat_dec_mesh_swin8_B_64l8m256c_fp16.json`) sets `use_color` to true. Baking
those vertex colours into a texture in Blender would skip both restricted
libraries. Nobody has run it, so its quality is unknown. The decoder builds its
mesh with a modified FlexiCubes whose licence file is missing from the pack's
copy of TRELLIS, so check that licence upstream before relying on this route.

## Runs are not byte-reproducible

Worth knowing before you diff two outputs. Three fresh executions of this graph
with the same seed and the same input produced three different files: same size,
same 48,000 faces, three different checksums. The variation is GPU
nondeterminism in the sparse-convolution and attention kernels, not anything you
changed.

If you re-run and the bytes differ, that is expected. Compare renders, not
hashes. And note that a repeat with identical node inputs returns in about a
second from ComfyUI's cache rather than re-executing, so a genuinely fresh run
needs a changed input or a restart.

## The manifest, and what was wrong with it

The `trellis` group used to list two entries, call itself roughly 10GB, and
report complete. All three were wrong about what a run needs, and the group could
not produce a mesh on either branch.

It now declares four entries totalling about 9GB: the plain branch's TRELLIS
image-large, the StableGen weights, the `.pth` DINOv2 that Stable3DGen actually
loads, and the original `facebook/dinov2-large`.

That last one is **read by nothing**, and is kept only so an existing 2.3GB
download is not orphaned. The plain branch pulls its encoder through `torch.hub`
into a separate cache; StableGen wants the `.pth`. Neither reads
`facebook/dinov2-large` in transformers layout. It carries a note saying so, and
it is a candidate for removal, which is a decision about what everyone downloads
rather than a fix.

## What is left

Done: the StableGen graph ships, its weights are declared, and it has been run.

Verified since: orientation agrees with Hunyuan3D (above), and the
`facebook/dinov2-large` download is confirmed unread by holding it out and
re-running.

Still open:

1. **The unread `facebook/dinov2-large` entry**, 2.3GB. Annotated in
   `models.json` rather than removed, because removing it changes what everyone
   downloads. Note StableFast3D does want that model, but as a hub id resolved
   through the HF cache, so this copy does not serve it either.
2. **The plain branch is still unwired as a graph.** It has been run outside
   ComfyUI ([above](#plain-trellis-was-run-the-colour-works-and-its-licence-does-not)).
   A graph would need the absolute-path workaround, an `InvertMask`, a cut-out
   source and both install fixes, and its colour would still be research-only.
   The untested vertex-colour route is the one worth trying next.

::: warning You may need the spconv fix first
TRELLIS is a sparse-convolution model, and the published 0.1.0 image shipped
with `spconv` unable to import. `scripts/doctor.py` names it; the remedy is in
[troubleshooting](/guide/troubleshooting#anything-using-sparse-convolution-dies-with-type-not-registered-yet).
An image built from the current Dockerfile is not affected.
:::
