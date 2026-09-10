---
layout: home

hero:
  name: Asset Engine
  text: Written description in, game asset out
  tagline: A local ComfyUI setup that takes a sentence, draws the concept art, builds a 3D model, textures it, rigs it, and renders the sprite sheet your game actually loads. Everything runs on your own machine.
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
  - title: One command per stage
    details: Each stage is a script with the settings already chosen. You are picking subjects, not tuning samplers.
  - title: The settings are the point
    details: Nearly every default here was found by something failing. Each page says what went wrong and why the number is what it is.
  - title: Measured, not guessed
    details: Face budgets, seam quality and camera angles come with numbers you can reproduce with the tools in the repo.
  - title: Nothing leaves your machine
    details: No cloud service, no per-image cost, no upload of work in progress. A GPU and about 200GB of disk.
---

## What you get

A written brief goes in one end. Out the other comes a folder holding the concept
image, the model, its texture maps, a skeleton, and a sprite sheet of animation
frames rendered from the camera angle your game uses.

```
"a mossy stone golem"
        |
   concept image       Qwen-Image, about 30 seconds
        |
    3D shape           Hunyuan3D or TripoSG, about a minute
        |
    textures           colour, metal and roughness maps
        |
    skeleton           UniRig, automatic, no hand weighting
        |
  sprite sheet         four or eight facings, one row per animation frame
```

## Who this is for

People building 2D or 3D games who need a lot of art, cannot draw all of it, and
would rather own the pipeline than rent one. It suits isometric and top down
games particularly well, because the last stage renders a 3D model to flat
frames at whatever angle your map uses.

## What it costs to run

A CUDA GPU with 12GB or more, about 200GB of disk for the weights, and roughly
27GB for the prebuilt image. There are no per asset fees. A concept image takes
about 30 seconds, a mesh about a minute, a rig a few minutes.

## Where to go next

New here, start with [what this is](/guide/) then
[install it](/guide/install).

Already running, go to [make your first asset](/guide/first-asset).

Trying to work out why a sprite faces the wrong way, that is
[facings and camera angles](/guide/facings).

Deciding how many faces a model should have, that is
[face counts and decimation](/guide/decimation).
