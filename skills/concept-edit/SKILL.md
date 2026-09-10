---
name: concept-edit
description: Change one element of an existing concept image - swap a piece of armour, add or remove a prop, alter a colour - without regenerating the whole picture. Use when a design is approved except for one detail, or when the user says "keep this but change X", "use that one and swap the Y", or asks to edit or fix part of an image.
---

# Concept edit: change one thing, keep the rest

Work in the asset-engine repo root. Workflow: `workflows/api/img_edit_qwen.json`.
Qwen-Image-Edit 2509, Apache-2.0.

**Use this whenever the user says "use that one, but…".** Regenerating with an
adjusted prompt will not preserve the approved design — even on the same seed, a
changed prompt produces a different picture. Editing is the only way to keep what
was approved.

## Before you start

```sh
scripts/doctor.py --skip-models
```

Read it. If the server is not answering, the doctor prints the one command to
run. On a cold start the container comes up before ComfyUI has finished loading
its node packs, so wait rather than restarting.

## Check the model is there first

```sh
scripts/fetch_models.py --group qwen_edit
scripts/fetch_models.py --download --group qwen_edit    # 19GB if missing
```

It reuses the `qwen` group's text encoder and VAE, so that group must be present
too — the edit model alone has nothing to run with.

## Run it

```sh
scripts/run_workflow.py workflows/api/img_edit_qwen.json \
    --image output/concept/<approved>.png \
    --set 'Positive.prompt=<instruction>'
```

~130s. It writes `output/concept/edit_NNNNN_.png`.

## Writing the instruction

Phrase it as an **instruction, not a description**, and always say what to keep:

> Replace the shoulder pauldron on the left of the image with a rounded glass
> chamber of glowing amber fluid in a brass housing. Keep the pose, helm, arms,
> legs, colours and grey background exactly the same.

Rules that matter, learned by getting them wrong:

- **Name the side by where it is in the image**, not the character's left or
  right. "The warrior's left shoulder" is ambiguous — the model reads a picture,
  not a body.
- **Be explicit about singular.** Asking to replace "a pauldron" got *both*
  replaced. If only one should change, say "only ONE shoulder" and describe what
  the other should stay as.
- **Ask for one change at a time when it matters.** Bundling two edits into one
  prompt makes it likelier that one is over-applied. Two passes at 130s each is
  cheaper than a wrong design carried into a mesh.
- **End with the keep-list.** Naming pose, background and colours measurably
  reduces drift.
- **Expect some global drift anyway.** The whole image is re-diffused, so
  lighting and surface finish shift slightly even in untouched areas. If a
  faithful crop matters, that is a compositing job, not this.

Edits chain: feed `edit_00001_.png` back in to correct an overshoot.

## Check the model is loaded rather than assuming

If a run fails with an unknown node or a missing checkpoint, ask the server what
it actually has rather than guessing:

```sh
scripts/run_workflow.py --list-nodes Qwen        # node types the server loaded
scripts/validate_workflows.py                    # every graph checked against it
docker logs --since 5m comfyui 2>&1 | grep -iE 'error|exception'
```

## Always show the result

**Read the output file** so the user sees it, and **compare it against the
input** — say plainly what changed, including anything that changed which
shouldn't have. An edit that silently altered something else is worse than a
failed one, because it will be discovered after a mesh has been built from it.

Then ask: approve / another edit / go back to the original.

## Denoise is the control, not the prompt

The single most useful number here, and it is not in the instruction you write.
`--set denoise=` decides how much of the source survives, and it behaves like a
**cliff rather than a dial**:

| Denoise | What you get |
|---|---|
| 0.70 and below | The source dominates. A restyle or simplify does almost nothing. |
| ~0.80 | Right for a small local swap - a pauldron, a colour, one prop. |
| 0.85 | Painterly rendering kept, clutter genuinely reduced. Good default for simplifying. |
| 0.93 | Pushed to clean game-ready forms, still shaded metal against leather. |
| 1.00 | The model's own style prior wins and returns flat vector art. |

At 1.0 the whole image is re-diffused, and no amount of prompt wording pulls it
back: "NOT cartoon, NOT flat plastic, NOT a clay render", written three
different ways, returned flat cartoon every time. **Negative phrasing in an edit
prompt is weak; the sampler setting is the actual control.** Reach for denoise
before adding words.

The cliff moves with how busy the source is, so test one image before running a
batch. `docs/guide/concept-art.md` has the measured numbers for two real sets.

## Why 20 steps and not the Lightning LoRA

The 4-step Lightning LoRA exists for this model, but applying a bf16 LoRA to the
fp8 base makes ComfyUI dequantize the affected layers to patch them, and that
spike OOMs a 16GB card. `txt2img_qwen_fast.json` dodges this with a pre-merged
4-step checkpoint; no such merge exists for the edit model, so it runs at 20
steps, cfg 4.0.
