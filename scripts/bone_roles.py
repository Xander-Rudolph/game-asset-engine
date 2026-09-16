#!/usr/bin/env python3
"""Name an articulationxl skeleton's bones by role, and compile role poses onto it.

UniRig's articulationxl template calls every bone bone_0 to bone_N, and the
count and order change from figure to figure, so a pose file keyed on bone
names fits the one rig it was written for. This tool works out what each bone
is from the skeleton's geometry, with skin weights to settle which bone is the
head, then turns a pose written against those roles, in the character's own
axes, into the ordinary per-rig transforms file that render_sheet.py reads.

    # which bone is which: prints a table, writes output/rigged/unit_warrior.roles.json
    scripts/bone_roles.py map output/rigged/unit_warrior.fbx

    # one walk file for any articulationxl humanoid, compiled for this rig
    scripts/bone_roles.py compile poses/roles/walk.json output/rigged/unit_warrior.roles.json \\
        --out output/poses/unit_warrior_walk.json
    scripts/render_sheet.py output/rigged/unit_warrior.fbx \\
        --poses transforms:output/poses/unit_warrior_walk.json --angles 4 --size 220 --check

    # compile straight from the FBX (maps it first, writes no roles file)
    scripts/bone_roles.py compile poses/roles/attack.json output/rigged/unit_rogue.fbx \\
        --out output/poses/unit_rogue_attack.json

    # which way did each part move? Bone ends, in the character's axes
    scripts/bone_roles.py probe output/poses/unit_warrior_walk.json \\
        output/rigged/unit_warrior.fbx --frame 1

HOW THE ROLES ARE FOUND

Bone heads, tails and parents are read, plus each bone's summed skin weight for
the one call geometry cannot make (the head, below). Never names.

  root       the bone with no parent
  pelvis     the root, or failing that the first bone below it, with three or
             more children
  legs       the two chains off the pelvis that reach furthest from it; along
             each, the thigh and shin are the consecutive pair with the greatest
             combined length, a bone before them is the hip, the foot is the
             shin's child whose chain reaches furthest horizontally from the ankle,
             and the toe continues the foot
  spine      the remaining pelvis chain pointing most nearly away from the legs,
             followed through whichever child continues most nearly straight
  up         from the midpoint of the two ankles to the top of that chain
  forward    the way the feet point: the sum of both feet's ankle to toe tip
             vectors, with its up component removed
  right      forward crossed with up, so right is the character's own right
  chest      the first spine bone with chains leaving it to both sides; bones
             between it and the pelvis are spine, spine_2 and so on
  head       the last bone above the chest, unless that bone carries less than
             a quarter of the skin weight of the bone before it: then it is
             only an end marker at the top of the head, head_end, and the
             bone before it is the head. Bones between the chest and the head
             are neck, neck_2. When the bone before the last carries no skin
             weight (or the rig has none), the count decides: with three or
             more bones above the chest, the last is head_end
  arms       the two side chains off the chest; upper arm and forearm are the
             longest consecutive pair, a bone before them is the shoulder, the
             bone after them the hand
  sides      whichever ankle, and whichever wrist, lies further along right is
             the right one

Up and forward are snapped to the nearest armature axis when within 20 degrees
of it, and the table says how far off the raw direction was.

Roles: root pelvis spine [spine_2 ...] chest [neck neck_2 ...] head [head_end],
and per side left_ and right_ hip (only if the rig has one), shoulder,
upper_arm, forearm, hand, thigh, shin, foot, toe. On articulationxl rigs root and
pelvis are the same bone; a frame that names both applies root outside pelvis.
The map table also lists each role bone's skin weight and whether it is
connected to its parent, which decides whether translate can move it.

ROLE POSE FILES (poses/roles/*.json)

A JSON list of frames. Each frame maps a role to a transform:

    [
      {"_note": "keys starting with _ are notes and are ignored"},
      {"left_thigh":  {"rotate": [28, 0, 0]},
       "right_shin":  {"rotate": [-40, 0, 0]},
       "pelvis":      {"translate": [0, 0, -0.02]},
       "@shape_keys": {"jawOpen": 0.4}}
    ]

"@shape_keys" and "@props" are render_sheet.py's own keys and are copied into
the compiled frame unchanged.

"rotate" is degrees about the CHARACTER'S OWN axes, not the bone's:

  X  points to the character's right
  Y  points forward, the way the character faces
  Z  points up

Positive angles follow the right-hand rule, applied in Blender's XYZ order (X
first, then Y, then Z, each about the fixed character axes). So:

  +X  swings anything hanging below the joint forward (a thigh, an arm), and
      tips anything rising above it backward (spine, neck, head); a knee bend
      is a negative X on the shin, an elbow bend a positive X on the forearm
  +Y  rolls the top of a rising part toward the character's right, lifts a
      hanging left arm outward, and swings a hanging right arm in across the
      body
  +Z  turns the character to its left, seen from above: the right shoulder
      comes forward

Each rotation is about the character axes as the bone's parent carries them, so
a shin's rotation adds to its thigh's, as in any forward kinematic chain.

"translate" is in rig units along the same axes, and moves only a bone that is
not connected to its parent: Blender pins a connected bone's head to its
parent's tail and ignores its location. On the articulationxl test rigs the
chest, head, shins, upper arms and forearms are always connected, the pelvis,
spine, neck, thighs and shoulders never are, and hands, feet and toes vary, so
the map table says per bone. In practice, translate the pelvis.

The same numbers give the same motion on every rig whose rest pose has the arms
hanging at the sides, as articulationxl rigs do, because compile converts them
per bone. On a T-pose rig the arm rotations mean something else: an X that
swings a hanging arm forward mostly twists an arm held out level.

COMPILING

For each bone, the rotation is mapped from character axes to armature axes
(R_arm = C R C^T, C holding right, forward and up as columns) and then
conjugated by the bone's rest orientation in armature space (R_local =
B^T R_arm B), which is what a pose bone's own Euler rotation means. The result
is written as XYZ Euler degrees, the format render_sheet.py --poses transforms:
reads. Roles the rig lacks, and translates on connected bones, are listed,
dropped and make compile exit 1; the file is still written. A roles file from
an older map is refused: run map again.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import container, exec_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Up and forward within this many degrees of an armature axis are snapped to it.
SNAP_DEG = 20.0

# The last bone above the chest is only an end marker (head_end), not the head,
# when it carries less than this share of the skin weight of the bone before it.
END_SHARE = 0.25

# Roles files from an older map lack the connected flags and used an older head
# rule, so compile refuses them rather than compile a pose that silently misses.
ROLES_VERSION = 2

# The Blender half: import the rig, record every bone's rest geometry, and
# optionally pose it frame by frame the way render_sheet.py does and record
# where every bone ended up. All the role logic stays on the host.
BLENDER_SCRIPT = r'''
import bpy, json, math, os, sys
from mathutils import Euler

cfg = json.loads(sys.argv[-1])
bpy.ops.wm.read_factory_settings(use_empty=True)
path = cfg["model"]
ext = os.path.splitext(path)[1].lower()
if ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=path)
elif ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=path)
else:
    raise SystemExit(f"unsupported rig format: {ext}")
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
if not arms:
    raise SystemExit("no armature in that file")
arm = arms[0]

def r(v):
    return [round(float(x), 6) for x in v]

# Summed skin weight per bone, over the meshes this armature deforms. It tells
# a bone the mesh follows from an end marker that carries next to nothing.
weight = {b.name: 0.0 for b in arm.data.bones}
skinned = [o for o in bpy.data.objects if o.type == "MESH" and any(
    m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
for o in skinned:
    names = {g.index: g.name for g in o.vertex_groups}
    for v in o.data.vertices:
        for g in v.groups:
            n = names.get(g.group)
            if n in weight:
                weight[n] += g.weight

bones = [{"n": b.name, "p": b.parent.name if b.parent else None,
          "h": r(b.head_local), "t": r(b.tail_local),
          "m": [r(row) for row in b.matrix_local.to_3x3()],
          "c": bool(b.use_connect), "w": round(weight[b.name], 3)}
         for b in arm.data.bones]

frames, missing = [], set()
for spec in cfg.get("frames") or []:
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = Euler((0, 0, 0), "XYZ")
        pb.location = (0, 0, 0)
    for name, t in spec.items():
        if name.startswith("@"):  # render_sheet.py's shape key and property keys
            continue
        pb = arm.pose.bones.get(name)
        if pb is None:
            missing.add(name)
            continue
        if "rotate" in t:
            pb.rotation_euler = Euler([math.radians(a) for a in t["rotate"]], "XYZ")
        if "translate" in t:
            pb.location = t["translate"]
    bpy.context.view_layer.update()
    frames.append({pb.name: {"h": r(pb.head), "t": r(pb.tail),
                             "m": [r(row) for row in pb.matrix.to_3x3()]}
                   for pb in arm.pose.bones})

print("BONES " + json.dumps({"armature": arm.name, "bones": bones,
                             "frames": frames, "missing": sorted(missing)}))
'''


class RoleError(Exception):
    pass


# --- small vector and matrix helpers (3-vectors, row-major 3x3) -------------

def sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def scale(a, s):
    return [a[0] * s, a[1] * s, a[2] * s]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def length(a):
    return math.sqrt(dot(a, a))


def unit(a):
    n = length(a)
    if n < 1e-9:
        raise RoleError("a direction came out as zero length")
    return scale(a, 1.0 / n)


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
            for i in range(3)]


def transpose(a):
    return [[a[j][i] for j in range(3)] for i in range(3)]


def apply(m, v):
    return [dot(m[0], v), dot(m[1], v), dot(m[2], v)]


def euler_to_matrix(deg):
    """XYZ Euler in degrees to a matrix, Blender's order: Rz @ Ry @ Rx."""
    x, y, z = (math.radians(a) for a in deg)
    cx, sx, cy, sy, cz, sz = (math.cos(x), math.sin(x), math.cos(y),
                              math.sin(y), math.cos(z), math.sin(z))
    rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    return matmul(rz, matmul(ry, rx))


