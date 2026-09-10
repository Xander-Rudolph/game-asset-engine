# TRELLIS, and why no graph ships for it

TRELLIS is MIT and carries no territorial clause, which makes it the obvious
choice for anything shipping into the EU, UK or South Korea. See
[licensing](/guide/licensing).

The nodes are installed and most of the weights are on disk. There is still no
workflow graph, and this page is the reason why: the two available routes each
need something the house pattern does not provide, and picking the wrong one
quietly costs you a multi-gigabyte download.

::: warning None of this has been run
Everything below is read from the server's node definitions and from the pack's
source inside the container. No graph was queued. The wiring is derived, not
proven, and the two "would corrupt" and "would re-download" findings are code
paths rather than observed failures.
:::

## There are two TRELLIS branches and they do not mix

Four nodes are registered, forming two independent chains. They share no pipeline
type, so you cannot swap halves.

| Branch | Loader | Generator | Pipeline type |
|---|---|---|---|
| Plain TRELLIS | `[Comfy3D] Load Trellis Structured 3D Latents Models` | `[Comfy3D] Trellis Structured 3D Latents Models` | `TRELLIS_PIPE` |
| StableGen | `[Comfy3D] Load StableGen Trellis Pipeline` | `[Comfy3D] StableGen Trellis Image To 3D` | `DIFFUSERS_PIPE` |

::: danger The type check will not protect you on the StableGen branch
`TRELLIS_PIPE` has exactly one producer, so that branch is self-checking.

`DIFFUSERS_PIPE` is generic and has **fourteen** producers, including the TripoSG
and Hunyuan loaders. ComfyUI will happily let you wire a TripoSG pipeline into
`StableGen Trellis Image To 3D`, and it will fail at run time rather than at
validation.
:::

## Which branch to choose

Neither is ready today. They fail in different directions.

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
2.3GB is currently downloaded and unused. See [the manifest bug](#the-manifest-bug)
below.

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
route to one is unavailable: `LoadBackgroundRemovalModel` is registered but its
model list is empty, so `RemoveBackground` has nothing to feed it.

**Do not put `Decimate Mesh` after it.** This generator returns a *textured* mesh,
carrying UV coordinates and an albedo. The decimation node reassigns only vertices
and faces, leaving the UV arrays pointing at the old topology. TripoSG and
Hunyuan3D are safe to decimate only because they return geometry with no UVs at
all. TRELLIS also simplifies internally already. Go straight to `Save 3D Mesh`.

### StableGen: cleaner wiring, no weights

This branch fits the house pattern exactly. Five nodes, no mask handling, and it
is safe to decimate because it returns geometry without UVs. It removes the
background itself using rembg with u2net, which is installed and cached, so it
works offline.

The blocker is simply that **the weights are not there**. The loader wants four
`.safetensors` under `Stable3DGen/trellis/trellis-normal-v0-1`; only the four
matching `.json` configs exist, 100K in total. It would download
`Stable-X/trellis-normal-v0-1` at run time, and `models.json` does not track it at
all. It also wants its DINOv2 as a `.pth` at
`Checkpoints/facebookresearch/dinov2/dinov2_vitl14_reg.pth`, which is a different
file from the one on disk, so that is another ~1.2GB.

One more difference worth knowing before you compare outputs: StableGen applies an
axis transform that the plain branch does not, so the two branches may not agree
on orientation with each other or with TripoSG and Hunyuan3D output.

## The wiring, if you build it

Derived from the node definitions, not from a successful run.

**Plain TRELLIS**, five nodes plus an inverter:

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

**StableGen**, matching the house pattern:

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

## The manifest bug

`models.json` describes the `trellis` group as roughly 10GB and lists two entries.
Both are on disk and `fetch_models.py` calls the group complete. Neither statement
survives contact with what the code loads.

- The actual total on disk is **5.7GB**, not 10GB.
- The **2.3GB DINOv2 entry is read by nothing.** The plain branch wants a torch
  hub cache entry and the StableGen branch wants a `.pth` in a different layout.
  Neither reads `facebook/dinov2-large` in transformers format.
- **Neither branch's real image encoder is tracked**, and the StableGen model
  weights are not tracked either.

So `fetch_models.py` reporting the group complete is true of what the manifest
declares and false of what a run would need. Fixing it means changing what people
download, so it is left as a finding rather than a patch.

## What it would take to finish this

In rough order of least surprise:

1. Build the **StableGen** graph, because its wiring is the house pattern and
   needs no mask work.
2. Add `Stable-X/trellis-normal-v0-1` and the `dinov2_vitl14_reg.pth` to
   `models.json` so the download is declared rather than a run-time surprise.
3. Fix or remove the unused `facebook/dinov2-large` entry.
4. Run it once and compare orientation against a TripoSG output, since the axis
   transform differs.
5. Only then consider the plain branch, which needs the absolute-path workaround,
   an `InvertMask`, and a cut-out source.
