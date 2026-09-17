---
layout: home

hero:
  name: Game Asset Engine
  text: Written description in, game asset out
  tagline: A local ComfyUI setup that takes a sentence, draws the concept art, builds a 3D model, textures it, rigs it, and renders the sprite sheet your game actually loads. Everything runs on your own machine.
  image:
    src: /logo.svg
    alt: An isometric wireframe cube
  actions:
    - theme: brand
      text: Start here
      link: /guide/
    - theme: alt
      text: Install it
      link: /guide/install
    - theme: alt
      text: Make your first asset
      link: /guide/first-asset

features:
  - icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="m4 17 6-5-6-5"/><path d="M12 19h8"/></svg>'
    title: One command per stage
    details: Each stage is a script with the settings already chosen. You are picking subjects, not tuning samplers.
  - icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h8M16 6h4M4 12h4M12 12h8M4 18h8M16 18h4"/><circle cx="14" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="14" cy="18" r="2"/></svg>'
    title: The settings are the point
    details: Nearly every default here was found by something failing. Each page says what went wrong and why the number is what it is.
  - icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 20h18"/><rect x="5" y="11" width="4" height="6" rx="1"/><rect x="10.5" y="7" width="4" height="10" rx="1"/><rect x="16" y="4" width="4" height="13" rx="1"/></svg>'
    title: Measured, not guessed
    details: Face budgets, seam quality and camera angles come with numbers you can reproduce with the tools in the repo.
  - icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M9 20h6M12 16v4"/></svg>'
    title: Nothing leaves your machine
    details: No cloud service, no per-image cost, no upload of work in progress. A GPU and about 200GB of disk.
---

## What you get

Write a description. You get back a folder with the concept image, the 3D model,
texture maps, a skeleton, and a sprite sheet of animation frames rendered at the
camera angle your game uses.

```
"a mossy stone golem"
        |
   concept image       Qwen-Image, 30 seconds fast, 2 minutes careful
        |
    3D shape           TRELLIS or Hunyuan3D, under a minute
        |
    textures           colour, metal and roughness maps
        |
    skeleton           UniRig, automatic, no hand weighting
        |
  sprite sheet         four or eight facings, one row per animation frame
```

## Who this is for

Game makers who need lots of art, can't draw all of it, and would rather own
the tools than rent them. It works especially well for isometric and top down
games, since it renders 3D models to 2D sprite sheets at exactly the camera
angle your map uses.

## What it costs to run

A CUDA GPU (measured on an RTX 4070 Ti SUPER with 16GB and 31GB of RAM; a 12GB
card has not been tested), about 200GB of disk for the model weights, and about
28GB for the prebuilt image. There are no per-asset fees. A concept image
takes 30 seconds to 2 minutes, a mesh about a minute, a rig a few minutes.

## Where to go next

New here, start with [what this is](/guide/) then
[install it](/guide/install).

Already running, go to [make your first asset](/guide/first-asset).

Trying to work out why a sprite faces the wrong way, that is
[facings and camera angles](/guide/facings).

Deciding how many faces a model should have, that is
[face counts and decimation](/guide/decimation).