def matrix_to_euler(m):
    """The inverse of euler_to_matrix, in degrees, with Y kept in [-90, 90]."""
    cy = math.hypot(m[0][0], m[1][0])
    y = math.atan2(-m[2][0], cy)
    if cy > 1e-6:
        x = math.atan2(m[2][1], m[2][2])
        z = math.atan2(m[1][0], m[0][0])
    else:  # Y at +-90 degrees: X and Z turn about the same axis, so fold into X
        x = math.atan2(-m[1][2], m[1][1])
        z = 0.0
    return [math.degrees(x), math.degrees(y), math.degrees(z)]


AXES = {"+X": [1, 0, 0], "-X": [-1, 0, 0], "+Y": [0, 1, 0],
        "-Y": [0, -1, 0], "+Z": [0, 0, 1], "-Z": [0, 0, -1]}


def snap(v):
    """Nearest armature axis if within SNAP_DEG, else v. Returns (vec, name, deg)."""
    v = unit(v)
    name, best = max(AXES.items(), key=lambda kv: dot(kv[1], v))
    deg = math.degrees(math.acos(max(-1.0, min(1.0, dot(best, v)))))
    if deg <= SNAP_DEG:
        return [float(c) for c in best], name, deg
    return v, None, deg


def axis_label(v, name):
    return name or "(" + ", ".join(f"{c:+.3f}" for c in v) + ")"


