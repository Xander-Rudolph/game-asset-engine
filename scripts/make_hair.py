#!/usr/bin/env python3
"""Grow layered hair guides on a scalp dome: a cap, four card layers, an atlas plan, and a numpy-only fallback mesh.

    scripts/make_hair.py --list
    scripts/make_hair.py --style wavy --colour brown
    scripts/make_hair.py --style long --colour blond --part left --name lyra
    scripts/make_hair.py --style none --beard full --colour brown --name beard_full

WHY: the engine's other two routes to hair both stop short.  A Daz hair product
is Daz 3D data, so it may be rendered but never shipped as 3D without an
Interactive License (docs/reference/daz-genesis.md).  A strand hair is worse
than licence-bound, it is empty: the two in the library carry 236,136 and
167,264 vertices and no polygons at all, so Cycles draws nothing but the cap
(scripts/daz_characters.py, `draws_nothing`).  This script writes guides and
polygons the repo owns outright, which any engine loads and which may ship.

WHAT IT IS NOT: static geometry, with no rig, no fitting and no morphs.  It
grows on a sphere of `--head-radius`, so it lands on a head by being placed
there, which `daz_import_probe.py scene --wear-obj` does by measurement.

HOW IT IS LAID OUT: every published card workflow is a layer stack over a scalp
cap, thick to thin outward (HAIR-001, HAIR-008, HAIR-044), so the hair is
grown as one cap and four layers, each with its own count, width, offset from
the scalp, point count and atlas band: shells (the opaque base), breakup cards
in three-card tents (HAIR-002), hairline cards and flyaways.  Roots are laid by
Bridson Poisson-disk sampling on the scalp cap under a density mask (HAIR-118)
inside a hairline shaped 48 degrees from the crown at the front, 76 at the
temples and 83 at the nape.  Hair leaves the scalp along a flow field: away
from a whorl behind the crown, swept off the parting, forward at the front and
down at the back (HAIR-106).  A card is a lock, not a strand (HAIR-087,
HAIR-101): roots are clustered by nearest Poisson centre at `--guide-distance`,
pulled towards the centre with a root-to-tip shape and spread at the tip
(HAIR-117), and the card's width comes from its cluster's spread within the
layer's bounds (HAIR-101).

HOW IT FALLS, in two stages.  First the guides are grown in a STYLED POSE: the
flow, the exit angle, the parting, the waves, the curl and the comb that lays
the heading over the skull, all of it shape rather than physics.  Then that
pose is dropped by a position-based settle, the solver the Virt-A-Mate work was
run with (docs/reference/vam-assets.md, VAM-031, run 2026-09-23): a Verlet step
with drag, a rigidity pull back towards the styled pose with a root-to-tip
rolloff, inextensible segments solved root first, and a collision against the
scalp sphere, the body capsules and the jaw ellipsoid, run until the strands
stop moving.  This is how a Virt-A-Mate groom works and why the two stages are
separate: the creator combs the guides and the solver only refines them
(VAM-030).  Measured on the wavy bob on 2026-09-23, combing and then settling
gives a span of 26.42 x 23.78 x 24.07 cm against 27.58 x 23.18 x 25.03 cm for
the comb alone, while settling WITHOUT the comb gives 31.00 x 23.92 x 28.15 cm,
because the rest pose is then a spike standing off the scalp and the rigidity
holds it there.  So `--comb` and `--settle` are separate flags and both default
on.  Note the styled pose is not free of downward terms even with `--no-comb`:
`scalp_flow` blends a little `down` into the tangential flow, `Jaw.flow` is
built from it, and `slide` forces a downward heading when a slid heading
collapses.  Those are styling and collision response, not free fall.

A BEARD is the same construction on a second surface: `--beard` grows roots
by the same Poisson sampler on a jaw ellipsoid (JAW_CENTRE, JAW_RADII) in the
ellipsoid's own scaled space, restricted to the beard region (BEARD_REGION:
below the mouth line round the chin and jaw, plus a moustache band), flowing
down the face, kept clear of the ellipsoid and of the neck capsule, with a cap
that is the beard region of the ellipsoid.  It is written as its own asset,
<name>_beard (or <name> with --style none), so it can be worn alone.

WHAT IT WRITES, all under output/hair/<name>: the layered guide curves
(<name>_guides.npz) and the atlas plan (<name>_atlas.json) for the Blender
side, scripts/bake_hair.py, which sweeps the shells, renders a real-strand atlas
and transfers normals; the scalp cap (<name>_cap.obj/.mtl and its two maps);
the numpy-only fallback (<name>_fallback.obj/.mtl with its own painted atlas)
for a host with no container; <name>_preview.obj for scripts/render_sheet.py;
and <name>.json with every setting and measurement.

WINDING: every face is wound so its geometric normal points away from the head.
The generator at commit 1fdbb72 emitted (a, b, d), (a, d, c), which is the
inverse, and that one bug was most of what looked wrong: the bob rendered at
mean luma 30.5 as written and 167.9 with the winding reversed
(docs/reference/hair-cards.md, measured 2026-09-22).  The report prints the
mean signed dot of face normal against the radial so it can never regress.

Standard library plus numpy and Pillow, both on the host's python3 (numpy 2.3.5,
Pillow 12.1.1, measured 2026-09-22).  It touches no network, no container and no
content library; `--no-bake` is a placeholder until the integrator wires the
Blender call.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "hair"

# Length is centimetres of hair; cap is how far down the scalp roots reach at
# the nape, in degrees from the crown; wave scales both sine amplitudes; scale
# multiplies every layer's count; points overrides every layer's point count
# (curls need many where a straight card needs 3 to 5, HAIR-019); width scales
# every layer's card width.  Shapes to start from, not measurements: every one
# is reachable with the flags as well.
STYLES = {
    "wavy":     {"length": 14.0, "variation": 3.0, "wave": 1.0, "cap": 83.0, "scale": 1.0, "points": None, "curl": 0.0, "curl_turns": 0.0, "curl_start": 0.0, "width": 1.0},
    "straight": {"length": 16.0, "variation": 2.0, "wave": 0.15, "cap": 83.0, "scale": 1.0, "points": None, "curl": 0.0, "curl_turns": 0.0, "curl_start": 0.0, "width": 1.0},
    # curly: the sideways sine wave read as no curl at all (2026-09-22), so the
    # style winds each strand round its own centreline instead, Blender's Curl
    # Hair Curves semantics (HAIR-117): a radius in cm, turns per strand, and
    # where along the strand the curl starts.  At 1.1 cm, 3 turns, 20 points
    # and cards 2.4 to 3.5 cm wide the helix was in the guides (keep_clear
    # moved 0.5 percent of their points) but the baked curls still read as
    # zigzag ribbons, because a card wider than the coil is a wavy sheet, not
    # a ringlet.  So the cards are half width (`width` scales every layer's)
    # and 25 points keep a turn round.  Tried at 1.0 cm, 4 turns and 0.42
    # scale: 20,808 triangles, but the crown showed through 38 shells and the
    # bake found shells wound inward (signed volume down to -2.576 cm3), the
    # sweep's frame flipping on the tight coil.  At 0.9 cm, 3.5 turns and 0.5
    # every one of the 45 shells is wound outward (min +1.25 cm3) and the
    # figure render shows corkscrews, at 24,108 triangles, the same past-20k
    # cost the old curls paid (all measured 2026-09-22; the shape is a guess).
    "curly":    {"length": 11.0, "variation": 2.5, "wave": 0.4, "cap": 83.0, "scale": 0.5, "points": 25,
                 "curl": 0.9, "curl_turns": 3.5, "curl_start": 0.15, "width": 0.5},
    "short":    {"length": 6.0, "variation": 1.5, "wave": 0.8, "cap": 88.0, "scale": 1.3, "points": None, "curl": 0.0, "curl_turns": 0.0, "curl_start": 0.0, "width": 1.0},
    "long":     {"length": 26.0, "variation": 4.0, "wave": 1.2, "cap": 80.0, "scale": 1.1, "points": None, "curl": 0.0, "curl_turns": 0.0, "curl_start": 0.0, "width": 1.0},
}

# The look sets how the cards gather and how the atlas is coloured.  `guide`
# is the Poisson spacing of the cluster centres in centimetres, the Blender
# Guide Distance and Houdini Clump Size semantics (HAIR-117): 4.5 stylised and
# 2.5 realistic are guesses to be tuned by looking.  `jitter` is how far a card
# may stray from its lock's shape, `band` a lighter sweep across the upper
# length, the graphic highlight stylised hair is drawn with, and `ramp` how
# much of the root-to-tip colour range the atlas keeps.
LOOKS = {
    "stylised":  {"guide": 4.5, "jitter": 0.3, "band": 0.3, "ramp": 0.5},
    "realistic": {"guide": 2.5, "jitter": 1.0, "band": 0.0, "ramp": 1.0},
}

# sRGB 0-255, root then tip then the tint of the occasional lighter flyaway.
# sRGB 0-255, root then tip then the flyaway tint.  These are the values from
# before 2026-09-22's lightening, which was compensating for faces wound into
# the head (docs/reference/hair-cards.md): with the winding right, the lighter
# set rendered brown as cream under the sheet's key.
COLOURS = {
    "black":  ((34, 30, 28), (78, 68, 60), (104, 92, 80)),
    "brown":  ((66, 44, 30), (146, 104, 68), (178, 138, 94)),
    "auburn": ((84, 38, 22), (170, 88, 46), (196, 118, 64)),
    "red":    ((112, 44, 18), (196, 96, 42), (222, 138, 68)),
    "blond":  ((132, 100, 54), (222, 186, 122), (240, 218, 166)),
    "grey":   ((104, 102, 100), (168, 166, 164), (196, 194, 192)),
    "white":  ((166, 164, 162), (226, 224, 222), (244, 242, 240)),
}

# The layer stack, inside to outside, for the default 14 cm wavy style before
# the style's scale.  Counts: 60 shells is a guess inside HAIR-087's 100 to 500
# strips for a realistic head and the CC0 VRoid sample's 52 shells (HAIR-150);
# 150 breakup cards are 50 three-card tents (HAIR-002); 40 hairline cards and
# 30 flyaways (HAIR-001).  Widths are constant within a layer (HAIR-013) and
# no source gives one in centimetres, so every width, tip and offset here is a
# guess; the thick-to-thin outward order is HAIR-001 and HAIR-044, and `max`
# is how far a shell may widen with its cluster's spread (HAIR-101).  Points
# per guide follow HAIR-019.  `length` scales the style's length: hairline
# transition cards are short wisps (guess).  `band` names the atlas band;
# shells take slot -1 in the guides file because the Blender side gives them a
# flat material, and use the base band only in the numpy fallback.  `mix` is
# how far the written vertex normal leans from the ribbon frame towards the
# radial: 1.0 for shells (HAIR-020), the rest guesses.  The shell offset is
# --cling, so the flag keeps its old meaning.
LAYERS = (
    {"name": "shell",    "count": 90,  "width": 2.4, "tip": 0.35, "max": 3.5,  "offset": -0.05, "points": 8, "length": 1.0, "band": "base",    "tent": False, "mix": 1.0},
    {"name": "breakup",  "count": 150, "width": 1.4, "tip": 0.5, "max": 1.75, "offset": 0.8,  "points": 6, "length": 1.0, "band": "breakup", "tent": True,  "mix": 0.6},
    {"name": "hairline", "count": 40,  "width": 1.0, "tip": 0.4, "max": 1.25, "offset": 0.3,  "points": 4, "length": 0.6, "band": "sparse",  "tent": False, "mix": 0.6},
    {"name": "flyaway",  "count": 30,  "width": 0.5, "tip": 0.2, "max": 0.6,  "offset": 1.5,  "points": 5, "length": 0.9, "band": "flyaway", "tent": False, "mix": 0.3},
)

# The atlas: a 2:1 sheet with density falling across it (HAIR-018), eight slots
# of 256 px across 2048 with 16 px gaps and 32 px of padding for the baker
# (HAIR-062).  Strands per slot 48 down to 1 were measured by the design pass
# to give mean alphas 0.395 down to 0.015 (output/hair_probe_hybrid/report.json,
# 2026-09-22); strand width 4 px root to 2 px tip keeps HAIR-062's 2 px floor.
ATLAS_SIZE = (2048, 1024)
ATLAS_GAP, ATLAS_DILATE, ATLAS_SLOT = 16, 32, 256
ATLAS_STRANDS = (48, 32, 20, 12, 8, 4, 2, 1)
ATLAS_BANDS = {"base": [0, 1], "breakup": [2, 3, 4], "sparse": [5, 6], "flyaway": [7]}
# waviness, end_low, end_high per band: how much a painted strand wanders and
# the range a strand's tip may end at (guesses).
ATLAS_BAND_LOOK = {"base": (0.25, 0.85, 1.0), "breakup": (0.35, 0.7, 1.0),
                   "sparse": (0.45, 0.55, 0.95), "flyaway": (0.6, 0.4, 0.9)}

# The scalp cap: a dome at the scalp radius plus this offset (guess), bounded
# by the hairline, with a single pole vertex; its maps are square.  14 rings
# of 48 are 1,296 triangles, which with the default cards' 2,820 keeps the
# whole fallback inside HAIR-016's 4k floor (12 rings left it at 3,924,
# measured on the first run).
CAP_OFFSET, CAP_RINGS, CAP_SEGMENTS, CAP_TEXTURE = 0.15, 14, 48, 1024
# The cap diffuse is the root colour darkened so it reads as occluded hair
# (HAIR-047), and its opacity is blurred at the hairline (HAIR-047).
CAP_DARKEN, CAP_BLUR_PX = 0.75, 40

# The whorl sits behind and lateral to the crown (HAIR-106, in words without
# numbers): 18 degrees behind and 8 degrees to the +X side are guesses.
WHORL_BEHIND_DEG, WHORL_ASIDE_DEG = 18.0, 8.0
# The body below the head, as capsules the falling hair slides over, in the
# hair's own frame: centimetres at the 9.5 cm scalp scale, +Y up, +Z the face,
# origin at the scalp centre, scaled with --head-radius.  Measured 2026-09-22
# on the Genesis 9 base figure by height band below the fitted skull centre
# (output/hair/_exp/measure_body.py): the neck 6 to 7.4 cm each side of the
# midline and from 8 cm behind to 5 in front of it, the shoulders 19.4 cm each
# side at 24 cm down and 22.6 at 26, the chest from 13.6 behind to 5.9 in front
# of the scalp centre.  Long hair grown without these splayed outward from its
# exit angle instead of falling down the neck (research/untested.md).
BODY = (
    ("neck", (0.0, -11.0, -1.5), (0.0, -24.0, -1.5), 6.5),
    ("shoulders", (-22.0, -27.0, -4.0), (22.0, -27.0, -4.0), 6.5),
    ("chest", (-12.0, -30.0, -4.0), (-12.0, -50.0, -4.0), 9.0),
    ("chest", (0.0, -30.0, -4.0), (0.0, -50.0, -4.0), 9.0),
    ("chest", (12.0, -30.0, -4.0), (12.0, -50.0, -4.0), 9.0),
)
BODY_SCALE_RADIUS = 9.5      # the scalp radius BODY was measured against
BODY_CLEAR = 0.8             # cm of air between the body and the hair (guess; at 0.5 the
                             # declip on Genesis 9 still found 0.5 percent of a 30 cm
                             # style deeper than its 20 mm reach, 2026-09-22)
# The jaw proxy a beard grows on: an ellipsoid of the lower face in the hair
# frame, centre and radii in cm at the 9.5 cm scalp scale, scaled with
# --head-radius like BODY.  The scalp sphere is far inside the face at the
# jaw, so a root put on it there sits inside the head.  The numbers are
# guesses from the Genesis 9 lower face measured by height band
# (output/hair/_exp/measure_body.py, 2026-09-22: at y -12 the head is x +-7.2
# and z front 12.2, at y -16 z front 11.1, the chin), refined by the fit in
# the report; see JAW_FIT below.
JAW_CENTRE, JAW_RADII = (0.0, -11.1, 2.1), (6.9, 7.2, 9.0)
# Those are a least-squares fit to 1,274 Genesis 9 vertices of the lower face
# (y -18 to -9.5, z above -4.5, ears out) read from output/daz/h_bob.blend
# the way measure_body.py reads the body, radii bounded to 9 cm and vertices
# deeper than 1.5 cm inside (the mouth cavity) clipped: rms 0.63 cm over the
# skin, the chin 1.1 cm outside the ellipsoid and the jaw sides 0.35 cm inside
# it, both within --declip's 20 mm reach (measured 2026-09-22; the z radius
# sits on its bound, since the jaw is a wedge, not an ellipsoid).
# The beard region on that ellipsoid, hair-frame cm at the 9.5 cm scale, from
# the same measurement: the nose base is at y -9.3, the upper lip -9.5 to -11,
# the lower lip -11 to -12.5, the chin -13 to -16.5 and the jaw's underside
# -17.5 (the midline's front drops from z 10.3 at y -17 to 4.9 at -18), the
# jaw angle at z -4 (the jaw side at |x| 5 to 7 spans z -4 to 8 at y -12).
# The beard's top edge runs from under the lower lip at the midline up to the
# mouth-corner line on the cheeks (`cheek_x` is where it rises, a guess), so
# the lower lip is the bare gap between it and the moustache band, which sits
# on the upper lip's skin, front only.  `neckline` trims the beard where the
# ellipsoid meets the neck.  `exit` is the angle a beard hair leaves the skin
# at, in degrees, and `outward` how much of the flow points away from the
# midline (guesses).
BEARD_REGION = {"top_y_mid": -12.5, "top_y_cheek": -11.2, "cheek_x": (2.5, 5.5),
                "jaw_z_back": -4.0, "neckline_y": -17.5,
                "moustache_y": (-11.0, -9.4), "moustache_x": 3.6,
                "exit_deg": 20.0, "outward": 0.25}
# The beards, each a length in cm, its variation, a card count per layer, a
# width scale on LAYERS' widths, a wave and a stand-off by the tip in cm.  All
# guesses: stubble is the cap plus a few flyaways, short adds cards, full adds
# the shell layer (the brief's starting point).  `guide` is the cluster
# spacing in cm, closer than the scalp's 4.5 because the region is smaller.
BEARDS = {
    "stubble": {"length": 0.4, "variation": 0.1, "wave": 0.2, "volume": 0.06, "width": 0.5, "points": 3,
                "cap_alpha": 0.4, "layers": {"shell": 0, "breakup": 0, "hairline": 0, "flyaway": 60}},
    "short":   {"length": 3.0, "variation": 0.6, "wave": 0.5, "volume": 0.4, "width": 0.8, "points": None,
                "cap_alpha": 0.45, "layers": {"shell": 0, "breakup": 220, "hairline": 80, "flyaway": 40}},
    "full":    {"length": 7.0, "variation": 1.5, "wave": 0.6, "volume": 1.0, "width": 1.0, "points": None,
                "cap_alpha": 0.7, "layers": {"shell": 30, "breakup": 90, "hairline": 30, "flyaway": 10}},
}
# `cap_alpha` is the beard cap's opacity where it is full: on the first
# figure renders (2026-09-22) the short and stubble caps read as a flat
# painted patch with a hard edge and the cards barely showed, so a stubble
# lets the skin through, the short beard doubles its cards, and the cap's
# edge blurs over BEARD_CAP_BLUR_PX rather than the scalp's 40 (guesses).
# 130 px of blur and the lower alphas above: at 70 px and 0.85 to 1.0 the
# beard cap read as a dark band with a straight top edge across the cheeks
# on the first figure renders (2026-09-22)
BEARD_GUIDE, BEARD_RIM_DEG, BEARD_CAP_BLUR_PX = 3.0, 10.0, 130
# BODY's neck capsule starts at y -11, lip height, because the nape rises
# that far; on the jaw that puts its top inside the beard region, so a beard
# drapes over the same capsules with the neck starting at the neckline.
BEARD_BODY = tuple((n, (a[0], BEARD_REGION["neckline_y"], a[2]) if n == "neck" else a, b, r)
                   for n, a, b, r in BODY)
# The density mask thins the frontal region to 0.6 (guess; HAIR-118).
FRONT_DENSITY = 0.6
# Cluster pull factor and its root-to-tip shape, and the tip spread in cm, in
# Blender's Clump Hair Curves terms (HAIR-117); the values are guesses.
CLUSTER_PULL, CLUSTER_SHAPE, TIP_SPREAD = 0.8, 0.5, 0.3
# Width is constant over the first 70 percent of the length then tapers (guess).
TAPER_FROM = 0.6
# Bridson's rejection count.
POISSON_K = 30


def unit(v: np.ndarray) -> np.ndarray:
    """Rows normalised, with a zero row left as zero rather than NaN."""
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-12)


def hairline_limit(forward: np.ndarray, hairline: float, cap: float) -> np.ndarray:
    """How far down the scalp hair reaches, in radians from the crown, by azimuth.

    `forward` is +1 at the face, 0 at the ears and -1 at the nape.  Hair does
    not grow on a face, so the limit is `hairline` at the front (48 degrees by
    default), reaches `cap` at the nape (83), and is at 80 percent of the way
    between them at the temples (76), the taper the contract records as
    today's measured shape.  Piecewise linear over forward through those three.
    """
    hairline, cap = np.radians(hairline), np.radians(cap)
    temple = hairline + (cap - hairline) * 0.8
    forward = np.asarray(forward, dtype=np.float64)
    return np.where(forward >= 0, temple + (hairline - temple) * forward,
                    temple + (cap - temple) * (-forward))


def parting_gap(forward: np.ndarray, part_width: float) -> np.ndarray:
    """Half-width of the bare parting line, as an x on the unit sphere, by azimuth.

    It runs from the forehead to the crown and stops, so the gap closes towards
    the nape: carried all the way round at full width it is a bald stripe over
    the crown and down the back of the head.
    """
    return np.sin(np.radians(part_width)) * np.clip((np.asarray(forward) + 0.35) / 1.1, 0.0, 1.0)


def on_scalp(p: np.ndarray, hairline: float, cap: float,
             part: float | None, part_width: float, rim: float | None = None) -> np.ndarray:
    """Which unit directions lie inside the hairline and off the parting line.

    With `rim`, only the band that many degrees inside the hairline counts,
    which is where the hairline transition cards go.
    """
    p = np.atleast_2d(p)
    r = np.hypot(p[:, 0], p[:, 2])
    forward = np.divide(p[:, 2], np.maximum(r, 1e-9))
    theta = np.arccos(np.clip(p[:, 1], -1.0, 1.0))
    limit = hairline_limit(forward, hairline, cap)
    inside = theta <= limit
    if rim is not None:
        inside &= theta >= limit - np.radians(rim)
    if part is not None:
        inside &= np.abs(p[:, 0] - part) >= parting_gap(forward, part_width)
    return inside


def density_mask(p: np.ndarray) -> np.ndarray:
    """Roots per area relative to the crown: 1.0 crown, sides and back, thinner over the front.

    Production root distribution is Poisson disk at a density scaled by a mask
    (HAIR-118).  The frontal region, forward of the ears and below the crown,
    is thinned to FRONT_DENSITY (a guess) so the hairline is not a wall.
    """
    p = np.atleast_2d(p)
    r = np.hypot(p[:, 0], p[:, 2])
    forward = np.divide(p[:, 2], np.maximum(r, 1e-9))
    front = np.clip((forward - 0.2) / 0.4, 0.0, 1.0)
    low = np.clip((np.degrees(np.arccos(np.clip(p[:, 1], -1, 1))) - 20.0) / 15.0, 0.0, 1.0)
    return 1.0 - (1.0 - FRONT_DENSITY) * front * low


def poisson_roots(spacing: float, hairline: float, cap: float, part: float | None,
                  part_width: float, rng: np.random.RandomState,
                  masked: bool = True, rim: float | None = None, k: int = POISSON_K,
                  inside=None) -> np.ndarray:
    """Bridson Poisson-disk sampling of unit directions on the scalp cap.

    `spacing` is the minimum chord between roots on the unit sphere where the
    density mask is 1; where it is d the local spacing is spacing / sqrt(d), so
    the count per area scales with d.  Two points are far enough apart when
    their chord exceeds the larger of their two local spacings.  The standard
    algorithm: keep an active list, take a random active point, try `k`
    candidates in the annulus between one and two spacings along random
    geodesics, keep the first that clears every neighbour, retire the point
    when none does.  Distances are checked against every accepted point rather
    than through a grid: the counts here are hundreds, and numpy does that in
    one line faster than a grid dictionary would.

    `inside` replaces the scalp test with another region on the unit sphere,
    which is how the beard samples the jaw ellipsoid: the same sampler in the
    ellipsoid's own scaled space.
    """
    def local(q):
        return spacing / np.sqrt(density_mask(q)) if masked else np.full(len(q), spacing)

    if inside is None:
        def inside(q):
            q = np.atleast_2d(q)
            return (q[:, 1] > 0) & on_scalp(q, hairline, cap, part, part_width, rim)

    for _ in range(1000):
        first = rng.normal(size=3)
        first /= np.linalg.norm(first)
        if inside(first)[0]:
            break
    else:
        raise ValueError("no scalp: the hairline leaves nothing to grow on")
    points, radii, active = [first], [float(local(first[None])[0])], [0]
    while active:
        slot = rng.randint(len(active))
        p, rp = points[active[slot]], radii[active[slot]]
        # random tangent directions at p, geodesic distances in [r, 2r]
        t = rng.normal(size=(k, 3))
        t -= (t @ p)[:, None] * p
        t = unit(t)
        d = rp * (1.0 + rng.rand(k))
        cand = unit(p[None, :] * np.cos(d)[:, None] + t * np.sin(d)[:, None])
        ok = inside(cand)
        if ok.any():
            arr = np.array(points)
            rc = local(cand)
            dist = np.linalg.norm(cand[:, None, :] - arr[None, :, :], axis=2)
            need = np.maximum(rc[:, None], np.array(radii)[None, :])
            ok &= (dist >= need).all(axis=1)
        hit = np.flatnonzero(ok)
        if len(hit):
            i = int(hit[0])
            points.append(cand[i])
            radii.append(float(rc[i]))
            active.append(len(points) - 1)
        else:
            active.pop(slot)
    return np.array(points)


def poisson_count(count: int, hairline: float, cap: float, part: float | None,
                  part_width: float, rng: np.random.RandomState, masked: bool = True,
                  rim: float | None = None, inside=None, area: float | None = None) -> np.ndarray:
    """Poisson roots at the spacing that yields `count` of them, then exactly `count`.

    The spacing that gives a wanted count is found by running the sampler at a
    guess and rescaling by the square root of the ratio, twice, aiming eight
    percent over; the surplus is then dropped at random, which keeps the blue
    noise where dropping the last accepted points, the gap fillers, would not.
    `inside` and `area` (steradians) describe another region, as for
    poisson_roots.
    """
    if area is None:
        area = 2 * np.pi * (1 - np.cos(np.radians((hairline + cap) / 2)))
    spacing = np.sqrt(area / (0.7 * count))          # 0.7 roots per spacing squared: a first guess
    want = int(round(count * 1.08)) + 1
    if rim is not None:
        spacing *= np.sqrt(rim / 45.0)                # a rim band holds a fraction of the cap
    roots = poisson_roots(spacing, hairline, cap, part, part_width, rng, masked, rim, inside=inside)
    for _ in range(2):
        spacing *= np.sqrt(len(roots) / want)
        roots = poisson_roots(spacing, hairline, cap, part, part_width, rng, masked, rim, inside=inside)
    if len(roots) > count:
        roots = roots[rng.choice(len(roots), count, replace=False)]
    return roots


def fibonacci_roots(n: int, cap: float, hairline: float,
                    part: float | None, part_width: float) -> np.ndarray:
    """The generator's roots before 2026-09-22: a Fibonacci spiral pulled up to the hairline.

    Kept only as the yardstick the report measures the Poisson roots against.
    A root that fell outside the hairline was pulled up to it along its
    meridian, which is what made a rim of roots along the front.
    """
    cap_r, hair_r = np.radians(cap), np.radians(hairline)
    i = np.arange(n, dtype=np.float64) + 0.5
    y = 1.0 - (i / n) * (1.0 - np.cos(cap_r))
    r = np.sqrt(np.maximum(0.0, 1.0 - y * y))
    phi = i * np.pi * (3.0 - np.sqrt(5.0))
    x, z = r * np.cos(phi), r * np.sin(phi)
    forward = np.divide(z, np.maximum(r, 1e-9))
    y = np.maximum(y, np.cos(hair_r + (cap_r - hair_r) * (1 - forward) / 2))
    r = np.sqrt(np.maximum(0.0, 1.0 - y * y))
    x, z = r * np.cos(phi), r * np.sin(phi)
    if part is not None:
        forward = np.divide(z, np.maximum(r, 1e-9))
        gap = parting_gap(forward, part_width)
        side = np.where(x - part >= 0, 1.0, -1.0)
        x = np.clip(part + side * np.maximum(np.abs(x - part), gap), -r, r)
        z = np.sign(z) * np.sqrt(np.maximum(0.0, r * r - x * x))
    return np.column_stack((x, y, z))


def spacing_stats(points: np.ndarray, radius: float) -> dict:
    """Nearest-neighbour distance over the scalp sphere, in cm: mean and coefficient of variation."""
    if len(points) < 2:
        return {"mean_cm": None, "cv": None}
    d = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
    np.fill_diagonal(d, np.inf)
    nn = 2.0 * np.arcsin(np.clip(d.min(axis=1) / 2.0, 0, 1)) * radius
    return {"mean_cm": round(float(nn.mean()), 3),
            "cv": round(float(nn.std() / max(nn.mean(), 1e-9)), 3)}


def whorl_direction() -> np.ndarray:
    """Unit direction of the crown whorl: behind the crown and off to one side."""
    b, a = np.radians(WHORL_BEHIND_DEG), np.radians(WHORL_ASIDE_DEG)
    return unit(np.array([np.sin(a) * np.cos(b), np.cos(a) * np.cos(b), -np.sin(b)]))


def scalp_flow(p: np.ndarray, part: float | None, part_flow: float, cap: float) -> np.ndarray:
    """The tangent a strand leaves the scalp along at root direction `p`.

    Hair leaves the whorl along the great circle away from it, which is
    forward on the mid-scalp and at the hairline, down towards the ears at the
    sides and down to the nape at the back (HAIR-106, in words), and the
    parting is a discontinuity with the hair swept off it either way,
    strongest at the crown and gone by the hairline.  Straight down is added
    lightly so a root on the whorl itself has somewhere to go.
    """
    w = whorl_direction()
    away = -(w - np.dot(w, p) * p)
    down = np.array([0.0, -1.0, 0.0])
    down = down - np.dot(down, p) * p
    flow = unit(away) * 0.85 + down * 0.15
    if part is not None and part_flow:
        top = np.clip((p[1] - np.cos(np.radians(cap))) / max(1.0 - np.cos(np.radians(cap)), 1e-9), 0.0, 1.0)
        side = np.array([1.0 if p[0] >= part else -1.0, 0.0, 0.0])
        sweep = side - np.dot(side, p) * p
        flow = flow + sweep * part_flow * top
    return unit(flow)


def exit_angle(p: np.ndarray, lift: float) -> float:
    """How far off the scalp a strand leaves, in radians, scaled by --lift.

    HAIR-106's angles by region are single-sourced to one clinic page and not
    claimed as numbers; what both its pages agree on is that the angle is
    acute, lowest at the temples and the hairline and highest on the
    mid-scalp.  So this is one smooth curve with that shape: 12 degrees at the
    rim rising to 30 at the crown, all behind one --lift scale.  The first
    bake used 15 to 50 and the crown fanned out like a palm (2026-09-22).
    """
    height = float(np.clip(p[1], 0.0, 1.0))
    return np.radians(lift * (12.0 + 18.0 * height * height))


def strand_path(direction: np.ndarray, flow: np.ndarray, lift: float, radius: float,
                offset: float, length: float, points: int, wave: float, volume: float,
                aside: np.ndarray, lock: np.random.RandomState,
                card: np.random.RandomState, jitter: float,
                body: tuple | None = None, curl: tuple = (0.0, 0.0, 0.0),
                surface: Jaw | None = None, comb: bool = True) -> np.ndarray:
    """One guide: `points` positions from the root, over the scalp first, then falling free.

    A strand leaves along the scalp flow tilted off it by the region's exit
    angle, lies on the scalp while the scalp is still under it, and falls free
    once it is past the head.  Grown along the normal instead, as the first
    draft was, every strand sprays outwards at once: on a 9.5 cm scalp that
    made a 46.6 cm wide spray with a bald crown showing through it.

    THE COMB, and where the falling comes from.  With `comb` the heading is
    blended towards straight down over the strand, which is a comb, not
    gravity: it is where the hair fell before there was a solver.  With
    `comb` off, which is what --settle wants, the heading keeps the styled
    direction, flow and exit angle and --sweep, with no down in it at all,
    and the strand is left standing along its style for settle() to drop.
    Left in under a settle the hair falls twice, once by the comb and once by
    the solver.

    Lying on the scalp is enforced rather than hoped for: every point is pushed
    back out to `offset` centimetres clear of the scalp sphere, so no strand
    passes through the head and the layers keep their thick-to-thin order.

    With `body` as (scale, clearance), a strand that reaches the neck, the
    shoulders or the chest is pushed out of them and slides along them step by
    step, so long hair drapes down the neck and over the shoulders instead of
    splaying outward from its exit angle.

    With `surface`, a Jaw, the strand is a beard hair: `direction` is a unit
    direction in the ellipsoid's scaled space, the root and the normal come
    from it, the exit angle is its fixed one, and the push-out is off the
    ellipsoid rather than the scalp sphere.
    """
    down = np.array([0.0, -1.0, 0.0])
    if surface is None:
        angle, normal, root = exit_angle(direction, lift), direction, direction * (radius + offset)
    else:
        angle, normal, root = surface.exit * lift, surface.normal(direction), surface.point(direction, offset)
    heading0 = flow * np.cos(angle) + normal * np.sin(angle)

    # The lock decides the shape and the card only strays from it, so the cards
    # in a lock move together.  Seeded per card instead, as the first draft was,
    # 320 cards each went their own way and the hair read as a mop.
    def strayed(low, high, spread):
        return lock.uniform(low, high) * (1.0 + jitter * card.uniform(-spread, spread))

    freq1, freq2 = strayed(1.5, 2.5, 0.25), strayed(3.0, 5.0, 0.25)
    amp1 = strayed(0.6, 1.3, 0.3) * wave
    amp2 = strayed(0.15, 0.4, 0.3) * wave
    phase = lock.uniform(0, 2 * np.pi) + jitter * card.uniform(-0.6, 0.6)
    twist = lock.normal(size=3) + jitter * 0.5 * card.normal(size=3)
    twist /= np.linalg.norm(twist) or 1.0
    keep_out = radius + offset

    # The centreline first, then the wave as a displacement from it.  Added to
    # the running point instead, each step's offset lands on top of the last
    # and the wave integrates into a drift: at --wave 2.2 the curly style
    # wandered into a 42.8 cm wide nest round the head (measured 2026-09-22).
    # Hair rooted over the face is brushed out to the sides as it falls, which
    # is why long hair frames a face rather than curtaining it.
    segments = points - 1
    step = length / segments
    spine, headings, contact = [root], [], None
    for i in range(1, segments + 1):
        t = i / segments
        heading = ((1 - t) * heading0 + t * down if comb else heading0) + aside * t
        norm = np.linalg.norm(heading)
        heading = heading / norm if norm > 1e-6 else down.copy()
        if body is not None and contact is not None:
            heading = slide(heading, contact, spine[-1], body[0])
        point = spine[-1] + heading * step
        if body is not None:
            point, contact = body_push(point, body[1], body[0], *body[2:])
        headings.append(heading)
        spine.append(point)

    # A curl is a helix round the centreline, not a wave beside it: radius
    # `c_r` cm, `c_turns` turns over the strand, growing in from `c_start`, with
    # the lock's own phase so a lock's cards spiral together.  The sine wave
    # alone, at any amplitude, read as no curl at all on the figure.
    c_r, c_turns, c_start = curl
    c_phase = lock.uniform(0, 2 * np.pi) + jitter * card.uniform(-0.4, 0.4)
    c_r = c_r * (1.0 + jitter * card.uniform(-0.25, 0.25))
    out = [spine[0]]
    for i in range(1, segments + 1):
        t = i / segments
        heading = headings[i - 1]
        side = np.cross(heading, twist)
        norm = np.linalg.norm(side)
        point = spine[i]
        if norm > 1e-6:
            side = side / norm
            swing = np.cross(heading, side)
            point = point + t * (
                side * (amp1 * np.sin(freq1 * t * np.pi + phase)
                        + amp2 * np.sin(freq2 * t * np.pi + phase * 1.7))
                + swing * amp1 * 0.4 * np.cos(freq1 * t * np.pi + phase))
            if c_r > 0.0 and c_turns > 0.0 and t > c_start:
                grow = min(1.0, (t - c_start) / max(1e-6, 0.5 * (1.0 - c_start)))
                theta = 2.0 * np.pi * c_turns * (t - c_start) / max(1e-6, 1.0 - c_start) + c_phase
                point = point + c_r * grow * (side * np.cos(theta) + swing * np.sin(theta))
        out.append(point)
    if surface is not None:
        return surface.keep_clear(np.array(out), offset, volume)
    return keep_clear(np.array(out), keep_out, volume, body)


def body_push(point: np.ndarray, clearance: float, scale: float, capsules: tuple = BODY):
    """The point pushed out of every body capsule, and the last surface normal it hit."""
    hit = None
    for _, a, b, r in capsules:
        a = np.asarray(a) * scale; b = np.asarray(b) * scale; r = r * scale
        ab = b - a
        t = float(np.clip(np.dot(point - a, ab) / np.dot(ab, ab), 0.0, 1.0))
        d = point - (a + t * ab)
        dist = np.linalg.norm(d)
        if dist < r + clearance:
            n = d / dist if dist > 1e-9 else np.array([0.0, 1.0, 0.0])
            point = a + t * ab + n * (r + clearance)
            hit = n
    return point, hit


def slide(heading: np.ndarray, normal: np.ndarray, point: np.ndarray, scale: float) -> np.ndarray:
    """A heading that no longer points into the body: its component into the
    surface removed, and on the flat top of a shoulder, where that leaves
    nothing, sent forward or back to whichever side the strand is already on,
    which is the side it falls down.  Left to push out along the normal every
    step, a strand meeting the shoulder from above stacks on one spot."""
    into = float(np.dot(heading, normal))
    if into < 0.0:
        heading = heading - into * normal
    norm = np.linalg.norm(heading)
    if norm < 0.3:
        front = 1.0 if point[2] > -4.0 * scale else -1.0
        heading = np.array([0.0, -0.3, front])
        norm = np.linalg.norm(heading)
    return heading / norm


def keep_clear(path: np.ndarray, keep_out: float, volume: float,
               body: tuple | None = None) -> np.ndarray:
    """Every point pushed out to the layer's offset, plus `volume` by the tip,
    and, when `body` is (scale, clearance) or (scale, clearance, capsules),
    out of the body capsules too."""
    t = np.linspace(0.0, 1.0, len(path))
    floor = keep_out + volume * t
    dist = np.linalg.norm(path, axis=1)
    scale = np.where(dist < floor, floor / np.maximum(dist, 1e-9), 1.0)
    path = path * scale[:, None]
    if body is not None:
        path = np.array([body_push(q, body[1], body[0], *body[2:])[0] for q in path])
    return path


def capsule_depth(points: np.ndarray, clearance: float, scale: float,
                  capsules: tuple = BODY) -> np.ndarray:
    """How far inside any body capsule plus `clearance` each point is, in cm; 0 when clear."""
    points = np.atleast_2d(points)
    depth = np.zeros(len(points))
    for _, a, b, r in capsules:
        a = np.asarray(a) * scale; b = np.asarray(b) * scale; r = r * scale
        ab = b - a
        t = np.clip((points - a) @ ab / np.dot(ab, ab), 0.0, 1.0)
        dist = np.linalg.norm(points - (a + t[:, None] * ab), axis=1)
        depth = np.maximum(depth, r + clearance - dist)
    return depth


class Jaw:
    """The lower face as an ellipsoid a beard grows on, beside the scalp sphere.

    Everything the sphere does for the scalp, the ellipsoid does here in its
    own scaled space: a unit direction `q` there is the point centre + q *
    radii on the surface, so the Poisson sampler, the clusters and the tents
    run unchanged on unit directions, and only the placement, the normal, the
    flow and the push-out differ.  Roots are the beard region of the surface
    (BEARD_REGION) less anything inside a body capsule, since the underside of
    the ellipsoid meets the neck; the capsules are BEARD_BODY, whose neck
    starts at the neckline.  The flow is down the face and a little outward,
    and every point is kept `offset` cm clear of the surface the way
    keep_clear keeps hair off the scalp.
    """

    def __init__(self, scale: float, body: tuple | None):
        self.scale = scale
        self.centre = np.array(JAW_CENTRE) * scale
        self.radii = np.array(JAW_RADII) * scale
        self.mean_radius = float(self.radii.mean())
        self.body = (body[0], body[1], BEARD_BODY) if body is not None else None
        self.exit = np.radians(BEARD_REGION["exit_deg"])
        # steradians of the region in the scaled space, by Monte Carlo, for
        # poisson_count's first spacing guess (seeded, so the count is stable)
        probe = unit(np.random.RandomState(3).normal(size=(20000, 3)))
        self.area = 4 * np.pi * float(self.inside(probe).mean())

    def point(self, q: np.ndarray, offset: float = 0.0) -> np.ndarray:
        return self.centre + np.asarray(q) * (self.radii + offset)

    def direction(self, p: np.ndarray) -> np.ndarray:
        return unit((np.asarray(p) - self.centre) / self.radii)

    def normal(self, q: np.ndarray) -> np.ndarray:
        """The surface normal at direction q: the gradient of the ellipsoid, not q itself."""
        return unit(np.asarray(q) / self.radii)

    def region(self, p: np.ndarray) -> np.ndarray:
        """Which world points lie in the beard region (BEARD_REGION, in unscaled cm)."""
        p = np.atleast_2d(p) / self.scale
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        b = BEARD_REGION
        top = np.interp(np.abs(x), b["cheek_x"], [b["top_y_mid"], b["top_y_cheek"]])
        jaw = (y < top) & (y >= b["neckline_y"]) & (z >= b["jaw_z_back"])
        # the moustache narrows towards the nose so it is not a rectangle (guess)
        m0, m1 = b["moustache_y"]
        half = b["moustache_x"] * (1.0 - 0.4 * np.clip((y - m0) / (m1 - m0), 0.0, 1.0))
        moustache = ((y > m0) & (y < m1) & (np.abs(x) < half)
                     & (z > JAW_CENTRE[2] + 0.5 * JAW_RADII[2]))
        return jaw | moustache

    def inside(self, q: np.ndarray, rim: float | None = None) -> np.ndarray:
        """Which unit directions are roots: in the region and clear of the body.

        With `rim` (degrees), only directions within that angle of the region's
        edge count, found by probing eight tangent directions, which is where
        the beard's transition cards go, as the hairline's do on the scalp.
        """
        q = np.atleast_2d(q)
        p = self.point(q)
        ok = self.region(p)
        if self.body is not None:
            ok &= capsule_depth(p, self.body[1], self.body[0], self.body[2]) <= 0.0
        if rim is not None:
            ref = np.where(np.abs(q[:, 1:2]) < 0.9, [[0.0, 1.0, 0.0]], [[1.0, 0.0, 0.0]])
            t1 = unit(np.cross(q, ref))
            t2 = np.cross(q, t1)
            r = np.radians(rim)
            edge = np.zeros(len(q), dtype=bool)
            for a in np.linspace(0.0, 2 * np.pi, 8, endpoint=False):
                probe = unit(np.cos(r) * q + np.sin(r) * (np.cos(a) * t1 + np.sin(a) * t2))
                edge |= ~self.inside(probe)
            ok &= edge
        return ok

    def flow(self, q: np.ndarray) -> np.ndarray:
        """The tangent a beard hair leaves the skin along: down, and a little away from the midline."""
        n = self.normal(q)
        down = np.array([0.0, -1.0, 0.0])
        out = np.array([1.0 if q[0] >= 0 else -1.0, 0.0, 0.0]) * BEARD_REGION["outward"]
        f = down + out
        f = f - np.dot(f, n) * n
        norm = np.linalg.norm(f)
        return f / norm if norm > 1e-6 else unit(np.cross(n, [1.0, 0.0, 0.0]))

    def keep_clear(self, path: np.ndarray, offset: float, volume: float) -> np.ndarray:
        """Every point pushed out to `offset` cm off the surface, plus `volume` by
        the tip, radially in the scaled space, then out of the body capsules."""
        t = np.linspace(0.0, 1.0, len(path))
        radii = self.radii[None, :] + (offset + volume * t)[:, None]
        q = (path - self.centre) / radii
        s = np.linalg.norm(q, axis=1)
        push = np.where(s < 1.0, 1.0 / np.maximum(s, 1e-9), 1.0)
        path = self.centre + q * push[:, None] * radii
        if self.body is not None:
            path = np.array([body_push(p, self.body[1], self.body[0], self.body[2])[0] for p in path])
        return path

    def stand_in(self) -> dict:
        """The ellipsoid as a low-poly mesh for the preview, wound outward."""
        sphere = scalp_sphere(1.0, rings=16, segments=24)
        return {"verts": sphere["verts"] * self.radii + self.centre,
                "normals": unit(sphere["normals"] / self.radii),
                "uvs": sphere["uvs"], "faces": sphere["faces"]}


# THE SETTLE.  Lifted from output/hair/_exp/groom2.py's settle(), the
# position-based solver the Virt-A-Mate work was measured with
# (docs/reference/vam-assets.md, VAM-031, run 2026-09-23): a Verlet step with
# drag, a rigidity pull toward the rest pose with a root-to-tip rolloff,
# inextensible segments solved root first, then a one-sided collision and
# friction.  Two things changed on the way in.  The collision no longer
# queries a scipy cKDTree of a Daz figure's skin.  What bars it is not scipy,
# which is on this host (scipy 1.16.3 on python3, measured 2026-09-23): it is
# the tree's contents.  Guides settled against a Daz figure are Daz-shaped
# geometry, which this repo may not hold, and this script's dependency
# surface is the standard library plus numpy and Pillow, as its docstring
# says.  So the colliders below are this file's own analytic stand-ins: the
# scalp sphere keep_clear holds hair off, the body capsules body_push and
# capsule_depth use, and the jaw ellipsoid Jaw.keep_clear uses.  And the
# solver runs on this file's units, not groom2's.
#
# THE ONE ADAPTOR, and the only place anything is converted: groom2 works in
# metres in the Blender world frame with gravity along -Z.  The four constants
# below convert FROM that frame INTO this file's, which is centimetres with
# +Y up, +Z the face and the origin at the centre of the scalp sphere: a
# length in metres becomes M_TO_CM times itself, and -Z there is SETTLE_DOWN
# here.  Nothing inside settle() or the colliders converts anything: they are
# centimetres and +Y up throughout, and the only number that leaves in
# another unit is the reported move, in millimetres.
M_TO_CM = 100.0
CM_TO_MM = 10.0
SETTLE_DOWN = np.array([0.0, -1.0, 0.0])          # groom2's -Z, in this frame
SETTLE_G_CM = 9.81 * M_TO_CM                      # m/s2 -> cm/s2
SETTLE_STOP_CM = 5e-5 * M_TO_CM                   # groom2's 5e-5 m early-out
SETTLE_MOVING_CM = 1e-3 * M_TO_CM                 # groom2's 1 mm "still moving" test
# The solver's own numbers.  root_rigidity, main_rigidity, tip_rigidity,
# rigidity_rolloff and frames are behind flags; the rest are groom2's values,
# which are the ones read verbatim out of the VaM packages' .vaj storables
# (docs/reference/vam-assets.md, VAM-015, read 2026-09-23).  There is no
# collision radius here: groom2 pushed a point out to 1 mm clear of the skin
# mesh, 6 mm after the first point, and the stand-ins below carry their own
# clearance instead (the layer's offset plus `volume` by the tip off the
# scalp or the jaw, BODY_CLEAR off the body), so a radius on top of that
# would be counted twice.  That is a judgement, not a measurement.
# no wind key: groom2's wind is metres per second squared in the Blender world
# frame and nothing here converts it, so a value set by hand would be 100 times
# too small and point along the wrong axis.  Add it with its conversion or not
# at all.
SETTLE = {"gravity": 1.0, "weight": 1.5,
          "dt": 1.0 / 60, "iterations": 2, "drag": 0.1, "friction": 0.2,
          "bending": 0.0}


def capsule_push(points: np.ndarray, clearance: float, scale: float,
                 capsules: tuple = BODY) -> tuple:
    """body_push over a whole array at once: every point pushed out of every
    body capsule, and which points any capsule pushed.

    The arithmetic is body_push's, capsule by capsule in the same order, so a
    point inside two capsules ends on the last of them, exactly as there.
    Shape (..., 3) in, the same shape out plus a (...) boolean.
    """
    shape = np.shape(points)[:-1]
    p = np.asarray(points, dtype=np.float64).reshape(-1, 3).copy()
    hit = np.zeros(len(p), dtype=bool)
    for _, a, b, r in capsules:
        a = np.asarray(a, dtype=np.float64) * scale
        b = np.asarray(b, dtype=np.float64) * scale
        r = r * scale
        ab = b - a
        t = np.clip((p - a) @ ab / np.dot(ab, ab), 0.0, 1.0)
        axis = a + t[:, None] * ab
        d = p - axis
        dist = np.linalg.norm(d, axis=1)
        inside = dist < r + clearance
        n = np.where(dist[:, None] > 1e-9, d / np.maximum(dist, 1e-9)[:, None],
                     np.array([0.0, 1.0, 0.0]))
        p[inside] = axis[inside] + n[inside] * (r + clearance)
        hit |= inside
    return p.reshape(*shape, 3), hit.reshape(shape)


class ScalpCollider:
    """What the settle collides with on the head: the scalp sphere and the body.

    `floor` is the radius each point is held out to, the one keep_clear uses
    (the layer's offset plus `volume` by the tip), as an (n, m) array in
    centimetres; `body` is keep_clear's (scale, clearance) or
    (scale, clearance, capsules), or None when --no-drape.
    """

    def __init__(self, floor: np.ndarray, body: tuple | None):
        self.floor = np.asarray(floor, dtype=np.float64)
        self.body = body

    def push(self, X: np.ndarray) -> tuple:
        dist = np.linalg.norm(X, axis=2)
        low = dist < self.floor
        X = X * np.where(low, self.floor / np.maximum(dist, 1e-9), 1.0)[:, :, None]
        hit = low
        if self.body is not None:
            X, capped = capsule_push(X, self.body[1], self.body[0], *self.body[2:])
            hit = hit | capped
        return X, hit


class JawCollider:
    """What a beard's settle collides with: the jaw ellipsoid and the body.

    `offset` is each card's stand-off from the surface in centimetres, an
    (n, 1) array, and the push is Jaw.keep_clear's, radially in the
    ellipsoid's own scaled space.
    """

    def __init__(self, jaw: Jaw, offset: np.ndarray, volume: float, points: int):
        t = np.linspace(0.0, 1.0, points)
        self.jaw = jaw
        self.radii = jaw.radii[None, None, :] + (np.asarray(offset, dtype=np.float64)
                                                 + volume * t[None, :])[:, :, None]

    def push(self, X: np.ndarray) -> tuple:
        q = (X - self.jaw.centre) / self.radii
        s = np.linalg.norm(q, axis=2)
        low = s < 1.0
        X = self.jaw.centre + q * np.where(low, 1.0 / np.maximum(s, 1e-9), 1.0)[:, :, None] * self.radii
        hit = low
        if self.jaw.body is not None:
            X, capped = capsule_push(X, self.jaw.body[1], self.jaw.body[0], self.jaw.body[2])
            hit = hit | capped
        return X, hit


def settle(X: np.ndarray, sim: dict, collider) -> tuple:
    """Position-based settle of every strand, in the order vkit says VaM's
    solver runs (read, not run, 2026-09-23): Verlet step with drag, a rigidity
    pull toward the PLANTED pose (root rigidity at point 1, then tip + (main -
    tip) * (1 - (i-1)/(n-2))^rolloff), inextensible segments root-first, then a
    one-sided collision with `collider` whose friction damps the point.  X is
    (n, m, 3) centimetres in the hair frame, root first.  Returns the settled
    X, the numbers to report and the per-strand arrays behind them.
    """
    n, m, _ = X.shape
    rest = X.copy()
    L = np.linalg.norm(np.diff(X, axis=1), axis=2)                  # rest segment lengths (n, m-1)
    i = np.arange(m)
    rig = np.zeros(m)
    rig[1] = sim.get("root_rigidity", 0.2)
    if m > 2:
        rig[2:] = sim.get("tip_rigidity", 0.0) \
            + (sim.get("main_rigidity", 0.75) - sim.get("tip_rigidity", 0.0)) \
            * (1.0 - (i[2:] - 1) / (m - 2)) ** sim.get("rigidity_rolloff", 2.0)
    bend = sim.get("bending", 0.0)
    G = SETTLE_DOWN * SETTLE_G_CM * sim.get("gravity", 1.0) * sim.get("weight", 1.5) \

    dt, its = sim.get("dt", 1.0 / 60), int(sim.get("iterations", 2))
    drag, fric = sim.get("drag", 0.1), sim.get("friction", 0.2)
    V = np.zeros_like(X)
    hit_share, moved, mv = 0.0, [], np.zeros(n)
    for frame in range(int(sim.get("frames", 240))):
        Xf = X.copy()
        for it in range(its):
            V *= (1.0 - drag / its)
            Xp = X + V * dt + G * dt * dt
            Xp[:, 0] = X[:, 0]
            # rigidity toward the planted pose (VaM: relative to the root, not a bend angle)
            Xp = Xp + rig[None, :, None] * (rest - Xp)
            if bend > 0:
                for k in range(2, m):
                    d = Xp[:, k - 1] - Xp[:, k - 2]
                    d /= np.maximum(np.linalg.norm(d, axis=1), 1e-9)[:, None]
                    Xp[:, k] += bend * (Xp[:, k - 1] + d * L[:, k - 1:k] - Xp[:, k])
            for k in range(1, m):
                d = Xp[:, k] - Xp[:, k - 1]
                d /= np.maximum(np.linalg.norm(d, axis=1), 1e-9)[:, None]
                Xp[:, k] = Xp[:, k - 1] + d * L[:, k - 1:k]
            pushed, hit = collider.push(Xp)
            Xp[:, 1:] = pushed[:, 1:]                   # the root stays where it grew
            hit[:, 0] = False
            V = (Xp - X) / dt
            V[hit] *= max(0.0, 1.0 - fric)
            X = Xp
        hit_share = float(hit[:, 1:].mean())
        mv = np.abs(X - Xf).max(axis=(1, 2))
        moved.append(float(np.percentile(mv, 99)))
        if frame > 30 and moved[-1] < SETTLE_STOP_CM:
            break
    still = mv > SETTLE_MOVING_CM
    seg = np.diff(X, axis=1)
    s = np.linalg.norm(seg, axis=2)
    u = seg / np.maximum(s, 1e-9)[:, :, None]
    bends = (np.degrees(np.arccos(np.clip((u[:, :-1] * u[:, 1:]).sum(2), -1, 1))).mean(axis=1)
             if m > 2 else np.zeros(n))
    reach = np.linalg.norm(X[:, -1] - X[:, 0], axis=1) / s.sum(1)
    lift = np.degrees(np.arccos(np.clip((u[:, 0] * (rest[:, 1] - rest[:, 0]) / L[:, :1]).sum(1), -1, 1)))
    raw = {"strands": n, "length_cm": s.sum(1), "reach": reach, "lift_deg": lift,
           "turn_deg": bends, "moving": still, "hit_share": hit_share}
    return X, {"frames": len(moved), "last_frame_p99_move_mm": round(moved[-1] * CM_TO_MM, 3),
               "share_moving_over_1mm": round(float(still.mean()), 4),
               "turn_deg": round(float(bends.mean()), 1),
               "root_segment_off_normal_deg": round(float(lift.mean()), 1),
               "reach_over_length_median": round(float(np.median(reach)), 3),
               "length_cm_median": round(float(np.median(s.sum(1))), 2),
               "last_frame_hit_share": round(hit_share, 4)}, raw


def settle_sim(args) -> dict:
    """The solver's numbers: SETTLE, plus the five the flags carry."""
    return dict(SETTLE, root_rigidity=args.root_rigidity, main_rigidity=args.main_rigidity,
                tip_rigidity=args.tip_rigidity, rigidity_rolloff=args.rigidity_rolloff,
                frames=args.settle_frames)


def settle_cards(args, cards: list, layers: list, shape: dict, body: tuple | None,
                 jaw: Jaw | None, radius: float) -> dict:
    """Settle every card in place, one layer at a time, and report the lot.

    A layer is the natural batch: its cards all carry the same number of
    points, which is what the solver needs to run them as one array.  Each
    layer's collider is built from the numbers that layer's own push-out
    used, so the settle holds the hair exactly where keep_clear and
    Jaw.keep_clear left it and no closer to the head.
    """
    sim = settle_sim(args)
    per_layer, raws = {}, []
    for li, layer in enumerate(layers):
        group = [c for c in cards if c["layer"] == li]
        if not group or len(group[0]["path"]) < 2:
            continue
        X = np.array([c["path"] for c in group], dtype=np.float64)
        offset = np.array([[c["offset_cm"]] for c in group], dtype=np.float64)
        points = X.shape[1]
        if jaw is None:
            t = np.linspace(0.0, 1.0, points)[None, :]
            collider = ScalpCollider(radius + offset + shape["volume"] * t, body)
        else:
            collider = JawCollider(jaw, offset, shape["volume"], points)
        X, info, raw = settle(X, sim, collider)
        for card, path in zip(group, X):
            card["path"] = path
        per_layer[layer["name"]] = info
        raws.append(raw)
    if not raws:
        return {"ran": False}
    strands = sum(r["strands"] for r in raws)
    joined = {k: np.concatenate([r[k] for r in raws])
              for k in ("length_cm", "reach", "lift_deg", "turn_deg", "moving")}
    report = {"frames": max(v["frames"] for v in per_layer.values()),
              "last_frame_p99_move_mm": max(v["last_frame_p99_move_mm"] for v in per_layer.values()),
              "share_moving_over_1mm": round(float(joined["moving"].mean()), 4),
              "turn_deg": round(float(joined["turn_deg"].mean()), 1),
              "root_segment_off_normal_deg": round(float(joined["lift_deg"].mean()), 1),
              "reach_over_length_median": round(float(np.median(joined["reach"])), 3),
              "length_cm_median": round(float(np.median(joined["length_cm"])), 2),
              "last_frame_hit_share": round(float(sum(r["hit_share"] * r["strands"] for r in raws)
                                                  / max(strands, 1)), 4)}
    return {"ran": True, "strands": strands,
            "sim": {k: (list(v) if isinstance(v, tuple) else v) for k, v in sim.items()},
            "report": report, "per_layer": per_layer}


def cluster_pull(path: np.ndarray, centre: np.ndarray, spread: np.ndarray) -> np.ndarray:
    """A member guide pulled towards its cluster's centre guide, root to tip, then spread at the tip.

    Blender's Clump Hair Curves and Houdini's clump node pull each curve
    towards its centre by a factor shaped root to tip and add a random tip
    spread (HAIR-117).  The shape is read as an exponent on t: 0.5 is linear,
    lower pulls late, higher pulls early.  The root stays where it grew.
    """
    t = np.linspace(0.0, 1.0, len(path))
    weight = CLUSTER_PULL * t ** (2.0 ** (1.0 - 2.0 * CLUSTER_SHAPE))
    pulled = path + weight[:, None] * (centre - path)
    return pulled + t[:, None] * spread[None, :]


def widths_along(width_root: float, width_tip: float, n: int) -> np.ndarray:
    """Full card width at each of n points: constant, then a linear taper from TAPER_FROM."""
    t = np.linspace(0.0, 1.0, n)
    k = np.clip((t - TAPER_FROM) / (1.0 - TAPER_FROM), 0.0, 1.0)
    return width_root * (1 - k) + width_tip * k


def ribbon(path: np.ndarray, widths: np.ndarray, u0: float, u1: float, uflip: bool,
           mix: float) -> tuple:
    """A guide widened into a two-vertex-wide ribbon with UVs, normals and outward faces.

    The ribbon's face lies along the scalp and points away from the head, so a
    card reads as a sheet of hair rather than a wire.  The written vertex
    normal leans from the ribbon frame towards the radial by `mix`, the numpy
    stand-in for the Blender side's dome transfer (HAIR-020).

    Faces are (a, d, b), (a, c, d) with `a` on the plus side, whose geometric
    normal is cross(side, tangent), the outward one.  The generator at commit
    1fdbb72 wrote (a, b, d), (a, d, c), the inverse, and Cycles lit every card
    from inside the head (docs/reference/hair-cards.md, measured 2026-09-22).
    """
    n = len(path)
    t = np.linspace(0.0, 1.0, n)
    tangents = np.empty_like(path)
    tangents[0] = path[1] - path[0]
    tangents[-1] = path[-1] - path[-2]
    tangents[1:-1] = path[2:] - path[:-2]
    tangents = unit(tangents)
    radial = unit(path)
    sides = np.cross(tangents, radial)
    bad = np.linalg.norm(sides, axis=1) < 1e-6
    sides[bad] = np.array([1.0, 0.0, 0.0])
    sides = unit(sides)
    normals = unit(np.cross(sides, tangents))
    half = (widths / 2)[:, None]
    verts = np.empty((2 * n, 3))
    verts[0::2] = path + sides * half
    verts[1::2] = path - sides * half
    vnorms = np.empty((2 * n, 3))
    vnorms[0::2] = vnorms[1::2] = unit(normals * (1 - mix) + radial * mix)
    left, right = (u1, u0) if uflip else (u0, u1)
    uvs = np.empty((2 * n, 2))
    uvs[0::2] = np.column_stack((np.full(n, left), t))
    uvs[1::2] = np.column_stack((np.full(n, right), t))
    faces = []
    for i in range(n - 1):
        a, b = 2 * i, 2 * i + 1
        c, d = 2 * (i + 1), 2 * (i + 1) + 1
        faces.append((a, d, b))
        faces.append((a, c, d))
    return verts, uvs, vnorms, faces


def atlas_plan(colour_root, colour_tip, band: float, ramp: float) -> dict:
    """The eight-slot density ladder the atlas painters follow, numpy's and Blender's alike."""
    slots = []
    for i, strands in enumerate(ATLAS_STRANDS):
        name = next(b for b, ids in ATLAS_BANDS.items() if i in ids)
        waviness, end_low, end_high = ATLAS_BAND_LOOK[name]
        slots.append({"index": i, "band": name, "x0": i * ATLAS_SLOT,
                      "x1": i * ATLAS_SLOT + ATLAS_SLOT - ATLAS_GAP,
                      "y0": 0, "y1": ATLAS_SIZE[1], "strands": strands, "waviness": waviness,
                      "end_low": end_low, "end_high": end_high,
                      "strand_width_px_root": 4, "strand_width_px_tip": 2})
    return {"size": list(ATLAS_SIZE), "gap_px": ATLAS_GAP, "dilate_px": ATLAS_DILATE,
            "slots": slots, "bands": {k: list(v) for k, v in ATLAS_BANDS.items()},
            "colour": {"root": [round(float(c), 4) for c in colour_root],
                       "tip": [round(float(c), 4) for c in colour_tip],
                       "band": band, "ramp": ramp}}


def assign_slots(cards: list, plan: dict) -> None:
    """Atlas slots per card: from the layer's band, and no two neighbours of one lock alike.

    Within each lock and band the cards are walked round by azimuth and each
    takes the first slot it prefers that its predecessor did not take, so
    consecutive cards of a lock differ whenever the band has more than one
    slot; the flyaway band has one, so its cards alternate the U mirror
    instead.  A tent's base card prefers the band's first slot, its densest,
    and the two on top the next two (HAIR-002); a plain card prefers the slots
    in turn.
    """
    groups: dict = {}
    for i, c in enumerate(cards):
        groups.setdefault((c["lock"], c["band"]), []).append(i)
    for (lock, band), members in groups.items():
        ids = list(plan["bands"][band])
        members.sort(key=lambda i: np.arctan2(cards[i]["root"][0], cards[i]["root"][2]))
        previous = None
        for k, i in enumerate(members):
            card = cards[i]
            if card["tent"] >= 0:
                prefer = [ids[min(card["tent_rank"], len(ids) - 1)]] + ids
            else:
                prefer = ids[k % len(ids):] + ids[:k % len(ids)]
            card["slot"] = next((s for s in prefer if s != previous), prefer[0])
            card["uflip"] = int(k % 2)
            previous = card["slot"]


def dome_mesh(limit, place, normal_of) -> dict:
    """A dome of CAP_RINGS by CAP_SEGMENTS with one pole vertex, bounded by `limit`.

    The dome is built on the unit sphere about its +Y pole, `limit(forward)`
    giving its reach in radians by azimuth (`forward` +1 at the face, -1
    behind), `place(d)` putting a unit direction in the world and `normal_of(d)`
    giving its normal there.  Its UV is the top-down view: the pole at the
    centre, the rim on the unit circle, the face towards the top of the image,
    so a texel's place on the surface is its angle from the pole as a fraction
    of the local limit.  Faces are wound outward.
    """
    pole = np.array([0.0, 1.0, 0.0])
    verts, uvs, normals = [place(pole)], [(0.5, 0.5)], [normal_of(pole)]
    for i in range(1, CAP_RINGS + 1):
        for j in range(CAP_SEGMENTS):
            phi = 2 * np.pi * j / CAP_SEGMENTS
            forward = np.sin(phi)
            theta = float(limit(forward)) * i / CAP_RINGS
            d = np.array([np.sin(theta) * np.cos(phi), np.cos(theta), np.sin(theta) * np.sin(phi)])
            verts.append(place(d))
            normals.append(normal_of(d))
            rho = 0.5 * i / CAP_RINGS
            uvs.append((0.5 + rho * np.cos(phi), 0.5 + rho * np.sin(phi)))
    faces = []
    ring = lambda i, j: 1 + (i - 1) * CAP_SEGMENTS + (j % CAP_SEGMENTS)
    # The pole fan runs the other way round from the quads: pole, next, this,
    # or its 48 faces point into the head (measured -1.0 on the first run).
    for j in range(CAP_SEGMENTS):
        faces.append((0, ring(1, j + 1), ring(1, j)))
    for i in range(1, CAP_RINGS):
        for j in range(CAP_SEGMENTS):
            a, b, c, d = ring(i, j), ring(i, j + 1), ring(i + 1, j + 1), ring(i + 1, j)
            faces.append((a, b, c))
            faces.append((a, c, d))
    return {"verts": np.array(verts), "uvs": np.array(uvs), "normals": np.array(normals),
            "faces": faces}


def cap_mesh(radius: float, hairline: float, cap: float) -> dict:
    """The scalp cap: a dome on the scalp sphere bounded by the hairline, with one pole vertex.

    Every workflow read has a cap under the cards (HAIR-008).  It sits at the
    cling radius plus CAP_OFFSET on the repo's own sphere, never shrinkwrapped
    to a Daz head, and reaches the shaped hairline at its rim; normals are
    radial.
    """
    return dome_mesh(lambda forward: hairline_limit(forward, hairline, cap),
                     lambda d: d * radius, lambda d: d)


# The beard cap is a dome from the bottom of the jaw ellipsoid, so the dome
# frame's +Y pole is the ellipsoid's -Y and its +X is the ellipsoid's -X: a
# half turn about Z, which keeps the face at +Z and the winding outward.
BEARD_DOME_TURN = np.array([-1.0, -1.0, 1.0])


def beard_limit(forward: np.ndarray) -> np.ndarray:
    """How far up the jaw the beard cap reaches, in radians from the chin, by azimuth.

    The mouth line everywhere, rising to the top of the moustache band at the
    front, each 3 degrees further so the opacity's blurred edge sits on the
    mesh (guess).  The maps cut the exact region.
    """
    b = BEARD_REGION
    mouth = np.arccos(-(b["top_y_cheek"] - JAW_CENTRE[1]) / JAW_RADII[1]) + np.radians(3.0)
    top = np.arccos(-(b["moustache_y"][1] - JAW_CENTRE[1]) / JAW_RADII[1]) + np.radians(3.0)
    return mouth + (top - mouth) * np.clip((np.asarray(forward, dtype=np.float64) - 0.3) / 0.4, 0.0, 1.0)


def beard_cap_mesh(jaw: Jaw) -> dict:
    """The beard cap: the beard region of the jaw ellipsoid, CAP_OFFSET out, as a dome from the chin.

    The ellipsoid's bottom sits inside the neck (its pole is at y -18.3, the
    neck's front at z 5), so the rings below the neckline, which the opacity
    map leaves transparent, are pushed out of the beard's body capsules like
    a strand: worn without that, 110 of the cap's vertices stayed deeper than
    --declip's 20 mm reach; pushed above the neckline too, the cap stood 8 mm
    off the neck at the jaw angle as a visible flap (both 2026-09-22).
    """
    cap = dome_mesh(beard_limit, lambda d: jaw.point(d * BEARD_DOME_TURN, CAP_OFFSET),
                    lambda d: jaw.normal(d * BEARD_DOME_TURN))
    if jaw.body is not None:
        neckline = BEARD_REGION["neckline_y"] * jaw.scale
        cap["verts"] = np.array([body_push(v, CAP_OFFSET, jaw.body[0], jaw.body[2])[0] if v[1] < neckline else v
                                 for v in cap["verts"]])
    return cap


def blur(img: np.ndarray, px: int) -> np.ndarray:
    """A separable box blur run three times, which is close to a Gaussian of about `px`."""
    if px < 1:
        return img
    out = img.astype(np.float32)
    w = max(1, px // 3) * 2 + 1
    for _ in range(3):
        for axis in (0, 1):
            pad = [(0, 0)] * out.ndim
            pad[axis] = (w // 2, w // 2)
            padded = np.pad(out, pad, mode="constant")   # outside the image is outside the cap
            csum = np.cumsum(padded, axis=axis)
            csum = np.concatenate([np.zeros_like(np.take(csum, [0], axis=axis)), csum], axis=axis)
            out = (np.take(csum, range(w, w + out.shape[axis]), axis=axis)
                   - np.take(csum, range(0, out.shape[axis]), axis=axis)) / w
    return out


def dome_uv(limit) -> tuple:
    """Every texel of a CAP_TEXTURE square map as a unit direction in the dome frame.

    Returns the directions, the texel's radius on the UV disc (1 at the rim)
    and its `forward`, the same top-down view dome_mesh lays out.
    """
    size = CAP_TEXTURE
    v, u = np.mgrid[0:size, 0:size]
    # image row 0 is the top, which is UV v = 1, the face
    uu = (u + 0.5) / size - 0.5
    vv = 0.5 - (v + 0.5) / size
    rho = np.hypot(uu, vv) * 2.0
    phi = np.arctan2(vv, uu)
    forward = np.sin(phi)
    theta = limit(forward) * np.minimum(rho, 1.0)
    dirs = np.stack([np.sin(theta) * np.cos(phi), np.cos(theta), np.sin(theta) * np.sin(phi)], axis=-1)
    return dirs, rho, forward


def follicle_strokes(diffuse: np.ndarray, base: np.ndarray, origin: tuple, towards: bool,
                     rng: np.random.RandomState) -> None:
    """Short follicle strokes painted into `diffuse`, in UV, heading away from
    `origin` (the whorl on the scalp) or towards it (the chin on a beard, where
    hair runs down to the pole at the map's centre)."""
    size = diffuse.shape[0]
    count = 9000
    su, sv = rng.uniform(-0.5, 0.5, count), rng.uniform(-0.5, 0.5, count)
    keep = np.hypot(su, sv) < 0.5
    su, sv = su[keep], sv[keep]
    du, dv = su - origin[0], sv - origin[1]
    norm = np.maximum(np.hypot(du, dv), 1e-6)
    sign = -1.0 if towards else 1.0
    du, dv = sign * du / norm, sign * dv / norm
    ang = rng.uniform(-0.35, 0.35, len(su))
    du, dv = du * np.cos(ang) - dv * np.sin(ang), du * np.sin(ang) + dv * np.cos(ang)
    length = rng.uniform(0.012, 0.035, len(su))
    tone = rng.uniform(0.8, 1.25, len(su))
    steps = np.linspace(0.0, 1.0, 24)
    for k in range(len(su)):
        pu = su[k] + du[k] * length[k] * steps
        pv = sv[k] + dv[k] * length[k] * steps
        col = np.clip(((pu + 0.5) * size).astype(int), 0, size - 1)
        row = np.clip(((0.5 - pv) * size).astype(int), 0, size - 1)
        diffuse[row, col] = np.clip(base * tone[k], 0, 1)


def to_images(diffuse: np.ndarray, mask: np.ndarray) -> tuple:
    """The diffuse as RGB and the mask in all four channels, so an importer
    reading either Alpha or Colour gets it."""
    mask8 = (mask * 255).astype(np.uint8)
    return (Image.fromarray((diffuse * 255).astype(np.uint8), mode="RGB"),
            Image.fromarray(np.dstack([mask8] * 4), mode="RGBA"))


def cap_textures(root_rgb: np.ndarray, hairline: float, cap: float, part: float | None,
                 part_width: float, rng: np.random.RandomState) -> tuple:
    """The cap's diffuse and opacity, in the dome's top-down UV.

    Diffuse: the root colour darkened by CAP_DARKEN so it reads as occluded
    hair, with short follicle strokes flowing away from the whorl, because an
    exposed scalp wants clearly defined follicles and not a colour fill
    (HAIR-047, HAIR-048); a lighter line along the parting, where scalp shows.
    Opacity: one inside the hairline, blurred over CAP_BLUR_PX at the rim so
    the cap blends into the head (HAIR-047), and written into all four
    channels so an importer reading either Alpha or Colour gets the mask.
    """
    size = CAP_TEXTURE
    dirs, rho, forward = dome_uv(lambda f: hairline_limit(f, hairline, cap))
    base = root_rgb * CAP_DARKEN
    diffuse = np.broadcast_to(base, (size, size, 3)).astype(np.float32).copy()
    # follicle strokes: short lines from random texels, heading away from the whorl in UV
    w = whorl_direction()
    wu, wv = 0.5 * (np.degrees(np.arctan2(np.hypot(w[0], w[2]), w[1])) / 70.0) * np.array([w[0], w[2]]) / max(np.hypot(w[0], w[2]), 1e-9)
    follicle_strokes(diffuse, base, (wu, wv), False, rng)
    if part is not None:
        gap = parting_gap(forward, part_width) * 0.5
        line = np.abs(dirs[..., 0] - part) < gap
        diffuse[line] = np.clip(diffuse[line] * 1.3 + 0.02, 0, 1)

    inside = (rho <= 1.0).astype(np.float32)
    mask = np.clip(blur(inside, CAP_BLUR_PX) * inside, 0, 1)
    # the parting is a bare line, so the cap is a touch thinner there too
    if part is not None:
        mask = np.where(line, mask * 0.85, mask)
    return to_images(diffuse, mask)


def beard_cap_textures(root_rgb: np.ndarray, jaw: Jaw, alpha: float,
                       rng: np.random.RandomState) -> tuple:
    """The beard cap's diffuse and opacity: the same darkened root colour and
    follicle strokes as the scalp cap, the strokes running down to the chin,
    and an opacity that is `alpha` over the beard region and blurred to
    nothing at the region's edge (HAIR-047), so the cap's own rim never
    shows."""
    size = CAP_TEXTURE
    dirs, rho, _ = dome_uv(beard_limit)
    base = root_rgb * CAP_DARKEN
    diffuse = np.broadcast_to(base, (size, size, 3)).astype(np.float32).copy()
    follicle_strokes(diffuse, base, (0.0, 0.0), True, rng)
    world = jaw.point(dirs.reshape(-1, 3) * BEARD_DOME_TURN)
    inside = (jaw.region(world).reshape(size, size) & (rho <= 1.0)).astype(np.float32)
    mask = np.clip(blur(inside, BEARD_CAP_BLUR_PX) * inside, 0, 1) * alpha
    return to_images(diffuse, mask)


def paint_atlas(plan: dict, band: float, ramp: float, rng: np.random.RandomState) -> tuple:
    """The numpy fallback atlas: the plan's eight slots painted as thin strands, root at the bottom.

    Each slot draws its planned count of strands at random columns, each 4 px
    wide at the root and 2 at the tip (HAIR-062's floor), wandering by the
    band's waviness and ending at a random height in [end_low, end_high].
    The diffuse is the root-to-tip ramp everywhere in the slot, strands
    tinted on top, so the colour under alpha zero is already hair colour and
    filtering never pulls a background into strand edges (HAIR-054).  Row 0
    of the image is the tip end: image V = 0 is the bottom row everywhere the
    maps are read, so the root colour goes on the last row.
    """
    width, height = plan["size"]
    root_rgb, tip_rgb = (np.array(plan["colour"][k], dtype=np.float32) for k in ("root", "tip"))
    diffuse = np.zeros((height, width, 3), dtype=np.float32)
    alpha = np.zeros((height, width), dtype=np.float32)
    v = 1.0 - np.arange(height) / (height - 1)                 # 1 at the top row, 0 at the root
    colour = root_rgb[None, :] * (1 - v)[:, None] + tip_rgb[None, :] * v[:, None]
    # Stylised hair carries less range along a strand and puts the contrast in
    # a highlight band instead, so `ramp` pulls root and tip towards their
    # mean and `band` lays one lighter sweep across the upper length.
    colour = colour.mean(axis=0)[None, :] + (colour - colour.mean(axis=0)[None, :]) * ramp
    colour = colour * (1.0 + band * np.exp(-(((v - 0.34) / 0.2) ** 2)))[:, None]
    rows = np.arange(height)
    for slot in plan["slots"]:
        x0, x1 = slot["x0"], slot["x1"]
        diffuse[:, x0:x1] = np.clip(colour, 0, 1)[:, None, :]
        for _ in range(slot["strands"]):
            centre = rng.uniform(x0 + 6, x1 - 6)
            end = rng.uniform(slot["end_low"], slot["end_high"])
            amp = slot["waviness"] * rng.uniform(4.0, 14.0)
            freq, phase = rng.uniform(0.8, 2.2), rng.uniform(0, 2 * np.pi)
            tint = rng.uniform(0.82, 1.18)
            xc = centre + amp * np.sin(freq * np.pi * v + phase) * v
            w = slot["strand_width_px_root"] * (1 - v) + slot["strand_width_px_tip"] * v
            fade = np.clip((end - v) / 0.05, 0, 1)
            cols = np.clip(np.floor(xc).astype(int)[:, None] + np.arange(-8, 9)[None, :], x0, x1 - 1)
            cover = np.clip(w[:, None] / 2 + 0.5 - np.abs(cols - xc[:, None]), 0, 1) * fade[:, None]
            r = np.repeat(rows[:, None], cols.shape[1], axis=1)
            live = cover > alpha[r, cols]
            alpha[r[live], cols[live]] = cover[live]
            strong = cover > 0.5
            diffuse[r[strong], cols[strong]] = np.clip(colour[r[strong]] * tint, 0, 1)
    mask = (alpha * 255).astype(np.uint8)
    return (Image.fromarray((diffuse * 255).astype(np.uint8), mode="RGB"),
            Image.fromarray(np.dstack([mask] * 4), mode="RGBA"))


def write_groups(path: Path, mtl: str, objects: list, header: list[str]) -> None:
    """One OBJ from a list of (object name, [(material, mesh), ...]).

    A mesh is a dict of verts, uvs, normals and zero-based faces.  Every
    object's groups are written in list order under one `o`, one `usemtl`
    each, which is the layout the Blender side writes too, so either file
    drops into --wear-obj: `o hair` with the cap, then the shells, then the
    cards, inside to outside.
    """
    with path.open("w") as fh:
        for line in header:
            fh.write(f"# {line}\n")
        fh.write(f"mtllib {mtl}\n")
        for oname, groups in objects:
            for _, mesh in groups:
                for x, y, z in mesh["verts"]:
                    fh.write(f"v {x:.5f} {y:.5f} {z:.5f}\n")
        for oname, groups in objects:
            for _, mesh in groups:
                for u, w in mesh["uvs"]:
                    fh.write(f"vt {u:.5f} {w:.5f}\n")
        for oname, groups in objects:
            for _, mesh in groups:
                for x, y, z in mesh["normals"]:
                    fh.write(f"vn {x:.5f} {y:.5f} {z:.5f}\n")
        base = 1
        for oname, groups in objects:
            fh.write(f"o {oname}\n")
            for material, mesh in groups:
                fh.write(f"usemtl {material}\n")
                for a, b, c in mesh["faces"]:
                    a, b, c = a + base, b + base, c + base
                    fh.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")
                base += len(mesh["verts"])


def material_text(name: str, diffuse: str | None, opacity: str | None,
                  kd=(1.0, 1.0, 1.0), ks=0.35, ns=430.0) -> str:
    lines = [f"newmtl {name}", "Ka 1.000 1.000 1.000",
             "Kd " + " ".join(f"{c:.3f}" for c in kd), f"Ks {ks:.3f} {ks:.3f} {ks:.3f}",
             f"Ns {ns:.1f}", "illum 2", "d 1.0"]
    if diffuse:
        lines.append(f"map_Kd {diffuse}")
    if opacity:
        lines.append(f"map_d {opacity}")
    return "\n".join(lines) + "\n"


def body_stand_in(scale: float, capsules: tuple = BODY) -> dict:
    """The body capsules as a run of low-poly spheres along each axis, for the preview."""
    verts, normals, faces = [], [], []
    for _, a, b, r in capsules:
        a = np.asarray(a) * scale; b = np.asarray(b) * scale; r = r * scale
        n = max(2, int(np.ceil(np.linalg.norm(b - a) / (r * 0.6))) + 1)
        for k in range(n):
            c = a + (b - a) * (k / (n - 1))
            sphere = scalp_sphere(r, rings=8, segments=12)
            base = len(verts)
            verts.extend(v + c for v in sphere["verts"])
            normals.extend(sphere["normals"])
            faces.extend((i + base, j + base, k2 + base) for i, j, k2 in sphere["faces"])
    return {"verts": np.array(verts), "normals": np.array(normals),
            "uvs": np.zeros((len(verts), 2)), "faces": faces}


def scalp_sphere(radius: float, rings: int = 32, segments: int = 48) -> dict:
    """A plain UV sphere the size of the scalp the roots were grown on, wound outward.

    The preview stands in for a head, so a hairstyle can be looked at on its
    own without a figure in the frame, and nothing licence-bound is near it.
    """
    verts, normals = [], []
    for i in range(rings + 1):
        theta = np.pi * i / rings
        for j in range(segments):
            phi = 2 * np.pi * j / segments
            d = np.array([np.sin(theta) * np.cos(phi), np.cos(theta), np.sin(theta) * np.sin(phi)])
            verts.append(d * radius)
            normals.append(d)
    faces = []
    for i in range(rings):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            c = (i + 1) * segments + (j + 1) % segments
            d = (i + 1) * segments + j
            faces.append((a, c, b))
            faces.append((a, d, c))
    return {"verts": np.array(verts), "uvs": np.zeros((len(verts), 2)),
            "normals": np.array(normals), "faces": faces}


def face_dot_radial(meshes: list) -> float:
    """Mean signed dot of each triangle's geometric normal with the radial from the origin.

    Positive means the faces point away from the head, which an engine that
    culls back faces needs and which commit 1fdbb72 got wrong on every card.
    """
    dots = []
    for mesh in meshes:
        v = mesh["verts"]
        f = np.array(mesh["faces"], dtype=int)
        if len(f) == 0:
            continue
        a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
        n = unit(np.cross(b - a, c - a))
        r = unit((a + b + c) / 3.0)
        dots.append((n * r).sum(axis=1))
    return float(np.concatenate(dots).mean()) if dots else float("nan")


def grow(args, layers: list, plan: dict, jaw: Jaw | None = None, shape: dict | None = None) -> dict:
    """Roots, flow, guides, clusters and widths for every layer; the cards and their statistics.

    With `jaw` the same steps run on the ellipsoid for a beard: `shape` then
    carries the beard's length, variation, wave, volume and cluster spacing in
    place of the style's, unit directions are in the ellipsoid's scaled space,
    the flow is the jaw's, and every push-out is off the ellipsoid.  A layer
    with a count of 0 grows nothing (stubble is the cap and a few flyaways).
    """
    body = (args.head_radius / BODY_SCALE_RADIUS, BODY_CLEAR) if args.drape else None
    R, seed = args.head_radius, args.seed
    scalp = (args.hairline, args.cap, args.part, args.part_width)
    shape = shape or {"length": args.length, "variation": args.variation, "wave": args.wave,
                      "volume": args.volume, "guide": args.guide_distance}
    curl = (args.curl, args.curl_turns, args.curl_start) if jaw is None else (0.0, 0.0, 0.0)
    # with a settle the rest pose is the styled pose and the solver does the
    # falling, so strand_path keeps its comb out of it (see strand_path)
    # The comb is the STYLED POSE, not gravity: a VaM creator combs the guides and
    # the solver only refines them (vam-assets.md, VAM-030).  Decoupled from
    # --settle so the two can be measured apart.
    comb = args.comb
    if jaw is not None:
        R = jaw.mean_radius
        seed += 500                    # the beard's roots are not the hair's roots
    region = {"inside": jaw.inside if jaw else None, "area": jaw.area if jaw else None}
    # Cluster centres: Poisson at the guide distance, unmasked, so a lock is
    # the same size everywhere on the head (HAIR-117 semantics).
    centres = poisson_roots(2 * np.sin(shape["guide"] / R / 2), *scalp,
                            np.random.RandomState(seed + 1), masked=False, inside=region["inside"])
    centre_paths: dict = {}

    def lock_rng(lock):
        return np.random.RandomState(seed + 9973 * int(lock))

    def flow_and_aside(direction):
        if jaw is not None:
            return jaw.flow(direction), np.zeros(3)
        flow = scalp_flow(direction, args.part, args.part_flow, args.cap)
        forward = direction[2] / max(np.hypot(direction[0], direction[2]), 1e-9)
        aside = np.array([1.0 if direction[0] >= 0 else -1.0, 0.0, 0.0]) * args.sweep * max(0.0, forward)
        return flow, aside

    def apart_cm(d, centre):
        """Root to cluster centre: an arc on the scalp sphere, a chord on the ellipsoid."""
        if jaw is not None:
            return float(np.linalg.norm(jaw.point(d) - jaw.point(centre)))
        return float(2 * np.arcsin(min(1.0, np.linalg.norm(d - centre) / 2)) * R)

    # a short beard's tips spread less than a lock of hair's (guess)
    tip_spread = TIP_SPREAD if jaw is None else TIP_SPREAD * min(1.0, shape["length"] / 5.0)

    def centre_path(lock, layer):
        key = (int(lock), layer["name"])
        if key not in centre_paths:
            d = centres[lock]
            flow, aside = flow_and_aside(d)
            centre_paths[key] = strand_path(
                d, flow, args.lift, R, layer["offset"], shape["length"] * layer["length"],
                layer["points"], shape["wave"], shape["volume"], aside, lock_rng(lock),
                np.random.RandomState(seed + 9973 * int(lock) + 1), 0.0, body, curl, jaw, comb)
        return centre_paths[key]

    cards, per_layer = [], {}
    for li, layer in enumerate(layers):
        count = layer["count"]
        if count < 1:
            per_layer[layer["name"]] = {"roots": 0, "poisson": spacing_stats(np.zeros((0, 3)), R)}
            continue
        roots_wanted = -(-count // 3) if layer["tent"] else count
        rim = (BEARD_RIM_DEG if jaw else 12.0) if layer["name"] == "hairline" else None
        roots = poisson_count(roots_wanted, *scalp, np.random.RandomState(seed + 100 + li),
                              masked=jaw is None, rim=rim, **region)
        stats = {"roots": int(len(roots)), "poisson": spacing_stats(roots, R)}
        if rim is None and jaw is None:
            stats["fibonacci"] = spacing_stats(
                fibonacci_roots(len(roots), args.cap, args.hairline, args.part, args.part_width), R)
        for direction in roots:
            lock = int(np.argmin(np.linalg.norm(centres - direction[None, :], axis=1)))
            flow, aside = flow_and_aside(direction)
            members = [(direction, 0, 0.0)]
            if layer["tent"]:
                # Three cards in a tent: the base at the root, two on top set
                # off either side and a touch higher, the base the most opaque
                # (HAIR-002).  The wing offsets are guesses.
                if jaw is None:
                    side = unit(np.cross(flow, direction))
                    shift = 0.45 * layer["width"] / R
                    wings = [unit(direction + side * shift), unit(direction - side * shift)]
                else:
                    side = unit(np.cross(flow, jaw.normal(direction)))
                    shift = 0.45 * layer["width"]
                    wings = [jaw.direction(jaw.point(direction) + side * shift),
                             jaw.direction(jaw.point(direction) - side * shift)]
                members += [(wings[0], 1, 0.35), (wings[1], 2, 0.35)]
            base_index = len(cards)
            for d, rank, raise_by in members:
                index = len(cards)
                lock_r, card_r = lock_rng(lock), np.random.RandomState(seed + 31 + index)
                length = (shape["length"] * layer["length"]
                          + lock_r.uniform(-shape["variation"], shape["variation"])
                          + args.jitter * card_r.uniform(-shape["variation"], shape["variation"]) / 2)
                path = strand_path(d, flow, args.lift, R, layer["offset"] + raise_by,
                                   max(length, 0.5 if jaw is None else 0.2), layer["points"],
                                   shape["wave"], shape["volume"], aside, lock_r, card_r,
                                   args.jitter, body, curl, jaw, comb)
                # pulled into the lock, spread at the tip, kept clear of the scalp
                tip_dir = unit(path[-1] - path[-2])
                spread = card_r.normal(size=3)
                spread -= np.dot(spread, tip_dir) * tip_dir
                spread = unit(spread) * card_r.uniform(0.0, tip_spread)
                path = cluster_pull(path, centre_path(lock, layer), spread)
                if jaw is None:
                    path = keep_clear(path, R + layer["offset"] + raise_by, shape["volume"], body)
                else:
                    path = jaw.keep_clear(path, layer["offset"] + raise_by, shape["volume"])
                cards.append({"layer": li, "band": layer["band"], "lock": lock, "root": d,
                              "path": path, "tent": base_index if layer["tent"] else -1,
                              "tent_rank": rank, "offset_cm": layer["offset"] + raise_by,
                              "spread_cm": apart_cm(d, centres[lock])})
        per_layer[layer["name"]] = stats

    # The settle, on the finished cards: they have been pulled into their
    # locks and pushed clear of the head, so this is the pose the solver
    # drops, and the guides that are written are the settled ones.
    settled = settle_cards(args, cards, layers, shape, body, jaw,
                           args.head_radius) if args.settle and cards else {"ran": False}

    # Width from the cluster's spread within the layer's bounds (HAIR-101):
    # a lock whose members sit far from its centre is a wider lock.  The map
    # from spread to width is a guess: 60 percent of the layer's width plus 40
    # percent scaled by the lock's spread over the mean, clipped to 75 percent
    # and the layer's maximum.
    by_lock: dict = {}
    for c in cards:
        by_lock.setdefault(c["lock"], []).append(c["spread_cm"])
    lock_spread = {k: float(np.mean(v)) for k, v in by_lock.items()}
    mean_spread = max(float(np.mean(list(lock_spread.values()))), 1e-6)
    for c in cards:
        layer = layers[c["layer"]]
        factor = float(np.clip(0.6 + 0.4 * lock_spread[c["lock"]] / mean_spread,
                               0.75, layer["max"] / layer["width"]))
        c["width_root"], c["width_tip"] = layer["width"] * factor, layer["tip"] * factor
    assign_slots(cards, plan)

    sizes = [len(v) for v in by_lock.values()]
    clusters = {"centres": int(len(centres)), "locks_used": int(len(by_lock)),
                "members_mean": round(float(np.mean(sizes)), 2), "members_min": int(min(sizes)),
                "members_max": int(max(sizes)), "spread_mean_cm": round(mean_spread, 3),
                "guide_distance_cm": shape["guide"]}
    return {"cards": cards, "centres": centres, "per_layer": per_layer, "clusters": clusters,
            "settle": settled}


PARTS = {"centre": 0.0, "center": 0.0, "left": -0.34, "right": 0.34, "none": None}

# Flags the layered generator has no use for, and what replaced each.
RETIRED = {
    "strands": "card counts are per layer: --layers shell=60,breakup=150,hairline=40,flyaway=30",
    "segments": "points per guide are per layer (8, 6, 4, 5; 25 for curly) and not a flag",
    "width_root": "widths are per layer and come from the cluster spread; edit LAYERS",
    "width_tip": "widths are per layer and come from the cluster spread; edit LAYERS",
    "round": "normals are a per-layer blend of the ribbon frame and the radial",
    "texture": "the atlas is 2048 x 1024 and the cap maps 1024 square",
    "slots": "the atlas has 8 slots in 4 bands; see <name>_atlas.json",
    "clumps": "locks are Poisson clusters at --guide-distance",
    "hairs": "strands per slot are the 48 to 1 density ladder in <name>_atlas.json",
    "core": "the fallback atlas paints fixed 4 px to 2 px strands",
    "edge": "cards have no edge falloff; the atlas carries the shape",
    "shade": "the fallback atlas tints per strand",
    "tip": "strand ends are per band in <name>_atlas.json",
    "ends": "strand ends are per band in <name>_atlas.json",
    "strays": "flyaways are a layer of their own",
}


def part_arg(text: str):
    """Where the parting sits: a side, none, or an x between -1 and 1."""
    key = text.strip().lower()
    if key in PARTS:
        return PARTS[key]
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected one of {', '.join(PARTS)} or an x from -1 to 1, got {text!r}")
    if not -1.0 <= value <= 1.0:
        raise argparse.ArgumentTypeError(f"expected an x from -1 to 1, got {text!r}")
    return value


def colour_arg(text: str) -> tuple:
    if text in COLOURS:
        return COLOURS[text]
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"expected one of {', '.join(sorted(COLOURS))} or R,G,B, got {text!r}")
    try:
        rgb = tuple(int(p) for p in parts)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected three whole numbers 0 to 255, got {text!r}")
    if any(not 0 <= c <= 255 for c in rgb):
        raise argparse.ArgumentTypeError(f"expected each of R,G,B in 0 to 255, got {text!r}")
    lighter = tuple(min(255, int(c * 2.1 + 14)) for c in rgb)
    return rgb, lighter, tuple(min(255, int(c * 2.8 + 20)) for c in rgb)


def layers_arg(text: str) -> dict:
    """Per-layer count overrides: name=count pairs separated by commas."""
    names = [l["name"] for l in LAYERS]
    out = {}
    for item in text.split(","):
        if not item.strip():
            continue
        name, _, value = item.partition("=")
        name = name.strip().lower()
        if name not in names or not value.strip().isdigit():
            raise argparse.ArgumentTypeError(
                f"expected name=count with a name from {', '.join(names)}, got {item!r}")
        out[name] = int(value)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Grow layered hair guides on a scalp cap, with an atlas plan, a cap mesh, "
                    "a numpy-only fallback mesh and a preview.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="styles: " + ", ".join(sorted(STYLES)) + "\ncolours: " + ", ".join(sorted(COLOURS))
               + "\nlayers: " + ", ".join(l["name"] for l in LAYERS))
    ap.add_argument("--list", action="store_true",
                    help="print the styles, looks, colours and layers with their numbers, and exit")
    ap.add_argument("--style", choices=sorted(STYLES) + ["none"], default="wavy",
                    help="the shape to start from (default wavy); every number below overrides it. "
                         "none writes no hairstyle, only the --beard")
    ap.add_argument("--beard", choices=["none"] + sorted(BEARDS), default="none",
                    help="also grow a beard on the jaw ellipsoid as a second asset, <name>_beard "
                         "(or <name> itself with --style none), in the same colour: stubble is "
                         "a half-opaque cap and 40 flyaways 0.4 cm long, short 2.5 cm of 180 "
                         "cards, full 7 cm with 30 shells (default none; every length a guess)")
    ap.add_argument("--beard-length", type=float, default=None, metavar="CM",
                    help="centimetres from the skin to the beard's tips (default from --beard)")
    ap.add_argument("--look", choices=sorted(LOOKS), default="stylised",
                    help="stylised gathers the cards into locks 4.5 cm apart, keeps half the "
                         "colour range and lays a highlight band; realistic clusters at 2.5 cm "
                         "with the full range and no band (default stylised)")
    ap.add_argument("--part", type=part_arg, default="centre",
                    metavar="centre|left|right|none|X",
                    help="where the parting sits, as a side or an x from -1 to 1 (default centre)")
    ap.add_argument("--part-width", type=float, default=1.5, metavar="DEG",
                    help="how wide the bare line of the parting is at the forehead, closing to "
                         "nothing at the nape (default 1.5)")
    ap.add_argument("--part-flow", type=float, default=0.35,
                    help="how hard the hair is swept off the parting (default 0.35; 0.5 left a "
                         "bare wedge on the first bake, 2026-09-22). Too hard and the parting "
                         "is a wedge of scalp rather than a line")
    ap.add_argument("--colour", type=colour_arg, default="brown",
                    metavar="NAME|R,G,B", help="a named colour or an sRGB root colour 0 to 255")
    ap.add_argument("--name", default=None,
                    help="stem of every file (default hair_<style>_<colour or rgb>)")
    ap.add_argument("--out", type=Path, default=OUT,
                    help=f"directory to write into (default {OUT.relative_to(ROOT)})")
    ap.add_argument("--layers", type=layers_arg, default={}, metavar="NAME=N,...",
                    help="card counts per layer, overriding the style's scaled defaults of "
                         "shell=60,breakup=150,hairline=40,flyaway=30 for the wavy style")
    ap.add_argument("--length", type=float, default=None, metavar="CM",
                    help="centimetres from root to tip (default from --style)")
    ap.add_argument("--variation", type=float, default=None, metavar="CM",
                    help="how far a guide's length may stray either way (default from --style)")
    ap.add_argument("--wave", type=float, default=None,
                    help="scales both sine amplitudes: 0 is straight (default from --style)")
    ap.add_argument("--curl", type=float, default=None, metavar="CM",
                    help="radius of the helix each strand winds round its own centreline; "
                         "0 is none (default from --style: 1.1 for curly, 0 otherwise)")
    ap.add_argument("--curl-turns", type=float, default=None,
                    help="turns of that helix over the strand (default from --style: 3)")
    ap.add_argument("--curl-start", type=float, default=None,
                    help="where along the strand, 0 to 1, the curl begins (default from "
                         "--style: 0.15)")
    ap.add_argument("--card-width", type=float, default=None, metavar="SCALE",
                    help="scales every layer's card width and tip (default from --style: "
                         "0.5 for curly, so a card is narrower than its coil, 1 otherwise)")
    ap.add_argument("--cap", type=float, default=None, metavar="DEG",
                    help="how far down the scalp roots reach at the nape, from the crown "
                         "(default from --style)")
    ap.add_argument("--hairline", type=float, default=48.0, metavar="DEG",
                    help="how far down they reach at the front, where a face is (default 48; "
                         "the temples sit 80 percent of the way from this to --cap)")
    ap.add_argument("--head-radius", type=float, default=9.5, metavar="CM",
                    help="radius of the scalp the roots sit on (default 9.5, Genesis scale)")
    ap.add_argument("--lift", type=float, default=1.0,
                    help="scales the exit angle off the scalp, 15 degrees at the rim to 50 at the "
                         "crown (default 1.0; 0 leaves flat along the scalp)")
    ap.add_argument("--guide-distance", type=float, default=None, metavar="CM",
                    help="spacing of the cluster centres the cards are gathered into "
                         "(default from --look: 4.5 stylised, 2.5 realistic)")
    ap.add_argument("--jitter", type=float, default=None,
                    help="how far a card may stray from its lock's shape, 0 to 1 (default from --look)")
    ap.add_argument("--sweep", type=float, default=0.55,
                    help="how far hair rooted over the face is brushed out to the sides as it "
                         "falls (default 0.55; 0 lets it hang straight over the face)")
    ap.add_argument("--cling", type=float, default=-0.05, metavar="CM",
                    help="how far clear of the scalp the shell roots are held (default -0.05, "
                         "just under the cap at 0.15, so a shell's closed root end never shows "
                         "above it; at 0.25 the ends showed as pale hexagons on the crown, "
                         "2026-09-22); the outer layers sit at 0.8, 0.3 and 1.5")
    ap.add_argument("--cap-diffuse", type=Path, default=None, metavar="PNG",
                    help="use this image as the scalp cap's colour instead of the painted "
                         "follicle strokes; it is resized to the cap map and masked by the "
                         "cap's own opacity")
    ap.add_argument("--drape", action=argparse.BooleanOptionalAction, default=True,
                    help="let falling hair slide over the neck, shoulders and chest measured "
                         "on Genesis 9 (default on); off, long hair splays outward from its "
                         "exit angle and passes through the body")
    ap.add_argument("--comb", action=argparse.BooleanOptionalAction, default=True,
                    help="lay the heading over the skull as the strand is grown, which is the "
                         "styled pose the settle then refines (default on). Off, the strand "
                         "stands along its flow and exit angle and the settle has to do all "
                         "the styling, which measured a wider silhouette on 2026-09-23")
    ap.add_argument("--settle", action=argparse.BooleanOptionalAction, default=True,
                    help="drop the styled hair under gravity with the position-based solver "
                         "lifted from the Virt-A-Mate work (default on; docs/reference/vam-assets.md, "
                         "VAM-031, run 2026-09-23). Off, the styled pose is written as grown"
                         "down as it is grown instead, which is what the generator did before there "
                         "was a solver")
    ap.add_argument("--root-rigidity", type=float, default=0.2,
                    help="how hard the first point off the root is held to the styled pose, 0 to 1 "
                         "(default 0.2, which cleanleft and vikingtop ship; vikingchin ships 0.4997, "
                         "VAM-015, read 2026-09-23)")
    ap.add_argument("--main-rigidity", type=float, default=0.75,
                    help="how hard the rest of the strand is held to the styled pose before the "
                         "rolloff (default 0.75: at 0.75 with a rolloff of 2 the crown survived "
                         "200 frames of gravity and the ends still fell, VAM-031, run 2026-09-23. "
                         "That was on a 24-point strand; this file's layers are 8, 6, 4 and 5 "
                         "points, so carrying the value over is a judgement, not a measurement)")
    ap.add_argument("--tip-rigidity", type=float, default=0.0,
                    help="what the rigidity falls to by the tip (default 0.0, free; the packages "
                         "ship 0 to 0.5, VAM-015, read 2026-09-23)")
    ap.add_argument("--rigidity-rolloff", type=float, default=2.0,
                    help="the power the rigidity falls off at from root to tip (default 2.0; the "
                         "packages ship 8, which leaves only the first three points of a 24-point "
                         "strand rigid and let 200 frames of gravity flatten the crown, VAM-031, "
                         "run 2026-09-23, on a 24-point strand)")
    ap.add_argument("--settle-frames", type=int, default=240, metavar="N",
                    help="how many frames of gravity to run at most; the solver stops early once "
                         "the 99th percentile move falls below 0.05 mm in a frame (default 240)")
    ap.add_argument("--volume", type=float, default=1.2, metavar="CM",
                    help="how far the hair may stand off the scalp by the tip (default 1.2; 0 is "
                         "flat to the head)")
    ap.add_argument("--band", type=float, default=None,
                    help="strength of the lighter highlight sweep in the atlas, 0 for none "
                         "(default from --look)")
    ap.add_argument("--ramp", type=float, default=None,
                    help="how much of the root-to-tip colour range to keep, 0 to 1 (default from --look)")
    ap.add_argument("--seed", type=int, default=7, help="random seed (default 7)")
    ap.add_argument("--preview", action=argparse.BooleanOptionalAction, default=True,
                    help="also write <name>_preview.obj, the fallback hair and cap on a plain "
                         "scalp sphere, for scripts/render_sheet.py to draw with no figure")
    ap.add_argument("--no-bake", action="store_true",
                    help="stop after the numpy files: do not run scripts/bake_hair.py in the "
                         "container. The fallback OBJ then stands in for the baked one")
    for name in RETIRED:
        ap.add_argument(f"--{name.replace('_', '-')}", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()

    for name, why in RETIRED.items():
        if getattr(args, name) is not None:
            print(f"  ! --{name.replace('_', '-')} was retired on 2026-09-22: {why}")
            return 2

    if args.list:
        print("  style      length  variation  wave   cap    scale  width  curl          points")
        for name, s in sorted(STYLES.items()):
            print(f"  {name:10s} {s['length']:5.1f} cm {s['variation']:5.1f} cm {s['wave']:5.2f} "
                  f"{s['cap']:5.1f} deg {s['scale']:4.2f} {s['width']:5.2f}  "
                  f"{s['curl']:3.1f} cm x {s['curl_turns']:3.1f}  {s['points'] or 'per layer'}")
        print("\n  look       guide   jitter  band  ramp")
        for name, l in sorted(LOOKS.items()):
            print(f"  {name:10s} {l['guide']:4.1f} cm {l['jitter']:5.2f} {l['band']:5.2f} {l['ramp']:5.2f}")
        print("\n  layer      count  width  tip   max   offset  points  band")
        for l in LAYERS:
            print(f"  {l['name']:10s} {l['count']:5d} {l['width']:5.1f} {l['tip']:5.1f} {l['max']:5.2f} "
                  f"{l['offset']:5.2f} cm {l['points']:5d}  {l['band']}")
        print("\n  colour     root            tip             flyaway")
        for name, (a, b, c) in sorted(COLOURS.items()):
            print(f"  {name:10s} {str(a):15s} {str(b):15s} {str(c)}")
        print("\n  beard      length  variation  wave   volume  width  cap    layers")
        for name, b in sorted(BEARDS.items()):
            print(f"  {name:10s} {b['length']:5.1f} cm {b['variation']:5.1f} cm {b['wave']:5.2f} "
                  f"{b['volume']:5.2f} cm {b['width']:4.1f}  {b['cap_alpha']:4.2f}   "
                  + ", ".join(f"{k} {v}" for k, v in b["layers"].items()))
        return 0

    if args.style == "none" and args.beard == "none":
        print("  ! nothing to make: --style none needs a --beard")
        return 2
    # With --style none only the beard is made, but the scalp numbers are
    # still read (the beard's cluster sampler takes them), so they come from
    # the wavy style.
    style = STYLES[args.style if args.style != "none" else "wavy"]
    for key in ("length", "variation", "wave", "cap", "curl", "curl_turns", "curl_start"):
        if getattr(args, key) is None:
            setattr(args, key, style[key])
    if args.card_width is None:
        args.card_width = style["width"]
    look = LOOKS[args.look]
    for key, flag in (("guide", "guide_distance"), ("jitter", "jitter"), ("band", "band"), ("ramp", "ramp")):
        if getattr(args, flag) is None:
            setattr(args, flag, look[key])
    if isinstance(args.part, str):
        args.part = part_arg(args.part)
    if isinstance(args.colour, str):
        args.colour = colour_arg(args.colour)
    root_rgb, tip_rgb, stray_rgb = args.colour
    if args.length <= 0 or args.head_radius <= 0 or args.guide_distance <= 0 or args.card_width <= 0:
        print("  ! --length, --head-radius, --guide-distance and --card-width need to be above 0")
        return 2
    if not 0 < args.hairline <= args.cap < 180:
        print("  ! --hairline must be above 0 and no more than --cap, which is below 180")
        return 2
    if args.beard_length is not None and args.beard_length <= 0:
        print("  ! --beard-length needs to be above 0")
        return 2
    if args.settle_frames < 1:
        print("  ! --settle-frames needs to be at least 1")
        return 2
    if args.rigidity_rolloff < 0:
        print("  ! --rigidity-rolloff cannot be negative")
        return 2
    if not all(0.0 <= r <= 1.0 for r in (args.root_rigidity, args.main_rigidity, args.tip_rigidity)):
        print("  ! --root-rigidity, --main-rigidity and --tip-rigidity are each 0 to 1")
        return 2
    layers = []
    for layer in LAYERS:
        layer = dict(layer)
        layer["count"] = args.layers.get(layer["name"], int(round(layer["count"] * style["scale"])))
        for key in ("width", "tip", "max"):
            layer[key] = round(layer[key] * args.card_width, 3)
        if style["points"]:
            layer["points"] = style["points"]
        if layer["name"] == "shell":
            layer["offset"] = args.cling
        layers.append(layer)
    if args.style != "none" and any(l["count"] < 1 for l in layers):
        print("  ! every layer needs at least one card; use --layers name=N")
        return 2
    named = next((n for n, c in COLOURS.items() if c == args.colour), None)
    colour_stem = named or "-".join(str(c) for c in root_rgb)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    # The beard: its own layer counts and widths from BEARDS, its own shape,
    # and the jaw ellipsoid to grow on; a second asset with its own files so
    # it can be worn alone.
    jaw, beard_layers, beard_shape = None, [], None
    if args.beard != "none":
        beard = BEARDS[args.beard]
        scale = args.head_radius / BODY_SCALE_RADIUS
        jaw = Jaw(scale, (scale, BODY_CLEAR) if args.drape else None)
        for layer in LAYERS:
            layer = dict(layer)
            layer["count"] = beard["layers"][layer["name"]]
            for key in ("width", "tip", "max"):
                layer[key] = round(layer[key] * beard["width"], 3)
            if beard["points"]:
                layer["points"] = beard["points"]
            if layer["name"] == "shell":
                layer["offset"] = args.cling
            beard_layers.append(layer)
        beard_shape = {"length": args.beard_length or beard["length"], "variation": beard["variation"],
                       "wave": beard["wave"], "volume": beard["volume"],
                       "guide": round(BEARD_GUIDE * args.guide_distance / LOOKS["stylised"]["guide"], 3)}
    if args.style != "none":
        stem = args.name or f"hair_{args.style}_{colour_stem}"
        beard_stem = f"{stem}_beard"
    else:
        stem = None
        beard_stem = args.name or f"beard_{args.beard}_{colour_stem}"

    root01 = np.array(root_rgb, dtype=np.float64) / 255.0
    tip01 = np.array(tip_rgb, dtype=np.float64) / 255.0
    colours = {"root": list(root_rgb), "tip": list(tip_rgb), "flyaway": list(stray_rgb), "name": named,
               "root01": root01, "tip01": tip01}
    baked = []
    if stem is not None:
        started = time.time()
        plan = atlas_plan(root01, tip01, args.band, args.ramp)
        grown = grow(args, layers, plan)
        grow_s = round(time.time() - started, 3)
        cap = cap_mesh(args.head_radius + CAP_OFFSET, args.hairline, args.cap)
        t0 = time.time()
        cap_maps = cap_textures(root01, args.hairline, args.cap, args.part, args.part_width,
                                np.random.RandomState(args.seed + 42))
        if args.cap_diffuse:
            # a scalp painted elsewhere (scripts/make_scalp.py, or by hand) stands in
            # for the follicle strokes; the opacity above still cuts the hairline
            # and lightens the parting, so only the colour changes
            cap_maps = (Image.open(args.cap_diffuse).convert("RGB").resize((CAP_TEXTURE, CAP_TEXTURE), Image.LANCZOS),
                        cap_maps[1])
        cap_s = round(time.time() - t0, 3)
        shape = {"length": args.length, "variation": args.variation, "wave": args.wave,
                 "volume": args.volume, "guide": args.guide_distance}
        write_asset(args, stem, out, layers, shape, plan, grown, cap, cap_maps, jaw, colours, started,
                    {"grow_s": grow_s, "cap_textures_s": cap_s},
                    f"{args.style} hair, {len(grown['cards'])} cards in {len(layers)} layers over a cap, "
                    f"{args.length} cm long, grown on a {args.head_radius} cm scalp sphere",
                    {"kind": "hair", "cap_diffuse_from": str(args.cap_diffuse) if args.cap_diffuse else None})
        baked.append(stem)
    if jaw is not None:
        started = time.time()
        plan = atlas_plan(root01, tip01, args.band, args.ramp)
        grown = grow(args, beard_layers, plan, jaw, beard_shape)
        grow_s = round(time.time() - started, 3)
        cap = beard_cap_mesh(jaw)
        t0 = time.time()
        cap_maps = beard_cap_textures(root01, jaw, beard["cap_alpha"], np.random.RandomState(args.seed + 44))
        cap_s = round(time.time() - t0, 3)
        b = BEARD_REGION
        write_asset(args, beard_stem, out, beard_layers, beard_shape, plan, grown, cap, cap_maps, jaw,
                    colours, started, {"grow_s": grow_s, "cap_textures_s": cap_s},
                    f"{args.beard} beard, {len(grown['cards'])} cards in {len(beard_layers)} layers over a cap, "
                    f"{beard_shape['length']} cm long, grown on a jaw ellipsoid beside a "
                    f"{args.head_radius} cm scalp sphere",
                    {"kind": "beard", "beard": args.beard, "beard_cap_alpha": beard["cap_alpha"],
                     "beard_cap_blur_px": BEARD_CAP_BLUR_PX,
                     "jaw": {"centre_cm": [round(float(c), 3) for c in jaw.centre],
                             "radii_cm": [round(float(r), 3) for r in jaw.radii],
                             "region": dict(b), "region_steradians": round(jaw.area, 4),
                             "exit_degrees": b["exit_deg"],
                             "body_capsules": [{"name": n, "a": list(a), "b": list(bb), "radius_cm": r}
                                               for n, a, bb, r in BEARD_BODY] if args.drape else []},
                     "cap_diffuse_from": None})
        baked.append(beard_stem)
    if args.no_bake:
        print("  bake      skipped (--no-bake): the numpy fallback OBJ stands in for the baked one")
        return 0
    # The Blender half: lens shells, cards, a rendered atlas and the final OBJ.
    # It is its own script so a host with no container still gets everything
    # above; here it runs as a child process, one asset at a time, and its
    # report follows this one.
    import subprocess
    for name in baked:
        bake = [sys.executable, str(ROOT / "scripts" / "bake_hair.py"), name, "--dir", str(out)]
        print(f"  bake      scripts/bake_hair.py {name} --dir {shown(out)}")
        sys.stdout.flush()          # or the child's report lands above this line in a pipe
        rc = subprocess.call(bake)
        if rc != 0:
            print(f"  ! bake_hair.py exited {rc}; {shown(out / (name + '_fallback.obj'))} is the numpy result")
            return rc
    return 0


def shown(path: Path) -> str:
    """Repo-relative when it is in the repo, else as given: --out may be anywhere."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_asset(args, stem: str, out: Path, layers: list, shape: dict, plan: dict, grown: dict,
                cap: dict, cap_maps: tuple, jaw: Jaw | None, colours: dict, started: float,
                timings: dict, header0: str, extra: dict) -> dict:
    """The meshes, maps, files, measurements and report of one asset, hair or beard.

    Writes <stem>_guides.npz, _atlas.json, the cap, the fallback, the preview
    and <stem>.json under `out`, prints the report and returns the facts.
    """
    cards = grown["cards"]
    # the meshes: cap, then the fallback cards in layer order, inside to outside
    t0 = time.time()
    inset = 4.0 / ATLAS_SIZE[0]
    card_meshes = {name: {"verts": [], "uvs": [], "normals": [], "faces": []}
                   for name in ("shell", "card")}
    for c in cards:
        layer = layers[c["layer"]]
        slot = plan["slots"][c["slot"]]
        u0, u1 = slot["x0"] / ATLAS_SIZE[0] + inset, slot["x1"] / ATLAS_SIZE[0] - inset
        widths = widths_along(c["width_root"], c["width_tip"], len(c["path"]))
        v, t, n, f = ribbon(c["path"], widths, u0, u1, bool(c["uflip"]), layer["mix"])
        group = card_meshes["shell" if layer["name"] == "shell" else "card"]
        base = len(group["verts"])
        group["verts"].extend(v)
        group["uvs"].extend(t)
        group["normals"].extend(n)
        group["faces"].extend((a + base, b + base, d + base) for a, b, d in f)
    for group in card_meshes.values():
        for key in ("verts", "uvs", "normals"):
            group[key] = np.array(group[key]).reshape(-1, 3 if key != "uvs" else 2)
    timings["mesh_s"] = round(time.time() - t0, 3)

    cap_dif, cap_opa = cap_maps
    t0 = time.time()
    atlas_dif, atlas_opa = paint_atlas(plan, args.band, args.ramp, np.random.RandomState(args.seed + 43))
    timings["atlas_s"] = round(time.time() - t0, 3)

    # the files
    t0 = time.time()
    files = {}
    guides = out / f"{stem}_guides.npz"
    offsets = np.cumsum([0] + [len(c["path"]) for c in cards]).astype(np.int32)
    colours = dict(colours)
    root01, tip01 = (colours.pop(k).astype(np.float32) for k in ("root01", "tip01"))
    np.savez(guides,
             points=np.concatenate([c["path"] for c in cards]).astype(np.float32),
             offsets=offsets,
             layer=np.array([c["layer"] for c in cards], dtype=np.int32),
             lock=np.array([c["lock"] for c in cards], dtype=np.int32),
             width_root=np.array([c["width_root"] for c in cards], dtype=np.float32),
             width_tip=np.array([c["width_tip"] for c in cards], dtype=np.float32),
             slot=np.array([-1 if c["layer"] == 0 else c["slot"] for c in cards], dtype=np.int32),
             uflip=np.array([c["uflip"] for c in cards], dtype=np.uint8),
             tent=np.array([c["tent"] for c in cards], dtype=np.int32),
             head_radius_cm=np.float32(args.head_radius), cling_cm=np.float32(args.cling),
             hairline_deg=np.float32(args.hairline), cap_deg=np.float32(args.cap),
             part_x=np.float32(np.nan if args.part is None else args.part),
             colour_root=root01, colour_tip=tip01)
    files["guides"] = guides
    files["atlas"] = out / f"{stem}_atlas.json"
    files["atlas"].write_text(json.dumps(plan, indent=1) + "\n")

    header = [header0,
              "static geometry: no rig, no fitting, no morphs",
              "units: centimetres, +Y up, +Z the face, origin at the centre of the scalp sphere",
              "faces wound outward: the geometric normal points away from the head",
              "made by scripts/make_hair.py in the game-asset-engine repo"]
    cap_names = {k: f"{stem}_cap{s}" for k, s in (("obj", ".obj"), ("mtl", ".mtl"),
                                                 ("diffuse", "_diffuse.png"), ("opacity", "_opacity.png"))}
    files.update({"cap_" + k: out / v for k, v in cap_names.items()})
    cap_dif.save(files["cap_diffuse"])
    cap_opa.save(files["cap_opacity"])
    files["cap_mtl"].write_text(material_text(f"{stem}_cap", cap_names["diffuse"], cap_names["opacity"],
                                              ks=0.05, ns=8.0))
    write_groups(files["cap_obj"], cap_names["mtl"], [("cap", [(f"{stem}_cap", cap)])], header[1:])

    fb = {k: f"{stem}_fallback{s}" for k, s in (("obj", ".obj"), ("mtl", ".mtl"),
                                               ("diffuse", "_diffuse.png"), ("opacity", "_opacity.png"))}
    files.update({"fallback_" + k: out / v for k, v in fb.items()})
    atlas_dif.save(files["fallback_diffuse"])
    atlas_opa.save(files["fallback_opacity"])
    files["fallback_mtl"].write_text(
        material_text(f"{stem}_cap", cap_names["diffuse"], cap_names["opacity"], ks=0.05, ns=8.0)
        + "\n" + material_text(f"{stem}_shell", fb["diffuse"], fb["opacity"])
        + "\n" + material_text(f"{stem}_card", fb["diffuse"], fb["opacity"])
        + "\n" + material_text(f"{stem}_scalp", None, None, kd=(0.08, 0.07, 0.065), ks=0.05, ns=8.0)
        + "\n" + material_text(f"{stem}_body", None, None, kd=(0.30, 0.28, 0.27), ks=0.05, ns=8.0))
    hair_groups = [(f"{stem}_cap", cap), (f"{stem}_shell", card_meshes["shell"]),
                   (f"{stem}_card", card_meshes["card"])]
    write_groups(files["fallback_obj"], fb["mtl"], [("hair", hair_groups)], header)
    preview = out / f"{stem}_preview.obj"
    if args.preview:
        stand_ins = [(f"{stem}_scalp", scalp_sphere(args.head_radius))]
        if jaw is not None:
            stand_ins.append((f"{stem}_body", jaw.stand_in()))
        if args.drape:
            capsules = BEARD_BODY if extra.get("kind") == "beard" else BODY
            stand_ins.append((f"{stem}_body", body_stand_in(args.head_radius / BODY_SCALE_RADIUS, capsules)))
        write_groups(preview, fb["mtl"], [("hair", hair_groups), ("scalp", stand_ins)],
                     ["the fallback hair, the cap, the scalp sphere it was grown on"
                      + (", the jaw ellipsoid the beard grows on" if jaw is not None else "")
                      + " and the body it drapes over, for a look"])
        files["preview"] = preview
    else:
        preview.unlink(missing_ok=True)
    timings["write_s"] = round(time.time() - t0, 3)

    # the measurements
    all_verts = np.concatenate([cap["verts"]] + [g["verts"] for g in card_meshes.values()])
    low, high = all_verts.min(axis=0), all_verts.max(axis=0)
    per_layer_cards = {l["name"]: sum(1 for c in cards if c["layer"] == i) for i, l in enumerate(layers)}
    per_layer_tris = {l["name"]: sum(2 * (len(c["path"]) - 1) for c in cards if c["layer"] == i)
                      for i, l in enumerate(layers)}
    tris = {"cap": len(cap["faces"]), **per_layer_tris}
    tris["total"] = sum(tris.values())

    def dot(meshes):
        """None rather than NaN for a group with no faces, so the JSON stays JSON."""
        d = face_dot_radial(meshes)
        return None if np.isnan(d) else round(d, 4)

    dots = {"all": dot([cap] + list(card_meshes.values())), "cap": dot([cap]),
            "shell": dot([card_meshes["shell"]]), "card": dot([card_meshes["card"]])}
    for l in layers:
        l["poisson"] = grown["per_layer"][l["name"]]

    facts = {
        "date": time.strftime("%Y-%m-%d"), "argv": ["scripts/make_hair.py"] + sys.argv[1:],
        **extra,
        "style": args.style, "look": args.look,
        "colour": colours,
        "seed": args.seed, "length_cm": shape["length"], "variation_cm": shape["variation"],
        "wave": shape["wave"], "curl_cm": args.curl, "curl_turns": args.curl_turns,
        "curl_start": args.curl_start, "card_width": args.card_width,
        "volume_cm": shape["volume"], "sweep": args.sweep, "lift": args.lift,
        "jitter": args.jitter, "band": args.band, "ramp": args.ramp,
        "cap_degrees": args.cap, "hairline_degrees": args.hairline,
        "temple_degrees": round(args.hairline + (args.cap - args.hairline) * 0.8, 2),
        "part": args.part, "part_width_degrees": args.part_width, "part_flow": args.part_flow,
        "head_radius_cm": args.head_radius, "cling_cm": args.cling,
        "cap_offset_cm": CAP_OFFSET, "cap_rings": CAP_RINGS, "cap_segments": CAP_SEGMENTS,
        "cap_texture_px": CAP_TEXTURE, "whorl_deg": {"behind": WHORL_BEHIND_DEG, "aside": WHORL_ASIDE_DEG},
        "front_density": FRONT_DENSITY, "cluster": {"pull": CLUSTER_PULL, "shape": CLUSTER_SHAPE,
                                                    "tip_spread_cm": TIP_SPREAD},
        "taper_from": TAPER_FROM, "poisson_k": POISSON_K,
        "drape": args.drape, "body_capsules": [{"name": n, "a": list(a), "b": list(b), "radius_cm": r}
                                               for n, a, b, r in BODY] if args.drape else [],
        "body_clear_cm": BODY_CLEAR,
        "layers": [{k: l[k] for k in ("name", "count", "width", "tip", "max", "offset", "points",
                                        "length", "band", "tent", "mix", "poisson")}
                   for l in layers],
        "settle": grown["settle"],
        "cards": len(cards), "cards_per_layer": per_layer_cards,
        "tents": sum(1 for c in cards if c["tent"] >= 0 and c["tent_rank"] == 0),
        "guide_points": int(offsets[-1]),
        "clusters": grown["clusters"],
        "triangles": tris, "vertices": int(len(all_verts)),
        "face_normal_dot_radial": dots,
        "bounding_box_cm": {"min": [round(float(x), 3) for x in low],
                            "max": [round(float(x), 3) for x in high],
                            "span": [round(float(x), 3) for x in (high - low)]},
        "atlas": {"size": plan["size"], "slots": len(plan["slots"]),
                  "strands": [s["strands"] for s in plan["slots"]]},
        "files": {k: shown(p) for k, p in files.items()},
        "bytes": {k: p.stat().st_size for k, p in files.items()},
        "timings": timings, "seconds": round(time.time() - started, 2),
    }
    facts_path = out / f"{stem}.json"
    facts_path.write_text(json.dumps(facts, indent=2) + "\n")

    what = f"{args.beard} beard" if extra.get("kind") == "beard" else f"{args.style} hair"
    print(f"  {'beard' if extra.get('kind') == 'beard' else 'style':9s} {what}, {stem}, "
          f"{colours['name'] or 'rgb ' + ','.join(str(c) for c in colours['root'])}, "
          f"{args.look}, seed {args.seed}, {shape['length']} cm give or take {shape['variation']} cm")
    print("  roots     poisson: " + ", ".join(
        f"{per_layer_cards[l['name']]} {l['name']}" + (f" ({facts['tents']} tents)" if l["tent"] else "")
        for l in layers))
    dense = next((l for l in layers if l["poisson"]["poisson"]["mean_cm"] is not None), None)
    if dense is not None:
        st = dense["poisson"]
        line = (f"  spacing   {dense['name']} nearest neighbour {st['poisson']['mean_cm']} cm, "
                f"cv {st['poisson']['cv']} poisson")
        if "fibonacci" in st:
            line += f"; {st['fibonacci']['mean_cm']} cm, cv {st['fibonacci']['cv']} fibonacci, same count"
        print(line)
    cl = grown["clusters"]
    print(f"  locks     {cl['locks_used']} of {cl['centres']} centres at {cl['guide_distance_cm']} cm, "
          f"{cl['members_mean']} cards each ({cl['members_min']} to {cl['members_max']})")
    st = grown["settle"]
    if st.get("ran"):
        r = st["report"]
        print(f"  settle    {r['frames']} frames of {st['sim']['frames']}, p99 move "
              f"{r['last_frame_p99_move_mm']} mm, {r['share_moving_over_1mm']} still over 1 mm, "
              f"hit share {r['last_frame_hit_share']}; rigidity root {st['sim']['root_rigidity']}, "
              f"main {st['sim']['main_rigidity']}, tip {st['sim']['tip_rigidity']}, "
              f"rolloff {st['sim']['rigidity_rolloff']}")
        print(f"  strands   turn {r['turn_deg']} deg, root segment {r['root_segment_off_normal_deg']} deg "
              f"off the styled pose, reach over length {r['reach_over_length_median']}, "
              f"length {r['length_cm_median']} cm, all medians but the two angles")
    else:
        print("  settle    none (--no-settle): the strand is combed towards down as it is grown")
    print(f"  mesh      {tris['total']} triangles: cap {tris['cap']}, " + ", ".join(
        f"{l['name']} {tris[l['name']]}" for l in layers) + "; 4k to 20k is the budget (HAIR-016)")
    fmt = lambda d: "none" if d is None else f"{d:+.3f}"
    print(f"  winding   face normal . radial {fmt(dots['all'])} mean (cap {fmt(dots['cap'])}, "
          f"shell {fmt(dots['shell'])}, card {fmt(dots['card'])}); must be positive")
    print(f"  size      {facts['bounding_box_cm']['span'][0]} x {facts['bounding_box_cm']['span'][1]} x "
          f"{facts['bounding_box_cm']['span'][2]} cm about the origin")
    print(f"  atlas     {plan['size'][0]} x {plan['size'][1]}, {len(plan['slots'])} slots of "
          f"{', '.join(str(s['strands']) for s in plan['slots'])} strands; "
          f"cap maps {CAP_TEXTURE} px")
    print(f"  wrote     {shown(out)}/{stem}_guides.npz, _atlas.json, _cap.obj/.mtl/_diffuse/_opacity, "
          f"_fallback.obj/.mtl/_diffuse/_opacity" + (", _preview.obj" if args.preview else ""))
    print(f"  facts     {shown(facts_path)}  ({facts['seconds']} s: grow {timings['grow_s']}, "
          f"mesh {timings['mesh_s']}, cap maps {timings['cap_textures_s']}, atlas {timings['atlas_s']}, "
          f"write {timings['write_s']})")
    return facts


if __name__ == "__main__":
    sys.exit(main())
