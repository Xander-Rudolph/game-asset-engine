#!/usr/bin/env python3
"""Roll random Genesis characters from the installed Daz library and render them.

Every character is a draw from what the library actually holds: a Daz character
preset for the face and skin, another character's shape dial mixed in, a height
dial, an eyebrow colour, hair, a beard, an outfit, a weapon and a pose. Each one
is built by scripts/daz_import_probe.py in the container's Blender, rendered
front and side by scripts/render_sheet.py, and written down in a JSON beside its
two images, with the command that rebuilds it.

    # what the library offers for each slot
    scripts/daz_characters.py list

    # twelve characters, the same twelve every time for one seed
    scripts/daz_characters.py make --count 12 --seed 20260921

    # one character, its .blend kept, at sprite size
    scripts/daz_characters.py make --count 1 --seed 7 --size 256 --keep-blend

Nothing here reaches the Daz website. The library is the one
scripts/daz_library.py installed from zips the user downloaded in a browser.

LICENCE. Everything this writes is Daz content under the Daz EULA. The renders
may ship in a game on the conditions in docs/reference/daz-genesis.md; the
.blend, the figure, its morphs, its outfits and anything exported from them may
not, without an Interactive License for each product used. None of it goes into
an AI stage, a commit or the container image. output/daz/ is gitignored.

WHAT A RUN COSTS. Measured on 2026-09-21 in comfyui-packaged on the reference
machine, twelve characters in the rest pose at 768 px with Cycles on the card:
10.3 to 25.5 s to build each one and 2.1 to 3.1 s to draw its two views,
230.9 s and 30.9 s over the twelve, with no garment left inside a body. Each
.blend was 71 to 179 MB and is deleted once the views are drawn, unless
--keep-blend, which left 8.1 MB of images, reports and one 4096 by 1629 px
sheet.
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daz_import_probe import anatomy_from_figure, read_duf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "daz" / "characters"
PROBE = ROOT / "scripts" / "daz_import_probe.py"
SHEET = ROOT / "scripts" / "render_sheet.py"
DEFAULT_LIBRARY = Path("/models/daz_library")

# Poses a character sheet can use: the figure has to be on its feet and facing
# the camera. The library's other poses are seated, laying or flying.
UPRIGHT = re.compile(r"standing|walking|flexing|running|stretching", re.I)
# The masculine and feminine pose folders, and the shared one.
POSE_FOLDERS = {"masculine": ("Base", "Base Masculine"),
                "feminine": ("Base", "Base Feminine"),
                "unknown": ("Base",)}
# Which of the six Genesis 9 characters are built on the masculine base. Read
# from their skin: the preset names its maps G9Masculine01 or G9Feminine01.
MASCULINE_MAP = re.compile(r"Masculine", re.I)
# Folders under a generation that hold something other than a character.
NOT_CHARACTERS = {"Clothing", "Hair", "Poses", "Props", "Anatomy", "Materials",
                  "Developer Kit", "Expressions", "Shapes"}
# A preset that wears a whole outfit at once, however its maker spelled it.
# The bang is a Daz shelf convention: it sorts a name to the top of the folder,
# and that is where a vendor puts the load-everything preset, whether the name
# begins with it ("!All") or carries it mid-name ("Asphalt Hound !Outfit").
WHOLE_OUTFIT = re.compile(r"(?:^|\s)!|complete|whole set|load all|\bset\b", re.I)
# Eyebrow colours the library ships that no one grows. Still rolled, but one
# character in five rather than one in three.
FANCY_COLOURS = {"Dark Blue", "Fuchsia", "Neon Blue"}
# Characters to leave out of a roll, and why.
SKIP_CHARACTERS = {
    "Julian 9 Surfer": "the owner judged it broken on 2026-09-21",
}
# Wearables to leave out of a roll, and why.
SKIP_WEARABLES = {
    # Measured on 2026-09-18: this strand hair's 236,136 vertex mesh carries one
    # vertex group, a dForce pin group with no bone, so a pose moves none of it
    # and deleting it changed 0 pixels of a 340 px render. Only its 1085 vertex
    # cap draws, so a character wearing it looks bald.
    "G9 Base dForce Pixie Hair": "a dForce strand mesh that renders nothing here",
}


def product_key(name: str) -> str:
    """The first two words of a product's name, lowercased.

    What ties a wearable to the character it was made for. A hair, a beard and
    an outfit that ship beside a character carry that character's name: "Wise
    Wizard HD" the figure, "Wise Wizard 2025" the beard, "Wise Wizard Remaster
    2025" the set. Measured on 2026-09-21, that beard floats a mean of 33.26 mm
    off another character's chin, so it is rolled only onto its own.
    """
    words = [w for w in re.sub(r"\s+for\s+Genesis\s+\d.*$", "", name, flags=re.I).split()
             if w.lower() not in ("dforce", "g9", "the")]
    return " ".join(words[:2]).casefold()


def character_build(path: Path) -> str | None:
    """Whether a character is built on the masculine or the feminine base.

    Read from the file rather than guessed at: a Genesis 9 character preset
    names the base it uses, through its skin maps or its morphs, hundreds of
    times. A file that names neither is left out of a roll, because the base
    is what decides which skins fit it.
    """
    try:
        text = raw_duf(path)
    except (OSError, ValueError, EOFError):
        return None
    masculine = len(re.findall("Masculine", text))
    feminine = len(re.findall("Feminine", text))
    if masculine == feminine:
        return None
    return "masculine" if masculine > feminine else "feminine"


def own_skin(path: Path) -> bool:
    """Whether a character preset brings its own texture maps."""
    try:
        return bool(read_duf(path).get("image_library"))
    except (OSError, ValueError, EOFError):
        return False


def raw_duf(path: Path) -> str:
    """A .duf as text, gzip-compressed or plain."""
    try:
        with gzip.open(path, "rt", encoding="utf-8-sig") as f:
            return f.read()
    except gzip.BadGzipFile:
        return path.read_text(encoding="utf-8-sig")


def duf_type(path: Path) -> str:
    try:
        return str(read_duf(path).get("asset_info", {}).get("type", ""))
    except (OSError, ValueError, EOFError):
        return ""


def rel(lib: Path, path: Path) -> str:
    return path.relative_to(lib).as_posix()


def eyebrow_colours(lib: Path, figure: str) -> list[dict]:
    """The colour presets for whichever eyebrow figure this character loads."""
    out = []
    for post in anatomy_from_figure(lib / figure):
        path = lib / post
        if "eyebrow" not in path.stem.lower():
            continue
        for preset in sorted((path.parent.parent / "Materials").glob("*Color *.duf")):
            out.append({"file": rel(lib, preset), "colour": preset.stem.split("Color ")[-1]})
    return out


def catalogue(lib: Path, generation: str | None = None) -> dict:
    """What the library offers for each slot, found by looking, not hardcoded.

    One figure generation at a time. A Genesis 8 hair and a Genesis 9 Toon
    outfit both sit in the same library and neither fits a Genesis 9 figure, so
    the generation is the folder under People/ that the character presets are
    in, and every other slot is read from that same folder.
    """
    if generation is None:
        holders = sorted({path.parts[1] for path in
                          (p.relative_to(lib) for p in lib.glob("People/*/Characters/* for *.duf"))})
        generation = holders[0] if holders else "Genesis 9"
    cat = {"characters": [], "eyebrows": [], "hair": [], "beards": [],
           "outfits": {}, "props": [],
           "poses": {"masculine": [], "feminine": [], "unknown": []},
           "shape_dials": [], "skins": {}, "library": str(lib), "generation": generation,
           "skipped": []}
    here = f"People/{generation}"

    # A character preset is usually under Characters/, and not always: one
    # vendor puts its own under People/<generation>/<vendor>/<product>/. So
    # every .duf outside the folders that hold something else is read, and the
    # file's own asset type decides. The generation's base figure is a
    # character too, and is not one to roll: it has no shape and no skin.
    base_figure = (lib / here / f"{generation}.duf").resolve()
    for path in sorted(lib.glob(f"{here}/**/*.duf")):
        if any(part in NOT_CHARACTERS for part in path.relative_to(lib / here).parts[:-1]):
            continue
        if path.resolve() == base_figure or duf_type(path) != "character":
            continue
        build = character_build(path)
        name = path.stem.split(" for ")[0].strip()
        if name in SKIP_CHARACTERS:
            cat["skipped"].append({"name": name, "why": SKIP_CHARACTERS[name]})
            continue
        if build is None:
            # No base named. That only matters because the base decides which
            # skins fit, so a character that brings its own skin is still
            # rollable and simply keeps it.
            if own_skin(path):
                cat["characters"].append({"file": rel(lib, path), "name": name,
                                          "build": "unknown"})
            else:
                cat["skipped"].append({"name": name,
                                       "why": "it ships no skin of its own and its .duf says "
                                              "nothing about which base's skin would fit it"})
            continue
        cat["characters"].append({"file": rel(lib, path), "name": name, "build": build})

    # The eyebrows are a figure of their own, and which one a character loads is
    # its own business: the six Genesis 9 characters are split between card and
    # fibre brows, whose materials are named differently. So the colours are
    # read per character, from the eyebrow figure that character's own post-load
    # script names.
    for entry in cat["characters"]:
        entry["eyebrows"] = eyebrow_colours(lib, entry["file"])
    cat["eyebrows"] = sorted({e["colour"] for c in cat["characters"] for e in c["eyebrows"]})

    for path in sorted(lib.glob(f"{here}/Hair/*/*/*.duf")):
        if duf_type(path) != "wearable":
            continue
        if path.stem in SKIP_WEARABLES:
            cat["skipped"].append({"name": path.stem, "why": SKIP_WEARABLES[path.stem]})
            continue
        # A hair keeps its colours in a folder beside it, one preset each.
        # Usually they are named after the hair, "Mavick Hair" and "Mavick Hair
        # Black", and one product names them after nothing in particular,
        # "Wise Wizard LongBeard" and "WWBeard Grey". So the named ones are
        # taken when there are any, and otherwise every material preset in a
        # folder beside the wearable, whose last word is the colour. That
        # second rule only holds while one wearable owns the folder, which is
        # checked: a folder shared by a hair and a beard keeps the first rule.
        colours = [{"file": rel(lib, preset),
                    "colour": preset.stem[len(path.stem):].strip()}
                   for preset in sorted(path.parent.glob(f"*/{path.stem} *.duf"))]
        if not colours and sum(1 for sib in path.parent.glob("*.duf")
                               if duf_type(sib) == "wearable") == 1:
            for preset in sorted(path.parent.glob("*/*.duf")):
                if duf_type(preset).startswith("preset_material") or \
                        duf_type(preset) == "preset_hierarchical_material":
                    colours.append({"file": rel(lib, preset),
                                    "colour": preset.stem.split()[-1]})
        where = cat["beards"] if "beard" in path.stem.lower() else cat["hair"]
        where.append({"file": rel(lib, path), "name": path.stem, "colours": colours})

    for path in sorted(lib.glob(f"{here}/Materials/*/*/G9 * Skin * MAT.duf")):
        build = "masculine" if "Masculine" in path.stem else "feminine"
        cat["skins"].setdefault(build, []).append(
            {"file": rel(lib, path), "name": path.stem.replace("G9 ", "").replace(" MAT", "")})

    for path in sorted(lib.glob(f"{here}/Clothing/*/*/*.duf")):
        if duf_type(path) != "wearable" or path.stem in SKIP_WEARABLES:
            continue
        cat["outfits"].setdefault(path.parent.name, []).append(
            {"file": rel(lib, path), "name": path.stem})

    for path in sorted(lib.glob(f"{here}/Props/*/*/*/*.duf")):
        if not re.search(r" (Base|Masculine|Feminine) (LT|RT)$", path.stem):
            continue
        if duf_type(path) != "wearable":
            continue
        weapon, build, hand = re.match(r"(.+) (Base|Masculine|Feminine) (LT|RT)$",
                                       path.stem).groups()
        cat["props"].append({"file": rel(lib, path), "name": path.stem, "weapon": weapon,
                             "build": build.lower(), "hand": hand})

    for path in sorted(lib.glob(f"{here}/Poses/*/*/*/*.duf")):
        for build, folders in POSE_FOLDERS.items():
            if path.parent.name in folders:
                entry = {"file": rel(lib, path), "name": path.stem,
                         "upright": bool(UPRIGHT.search(path.stem))}
                cat["poses"][build].append(entry)

    # Whatever ships beside a character belongs to that character.
    owners = {product_key(c["name"]): c["name"] for c in cat["characters"]}
    for entry in cat["hair"] + cat["beards"] + [o for g in cat["outfits"].values() for o in g]:
        folder = PurePosixPath(entry["file"]).parent
        if folder.name.lower() == "individual items":
            folder = folder.parent
        entry["owner"] = owners.get(product_key(folder.name))

    # Two folders of dials, and a character takes one of them: the probe loads
    # one custom morph folder per run, and no standard morph set carries either
    # (the "body" set is the Base Pose folder, from the add-on's own path table).
    base = lib / f"data/Daz 3D/{generation}/Base/Morphs/Daz 3D"
    for path in sorted((base / "Base Characters 9").glob("*_figure_ctrl_Character.dsf")):
        cat["shape_dials"].append({"file": path.name, "property": path.stem,
                                   "folder": rel(lib, base / "Base Characters 9")})
    cat["proportion_dials"] = [
        {"file": path.name, "property": path.stem,
         "folder": rel(lib, base / "Base Proportion"),
         "name": path.stem.replace("body_bs_Proportion", "")}
        for path in sorted((base / "Base Proportion").glob("body_bs_Proportion*.dsf"))
        if not path.stem.endswith(("BO", "_scl"))]
    return cat


def pick(rng: random.Random, items: list, chance: float = 1.0):
    if not items or rng.random() > chance:
        return None
    return rng.choice(items)


def base_order(rng: random.Random, characters: list, count: int) -> list:
    """Which character preset each roll starts from.

    Drawn rather than chosen at random one at a time, so twelve characters use
    all six presets twice rather than landing on Ty four times.
    """
    order = []
    while len(order) < count:
        batch = list(characters)
        rng.shuffle(batch)
        order += batch
    return order[:count]


def roll(rng: random.Random, cat: dict, index: int, base: dict, poses: str = "none",
         any_brow: bool = False, dials: str = "none", outfit_kind: str | None = None) -> dict:
    """One character: what it is made of, before anything is built."""
    build = base["build"]
    recipe = {"index": index, "figure": base["file"], "base_character": base["name"],
              "build": build, "morph_sets": ["body", "jcms"], "dials": {},
              "custom_morphs": None, "wear": [], "mat_presets": [], "mat_replaces": [],
              "pose": None, "prop": None, "hair": None, "beard": None, "outfit": [],
              "skin": "the character's own", "hair_colour": None,
              "outfit_kind": outfit_kind}

    # Either another character's shape mixed in, or a handful of proportion
    # dials: one folder of custom morphs per build, so one or the other.
    #
    # Off by default, and measured: a dial reshapes the body and nothing else
    # follows it. On 2026-09-21 a figure with three proportion dials set had
    # 68.7% of its trouser vertices inside its own legs, against 9.6% for the
    # same outfit with no dials, and its eyes sat 14 mm inside its head.
    others = [d for d in cat["shape_dials"] if not d["property"].startswith(base["name"])]
    packs = ([("shape", others)] if others else []) + \
            ([("proportions", cat["proportion_dials"])] if cat["proportion_dials"] else [])
    if dials == "none":
        packs = []
        recipe["dial_pack"] = "none"
    if packs:
        kind, pack = packs[rng.randrange(len(packs))]
        recipe["dial_pack"] = kind
        if kind == "shape":
            mix = rng.choice(pack)
            recipe["custom_morphs"] = {"folder": mix["folder"], "files": [mix["file"]],
                                       "category": "Characters", "bodypart": "Body"}
            recipe["dials"][mix["property"]] = round(rng.uniform(0.2, 0.65), 2)
        else:
            chosen = rng.sample(pack, k=min(len(pack), rng.randint(2, 3)))
            recipe["custom_morphs"] = {"folder": chosen[0]["folder"],
                                       "files": [d["file"] for d in chosen],
                                       "category": "Shapes", "bodypart": "Body"}
            for dial in chosen:
                # Positive only. Most of these dials run -2 to 2, but the
                # pair Daz splits in two, Larger and Smaller, starts at 0:
                # body_bs_ProportionSmaller at -0.13 moved 0 vertices on
                # 2026-09-21, while ChestWidth at 0.5 moved 11,822.
                span = (0.15, 0.35) if dials == "small" else (0.15, 0.8)
                recipe["dials"][dial["property"]] = round(rng.uniform(*span), 2)

    brows = base.get("eyebrows") or []
    natural = [b for b in brows if b["colour"] not in FANCY_COLOURS]
    brow = pick(rng, brows if any_brow or not natural else natural)
    if brow:
        recipe["mat_presets"].append(brow["file"])
        recipe["eyebrow_colour"] = brow["colour"]

    # One of the base skins for this build, or the one the character came with.
    # A character whose base is unknown keeps its own: nothing says which of
    # the base skins would fit it.
    skins = cat["skins"].get(build) or []
    skin = pick(rng, skins, 0.75)
    if skin:
        recipe["skin"] = skin["name"]
        recipe["mat_replaces"].append(skin["file"])

    # The hair and the beard take the same colour, because a person's do.
    colour = None
    def mine(items):
        """What this character may wear: anything free, plus its own."""
        return [i for i in items if i.get("owner") in (None, base["name"])]

    hair = pick(rng, mine(cat["hair"]), 0.85)
    if hair:
        recipe["hair"] = hair["name"]
        recipe["wear"].append(hair["file"])
        colour = pick(rng, hair.get("colours") or [])
        if colour:
            recipe["hair_colour"] = colour["colour"]
            recipe["mat_presets"].append(colour["file"])
    if build == "masculine":
        beard = pick(rng, mine(cat["beards"]), 0.6)
        if beard:
            recipe["beard"] = beard["name"]
            recipe["wear"].append(beard["file"])
            same = [c for c in (beard.get("colours") or [])
                    if colour and c["colour"] == colour["colour"]]
            if same:
                recipe["mat_presets"].append(same[0]["file"])

    free = {g: mine(items) for g, items in cat["outfits"].items()}
    free = {g: items for g, items in free.items() if items}
    group = recipe.get("outfit_kind") or rng.choice(sorted(free) or sorted(cat["outfits"]))
    pieces = free.get(group) or cat["outfits"].get(group) or []
    whole = [o for o in pieces if WHOLE_OUTFIT.search(o["name"])]
    if group == "Base Clothing":
        # The only product that is separate garments rather than a set, and the
        # only one with pieces that suit one build and not the other.
        wanted = ("Shirt", "Shorts") if build == "masculine" or rng.random() < 0.5 \
            else ("Bra", "Shorts")
        chosen = [o for o in pieces if o["name"].split()[-1] in wanted]
    elif whole:
        # A set that ships a preset holding all of it: wear that, not a guess
        # at which pieces go together.
        chosen = [rng.choice(whole)]
    else:
        rest = [o for o in pieces if o not in whole]
        chosen = rng.sample(rest, k=min(len(rest), rng.randint(3, 5))) if rest else []
    for piece in chosen:
        recipe["outfit"].append(piece["name"])
        recipe["wear"].append(piece["file"])

    # A weapon comes in a grip for each base and each hand; take the one that
    # matches this figure, in its right hand.
    fits = [p for p in cat["props"] if p["hand"] == "RT"
            and p["build"] in (build, "base")]
    weapons = {p["weapon"] for p in fits}
    prop = None
    if weapons and rng.random() < 0.45:
        weapon = rng.choice(sorted(weapons))
        exact = [p for p in fits if p["weapon"] == weapon and p["build"] == build]
        prop = (exact or [p for p in fits if p["weapon"] == weapon])[0]
    if prop:
        recipe["prop"] = prop["name"]
        recipe["wear"].append(prop["file"])

    # No pose by default: Genesis 9's rest pose is the A pose a character sheet
    # wants, and a stretching or running pose hides as much as it shows.
    choices = [p for p in cat["poses"][build] if poses == "any" or p["upright"]]
    pose = pick(rng, choices) if poses != "none" else None
    if pose:
        recipe["pose"] = pose["file"]
        recipe["pose_name"] = pose["name"]
    else:
        recipe["pose_name"] = "rest (A pose)"
    return recipe


def slug_of(recipe: dict) -> str:
    bits = [f"{recipe['index']:02d}", recipe["base_character"].lower()]
    if recipe["outfit"]:
        # The outfit's product, in a word: its first, once a maker's prefix is
        # off the front. "dForce Leather Viking Armor" is leather, "Wise Wizard
        # Remaster 2025" is wise.
        words = [w for w in (recipe.get("outfit_kind") or "").split()
                 if w.lower() not in ("dforce", "g9", "the")]
        bits.append(words[0].lower() if words else "kit")
    return "-".join(re.sub(r"[^a-z0-9]+", "", b) or "x" for b in bits)


def build_command(recipe: dict, blend: Path, lib: Path, timeout: int,
                  declip: float = 0.0) -> list[str]:
    cmd = [sys.executable, str(PROBE), "scene", "--out", str(blend),
           "--library", str(lib), "--figure", recipe["figure"],
           "--morphs", ",".join(recipe["morph_sets"]), "--subdivision", "off",
           "--timeout", str(timeout)]
    if declip > 0 and not recipe["pose"]:
        cmd += ["--declip", str(declip)]
    if recipe.get("hide_figure"):
        cmd += ["--hide-figure"]
    if recipe.get("hide"):
        cmd += ["--hide", ",".join(recipe["hide"])]
    if recipe.get("hide_materials"):
        cmd += ["--hide-material", ",".join(recipe["hide_materials"])]
    custom = recipe["custom_morphs"]
    if custom:
        cmd += ["--custom-morphs", custom["folder"], "--custom-files", ",".join(custom["files"]),
                "--custom-category", custom["category"], "--custom-bodypart", custom["bodypart"]]
    for name, value in recipe["dials"].items():
        cmd += ["--set", f"{name}={value}"]
    for preset in recipe["mat_presets"]:
        cmd += ["--mat-preset", preset]
    for preset in recipe["mat_replaces"]:
        cmd += ["--mat-replace", preset]
    for wear in recipe["wear"]:
        cmd += ["--wear", wear]
    if recipe["pose"]:
        cmd += ["--pose", recipe["pose"]]
    return cmd


def render_command(blend: Path, sheet: Path, args) -> list[str]:
    cmd = [sys.executable, str(SHEET), str(blend), "--azimuths", args.azimuths,
           "--elevation", str(args.elevation), "--size", str(args.size),
           "--span", str(args.span), "--key", str(args.key),
           "--ambient", str(args.ambient), "--out", str(sheet)]
    if args.samples:
        cmd += ["--samples", str(args.samples)]
    return cmd


def run(cmd: list[str], log: Path) -> tuple[int, float, str]:
    start = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log.write_text(f"$ {' '.join(cmd)}\n\n{proc.stdout}\n{proc.stderr}")
    return proc.returncode, round(time.time() - start, 2), proc.stdout


def cut_cells(sheet: Path, size: int, names: list[str]) -> list[dict]:
    """The sheet's cells as their own images, one per facing."""
    from PIL import Image
    import numpy as np
    out = []
    with Image.open(sheet) as img:
        image = img.convert("RGBA")
    for i, name in enumerate(names):
        cell = image.crop((i * size, 0, (i + 1) * size, size))
        path = sheet.with_name(f"{sheet.stem.replace('_sheet', '')}_{name}.png")
        cell.save(path)
        alpha = np.asarray(cell).astype("float32")[..., 3] / 255.0
        out.append({"facing": name, "file": path.name,
                    "drawn_px": int((alpha > 0.5).sum()),
                    "bytes": path.stat().st_size})
    return out