# --- deriving roles ----------------------------------------------------------

def derive(bones: list[dict]) -> dict:
    """Roles from rest geometry. `bones` as dumped: n, p, h, t, m."""
    by = {b["n"]: b for b in bones}
    kids = {b["n"]: [] for b in bones}
    for b in bones:
        if b["p"] is not None:
            kids[b["p"]].append(b["n"])

    def subtree(n):
        out, stack = [], [n]
        while stack:
            x = stack.pop()
            out.append(x)
            stack.extend(kids[x])
        return out

    def direction(n):
        return unit(sub(by[n]["t"], by[n]["h"]))

    def bone_len(n):
        return length(sub(by[n]["t"], by[n]["h"]))

    def straight(n):
        """n, then whichever child continues most nearly straight, to a leaf."""
        chain = [n]
        while kids[chain[-1]]:
            d = direction(chain[-1])
            chain.append(max(kids[chain[-1]], key=lambda c: dot(direction(c), d)))
        return chain

    def tip(n):
        return by[straight(n)[-1]]["t"]

    roots = [b["n"] for b in bones if b["p"] is None]
    if not roots:
        raise RoleError("no bone without a parent, so no root")
    root = max(roots, key=lambda n: len(subtree(n)))

    pelvis = root
    while len(kids[pelvis]) < 3:
        if len(kids[pelvis]) != 1:
            raise RoleError(
                f"no pelvis: {pelvis} has {len(kids[pelvis])} children, and the "
                "pelvis is the root, or the first bone below it, with three or "
                "more (the spine and two legs)")
        pelvis = kids[pelvis][0]
    ph = by[pelvis]["h"]

    reach = {c: length(sub(tip(c), ph)) for c in kids[pelvis]}
    legs = sorted(kids[pelvis], key=lambda c: -reach[c])[:2]
    leg_dir = unit(add(sub(tip(legs[0]), ph), sub(tip(legs[1]), ph)))
    others = [c for c in kids[pelvis] if c not in legs]
    spine_child = min(others, key=lambda c: dot(unit(sub(tip(c), ph)), leg_dir))
    if dot(unit(sub(tip(spine_child), ph)), leg_dir) >= 0:
        raise RoleError(f"no chain off the pelvis ({pelvis}) points away from "
                        "the legs, so no spine")

    def longest_pair(chain, what):
        if len(chain) < 2:
            raise RoleError(f"the {what} chain from {chain[0]} is one bone long")
        i = max(range(len(chain) - 1),
                key=lambda k: bone_len(chain[k]) + bone_len(chain[k + 1]))
        return i

    leg_parts = []
    for c in legs:
        chain = straight(c)
        i = longest_pair(chain, "leg")
        leg_parts.append({"chain": chain, "i": i,
                          "thigh": chain[i], "shin": chain[i + 1]})

    spine = straight(spine_child)
    ankles = scale(add(by[leg_parts[0]["shin"]]["t"],
                       by[leg_parts[1]["shin"]]["t"]), 0.5)
    up_raw = sub(by[spine[-1]]["t"], ankles)
    up, up_name, up_off = snap(up_raw)

    def flat(v):
        return sub(v, scale(up, dot(v, up)))

    toe_sum = [0.0, 0.0, 0.0]
    for lp in leg_parts:
        shin = lp["shin"]
        if not kids[shin]:
            raise RoleError(f"the shin {shin} has no child, so there is no foot "
                            "to tell which way the figure faces")
        at = by[shin]["t"]
        foot = max(kids[shin], key=lambda k: max(
            length(flat(sub(by[x]["t"], at))) for x in subtree(k)))
        lp["foot"] = foot
        after = straight(foot)
        lp["toe"] = after[1] if len(after) > 1 else None
        toe_sum = add(toe_sum, sub(by[after[-1]]["t"], by[foot]["h"]))
    fwd_flat = flat(toe_sum)
    if length(fwd_flat) < 1e-6:
        raise RoleError("the feet point straight up or down, so no facing")
    forward, fwd_name, fwd_off = snap(fwd_flat)
    forward = unit(flat(forward))
    right = cross(forward, up)
    right_name = next((k for k, v in AXES.items()
                       if fwd_name and up_name and dot(v, right) > 0.999), None)

    # chest: first spine bone with side chains going both ways
    chest, arm_roots = None, None
    for k, s in enumerate(spine[:-1]):
        sides = [c for c in kids[s] if c != spine[k + 1]]
        lat = {c: dot(sub(tip(c), by[s]["h"]), right) for c in sides}
        pos = [c for c in sides if lat[c] > 0]
        neg = [c for c in sides if lat[c] < 0]
        if pos and neg:
            chest = s
            arm_roots = (max(pos, key=lambda c: lat[c]),
                         min(neg, key=lambda c: lat[c]))
            break
    if chest is None:
        raise RoleError("no spine bone has chains leaving it to both sides, "
                        "so no chest and no arms")

    roles = {"root": root, "pelvis": pelvis}
    ci = spine.index(chest)
    for k, b in enumerate(spine[:ci]):
        roles["spine" if k == 0 else f"spine_{k + 1}"] = b
    roles["chest"] = chest
    above = spine[ci + 1:]
    # The chain ends in a leaf. On some rigs that leaf is the head; on others it
    # is only an end marker past the top of the skull, which the mesh barely
    # follows, and the bone before it is the head.
    skinned = any(b.get("w", 0.0) > 0 for b in bones)
    head_end, head_rule = None, None
    if len(above) >= 2:
        last, before = above[-1], above[-2]
        w_last, w_before = by[last].get("w", 0.0), by[before].get("w", 0.0)
        if w_before > 0:
            share = w_last / w_before
            if share < END_SHARE:
                head_end = last
            head_rule = (f"{last} carries {share:.3f} of {before}'s skin weight "
                         f"({w_last:.1f} of {w_before:.1f}); under {END_SHARE} "
                         f"makes it head_end: {'yes' if head_end else 'no'}")
        else:
            if len(above) >= 3:
                head_end = last
            why = (f"{before} carries no skin weight" if skinned
                   else "no skin weights")
            head_rule = (f"{why}, so by count: {len(above)} bones above the "
                         f"chest; three or more makes the last head_end: "
                         f"{'yes' if head_end else 'no'}")
    head_chain = above[:-1] if head_end else above
    for k, b in enumerate(head_chain[:-1]):
        roles["neck" if k == 0 else f"neck_{k + 1}"] = b
    if head_chain:
        roles["head"] = head_chain[-1]
    if head_end:
        roles["head_end"] = head_end

    # sides: the ankle and the hand further along right are the right ones
    leg_parts.sort(key=lambda lp: -dot(by[lp["shin"]]["t"], right))
    for side, lp in zip(("right", "left"), leg_parts):
        if lp["i"] >= 1:
            roles[f"{side}_hip"] = lp["chain"][lp["i"] - 1]
        roles[f"{side}_thigh"] = lp["thigh"]
        roles[f"{side}_shin"] = lp["shin"]
        roles[f"{side}_foot"] = lp["foot"]
        if lp["toe"]:
            roles[f"{side}_toe"] = lp["toe"]

    arm_parts = []
    for c in arm_roots:
        chain = straight(c)
        i = longest_pair(chain, "arm")
        arm_parts.append((chain, i))
    arm_parts.sort(key=lambda part: -dot(by[part[0][part[1] + 1]]["t"], right))
    for side, (chain, i) in zip(("right", "left"), arm_parts):
        if i >= 1:
            roles[f"{side}_shoulder"] = chain[i - 1]
        roles[f"{side}_upper_arm"] = chain[i]
        roles[f"{side}_forearm"] = chain[i + 1]
        if i + 2 < len(chain):
            roles[f"{side}_hand"] = chain[i + 2]

    named = {}
    for role, b in roles.items():
        named[b] = role  # pelvis rather than root when they share a bone
    unassigned = {}
    for b in bones:
        if b["n"] in named:
            continue
        p = b["p"]
        while p is not None and p not in named:
            p = by[p]["p"]
        unassigned[b["n"]] = f"below {named[p]}" if p else "outside the skeleton"

    heights = [dot(by[n][k], up) for n in by for k in ("h", "t")]
    role_bones = dict.fromkeys(roles.values())
    return {
        "version": ROLES_VERSION,
        "bones": len(bones),
        "axes": {"right": right, "forward": forward, "up": up},
        "axis_names": {"right": right_name, "forward": fwd_name, "up": up_name},
        "facing": {
            "method": "sum of both feet's ankle to toe tip vectors, up removed",
            "raw_forward": [round(c, 4) for c in unit(fwd_flat)],
            "forward_off_axis_deg": round(fwd_off, 2),
            "raw_up": [round(c, 4) for c in unit(up_raw)],
            "up_off_axis_deg": round(up_off, 2),
        },
        "height": round(max(heights) - min(heights), 4),
        "head_rule": head_rule,
        "roles": roles,
        "unassigned": unassigned,
        "rest": {b: by[b]["m"] for b in role_bones},
        "rest_head": {b: by[b]["h"] for b in role_bones},
        "connected": {b: bool(by[b].get("c", False)) for b in role_bones},
        "weight": {b: by[b].get("w", 0.0) for b in role_bones},
    }


