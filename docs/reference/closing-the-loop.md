# Closing the loop

A design note, written 2026-09-10, prompted by looking at what GPT-6 Astra does
with Blender and asking what is worth taking from it.

The short answer: the interesting part is not the model. It is the shape of the
loop, and this repo already has both halves of that loop with no wire between
them.

## What the comparison actually showed

Astra writes Blender Python, runs Blender headless, reads the render back as an
image, and revises the script where the render disagrees with the brief. Its API
model card lists output as text only. There is no 3D output modality. Every
artefact is a side effect of code the model wrote and a harness executed.

That is the same architecture used here. `render_sheet.py`, `decimation_report.py`
and `transfer_weights.py` all deliver Python into `bpy` inside the container with
the configuration as a single JSON blob on argv.

The difference is the wire back.

## Where the loop is open

Verified against the files, not recalled.

**`render_sheet.py` never opens its own output.** It renders the cells, pastes
them into a sheet at line 381, saves, and prints a path. The last thing it does
with pixels is write them.

**`decimation_report.py` measures well and decides nothing.** It has the one
genuinely closed-loop primitive in the repo: `compare()` reads Blender's own
render buffer and returns silhouette IoU plus a colour difference. Then it sweeps
a caller-supplied list of face budgets, prints a table, and leaves the decision to
you.

**Its measurement renders are unreachable.** Lines 208 and 229 write to
`/tmp/dec_ref.png` and `/tmp/dec_<target>.png` inside the container, which is not
a bind mount. The numbers exist; the pixels they describe cannot be looked at by
anyone.

**The gap is handed to a human by policy.** `skills/pose-sheet/SKILL.md` has a
step titled "Look at it, then say what you see", and the rule "do not hand over a
sheet you have not looked at".

That rule is right for taste. It is doing too much work for arithmetic. The
sharpest example: the skill asks the agent to find, by eye, which cell shows the
figure facing down and to the right. `render_sheet.py` computes that azimuth list
arithmetically and prints it. **The script already knows the answer and asks the
picture instead.**

## The principle

> Every check whose answer is a number gets computed. The human keeps only the
> checks whose answer is taste.

The repo already contains its own best example. `skills/mesh-budget/SKILL.md`
never tells anyone to look at an image. Its gate is "measure, do not guess", and
it argues from measurement that the numbers catch what a glance misses: at 12,000
faces the outline has lost 0.7% while the texture already differs by 2.1 levels.

The mesh path is by number. The pose path is by eye. The mesh path is better.

## What to build

Ranked. All of it uses the existing mechanism plus a measurement. None of it
needs a new model, an API key or a subscription.

### 1. `scripts/normalise_mesh.py`

Scale and centre a mesh to a declared convention, and write a sidecar recording
which rule was applied. Figures are sized by height; anything tile bound is sized
by footprint.

This is first because of a specific trap. `render_sheet.py` frames every model to
its own bounding box, so **a mis-scaled model renders perfectly and ships wrong**.
The error is invisible in exactly the artefact the docs tell you to inspect.

Nothing in `scripts/` currently scales a mesh to a world size.

### 2. `decimation_report.py --target-iou`

Everything needed is already in the file: the reference BVH, the render, and
`compare()`. Replace the fixed sweep with a bisection on measured silhouette IoU
and it stops being a table you interpret and becomes an answer: ship this at 9,400
faces.

Two things fall out free. The boundary-edge floor detects itself, because two
successive bisections returning the same face count means you are on it. And the
existing fixed sweep stays available as `--sweep`, because the shape of the whole
table is what teaches the trade-off.

### 3. `scripts/sheet_check.py`

The per-frame PNGs are already on the host. Compute what is computable:

- an empty or near-empty cell, meaning the render failed or the subject rotated
  out of frame
- rest-pose repetition, where row N matches row 0 across every angle. The existing
  missing-bone check catches a typo, not a rotation that cancelled
- frame clipping, which is nonzero alpha touching a cell border
- the facing index, printed from the azimuth list rather than found by eye
- silhouette area at ship size

Then the skill's step 5 becomes: run the check, then look at the sheet for the one
thing the check cannot see, which is whether the motion reads as the motion.

