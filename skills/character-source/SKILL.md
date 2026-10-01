---
name: character-source
description: Say what a character made in Character Creator, iClone, ActorCore, Poser, ZBrush or Autodesk Character Generator may ship as, and keep it out of the AI stages. Use when the user asks "can I use my Character Creator character in my game", "is Character Generator output mine", or brings a character or base mesh from one of those tools. Licence first.
---

# Character source: what a commercial character tool lets you ship

Work in the asset-engine repo root. The research behind every rule here is
`docs/reference/character-tools.md`, with its claims in
`research/claims/character-tools.json`. It was read on 2026-09-23. Nothing in
it was installed or run on this host, so no Reallusion, Poser, ZBrush or
Autodesk file has ever been imported or rendered here. Say that when it
matters.

What each ecosystem's characters, clothing, hair and non-human figures cost,
and the free CC0 and CC BY alternatives, are in
`docs/reference/character-assets.md`. Daz content has its own skill,
`daz-figure`. A base the repo can own outright
is MakeHuman through MPFB2, whose bundled assets are CC0
(`docs/reference/daz-genesis.md`, "MakeHuman and MPFB2").

**The licence comes first, before any file is touched.** State it, get an
answer, then do the next step. One step per turn.

## Before you start

```sh
scripts/doctor.py --skip-models
```

Read its output. A render in step 4 runs in the container, so do not start that
step until doctor says ready.

## 1. Ask three things

- **Which tool, and which licence they hold.** A perpetual licence, a
  subscription, a trial, an education licence, or a Reallusion content plan.
  Character Creator and ZBrush trials, ZBrush education licences and
  Autodesk education licences may not be used commercially.
- **What they want to end up with.** Renders and sprites, or the 3D data itself
  in a game build.
- **Whether any AI stage is involved.** A Qwen-Image restyle, a TRELLIS or
  Hunyuan3D mesh, or a lip-sync portrait edit are all AI stages.

## 2. State the rule for that tool

Quote the terms; do not soften them. Every row was read on 2026-09-23.

| Tool | Renders in a game | 3D data in a build | AI stages |
|---|---|---|---|
| Character Creator 5, ActorCore | Yes, Content EULA 2.1(A) | Yes, but only "contained in proprietary formats" no public app can open (6.3); the "embedded content" restriction is an open question | Barred: "For machine learning, AI training, or AI-generated output" |
| The five free CC base characters | Yes | Commercial use including games, under Software EULA section 5, which bars character generators, marketplaces and "AI training, machine learning, or synthetic data generation" | Barred |
| Character Creator 3, iClone 7 | Yes, under today's Standard licence | Unsettled: whether the 2026 terms reach an old licence is not clear | Barred by the current texts |
| Autodesk Character Generator | Only forum posts permit it; no terms page names the service | Same | The Acceptable Use Policy bars training a model to replicate an Autodesk product |
| Poser 14 | Renderosity Standard licence: yes | Only the Vendor Resource figures, and the two Poser 14 EULA texts disagree | No clause |
| ZBrush | Yes, for your own sculpts on a paid plan | Your own sculpts, yes; bundled meshes other than Capsules are unclear | Bars training a model that does what ZBrush does |

Two traps to name when they apply:

- **Section 5 covers only an "Original Character Creation"**: a character made
  "without using any content from Reallusion or its developers, including
  models, morphs, textures, hair, and outfit assets". Bundled skins, hair and
  outfits bring the Content EULA instead.
- **A lapsed Reallusion content plan** turns saved project files into trial
  content that "cannot be exported". Export first.

## 3. Choose the route

- **Sprites or portraits.** Go on to step 4. It works for every tool here.
- **3D data in the build.** Give the conditions above. If they cannot meet
  them, offer MPFB2, which is CC0.
- **An AI stage on Reallusion content.** Refuse, and say why. Offer MPFB2 or
  art the user owns instead. Poser and ZBrush sculpts carry no such ban, but
  third-party content inside them may.
- **They want Reallusion, Bondware or Autodesk to settle a question.** Point
  them to "Honest uncertainty" in the research note. Do not settle it yourself.

## 4. Render it, if they want renders

The user downloads the content in their own browser, from their own account.
Never fetch store content with a tool. Every one of these downloads needs a
login.

Keep the files outside the repo, or under `output/`, which git ignores. Then:

```sh
scripts/render_sheet.py output/characters/<name>.fbx --azimuths 0,90 --elevation 0
```

That command has never been run on a Character Creator, Poser or Character
Generator FBX, so say so.

Read the sheet back into the conversation and look at it, then show it. The
owner settled on 2026-09-23 that Claude may read a Reallusion render, as it
may a Daz render. That changes nothing else: the render and its source files
still never go into an AI stage, and none of them is committed.

## Rules

- **Never commit their 3D data.** `scripts/cleanup.py keep` guards Daz files
  only. Do not run `keep` on a mesh, texture or `.blend` from these tools.
- **Never pass a Reallusion render to `scripts/run_workflow.py`**, or to any
  other stage that feeds a model.
- **Never vendor a third-party add-on.** Link to the CC/iC Blender Tools add-on
  (GPL-3.0); do not copy it in.
- **Nothing here runs on Linux.** Reallusion's current products and Poser 14 are
  Windows only. ZBrush runs on Windows, macOS and iPad. Character Generator is
  a web service reached through an Autodesk subscription.