# --- compiling ---------------------------------------------------------------

ROLE_ORDER = ["root", "pelvis"]

# render_sheet.py's own per-pose keys, copied into the compiled frame unchanged.
PASS_THROUGH = ("@shape_keys", "@props")


def three_numbers(v) -> bool:
    return (isinstance(v, list) and len(v) == 3 and all(
        isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
        for x in v))


def compile_frames(frames: list, rolemap: dict) -> tuple[list, dict, dict]:
    """Role frames to transforms frames. Returns (frames, missing, ignored):
    missing maps a role the rig lacks to its frame numbers, ignored maps a role
    whose translate Blender would ignore (a connected bone) to its frame numbers."""
    axes = rolemap["axes"]
    c = transpose([axes["right"], axes["forward"], axes["up"]])  # columns
    roles, rest, connected = rolemap["roles"], rolemap["rest"], rolemap["connected"]
    out, missing, ignored = [], {}, {}
    for fi, frame in enumerate(frames, 1):
        if not isinstance(frame, dict):
            raise SystemExit(f"frame {fi}: expected an object of role: transform")
        oframe = {}
        for key in frame:
            if key.startswith("@"):
                if key not in PASS_THROUGH:
                    raise SystemExit(f"frame {fi}: unknown key {key!r}; render_sheet.py "
                                     f"reads only {' and '.join(PASS_THROUGH)}")
                oframe[key] = frame[key]
        names = [k for k in frame if not k.startswith(("_", "@"))]
        names.sort(key=lambda k: ROLE_ORDER.index(k) if k in ROLE_ORDER else 99)
        per_bone: dict[str, dict] = {}
        for role in names:
            t = frame[role]
            if not isinstance(t, dict):
                raise SystemExit(f"frame {fi}, {role}: expected an object such as "
                                 '{"rotate": [x, y, z]}')
            unknown = set(t) - {"rotate", "translate"}
            if unknown:
                raise SystemExit(f"frame {fi}, {role}: unknown keys {sorted(unknown)}")
            for k in ("rotate", "translate"):
                if k in t and not three_numbers(t[k]):
                    raise SystemExit(f"frame {fi}, {role}: {k} must be three numbers "
                                     f"[x, y, z], not {json.dumps(t[k])}")
            bone = roles.get(role)
            if bone is None:
                missing.setdefault(role, []).append(fi)
                continue
            acc = per_bone.setdefault(bone, {})
            if "rotate" in t:
                r = euler_to_matrix(t["rotate"])
                acc["R"] = matmul(acc["R"], r) if "R" in acc else r
            if "translate" in t:
                if connected.get(bone):
                    # Blender pins a connected bone's head to its parent's tail
                    # and ignores its location, so the move would do nothing.
                    ignored.setdefault(role, []).append(fi)
                else:
                    acc["T"] = add(acc.get("T", [0, 0, 0]),
                                   [float(v) for v in t["translate"]])
        for bone, acc in per_bone.items():
            b = rest[bone]
            bt = transpose(b)
            o = {}
            if "R" in acc:
                r_arm = matmul(c, matmul(acc["R"], transpose(c)))
                o["rotate"] = [round(v, 3) + 0.0 for v in
                               matrix_to_euler(matmul(bt, matmul(r_arm, b)))]
            if "T" in acc:
                o["translate"] = [round(v, 5) + 0.0 for v in apply(bt, apply(c, acc["T"]))]
            if o:
                oframe[bone] = o
        out.append(oframe)
    return out, missing, ignored


