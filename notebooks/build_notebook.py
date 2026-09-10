#!/usr/bin/env python3
"""Generate notebooks/asset_pipeline.ipynb.

The notebook is generated rather than hand-edited, because a notebook that has
been run carries its outputs, its execution counts and whatever state the last
session left in it.  Regenerating gives a clean one every time:

    notebooks/build_notebook.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "asset_pipeline.ipynb"


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip().splitlines(True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": text.strip().splitlines(True)}


cells = [
    md("""
# Asset Engine: click through the whole pipeline

Run the cells in order. Each one does one stage and shows you the result.

You need the engine running. The first cell checks, and tells you what to do if
it is not.

Nothing here is destructive. Everything lands in `output/`, which is not tracked
by git.
"""),

    md("## 0. Setup\n\nRun this once. It points the notebook at the repo root."),
    code("""
import subprocess, sys, os
from pathlib import Path
from IPython.display import Image, Markdown, display

ROOT = Path.cwd()
while not (ROOT / "scripts" / "doctor.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
os.chdir(ROOT)
print("working in", ROOT)

def run(*args, quiet=False):
    "Run a repo script and show its output."
    cmd = [sys.executable, *[str(a) for a in args]]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip()
    if not quiet:
        print(out)
    if p.returncode != 0:
        print(f"\\n[exit {p.returncode}]")
    return out

def newest(pattern):
    "The most recently written file matching a glob, or None."
    hits = sorted(Path(".").glob(pattern), key=lambda p: p.stat().st_mtime)
    return hits[-1] if hits else None

def show(path, width=520):
    "Display an image, or say why there is nothing to show."
    if path and Path(path).exists():
        display(Image(filename=str(path), width=width))
    else:
        print("nothing to show yet")
"""),

    md("""
## 1. Is the engine ready?

This checks Docker, the GPU runtime, your `.env`, the image, the container, the
server, the node packs, Blender and the weights.

If it is not ready it prints one next step. Do that, then run this cell again.
"""),
    code('run("scripts/doctor.py", "--skip-models")'),

    md("""
## 2. Draw a concept image

Change the subject and run. About two minutes.

This uses the 20 step workflow rather than the fast one, because the fast one
runs at a guidance scale where negative prompts do nothing at all.
"""),
    code('''
SUBJECT = "a mossy stone golem, thick moss on the shoulders, cracked granite skin"

run("scripts/run_workflow.py", "workflows/api/preset_concept_creature.json",
    "--prompt", SUBJECT,
    "--set", "Save.filename_prefix=nb/concept")

concept = newest("output/nb/concept*.png")
print(concept)
show(concept)
'''),

    md("""
### Look at it before going on

This is the cheapest stage and it decides everything downstream. A cropped
figure becomes a cropped mesh. Two figures become one fused blob.

Not right? Change `SUBJECT` and run the cell again, or add
`"--set", "seed=12345"` to reroll the same prompt.
"""),

    md("""
## 3. Build the 3D shape

TripoSG is fast and clean. Hunyuan3D makes better meshes but cannot ship to the
EU, UK or South Korea, and TripoSG's licence status inside this node pack is
unresolved, so check the licensing guide before shipping either.

About a minute.
"""),
    code('''
run("scripts/run_workflow.py", "workflows/api/img2mesh_hunyuan3d21.json",
    "--image", str(concept),
    "--set", "save_path=mesh/nb_asset.glb")

mesh = Path("output/mesh/nb_asset.glb")
print(mesh, mesh.exists())
'''),

    md("## 4. Look at the mesh from four sides\n\nA mesh cannot be displayed, so render it. Most bad meshes are obvious here and nowhere else."),
    code('''
run("scripts/render_sheet.py", str(mesh),
    "--angles", "4", "--size", "320",
    "--out", "output/nb/turnaround.png")

show("output/nb/turnaround.png", width=760)
'''),

    md("""
Grey means the mesh has no texture yet. That is expected, not a fault.

What to look for: a back that is a smear, limbs fused to the body, and thin parts
that came out broken. None of those can be fixed later. Go back to step 2.
"""),

    md("""
## 5. How many faces does it need?

This measures what each face budget actually costs, three different ways, at the
size the sprite will be seen.

Read the silhouette column. For a 2D game, a sprite is its outline.
"""),
    code('run("scripts/decimation_report.py", str(mesh), "--sprite", "128")'),

    md("""
## 6. Texture it

The concept image goes in again here, because the texture stage paints the model
to match the drawing.

Two to four minutes.
"""),
    code('''
run("scripts/run_workflow.py", "workflows/api/mesh_texture_hunyuan3d21.json",
    "--image", str(concept),
    "--set", "mesh_path=/app/output/mesh/nb_asset.glb",
    "--set", "TexGen Pipeline.max_num_view=6",
    "--set", "TexGen Pipeline.resolution=512")

textured = newest("output/mesh/textured_*.glb") or mesh
print(textured)

run("scripts/render_sheet.py", str(textured),
    "--angles", "4", "--size", "320",
    "--out", "output/nb/textured.png")
show("output/nb/textured.png", width=760)
'''),

    md("""
::: note
The texture stage always writes its maps to the same fixed paths. Generate a
second asset and this one's maps are gone. Copy them out now if you want them.
:::
"""),

    md("""
## 7. Rig it

The rigger fits a skeleton and binds the mesh to it. No weight painting.

Note what comes back: the rigger decimates anything above 48,000 faces and hands
back the decimated mesh, not yours. Under that, your mesh passes through
untouched.

Three to six minutes.
"""),
    code('''
import shutil
Path("input/3d").mkdir(parents=True, exist_ok=True)
shutil.copy(textured, "input/3d/nb_asset.glb")

out = subprocess.run(["bash", "scripts/rig_units.sh", "nb_asset"],
                     capture_output=True, text=True)
print((out.stdout + out.stderr).strip())

rig = Path("output/rigged/nb_asset.fbx")
print(rig, rig.exists())
'''),

    md("### What did the rigger actually produce?\n\nCheck rather than assume. This reads the file itself."),
    code('''
probe = subprocess.run([
    "docker", "exec", "comfyui", "python3", "-c",
    "import bpy; bpy.ops.wm.read_factory_settings(use_empty=True);"
    "bpy.ops.import_scene.fbx(filepath='/app/output/rigged/nb_asset.fbx');"
    "ms=[o for o in bpy.data.objects if o.type=='MESH'];"
    "ar=[o for o in bpy.data.objects if o.type=='ARMATURE'];"
    "print('RESULT faces', sum(len(m.data.polygons) for m in ms), 'bones', len(ar[0].data.bones))"
], capture_output=True, text=True)
print([l for l in probe.stdout.splitlines() if l.startswith("RESULT")] or probe.stderr[-400:])
'''),

    md("""
## 8. Render the animation frames

Angles across, animation frames down.

**The camera matters here.** The defaults are isometric: elevation 30, first
facing at 45 degrees. For a top down game use `--elevation 90 --azimuth-start 0`
instead. Render an isometric game at 0, 90, 180, 270 and every unit stands square
on while the ground runs diagonally underneath.
"""),
    code('''
run("scripts/render_sheet.py", str(rig),
    "--poses", "transforms:poses/walk.json",
    "--angles", "4", "--size", "220",
    "--out", "output/nb/walk.png")

show("output/nb/walk.png", width=760)
'''),

    md("""
If that came back as the same pose four times, look for a line saying
`! bones not in the rig`. Bone names differ per model. Dump this rig's own map:
"""),
    code('''
subprocess.run(["docker", "exec", "comfyui", "python3", "-c",
    "import bpy; bpy.ops.wm.read_factory_settings(use_empty=True);"
    "bpy.ops.import_scene.fbx(filepath='/app/output/rigged/nb_asset.fbx');"
    "a=[o for o in bpy.data.objects if o.type=='ARMATURE'][0];"
    "print('\\\\n'.join(f'{b.name} <- {b.parent.name if b.parent else \\"-\\"}' for b in a.data.bones))"
], capture_output=True, text=True).stdout[-1500:]
'''),

    md("""
## 9. Compare the two camera conventions

Renders the same model both ways so you can see the difference rather than take
it on trust. The left sheet is square on. The right is isometric.
"""),
    code('''
run("scripts/render_sheet.py", str(textured), "--angles", "4", "--size", "200",
    "--azimuth-start", "0", "--out", "output/nb/facing_square.png", quiet=True)
run("scripts/render_sheet.py", str(textured), "--angles", "4", "--size", "200",
    "--azimuth-start", "45", "--out", "output/nb/facing_iso.png", quiet=True)

display(Markdown("**Square on, azimuth 0, 90, 180, 270.** For side views and paper dolls."))
show("output/nb/facing_square.png", width=760)
display(Markdown("**Isometric, azimuth 45, 135, 225, 315.** For a 2 to 1 diamond grid."))
show("output/nb/facing_iso.png", width=760)
'''),

    md("""
## 10. Keep the good parts

Copies the keepers into `output/assets/<name>/` with predictable names, and
records where each came from. It copies rather than moves, so a later sweep
cannot destroy a curated asset.
"""),
    code('''
run("scripts/cleanup.py", "keep", "nb_asset",
    "--concept", str(concept),
    "--model", str(textured),
    "--rig", str(rig),
    "--sheets", "output/nb/walk.png")

run("scripts/cleanup.py")
'''),

    md("""
## Where to go next

- [Face counts and decimation](https://xander-rudolph.github.io/asset-engine/guide/decimation) for what a budget really costs
- [Facings and camera angles](https://xander-rudolph.github.io/asset-engine/guide/facings) if a sprite faces the wrong way
- [Rigging](https://xander-rudolph.github.io/asset-engine/guide/rigging) for heavy meshes and weight transfer
- [Ground and terrain](https://xander-rudolph.github.io/asset-engine/guide/terrain) for tileable textures
- [Licensing](https://xander-rudolph.github.io/asset-engine/guide/licensing) before you ship anything

To clear the notebook's working files:

```sh
rm -rf output/nb input/3d/nb_asset.glb
```
"""),
]

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT.write_text(json.dumps(nb, indent=1) + "\n")
print(f"wrote {OUT} ({len(cells)} cells)")