### 4. Smaller, and worth doing while you are in there

- **Write the decimation renders somewhere mounted**, so the number and the
  picture live in the same place.
- **`_engine.exec_python` is dead code.** It implements exactly the call all three
  tools make, including a timeout, and nothing imports it. Meanwhile none of the
  three passes a timeout at all, so an iterative loop inherits one chance to hang
  per iteration.
- **Nothing cleans `output/_sheet_frames`.** It holds 40 directories today. A
  check flag that re-reads frames multiplies that.

## What not to do

**Do not replace this pipeline with a hosted model.** It runs locally, costs
nothing per asset, and its quality is measured. The alternative is priced per
token, non-deterministic with no seed, and produces no watertight shell, no UV
set and no rig.

**Do not add a GUI-driving addon.** The transport here is already better than
driving an application through its interface.

**Do not build a cross-stage autonomous loop.** `skills/asset-pipeline/SKILL.md`
is explicit: one stage per turn, show, ask, wait. Every loop above lives strictly
inside one stage. That rule is why this pipeline produces coherent sets rather
than confident piles.

**Do not auto-repair on a single metric.** `scripts/make_seamless.py` is the
cautionary precedent already in the repo: its first seam metric scored an already
perfect texture at 81%, and acting on one number repaired a working texture into a
worse one. Measure and report. Only the IoU bisection decides anything, and it
decides on a metric with a published table behind it.

**Do not chase organic characters with procedural code.** Diffusion is better at
creatures than any code path will be. That is the half of this pipeline that
works.

## Where code-driven modelling genuinely wins

As asset classes rather than adjectives. Note the win is procedural modelling in
general, not any particular model. You already own the runtime that executes the
scripts.

1. **Modular kits.** Tiles, walls, corridors, fences, dungeon pieces. Anything
   that must butt against a sibling needs vertex-exact seams, and a generator puts
   boundary vertices wherever it likes. This repo already made that ruling once
   for terrain, and the reasoning was representation-level rather than terrain
   specific.
2. **Buildings.** Every stage mishandles them. The concept prompt asks for a self
   contained diorama, so the plinth becomes geometry that double draws against
   your tiles. They are sized by footprint, not height. And large flat panels
   collapse first at decimation, which is most of what a building is.
3. **Thin and bladed parts.** Straps, staffs, horns. Both shipped generators are
   volumetric, so anything below one cell disappears, and raising the resolution is
   what tips a run into the out-of-memory killer.
4. **Hard-surface manufactured objects.** Crates, doors, carts, machinery. Their
   defining properties are constraints: symmetry, planarity, right angles, exact
   dimensions. The only input this pipeline has is a picture, and a picture is not
   a channel for stating a constraint. Telling detail: not one manufactured object
   ships as a working example anywhere in this repo.
5. **Parametric variants.** Eleven columns instead of six is one function in code
   and N unrelated rerolls here.
6. **Anything carrying lettering.** Every concept negative in this repo excludes
   text for good reason.
7. **Very low-poly targets.** Below about 2,000 faces for a character sized
   subject, the guide already says the answer is a different approach rather than
   more decimation.

Keep sending creatures, characters and organic scenery through diffusion.

## Honest uncertainty

About the model that prompted this, one week after release:

- No independent reproductions of the marquee demos exist. They are all from early
  access testers. There are also no published failed attempts, so the honest
  status is silence rather than refutation.
- No convergence data from anyone. No iteration counts, no success rate, no
  example of a run that did not converge. Assume survivorship bias until measured.
- No per-asset cost published by anyone, including the vendor.
- Rigging is the weakest evidenced claim by a long way. Nobody has published a
  weight-map inspection or a deformation test.
- No published example of it editing a large human-authored file it did not
  create. Every editing demo was it editing its own prior output.

About the recommendations here: they rest on reading this repo's files, which is
cheap to check and worth checking. The quickest experiment is item 3. Build the
sheet check, run it over the sheets already in `output/sheets/`, and see whether
it agrees with what you thought of them. If the numbers keep flagging good sheets
or passing bad ones, the loop is not closeable on those metrics and the by-eye
rule was right all along.