# --- the command line --------------------------------------------------------

def resolve(p: Path) -> Path:
    return p if p.is_absolute() else ROOT / p


def to_container(p: Path) -> str:
    p = p.resolve()
    for host, cont in ((ROOT / "output", "/app/output"), (ROOT / "input", "/app/input")):
        try:
            return f"{cont}/{p.relative_to(host)}"
        except ValueError:
            continue
    raise SystemExit(f"{p}: the container only sees output/ and input/, "
                     "so put the rig under one of them")


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def blender(model: Path, frames: list | None, timeout: int) -> dict:
    if not model.exists():
        raise SystemExit(f"no such rig: {model}")
    info = exec_json(BLENDER_SCRIPT, {"model": to_container(model), "frames": frames},
                     "BONES ", timeout=timeout)
    if info is None:
        raise SystemExit(f"Blender did not return the skeleton of {rel(model)} "
                         f"(container {container()})")
    return info


def map_rig(model: Path, timeout: int) -> dict:
    info = blender(model, None, timeout)
    try:
        m = derive(info["bones"])
    except RoleError as e:
        raise SystemExit(f"{rel(model)}: {e}")
    m = {"rig": rel(model), "armature": info["armature"], **m}
    return m


def print_table(m: dict) -> None:
    ax, names, f = m["axes"], m["axis_names"], m["facing"]
    left = scale(ax["right"], -1)
    left_name = next((k for k, v in AXES.items() if dot(v, left) > 0.999), None)
    print(f"  rig      {m['rig']}  ({m['bones']} bones, armature {m['armature']})")
    print(f"  up       {axis_label(ax['up'], names['up'])}"
          f"  ({f['up_off_axis_deg']:.1f} deg from the ankles to the top of the spine)")
    print(f"  forward  {axis_label(ax['forward'], names['forward'])}"
          f"  ({f['forward_off_axis_deg']:.1f} deg from the way the toes point)")
    print(f"  right    {axis_label(ax['right'], names['right'])}"
          f"  (the character's own right; its left is "
          f"{axis_label(left, left_name)})")
    if m["head_rule"]:
        print(f"  head_end {m['head_rule']}")
    print()
    bw = max([9] + [len(b) for b in m["roles"].values()])
    print(f"  {'role':<16} {'bone':<{bw}} {'head':<26} {'skin weight':>11}  connected")
    for role, bone in m["roles"].items():
        h = m["rest_head"][bone]
        print(f"  {role:<16} {bone:<{bw}} ({h[0]:+.3f}, {h[1]:+.3f}, {h[2]:+.3f})"
              f"  {m['weight'][bone]:>11.1f}  {'yes' if m['connected'][bone] else 'no'}")
    if m["unassigned"]:
        groups: dict[str, list] = {}
        for b, where in m["unassigned"].items():
            groups.setdefault(where, []).append(b)
        print()
        for where, bs in groups.items():
            print(f"  no role  {', '.join(bs)}  ({where})")