def label_font(size: int):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                 # Pillow before 10.1 has one fixed size
        return ImageFont.load_default()


def roster_sheet(rows: list[dict], out: Path, cell: int, per_row: int) -> dict | None:
    """Every character on one page: its views side by side, under its name.

    On a mid grey, because a sheet of cut-out figures on nothing is hard to read
    and half of what wants looking at is the silhouette's edge. Mid rather than
    dark, so black leather and pale skin both show against it.
    """
    from PIL import Image, ImageDraw
    drawn = [r for r in rows if r.get("views")]
    if not drawn:
        return None
    views = max(len(r["views"]) for r in drawn)
    per_row = max(1, min(per_row, len(drawn)))
    lines = (len(drawn) + per_row - 1) // per_row
    label = max(14, cell // 24)
    pad = label // 2
    width = per_row * views * cell
    height = lines * (cell + label + pad)
    page = Image.new("RGBA", (width, height), (118, 120, 124, 255))
    draw = ImageDraw.Draw(page)
    font = label_font(label)
    for i, row in enumerate(drawn):
        x0 = (i % per_row) * views * cell
        y0 = (i // per_row) * (cell + label + pad)
        for j, view in enumerate(row["views"]):
            path = out.parent / row["slug"] / view["file"]
            with Image.open(path) as img:
                page.alpha_composite(img.convert("RGBA").resize((cell, cell), Image.LANCZOS),
                                     (x0 + j * cell, y0))
        recipe = row["recipe"]
        bits = [recipe["base_character"], recipe.get("skin") or "own skin"]
        if recipe.get("hair_colour"):
            bits.append(f"{recipe['hair_colour'].lower()} hair"
                        + (" and beard" if recipe.get("beard") else ""))
        elif recipe.get("beard"):
            bits.append("beard")
        if recipe["outfit"]:
            bits.append("+".join(o.replace("G9 Base ", "").replace("LVA ", "")
                                 for o in recipe["outfit"]))
        if recipe.get("prop"):
            bits.append(recipe["prop"].replace("Tubal ", "").replace(" RT", ""))
        if recipe.get("hide_figure"):
            bits.append("figure hidden")
        draw.rectangle((x0, y0 + cell, x0 + views * cell, y0 + cell + label + pad),
                       fill=(58, 60, 64, 255))
        draw.text((x0 + pad, y0 + cell + pad // 2), f"{row['slug']}  {', '.join(bits)}",
                  fill=(232, 232, 236, 255), font=font)
    page.save(out)
    return {"file": out.name, "characters": len(drawn), "views_each": views,
            "cell_px": cell, "size": list(page.size), "bytes": out.stat().st_size}


def cmd_keep(args) -> int:
    """Write the recipes of the characters worth keeping to one file.

    A roll is only as good as its luck, and most of a roster is thrown away.
    The ones that are kept go into a roster file, which `make --from` builds
    again exactly: the same figure, skin, hair colour, outfit and weapon, with
    no seed to remember. Edit the file to change one of them.
    """
    wanted = [w.strip() for w in args.slugs.split(",") if w.strip()]
    folders = sorted(d for d in args.dir.iterdir() if d.is_dir())
    chosen, missing = [], []
    for want in wanted:
        prefixes = [f"{want}-"]
        if want.isdigit():
            prefixes.append(f"{int(want):02d}-")
        hit = next((d for d in folders
                    if d.name == want or any(d.name.startswith(p) for p in prefixes)), None)
        if hit is None or not (hit / f"{hit.name}.json").is_file():
            missing.append(want)
            continue
        chosen.append(json.loads((hit / f"{hit.name}.json").read_text())["recipe"])
    if missing:
        print(f"  ! no character in {args.dir} for: {', '.join(missing)}")
        return 1
    roster = {"date": time.strftime("%Y-%m-%d"), "from": str(args.dir),
              "characters": chosen}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(roster, indent=1) + "\n")
    for recipe in chosen:
        print(f"  kept      {slug_of(recipe):18s} {recipe['base_character']:8s} "
              f"{recipe['skin']}, {recipe['hair_colour'] or 'no'} hair")
    print(f"  roster    {args.out}  ({len(chosen)} character(s))")
    print("  rebuild   scripts/daz_characters.py make --from "
          f"{args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}")
    return 0


def read_roster(path: Path) -> list[dict]:
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"  ! cannot read the roster {path}: {exc}")
    recipes = doc.get("characters") if isinstance(doc, dict) else doc
    if not isinstance(recipes, list) or not recipes:
        raise SystemExit(f"  ! {path} holds no characters")
    for i, recipe in enumerate(recipes, 1):
        recipe.setdefault("index", i)
        for key, default in (("morph_sets", ["body", "jcms"]), ("dials", {}),
                             ("custom_morphs", None), ("wear", []), ("mat_presets", []),
                             ("mat_replaces", []), ("pose", None), ("prop", None),
                             ("hair", None), ("beard", None), ("outfit", []),
                             ("hide", []), ("hide_figure", False), ("hide_materials", []),
                             ("skin", "the character's own"), ("hair_colour", None)):
            recipe.setdefault(key, default)
    return recipes


def cmd_list(args) -> int:
    cat = catalogue(args.library.resolve(), args.generation)
    print(f"  library   {cat['library']}")
    print(f"  figures   {cat['generation']}")
    print(f"  characters {len(cat['characters'])}: "
          + ", ".join(f"{c['name']} ({c['build'][0]})" for c in cat["characters"]))
    print(f"  eyebrows  {len(cat['eyebrows'])} colours: " + ", ".join(cat["eyebrows"]))
    print(f"  dials     {len(cat['shape_dials'])} character shapes, "
          f"{len(cat['proportion_dials'])} proportions: "
          + ", ".join(d["name"] for d in cat["proportion_dials"]))
    print(f"  hair      {len(cat['hair'])}: " + ", ".join(h["name"] for h in cat["hair"]))
    print(f"  beards    {len(cat['beards'])}: " + ", ".join(b["name"] for b in cat["beards"]))
    for group, items in cat["outfits"].items():
        print(f"  outfit    {group}: " + ", ".join(i["name"] for i in items))
    weapons = sorted({p["weapon"] for p in cat["props"]})
    print(f"  props     {len(cat['props'])} grips of {len(weapons)}: " + ", ".join(weapons))
    for skipped in cat["skipped"]:
        print(f"  left out  {skipped['name']}: {skipped['why']}")
    for build, poses in cat["poses"].items():
        print(f"  poses     {build}: {sum(1 for p in poses if p['upright'])} upright "
              f"of {len(poses)}")
    return 0


def cmd_make(args) -> int:
    lib = args.library.resolve()
    if not lib.is_dir():
        print(f"  ! no library at {lib}")
        return 2
    if args.recipes_from:
        recipes = read_roster(args.recipes_from)
    else:
        cat = catalogue(lib, args.generation)
        if not cat["characters"]:
            print(f"  ! {lib} holds no Genesis character preset to start from")
            return 1
        rng = random.Random(args.seed)
        bases = base_order(rng, cat["characters"], args.count)
        kinds = base_order(rng, sorted(cat["outfits"]) or ["Base Clothing"], args.count)
        recipes = [roll(rng, cat, i + 1, bases[i], args.poses, args.any_brow_colour,
                        args.dials, kinds[i])
                   for i in range(args.count)]
    print(f"  library   {lib}")
    print(f"  roster    {args.recipes_from}, {len(recipes)} character(s)"
          if args.recipes_from else f"  seed      {args.seed}, {args.count} character(s)")
    print(f"  render    {args.size} px cells at azimuths {args.azimuths}, elevation "
          f"{args.elevation}, span {args.span}, key {args.key}, ambient {args.ambient}"
          + (f", {args.samples} samples" if args.samples else ""))
    print(f"  poses     {args.poses}"
          + (" (the rest pose Genesis 9 ships with)" if args.poses == "none" else ""))
    for recipe in recipes:
        print(f"  {slug_of(recipe):16s} {recipe['base_character']:7s} "
              f"skin {recipe['skin']:18s} hair {recipe['hair_colour'] or '-':6s} "
              f"beard {'y' if recipe['beard'] else '-'}; "
              f"{', '.join(recipe['outfit']) or 'no outfit'}; "
              f"prop {recipe['prop'] or '-'}")
    if args.dry_run:
        print("  dry run: nothing was built")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    rows, failed = [], 0
    for recipe in recipes:
        slug = slug_of(recipe)
        folder = OUT / slug
        folder.mkdir(parents=True, exist_ok=True)
        blend = folder / f"{slug}.blend"
        row = {"slug": slug, "seed": args.seed, "recipe": recipe, "views": [],
               "licence": "Daz Standard License: a render may ship on the conditions in "
                          "docs/reference/daz-genesis.md; the 3D data needs an Interactive "
                          "License for each product used"}
        cmd = build_command(recipe, blend, lib, args.timeout, args.declip)
        row["build_command"] = " ".join(cmd[1:])
        code, seconds, _ = run(cmd, folder / f"{slug}_build.log")
        row["build"] = {"exit": code, "seconds": seconds,
                        "blend_bytes": blend.stat().st_size if blend.exists() else 0}
        report = OUT.parent / f"{slug}_scene.json"
        if report.exists():
            blender = json.loads(report.read_text()).get("blender", {})
            fit = (blender.get("fit") or {}).get("meshes", {})
            worn = set(blender.get("worn_meshes") or [])
            row["fit"] = {"body": (blender.get("fit") or {}).get("body"),
                          "worn": sorted(worn),
                          "inside_pct": {name: m["inside_pct"] for name, m in fit.items()},
                          "max_depth_mm": {name: m["max_depth_mm"] for name, m in fit.items()}}
            row["declip"] = blender.get("declip")
        fit = row.get("fit", {})
        worn_fit = {k: v for k, v in fit.get("inside_pct", {}).items()
                    if k in set(fit.get("worn", []))}
        worst = max(worn_fit.items(), key=lambda kv: kv[1], default=("nothing worn", 0.0))
        print(f"  {slug:16s} built in {seconds}s (exit {code}); worst worn fit: "
              f"{worst[0][:26]} {worst[1]}% inside", flush=True)
        if not blend.exists():
            row["error"] = "the scene build wrote no .blend; see the build log"
            rows.append(row)
            failed += 1
            (folder / f"{slug}.json").write_text(json.dumps(row, indent=1) + "\n")
            continue

        sheet = folder / f"{slug}_sheet.png"
        cmd = render_command(blend, sheet, args)
        row["render_command"] = " ".join(cmd[1:])
        code, seconds, out = run(cmd, folder / f"{slug}_render.log")
        engine = next((l.strip() for l in out.splitlines() if l.strip().startswith("engine")), "")
        row["render"] = {"exit": code, "seconds": seconds, "size": args.size,
                         "azimuths": [float(a) for a in args.azimuths.split(",")],
                         "elevation": args.elevation, "span": args.span,
                         "key": args.key, "ambient": args.ambient,
                         "samples": args.samples, "engine": engine[7:].strip() or None}
        if sheet.exists():
            row["views"] = cut_cells(sheet, args.size, args.facings)
            sheet.unlink()
        else:
            row["error"] = "no sheet was drawn; see the render log"
            failed += 1
        print(f"  {slug:16s} drew {len(row['views'])} view(s) in {seconds}s (exit {code})",
              flush=True)

        if not args.keep_blend:
            blend.unlink(missing_ok=True)
            row["build"]["blend_kept"] = False
        else:
            row["build"]["blend_kept"] = True
        # The probe writes its reports to output/daz/ under the .blend's stem,
        # whatever folder the .blend went to. Keep the scene report beside the
        # character it describes, and drop the rest.
        for leftover in sorted((OUT.parent).glob(f"{slug}_*")):
            if leftover.name == f"{slug}_scene.json":
                shutil.move(str(leftover), folder / leftover.name)
            else:
                leftover.unlink()
        (folder / f"{slug}.json").write_text(json.dumps(row, indent=1) + "\n")
        rows.append(row)

    pruned = []
    if args.prune:
        kept = {row["slug"] for row in rows}
        for folder in sorted(d for d in OUT.iterdir() if d.is_dir()):
            if folder.name not in kept:
                shutil.rmtree(folder)
                pruned.append(folder.name)

    page = roster_sheet(rows, OUT / "roster_sheet.png", args.sheet_cell, args.sheet_columns)
    index = {"date": time.strftime("%Y-%m-%d"),
             "seed": None if args.recipes_from else args.seed,
             "roster": str(args.recipes_from) if args.recipes_from else None,
             "library": str(lib),
             "count": len(rows), "failed": failed, "roster_sheet": page,
             "pruned": pruned, "poses": args.poses,
             "characters": [{"slug": r["slug"], "base": r["recipe"]["base_character"],
                             "files": [v["file"] for v in r["views"]],
                             "error": r.get("error")} for r in rows]}
    (OUT / "characters.json").write_text(json.dumps(index, indent=1) + "\n")
    if pruned:
        print(f"  pruned    {len(pruned)} folder(s) this run did not write: "
              + ", ".join(pruned[:6]) + (" ..." if len(pruned) > 6 else ""))
    print(f"  index     {(OUT / 'characters.json').relative_to(ROOT)}")
    if page:
        print(f"  sheet     {(OUT / page['file']).relative_to(ROOT)}  "
              f"({page['characters']} characters, {page['views_each']} views each, "
              f"{page['size'][0]}x{page['size'][1]} px)")
    print(f"  done      {len(rows) - failed} of {len(rows)} character(s); "
          f"{sum(len(r['views']) for r in rows)} image(s) under {OUT.relative_to(ROOT)}")
    print("  licence   renders may ship on conditions; the .blend and the figure may not. "
          "Keep all of it out of the AI stages (docs/reference/daz-genesis.md)")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keep", help="write the recipes of named characters to a roster file")
    k.add_argument("slugs", help="which to keep, comma separated, by slug or by number: 1,3,4,12")
    k.add_argument("--dir", type=Path, default=OUT,
                   help=f"the run to take them from (default {OUT.relative_to(ROOT)})")
    k.add_argument("--out", type=Path, default=OUT / "roster.json",
                   help=f"where to write the roster (default {(OUT / 'roster.json').relative_to(ROOT)})")

    for name, help_text in (("list", "what the library offers for each slot"),
                            ("make", "roll characters, build them and render them")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--library", type=Path, default=DEFAULT_LIBRARY,
                       help=f"the Daz content library (default {DEFAULT_LIBRARY})")
        p.add_argument("--generation", default=None,
                       help="the folder under People/ to draw every slot from, such as "
                            "\"Genesis 9\" (default: the one the character presets are in). "
                            "A Genesis 8 hair does not fit a Genesis 9 figure")
        if name == "list":
            continue
        p.add_argument("--from", dest="recipes_from", type=Path, default=None, metavar="FILE",
                       help="build the characters in this roster file instead of rolling "
                            "new ones, as `keep` writes it. The roll options are then "
                            "unused, and the file is what to edit to change a character")
        p.add_argument("--count", type=int, default=12, help="how many characters (default 12)")
        p.add_argument("--seed", type=int, default=int(time.strftime("%Y%m%d")),
                       help="the roll's seed; the same seed and library give the same "
                            "characters (default today's date)")
        p.add_argument("--size", type=int, default=768, help="pixels per view (default 768)")
        p.add_argument("--azimuths", default="0,90",
                       help="the facings to draw, in degrees (default 0,90: front and side)")
        p.add_argument("--facings", default="front,side",
                       help="what to call each facing in the file names (default front,side)")
        p.add_argument("--elevation", type=float, default=0.0,
                       help="camera elevation; 0 is eye level, square on (default 0)")
        p.add_argument("--span", type=float, default=None,
                       help="frame every character against this height in metres, so a "
                            "short character reads as short. The default follows --poses: "
                            "2.0 for the rest pose, where a Genesis 9 figure is about "
                            "1.76 m and fills three quarters of the cell, and 2.4 when a "
                            "pose is rolled, because at 2.0 a stretching figure was cut "
                            "off at the top on 2026-09-21")
        p.add_argument("--samples", type=int, default=None,
                       help="render samples per cell (default: render_sheet.py's own)")
        p.add_argument("--key", type=float, default=6.5,
                       help="sun strength. The default is 6.5, not render_sheet.py's 1.6, "
                            "because Daz skin is dark under a sprite sheet's light: "
                            "measured on 2026-09-21 on a dressed figure, the lit pixels "
                            "averaged 0.248 of 1 at 1.6 and 0.425 at 6.5, with 0.06 per "
                            "cent of them clipped (default 6.5)")
        p.add_argument("--ambient", type=float, default=1.3,
                       help="world light strength, raised with the sun for the same "
                            "reason (default 1.3)")
        p.add_argument("--poses", choices=("none", "upright", "any"), default="none",
                       help="none leaves every figure in the rest pose Genesis 9 ships "
                            "with, which is the A pose a character sheet wants (default); "
                            "upright rolls a standing, walking, flexing, running or "
                            "stretching pose; any rolls from every pose the library has")
        p.add_argument("--dials", choices=("none", "small", "any"), default="none",
                       help="none leaves every figure the shape its character preset "
                            "gives it (default), because a dial reshapes the body and "
                            "nothing it wears follows: with three proportion dials set, "
                            "68.7 per cent of a figure's trouser vertices sat inside its "
                            "own legs on 2026-09-21, against 9.6 per cent with none. "
                            "small keeps a rolled dial under 0.35, any is the full range")
        p.add_argument("--declip", type=float, default=1.5, metavar="MM",
                       help="push each worn garment this far clear of the body, which is "
                            "what stops a hip coming through a pair of shorts authored "
                            "for another figure: on a measured figure the shorts went "
                            "from 73.3 per cent of their vertices inside the body to 0. "
                            "Skipped when a pose is rolled, because it edits the rest "
                            "shape (default 1.5)")
        p.add_argument("--any-brow-colour", action="store_true",
                       help="let a roll pick the blue, fuchsia and neon eyebrows the "
                            "library ships; by default only the six that grow on people")
        p.add_argument("--sheet-cell", type=int, default=512,
                       help="pixels per cell on the one sheet that holds every character "
                            "(default 512; the per-character images keep --size)")
        p.add_argument("--sheet-columns", type=int, default=4,
                       help="characters per row on that sheet (default 4)")
        p.add_argument("--timeout", type=int, default=3600,
                       help="seconds for each Blender build (default 3600)")
        p.add_argument("--keep-blend", action="store_true",
                       help="keep each .blend, about 150 MB each, instead of deleting it "
                            "once its views are drawn")
        p.add_argument("--prune", action="store_true",
                       help="delete the character folders this run did not write, so what "
                            "is left under output/daz/characters/ is this roster and "
                            "nothing else")
        p.add_argument("--dry-run", action="store_true",
                       help="print the roll and build nothing")
    args = ap.parse_args()
    if args.cmd == "keep":
        return cmd_keep(args)
    if args.cmd == "list":
        return cmd_list(args)
    if args.span is None:
        args.span = 2.0 if args.poses == "none" else 2.4
    args.facings = [f.strip() for f in args.facings.split(",") if f.strip()]
    if len(args.facings) != len(args.azimuths.split(",")):
        ap.error("--facings must name as many facings as --azimuths has angles")
    return cmd_make(args)


if __name__ == "__main__":
    sys.exit(main())
