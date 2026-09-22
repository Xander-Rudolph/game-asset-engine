#!/usr/bin/env python3
"""Grow a hair mesh from a scalp dome: ribbon strands, UVs and two maps.

    scripts/make_hair.py --list
    scripts/make_hair.py --style wavy --colour brown
    scripts/make_hair.py --style long --colour blond --strands 1400 --name lyra

WHY: the engine's other two routes to hair both stop short.  A Daz hair product
is Daz 3D data, so it may be rendered but never shipped as 3D without an
Interactive License (docs/reference/daz-genesis.md).  A strand hair is worse
than licence-bound, it is empty: the two in the library carry 236,136 and
167,264 vertices and no polygons at all, so Cycles draws nothing but the cap
(scripts/daz_characters.py, `draws_nothing`).  This script writes polygons the
repo owns outright: ribbons with UVs, a diffuse map and an opacity map, as OBJ,
MTL and two PNGs, which any engine loads and which may ship.

WHAT IT IS NOT: static geometry, with no rig, no fitting and no morphs.  It
grows on a sphere of `--head-radius`, so it lands on a head by being placed
there, which `daz_import_probe.py scene --wear-obj` does by measurement.

HOW A STRAND IS BUILT: `--strands` roots are spread over a polar cap of the
scalp sphere by the Fibonacci spiral, so no seam and no pole cluster.  Each root
grows `--segments` steps that turn from the scalp normal towards straight down,
lean outwards while they are still near the scalp, and are pushed sideways by
two sine waves whose amplitude `--wave` scales.  Every step is a ribbon
cross-section two vertices wide, tapering from `--width-root` to `--width-tip`,
and the ribbon is triangulated with two triangles per step.

HOW THE MAPS ARE BUILT: the two textures are an atlas of `--slots` vertical
strand slots.  Each strand takes one whole slot, and its UVs span exactly that
slot, so the slot's cosine edge falloff feathers across the ribbon's own width
and the ribbon reads as several fine strands rather than one flat card.  V runs
root at 0 to tip at 1, and the image is written bottom row first to match,
because image V = 0 is the bottom row everywhere the maps are read.

Standard library plus numpy and Pillow, both on the host's python3 (numpy 2.3.5,
Pillow 12.1.1, measured 2026-09-22).  It touches no network, no container and no
content library.
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

# Length is centimetres of hair; cap is how far down the scalp roots reach, in
# degrees from the crown; wave scales both sine amplitudes.  These are shapes to
# start from, not measurements: every one is reachable with the flags as well.
STYLES = {
    "wavy":     {"length": 14.0, "variation": 3.0, "wave": 1.0, "cap": 83.0, "segments": 14},
    "straight": {"length": 16.0, "variation": 2.0, "wave": 0.15, "cap": 83.0, "segments": 14},
    "curly":    {"length": 11.0, "variation": 2.5, "wave": 2.2, "cap": 83.0, "segments": 18},
    "short":    {"length": 6.0, "variation": 1.5, "wave": 0.8, "cap": 88.0, "segments": 10},
    "long":     {"length": 26.0, "variation": 4.0, "wave": 1.2, "cap": 80.0, "segments": 20},
}

# How the cards are grouped and drawn, which is what decides whether the hair
# reads as a stylised head of locks or as a photographic mop.  `clumps` is how
# many locks the cards are gathered into by azimuth, `jitter` how far a card may
# stray from its lock, `hairs` how many strands are drawn in a card's slot in
# the maps, `core` and `edge` how hard the strand and the card's own edges are,
# `shade` how much per-row noise the colour carries, `tip` how sharply a strand
# ends and `ends` the earliest a strand may end, and `band` a lighter sweep
# across the upper length, the graphic highlight stylised hair is drawn with.
LOOKS = {
    "stylised": {"clumps": 34, "jitter": 0.3, "hairs": 3, "core": 0.4, "edge": 0.3,
                 "shade": 0.02, "tip": 0.1, "ends": 0.82, "band": 0.3, "ramp": 0.5,
                 "strays": 0.04},
    "realistic": {"clumps": 0, "jitter": 1.0, "hairs": 7, "core": 0.9, "edge": 0.6,
                  "shade": 0.06, "tip": 0.22, "ends": 0.55, "band": 0.0, "ramp": 1.0,
                  "strays": 0.08},
}

# sRGB 0-255, root then tip then the tint of the occasional lighter flyaway.
COLOURS = {
    "black":  ((48, 42, 38), (92, 80, 70), (116, 102, 90)),
    "brown":  ((96, 66, 44), (172, 126, 86), (200, 158, 112)),
    "auburn": ((118, 56, 32), (196, 108, 58), (218, 136, 78)),
    "red":    ((150, 64, 28), (220, 118, 56), (238, 156, 86)),
    "blond":  ((168, 130, 76), (238, 206, 150), (248, 228, 186)),
    "grey":   ((132, 130, 128), (190, 188, 186), (212, 210, 208)),
    "white":  ((196, 194, 192), (240, 238, 236), (250, 248, 246)),
}


def scalp_roots(n: int, cap_degrees: float, hairline_degrees: float,
                part: float | None, part_width: float) -> np.ndarray:
    """Unit directions spread over the polar cap of a sphere, +Y at the crown.

    The Fibonacci spiral, so the roots are even and there is no seam and no
    cluster at the pole, which a latitude and longitude grid gives both of.  The
    half step keeps the first root off the pole itself, where "downhill along
    the scalp" is every direction at once and a strand has nowhere to start.

    Hair does not grow on a face, so the cap is not the same depth all the way
    round: it reaches `hairline_degrees` from the crown at the front, +Z, and
    `cap_degrees` at the back, and a root that falls outside it is pulled up to
    it rather than dropped, so the count asked for is the count returned.

    `part` is where the parting sits, as an x between -1 and 1, or None for no
    parting; `part_width` is how wide the bare line is, in degrees of arc.
    """
    cap, hairline = np.radians(cap_degrees), np.radians(hairline_degrees)
    i = np.arange(n, dtype=np.float64) + 0.5
    y = 1.0 - (i / n) * (1.0 - np.cos(cap))
    r = np.sqrt(np.maximum(0.0, 1.0 - y * y))
    phi = i * np.pi * (3.0 - np.sqrt(5.0))
    x, z = r * np.cos(phi), r * np.sin(phi)
    # forward is +Z: 1 at the face, 0 at the ears, -1 at the nape
    forward = np.divide(z, np.maximum(r, 1e-9))
    limit = np.cos(hairline + (cap - hairline) * (1 - forward) / 2)
    y = np.maximum(y, limit)
    r = np.sqrt(np.maximum(0.0, 1.0 - y * y))
    x, z = r * np.cos(phi), r * np.sin(phi)

    if part is not None:
        # A parting is a bare line of scalp with the hair swept off it either
        # way.  Every root inside the line is moved out to its edge along its
        # own latitude circle, so it stays on the sphere and at the same height.
        #
        # It runs from the forehead to the crown and stops, so the gap closes
        # towards the nape: carried all the way round at full width it is a bald
        # stripe over the crown and down the back of the head, with a hard
        # rectangular notch where the push saturates at the pole.
        forward = np.divide(z, np.maximum(r, 1e-9))
        gap = np.sin(np.radians(part_width)) * np.clip((forward + 0.35) / 1.1, 0.0, 1.0)
        side = np.where(x - part >= 0, 1.0, -1.0)
        wanted = part + side * np.maximum(np.abs(x - part), gap)
        x = np.clip(wanted, -r, r)
        z = np.sign(z) * np.sqrt(np.maximum(0.0, r * r - x * x))
    return np.column_stack((x, y, z))


def strand_path(direction: np.ndarray, radius: float, cling: float, length: float,
                segments: int, wave: float, volume: float, sweep: np.ndarray,
                aside: np.ndarray, lock: np.random.RandomState,
                card: np.random.RandomState, jitter: float) -> np.ndarray:
    """One strand: over the scalp first, then falling free, never through the head.

    A strand does not leave the head along the scalp normal.  It leaves downhill
    along the scalp, lies on it while the scalp is still under it, and only
    falls free once it is past the head.  The first draft grew along the normal,
    which sends every strand outwards at once: on a 9.5 cm scalp that made a
    46.6 cm wide spray with a bald crown showing through it.

    Lying on the scalp is enforced rather than hoped for.  Every point is pushed
    back out to `cling` centimetres clear of the scalp sphere, so no strand
    passes through the head, and none floats off it either.
    """
    down = np.array([0.0, -1.0, 0.0])
    tangent = down - np.dot(down, direction) * direction
    norm = np.linalg.norm(tangent)
    if norm < 1e-6:                      # the crown, where every way is downhill
        tangent = np.array([direction[2], 0.0, -direction[0]])
        norm = np.linalg.norm(tangent) or 1.0
    tangent = tangent / norm
    # Swept off the parting: the strand leaves along the scalp and away from the
    # line, which is what makes a parting read as one rather than as a bald
    # stripe.  The sweep is already tangent to the sphere at the root.
    tangent = tangent + sweep
    tangent = tangent / (np.linalg.norm(tangent) or 1.0)

    # The lock decides the shape and the card only strays from it, so the cards
    # in a lock move together.  Seeded per card instead, as the first draft was,
    # 320 cards each go their own way and the hair reads as a mop.
    def strayed(low, high, spread):
        return lock.uniform(low, high) * (1.0 + jitter * card.uniform(-spread, spread))

    freq1, freq2 = strayed(1.5, 2.5, 0.25), strayed(3.0, 5.0, 0.25)
    amp1 = strayed(0.6, 1.3, 0.3) * wave
    amp2 = strayed(0.15, 0.4, 0.3) * wave
    phase = lock.uniform(0, 2 * np.pi) + jitter * card.uniform(-0.6, 0.6)
    twist = lock.normal(size=3) + jitter * 0.5 * card.normal(size=3)
    twist /= np.linalg.norm(twist) or 1.0
    keep_out = radius + cling

    # The centreline first, then the wave as a displacement from it.  Added to
    # the running point instead, as the first draft did, each step's offset
    # lands on top of the last and the wave integrates into a drift: at
    # --wave 2.2 the curly style wandered into a 42.8 cm wide nest round the
    # head rather than curling (measured 2026-09-22).
    # Hair rooted over the face is brushed out to the sides as it falls, which
    # is why long hair frames a face rather than curtaining it.  Left to fall
    # straight down, the long styles hung flat over the nose and the declip then
    # pushed them out onto it.
    step = length / segments
    spine, headings = [direction * keep_out], []
    for i in range(1, segments + 1):
        t = i / segments
        heading = (1 - t) * tangent + t * down + aside * t
        norm = np.linalg.norm(heading)
        heading = heading / norm if norm > 1e-6 else down.copy()
        headings.append(heading)
        spine.append(spine[-1] + heading * step)

    points = [spine[0]]
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
        distance = np.linalg.norm(point)
        if distance < keep_out + volume * t:
            point = point * ((keep_out + volume * t) / max(distance, 1e-9))
        points.append(point)
    return np.array(points)


def ribbon(path: np.ndarray, width_root: float, width_tip: float,
           slot: int, slots: int, round_degrees: float) -> tuple:
    """A strand path widened into a two-vertex-wide ribbon with UVs and normals.

    The two UV columns are the inside edges of one texture slot, so the slot's
    own feathering runs across the ribbon rather than at some angle to it.
    """
    n = len(path)
    t = np.linspace(0.0, 1.0, n)
    widths = width_root * (1 - t) + width_tip * t

    tangents = np.empty_like(path)
    tangents[0] = path[1] - path[0]
    tangents[-1] = path[-1] - path[-2]
    tangents[1:-1] = path[2:] - path[:-2]
    lengths = np.linalg.norm(tangents, axis=1, keepdims=True)
    tangents = np.where(lengths > 1e-6, tangents / np.maximum(lengths, 1e-9),
                        np.array([0.0, -1.0, 0.0]))

    # The ribbon's face lies along the scalp and points away from the head, so a
    # card reads as a sheet of hair.  Squared against world up instead, as the
    # first draft had it, the cards on the sides of the head are edge on to the
    # camera and the hair reads as wires.
    radial = path / np.maximum(np.linalg.norm(path, axis=1, keepdims=True), 1e-9)
    sides = np.cross(tangents, radial)
    lengths = np.linalg.norm(sides, axis=1, keepdims=True)
    sides = np.where(lengths > 1e-6, sides / np.maximum(lengths, 1e-9),
                     np.array([1.0, 0.0, 0.0]))
    normals = np.cross(sides, tangents)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.where(lengths > 1e-6, normals / np.maximum(lengths, 1e-9),
                       np.array([0.0, 0.0, 1.0]))

    half = (widths / 2)[:, None]
    verts = np.empty((2 * n, 3))
    verts[0::2] = path + sides * half
    verts[1::2] = path - sides * half

    # A card is a clump of round hairs, not a sheet of paper, so its two edges
    # carry normals tilted out by `round_degrees` about the strand and smooth
    # shading sweeps between them.  A flat sheet normal is why the fringe went
    # black: it faces the camera, the key sun is overhead, and a flat card
    # square to the camera catches none of it.  Tilted, the same card has an
    # edge turned up to the sun wherever it hangs.
    angle = np.radians(round_degrees)
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    vnorms = np.empty((2 * n, 3))
    vnorms[0::2] = normals * cos_a + sides * sin_a
    vnorms[1::2] = normals * cos_a - sides * sin_a
    vnorms /= np.maximum(np.linalg.norm(vnorms, axis=1, keepdims=True), 1e-9)
    left, right = (slot + 0.02) / slots, (slot + 0.98) / slots
    uvs = np.empty((2 * n, 2))
    uvs[0::2] = np.column_stack((np.full(n, left), t))
    uvs[1::2] = np.column_stack((np.full(n, right), t))
    return verts, uvs, vnorms


def locks_of(directions: np.ndarray, clumps: int) -> np.ndarray:
    """Which lock each root belongs to, by where it sits round the head.

    Azimuth wedges, so a lock is a column of cards running from the crown down
    one part of the scalp, which is the shape hair actually falls in.  The
    Fibonacci spiral numbers its roots by the golden angle, so consecutive
    indices are nowhere near each other and grouping by index would scatter a
    lock over the whole head.
    """
    if clumps < 1:
        return np.arange(len(directions))
    azimuth = np.arctan2(directions[:, 0], directions[:, 2])
    return (((azimuth + np.pi) / (2 * np.pi) * clumps).astype(int)) % clumps


def build(args) -> dict:
    rng = np.random.RandomState(args.seed)
    directions = scalp_roots(args.strands, args.cap, args.hairline,
                             args.part, args.part_width)
    locks = locks_of(directions, args.clumps)
    verts, uvs, normals, faces = [], [], [], []
    for index, direction in enumerate(directions):
        lock = np.random.RandomState(args.seed + 9973 * int(locks[index]))
        card = np.random.RandomState(args.seed + 31 + index)
        length = args.length + lock.uniform(-args.variation, args.variation) \
            + args.jitter * card.uniform(-args.variation, args.variation) / 2
        sweep = np.zeros(3)
        if args.part is not None and args.part_flow:
            # strongest at the crown, gone by the hairline
            top = np.clip((direction[1] - np.cos(np.radians(args.cap)))
                          / max(1.0 - np.cos(np.radians(args.cap)), 1e-9), 0.0, 1.0)
            away = np.array([1.0 if direction[0] >= args.part else -1.0, 0.0, 0.0])
            sweep = away - np.dot(away, direction) * direction
            sweep = sweep * args.part_flow * top
        forward = direction[2] / max(np.hypot(direction[0], direction[2]), 1e-9)
        aside = np.array([1.0 if direction[0] >= 0 else -1.0, 0.0, 0.0]) \
            * args.sweep * max(0.0, forward)
        path = strand_path(direction, args.head_radius, args.cling, max(length, 0.5),
                           args.segments, args.wave, args.volume, sweep, aside,
                           lock, card, args.jitter)
        slot = int(locks[index] * 7 + card.randint(0, 3)) % args.slots
        v, t, n = ribbon(path, args.width_root, args.width_tip, slot, args.slots,
                         args.round)
        first = len(verts) + 1
        verts.extend(v)
        uvs.extend(t)
        normals.extend(n)
        for i in range(len(path) - 1):
            a, b = first + 2 * i, first + 2 * i + 1
            c, d = first + 2 * (i + 1), first + 2 * (i + 1) + 1
            faces.append((a, b, d))
            faces.append((a, d, c))
    return {"verts": np.array(verts), "uvs": np.array(uvs),
            "normals": np.array(normals), "faces": faces}


def textures(args, root_rgb, tip_rgb, stray_rgb) -> tuple:
    """One slot per card across U, root at the bottom of the image.

    A card is a clump, so its alpha is not one soft blob: each slot holds
    `--hairs` narrow strands at random offsets, each ending at its own height,
    and the card's tip is wherever its strands have run out.  Drawn as one blob
    the cards end in blunt rectangles and the hair reads as straw.

    Row 0 of a PIL array is the top of the image and image V = 0 is the bottom
    row, so the row that holds the root colour is the last one.  Written the
    other way round, as the first draft of this was, every strand wears its tip
    colour at the scalp and fades out at the roots instead of at the ends.
    """
    size, slots = args.texture, args.slots
    rng = np.random.RandomState(args.seed + 42)
    diffuse = np.zeros((size, size, 3), dtype=np.float32)
    opacity = np.zeros((size, size), dtype=np.float32)
    root_rgb, tip_rgb, stray_rgb = (np.array(c, dtype=np.float64) / 255.0
                                    for c in (root_rgb, tip_rgb, stray_rgb))

    v = 1.0 - np.arange(size) / (size - 1)          # bottom row is the root
    ramp = root_rgb[None, :] * (1 - v)[:, None] + tip_rgb[None, :] * v[:, None]
    # Stylised hair carries less range along a strand than a photograph does and
    # puts the contrast in a highlight instead, so --ramp pulls the root and the
    # tip towards their mean and --band lays one broad lighter sweep across the
    # upper length.  At full range and a strong band the crown reads as a
    # bleached patch over black hair rather than as a sheen.
    ramp = ramp.mean(axis=0)[None, :] + (ramp - ramp.mean(axis=0)[None, :]) * args.ramp
    sweep = 1.0 + args.band * np.exp(-(((v - 0.34) / 0.2) ** 2))

    for slot in range(slots):
        x0, x1 = int(slot * size / slots), int((slot + 1) * size / slots)
        width = x1 - x0
        if width <= 0:
            continue
        # One number, not three: a per-channel tint shifts each slot's hue and
        # the head comes out streaked green, pink and yellow rather than one
        # colour lit unevenly.
        tint = rng.uniform(0.85, 1.15)
        colour = (ramp + stray_rgb[None, :]) / 2.0 if rng.rand() < args.strays else ramp
        shade = 1.0 + rng.uniform(-args.shade, args.shade, size=size)[:, None]
        diffuse[:, x0:x1, :] = np.clip(colour * tint * shade * sweep[:, None],
                                       0, 1)[:, None, :]

        across = np.linspace(0.0, 1.0, width)
        card = np.clip(np.cos((across - 0.5) * np.pi) ** args.edge, 0, 1)
        alpha = np.zeros((size, width), dtype=np.float32)
        for _ in range(args.hairs):
            centre = rng.uniform(0.08, 0.92)
            half = rng.uniform(0.6, 1.8) / args.hairs
            ends = rng.uniform(args.ends, 1.0)
            profile = np.clip(1.0 - np.abs(across - centre) / half, 0, 1) ** args.core
            fade = np.clip((ends - v) / args.tip, 0, 1)[:, None]
            alpha = np.maximum(alpha, profile[None, :] * fade)
        opacity[:, x0:x1] = alpha * card[None, :]

    # The mask goes in the alpha channel as well as in the three colour ones.
    # Blender's OBJ importer wires map_d's image *Alpha* output into Principled
    # Alpha, and a greyscale PNG has no alpha channel, so that output is 1.0
    # everywhere and the hair renders as solid cards with blunt square ends: 320
    # of them, and not one transparent pixel (measured 2026-09-22).  Written
    # RGBA, the same file reads right whether an importer takes Alpha or Colour.
    mask = (np.clip(opacity, 0, 1) * 255).astype(np.uint8)
    return (Image.fromarray((diffuse * 255).astype(np.uint8), mode="RGB"),
            Image.fromarray(np.dstack([mask, mask, mask, mask]), mode="RGBA"))


def write_obj(path: Path, mesh: dict, mtl: str, material: str, header: list[str]) -> None:
    with path.open("w") as fh:
        for line in header:
            fh.write(f"# {line}\n")
        fh.write(f"mtllib {mtl}\n")
        fh.write(f"o {path.stem}\n")
        for x, y, z in mesh["verts"]:
            fh.write(f"v {x:.5f} {y:.5f} {z:.5f}\n")
        for u, w in mesh["uvs"]:
            fh.write(f"vt {u:.5f} {w:.5f}\n")
        for x, y, z in mesh["normals"]:
            fh.write(f"vn {x:.5f} {y:.5f} {z:.5f}\n")
        fh.write(f"usemtl {material}\n")
        for a, b, c in mesh["faces"]:
            fh.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")


def scalp_sphere(radius: float, rings: int = 32, segments: int = 48) -> dict:
    """A plain UV sphere the size of the scalp the roots were grown on.

    The preview stands in for a head, so a hairstyle can be looked at on its own
    without a figure in the frame: whether it lies on the scalp or fountains off
    the crown shows at once, and nothing licence-bound is anywhere near it.
    """
    verts, faces = [], []
    for i in range(rings + 1):
        theta = np.pi * i / rings
        for j in range(segments):
            phi = 2 * np.pi * j / segments
            verts.append((radius * np.sin(theta) * np.cos(phi), radius * np.cos(theta),
                          radius * np.sin(theta) * np.sin(phi)))
    for i in range(rings):
        for j in range(segments):
            a = i * segments + j + 1
            b = i * segments + (j + 1) % segments + 1
            c = (i + 1) * segments + (j + 1) % segments + 1
            d = (i + 1) * segments + j + 1
            faces.append((a, b, c))
            faces.append((a, c, d))
    return {"verts": np.array(verts), "faces": faces}


def write_preview(path: Path, mesh: dict, sphere: dict, mtl: str,
                  hair_material: str, scalp_material: str) -> None:
    """The hair and a scalp sphere in one OBJ, for a look with no figure in it."""
    with path.open("w") as fh:
        fh.write("# hair and the scalp sphere it was grown on, for a look at the shape\n")
        fh.write(f"mtllib {mtl}\n")
        for x, y, z in mesh["verts"]:
            fh.write(f"v {x:.5f} {y:.5f} {z:.5f}\n")
        for x, y, z in sphere["verts"]:
            fh.write(f"v {x:.5f} {y:.5f} {z:.5f}\n")
        for u, w in mesh["uvs"]:
            fh.write(f"vt {u:.5f} {w:.5f}\n")
        for x, y, z in mesh["normals"]:
            fh.write(f"vn {x:.5f} {y:.5f} {z:.5f}\n")
        fh.write(f"o hair\nusemtl {hair_material}\n")
        for a, b, c in mesh["faces"]:
            fh.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")
        shift = len(mesh["verts"])
        fh.write(f"o scalp\nusemtl {scalp_material}\n")
        for a, b, c in sphere["faces"]:
            fh.write(f"f {a + shift} {b + shift} {c + shift}\n")


def write_mtl(path: Path, material: str, diffuse: str, opacity: str) -> None:
    path.write_text(
        f"newmtl {material}\n"
        "Ka 1.000 1.000 1.000\n"
        "Kd 1.000 1.000 1.000\n"
        "Ks 0.350 0.350 0.350\n"
        "Ns 430.0\n"
        "illum 2\n"
        "d 1.0\n"
        f"map_Kd {diffuse}\n"
        f"map_d {opacity}\n"
        f"\nnewmtl {material}_scalp\n"
        "Ka 0.000 0.000 0.000\n"
        "Kd 0.080 0.070 0.065\n"
        "Ks 0.050 0.050 0.050\n"
        "Ns 8.0\n"
        "illum 2\n"
        "d 1.0\n")


PARTS = {"centre": 0.0, "center": 0.0, "left": -0.34, "right": 0.34, "none": None}


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


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Grow a ribbon hair mesh with UVs, a diffuse map and an opacity map.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="styles: " + ", ".join(sorted(STYLES)) + "\ncolours: " + ", ".join(sorted(COLOURS)))
    ap.add_argument("--list", action="store_true",
                    help="print the styles and colours with their numbers, and exit")
    ap.add_argument("--style", choices=sorted(STYLES), default="wavy",
                    help="the shape to start from (default wavy); every number below overrides it")
    ap.add_argument("--look", choices=sorted(LOOKS), default="stylised",
                    help="how the cards are grouped and drawn: stylised gathers them into "
                         "locks with hard edges and a highlight band, realistic leaves each "
                         "card to itself with fine wispy strands (default stylised)")
    ap.add_argument("--part", type=part_arg, default="centre",
                    metavar="centre|left|right|none|X",
                    help="where the parting sits, as a side or an x from -1 to 1 "
                         "(default centre)")
    ap.add_argument("--part-width", type=float, default=1.5, metavar="DEG",
                    help="how wide the bare line of the parting is at the forehead, "
                         "closing to nothing at the nape (default 1.5)")
    ap.add_argument("--part-flow", type=float, default=0.5,
                    help="how hard the hair is swept off the parting (default 0.5). Too "
                         "hard and the parting is a bare wedge of scalp rather than a line")
    ap.add_argument("--colour", type=colour_arg, default="brown",
                    metavar="NAME|R,G,B", help="a named colour or an sRGB root colour 0 to 255")
    ap.add_argument("--name", default=None,
                    help="stem of the four files (default hair_<style>_<colour or rgb>)")
    ap.add_argument("--out", type=Path, default=OUT,
                    help=f"directory to write into (default {OUT.relative_to(ROOT)})")
    ap.add_argument("--strands", type=int, default=320,
                    help="card count (default 320, about four layers over the head)")
    ap.add_argument("--segments", type=int, default=None,
                    help="steps down a strand, one ribbon step each (default from --style)")
    ap.add_argument("--length", type=float, default=None, metavar="CM",
                    help="centimetres from root to tip (default from --style)")
    ap.add_argument("--variation", type=float, default=None, metavar="CM",
                    help="how far a strand's length may stray either way (default from --style)")
    ap.add_argument("--wave", type=float, default=None,
                    help="scales both sine amplitudes: 0 is straight (default from --style)")
    ap.add_argument("--cap", type=float, default=None, metavar="DEG",
                    help="how far down the scalp roots reach at the back, from the crown "
                         "(default from --style)")
    ap.add_argument("--hairline", type=float, default=48.0, metavar="DEG",
                    help="how far down they reach at the front, where a face is "
                         "(default 58)")
    ap.add_argument("--head-radius", type=float, default=9.5, metavar="CM",
                    help="radius of the scalp the roots sit on (default 9.5, Genesis scale)")
    ap.add_argument("--width-root", type=float, default=1.4, metavar="CM",
                    help="card width at the root (default 1.4: a card is a clump of hair, "
                         "not one hair)")
    ap.add_argument("--width-tip", type=float, default=0.5, metavar="CM",
                    help="card width at the tip (default 0.5)")
    ap.add_argument("--sweep", type=float, default=0.55,
                    help="how far hair rooted over the face is brushed out to the sides as "
                         "it falls (default 0.55; 0 lets it hang straight over the face)")
    ap.add_argument("--round", type=float, default=62.0, metavar="DEG",
                    help="how far a card's edge normals are tilted out, so it shades like "
                         "a clump of round hairs rather than a flat sheet (default 62; "
                         "0 is a flat card)")
    ap.add_argument("--cling", type=float, default=0.25, metavar="CM",
                    help="how far clear of the scalp a strand is held (default 0.25)")
    ap.add_argument("--volume", type=float, default=1.2, metavar="CM",
                    help="how far the hair is allowed to stand off the scalp by the tip "
                         "(default 1.2; 0 is flat to the head)")
    ap.add_argument("--texture", type=int, default=1024, metavar="PX",
                    help="square map size (default 1024)")
    ap.add_argument("--slots", type=int, default=64,
                    help="card slots across the maps (default 64)")
    for name, help_text in (
            ("clumps", "locks the cards are gathered into round the head"),
            ("jitter", "how far a card may stray from its lock, 0 to 1"),
            ("hairs", "strands drawn inside each card's slot in the maps"),
            ("core", "strand profile exponent: below 1 is a fatter, harder strand"),
            ("edge", "the card's own edge falloff exponent"),
            ("shade", "per-row colour noise, 0 for none"),
            ("tip", "how sharply a strand ends, as a fraction of its length"),
            ("ends", "the earliest along a card a strand may end, 0 to 1"),
                    ("band", "strength of the lighter highlight sweep, 0 for none"),
            ("ramp", "how much of the root-to-tip colour range to keep, 0 to 1"),
            ("strays", "fraction of slots tinted as lighter flyaways")):
        ap.add_argument(f"--{name}", type=int if name in ("clumps", "hairs") else float,
                        default=None, help=f"{help_text} (default from --look)")
    ap.add_argument("--seed", type=int, default=7, help="random seed (default 7)")
    ap.add_argument("--preview", action=argparse.BooleanOptionalAction, default=True,
                    help="also write <name>_preview.obj, the hair on a plain scalp sphere, "
                         "for scripts/render_sheet.py to draw with no figure in the frame")
    args = ap.parse_args()

    if args.list:
        print("  style      length  variation  wave   cap    segments")
        for name, s in sorted(STYLES.items()):
            print(f"  {name:10s} {s['length']:5.1f} cm {s['variation']:5.1f} cm "
                  f"{s['wave']:5.2f} {s['cap']:5.1f} deg {s['segments']:5d}")
        print("\n  colour     root            tip             flyaway")
        for name, (a, b, c) in sorted(COLOURS.items()):
            print(f"  {name:10s} {str(a):15s} {str(b):15s} {str(c)}")
        return 0

    style = STYLES[args.style]
    for key in ("length", "variation", "wave", "cap", "segments"):
        if getattr(args, key) is None:
            setattr(args, key, style[key])
    for key, value in LOOKS[args.look].items():
        if getattr(args, key) is None:
            setattr(args, key, value)
    if isinstance(args.part, str):
        args.part = part_arg(args.part)
    if isinstance(args.colour, str):
        args.colour = colour_arg(args.colour)
    root_rgb, tip_rgb, stray_rgb = args.colour
    if args.strands < 1 or args.segments < 2 or args.slots < 1 or args.texture < 8:
        print("  ! --strands and --slots need at least 1, --segments at least 2, "
              "--texture at least 8")
        return 2
    named = next((n for n, c in COLOURS.items() if c == args.colour), None)
    stem = args.name or f"hair_{args.style}_" + (named or "-".join(str(c) for c in root_rgb))

    started = time.time()
    mesh = build(args)
    diffuse, opacity = textures(args, root_rgb, tip_rgb, stray_rgb)

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    obj, mtl = out / f"{stem}.obj", out / f"{stem}.mtl"
    dif, opa = out / f"{stem}_diffuse.png", out / f"{stem}_opacity.png"
    material = f"{stem}_material"
    write_obj(obj, mesh, mtl.name, material, [
        f"{args.style} hair, {args.strands} strands, {args.length} cm long, "
        f"grown on a {args.head_radius} cm scalp sphere",
        "static geometry: no rig, no fitting, no morphs",
        "units: centimetres, +Y up, origin at the centre of the scalp sphere",
        "made by scripts/make_hair.py in the game-asset-engine repo",
    ])
    write_mtl(mtl, material, dif.name, opa.name)
    diffuse.save(dif)
    opacity.save(opa)
    preview = out / f"{stem}_preview.obj"
    if args.preview:
        write_preview(preview, mesh, scalp_sphere(args.head_radius), mtl.name,
                      material, f"{material}_scalp")
    else:
        preview.unlink(missing_ok=True)

    v = mesh["verts"]
    roots = v[::2 * (args.segments + 1)]
    low, high = v.min(axis=0), v.max(axis=0)
    # How many cards a ray through the hair crosses on average, which is what
    # decides whether it reads as hair or as a black mass.  Card area over the
    # area the hair covers: the scalp cap plus the skirt that hangs below it.
    cap = np.radians(args.cap)
    covered = (2 * np.pi * args.head_radius ** 2 * (1 - np.cos(cap))
               + 2 * np.pi * args.head_radius * min(args.length, 2 * args.head_radius))
    card_area = args.strands * args.length * (args.width_root + args.width_tip) / 2
    def shown(path: Path) -> str:
        """Repo-relative when it is in the repo, else as given: --out may be anywhere."""
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)

    facts = {
        "date": time.strftime("%Y-%m-%d"), "argv": ["scripts/make_hair.py"] + sys.argv[1:],
        "style": args.style, "colour": {"root": list(root_rgb), "tip": list(tip_rgb),
                                        "flyaway": list(stray_rgb), "name": named},
        "strands": args.strands, "segments": args.segments, "seed": args.seed,
        "length_cm": args.length, "variation_cm": args.variation, "wave": args.wave,
        "cap_degrees": args.cap, "hairline_degrees": args.hairline,
        "head_radius_cm": args.head_radius,
        "width_root_cm": args.width_root, "width_tip_cm": args.width_tip,
        "cling_cm": args.cling, "volume_cm": args.volume, "round_degrees": args.round,
        "sweep": args.sweep,
        "texture_px": args.texture, "slots": args.slots, "hairs": args.hairs,
        "strays": args.strays,
        "vertices": len(v), "triangles": len(mesh["faces"]), "uvs": len(mesh["uvs"]),
        "bounding_box_cm": {"min": [round(float(x), 3) for x in low],
                            "max": [round(float(x), 3) for x in high],
                            "span": [round(float(x), 3) for x in (high - low)]},
        "root_radius_cm": round(float(np.linalg.norm(roots, axis=1).mean()), 3),
        "card_area_cm2": round(float(card_area)), "covered_area_cm2": round(float(covered)),
        "layers": round(float(card_area / covered), 1),
        "files": {k: shown(p) for k, p in
                  (("obj", obj), ("mtl", mtl), ("diffuse", dif), ("opacity", opa))
                  + ((("preview", preview),) if args.preview else ())},
        "bytes": {k: p.stat().st_size for k, p in
                  (("obj", obj), ("mtl", mtl), ("diffuse", dif), ("opacity", opa))},
        "seconds": round(time.time() - started, 2),
    }
    (out / f"{stem}.json").write_text(json.dumps(facts, indent=2) + "\n")

    print(f"  style     {args.style}, {named or 'rgb ' + ','.join(str(c) for c in root_rgb)}, "
          f"seed {args.seed}")
    print(f"  strands   {args.strands} of {args.segments} segments, {args.length} cm "
          f"give or take {args.variation} cm, wave {args.wave}")
    print(f"  mesh      {len(v)} vertices, {len(mesh['faces'])} triangles, "
          f"{len(mesh['uvs'])} UVs")
    print(f"  size      {facts['bounding_box_cm']['span'][0]} x "
          f"{facts['bounding_box_cm']['span'][1]} x {facts['bounding_box_cm']['span'][2]} cm, "
          f"roots on a {facts['root_radius_cm']} cm sphere about the origin")
    print(f"  layers    {facts['layers']} cards deep: {facts['card_area_cm2']} cm2 of card "
          f"over {facts['covered_area_cm2']} cm2 of head. Past about 8 it renders as a "
          f"black mass")
    print(f"  maps      {args.texture} px, {args.slots} slots of {args.hairs} strands, "
          f"{facts['bytes']['diffuse'] // 1024} KiB diffuse, "
          f"{facts['bytes']['opacity'] // 1024} KiB opacity")
    for key in ("obj", "mtl", "diffuse", "opacity", "preview"):
        if key in facts["files"]:
            print(f"  wrote     {facts['files'][key]}")
    print(f"  facts     {shown(out / (stem + '.json'))}  ({facts['seconds']} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