def default_roles_path(model: Path) -> Path:
    return ROOT / "output" / "rigged" / f"{model.stem}.roles.json"


def read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise SystemExit(f"{rel(p)}: not valid JSON: {e}")


def read_list(p: Path, what: str) -> list:
    if not p.exists():
        raise SystemExit(f"no such file: {p}")
    data = read_json(p)
    if not isinstance(data, list):
        raise SystemExit(f"{rel(p)}: expected a JSON list of {what}")
    return data


def load_rolemap(rig: Path, timeout: int) -> dict:
    if not rig.exists():
        raise SystemExit(f"no such rig or roles file: {rig}")
    if rig.suffix == ".json":
        m = read_json(rig)
        if not isinstance(m, dict) or "roles" not in m or "rest" not in m:
            raise SystemExit(f"{rel(rig)}: not a roles file from bone_roles.py map")
        if m.get("version") != ROLES_VERSION:
            raise SystemExit(f"{rel(rig)}: made by an older bone_roles.py map, before "
                             "the head_end rule and connected bones; run map again")
        return m
    return map_rig(rig, timeout)


def cmd_map(args) -> int:
    model = resolve(args.rig)
    m = map_rig(model, args.timeout)
    print_table(m)
    out = resolve(args.out) if args.out else default_roles_path(model)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, indent=1) + "\n")
    print(f"\n  wrote    {rel(out)}")
    return 0


