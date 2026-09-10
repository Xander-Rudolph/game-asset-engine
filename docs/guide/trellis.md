# TRELLIS

TRELLIS is MIT and carries no territorial clause, which makes it the choice for
anything shipping into the EU, UK or South Korea. See
[licensing](/guide/licensing).

```sh
scripts/fetch_models.py --download --group trellis
scripts/run_workflow.py workflows/api/img2mesh_trellis.json \
    --image input/concept.png --set 'save_path=mesh/asset.glb'
```

`img2mesh_trellis.json` uses the Stable3DGen branch. It has been run end to end:
a 1104x1472 character concept on a plain grey background produced a clean
48,000-face mesh in 29 seconds, with the background removed automatically.

::: tip It needs no cut-out, unlike TripoSG
This is the practical reason to reach for it beyond the licence. The pipeline
runs rembg with u2net itself, so a plain grey-background concept render works
directly. `img2mesh_triposg.json` needs an RGBA cut-out and there is no node in
this install that makes one.
:::

The rest of this page is why there are two TRELLIS branches, why only one of
them ships as a graph, and what the other would need.

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

It now declares four entries totalling about 9.6GB: the plain branch's TRELLIS
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
2. **The plain branch is still unwired**, and needs the absolute-path workaround,
   an `InvertMask`, and a cut-out source.

::: warning You may need the spconv fix first
TRELLIS is a sparse-convolution model, and the published 0.1.0 image shipped
with `spconv` unable to import. `scripts/doctor.py` names it; the remedy is in
[troubleshooting](/guide/troubleshooting#anything-using-sparse-convolution-dies-with-type-not-registered-yet).
An image built from the current Dockerfile is not affected.
:::
