# Credits

This repo is scripts, prompts, documentation and glue. Almost all of the actual
capability comes from other people's work. Here is whose.

## The node packs this is built on

- **[ComfyUI-3D-Pack](https://github.com/MrForExample/ComfyUI-3D-Pack)** by
  MrForExample. Image to 3D, mesh handling, decimation, orbit rendering, and the
  wheel builds that make CUDA extensions installable at all. This is the
  foundation of the whole mesh side of the pipeline.
- **[ComfyUI-UniRig](https://github.com/PozzettiAndrea/ComfyUI-UniRig)** by
  Andrea Pozzetti. Automatic skeleton extraction and skinning, wrapped so it can
  be driven from a graph. Everything on the rigging pages here is downstream of
  this.
- **[ComfyUI-mesh2motion](https://github.com/jtydhr88/ComfyUI-mesh2motion)** by
  jtydhr88. An interactive rigging and animation editor embedded in a node, and
  the source of the 176 CC0 animation clips, including every non humanoid
  skeleton available here.
- **ComfyUI-CameraPack**, pulled in as a declared dependency of UniRig.

And **[ComfyUI](https://github.com/comfyanonymous/ComfyUI)** by comfyanonymous,
which all of the above extends.

## Research and models

- **UniRig**, the automatic rigging method (SIGGRAPH 2025), and
  **Make-it-Animatable** for humanoids.
- **Hunyuan3D 2 and 2.1** by Tencent. The best mesh generation in this stack.
  Territorially limited licence, covered in the licensing guide.
- **TripoSG** and **TripoSR** by Tripo AI and Stability AI. MIT.
- **TRELLIS** by Microsoft. MIT.
- **Qwen-Image** and **Qwen-Image-Edit** by Alibaba. Apache 2.0, and the default
  concept generator here.
- **Stable Diffusion XL** and **SD 1.5** by Stability AI.
- **InstantMesh**, **Zero123++**, **MV-Adapter**, **Unique3D**, **CharacterGen**,
  **LGM**, **CRM**, **TriplaneGaussian**, **PartCrafter**, **StableFast3D**.
- **rembg** and **u2net** for background removal. Apache 2.0.

## Animation

- **mesh2motion's clip library**, released CC0 by its author, who wrote: "The art
  assets (3d models, rigs, animations) are all licensed under CC0. I tried making
  everything as open as possible to remix, change, and build upon." That is the
  cleanest source in this stack.
- **Carnegie Mellon motion capture**, via
  [RancidMilk](https://rancidmilk.itch.io/free-character-animations).
- **[Mixamo](https://www.mixamo.com)** by Adobe.

## Tools

- **[Blender](https://www.blender.org)** and its `bpy` module. Every sprite
  sheet, pose, decimation measurement and weight transfer here runs through it.
- **[VitePress](https://vitepress.dev)** for the documentation site.
- **Pillow**, **NumPy**, **trimesh**.

## Licences

Every dependency keeps its own licence. The ones with conditions that affect a
shipped game are listed with their exact terms in
[the licensing guide](https://athanorgames.github.io/asset-engine/guide/licensing),
and `scripts/fetch_models.py --licenses` prints the current set.

If you are credited here and want the wording changed or the entry removed, open
an issue.