def cmd_compile(args) -> int:
    src = resolve(args.roleposes)
    frames = read_list(src, "frames")
    rig = resolve(args.rig)
    m = load_rolemap(rig, args.timeout)
    out_frames, missing, ignored = compile_frames(frames, m)
    stem = rig.name.split(".")[0]
    out = resolve(args.out) if args.out else ROOT / "output" / "poses" / f"{stem}_{src.stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("[\n" + ",\n".join(" " + json.dumps(f) for f in out_frames) + "\n]\n")
    bones = sorted({b for f in out_frames for b in f if not b.startswith("@")},
                   key=lambda b: (len(b), b))
    copied = [k for k in PASS_THROUGH if any(k in f for f in out_frames)]
    print(f"  poses    {rel(src)}  ({len(frames)} frame(s))")
    print(f"  rig      {m['rig']}  ({m['bones']} bones)")
    print(f"  bones    {', '.join(bones)}")
    if copied:
        print(f"  copied   {', '.join(copied)}, unchanged for render_sheet.py")
    if len({m['roles'].get(r) for r in ('root', 'pelvis')}) == 1 and any(
            'root' in f and 'pelvis' in f for f in frames):
        print("  note     root and pelvis are one bone here; root applied outside pelvis")
    print(f"  wrote    {rel(out)}")
    for role, fis in missing.items():
        print(f"  ! role not in this rig: {role} (frame {', '.join(map(str, fis))})")
    for role, fis in ignored.items():
        print(f"  ! translate on a connected bone, which Blender ignores: {role} "
              f"({m['roles'][role]}, frame {', '.join(map(str, fis))})")
    if missing or ignored:
        print("  ! those parts of the pose were dropped")
        return 1
    return 0


def cmd_probe(args) -> int:
    src = resolve(args.transforms)
    frames = read_list(src, "poses")
    pick = list(range(1, len(frames) + 1)) if args.frame is None else [args.frame]
    for fi in pick:
        if not 1 <= fi <= len(frames):
            raise SystemExit(f"--frame {fi}: the file has {len(frames)} frame(s)")
    rig = resolve(args.rig)
    info = blender(rig, [frames[fi - 1] for fi in pick], args.timeout)
    try:
        m = derive(info["bones"])
    except RoleError as e:
        raise SystemExit(f"{rel(rig)}: {e}")
    by = {b["n"]: b for b in info["bones"]}
    ax = m["axes"]
    result = {"rig": rel(rig), "transforms": rel(src), "height": m["height"],
              "missing_bones": info["missing"], "frames": {}}
    for fi, posed in zip(pick, info["frames"]):
        rows = {}
        for role, bone in m["roles"].items():
            d = sub(posed[bone]["t"], by[bone]["t"])
            rows[role] = {"bone": bone,
                          "right": round(dot(d, ax["right"]), 4),
                          "forward": round(dot(d, ax["forward"]), 4),
                          "up": round(dot(d, ax["up"]), 4)}
        result["frames"][fi] = rows
    if args.json:
        print(json.dumps(result, indent=1))
        return 1 if info["missing"] else 0
    print(f"  rig      {rel(rig)}  (height {m['height']:.3f} units, bone ends "
          "moved along the character's axes)")
    if info["missing"]:
        print(f"  ! bones not in the rig: {', '.join(info['missing'])}")
    for fi, rows in result["frames"].items():
        print(f"\n  frame {fi}")
        bw = max([9] + [len(r["bone"]) for r in rows.values()])
        print(f"  {'role':<16} {'bone':<{bw}} {'right':>8} {'forward':>8} {'up':>8}")
        for role, r in rows.items():
            if not args.all and max(abs(r[k]) for k in ("right", "forward", "up")) < 1e-3:
                continue
            print(f"  {role:<16} {r['bone']:<{bw}} {r['right']:+8.3f} "
                  f"{r['forward']:+8.3f} {r['up']:+8.3f}")
    return 1 if info["missing"] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("map", help="derive bone roles from a rig's geometry")
    p.add_argument("rig", type=Path, help="rigged .fbx (or .glb)")
    p.add_argument("--out", type=Path,
                   help="roles JSON (default output/rigged/<stem>.roles.json)")
    p.add_argument("--timeout", type=int, default=600,
                   help="seconds before giving up on Blender (default 600)")
    p.set_defaults(func=cmd_map)

    p = sp.add_parser("compile", help="role pose file to this rig's transforms file")
    p.add_argument("roleposes", type=Path, help="poses/roles/*.json")
    p.add_argument("rig", type=Path, help="a .roles.json from map, or the rig itself")
    p.add_argument("--out", type=Path,
                   help="transforms JSON (default output/poses/<rig>_<poses>.json)")
    p.add_argument("--timeout", type=int, default=600,
                   help="seconds before giving up on Blender when RIG is a model "
                        "(default 600)")
    p.set_defaults(func=cmd_compile)

    p = sp.add_parser("probe", help="how far each role's bone end moves, per frame")
    p.add_argument("transforms", type=Path, help="a transforms file render_sheet.py reads")
    p.add_argument("rig", type=Path, help="rigged .fbx (or .glb)")
    p.add_argument("--frame", type=int, help="1-based frame (default: every frame)")
    p.add_argument("--all", action="store_true", help="list roles that did not move too")
    p.add_argument("--json", action="store_true", help="print JSON instead of a table")
    p.add_argument("--timeout", type=int, default=600,
                   help="seconds before giving up on Blender (default 600)")
    p.set_defaults(func=cmd_probe)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
