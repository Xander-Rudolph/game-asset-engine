#!/usr/bin/env python3
r"""Probe the Diffeomorphic DAZ Importer (import_daz 5.2.0) in the container's headless bpy.

Imports a Genesis 9 figure from a Daz content library installed outside the
repo, loads its viseme and FACS controllers, saves a .blend under output/daz/
and renders one viseme per row, so you can see whether the importer runs with
no UI and whether the Genesis face reads at sprite sizes.

`scene` goes further on the same headless Blender, with no Daz Studio on the
host: it loads morph sets and character shape dials, lists every slider the
rig gains with its range, sets named ones and measures how far the mesh
moves, imports clothing and hair onto the figure already in the scene and
merges their rigs into its own, applies a pose preset, and saves the lot.
`verify` reopens what it saved in a Blender with no add-on at all.

    scripts/daz_import_probe.py fetch
        # import_daz at the version_5_2_0 tag, pinned, into input/_devtools/import_daz

    scripts/daz_import_probe.py build --facs --subdivision off --out output/daz/g9_cage.blend
        # output/daz/g9_cage.blend, _build.json, _blender.log, _poses.json

    scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend
        # render_sheet.py's whole-figure rows at 128 px, then the probe's three
        # framings at 128, 220 and 340 px: g9_cage_render_sheet_128.png,
        # g9_cage_sheet_<size>.png and _labelled.png, g9_cage_render.json;
        # about 25 min on llvmpipe (see MEASURED)

    # a short run: the neutral row and AA in both stages, one framing, one
    # size, 16 samples, into files named g9_cage_AA_128_face_s16_...
    scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend --only AA \
        --sizes 128 --columns face --samples 16

    # what each viseme moves, with no rendering: g9_cage_motion.json
    scripts/daz_import_probe.py render --blend output/daz/g9_cage.blend --motion-only

    # also call import_visemes, which adds nothing on Genesis 9 and so makes the
    # build exit 1, and save the importer's Subsurf levels
    scripts/daz_import_probe.py build --visemes --facs --out output/daz/g9_visemes.blend

    # render at the Subsurf levels saved in the file, which has to be asked for
    scripts/daz_import_probe.py render --blend output/daz/g9_visemes.blend --no-sheet \
        --subdivision as-saved --only AA --sizes 128 --columns face --samples 16

    # an eyebrow colour of your own, over the presets found beside the figure
    scripts/daz_import_probe.py build --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf" \
        --mat-preset "People/Genesis 9/Anatomy/Daz Originals/Base Anatomy/Eyebrows Card/Materials/G9 Eyebrows Color Red.duf" \
        --subdivision off --out output/daz/g9_kat_red.blend

    # a character preset with 26 texture references, saved with its images and without
    scripts/daz_import_probe.py build --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf" \
        --facs --out output/daz/g9_kat.blend
    scripts/daz_import_probe.py build --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf" \
        --facs --no-textures --out output/daz/g9_kat_notex.blend
    scripts/daz_import_probe.py render --blend output/daz/g9_kat.blend --no-sheet --materials \
        --sizes 340 --columns face --only AA --samples 16

    # the developer load, no Eyes, Mouth, Eyelashes or Tear figures
    scripts/daz_import_probe.py build --figure "People/Genesis 9/Developer Kit/Genesis 9 Dev Load.duf" \
        --anatomy none --out output/daz/g9_devload.blend

    # what a wrong content path does: the checks are recorded, not obeyed
    scripts/daz_import_probe.py build --content-dir /app/models/daz_library_missing --no-dir-check \
        --anatomy none --out output/daz/g9_wrongdir.blend

    # every standard morph set the add-on knows, the six character dials the
    # Starter Essentials ships, and two sliders set and measured
    scripts/daz_import_probe.py scene --out output/daz/g9_morphs.blend --anatomy none \
        --morphs units,expressions,visemes,head,body,jcms,flexions,masculine,feminine,powerpose,facsexpr \
        --custom-morphs "data/Daz 3D/Genesis 9/Base/Morphs/Daz 3D/Base Characters 9" \
        --custom-files Kat_figure_ctrl_Character.dsf,Amala_figure_ctrl_Character.dsf \
        --custom-category Characters --custom-bodypart Body \
        --set Kat_figure_ctrl_Character=1.0 --set body_bs_ProportionHeight=1.0 --subdivision off

    # a shirt, shorts and hair onto the figure already in the scene, then a
    # character dial and a pose, and the saved file reopened with no add-on
    scripts/daz_import_probe.py scene --out output/daz/g9_outfit.blend --anatomy none \
        --morphs body,jcms --custom-morphs "data/Daz 3D/Genesis 9/Base/Morphs/Daz 3D/Base Characters 9" \
        --custom-files Kat_figure_ctrl_Character.dsf --custom-category Characters --custom-bodypart Body \
        --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shirt.duf" \
        --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shorts.duf" \
        --wear "People/Genesis 9/Hair/Daz Originals/Base Hair/G9 Base dForce Pixie Hair.duf" \
        --skip-transfer "dForce Pixie Cut Mesh,dForce Pixie Hair Cap Mesh" \
        --set-dressed Kat_figure_ctrl_Character=1.0 \
        --pose "People/Genesis 9/Poses/Daz Originals/Base Poses/Base/G9 Base Pose 13 Walking G9B.duf" \
        --subdivision off

    # the file the measure track renders: a character preset, its anatomy
    # figures, body and corrective morphs, FACS, an outfit, hair and a pose
    scripts/daz_import_probe.py scene --out output/daz/g9_dressed.blend \
        --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf" --morphs body,jcms,flexions --facs \
        --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shirt.duf" \
        --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shorts.duf" \
        --wear "People/Genesis 9/Hair/Daz Originals/Base Hair/G9 Base dForce Pixie Hair.duf" \
        --skip-transfer "dForce Pixie Cut Mesh,dForce Pixie Hair Cap Mesh" \
        --pose "People/Genesis 9/Poses/Daz Originals/Base Poses/Base/G9 Base Pose 13 Walking G9B.duf"

    # what the DBZFILE fitting route asks for, which only Daz Studio can write
    scripts/daz_import_probe.py scene --out output/daz/g9_dbz.blend --anatomy none --fit DBZFILE \
        --wear "People/Genesis 9/Clothing/Daz Originals/Base Clothing/G9 Base Shirt.duf"

    # reopen any .blend this wrote in a Blender with no add-on
    scripts/daz_import_probe.py verify --blend output/daz/g9_dressed.blend

WHAT IS DOWNLOADED. `fetch` pins GitHub's archive of the version_5_2_0 tag by
byte size and sha256, writes it to input/_devtools/import_daz/downloads/ as a
.part file, and renames it into place only when both match; on a mismatch or
a broken download it deletes the .part file and exits 1. GitHub publishes no
checksum for tag archives, so the pins are the bytes downloaded on 2026-09-16,
the same from github.com and from codeload.github.com. The zip's comment
names the tagged commit, and `fetch` checks that too. The add-on is unpacked,
without its top folder, into input/_devtools/import_daz/ext/import_daz, and
unpacked again when a file the archive holds is missing there or has another
size.

LICENCE. The code is GPL-2.0-or-later (blender_manifest.toml in the archive),
copyright 2016-2026 Thomas Larsson (its __init__.py), both read 2026-09-16. It
is run, never copied into the repo: input/ is gitignored. Daz content keeps
the Daz EULA after import, so what this script writes from it (the .blend
files, logs, reports and renders) goes to the gitignored output/daz/, and none
of it may be committed. The one exception is render_sheet.py, which writes its
cells to output/_sheet_frames/<its pid>_<unix time>/ while it runs and deletes
them when it finishes; if it exits non-zero, runs past its time or is stopped,
this script ends its Blender job and deletes that folder. Keep all of it out
of the AI stages, as docs/reference/daz-genesis.md warns: never load the
Genesis mesh, its textures or its UV maps into Hunyuan3D 2.1, UniRig or any
other model, and do not feed a render from output/daz/ to Qwen-Image,
ControlNet, TRELLIS, Hunyuan3D or any training without a written answer from
Daz.

HOW IT RUNS WITHOUT A UI, the method scripts/mpfb_probe.py found for MPFB:
  1. BLENDER_USER_RESOURCES and HOME are set before `import bpy`, pointing
     under input/_devtools/import_daz/. Blender's user config and the
     importer's "~/DAZ Importer" settings and error file land there, not in
     the image or /app/.home.
  2. input/_devtools/import_daz/ext is added as a local extension repository
     with preferences.extensions.repos.new(module="import_daz_probe", ...),
     and the add-on is enabled as bl_ext.import_daz_probe.import_daz.
  3. contentDirs is set to the library as the container sees it, and mdlDirs
     and cloudDirs are emptied, through import_daz.set_global_setting. The
     build first checks that the directory and the figure exist, then that
     get_root_paths() returns exactly that directory and that
     get_absolute_paths() resolves the figure, because a wrong content path
     raises nothing. --figure and --anatomy take paths inside the library.
  4. set_silent_mode(True) before every operator, because easy_import_daz
     sets it back to False when it returns.
  5. bpy.ops.daz.easy_import_daz(directory=..., files=[{"name": ...}],
     materialMethod=..., fitMeshes=...) imports the figure. With no .dbz file
     from Daz Studio, fitMeshes must not be its default DBZFILE; the default
     here is MORPHED.
  6. Genesis 9.duf loads the Eyes, Mouth, Eyelashes, Tear and eyebrow figures
     through a Daz Studio post-load script, which the importer does not run.
     With --anatomy auto (the default) the build reads that script's
     AssetFile list from the .duf, plain or gzip-compressed as the importer
     reads it, imports each file the same way, parents each new rig to the
     body rig and merges them with bpy.ops.daz.merge_rigs.
  7. With the body rig active, bpy.ops.daz.import_visemes() and
     bpy.ops.daz.import_facs() load the controllers as rig properties whose
     drivers move shape keys and bones.
  8. The anatomy figures arrive with no maps: their .duf files carry a Cutout
     Opacity of 1 and no image library at all, and Daz Studio fills them in
     afterwards by running a MAT preset. So the build reads those presets
     itself and wires what it understands, filling in only what a material is
     missing: the cutout opacity map (or value), the colour map or flat
     colour, a layered colour image whose layers are laid plainly over one
     another, and a refraction weight of 0.5 or more, which becomes the
     Principled BSDF's Transmission Weight with the preset's refraction index
     as its IOR. Without the first an eyelash card renders as an opaque fan
     across the eyelid; without the last the film of moisture over each eye
     renders as an opaque white dome. --mat-preset names one and wins over the presets
     found beside the figure; --no-auto-materials turns the search off.
     bpy.ops.daz.import_daz_materials is not used: it keys a preset's channel
     values by the url-quoted material name and looks them up under the plain
     one, so every material whose name holds a space loses its maps (main.py
     splitUrl and run, read at the 5.2.0 tag). useMergeMaterials is also off,
     because bare anatomy materials are identical and were merged into one
     slot, leaving nowhere to put the maps.
  9. --mat-replace is the other half of that: it swaps the maps a material
     already has for another preset's, matched by what each file name says
     the map is for (D, SSS, R, SO, NM, SLW), which is what a skin swap
     needs. It runs after the fill, because the fill is what puts a skin's
     colour map into Base Color, and it leaves the graph alone. Handing the
     preset to bpy.ops.daz.import_daz_materials instead left a Genesis 9 body
     with three of its seven material slots (measured 2026-09-21).
 10. Every build measures how each mesh sits against the body's evaluated
     surface: how many of its vertices are inside it, how deep and the mean
     gap. Garments should be outside; an eyeball is inside a head whatever
     anyone does. --declip MM then pushes each worn mesh clear of the body by
     that much, measuring on the evaluated mesh and moving the rest shape,
     over up to four passes, which takes a pair of shorts authored for
     another figure from 73.3% of its vertices inside to 0. A mesh above
     --declip-max-verts is left alone, so a card hair keeps its shape, and a
     posed figure is refused because the rest shape is what is edited.
WHAT `scene` ADDS to that, in this order, each one a step that records its
seconds, peak RSS and get_error_message() and carries on when it fails:
  1. --morphs runs one standard morph operator per set (import_units,
     import_body_morphs, import_jcms and the rest). Called from Python the
     selector dialog never opens: Selector.getScriptedValues() returns
     LS.selection, which is empty, so every file the add-on's paths table
     lists for the figure is loaded (read in selector.py and morphing.py).
  2. --custom-morphs runs bpy.ops.daz.import_custom_morphs() on named .dsf
     files with onDrivers='RIG', which is how the character shape dials in
     "Base Characters 9" load: the add-on's data/paths/genesis9.json has no
     entry for them, so no standard set finds them.
  3. --facs, as in `build`, so `render --blend` has its viseme properties.
  4. Every numeric property on the rig object and its data is written to
     <name>_morphs.json with the min, max, soft min, soft max and default the
     importer gave it.
  5. --set NAME=VALUE writes the property, tags the rig and its objects (a
     plain write does not tag anything, so the drivers would not run), and
     measures how far each mesh the rig deforms moves, in millimetres.
  6. --wear imports a clothing or hair .duf with the figure already in the
     scene. Each wearable arrives as its own armature and mesh; the probe
     parents that armature to the body rig, selects both and calls
     bpy.ops.daz.merge_rigs(useOnlySelected=True), after which the mesh is
     parented to the body rig with its Armature modifier pointing at it.
  7. bpy.ops.daz.transfer_shapekeys(transferMethod='NEAREST') from the body
     to those meshes, unless --no-transfer. Its poll needs an active mesh
     with shape keys, so with no morphs loaded it fails with "Operator
     bpy.ops.daz.transfer_shapekeys.poll() failed, context is incorrect".
  8. --set-dressed, the same as --set but after the wearables are on.
  9. --pose runs bpy.ops.daz.import_pose() and counts the pose bones whose
     matrix_basis changed. The probe passes affectMorphs=False, as the
     operator's own invoke() does: called from Python the property keeps its
     default True, and with useClearMorphs also True the pose preset zeroes
     every morph dial on the figure. --pose-affects-morphs leaves it at True.
 10. After saving, `verify` reopens the .blend in a second Blender with no
     add-on and no extension repository, counts the posed bones, clears the
     pose and zeroes the sliders that were set, and reports how far each mesh
     moves. --no-verify skips it.
Every operator returns FINISHED even when it failed, so each step also
records import_daz.get_error_message(), and a step that made nothing it
should have made is marked failed. The importer's own terminal output goes to
<name>_blender.log. The build carries on past a failed morph step and saves
what it has.

TWO VERTEX COUNTS, AND WHICH IS WHICH. `survey`, `mesh_facts` and `verify`'s
`meshes` count the mesh as it is stored, the cage. Every count under a `moved`
key, in a dial, in `pose` and in `verify`'s `pose_cleared` and `props_zeroed`,
is taken on the mesh as Blender evaluates it, so a Subsurf modifier that is
still on multiplies it. With --subdivision off the two agree, because every
Subsurf in the scene is switched off before the first measurement and again as
soon as the wearables are in; with --subdivision keep, the default, they do
not, and the same mesh appears in one report at both counts.

`render --blend` reads <name>_build.json for the viseme properties and runs
two stages, each with a neutral row (every viseme property 0) and then a row
per viseme, all 17 or those --only names:
  1. scripts/render_sheet.py: the whole figure, one angle, at --sheet-size,
     each row setting its viseme property to 1 through "@props". It is run
     with --engine eevee, pinned rather than left to that script's default,
     which became Cycles on 2026-09-18: stage 2 below rasterises with EEVEE,
     the two stages are read side by side, and every render number this file
     records was measured on EEVEE.
     render_sheet.py opens a .blend as saved, so with --subdivision off (the
     default) this first opens the file and, if any Subsurf modifier is on,
     saves a copy beside it with every one off, _<name>_sheet_<pid>.blend,
     for render_sheet.py to open. The copy and the rows file are deleted
     afterwards. --subdivision as-saved hands render_sheet.py the file itself.
  2. The probe's own renderer, with render_sheet.py's default clay, sun and
     world light, as scripts/mpfb_probe.py does, in these framings:
       body     the whole figure, orthographic, azimuth 45, elevation 30
       face     front on; the band from the crown down to the lowest vertex
                AA moves (or, if AA moves none, the viseme that moves the
                most body vertices) fills three quarters of the cell height,
                whatever --only says
       face34   the same framing, 35 degrees round towards the key light and
                10 degrees up
Files are named <name>_<label>_<file>. The label is --label, or by default the
options that differ from their defaults, joined with _ in this order: the
--only visemes joined with -, the --sizes, the --columns, s<samples>,
materials, as-saved, no-sheet or sheet<size>, t<threshold>. A default run and
--motion-only have no label, so a short run does not overwrite a full one.
<name>[_<label>]_render.json records the command line, every option, the
render_sheet.py command, the file it opened and its exit, and, per size and
framing, the pixels each viseme changes against the neutral row, with the
threshold mpfb_probe.py uses. It and _motion.json hold, for all 17 visemes,
how far the drivers moved the evaluated body and Mouth meshes and which pose
bones moved in armature space, sorted into the importer's "(drv)" helper
bones (and which of those the drivers posed), Daz bones whose own channels
changed, Daz bones following a helper through a constraint, and Daz bones
carried by a moving parent.

MEASURED on 2026-09-16 in comfyui-packaged (bpy 4.5.9 LTS, EEVEE drawing
through llvmpipe) against Genesis 9 Starter Essentials (SKU 86958) installed
at /models/daz_library. Each item names the command that produced it; unless
it says otherwise that is an example above, run with this version of the
script. Peak memory is the Blender process's peak RSS; docker stats took 1 to
4 samples of a build, too few to follow it.
  source    Read, not run: in input/_devtools/import_daz/ext/import_daz no
            line references bpy.app.background, and the 9 lines that call
            invoke_props_dialog sit on invoke() paths, which an operator
            called from Python does not take (grep and the enclosing
            functions).
  build     `build --visemes --facs --out output/daz/g9_visemes.blend`, exit
            1 because import_visemes added nothing: 5.7 s wall, 5.48 s in
            Blender, peak 653 MiB, import_facs 4.19 s. The add-on registered
            as an extension and every operator ran from Python in background
            mode with no dialog waiting. Blender drops bl_info from a module
            it enables as an extension, so the build reads
            blender_manifest.toml: version 5.2.0, BUILD 3018.
            `build --facs --subdivision off --out output/daz/g9_cage.blend`:
            5.7 s wall, 5.51 s in Blender, peak 711 MiB.
  figure    Genesis 9.duf, because it is the load Daz Studio offers. Against
            the Dev Load it also names body_bs_Navel_HD3,
            head_bs_MouthRealism_HD3 and facs_ctrl_EyeRestingFocalPoint (read
            from both files), and the anatomy figures in its post-load script. The g9_visemes
            build log prints "Missing geonode" for the two HD3 morphs. That
            build's body mesh has 25182 vertices and 25156 faces; Mouth 5079
            and 5000, Eyes 2120 and 2112, Eyelashes 2028 and 858, Tear 280
            and 220. The Dev Load example: 150 bones, 0.9 s wall.
  rig       g9_visemes build: 152 bones after the figure (138 Daz bones and
            14 "(drv)" helpers), 157 after merge_rigs, and 177 after
            import_facs: 143 Daz bones (138 and tongue01 to tongue05 from the
            Mouth), as the research note says, and 34 "(drv)" helpers.
  visemes   g9_visemes build: bpy.ops.daz.import_visemes() returns FINISHED,
            logs "Load Visemes to Genesis 9 Mesh (0 morphs)" and the same for
            the other 4 meshes, and leaves get_error_message() empty:
            data/paths/genesis9.json has no viseme table (read).
            bpy.ops.daz.import_facs() logs 285 morphs for the body, 21 for
            the Mouth, including 10 viseme controllers (vER, vIH, vIY, vL,
            vOW, vS, vSH, vT, vTH, vUW), 18 for the Tear, 2 for the Eyelashes
            and 1 for the Eyes. It adds 284 object and 338 data properties,
            among them facs_ctrl_vAA to facs_ctrl_vW, 17 on the rig object
            with 17 "(fin)" twins on its data. No shape key carries a viseme
            name: the body gets 178 FACS shape keys and the Mouth 6 tongue
            keys. The Mouth's controllers share the body's property names,
            so one property drives both.
  drivers   g9_visemes build: 409 drivers on the rig and 325 on shape keys,
            none of them anything but a simple expression, and nothing added
            to bpy.app.driver_namespace.
  motion    `render --blend output/daz/g9_cage.blend --motion-only`, 0.6 s
            wall: the .blend opened with no DAZ add-on and auto-run scripts
            off. facs_ctrl_vAA at 1 moves 2880 body cage vertices, up to 7.8
            mm, and 12 body shape keys. Over the 17 visemes the body moves
            1419 (T) to 3494 (EE) vertices, up to 2.8 (T) to 11.8 (W) mm, and
            3 (L) to 41 (OW) shape keys. M moves 24 shape keys and no bone.
            Every other viseme changes the same 33 pose bones in armature
            space: 15 are the importer's "(drv)" helpers, 9 to 14 of which
            the drivers pose while the rest move with their parent; 15 are
            Daz bones following their helper through a Copy Transforms
            constraint, lowerjaw and tongue01 to tongue05 among them; and 3,
            lowerteeth, lowerfacerig and chin, are carried by a moving
            parent. No Daz bone's own channels change.
  paths     The wrong content path example, exit 1: set_global_setting raised
            nothing, get_root_paths() and get_absolute_paths() returned [],
            easy_import_daz returned FINISHED with no object, and
            get_error_message() said "Some assets were not found. Check that
            all DAZ root paths have been set up correctly." and listed five
            .dsf files. In the g9_visemes build the library's "Daz 3D" folder
            resolved against the importer's "DAZ 3D" tables, because it
            matches names without regard to case on Linux.
  render    Diffeomorphic saves 5 Subsurf modifiers at level 1 in the
            viewport and up to 3 for render. The as-saved example above, on
            g9_visemes.blend: 2 face cells of 128 px at 16 samples in 88.7 s,
            peak 4593 MiB, container 4.54 to 8.83 GiB.
            `render --blend output/daz/g9_visemes.blend --only AA --sizes 128
            --columns face --samples 16`: the copy with Subsurf off took 0.5 s
            wall, render_sheet.py drew its 2 rows in 28.8 s wall, and the
            probe's 2 cells took 17.9 s, peak 2655 MiB.
            `render --blend output/daz/g9_visemes.blend`, run with the
            earlier version of this script that handed render_sheet.py the
            file as saved: its whole-figure cells at 64 samples came about
            238 s apart, so 18 rows would pass the 3600 s timeout, and the
            run was stopped after 3.
            The Kat example above: 2 cells in 81.9 s, peak 6312 MiB, container
            4.54 to 10.63 GiB; the same command on g9_kat_notex.blend, 27.7 s
            and 2836 MiB. The Kat builds: 8.7 s wall each; the figure import
            alone reached 1444 MiB in 3.02 s, because the importer reads the
            images as it imports, so --no-textures, which clears them
            afterwards, does not lower that peak (1456 MiB).
  full run  `render --blend output/daz/g9_cage.blend`, run once, with the
            version of this script before it made the Subsurf copy or wrote
            its options, which for this file rendered the same rows (not
            re-run): render_sheet.py's 18 rows in 184.3 s wall; the probe's
            162 cells (3 framings, 3 sizes, 64 samples) in 1287.6 s wall,
            390.1 s at 128 px, 422.9 s at 220 px and 473.5 s at 340 px, peak
            3401 MiB, container 4.54 to 7.67 GiB.
  visible   From that full run: render_sheet.py, whole figure at 128 px,
            changed 0 to 4 pixels per viseme, and its --check called 7 rows
            (IH, K, L, S, T, TH, W) the rest pose repeated, so it exited 1.
            The probe's framings, pixels changed against the neutral row
            (threshold 8), fewest to most over the 17 visemes:
                    128 px      220 px      340 px
           body     0 to 4      2 to 12     9 to 27
           face     67 to 258   213 to 791  533 to 1873
           face34   87 to 253   238 to 704  537 to 1559
            Read by Claude on 2026-09-16 from a crop of the 340 px face
            column, clay: OW and UW read as rounded mouths, EH and ER as open
            with teeth, EE and IY as teeth behind parted lips, M as pressed
            lips; F, K, L, S, T, TH, IH and W look like one slightly parted
            mouth, and AA opens less than OW. Whether a Daz render may be shown
            to an AI model at all is unsettled (docs/reference/daz-genesis.md,
            "The AI clauses"), so the daz-figure skill has a person judge them.

MEASURED on 2026-09-18 in comfyui-packaged, the same library and bpy, by the
`scene` and `verify` examples above. Each item names the command that made it.
  morph     The morphs example, 5.0 s wall, 4.86 s in Blender, peak 642.0 MB
  sets      RSS, container 2.76 to 3.19 GiB. import_units,
            import_expressions, import_visemes and import_head each returned
            FINISHED and added nothing: the add-on's data/paths/genesis9.json
            has no units, expressions, visemes or head entry (read).
            import_body_morphs added 102 object and 251 data properties and 5
            body shape keys in 0.19 s, import_jcms 116 and 122 with 103 keys,
            import_flexions 27 and 27 with 14, import_masculine 13 and 13
            with 11, import_feminine 11 and 11 with 9, import_powerpose 88
            and 92 with 52, import_facs_expressions nothing.
  character The same run: the six Base Characters 9 "figure_ctrl_Character"
  dials     files, loaded with import_custom_morphs, added 86 object and 630
            data properties and 61 shape keys in 1.43 s, and each of them
            leaves get_error_message() "Found morphs that want to change the
            rest pose." The rig ended with 270 bones, up from 152 after the
            figure, and 1593 numeric properties, 444 on the object and 1149
            on its data. Their hard min and max are the float limits; the
            Daz limits are the soft range, 0.0 to 1.0 on Kat_figure_ctrl_
            Character and -2.0 to 2.0 on body_bs_ProportionHeight. 417 of the
            1593 have the soft range 0 to 1 and 862 have none (the "(fin)"
            and "(rst)" twins and the corrective "cbs" morphs).
  sliders   The same run, on the cage with every Subsurf off: setting
            Kat_figure_ctrl_Character to 1.0 moved all 25182 body vertices,
            by up to 59.67 mm; body_bs_ProportionHeight at 1.0 moved 22292 of
            them by up to 14.0 mm.
  character `build --figure "People/Genesis 9/Genesis 9.duf"` against `build
  preset    --figure "People/Genesis 9/Characters/Kat for Genesis 9.duf"`,
            1.4 s and 4.7 s wall: the base figure gives a rig of 157 bones
            with 2 object and 4 data properties and 23 drivers, a body mesh
            of 25182 vertices with no shape key, 2 images and 18 materials;
            the Kat preset gives 158 bones with 47 and 64 properties and 90
            drivers, the same 25182 vertices with 40 shape keys (39 driven),
            18 images and 18 materials, and a different eyebrow figure (Card
            Style 12, 9000 vertices, against Style 06, 6944). Its import step
            alone took 3.38 s and reached 1436.3 MB peak RSS. The same
            command with --no-textures gives the same counts and clears 29
            image texture nodes, leaving 0 images in the file.
  wearables The outfit example, 5.2 s wall, peak 998.4 MB RSS, container 2.22
            to 2.90 GiB. Each wearable arrives as its own armature and mesh
            (G9 Base Shirt 126 bones, G9 Base Shorts 126, dForce Pixie Hair
            Cap 51) with the mesh parented to that armature and an "Armature
            SkinBinding" modifier pointing at it. merge_rigs returned
            FINISHED, left no other armature and did not change the body
            rig's 233 bones, so every wearable bone is a duplicate of one the
            figure already has; afterwards each mesh is parented to the body
            rig, keeps its own vertex groups (shirt 20, shorts 7, hair cap
            18) and its Armature modifier points at the body rig.
  outfit    The same run: transfer_shapekeys returned FINISHED with no error
  and a    and added 0 shape keys to the shirt and the shorts, which is the
  dial      wiki's "Morphed (Characters): Don't fit meshes, but load
            shapekeys. Not all shapekeys are found. Shapekeys are not
            transferred to clothes" (Import_Import_DAZ_Manually.md). Setting
            Kat_figure_ctrl_Character to 1.0 with the outfit on moved all of
            the shirt's and the shorts' vertices by 57.25 mm, mean and
            maximum the same, so the outfit follows the rest pose the dial
            changes as a rigid body and not the body's new shape, while the
            body's own vertices moved by up to 66.21 mm with a mean of 43.09.
  pose      The same run: import_pose on "G9 Base Pose 13 Walking G9B.duf"
            returned FINISHED, moved 48 of the rig's 233 pose bones (50 have
            a rotation once the drivers have run) and wrote no f-curve. The
            body moved 801.24 mm at most, the shirt 214.70, the shorts
            214.97 and the hair cap 180.89. The strand mesh dForce Pixie Cut
            Mesh did not move at all: its only vertex group is "dForce Pin",
            a simulation group with no bone of that name, so its Armature
            modifier deforms nothing. With --pose-affects-morphs, or from any
            caller that does not pass affectMorphs, the same call put
            Kat_figure_ctrl_Character back to 0.0.
  no add-on `verify --blend output/daz/g9_outfit.blend`, 0.8 s wall, peak
            578.5 MB: reopened with no DAZ add-on enabled and auto-run
            scripts off, the file still has 233 bones, 88 posed bones, 618
            drivers, 267 object and 438 data properties, and the dial still
            reads 1.0. Clearing the pose moves the body 801.24 mm, the shirt
            214.86 and the shorts 215.14; zeroing the one dial moves the body
            66.21 mm and the outfit 57.25 mm. Nothing in the file needs the
            add-on.
  dressed   The dressed example, 17.5 s wall, 17.39 s in Blender, peak
            1643.7 MB RSS, container 2.29 to 3.59 GiB, output/daz/g9_dressed
            .blend 140,971,653 bytes. 258 bones, 578 object and 803 data
            properties, 1031 drivers, all 17 viseme properties found; body
            25182 vertices with 339 shape keys, shirt 8038, shorts 8256,
            hair cap 1085, hair strands 236136, plus the five anatomy meshes.
            import_facs took 5.68 s of it, the three wearables 5.09 s.
  rendering `render --blend output/daz/g9_dressed.blend --only AA --sizes 128
            --columns face --samples 16 --no-sheet`: 2 cells of 128 px in
            20.0 s, 21.0 s wall, container peak 5.50 GiB. AA moves 2880 body
            vertices by up to 7.5 mm and changes 218 of the cell's 6584
            figure pixels. The same options on g9_cage.blend give the same
            210 changed pixels of 6619 as the run of 2026-09-16, so the body
            mesh change below did not move the older numbers.
  body mesh Before 2026-09-18 `render` took the figure to be the largest mesh
            parented to the rig, which on a dressed figure is the hair (236136
            vertices against the body's 25182): the first render of
            g9_dressed.blend reported AA moving 0 body vertices and framed
            the head from the head bone. It now prefers the mesh the report
            names, then the one with the most shape keys.

Before each Blender job this waits, polling every 30 s, until ComfyUI's queue
is empty and `docker top` shows no other `python3 -c` job in the container.
--no-wait skips that. Peak memory is sampled from `docker stats` on the host
while the job runs, and the Blender process reports its own peak RSS. Every
Blender job ends itself inside the container after --timeout. On Ctrl-C or
SIGTERM, and whenever render_sheet.py exits non-zero, this ends the Blender
job it started in the container, found by a path unique to that job in its
arguments (SIGTERM, then SIGKILL after 10 s), deletes the frames and
temporary files that job was writing, and on a stop writes no report.

Exit codes: 0 done; 1 a download, checksum, Blender step or check failed,
render_sheet.py exited non-zero (as its --check does when a row repeats the
rest pose), or Blender ran past --timeout; 2 bad arguments; 130 stopped by
Ctrl-C; 143 stopped by SIGTERM.
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import gzip
import hashlib
import http.client
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import ALARM_GRACE, container, exec_json, exec_python  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEV = ROOT / "input" / "_devtools" / "import_daz"
DOWNLOADS = DEV / "downloads"
EXT = DEV / "ext"
OUT = ROOT / "output" / "daz"
REPO_MODULE = "import_daz_probe"
COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
DEFAULT_LIBRARY = Path("/models/daz_library")
DEFAULT_FIGURE = "People/Genesis 9/Genesis 9.duf"

PIN = {
    "name": "import_daz",
    "version": "5.2.0",
    "tag": "version_5_2_0",
    "commit": "1abc6815bdc5c305d8128f5714b73622af6838ce",
    "file": "import_daz-version_5_2_0.zip",
    "top": "import_daz-version_5_2_0/",
    "urls": ["https://github.com/Diffeomorphic/import_daz/archive/refs/tags/version_5_2_0.zip",
             "https://codeload.github.com/Diffeomorphic/import_daz/zip/refs/tags/version_5_2_0"],
    "size": 1697629,
    "sha256": "b6921c46e9a876fe88ab0ef75f47c8eac67cf4c4314059871d2a78bdcfccf9d2",
    "licence": "code GPL-2.0-or-later",
    "licence_source": "blender_manifest.toml in the archive (license = SPDX:GPL-2.0-or-later)",
}

# The 17 Genesis viseme names, in the order the research note gives them.
VISEMES = ["AA", "EE", "EH", "ER", "F", "IH", "IY", "K", "L", "M",
           "OW", "S", "SH", "T", "TH", "UW", "W"]
PROP_PATTERN = r"facs_ctrl_v|ectrlv|viseme"
MATERIAL_METHODS = ("EXTENDED_PRINCIPLED", "BSDF", "FBX_COMPATIBLE")
# The importer's standard morph sets, from its own operator names. Which of
# them find anything depends on the paths table for the figure, which for
# Genesis 9 is data/paths/genesis9.json inside the add-on.
MORPH_SETS = {
    "units": "import_units", "expressions": "import_expressions",
    "visemes": "import_visemes", "head": "import_head", "facs": "import_facs",
    "facsdetails": "import_facs_details", "facsexpr": "import_facs_expressions",
    "powerpose": "import_powerpose", "anime": "import_anime",
    "body": "import_body_morphs", "jcms": "import_jcms",
    "masculine": "import_masculine", "feminine": "import_feminine",
    "flexions": "import_flexions",
}
FIT_METHODS = ("MORPHED", "UNIQUE", "SHARED", "DBZFILE")
COLUMNS = ("body", "face", "face34")
SIZES = [128, 220, 340]
TIMEOUT_GRACE = ALARM_GRACE
# render_sheet.py hardcodes where its Blender job writes cells: this folder,
# then "<its pid>_<unix time>".
SHEET_FRAMES = ROOT / "output" / "_sheet_frames"
SHEET_FRAMES_C = "/app/output/_sheet_frames"


# ------------------------------------------------------------------ fetch

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(pin: dict) -> bool:
    dest = DOWNLOADS / pin["file"]
    if dest.exists() and dest.stat().st_size == pin["size"] and sha256_of(dest) == pin["sha256"]:
        print(f"  have     {dest.relative_to(ROOT)}")
        return True
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    for url in pin["urls"]:
        print(f"  get      {url}")
        h = hashlib.sha256()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "asset-engine daz_import_probe"})
            with urllib.request.urlopen(req, timeout=120) as r, part.open("wb") as f:
                for chunk in iter(lambda: r.read(1 << 20), b""):
                    f.write(chunk)
                    h.update(chunk)
        except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
            print(f"  ! {url}: {type(exc).__name__}: {exc}")
            part.unlink(missing_ok=True)
            continue
        size = part.stat().st_size
        if size != pin["size"] or h.hexdigest() != pin["sha256"]:
            print(f"  ! {pin['file']}: got {size} bytes, sha256 {h.hexdigest()}; "
                  f"pinned {pin['size']} bytes, sha256 {pin['sha256']}. Deleted.")
            part.unlink(missing_ok=True)
            continue
        part.replace(dest)
        print(f"  ok       {dest.relative_to(ROOT)}  {size} bytes  sha256 {pin['sha256']}")
        return True
    return False


def unpacked_intact(pin: dict, target: Path) -> str | None:
    """None when every file member of the checked archive is on disk at its size, else why not."""
    try:
        if json.loads((target / ".fetched.json").read_text())["sha256"] != pin["sha256"]:
            return "its .fetched.json names another archive"
    except (OSError, ValueError, KeyError, TypeError):
        return "its .fetched.json cannot be read"
    with zipfile.ZipFile(DOWNLOADS / pin["file"]) as zf:
        for info in zf.infolist():
            rel = info.filename[len(pin["top"]):]
            if not rel or info.is_dir():
                continue
            p = target / rel
            if not p.is_file():
                return f"{rel} is missing"
            if p.stat().st_size != info.file_size:
                return f"{rel} is {p.stat().st_size} bytes, the archive holds {info.file_size}"
    return None


def unpack_addon(pin: dict) -> bool:
    target = EXT / "import_daz"
    if (target / ".fetched.json").is_file():
        why = unpacked_intact(pin, target)
        if why is None:
            print(f"  have     {target.relative_to(ROOT)}")
            return True
        print(f"  ! {target.relative_to(ROOT)} does not match the archive: {why}; unpacking again")
    archive = DOWNLOADS / pin["file"]
    staging = EXT / ".import_daz.staging"
    shutil.rmtree(staging, ignore_errors=True)
    with zipfile.ZipFile(archive) as zf:
        comment = zf.comment.decode("ascii", "replace")
        if comment != pin["commit"]:
            print(f"  ! {pin['file']}: zip comment names commit {comment!r}, pinned {pin['commit']}")
            return False
        infos = zf.infolist()
        for info in infos:
            p = PurePosixPath(info.filename)
            if p.is_absolute() or ".." in p.parts or not info.filename.startswith(pin["top"]):
                print(f"  ! refusing {pin['file']}: member {info.filename!r} is outside {pin['top']}")
                return False
        manifest = zf.read(pin["top"] + "blender_manifest.toml").decode("utf-8")
        if not re.search(r'^id = "import_daz"$', manifest, re.M) or \
                not re.search(rf'^version = "{re.escape(pin["version"])}"$', manifest, re.M):
            print(f"  ! {pin['file']}: blender_manifest.toml is not import_daz {pin['version']}")
            return False
        staging.mkdir(parents=True)
        files = 0
        for info in infos:
            rel = info.filename[len(pin["top"]):]
            if not rel:
                continue
            dest = staging / rel
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)
            files += 1
    (staging / ".fetched.json").write_text(json.dumps(
        {"file": pin["file"], "sha256": pin["sha256"], "commit": pin["commit"],
         "tag": pin["tag"], "files": files, "licence": pin["licence"]}, indent=2) + "\n")
    shutil.rmtree(target, ignore_errors=True)
    staging.replace(target)
    print(f"  unpacked {target.relative_to(ROOT)}  ({files} files, commit {pin['commit'][:7]})")
    return True


def cmd_fetch(args) -> int:
    if not download(PIN):
        return 1
    return 0 if unpack_addon(PIN) else 1


# ------------------------------------------------------------------ Blender side

PRELUDE = r'''
import json, math, os, re, resource, signal, sys, time, traceback
cfg = json.loads(sys.argv[-1])
# The host's timeout only stops docker exec; SIGALRM's default action ends
# this process even inside C code or a hang at exit.
signal.signal(signal.SIGALRM, signal.SIG_DFL)
signal.alarm(cfg["timeout"])
for d in (cfg["user_resources"], os.path.join(cfg["home"], "DAZ Importer"), os.path.dirname(cfg["blend"])):
    os.makedirs(d, exist_ok=True)
# Before bpy loads: Blender's user folders and the importer's ~/DAZ Importer
# settings and error file go under the dev folder.
os.environ["BLENDER_USER_RESOURCES"] = cfg["user_resources"]
os.environ["HOME"] = cfg["home"]
# The importer prints a great deal; send this process's stdout to the log and
# restore it only for the result line.
sys.stdout.flush()
_saved_stdout = os.dup(1)
_log = os.open(cfg["log"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
os.dup2(_log, 1)
T0 = time.time()
import bpy, addon_utils

result = {"steps": [], "stopped_at": None, "failures": []}
daz = None


class Stop(Exception):
    pass


def peak_rss_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def checkpoint():
    with open(cfg["partial"], "w") as f:
        json.dump(result, f, indent=1)


def step(name, fn, fatal=True):
    print("\n=== PROBE STEP " + name, flush=True)
    t = time.time()
    entry = {"step": name}
    value = None
    try:
        value = fn()
        entry["ok"] = True
    except Exception as exc:
        entry["ok"] = False
        entry["error"] = f"{type(exc).__name__}: {exc}"
        entry["traceback"] = traceback.format_exc()[-3000:]
    entry["seconds"] = round(time.time() - t, 2)
    entry["peak_rss_mb"] = peak_rss_mb()
    if daz is not None:
        entry["get_error_message"] = daz.get_error_message()
    result["steps"].append(entry)
    sys.stdout.flush()
    checkpoint()
    if not entry["ok"]:
        result["failures"].append({"step": name, "error": entry["error"],
                                   "get_error_message": entry.get("get_error_message", "")})
        if fatal:
            result["stopped_at"] = name
            raise Stop(name)
    return value


def reraise(exc):
    raise exc


def deselect_all():
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)


def activate(ob):
    deselect_all()
    ob.hide_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def import_duf(abspath):
    """easy_import_daz on one file; returns the new objects or raises.

    useMergeMaterials is off. It merges materials that are identical at import
    time, and a Genesis 9 anatomy figure arrives with every one of its
    materials bare and so identical: the eyelash upper and lower surfaces came
    out as one material, and the four eye surfaces as one, which left nowhere
    for their MAT preset to put the maps that make them read.
    """
    before = set(bpy.data.objects)
    daz.set_silent_mode(True)
    ret = bpy.ops.daz.easy_import_daz(
        directory=os.path.dirname(abspath),
        files=[{"name": os.path.basename(abspath)}],
        materialMethod=cfg["material_method"],
        useMergeMaterials=cfg["merge_materials"],
        fitMeshes=cfg["fit"])
    # easy_import_daz leaves silent mode off when it returns.
    daz.set_silent_mode(True)
    new = [ob for ob in bpy.data.objects if ob not in before]
    if not new:
        raise RuntimeError(f"easy_import_daz returned {sorted(ret)} and made no object; "
                           f"get_error_message(): {daz.get_error_message()!r}")
    return new


def armature_props(rig):
    out = {}
    for owner, label in ((rig, "object"), (rig.data, "data")):
        for k in owner.keys():
            out.setdefault(label, []).append(k)
    return out


def matching(names):
    return sorted(n for n in names if re.search(cfg["prop_pattern"], n, re.I))


def driver_stats(idblock):
    ad = getattr(idblock, "animation_data", None)
    if not ad:
        return 0, 0
    total = complex_ = 0
    for fc in ad.drivers:
        total += 1
        if fc.driver.type == "SCRIPTED" and not fc.driver.is_simple_expression:
            complex_ += 1
    return total, complex_


def survey():
    s = {"objects": [], "meshes": {}, "armatures": {}}
    for ob in bpy.data.objects:
        s["objects"].append({"name": ob.name, "type": ob.type,
                             "parent": ob.parent.name if ob.parent else None,
                             "parent_type": ob.parent_type if ob.parent else None})
        if ob.type == "MESH":
            me = ob.data
            keys = me.shape_keys.key_blocks if me.shape_keys else []
            dk = driver_stats(me.shape_keys) if me.shape_keys else (0, 0)
            mats = []
            for slot in ob.material_slots:
                m = slot.material
                if not m:
                    continue
                types = sorted({n.type for n in m.node_tree.nodes}) if m.node_tree else []
                groups = sorted({n.node_tree.name for n in m.node_tree.nodes
                                 if n.type == "GROUP" and n.node_tree}) if m.node_tree else []
                mats.append({"name": m.name, "node_types": types, "groups": groups})
            s["meshes"][ob.name] = {
                "vertices": len(me.vertices), "faces": len(me.polygons),
                "shape_keys": len(keys),
                "shape_key_names": [k.name for k in keys],
                "shape_key_drivers": dk[0], "shape_key_python_drivers": dk[1],
                "modifiers": [[m.name, m.type] for m in ob.modifiers],
                "materials": mats,
            }
        elif ob.type == "ARMATURE":
            props = armature_props(ob)
            names = props.get("object", []) + props.get("data", [])
            do = driver_stats(ob)
            dd = driver_stats(ob.data)
            s["armatures"][ob.name] = {
                "bones": len(ob.data.bones),
                "bone_names": [b.name for b in ob.data.bones],
                "deform_bones": sum(1 for b in ob.data.bones if b.use_deform),
                "custom_properties": {k: len(v) for k, v in props.items()},
                "matching_properties": {k: matching(v) for k, v in props.items()},
                "drivers": do[0] + dd[0], "python_drivers": do[1] + dd[1],
            }
    s["images"] = len(bpy.data.images)
    s["materials"] = len(bpy.data.materials)
    s["node_groups"] = len(bpy.data.node_groups)
    return s


def base_material_name(name):
    """The Daz material behind a Blender one: Blender's .001 copy suffix and
    Daz's own -1 instance suffix both come off."""
    return re.sub(r"-\d+$", "", re.sub(r"\.\d{3}$", "", name))


def principled_of(mat):
    """The one Principled BSDF this material's surface comes from, or None."""
    tree = mat.node_tree
    out = next((n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
    if out is not None and out.inputs["Surface"].is_linked:
        node = out.inputs["Surface"].links[0].from_node
        if node.type == "BSDF_PRINCIPLED":
            return node
    found = [n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"]
    return found[0] if len(found) == 1 else None


def transparency_of(mat):
    """What already makes this material see-through, if anything does."""
    for node in mat.node_tree.nodes:
        if node.type == "BSDF_TRANSPARENT":
            return "a Transparent BSDF"
        if node.type == "GROUP" and node.node_tree and "Transparent" in node.node_tree.name:
            return "the %s group" % node.node_tree.name
    bsdf = principled_of(mat)
    alpha = bsdf.inputs.get("Alpha") if bsdf is not None else None
    if alpha is None:
        return None
    if alpha.is_linked:
        return "a link into Alpha"
    if alpha.default_value < 1.0:
        return "Alpha %s" % round(alpha.default_value, 3)
    return None


def preset_image(rel, colorspace):
    """One image datablock per file, its colour space set for the use it is put
    to. A file used as both a colour map and a cutout map would end up with
    whichever came last, which nothing in the Genesis 9 presets does: the
    eyelashes take the C map as cutout opacity and a flat colour beside it."""
    img = bpy.data.images.load(os.path.join(cfg["library"], rel), check_existing=True)
    img.colorspace_settings.name = colorspace
    return img


def texture_node(tree, image, label, x, y):
    node = tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    node.label = label
    node.location = (x, y)
    return node


def layer_stack(tree, layers, x, y):
    """Rebuild a Daz layered image: each layer laid over the one below it,
    through the top layer's own alpha. Returns the socket to link on."""
    socket = None
    for i, layer in enumerate(layers):
        if "image" in layer:
            tex = texture_node(tree, preset_image(layer["image"], "sRGB"),
                               layer.get("label") or "layer", x, y - i * 300)
            colour, alpha = tex.outputs["Color"], tex.outputs["Alpha"]
        else:
            flat = tree.nodes.new("ShaderNodeRGB")
            flat.location = (x, y - i * 300)
            flat.label = layer.get("label") or "base"
            flat.outputs[0].default_value = tuple(layer["colour"]) + (1.0,)
            colour, alpha = flat.outputs[0], None
        if socket is None:
            socket = colour
            continue
        mix = tree.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MIX"
        mix.location = (x + 260, y - i * 300)
        tree.links.new(socket, mix.inputs[6])          # A, the layer below
        tree.links.new(colour, mix.inputs[7])          # B, this layer
        if alpha is not None:
            tree.links.new(alpha, mix.inputs[0])       # Factor, its own alpha
        else:
            mix.inputs[0].default_value = 1.0
        socket = mix.outputs[2]
    return socket


def body_of(rig, meshes):
    """The figure's own mesh among the ones a rig deforms."""
    if not meshes:
        return None
    named = [o for o in meshes if o.name == f"{rig.name} Mesh" or o.name.startswith(rig.name)]
    return max(named or meshes,
               key=lambda o: (len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0,
                              len(o.data.vertices)))


def offset_meshes(moves):
    """Move a worn mesh bodily, in millimetres, along the world axes.

    The blunt instrument, for a garment that sits where its author put it and
    that is not where this figure needs it. Measured before it is used: the
    Wise Wizard's cloak tops out 69.6 mm below the crown of the head it is
    hooded over. The rest shape moves and every shape key with it, so this is
    only sound on an unposed figure, as the declip is.
    """
    from mathutils import Vector
    out = {}
    for name, (dx, dy, dz) in moves.items():
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != "MESH":
            out[name] = {"skipped": "no mesh of that name"}
            continue
        delta = ob.matrix_world.to_3x3().inverted() @ Vector((dx / 1000.0, dy / 1000.0,
                                                              dz / 1000.0))
        keys = ob.data.shape_keys.key_blocks if ob.data.shape_keys else []
        for i, v in enumerate(ob.data.vertices):
            v.co = v.co + delta
            for block in keys:
                block.data[i].co = block.data[i].co + delta
        ob.data.update()
        out[name] = {"moved_mm": [dx, dy, dz], "vertices": len(ob.data.vertices),
                     "shape_keys": len(keys)}
    return out


def owned_vertices(ob, group_name, dg):
    """World-space positions of the evaluated vertices one vertex group owns.

    Owns means that group carries the vertex's largest weight, so the head bone's
    share of Genesis 9 is the skull and the face rather than every vertex the
    head pulls on a little.
    """
    group = ob.vertex_groups.get(group_name)
    if group is None:
        return []
    index, mw = group.index, ob.matrix_world
    evaluated = ob.evaluated_get(dg)
    me = evaluated.to_mesh()
    out = []
    for v in me.vertices:
        best = None
        for g in v.groups:
            if best is None or g.weight > best.weight:
                best = g
        if best is not None and best.group == index:
            out.append(mw @ v.co)
    evaluated.to_mesh_clear()
    return out


def fitted_sphere(points):
    """Centre and radius of the sphere closest to a cloud, by least squares.

    The algebraic fit: |p - c|^2 = r^2 is linear in (c, r^2 - |c|^2), so one
    lstsq on [2x 2y 2z 1] against x^2 + y^2 + z^2 gives both with no iteration.
    A scalp is what this is for, and a scalp is the top of a head, so the caller
    hands in the upper part of a bone's skin and not the jaw and the nose.
    """
    import numpy as np
    a = np.array([[p.x, p.y, p.z] for p in points], dtype=np.float64)
    lhs = np.column_stack((2 * a, np.ones(len(a))))
    rhs = (a ** 2).sum(axis=1)
    sol, *_ = np.linalg.lstsq(lhs, rhs, rcond=None)
    centre = sol[:3]
    radius = float(np.sqrt(max(sol[3] + (centre ** 2).sum(), 0.0)))
    residual = np.abs(np.linalg.norm(a - centre, axis=1) - radius)
    return {"centre": [float(c) for c in centre], "radius_m": radius,
            "points": len(a),
            "residual_mean_mm": float(residual.mean() * 1000),
            "residual_max_mm": float(residual.max() * 1000)}


def wear_objs(specs, rig, body):
    """Import a Wavefront OBJ, put it where a bone's skin says, and hang it there.

    For geometry that is nobody's Daz product: a hair mesh this repo grew with
    scripts/make_hair.py is static, unrigged and modelled around its own origin
    on a scalp sphere, so it is placed rather than fitted.  The anchor is
    measured, not guessed: a sphere is fitted to the upper half of the bone's
    own skin and the object's origin goes to that sphere's centre.  The object
    is then bone-parented, so it follows a pose like a hat and not like skin.
    """
    from mathutils import Matrix, Vector
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for spec in specs:
        name = os.path.splitext(os.path.basename(spec["path"]))[0]
        before = set(bpy.data.objects)
        ret = bpy.ops.wm.obj_import(filepath=spec["path"], forward_axis=spec["forward"],
                                    up_axis=spec["up"], use_split_objects=False)
        added = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in added if o.type == "MESH"]
        entry = {"file": os.path.basename(spec["path"]), "returned": sorted(ret),
                 "objects": [[o.name, o.type] for o in added],
                 "vertices": sum(len(o.data.vertices) for o in meshes),
                 "faces": sum(len(o.data.polygons) for o in meshes),
                 "uv_layers": sorted({l.name for o in meshes for l in o.data.uv_layers}),
                 "materials": sorted({s.material.name for o in meshes
                                      for s in o.material_slots if s.material})}
        if not meshes:
            out[name] = dict(entry, skipped="the file imported no mesh")
            continue
        if not entry["faces"]:
            out[name] = dict(entry, skipped="the file has no polygons, so nothing would draw")
            continue

        box = [Vector(c) for o in meshes for c in o.bound_box]
        entry["box_before_m"] = {ax: [round(min(v[i] for v in box), 4),
                                      round(max(v[i] for v in box), 4)]
                                 for i, ax in enumerate("xyz")}
        anchor = Vector((0.0, 0.0, 0.0))
        if spec["bone"]:
            if body is None:
                out[name] = dict(entry, skipped="no body mesh to measure the bone's skin on")
                continue
            skin = owned_vertices(body, spec["bone"], dg)
            if len(skin) < 16:
                out[name] = dict(entry, skipped=f"{len(skin)} vertices are owned by vertex "
                                 f"group {spec['bone']!r}, too few to fit a sphere to")
                continue
            mid = (min(p.z for p in skin) + max(p.z for p in skin)) / 2
            upper = [p for p in skin if p.z >= mid]
            sphere = fitted_sphere(upper)
            entry["bone"] = spec["bone"]
            entry["skin_vertices"] = len(skin)
            entry["skull_sphere"] = sphere
            entry["skull_box_m"] = {ax: [round(min(p[i] for p in skin), 4),
                                         round(max(p[i] for p in skin), 4)]
                                    for i, ax in enumerate("xyz")}
            anchor = Vector(sphere["centre"])
            # The OBJ is in its own units and its roots sit `radius_cm` from its
            # own origin, so this is the scale that lands them on the skull.
            entry["scale_that_matches_the_sphere"] = round(
                sphere["radius_m"] / spec["radius_cm"], 6)
        anchor = anchor + Vector([v / 1000.0 for v in spec["offset"]])
        scale = spec["scale"]
        if scale is None:
            scale = entry.get("scale_that_matches_the_sphere", 0.01)
            entry["scale_chosen"] = "from the fitted sphere" if "scale_that_matches_the_sphere" \
                in entry else "0.01, centimetres to metres, with no bone to measure"
        spec = dict(spec, scale=scale)
        entry["scale"] = scale
        entry["yaw_degrees"] = spec["yaw"]
        entry["placed_at_m"] = [round(v, 4) for v in anchor]

        for ob in meshes:
            ob.matrix_world = (Matrix.Translation(anchor)
                               @ Matrix.Rotation(math.radians(spec["yaw"]), 4, "Z")
                               @ Matrix.Diagonal((spec["scale"],) * 3).to_4x4()
                               @ ob.matrix_world)
            for poly in ob.data.polygons:
                poly.use_smooth = True
            if spec["bone"] and rig is not None and spec["bone"] in rig.data.bones:
                keep = ob.matrix_world.copy()
                ob.parent = rig
                ob.parent_type = "BONE"
                ob.parent_bone = spec["bone"]
                ob.matrix_world = keep
                entry["parented_to"] = f"{rig.name}:{spec['bone']}"
            for slot in ob.material_slots:
                if slot.material:
                    entry.setdefault("alpha", {})[slot.material.name] = wire_cutout(slot.material)
        bpy.context.view_layer.update()
        box = [ob.matrix_world @ Vector(c) for ob in meshes for c in ob.bound_box]
        entry["box_after_m"] = {ax: [round(min(v[i] for v in box), 4),
                                     round(max(v[i] for v in box), 4)]
                                for i, ax in enumerate("xyz")}
        out[name] = entry
    return out


def wire_cutout(mat):
    """Make an OBJ material's alpha map cut the surface out rather than tint it.

    The OBJ importer reads map_d into Alpha but leaves the image in sRGB, which
    lightens every alpha value it reads, and leaves EEVEE rendering the surface
    opaque.  Cycles needs only the first of those fixed; both are set here so
    the same .blend draws the same either way.
    """
    node = principled_of(mat)
    done = {"material": mat.name, "alpha_linked": False}
    if node is None:
        return done
    link = node.inputs["Alpha"].links
    if link:
        source = link[0].from_node
        done["alpha_linked"] = True
        done["alpha_from"] = source.bl_idname
        if source.bl_idname == "ShaderNodeTexImage" and source.image:
            source.image.colorspace_settings.name = "Non-Color"
            done["alpha_image"] = source.image.name
            done["alpha_colorspace"] = "Non-Color"
    else:
        done["alpha_value"] = round(node.inputs["Alpha"].default_value, 3)
    base = node.inputs["Base Color"].links
    if base and base[0].from_node.bl_idname == "ShaderNodeTexImage" and base[0].from_node.image:
        done["base_colour_image"] = base[0].from_node.image.name
    mat.use_backface_culling = False
    for attr, value in (("blend_method", "BLENDED"), ("surface_render_method", "BLENDED"),
                        ("shadow_method", "CLIP")):
        try:
            setattr(mat, attr, value)
            done[attr] = value
        except (AttributeError, TypeError):
            pass
    return done


def declip(body, meshes, margin, max_verts, skip, max_push=0.0, passes=4):
    """Push a garment's vertices out of the body it is worn on.

    A garment is authored for one figure and worn by another, and no amount of
    fitting stops a wider hip coming through a pair of shorts. Every vertex
    that sits behind the body's surface is moved until it stands `margin`
    clear of it.

    The measuring is done on the evaluated mesh and the moving on the rest
    shape, because that is the one a .blend keeps, and the two differ: a
    character morph drives bones, so the figure is already deformed before any
    pose is applied. The difference is taken out by repeating: each pass moves
    a vertex by the gap it can still see, and the passes stop when nothing
    moves. It edits the rest shape, so a posed figure is refused by the caller.

    Meshes above `max_verts` are left alone, which is how a card hair, whose
    shape is the style, keeps it.
    """
    from mathutils.bvhtree import BVHTree
    targets = []
    out = {}
    for ob in meshes:
        if ob is body or ob.name in skip:
            continue
        if len(ob.data.vertices) > max_verts:
            out[ob.name] = {"skipped": f"{len(ob.data.vertices)} vertices, over the limit"}
            continue
        targets.append(ob)
        out[ob.name] = {"vertices": len(ob.data.vertices), "moved": 0,
                        "max_push_mm": 0.0, "passes": []}
    for _ in range(max(1, passes)):
        dg = bpy.context.evaluated_depsgraph_get()
        tree = BVHTree.FromObject(body, dg)
        moved_any = 0
        for ob in targets:
            evaluated = ob.evaluated_get(dg)
            me = evaluated.to_mesh()
            here = [ob.matrix_world @ v.co for v in me.vertices]
            evaluated.to_mesh_clear()
            if len(here) != len(ob.data.vertices):
                out[ob.name]["skipped"] = "the evaluated mesh has another vertex count"
                continue
            rotate_back = ob.matrix_world.to_3x3().inverted()
            keys = ob.data.shape_keys.key_blocks if ob.data.shape_keys else []
            moved, worst, deep = 0, 0.0, 0
            for i, point in enumerate(here):
                hit, normal, index, dist = tree.find_nearest(point)
                if hit is None:
                    continue
                signed = (point - hit).dot(normal)
                if signed >= margin:
                    continue
                if max_push and (margin - signed) > max_push:
                    # Too deep to be cloth clipping. A hood sits around a head
                    # rather than through it, and dragging its vertices onto
                    # the scalp is what "the cloak is shifted down" looks like:
                    # on the Wise Wizard's cloak the worst push was 68.09 mm.
                    deep += 1
                    continue
                delta = rotate_back @ ((hit + normal * margin) - point)
                ob.data.vertices[i].co = ob.data.vertices[i].co + delta
                for block in keys:
                    block.data[i].co = block.data[i].co + delta
                moved += 1
                worst = max(worst, margin - signed)
            if moved:
                ob.data.update()
            out[ob.name]["passes"].append(moved)
            out[ob.name]["left_deep"] = deep
            out[ob.name]["moved"] = max(out[ob.name]["moved"], moved)
            out[ob.name]["max_push_mm"] = max(out[ob.name]["max_push_mm"],
                                              round(worst * 1000, 2))
            moved_any += moved
        bpy.context.view_layer.update()
        if not moved_any:
            break
    for name, entry in out.items():
        if "vertices" in entry:
            entry["moved_pct"] = round(100.0 * entry["moved"] / max(1, entry["vertices"]), 2)
    return {"margin_mm": round(margin * 1000, 2), "max_vertices": max_verts,
            "max_push_mm": round(max_push * 1000, 2) if max_push else None, "meshes": out}


def fit_report(body, meshes, tolerance=0.0005):
    """How each other mesh sits against the body, in millimetres.

    Clipping is not a matter of taste: a garment vertex on the far side of the
    body's surface is inside the body, and the render shows skin through cloth.
    Every vertex is measured against the body's evaluated surface, and a
    vertex counts as inside when it lies more than `tolerance` behind the
    nearest face's normal.
    """
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(body, dg)
    out = {}
    for ob in meshes:
        if ob is body:
            continue
        evaluated = ob.evaluated_get(dg)
        me = evaluated.to_mesh()
        inside, depths, gaps = 0, [], []
        for v in me.vertices:
            point = ob.matrix_world @ v.co
            hit, normal, index, dist = tree.find_nearest(point)
            if hit is None:
                continue
            signed = (point - hit).dot(normal)
            gaps.append(signed)
            if signed < -tolerance:
                inside += 1
                depths.append(-signed)
        evaluated.to_mesh_clear()
        n = len(gaps) or 1
        out[ob.name] = {
            "vertices": len(gaps), "inside": inside,
            "inside_pct": round(100.0 * inside / n, 2),
            "max_depth_mm": round(max(depths) * 1000, 2) if depths else 0.0,
            "mean_depth_mm": round(sum(depths) / len(depths) * 1000, 2) if depths else 0.0,
            "mean_gap_mm": round(sum(gaps) / n * 1000, 2),
        }
    return {"body": body.name, "tolerance_mm": tolerance * 1000, "meshes": out}


def image_role(name):
    """What a Daz map is for, from its file name: D, SSS, R, SO, NM, SLW."""
    stem = str(name).rsplit("/", 1)[-1].rsplit(".", 1)[0]
    for part in reversed(re.split(r"[_.]", stem)):
        if part.upper() in cfg["role_tokens"]:
            return part.upper()
    return None


def replace_mat_presets(specs):
    """Swap the maps of a material that already has some, for a skin or a hair
    colour, where every channel changes rather than the missing ones.

    The graph is left exactly as the importer built it and only the image each
    texture node points at changes, matched by what the file name says the map
    is for. That is the difference between this and handing the preset to the
    importer's own material loader, which rebuilt the materials and left a
    Genesis 9 body with three of its seven material slots (measured
    2026-09-21).
    """
    report = []
    for spec in specs:
        entry = {"file": spec["file"], "objects": spec["objects"] or "every mesh",
                 "swapped": [], "left_alone": []}
        for ob in bpy.data.objects:
            if ob.type != "MESH" or (spec["objects"] and ob.name not in spec["objects"]):
                continue
            for slot in ob.material_slots:
                mat = slot.material
                if mat is None or mat.node_tree is None:
                    continue
                want = spec["materials"].get(base_material_name(mat.name))
                if not want:
                    continue
                did = {"material": mat.name, "object": ob.name, "maps": {}}
                tree = mat.node_tree
                images = want.get("images") or {}
                for node in mat.node_tree.nodes:
                    if node.type != "TEX_IMAGE" or node.image is None:
                        continue
                    rel = images.get(image_role(node.image.filepath or node.image.name))
                    if not rel:
                        continue
                    new = preset_image(rel, node.image.colorspace_settings.name)
                    if new is node.image:
                        continue
                    did["maps"][image_role(rel)] = [node.image.name, new.name]
                    node.image = new
                bsdf = principled_of(mat)
                base = bsdf.inputs.get("Base Color") if bsdf is not None else None
                if base is not None and not base.is_linked and want.get("colour"):
                    base.default_value = tuple(want["colour"]) + (1.0,)
                    did["colour"] = [round(c, 4) for c in want["colour"]]
                elif base is not None and base.is_linked and want.get("colour") \
                        and tuple(round(c, 3) for c in want["colour"]) != (1.0, 1.0, 1.0):
                    # Daz multiplies a mappable colour channel by its map, so a
                    # hair cap keeps its own scalp texture and takes the
                    # preset's grey with it. Filling in what is missing cannot
                    # do that, because nothing is missing: the map is already
                    # there and it is the wrong colour on its own.
                    source = base.links[0].from_socket
                    mix = tree.nodes.new("ShaderNodeMix")
                    mix.data_type = "RGBA"
                    mix.blend_type = "MULTIPLY"
                    mix.location = (bsdf.location.x - 220, bsdf.location.y + 120)
                    mix.inputs[0].default_value = 1.0
                    tree.links.remove(base.links[0])
                    tree.links.new(source, mix.inputs[6])
                    mix.inputs[7].default_value = tuple(want["colour"]) + (1.0,)
                    tree.links.new(mix.outputs[2], base)
                    did["colour_multiplied"] = [round(c, 4) for c in want["colour"]]
                if did["maps"] or "colour" in did or "colour_multiplied" in did:
                    entry["swapped"].append(did)
                else:
                    entry["left_alone"].append(did)
        report.append(entry)
    return report


def hide_materials(names):
    """Make a material invisible, so part of a mesh drops out of the render.

    A garment is one mesh with several material zones, and a zone is often
    exactly the part someone wants gone: the Wise Wizard's cloak keeps its hood
    in "03CloakHood", separate from the cloak itself. Alpha goes to zero, which
    Cycles renders as nothing at all, and any link into Alpha is taken out
    first so the zero holds.
    """
    wanted = {n.casefold() for n in names}
    done, missing = [], set(wanted)
    for mat in bpy.data.materials:
        key = base_material_name(mat.name).casefold()
        if key not in wanted or mat.node_tree is None:
            continue
        missing.discard(key)
        bsdf = principled_of(mat)
        if bsdf is None or bsdf.inputs.get("Alpha") is None:
            done.append({"material": mat.name, "skipped": "no single Principled BSDF"})
            continue
        alpha = bsdf.inputs["Alpha"]
        unlinked = 0
        for link in list(alpha.links):
            mat.node_tree.links.remove(link)
            unlinked += 1
        alpha.default_value = 0.0
        done.append({"material": mat.name, "alpha": 0.0, "links_removed": unlinked,
                     "objects": sorted(o.name for o in bpy.data.objects
                                       if o.type == "MESH"
                                       and mat.name in [sl.material.name for sl in o.material_slots
                                                        if sl.material])})
    return {"hidden": done, "not_found": sorted(missing)}


def apply_mat_presets(specs):
    """Fill in what a material is missing from the Daz material presets.

    Only what is missing. A material that already has something linked into
    Base Color keeps it, and one that is already see-through is left alone, so
    this adds the maps the anatomy figures arrive without and changes nothing
    on skin the importer already built. Every value comes from the preset file:
    the cutout opacity map becomes the Principled BSDF's Alpha through an RGB
    to BW node, and a flat colour becomes its Base Color.
    """
    report = []
    # What this pass has already written. A value it set itself is not a link,
    # so a later preset would happily write over it: the first preset named
    # wins, which is what makes --mat-preset beat the presets found by looking.
    filled = {"alpha": set(), "colour": set()}
    for spec in specs:
        entry = {"file": spec["file"], "objects": spec["objects"] or "every mesh",
                 "applied": [], "left_alone": [], "unresolved": spec.get("unresolved", [])}
        matched = set()
        for ob in bpy.data.objects:
            if ob.type != "MESH" or (spec["objects"] and ob.name not in spec["objects"]):
                continue
            for slot in ob.material_slots:
                mat = slot.material
                if mat is None or mat.node_tree is None:
                    continue
                want = spec["materials"].get(base_material_name(mat.name))
                if not want:
                    continue
                matched.add(base_material_name(mat.name))
                did = {"material": mat.name, "object": ob.name}
                tree = mat.node_tree
                bsdf = principled_of(mat)
                if bsdf is None:
                    did["skipped"] = "no single Principled BSDF"
                    entry["left_alone"].append(did)
                    continue
                already = transparency_of(mat) or (
                    "set by an earlier preset" if mat.name in filled["alpha"] else None)
                if already:
                    did["transparency_kept"] = already
                elif want.get("alpha_image"):
                    tex = texture_node(tree, preset_image(want["alpha_image"], "Non-Color"),
                                       "Cutout Opacity", bsdf.location.x - 700, bsdf.location.y - 500)
                    grey = tree.nodes.new("ShaderNodeRGBToBW")
                    grey.location = (bsdf.location.x - 380, bsdf.location.y - 500)
                    tree.links.new(tex.outputs["Color"], grey.inputs["Color"])
                    tree.links.new(grey.outputs["Val"], bsdf.inputs["Alpha"])
                    did["alpha_image"] = want["alpha_image"]
                elif want.get("alpha_value", 1.0) < 1.0:
                    bsdf.inputs["Alpha"].default_value = want["alpha_value"]
                    did["alpha_value"] = want["alpha_value"]
                if "alpha_image" in did or "alpha_value" in did:
                    filled["alpha"].add(mat.name)
                # A refractive surface, such as the film of moisture over an
                # eye: opaque white without this, and glass with it.
                transmission = bsdf.inputs.get("Transmission Weight")
                if (want.get("refraction", 0.0) >= cfg["refractive"] and transmission is not None
                        and not transmission.is_linked and transmission.default_value == 0.0
                        and mat.name not in filled["alpha"]):
                    transmission.default_value = want["refraction"]
                    ior = bsdf.inputs.get("IOR")
                    if ior is not None and want.get("ior") and not ior.is_linked:
                        ior.default_value = want["ior"]
                    did["refraction"] = want["refraction"]
                    did["ior"] = want.get("ior")
                base = bsdf.inputs.get("Base Color")
                if mat.name in filled["colour"]:
                    did["colour_kept"] = "set by an earlier preset"
                elif base is None or base.is_linked:
                    did["colour_kept"] = "a link into Base Color"
                elif want.get("colour_layers"):
                    socket = layer_stack(tree, want["colour_layers"],
                                         bsdf.location.x - 1000, bsdf.location.y)
                    if socket is not None:
                        tree.links.new(socket, base)
                        did["colour_layers"] = [l.get("label") for l in want["colour_layers"]]
                elif want.get("colour_image"):
                    tex = texture_node(tree, preset_image(want["colour_image"], "sRGB"),
                                       "Base Color", bsdf.location.x - 700, bsdf.location.y)
                    tree.links.new(tex.outputs["Color"], base)
                    did["colour_image"] = want["colour_image"]
                elif want.get("colour"):
                    base.default_value = tuple(want["colour"]) + (1.0,)
                    did["colour"] = [round(c, 4) for c in want["colour"]]
                if any(k in did for k in ("colour_image", "colour_layers", "colour")):
                    filled["colour"].add(mat.name)
                if any(k in did for k in ("alpha_image", "alpha_value", "colour_image",
                                          "colour_layers", "colour", "refraction")):
                    entry["applied"].append(did)
                else:
                    entry["left_alone"].append(did)
        entry["matched"] = sorted(matched)
        entry["not_matched"] = sorted(set(spec["materials"]) - matched)
        report.append(entry)
    return report


def main_rig(objs):
    rigs = [o for o in objs if o.type == "ARMATURE" and o.parent is None]
    if not rigs:
        raise RuntimeError("the import made no top-level armature")
    return max(rigs, key=lambda o: len(o.data.bones))
'''

SETUP = r'''

try:
    step("read_factory_settings(use_empty=True)",
         lambda: bpy.ops.wm.read_factory_settings(use_empty=True))
    ns_before = set(bpy.app.driver_namespace.keys())
    pkg = "bl_ext." + cfg["repo_module"] + ".import_daz"

    def add_repo():
        bpy.context.preferences.extensions.repos.new(
            name=cfg["repo_module"], module=cfg["repo_module"],
            custom_directory=cfg["repo_dir"], source="USER")
        addon_utils.extensions_refresh(ensure_wheels=False)

    step("add local extension repository", add_repo)

    def enable():
        mod = addon_utils.enable(pkg, default_set=True, handle_error=reraise)
        if mod is None:
            raise RuntimeError(f"addon_utils.enable({pkg!r}) returned None")
        return mod

    step(f"enable {pkg}", enable)
    daz = sys.modules[pkg]
    # Blender drops bl_info from a module it enables as an extension.
    result["bl_info_on_module"] = hasattr(daz, "bl_info")
    result["manifest_version"] = re.search(
        r'^version = "([^"]+)"', open(os.path.join(cfg["repo_dir"], "import_daz", "blender_manifest.toml")).read(),
        re.M).group(1)
    result["build"] = sys.modules[pkg + ".buildnumber"].BUILD
    result["driver_namespace_added"] = sorted(set(bpy.app.driver_namespace.keys()) - ns_before)
    result["operators"] = {op: hasattr(bpy.ops.daz, op) for op in
                           ("easy_import_daz", "import_visemes", "import_facs", "merge_rigs")}
    GS = sys.modules[pkg + ".settings"].GS
    result["settings_dir"] = GS.settingsDir

    lib = cfg["library"]

    dirs = cfg["content_dirs"]
    figure_path = os.path.join(lib, cfg["figure"])

    def check_library():
        missing = [p for d in dirs for p in [d] + [os.path.join(d, s) for s in ("data", "People", "Runtime")]
                   if not os.path.isdir(p)]
        if missing:
            raise FileNotFoundError(f"content directory missing in the container: {missing}")
        if not os.path.isfile(figure_path):
            raise FileNotFoundError(f"figure not found: {figure_path}")

    # With --no-dir-check these two steps are recorded but do not stop the
    # build, to show what the importer does with a wrong content path.
    step("content directory and figure exist", check_library, fatal=cfg["dir_check"])

    def set_dirs():
        daz.set_global_setting("contentDirs", dirs)
        daz.set_global_setting("mdlDirs", [])
        daz.set_global_setting("cloudDirs", [])
        daz.set_global_setting("verbosity", cfg["verbosity"])
        roots = daz.get_root_paths()
        result["get_root_paths"] = roots
        found = daz.get_absolute_paths(["/" + cfg["figure"]])
        result["get_absolute_paths_figure"] = found
        if roots != dirs:
            raise RuntimeError(f"get_root_paths() returned {roots}, expected {dirs}")
        if not found:
            raise RuntimeError(f"get_absolute_paths() did not resolve /{cfg['figure']}")

    step("set_global_setting('contentDirs') and resolve the figure", set_dirs, fatal=cfg["dir_check"])
    figure_abs = figure_path
    daz.set_silent_mode(True)
    result["silent_mode_after_set"] = daz.get_silent_mode()

    new = step(f"easy_import_daz {os.path.basename(figure_abs)}", lambda: import_duf(figure_abs))
    result["figure_objects"] = [[o.name, o.type] for o in new]
    rig = step("find the body rig", lambda: main_rig(new))
    result["body_rig"] = rig.name
    result["silent_mode_after_easy_import"] = "reset to True by the probe"
    result["survey_after_figure"] = survey()

    # The anatomy figures a Daz Studio post-load script would add.
    anatomy = []
    for rel in cfg["anatomy"]:
        absp = os.path.join(lib, rel)
        name = os.path.splitext(os.path.basename(rel))[0]

        def one(absp=absp):
            if not os.path.isfile(absp):
                raise FileNotFoundError(f"not in the library: {absp}")
            return import_duf(absp)

        objs = step(f"easy_import_daz anatomy {name}", one, fatal=False)
        if objs:
            anatomy.append((name, objs))
    result["anatomy_objects"] = {n: [[o.name, o.type] for o in objs] for n, objs in anatomy}
    # The figure's own meshes: its body and the eyes, mouth, lashes, tear and
    # eyebrows that a post-load script brings with it. What --hide-figure hides.
    figure_meshes = {o.name for _, objs in anatomy for o in objs if o.type == "MESH"}
    figure_meshes.update(o.name for o in new if o.type == "MESH")

    subrigs = [o for _, objs in anatomy for o in objs if o.type == "ARMATURE" and o.parent is None]
    if subrigs:
        def merge():
            for sub in subrigs:
                wm = sub.matrix_world.copy()
                sub.parent = rig
                sub.matrix_world = wm
            activate(rig)
            for sub in subrigs:
                sub.select_set(True)
            daz.set_silent_mode(True)
            before = len(rig.data.bones)
            ret = bpy.ops.daz.merge_rigs(useOnlySelected=True)
            daz.set_silent_mode(True)
            left = [o.name for o in bpy.data.objects if o.type == "ARMATURE" and o != rig]
            if left:
                raise RuntimeError(f"merge_rigs returned {sorted(ret)} and left armatures {left}; "
                                   f"get_error_message(): {daz.get_error_message()!r}")
            return {"bones_before": before, "bones_after": len(rig.data.bones)}

        result["merge_rigs"] = step(f"parent {len(subrigs)} anatomy rigs and merge_rigs", merge, fatal=False)

'''

BUILD_TAIL = r'''
    def import_morphs(op_name):
        def run():
            activate(rig)
            daz.set_silent_mode(True)
            before = armature_props(rig)
            meshes_before = {o.name: len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0
                             for o in bpy.data.objects if o.type == "MESH"}
            ret = getattr(bpy.ops.daz, op_name)()
            daz.set_silent_mode(True)
            after = armature_props(rig)
            added = {k: len(set(after.get(k, [])) - set(before.get(k, []))) for k in ("object", "data")}
            keys_added = {o.name: (len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0)
                          - meshes_before.get(o.name, 0)
                          for o in bpy.data.objects if o.type == "MESH"}
            out = {"returned": sorted(ret), "properties_added": added,
                   "shape_keys_added": keys_added,
                   "get_error_message": daz.get_error_message()}
            if not any(added.values()) and not any(keys_added.values()):
                raise RuntimeError(f"bpy.ops.daz.{op_name}() returned {sorted(ret)} and added no "
                                   f"property or shape key; get_error_message(): "
                                   f"{daz.get_error_message()!r}")
            return out
        return run

    if cfg["visemes"]:
        result["import_visemes"] = step("bpy.ops.daz.import_visemes()", import_morphs("import_visemes"), fatal=False)
    if cfg["facs"]:
        result["import_facs"] = step("bpy.ops.daz.import_facs()", import_morphs("import_facs"), fatal=False)

    if cfg["mat_presets"]:
        result["mat_presets"] = step(
            "apply %d Daz material preset(s)" % len(cfg["mat_presets"]),
            lambda: apply_mat_presets(cfg["mat_presets"]), fatal=False)

    # After the fill, not before: the importer leaves a skin's Base Color with
    # nothing linked into it, so the map a swap points elsewhere is one the
    # fill pass has just added.
    if cfg["mat_replaces"]:
        result["mat_replaces"] = step(
            "swap the textures of %d Daz material preset(s)" % len(cfg["mat_replaces"]),
            lambda: replace_mat_presets(cfg["mat_replaces"]), fatal=False)

    if cfg["fit_report"]:
        def measure_fit():
            meshes = [o for o in bpy.data.objects if o.type == "MESH"]
            worn = body_of(rig, [o for o in meshes if o.find_armature() == rig]) or (
                meshes[0] if meshes else None)
            if worn is None:
                raise RuntimeError("no mesh to measure against")
            return fit_report(worn, meshes)
        result["fit"] = step("measure how each mesh sits on the body", measure_fit, fatal=False)

    final = survey()
    result["survey"] = final
    arm = final["armatures"].get(rig.name, {})
    names = set()
    for v in arm.get("matching_properties", {}).values():
        names.update(v)
    result["viseme_props"] = {}
    for v in cfg["visemes_list"]:
        hits = sorted(n for n in names if re.fullmatch(rf"(facs_ctrl_v|ectrlv|ctrl_v|v){v}", n, re.I))
        if hits:
            result["viseme_props"][v] = hits[0]
    result["viseme_props_owner"] = {
        n: ("object" if n in rig.keys() else "data" if n in rig.data.keys() else None)
        for n in result["viseme_props"].values()}

    def strip_textures():
        cleared = 0
        trees = [m.node_tree for m in bpy.data.materials if m.node_tree] + list(bpy.data.node_groups)
        for tree in trees:
            for node in tree.nodes:
                if node.type == "TEX_IMAGE" and node.image is not None:
                    node.image = None
                    cleared += 1
        images = len(bpy.data.images)
        for img in list(bpy.data.images):
            if img.users == 0:
                bpy.data.images.remove(img)
        return {"image_nodes_cleared": cleared, "images_before": images, "images_after": len(bpy.data.images)}

    if cfg["no_textures"]:
        result["no_textures"] = step("clear image textures", strip_textures, fatal=False)

    def subdivision_off():
        mods = [m for o in bpy.data.objects if o.type == "MESH" for m in o.modifiers if m.type == "SUBSURF"]
        levels = sorted({(m.levels, m.render_levels) for m in mods})
        for m in mods:
            m.show_viewport = False
            m.show_render = False
        return {"subsurf_modifiers": len(mods), "levels_viewport_render": levels}

    if cfg["subdivision"] == "off":
        result["subdivision_off"] = step("switch off Subsurf modifiers", subdivision_off, fatal=False)

    def save():
        bpy.context.preferences.filepaths.save_version = 0
        ret = bpy.ops.wm.save_as_mainfile(filepath=cfg["blend"], check_existing=False)
        if "FINISHED" not in ret:
            raise RuntimeError(f"save_as_mainfile returned {sorted(ret)}")

    step("save .blend", save)
'''

EPILOGUE = r'''except Stop:
    pass
except Exception:
    result["stopped_at"] = result["stopped_at"] or "outside a step"
    result["fatal"] = traceback.format_exc()[-3000:]

result["blender_seconds"] = round(time.time() - T0, 2)
result["peak_rss_mb"] = peak_rss_mb()
checkpoint()
sys.stdout.flush()
os.dup2(_saved_stdout, 1)
print("DAZ_BUILD " + json.dumps(result), flush=True)
sys.stderr.flush()
# Leave directly: an add-on or a Python-expression driver can leave the bpy
# module hanging at interpreter exit (seen with MPFB and render_sheet.py).
os._exit(0)
'''

SCENE_TAIL = r'''
    import numpy as np

    def numeric_props(ob):
        """Every float or int custom property on the rig object and its data,
        with the range the importer gave it."""
        out = {}
        for owner, label in ((ob, "object"), (ob.data, "data")):
            for k in owner.keys():
                v = owner[k]
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    continue
                try:
                    ui = owner.id_properties_ui(k).as_dict()
                except (TypeError, KeyError, ValueError):
                    ui = {}
                out[k] = {"owner": label, "value": round(float(v), 6),
                          "min": ui.get("min"), "max": ui.get("max"),
                          "soft_min": ui.get("soft_min"), "soft_max": ui.get("soft_max"),
                          "default": ui.get("default")}
        return out

    def prop_owner(name):
        for owner in (rig, rig.data):
            if name in owner.keys():
                return owner
        return None

    def shape_key_counts():
        return {o.name: (len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0)
                for o in bpy.data.objects if o.type == "MESH"}

    def coords(ob):
        """The evaluated mesh's vertex positions in world space, metres."""
        dg = bpy.context.evaluated_depsgraph_get()
        eob = ob.evaluated_get(dg)
        me = eob.to_mesh()
        n = len(me.vertices)
        co = np.empty(n * 3, dtype=np.float64)
        me.vertices.foreach_get("co", co)
        eob.to_mesh_clear()
        co = co.reshape(n, 3)
        m = np.array(ob.matrix_world.to_4x4())
        return co @ m[:3, :3].T + m[:3, 3]

    def moved(before, after):
        if before.shape != after.shape:
            return {"same_vertex_count": False,
                    "vertices_before": int(before.shape[0]), "vertices_after": int(after.shape[0])}
        d = np.linalg.norm(after - before, axis=1)
        return {"vertices": int(before.shape[0]),
                "moved": int((d > 1e-5).sum()),
                "max_mm": round(float(d.max()) * 1000.0, 2) if d.size else 0.0,
                "mean_mm": round(float(d.mean()) * 1000.0, 3) if d.size else 0.0}

    def rig_meshes():
        """Meshes the rig deforms, by find_armature(), which reads the armature
        modifier first and then the parent."""
        return [o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() == rig]

    def mesh_facts(ob):
        arm = [[m.name, m.object.name if m.object else None] for m in ob.modifiers if m.type == "ARMATURE"]
        return {"vertices": len(ob.data.vertices), "faces": len(ob.data.polygons),
                "shape_keys": len(ob.data.shape_keys.key_blocks) if ob.data.shape_keys else 0,
                "parent": ob.parent.name if ob.parent else None,
                "parent_type": ob.parent_type if ob.parent else None,
                "armature_modifiers": arm,
                "follows_rig": ob.find_armature() == rig,
                "vertex_groups": len(ob.vertex_groups),
                "vertex_group_names": [g.name for g in ob.vertex_groups][:12],
                "materials": [s.material.name for s in ob.material_slots if s.material],
                "modifiers": [[m.name, m.type] for m in ob.modifiers]}

    def update():
        # Writing a custom property does not tag the rig on its own, so the
        # drivers that read it are not re-evaluated without update_tag().
        rig.update_tag()
        rig.data.update_tag()
        for ob in bpy.data.objects:
            ob.update_tag()
        bpy.context.view_layer.update()

    def body_mesh():
        """The figure's own mesh, which the importer names after the figure.

        Not the largest one: the fibre eyebrows some characters load carry more
        vertices than the body (26,376 against Fabrice's 25,182), and a hair
        mesh carries far more, so picking by size handed transfer_shapekeys a
        mesh with no shape keys and its poll refused the call.
        """
        meshes = rig_meshes()
        if not meshes:
            return None
        named = [o for o in meshes if o.name == f"{rig.name} Mesh" or o.name.startswith(rig.name)]
        return max(named or meshes,
                   key=lambda o: (len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0,
                                  len(o.data.vertices)))

    body = body_mesh()
    result["body_mesh"] = body.name if body else None

    # ---------------------------------------------------------------- morphs
    result["morph_sets"] = {}
    for label, opname in cfg["morph_sets"]:
        def load_set(opname=opname):
            activate(rig)
            daz.set_silent_mode(True)
            before, keys_before = armature_props(rig), shape_key_counts()
            ret = getattr(bpy.ops.daz, opname)()
            daz.set_silent_mode(True)
            after, keys_after = armature_props(rig), shape_key_counts()
            added = {k: sorted(set(after.get(k, [])) - set(before.get(k, []))) for k in ("object", "data")}
            keys = {k: v - keys_before.get(k, 0) for k, v in keys_after.items() if v - keys_before.get(k, 0)}
            return {"operator": f"bpy.ops.daz.{opname}()", "returned": sorted(ret),
                    "properties_added": {k: len(v) for k, v in added.items()},
                    "first_properties": added["object"][:6],
                    "shape_keys_added": keys,
                    "get_error_message": daz.get_error_message()}
        result["morph_sets"][label] = step(f"bpy.ops.daz.{opname}()", load_set, fatal=False)

    if cfg["custom"]:
        def load_custom():
            activate(rig)
            daz.set_silent_mode(True)
            before, keys_before = armature_props(rig), shape_key_counts()
            ret = bpy.ops.daz.import_custom_morphs(
                directory=cfg["custom"]["dir"],
                files=[{"name": n} for n in cfg["custom"]["files"]],
                category=cfg["custom"]["category"],
                bodypart=cfg["custom"]["bodypart"],
                onDrivers="RIG")
            daz.set_silent_mode(True)
            after, keys_after = armature_props(rig), shape_key_counts()
            added = {k: sorted(set(after.get(k, [])) - set(before.get(k, []))) for k in ("object", "data")}
            keys = {k: v - keys_before.get(k, 0) for k, v in keys_after.items() if v - keys_before.get(k, 0)}
            # A morph already loaded adds nothing, and that is not a failure: a
            # standard set pulls in morphs the named files also carry, and on
            # Laura the "body" set had already brought in all 18 Proportion
            # dials before this ran (2026-09-21).
            here = set(after.get("object", [])) | set(after.get("data", []))
            present = [n for n in (os.path.splitext(f)[0] for f in cfg["custom"]["files"])
                       if n in here]
            if not any(added.values()) and not keys and not present:
                raise RuntimeError("bpy.ops.daz.import_custom_morphs() returned "
                                   f"{sorted(ret)} and added no property or shape key, and none "
                                   "of the files named is a property on the rig; "
                                   f"get_error_message(): {daz.get_error_message()!r}")
            return {"operator": "bpy.ops.daz.import_custom_morphs()", "returned": sorted(ret),
                    "files": len(cfg["custom"]["files"]),
                    "already_present": present,
                    "category": cfg["custom"]["category"],
                    "properties_added": {k: len(v) for k, v in added.items()},
                    "property_names": added["object"] + added["data"],
                    "shape_keys_added": keys,
                    "get_error_message": daz.get_error_message()}
        result["custom_morphs"] = step(
            f"bpy.ops.daz.import_custom_morphs() {cfg['custom']['category']}", load_custom, fatal=False)

    if cfg["facs"]:
        def load_facs():
            activate(rig)
            daz.set_silent_mode(True)
            before = armature_props(rig)
            ret = bpy.ops.daz.import_facs()
            daz.set_silent_mode(True)
            after = armature_props(rig)
            added = {k: len(set(after.get(k, [])) - set(before.get(k, []))) for k in ("object", "data")}
            if not any(added.values()):
                raise RuntimeError(f"bpy.ops.daz.import_facs() returned {sorted(ret)} and added no "
                                   f"property; get_error_message(): {daz.get_error_message()!r}")
            return {"returned": sorted(ret), "properties_added": added,
                    "get_error_message": daz.get_error_message()}
        result["import_facs"] = step("bpy.ops.daz.import_facs()", load_facs, fatal=False)

    step("list rig properties and their ranges", lambda: result.update(
        {"rig_properties": numeric_props(rig)}), fatal=False)

    def subdivision_off():
        mods = [m for o in bpy.data.objects if o.type == "MESH" for m in o.modifiers if m.type == "SUBSURF"]
        levels = sorted({(m.levels, m.render_levels) for m in mods})
        for m in mods:
            m.show_viewport = False
            m.show_render = False
        return {"subsurf_modifiers": len(mods), "levels_viewport_render": levels}

    if cfg["subdivision"] == "off":
        result["subdivision_off"] = step("switch off Subsurf modifiers", subdivision_off, fatal=False)

    # ------------------------------------------------------------ set sliders
    result["dials"] = {}
    for name, value in cfg["set"]:
        def set_one(name=name, value=value):
            owner = prop_owner(name)
            if owner is None:
                raise KeyError(f"no property {name!r} on {rig.name} or {rig.name}.data; "
                               f"{len(numeric_props(rig))} numeric properties exist")
            meshes = rig_meshes()
            update()
            before = {ob.name: coords(ob) for ob in meshes}
            was = float(owner[name])
            owner[name] = float(value)
            update()
            after = {ob.name: coords(ob) for ob in meshes}
            keys = {}
            for ob in meshes:
                if ob.data.shape_keys:
                    keys[ob.name] = sum(1 for k in ob.data.shape_keys.key_blocks if abs(k.value) > 1e-4)
            return {"property": name, "owner": "object" if owner is rig else "data",
                    "from": was, "to": float(value),
                    "moved": {n: moved(before[n], after[n]) for n in before},
                    "shape_keys_nonzero": keys}
        result["dials"][f"{name}={value}"] = step(f"set {name} = {value}", set_one, fatal=False)

    # -------------------------------------------------------------- wearables
    result["wearables"] = {}
    worn_meshes = set()
    for rel, absp in cfg["wear"]:
        name = os.path.splitext(os.path.basename(absp))[0]

        def wear(absp=absp, name=name):
            entry = {"file": name}
            activate(rig)
            objs = import_duf(absp)
            entry["objects"] = [[o.name, o.type] for o in objs]
            meshes = [o for o in objs if o.type == "MESH"]
            rigs = [o for o in objs if o.type == "ARMATURE"]
            entry["before_merge"] = {o.name: mesh_facts(o) for o in meshes}
            entry["own_rigs"] = {o.name: len(o.data.bones) for o in rigs}
            if rigs:
                bones_before = len(rig.data.bones)
                for sub in rigs:
                    wm = sub.matrix_world.copy()
                    sub.parent = rig
                    sub.matrix_world = wm
                activate(rig)
                for sub in rigs:
                    sub.select_set(True)
                daz.set_silent_mode(True)
                ret = bpy.ops.daz.merge_rigs(useOnlySelected=True)
                daz.set_silent_mode(True)
                entry["merge_rigs"] = {
                    "returned": sorted(ret), "bones_before": bones_before,
                    "bones_after": len(rig.data.bones),
                    "armatures_left": [o.name for o in bpy.data.objects
                                       if o.type == "ARMATURE" and o != rig],
                    "get_error_message": daz.get_error_message()}
            entry["after_merge"] = {}
            for o in meshes:
                try:
                    entry["after_merge"][o.name] = mesh_facts(o)
                except ReferenceError:
                    entry["after_merge"][o.name] = {"deleted_by_the_importer": True}
            return entry
        result["wearables"][name] = step(f"easy_import_daz wearable {name}", wear, fatal=False)
        entry = result["wearables"][name] or {}
        worn_meshes.update(n for n, kind in entry.get("objects", []) if kind == "MESH")
        result["worn_meshes"] = sorted(worn_meshes)

    # Before anything else is measured. Every later step reads the evaluated
    # mesh, so a wearable whose own Subsurf is still on would have its dial and
    # pose counts taken on a subdivided mesh while `survey` counts its cage,
    # and one report would carry two counts for the same mesh.
    if cfg["subdivision"] == "off" and cfg["wear"]:
        result["subdivision_off_wearables"] = step(
            "switch off the wearables' Subsurf modifiers", subdivision_off, fatal=False)

    if cfg["wear"] and cfg["transfer"] and body is not None:
        def transfer():
            targets = [o for o in rig_meshes() if o != body and o.name not in cfg["skip_transfer"]]
            names = [o.name for o in targets]
            before = {o.name: (len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0)
                      for o in targets}
            activate(body)
            for o in targets:
                o.select_set(True)
            daz.set_silent_mode(True)
            ret = bpy.ops.daz.transfer_shapekeys(transferMethod="NEAREST")
            daz.set_silent_mode(True)
            after = {o.name: (len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0)
                     for o in targets}
            return {"operator": "bpy.ops.daz.transfer_shapekeys(transferMethod='NEAREST')",
                    "returned": sorted(ret), "targets": names,
                    "shape_keys_added": {n: after[n] - before[n] for n in after},
                    "get_error_message": daz.get_error_message()}
        result["transfer_shapekeys"] = step("bpy.ops.daz.transfer_shapekeys()", transfer, fatal=False)

    obj_meshes = set()
    if cfg["wear_objs"]:
        result["wear_objs"] = step(
            "import %d Wavefront OBJ(s)" % len(cfg["wear_objs"]),
            lambda: wear_objs(cfg["wear_objs"], rig, body), fatal=False)
        for entry in (result["wear_objs"] or {}).values():
            if not entry.get("skipped"):
                obj_meshes.update(n for n, kind in entry.get("objects", []) if kind == "MESH")
        result["obj_meshes"] = sorted(obj_meshes)

    # a dial set after the clothes are on: does the outfit follow the shape?
    for name, value in cfg["set_after"]:
        def set_after(name=name, value=value):
            owner = prop_owner(name)
            if owner is None:
                raise KeyError(f"no property {name!r} on {rig.name} or {rig.name}.data")
            meshes = rig_meshes()
            update()
            before = {ob.name: coords(ob) for ob in meshes}
            was = float(owner[name])
            owner[name] = float(value)
            update()
            after = {ob.name: coords(ob) for ob in meshes}
            return {"property": name, "from": was, "to": float(value),
                    "moved": {n: moved(before[n], after[n]) for n in before}}
        result["dials"][f"{name}={value} dressed"] = step(
            f"set {name} = {value} with the outfit on", set_after, fatal=False)

    if cfg["offsets"]:
        def move_them():
            if cfg["pose"]:
                raise RuntimeError("a pose is applied, and this edits the rest shape")
            return offset_meshes({n: v for n, v in cfg["offsets"]})
        result["offsets"] = step("move %d worn mesh(es)" % len(cfg["offsets"]),
                                 move_them, fatal=False)

    if cfg["declip"] > 0 and (worn_meshes or obj_meshes):
        def push_out():
            meshes = [o for o in bpy.data.objects if o.type == "MESH"]
            body_now = body_of(rig, [o for o in meshes if o.find_armature() == rig])
            if body_now is None:
                raise RuntimeError("no body mesh to push away from")
            if cfg["pose"]:
                raise RuntimeError("a pose is applied, and this edits the rest shape")
            # Only what the rig deforms. A bone-parented prop, a staff or a
            # brooch, is placed rather than fitted, and pushing its vertices
            # to the body would bend it: the Wise Wizard's brooch had all
            # 4,560 of them moved before this rule (2026-09-21).
            # An imported OBJ is in too: it is not a rigid prop but a sheet of
            # hair or cloth modelled around a sphere, and bending it onto the
            # body it sits against is the whole point.  On Genesis 9 the hair
            # grown for a 9.5 cm scalp sank 18.04 mm into the neck before this
            # (2026-09-22).
            wearing = [o for o in meshes
                       if (o.name in worn_meshes and o.find_armature() == rig)
                       or o.name in obj_meshes]
            before = fit_report(body_now, wearing)
            done = declip(body_now, wearing, cfg["declip"] / 1000.0, cfg["declip_max_verts"],
                          set(cfg["declip_skip"]), cfg["declip_max_push"] / 1000.0)
            done["inside_before"] = {k: v["inside_pct"] for k, v in before["meshes"].items()}
            after = fit_report(body_now, wearing)
            done["inside_after"] = {k: v["inside_pct"] for k, v in after["meshes"].items()}
            return done
        result["declip"] = step("push the worn meshes out of the body", push_out, fatal=False)

    # ------------------------------------------------------------------ pose
    if cfg["pose"]:
        def pose():
            meshes = rig_meshes()
            before_co = {ob.name: coords(ob) for ob in meshes}
            before = {pb.name: pb.matrix_basis.copy() for pb in rig.pose.bones}
            activate(rig)
            daz.set_silent_mode(True)
            ret = bpy.ops.daz.import_pose(
                directory=os.path.dirname(cfg["pose"]),
                files=[{"name": os.path.basename(cfg["pose"])}],
                affectMorphs=cfg["pose_affect_morphs"])
            daz.set_silent_mode(True)
            update()
            after_co = {ob.name: coords(ob) for ob in meshes}
            changed = [pb.name for pb in rig.pose.bones
                       if any(abs(a - b) > 1e-6 for row_a, row_b in zip(pb.matrix_basis, before[pb.name])
                              for a, b in zip(row_a, row_b))]
            rotated = [pb.name for pb in rig.pose.bones
                       if pb.matrix_basis.to_quaternion().angle > 1e-4]
            return {"operator": "bpy.ops.daz.import_pose()", "returned": sorted(ret),
                    "affectMorphs": cfg["pose_affect_morphs"],
                    "file": os.path.basename(cfg["pose"]),
                    "bones": len(rig.pose.bones),
                    "bones_moved": len(changed), "bones_rotated": len(rotated),
                    "bones_moved_names": sorted(changed),
                    "keyframes": (len(rig.animation_data.action.fcurves)
                                  if rig.animation_data and rig.animation_data.action else 0),
                    "moved": {n: moved(before_co[n], after_co[n]) for n in before_co},
                    "get_error_message": daz.get_error_message()}
        result["pose"] = step(f"bpy.ops.daz.import_pose() {os.path.basename(cfg['pose'])}",
                              pose, fatal=False)

    if cfg["mat_presets"]:
        result["mat_presets"] = step(
            "apply %d Daz material preset(s)" % len(cfg["mat_presets"]),
            lambda: apply_mat_presets(cfg["mat_presets"]), fatal=False)

    # After the fill, not before: the importer leaves a skin's Base Color with
    # nothing linked into it, so the map a swap points elsewhere is one the
    # fill pass has just added.
    if cfg["mat_replaces"]:
        result["mat_replaces"] = step(
            "swap the textures of %d Daz material preset(s)" % len(cfg["mat_replaces"]),
            lambda: replace_mat_presets(cfg["mat_replaces"]), fatal=False)

    if cfg["fit_report"]:
        def measure_fit():
            meshes = [o for o in bpy.data.objects if o.type == "MESH"]
            worn = body_of(rig, [o for o in meshes if o.find_armature() == rig]) or (
                meshes[0] if meshes else None)
            if worn is None:
                raise RuntimeError("no mesh to measure against")
            return fit_report(worn, meshes)
        result["fit"] = step("measure how each mesh sits on the body", measure_fit, fatal=False)

    if cfg["hide_materials"]:
        result["hide_materials"] = step(
            "hide %d material zone(s)" % len(cfg["hide_materials"]),
            lambda: hide_materials(cfg["hide_materials"]), fatal=False)

    if cfg["hide"] or cfg["hide_figure"]:
        def hide():
            """Keep a mesh out of the render without deleting it.

            A figure under a costume is the case this exists for: hide the body
            and its eyes, mouth and lashes and what is left is the robes and
            whatever the costume puts where a face was. The meshes stay in the
            file, so the clothes still fit what they were fitted to, and
            render_sheet.py frames only what it can see.
            """
            wanted = set(cfg["hide"])
            if cfg["hide_figure"]:
                wanted |= set(figure_meshes)
            hidden, missing = [], sorted(n for n in cfg["hide"]
                                         if n not in {o.name for o in bpy.data.objects})
            for ob in bpy.data.objects:
                if ob.type == "MESH" and ob.name in wanted:
                    ob.hide_render = True
                    ob.hide_viewport = True
                    hidden.append(ob.name)
            return {"hidden": sorted(hidden), "not_found": missing,
                    "figure_meshes": sorted(figure_meshes) if cfg["hide_figure"] else [],
                    "still_rendered": sorted(o.name for o in bpy.data.objects
                                             if o.type == "MESH" and not o.hide_render)}
        result["hide"] = step("hide meshes from the render", hide, fatal=False)

    final = survey()
    result["survey"] = final
    arm = final["armatures"].get(rig.name, {})
    names = set()
    for v in arm.get("matching_properties", {}).values():
        names.update(v)
    result["viseme_props"] = {}
    for v in cfg["visemes_list"]:
        hits = sorted(n for n in names if re.fullmatch(rf"(facs_ctrl_v|ectrlv|ctrl_v|v){v}", n, re.I))
        if hits:
            result["viseme_props"][v] = hits[0]
    result["viseme_props_owner"] = {
        n: ("object" if n in rig.keys() else "data" if n in rig.data.keys() else None)
        for n in result["viseme_props"].values()}

    def save():
        bpy.context.preferences.filepaths.save_version = 0
        ret = bpy.ops.wm.save_as_mainfile(filepath=cfg["blend"], check_existing=False)
        if "FINISHED" not in ret:
            raise RuntimeError(f"save_as_mainfile returned {sorted(ret)}")

    step("save .blend", save)
'''

BUILD_SCRIPT = PRELUDE + SETUP + BUILD_TAIL + EPILOGUE
SCENE_SCRIPT = PRELUDE + SETUP + SCENE_TAIL + EPILOGUE

# A .blend opened with no DAZ add-on: what survives the save, and does the
# rig still carry the meshes?
VERIFY_SCRIPT = r'''
import json, os, resource, signal, sys, time
cfg = json.loads(sys.argv[-1])
signal.signal(signal.SIGALRM, signal.SIG_DFL)
signal.alarm(cfg["timeout"])
os.makedirs(cfg["user_resources"], exist_ok=True)
os.environ["BLENDER_USER_RESOURCES"] = cfg["user_resources"]
import bpy
import numpy as np
from mathutils import Matrix

T0 = time.time()
out = {}
bpy.ops.wm.open_mainfile(filepath=cfg["blend"], load_ui=False)
out["daz_addons_enabled"] = [a.module for a in bpy.context.preferences.addons if "daz" in a.module]
out["scripts_auto_execute"] = bpy.context.preferences.filepaths.use_scripts_auto_execute
rig = bpy.data.objects.get(cfg["rig"])
if rig is None or rig.type != "ARMATURE":
    print("DAZ_VERIFY " + json.dumps({"error": f"no armature named {cfg['rig']!r}"}), flush=True)
    os._exit(0)


def coords(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    eob = ob.evaluated_get(dg)
    me = eob.to_mesh()
    n = len(me.vertices)
    co = np.empty(n * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    eob.to_mesh_clear()
    co = co.reshape(n, 3)
    m = np.array(ob.matrix_world.to_4x4())
    return co @ m[:3, :3].T + m[:3, 3]


def moved(before, after):
    d = np.linalg.norm(after - before, axis=1)
    return {"vertices": int(before.shape[0]), "moved": int((d > 1e-5).sum()),
            "max_mm": round(float(d.max()) * 1000.0, 2) if d.size else 0.0}


def update():
    rig.update_tag()
    rig.data.update_tag()
    for ob in bpy.data.objects:
        ob.update_tag()
    bpy.context.view_layer.update()


meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() == rig]
out["rig"] = {"name": rig.name, "bones": len(rig.data.bones),
              "pose_bones_moved": sum(1 for pb in rig.pose.bones
                                      if pb.matrix_basis != Matrix.Identity(4)),
              "object_properties": len(rig.keys()), "data_properties": len(rig.data.keys()),
              "drivers": (len(rig.animation_data.drivers) if rig.animation_data else 0)
                         + (len(rig.data.animation_data.drivers) if rig.data.animation_data else 0)}
out["meshes"] = {o.name: {"vertices": len(o.data.vertices),
                          "shape_keys": len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0,
                          "shape_keys_nonzero": (sum(1 for k in o.data.shape_keys.key_blocks
                                                     if abs(k.value) > 1e-4)
                                                 if o.data.shape_keys else 0),
                          "armature_modifier": [m.object.name for m in o.modifiers
                                                if m.type == "ARMATURE" and m.object],
                          "parent": o.parent.name if o.parent else None}
                 for o in meshes}
out["props"] = {name: (rig[name] if name in rig.keys() else
                       rig.data[name] if name in rig.data.keys() else None)
                for name in cfg["props"]}

posed = {o.name: coords(o) for o in meshes}
for pb in rig.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
update()
rest = {o.name: coords(o) for o in meshes}
out["pose_cleared"] = {n: moved(rest[n], posed[n]) for n in posed}

for name in cfg["props"]:
    for owner in (rig, rig.data):
        if name in owner.keys():
            owner[name] = 0.0
update()
zeroed = {o.name: coords(o) for o in meshes}
out["props_zeroed"] = {n: moved(zeroed[n], rest[n]) for n in rest}
out["seconds"] = round(time.time() - T0, 2)
out["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
print("DAZ_VERIFY " + json.dumps(out), flush=True)
sys.stdout.flush()
os._exit(0)
'''

RENDER_SCRIPT = r'''
import json, os, resource, signal, sys, time
cfg = json.loads(sys.argv[-1])
signal.signal(signal.SIGALRM, signal.SIG_DFL)
signal.alarm(cfg["timeout"])
os.makedirs(cfg["user_resources"], exist_ok=True)
os.environ["BLENDER_USER_RESOURCES"] = cfg["user_resources"]
import bpy, math
import numpy as np
from mathutils import Vector, Euler

t0 = time.time()
os.makedirs(cfg["frames_dir"], exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=cfg["blend"], load_ui=False)
enabled = [a.module for a in bpy.context.preferences.addons if "daz" in a.module]
auto_exec = bpy.context.preferences.filepaths.use_scripts_auto_execute

rig = bpy.data.objects.get(cfg["rig"])
if rig is None or rig.type != "ARMATURE":
    raise SystemExit(f"no armature named {cfg['rig']!r} in {cfg['blend']}")
props = cfg["props"]           # viseme -> property name


def owner_of(name):
    for owner in (rig, rig.data):
        if name in owner.keys():
            return owner
    return None


owners = {v: owner_of(p) for v, p in props.items()}
missing = sorted(v for v, o in owners.items() if o is None)
# Motion and framing are measured over every viseme the rig has; --only
# narrows what is rendered, not what the framing is taken from.
avail = [v for v in cfg["visemes"] if owners.get(v) is not None]
order = [None] + [v for v in avail if not cfg["only"] or v in cfg["only"]]
meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render]
# The body is the mesh the viseme drivers move. A dressed figure can carry a
# hair or clothing mesh with more vertices than the body, so the mesh named in
# the report wins, then the one with the most shape keys, then the largest.
own = [o for o in meshes if o.parent == rig]
body = next((o for o in own if o.name == cfg.get("body_mesh")), None)
if body is None:
    body = max(own, key=lambda o: (len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0,
                                   len(o.data.vertices)), default=None)
if body is None:
    raise SystemExit("no mesh parented to " + rig.name)
mouth = next((o for o in meshes if "mouth" in o.name.lower()), None)

# Diffeomorphic gives each figure mesh a Subsurf modifier. Motion and framing
# are measured on the cage, with every Subsurf switched off; --subdivision
# decides whether renders use the file's own levels.
subsurfs = [(m, m.show_viewport, m.show_render) for o in meshes for m in o.modifiers if m.type == "SUBSURF"]
subsurf_levels = sorted({(m.levels, m.render_levels) for m, _, _ in subsurfs})
for m, _, _ in subsurfs:
    m.show_viewport = False

if cfg["clay"]:
    clay = bpy.data.materials.new("probe_clay")
    clay.use_nodes = True
    bsdf = clay.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = tuple(cfg["clay_color"]) + (1.0,)
    bsdf.inputs["Roughness"].default_value = 0.65
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.3
    for o in meshes:
        o.data.materials.clear()
        o.data.materials.append(clay)

scene = bpy.context.scene
for o in scene.objects:
    if o.type in ("LIGHT", "CAMERA", "LIGHT_PROBE"):
        o.hide_render = True
scene.render.use_compositing = False
scene.render.use_sequencer = False


def set_pose(v):
    for vv, owner in owners.items():
        if owner is not None:
            owner[props[vv]] = 0.0
            owner.update_tag()
    if v is not None:
        owners[v][props[v]] = 1.0
        owners[v].update_tag()
    bpy.context.view_layer.update()


def positions(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    co = co.reshape(-1, 3)
    m = np.array(ev.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3]


pose_bones = list(rig.pose.bones)


def bone_matrices():
    """Armature-space matrices, and the bones' own pose channels (matrix_basis)."""
    return (np.array([np.array(pb.matrix) for pb in pose_bones]),
            np.array([np.array(pb.matrix_basis) for pb in pose_bones]))


def classify_bones(now, before):
    """Which bones moved in armature space, and why: the importer's (drv)
    helpers (with those whose own channels changed), Daz bones whose own
    channels changed, Daz bones with a constraint aimed at a moving (drv)
    helper, and Daz bones only carried along by a moving parent."""
    moved = np.abs(now[0] - before[0]).max(axis=(1, 2)) > 1e-6
    posed = np.abs(now[1] - before[1]).max(axis=(1, 2)) > 1e-6
    helpers = {pb.name for pb, m in zip(pose_bones, moved) if m and "(drv)" in pb.name}
    out = {"helpers": [], "helpers_posed": [], "posed": [], "follow_helper": [], "carried": [],
           "constraints": {}}
    for pb, m, p in zip(pose_bones, moved, posed):
        if not m:
            continue
        if "(drv)" in pb.name:
            out["helpers"].append(pb.name)
            if p:
                out["helpers_posed"].append(pb.name)
            continue
        live = [c for c in pb.constraints if not c.mute and c.influence > 0]
        if live:
            out["constraints"][pb.name] = [[c.type, getattr(c, "subtarget", "")] for c in live]
        if p:
            out["posed"].append(pb.name)
        elif any(getattr(c, "subtarget", "") in helpers for c in live):
            out["follow_helper"].append(pb.name)
        else:
            out["carried"].append(pb.name)
    return int(moved.sum()), out


def key_values(ob):
    if ob is None or not ob.data.shape_keys:
        return None
    return np.array([k.value for k in ob.data.shape_keys.key_blocks])


set_pose(None)
neutral = {"body": positions(body), "mouth": positions(mouth) if mouth else None,
           "bones": bone_matrices(), "keys_body": key_values(body), "keys_mouth": key_values(mouth)}
motion = {}
widest = None
for v in avail:
    set_pose(v)
    d = np.linalg.norm(positions(body) - neutral["body"], axis=1)
    rec = {"body_max_shift_m": round(float(d.max()), 5), "body_vertices_moved": int((d > 1e-4).sum())}
    if mouth:
        dm = np.linalg.norm(positions(mouth) - neutral["mouth"], axis=1)
        rec["mouth_max_shift_m"] = round(float(dm.max()), 5)
        rec["mouth_vertices_moved"] = int((dm > 1e-4).sum())
    n, kinds = classify_bones(bone_matrices(), neutral["bones"])
    # pose_bones_moved counts armature-space change, so it includes the (drv)
    # helpers and bones carried along by a moving parent.
    rec["pose_bones_moved"] = n
    rec["pose_bones_moved_helpers"] = len(kinds["helpers"])
    rec["pose_bones_moved_daz"] = n - len(kinds["helpers"])
    rec["pose_bones"] = kinds
    kb = key_values(body)
    if kb is not None:
        rec["body_shape_keys_nonzero"] = int((np.abs(kb - neutral["keys_body"]) > 1e-6).sum())
    km = key_values(mouth)
    if km is not None:
        rec["mouth_shape_keys_nonzero"] = int((np.abs(km - neutral["keys_mouth"]) > 1e-6).sum())
    motion[v] = rec
    if widest is None or rec["body_vertices_moved"] > motion[widest]["body_vertices_moved"]:
        widest = v
set_pose(None)

pts = neutral["body"]
lo, hi = pts.min(axis=0), pts.max(axis=0)
# The face band runs down to the lowest vertex frame_key (AA) moves, or, if
# it moves none, the viseme that moves the most body vertices.
key = cfg["frame_key"] if cfg["frame_key"] in motion and motion[cfg["frame_key"]]["body_vertices_moved"] else widest
if key and motion[key]["body_vertices_moved"]:
    set_pose(key)
    moved = np.linalg.norm(positions(body) - neutral["body"], axis=1) > 1e-4
    set_pose(None)
    chin = float(pts[moved][:, 2].min())
    chin_from = "lowest vertex moved by " + key
else:
    hb = rig.data.bones.get("head")
    chin = float((rig.matrix_world @ hb.head_local).z) if hb else float(hi[2] - 0.25)
    chin_from = "head bone (no viseme moved the body)"
band = pts[pts[:, 2] >= chin]
head_h = float(hi[2] - chin)
head_centre = Vector(((band[:, 0].min() + band[:, 0].max()) / 2.0,
                      (band[:, 1].min() + band[:, 1].max()) / 2.0,
                      (hi[2] + chin) / 2.0))
extent = float((hi - lo).max())
centre = Vector(((lo + hi) / 2.0).tolist())

cam_data = bpy.data.cameras.new("probe_cam")
cam_data.type = "ORTHO"
cam_data.clip_start = 0.01
cam_data.clip_end = 100.0
cam = bpy.data.objects.new("probe_cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
world = bpy.data.worlds.new("probe_world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = cfg["ambient"]
scene.world = world
sun = bpy.data.lights.new("probe_key", "SUN")
sun.energy = cfg["key"]
sun_ob = bpy.data.objects.new("probe_key", sun)
scene.collection.objects.link(sun_ob)
sun_ob.rotation_euler = Euler((math.radians(55), 0, math.radians(30)), "XYZ")
sun_ob.parent = cam

scene.render.engine = "BLENDER_EEVEE_NEXT"
if cfg["samples"]:
    scene.eevee.taa_render_samples = cfg["samples"]
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
columns = {
    "body": {"target": centre, "scale": extent * 1.15, "az": -45.0, "el": 30.0, "dist": extent * 3.0},
    "face": {"target": head_centre, "scale": head_h / 0.75, "az": 0.0, "el": 0.0, "dist": 2.0},
    "face34": {"target": head_centre, "scale": head_h / 0.75, "az": -35.0, "el": 10.0, "dist": 2.0},
}
for m, viewport, render in subsurfs:
    m.show_viewport = viewport if cfg["subdivision"] == "as-saved" else False
    m.show_render = render if cfg["subdivision"] == "as-saved" else False


def place(col):
    c = columns[col]
    az, el = math.radians(c["az"]), math.radians(c["el"])
    offset = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * c["dist"]
    cam.location = c["target"] + offset
    cam.rotation_euler = Euler((math.radians(90.0) - el, 0.0, az), "XYZ")
    cam_data.ortho_scale = c["scale"]


frames = []
timing = {}
for size in cfg["sizes"]:
    scene.render.resolution_x = scene.render.resolution_y = size
    ts = time.time()
    for ri, v in enumerate(order):
        set_pose(v)
        for ci, col in enumerate(cfg["columns"]):
            place(col)
            f = os.path.join(cfg["frames_dir"], f"s{size}_r{ri:02d}_c{ci}.png")
            scene.render.filepath = f
            bpy.ops.render.render(write_still=True)
            frames.append(f)
    timing[str(size)] = round(time.time() - ts, 1)

import gpu
try:
    renderer = gpu.platform.renderer_get()
except Exception as exc:
    renderer = f"unavailable: {exc}"
print("DAZ_RENDER " + json.dumps({
    "frames": frames, "order": ["neutral"] + order[1:], "missing": missing,
    "columns": cfg["columns"], "daz_addons_enabled": enabled,
    "use_scripts_auto_execute": auto_exec, "body": body.name,
    "mouth": mouth.name if mouth else None, "motion": motion, "widest": widest,
    "vertices": {"body": len(body.data.vertices), "mouth": len(mouth.data.vertices) if mouth else None},
    "subsurf_modifiers": len(subsurfs), "subsurf_levels_viewport_render": subsurf_levels,
    "subdivision": cfg["subdivision"],
    "frame_key_used": key, "chin_from": chin_from,
    "head_height_m": round(head_h, 4), "figure_height_m": round(float(hi[2] - lo[2]), 4),
    "eevee_samples": scene.eevee.taa_render_samples, "gpu_renderer": renderer,
    "seconds_per_size": timing, "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1),
    "seconds": round(time.time() - t0, 1)}), flush=True)
sys.stderr.flush()
os._exit(0)
'''

# render_sheet.py opens a .blend as saved, Subsurf modifiers and all. So that
# its rows get the subdivision --subdivision asks for, this opens the file,
# switches every Subsurf modifier off and saves a copy beside it for
# render_sheet.py to open, and saves nothing when none is switched on.
PREP_SCRIPT = r'''
import json, os, resource, sys, time
cfg = json.loads(sys.argv[-1])
os.makedirs(cfg["user_resources"], exist_ok=True)
os.environ["BLENDER_USER_RESOURCES"] = cfg["user_resources"]
import bpy
t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=cfg["blend"], load_ui=False)
mods = [m for o in bpy.data.objects if o.type == "MESH" for m in o.modifiers if m.type == "SUBSURF"]
on = [m for m in mods if m.show_viewport or m.show_render]
out = {"subsurf_modifiers": len(mods), "subsurf_switched_on": len(on),
       "levels_viewport_render": sorted({(m.levels, m.render_levels) for m in on}), "copy": None}
if on:
    for m in on:
        m.show_viewport = False
        m.show_render = False
    bpy.context.preferences.filepaths.save_version = 0
    ret = bpy.ops.wm.save_as_mainfile(filepath=cfg["copy"], check_existing=False, copy=True)
    if "FINISHED" not in ret:
        raise SystemExit(f"save_as_mainfile returned {sorted(ret)}")
    out["copy"] = cfg["copy"]
out["seconds"] = round(time.time() - t0, 1)
out["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
print("DAZ_PREP " + json.dumps(out), flush=True)
sys.stderr.flush()
os._exit(0)
'''

# Stopping the docker exec client leaves its process running in the container,
# still writing frames. This ends the `python3 -c` jobs whose arguments hold
# the marker: SIGTERM, then SIGKILL for any still there after 10 s.
STOP_SCRIPT = r'''
import json, os, signal, sys, time
marker = sys.argv[-1].encode()
me = os.getpid()


def jobs():
    found = []
    for d in os.listdir("/proc"):
        if not d.isdigit() or int(d) == me:
            continue
        try:
            with open(f"/proc/{d}/cmdline", "rb") as f:
                argv = f.read().split(b"\0")
        except OSError:
            continue
        if len(argv) > 2 and argv[1] == b"-c" and any(marker in a for a in argv[2:]):
            found.append(int(d))
    return found


ended = jobs()
for pid in ended:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
deadline = time.time() + 10
while ended and time.time() < deadline and jobs():
    time.sleep(0.5)
killed = jobs()
for pid in killed:
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
print("DAZ_STOP " + json.dumps({"ended": ended, "killed": killed}), flush=True)
'''


# ------------------------------------------------------------------ host side

class Stopped(Exception):
    """SIGTERM, raised so the same clean-up runs as for Ctrl-C."""


@contextlib.contextmanager
def signals_held():
    """Ignore Ctrl-C and SIGTERM while a stop is being cleaned up."""
    old = {s: signal.signal(s, signal.SIG_IGN) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for s, h in old.items():
            signal.signal(s, h)


def end_container_job(marker: str) -> None:
    """End the Blender job in the container whose arguments hold `marker`."""
    try:
        r = exec_python(STOP_SCRIPT, marker, timeout=40)
        line = next((l for l in r.stdout.splitlines() if l.startswith("DAZ_STOP ")), None)
        res = json.loads(line[len("DAZ_STOP "):]) if line else None
        why = f"exit {r.returncode}: {r.stderr.strip()[-300:]}"
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        res, why = None, f"{type(exc).__name__}: {exc}"
    if res is None:
        print(f"  ! could not check {container()} for the job writing {marker} ({why}); "
              f"look for it with `docker top {container()} -o pid,etimes,args`")
    elif res["ended"]:
        print(f"  stopped   Blender job(s) {res['ended']} in {container()}"
              + (f", {res['killed']} with SIGKILL" if res["killed"] else ""))

def other_blender_jobs() -> list[str]:
    """`python3 -c` processes in the container other than this probe's own."""
    try:
        out = subprocess.run(["docker", "top", container(), "-o", "pid,etimes,args"],
                             capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"(docker top failed: {exc})"]
    return [line.strip() for line in out.splitlines()[1:] if "python3 -c" in line]


def wait_for_idle(skip: bool) -> None:
    """Wait while ComfyUI runs or queues a job, or another Blender job runs in the container."""
    if skip:
        return
    while True:
        busy = []
        try:
            with urllib.request.urlopen(COMFY + "/queue", timeout=10) as r:
                q = json.load(r)
            n = len(q.get("queue_running", [])) + len(q.get("queue_pending", []))
            if n:
                busy.append(f"ComfyUI queue holds {n} job(s)")
        except (urllib.error.URLError, OSError, ValueError) as exc:
            busy.append(f"could not read {COMFY}/queue: {exc}")
        jobs = other_blender_jobs()
        if jobs:
            busy.append(f"{len(jobs)} other python3 -c job(s) in {container()}")
        if not busy:
            return
        print(f"  waiting: {'; '.join(busy)}; checking again in 30 s ({time.strftime('%H:%M:%S')})",
              flush=True)
        time.sleep(30)


UNITS = {"B": 1, "KiB": 1 << 10, "MiB": 1 << 20, "GiB": 1 << 30, "TiB": 1 << 40,
         "kB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3}


def parse_mem(text: str) -> int | None:
    m = re.match(r"\s*([\d.]+)\s*([A-Za-z]+)", text)
    if not m or m.group(2) not in UNITS:
        return None
    return int(float(m.group(1)) * UNITS[m.group(2)])


class MemSampler(threading.Thread):
    """Container memory from `docker stats --no-stream`, sampled until stopped."""

    def __init__(self):
        super().__init__(daemon=True)
        self.samples: list[int] = []
        self.halt = threading.Event()

    def sample(self) -> int | None:
        try:
            out = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}",
                                  container()], capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.TimeoutExpired):
            return None
        return parse_mem(out.split("/")[0]) if out else None

    def run(self):
        while not self.halt.is_set():
            v = self.sample()
            if v is not None:
                self.samples.append(v)
            self.halt.wait(1.0)

    def summary(self, baseline: int | None) -> dict:
        gib = 1 << 30
        peak = max(self.samples) if self.samples else None
        return {"samples": len(self.samples),
                "baseline_gib": round(baseline / gib, 2) if baseline else None,
                "peak_gib": round(peak / gib, 2) if peak else None,
                "peak_above_baseline_gib": round((peak - baseline) / gib, 2) if peak and baseline else None}


@functools.lru_cache(maxsize=None)
def container_mounts() -> tuple:
    try:
        out = subprocess.run(["docker", "inspect", "-f", "{{json .Mounts}}", container()],
                             capture_output=True, text=True, timeout=30).stdout
        return tuple(json.loads(out) or ())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ()


def container_path(host: Path) -> str | None:
    """Where the container sees a host path, from its bind mounts."""
    best = None
    for m in container_mounts():
        src = Path(m.get("Source", ""))
        try:
            rel = host.resolve().relative_to(src)
        except ValueError:
            continue
        if best is None or len(str(src)) > len(str(best[0])):
            best = (src, str(PurePosixPath(m["Destination"]) / rel.as_posix()))
    return best[1] if best else None


def run_blender(script: str, cfg: dict, sentinel: str, timeout: int,
                marker: str) -> tuple[dict | None, float, dict]:
    """Run a Blender job; on Ctrl-C or SIGTERM end its process in the container
    too, found by `marker`, a path unique to this job in its arguments."""
    sampler = MemSampler()
    baseline = sampler.sample()
    sampler.start()
    t = time.time()
    try:
        res = exec_json(script, cfg, sentinel, timeout=timeout)
        wall = round(time.time() - t, 1)
    except (KeyboardInterrupt, Stopped):
        with signals_held():
            end_container_job(marker)
        raise
    finally:
        sampler.halt.set()
        sampler.join(timeout=35)
    return res, wall, sampler.summary(baseline)


def no_result(wall: float, timeout: int) -> None:
    if wall >= timeout + TIMEOUT_GRACE:
        print(f"  ! Blender was still running {TIMEOUT_GRACE} s after its --timeout {timeout} s "
              f"alarm; look for it with `docker top {container()}`")
    elif wall >= timeout:
        print(f"  ! Blender ran past --timeout {timeout} s and its SIGALRM ended it ({wall} s wall)")
    else:
        print("  ! Blender printed no result (traceback above)")


def read_duf(path: Path) -> dict:
    """A .duf or .dsf as JSON, gzip-compressed or plain, as the importer's
    load_json.loadJson reads it: gzip first, plain text when that fails."""
    try:
        with gzip.open(path, "rt", encoding="utf-8-sig") as f:
            return json.load(f)
    except gzip.BadGzipFile:
        pass
    return json.loads(path.read_text(encoding="utf-8-sig"))


def anatomy_from_figure(figure: Path) -> list[str]:
    """The AssetFile entries of a .duf's post-load add-on script, if it has one."""
    try:
        doc = read_duf(figure)
    except (OSError, ValueError, EOFError) as exc:
        raise SystemExit(f"could not read {figure}: {exc}")
    files = []
    for extra in doc.get("scene", {}).get("extra", []):
        if extra.get("type") != "scene_post_load_script":
            continue
        addons = extra.get("settings", {}).get("PostLoadAddons", {}).get("value", {})
        for entry in addons.values():
            asset = (entry.get("value") or {}).get("AssetFile")
            if asset:
                # Daz writes these both with and without a leading slash.
                files.append(asset.lstrip("/"))
    return files


# ------------------------------------------------------ material presets

# A Genesis 9 anatomy figure ships with no maps at all: the eyelash, eye, mouth
# and eyebrow .duf files carry a material whose channels are bare, and Daz
# Studio fills them in by running a MAT preset after the figure loads. Nothing
# here ran one, so an eyelash card rendered as an opaque fan across the eyelid.
#
# A preset writes its channel values two ways. They sit in the file's own
# materials, which is what a wearable does, or they arrive as "animations"
# whose url names the material and the channel, which is what every
# hierarchical preset does. Both are read below. Only the channels this script
# can wire are kept, and the values are the file's own: nothing is guessed.
PRESET_CHANNELS = ("Cutout Opacity", "diffuse", "Refraction Weight", "Refraction Index")
# A surface this refractive is glass, not a solid: the Genesis 9 eye moisture
# and tear layers set Refraction Weight to 1, and without it they render as
# opaque white domes over the eyes.
REFRACTIVE = 0.5
# Suffixes Daz puts on a material instance, as in "Eyelashes Lower-1".
DAZ_INSTANCE = re.compile(r"-\d+$")


def srgb_to_linear(rgb) -> list[float]:
    """Daz writes a colour the way a screen shows it; Blender wants it linear."""
    out = []
    for c in rgb[:3]:
        c = max(0.0, float(c))
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def library_image(lib: Path, ref: str) -> str | None:
    """A Daz image reference as a library-relative path, if the file is there."""
    rel = PurePosixPath(urllib.parse.unquote(str(ref)).lstrip("/"))
    if not rel.parts or ".." in rel.parts:
        return None
    return rel.as_posix() if (lib / rel).is_file() else None


def as_number(value, default=None):
    """Daz writes a channel number as a number or as a string."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_flag(value) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes")


def layered_image(doc: dict, ref: str, lib: Path) -> tuple[list, str]:
    """A Daz layered image as a stack this script can rebuild with nodes.

    Daz composes an eye from a flat base, a sclera map and an iris map, each
    laid over the one below. Only that plain case is taken: every layer laid
    over with no rotation, mirroring, offset or scaling, and left at full
    strength. Anything else is named as unresolved rather than guessed at.
    """
    wanted = urllib.parse.unquote(str(ref)).lstrip("#")
    entry = next((i for i in doc.get("image_library") or []
                  if urllib.parse.unquote(str(i.get("id", ""))) == wanted), None)
    if entry is None:
        return [], "no such image in the file"
    layers = []
    for layer in entry.get("map") or []:
        if not as_flag(layer.get("active", True)):
            continue
        if (str(layer.get("operation", "blend_source_over")) != "blend_source_over"
                or as_number(layer.get("transparency"), 1.0) != 1.0
                or as_number(layer.get("rotation"), 0.0) != 0.0
                or as_flag(layer.get("xmirror")) or as_flag(layer.get("ymirror"))
                or as_number(layer.get("xscale"), 1.0) != 1.0
                or as_number(layer.get("yscale"), 1.0) != 1.0
                or as_number(layer.get("xoffset"), 0.0) != 0.0
                or as_number(layer.get("yoffset"), 0.0) != 0.0
                or as_flag(layer.get("invert"))):
            return [], "a layer this script does not compose"
        colour = layer.get("color")
        if isinstance(colour, str):
            try:
                colour = json.loads(colour)
            except ValueError:
                colour = None
        built = {"label": str(layer.get("label", ""))}
        if layer.get("url"):
            rel = library_image(lib, layer["url"])
            if rel is None:
                return [], "a layer whose map is not in the library"
            built["image"] = rel
        elif isinstance(colour, list) and len(colour) >= 3:
            built["colour"] = srgb_to_linear(colour)
        else:
            return [], "a layer with neither a map nor a colour"
        layers.append(built)
    return layers, ""


# What a Daz map is for, read from its file name. Every Genesis 9 texture is
# named <skin>_<part>_<role>_<udim>, and the role is the only part of that this
# script needs: it says which image node in an already-built material a new
# file replaces.
ROLE_TOKENS = ("D", "SSS", "R", "SO", "NM", "B", "SLW", "TM", "OP")


def map_role(name: str) -> str | None:
    stem = str(name).rsplit("/", 1)[-1].rsplit(".", 1)[0]
    for part in reversed(re.split(r"[_.]", stem)):
        if part.upper() in ROLE_TOKENS:
            return part.upper()
    return None


def channel_bits(chan: dict) -> dict:
    return {k: chan[k] for k in ("value", "image", "image_file") if k in chan}


def preset_materials(path: Path, lib: Path) -> dict:
    """What a Daz material preset sets, as far as this script can wire it.

    Returns {"materials": {name: {alpha_image, alpha_value, colour_image,
    colour}}, "unresolved": [...]}, with every image a library-relative path
    that exists. A material name keeps no instance suffix, so "Eyelashes
    Lower-1" and "Eyelashes Lower" are the same material.
    """
    doc = read_duf(path)
    raw: dict[str, dict] = {}
    all_images: dict[str, list] = {}
    roles: dict[str, dict] = {}

    def note_image(material: str, ref) -> None:
        if material and isinstance(ref, str):
            all_images.setdefault(material, []).append(ref)

    def note(material: str, channel: str, bits: dict) -> None:
        if material and bits:
            raw.setdefault(material, {}).setdefault(channel, {}).update(bits)

    def from_struct(mat: dict) -> None:
        name = DAZ_INSTANCE.sub("", str(mat.get("id", "")))
        diffuse = mat.get("diffuse")
        if isinstance(diffuse, dict) and isinstance(diffuse.get("channel"), dict):
            note(name, "diffuse", channel_bits(diffuse["channel"]))
            note_image(name, diffuse["channel"].get("image_file"))
        for extra in mat.get("extra") or []:
            for entry in (extra or {}).get("channels") or []:
                chan = entry.get("channel", entry)
                if not isinstance(chan, dict):
                    continue
                if chan.get("id") in PRESET_CHANNELS:
                    note(name, chan["id"], channel_bits(chan))
                note_image(name, chan.get("image_file"))

    for mat in doc.get("material_library") or []:
        from_struct(mat)
    for mat in (doc.get("scene") or {}).get("materials") or []:
        from_struct(mat)

    prefix = "extra/studio_material_channels/channels/"
    for anim in (doc.get("scene") or {}).get("animations") or []:
        url = str(anim.get("url", ""))
        if "#materials/" not in url or ":?" not in url:
            continue
        head, _, tail = url.partition(":?")
        material = DAZ_INSTANCE.sub("", urllib.parse.unquote(head.split("#materials/")[1]))
        if tail.startswith(prefix):
            tail = tail[len(prefix):]
        channel, _, kind = tail.rpartition("/")
        channel = urllib.parse.unquote(channel)
        keys = anim.get("keys") or []
        if not keys or len(keys[0]) < 2:
            continue
        if kind == "image_file":
            note_image(material, keys[0][1])
        if channel not in PRESET_CHANNELS or kind not in ("value", "image", "image_file"):
            continue
        note(material, channel, {kind: keys[0][1]})

    materials, unresolved = {}, []
    for name, channels in sorted(all_images.items()):
        by_role = {}
        for ref in channels:
            rel = library_image(lib, ref)
            role = map_role(ref)
            if rel and role:
                by_role.setdefault(role, rel)
        if by_role:
            roles.setdefault(name, {}).update(by_role)
    for name, channels in sorted(raw.items()):
        spec = {}
        if name in roles:
            spec["images"] = roles[name]
        for channel, image_key, value_key in (("Cutout Opacity", "alpha_image", "alpha_value"),
                                              ("diffuse", "colour_image", "colour"),
                                              ("Refraction Weight", None, "refraction"),
                                              ("Refraction Index", None, "ior")):
            bits = channels.get(channel) or {}
            if image_key is None:
                value = bits.get("value")
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    spec[value_key] = float(value)
                continue
            if bits.get("image_file"):
                rel = library_image(lib, bits["image_file"])
                if rel:
                    spec[image_key] = rel
                else:
                    unresolved.append({"material": name, "channel": channel,
                                       "reason": "not in the library",
                                       "reference": str(bits["image_file"])})
            elif bits.get("image"):
                layers, why = layered_image(doc, bits["image"], lib)
                if layers and image_key == "colour_image":
                    spec["colour_layers"] = layers
                else:
                    unresolved.append({"material": name, "channel": channel,
                                       "reason": why or "a layered image this script does not compose",
                                       "reference": str(bits["image"])})
            if isinstance(bits.get("value"), (int, float)) and not isinstance(bits["value"], bool):
                spec[value_key] = float(bits["value"])
            elif isinstance(bits.get("value"), list) and len(bits["value"]) >= 3:
                spec[value_key] = srgb_to_linear(bits["value"])
        if spec:
            materials[name] = spec
    return {"materials": materials, "unresolved": unresolved}


def auto_mat_presets(lib: Path, figure: str, anatomy: list[str]) -> list[str]:
    """The MAT presets Daz Studio would run for this figure, where they exist.

    Three rules, each measured against Genesis 9 Starter Essentials: a
    character preset keeps its materials in a Materials folder beside it, an
    anatomy figure keeps a "<name> MAT.duf" next to itself, and the eyebrow
    cards keep a colour preset per colour, of which none is the default, so
    Brown is taken when it is there.
    """
    found = []
    stem = PurePosixPath(figure).stem
    who = stem.split(" for ")[0].strip()
    if who and who != stem:
        for match in sorted((lib / PurePosixPath(figure).parent).glob(
                f"*/{who}*/Materials/*All MAT*.duf")):
            found.append(match.relative_to(lib).as_posix())
            break
    for rel in anatomy:
        path = PurePosixPath(rel)
        sibling = lib / path.parent / f"{path.stem} MAT.duf"
        if sibling.is_file():
            found.append(PurePosixPath(rel).parent.joinpath(sibling.name).as_posix())
            continue
        colours = sorted((lib / path.parent.parent / "Materials").glob("*Color *.duf"))
        if colours:
            brown = [c for c in colours if "Brown" in c.name]
            found.append((brown or colours)[0].relative_to(lib).as_posix())
    seen, unique = set(), []
    for rel in found:
        if rel not in seen:
            seen.add(rel)
            unique.append(rel)
    return unique


def mat_preset_specs(lib: Path, presets: list[tuple]) -> list[dict]:
    """Read each preset once, for the Blender side to apply."""
    specs = []
    for rel, objects in presets:
        path = lib / rel
        if not path.is_file():
            raise SystemExit(f"  ! material preset not in the library: {path}")
        read = preset_materials(path, lib)
        specs.append({"file": rel, "objects": objects, **read})
    return specs


def chosen_replaces(lib: Path, args) -> list[tuple]:
    """The presets whose textures replace the ones already on a material."""
    seen, unique = set(), []
    for rel, objects in args.mat_replace:
        if not (lib / rel).is_file():
            raise SystemExit(f"  ! material preset not in the library: {lib / rel}")
        key = (rel, tuple(objects))
        if key not in seen:
            seen.add(key)
            unique.append((rel, objects))
    return unique


def chosen_presets(lib: Path, args, anatomy: list[str]) -> list[tuple]:
    """The presets to apply, each once: the ones asked for first, then the ones
    found beside the figure.

    That order is what makes --mat-preset mean something. A preset only fills in
    what a material is missing, so whichever runs first decides, and the one the
    caller named should win over the one this script went looking for.
    """
    chosen = list(args.mat_preset)
    if args.auto_materials:
        chosen += [(rel, []) for rel in auto_mat_presets(lib, args.figure, anatomy)]
    seen, unique = set(), []
    for rel, objects in chosen:
        key = (rel, tuple(objects))
        if key not in seen:
            seen.add(key)
            unique.append((rel, objects))
    return unique


def mat_preset_line(specs: list[dict]) -> str:
    if not specs:
        return "no preset; imported materials as they arrive"
    names = ", ".join(PurePosixPath(spec["file"]).name for spec in specs)
    total = sum(len(spec["materials"]) for spec in specs)
    return f"{len(specs)} preset(s), {total} material(s) named: {names}"


def print_mat_presets(res: dict) -> None:
    """What the material presets filled in, and what they left alone."""
    for entry in res.get("mat_presets") or []:
        name = PurePosixPath(entry["file"]).name
        applied = entry["applied"]
        bits = []
        for did in applied:
            what = [k for k in ("alpha_image", "alpha_value", "colour_image",
                                "colour_layers", "colour", "refraction") if k in did]
            bits.append(f"{did['material']} ({', '.join(what)})")
        print(f"  preset    {name}: filled in {len(applied)} of {len(entry['matched'])} matched"
              + (f"; {', '.join(bits)}" if bits else ""))
        if entry["not_matched"]:
            print(f"            no material here for {', '.join(entry['not_matched'][:6])}"
                  + (" ..." if len(entry["not_matched"]) > 6 else ""))
        for u in entry["unresolved"][:3]:
            print(f"            {u['material']} {u['channel']}: {u['reason']}")


def offset_arg(text: str) -> tuple:
    """MESH=DX,DY,DZ in millimetres."""
    name, _, numbers = text.partition("=")
    try:
        values = [float(v) for v in numbers.split(",")]
    except ValueError:
        values = []
    if not name.strip() or len(values) != 3:
        raise argparse.ArgumentTypeError(
            f"expected MESH=DX,DY,DZ in millimetres, got {text!r}")
    return name.strip(), values


def obj_scale_arg(text: str):
    """A uniform scale for --wear-obj, or auto to take it from the fitted sphere."""
    if text.strip().lower() == "auto":
        return None
    try:
        return float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a number or auto, got {text!r}")


def offset_arg_mm(text: str) -> list:
    """Three millimetres along the world axes: DX,DY,DZ."""
    try:
        values = [float(v) for v in text.split(",")]
    except ValueError:
        values = []
    if len(values) != 3:
        raise argparse.ArgumentTypeError(f"expected DX,DY,DZ in millimetres, got {text!r}")
    return values


def mat_preset_arg(text: str) -> tuple:
    """A library-relative preset, optionally @ the meshes it applies to."""
    file, at, objects = text.partition("@")
    names = [n.strip() for n in objects.split(",") if n.strip()] if at else []
    return library_relative(file), names


def resolve_in_library(lib: Path, rel: str) -> tuple[str | None, bool]:
    """A library-relative path as it is actually spelled on disk.

    Daz content is written for a case-insensitive filesystem and does not
    always agree with itself. The Wise Wizard's own post-load script asks for
    "WW_eyebrows.duf" where its package installed "WW_Eyebrows.duf", and on
    this filesystem that is a missing file. Exact match first; then one
    case-insensitive step per segment, which is what Daz Studio gets for free.
    Returns (the path on disk, whether the case had to be fixed).
    """
    if (lib / rel).exists():
        return rel, False
    here, parts = lib, []
    for want in PurePosixPath(rel).parts:
        if (here / want).exists():
            here, _ = here / want, parts.append(want)
            continue
        try:
            found = next((n for n in sorted(os.listdir(here))
                          if n.casefold() == want.casefold()), None)
        except OSError:
            return None, False
        if found is None:
            return None, False
        here, _ = here / found, parts.append(found)
    return "/".join(parts), True


def resolve_all(lib: Path, rels: list[str]) -> tuple[list[str], list[list[str]], list[str]]:
    """Every path as it is spelled on disk, what was re-cased, and what is missing."""
    out, fixed, missing = [], [], []
    for rel in rels:
        found, changed = resolve_in_library(lib, rel)
        if found is None:
            missing.append(rel)
            continue
        out.append(found)
        if changed:
            fixed.append([rel, found])
    return out, fixed, missing


def out_path(text: str) -> Path:
    p = Path(text)
    p = (ROOT / p) if not p.is_absolute() else p
    p = p.resolve()
    try:
        p.relative_to(OUT.resolve())
    except ValueError:
        raise argparse.ArgumentTypeError(f"--out must be under {OUT.relative_to(ROOT)}/, got {text!r}")
    if p.suffix != ".blend":
        raise argparse.ArgumentTypeError(f"--out must end in .blend, got {text!r}")
    return p


def obj_path(text: str) -> Path:
    """A Wavefront OBJ on the host, which the container has to be able to see."""
    p = Path(text)
    p = (ROOT / p) if not p.is_absolute() else p
    p = p.resolve()
    if p.suffix.lower() != ".obj":
        raise argparse.ArgumentTypeError(f"--wear-obj takes a .obj file, got {text!r}")
    if not p.is_file():
        raise argparse.ArgumentTypeError(f"no such file: {p}")
    return p


def c_path(host: Path) -> str:
    """A host path under output/ or input/ as the container mounts it."""
    p = container_path(host)
    if p is None:
        raise SystemExit(f"  ! {container()} mounts no folder holding {host}")
    return p


def library_relative(text: str) -> str:
    """A path inside the content library: relative, with no .. part."""
    p = PurePosixPath(text.strip())
    if not text.strip() or p.is_absolute() or ".." in p.parts:
        raise argparse.ArgumentTypeError(
            f"expected a path relative to the library with no .. part, got {text!r}")
    return p.as_posix()


def anatomy_arg(text: str) -> str | list[str]:
    if text in ("auto", "none"):
        return text
    items = [library_relative(a) for a in text.split(",") if a.strip()]
    if not items:
        raise argparse.ArgumentTypeError("expected auto, none or library-relative .duf paths")
    return items


def cmd_build(args) -> int:
    if not (EXT / "import_daz" / "blender_manifest.toml").exists():
        print("  ! run `scripts/daz_import_probe.py fetch` first")
        return 1
    lib = args.library.resolve()
    try:
        lib.relative_to(ROOT)
        print(f"  ! the library must be outside the repo, got {lib}")
        return 2
    except ValueError:
        pass
    figure = lib / args.figure
    if not figure.is_file():
        print(f"  ! figure not found on the host: {figure}")
        return 1
    lib_c = container_path(lib)
    if lib_c is None:
        print(f"  ! {container()} mounts no folder holding {lib}")
        return 1
    if args.anatomy == "auto":
        anatomy = anatomy_from_figure(figure)
        for a in anatomy:
            try:
                library_relative(a)
            except argparse.ArgumentTypeError:
                print(f"  ! {args.figure} names post-load file {a!r}, which is outside the library")
                return 1
    elif args.anatomy == "none":
        anatomy = []
    else:
        anatomy = args.anatomy
    anatomy, recased, missing_anatomy = resolve_all(lib, anatomy)
    name = args.out.stem
    OUT.mkdir(parents=True, exist_ok=True)
    DEV.mkdir(parents=True, exist_ok=True)
    dev_c = c_path(DEV)
    cfg = {
        "user_resources": f"{dev_c}/blender_user",
        "home": f"{dev_c}/home",
        "repo_module": REPO_MODULE,
        "repo_dir": f"{dev_c}/ext",
        "library": lib_c,
        "content_dirs": [args.content_dir or lib_c],
        "dir_check": not args.no_dir_check,
        "figure": args.figure,
        "anatomy": anatomy,
        "anatomy_recased": recased,
        "anatomy_missing": missing_anatomy,
        "material_method": args.material_method,
        "merge_materials": False,
        "refractive": REFRACTIVE,
        "fit": args.fit,
        "verbosity": args.verbosity,
        "visemes": args.visemes,
        "facs": args.facs,
        "mat_presets": mat_preset_specs(lib, chosen_presets(lib, args, anatomy)),
        "mat_replaces": mat_preset_specs(lib, chosen_replaces(lib, args)),
        "role_tokens": list(ROLE_TOKENS),
        "fit_report": args.fit_report,
        "no_textures": args.no_textures,
        "subdivision": args.subdivision,
        "prop_pattern": PROP_PATTERN,
        "visemes_list": VISEMES,
        "blend": c_path(args.out),
        "log": c_path(OUT / f"{name}_blender.log"),
        "partial": c_path(OUT / f"{name}_build.partial.json"),
        "timeout": args.timeout,
    }
    print(f"  container {container()}")
    print(f"  add-on    {cfg['repo_dir']}/import_daz as bl_ext.{REPO_MODULE}.import_daz")
    print(f"  library   {lib} (container {lib_c})")
    print(f"  figure    {args.figure}")
    print(f"  anatomy   {len(anatomy)} post-load figure file(s)" if anatomy else "  anatomy   none")
    for asked, found in recased:
        print(f"            re-cased: {asked} is on disk as {found}")
    for gone in missing_anatomy:
        print(f"  ! the figure names a post-load file that is not in the library: {gone}")
    print(f"  materials {mat_preset_line(cfg['mat_presets'])}")
    print(f"  morphs    visemes {'yes' if args.visemes else 'no'}, FACS {'yes' if args.facs else 'no'}; "
          f"materials {args.material_method}; fit {args.fit}"
          + ("; textures cleared before saving" if args.no_textures else ""))
    wait_for_idle(args.no_wait)
    partial = OUT / f"{name}_build.partial.json"
    try:
        res, wall, mem = run_blender(BUILD_SCRIPT, cfg, "DAZ_BUILD ", args.timeout, cfg["partial"])
    except (KeyboardInterrupt, Stopped):
        partial.unlink(missing_ok=True)
        raise
    report = {"date": time.strftime("%Y-%m-%d"), "container": container(),
              "argv": ["scripts/daz_import_probe.py"] + sys.argv[1:], "wall_seconds": wall,
              "docker_stats_memory": mem, "download": {k: v for k, v in PIN.items() if k != "urls"}
              | {"url": PIN["urls"][0]}, "config": cfg}
    if res is None:
        no_result(wall, args.timeout)
        if partial.exists():
            report["blender_partial"] = json.loads(partial.read_text())
            done = report["blender_partial"]["steps"]
            print(f"  last step that finished: {done[-1]['step'] if done else 'none'}")
        rc = 1
    else:
        report["blender"] = res
        rc = summarise_build(res, args, name)
    partial.unlink(missing_ok=True)
    report_path = OUT / f"{name}_build.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"  memory    container {mem['baseline_gib']} GiB before, peak {mem['peak_gib']} GiB "
          f"({mem['samples']} docker stats samples)")
    in_blender = f", {res['blender_seconds']} s in Blender" if res else ""
    print(f"  report    {report_path.relative_to(ROOT)}  ({wall} s wall{in_blender})")
    print(f"  log       {(OUT / (name + '_blender.log')).relative_to(ROOT)}")
    return rc


def summarise_build(res: dict, args, name: str) -> int:
    for s in res["steps"]:
        mark = "ok" if s["ok"] else "FAILED"
        print(f"  {mark:6s} {s['seconds']:7.2f} s  {s['peak_rss_mb']:8.1f} MB peak  {s['step']}")
        if not s["ok"]:
            print(f"         {s['error']}")
        msg = (s.get("get_error_message") or "").strip()
        if msg:
            print("         get_error_message(): " + msg.replace("\n", " | ")[:400])
    rc = 0
    if res.get("stopped_at") or res.get("fatal"):
        print(f"  ! stopped at: {res.get('stopped_at')}")
        if res.get("fatal"):
            print(res["fatal"])
        return 1
    if res["failures"]:
        rc = 1
    survey = res.get("survey", {})
    for rig, a in survey.get("armatures", {}).items():
        props = a["custom_properties"]
        print(f"  rig       {rig}: {a['bones']} bones ({a['deform_bones']} deform), "
              f"{props.get('object', 0)} object and {props.get('data', 0)} data properties, "
              f"{a['drivers']} drivers ({a['python_drivers']} not simple expressions)")
        for owner, names in a["matching_properties"].items():
            if names:
                print(f"            {len(names)} {owner} properties match {PROP_PATTERN}")
    for mesh, m in survey.get("meshes", {}).items():
        print(f"  mesh      {mesh}: {m['vertices']} vertices, {m['faces']} faces, "
              f"{m['shape_keys']} shape keys ({m['shape_key_drivers']} driven)")
    print(f"  images    {survey.get('images')}; materials {survey.get('materials')}")
    print_mat_presets(res)
    if res.get("no_textures"):
        t = res["no_textures"]
        print(f"  textures  {t['image_nodes_cleared']} image nodes cleared; images {t['images_before']} "
              f"before, {t['images_after']} saved")
    props = res.get("viseme_props", {})
    print(f"  visemes   {len(props)} of {len(VISEMES)} found as rig properties")
    if props:
        poses = OUT / f"{name}_poses.json"
        rows = [{"@props": {p: 0.0 for p in props.values()}}]
        rows += [{"@props": {p: (1.0 if p == props[v] else 0.0) for p in props.values()}}
                 for v in VISEMES if v in props]
        poses.write_text(json.dumps(rows, indent=1) + "\n")
        print(f"  poses     {poses.relative_to(ROOT)}  (render_sheet.py --poses transforms:, "
              "row 0 neutral)")
    print(f"  wrote     {args.out.relative_to(ROOT)}"
          if args.out.exists() else f"  ! {args.out.relative_to(ROOT)} was not written")
    return rc if args.out.exists() else 1


# ------------------------------------------------------------------ scene

def dial_arg(text: str) -> tuple:
    """NAME=VALUE for a rig property."""
    if "=" not in text:
        raise argparse.ArgumentTypeError(f"expected NAME=VALUE, got {text!r}")
    name, _, value = text.partition("=")
    try:
        return (name.strip(), float(value))
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} in {text!r} is not a number")


def morph_sets_arg(text: str) -> list:
    if not text.strip():
        return []
    out = []
    for word in text.split(","):
        word = word.strip().lower()
        if not word:
            continue
        if word not in MORPH_SETS:
            raise argparse.ArgumentTypeError(
                f"unknown morph set {word!r}; expected any of {', '.join(sorted(MORPH_SETS))}")
        if word not in [w for w, _ in out]:
            out.append((word, MORPH_SETS[word]))
    return out


def csv_names(text: str) -> list[str]:
    return [w.strip() for w in text.split(",") if w.strip()]


def cmd_scene(args) -> int:
    if not (EXT / "import_daz" / "blender_manifest.toml").exists():
        print("  ! run `scripts/daz_import_probe.py fetch` first")
        return 1
    lib = args.library.resolve()
    try:
        lib.relative_to(ROOT)
        print(f"  ! the library must be outside the repo, got {lib}")
        return 2
    except ValueError:
        pass
    lib_c = container_path(lib)
    if lib_c is None:
        print(f"  ! {container()} mounts no folder holding {lib}")
        return 1
    for rel in [args.figure] + args.wear + ([args.pose] if args.pose else []):
        if not (lib / rel).is_file():
            print(f"  ! not in the library: {lib / rel}")
            return 1
    if args.anatomy == "auto":
        anatomy = anatomy_from_figure(lib / args.figure)
    elif args.anatomy == "none":
        anatomy = []
    else:
        anatomy = args.anatomy
    anatomy, recased, missing_anatomy = resolve_all(lib, anatomy)
    custom = None
    if args.custom_morphs:
        cdir = lib / args.custom_morphs
        if not cdir.is_dir():
            print(f"  ! not a directory in the library: {cdir}")
            return 1
        files = args.custom_files or sorted(p.name for p in cdir.glob("*.dsf"))
        missing = [n for n in files if not (cdir / n).is_file()]
        if missing:
            print(f"  ! not in {args.custom_morphs}: {missing}")
            return 1
        if not files:
            print(f"  ! no .dsf file in {args.custom_morphs}")
            return 1
        custom = {"dir": f"{lib_c}/{args.custom_morphs}", "files": files,
                  "category": args.custom_category, "bodypart": args.custom_bodypart}
    morph_sets = [(label, op) for label, op in args.morphs if not (args.facs and label == "facs")]
    name = args.out.stem
    OUT.mkdir(parents=True, exist_ok=True)
    DEV.mkdir(parents=True, exist_ok=True)
    dev_c = c_path(DEV)
    cfg = {
        "user_resources": f"{dev_c}/blender_user",
        "home": f"{dev_c}/home",
        "repo_module": REPO_MODULE,
        "repo_dir": f"{dev_c}/ext",
        "library": lib_c,
        "content_dirs": [lib_c],
        "dir_check": True,
        "figure": args.figure,
        "anatomy": anatomy,
        "anatomy_recased": recased,
        "anatomy_missing": missing_anatomy,
        "material_method": args.material_method,
        "merge_materials": False,
        "refractive": REFRACTIVE,
        "fit": args.fit,
        "verbosity": args.verbosity,
        "morph_sets": morph_sets,
        "custom": custom,
        "facs": args.facs,
        "mat_presets": mat_preset_specs(lib, chosen_presets(lib, args, anatomy)),
        "mat_replaces": mat_preset_specs(lib, chosen_replaces(lib, args)),
        "role_tokens": list(ROLE_TOKENS),
        "fit_report": args.fit_report,
        "hide": args.hide,
        "hide_figure": args.hide_figure,
        "hide_materials": args.hide_material,
        "offsets": args.offset,
        "declip": args.declip,
        "declip_max_verts": args.declip_max_verts,
        "declip_max_push": args.declip_max_push,
        "declip_skip": args.declip_skip,
        "set": args.set,
        "set_after": args.set_dressed,
        "wear": [[rel, f"{lib_c}/{rel}"] for rel in args.wear],
        "wear_objs": [{"path": c_path(p), "host": str(p), "bone": args.obj_bone,
                       "scale": args.obj_scale, "offset": args.obj_offset,
                       "yaw": args.obj_yaw, "radius_cm": args.obj_radius,
                       "forward": args.obj_forward, "up": args.obj_up}
                      for p in args.wear_obj],
        "transfer": not args.no_transfer,
        "skip_transfer": args.skip_transfer,
        "pose": f"{lib_c}/{args.pose}" if args.pose else "",
        "pose_affect_morphs": args.pose_affects_morphs,
        "subdivision": args.subdivision,
        "prop_pattern": PROP_PATTERN,
        "visemes_list": VISEMES,
        "blend": c_path(args.out),
        "log": c_path(OUT / f"{name}_blender.log"),
        "partial": c_path(OUT / f"{name}_scene.partial.json"),
        "timeout": args.timeout,
    }
    print(f"  container {container()}")
    print(f"  library   {lib} (container {lib_c})")
    print(f"  figure    {args.figure}")
    print(f"  morphs    {', '.join(label for label, _ in morph_sets) or 'none'}"
          f"{'; FACS' if args.facs else ''}"
          f"{'; custom ' + str(len(custom['files'])) + ' file(s) from ' + args.custom_morphs if custom else ''}")
    print(f"  wear      {len(args.wear)} file(s); pose {args.pose or 'none'}")
    for spec in cfg["wear_objs"]:
        print(f"  obj       {Path(spec['host']).name} at scale "
              f"{spec['scale'] if spec['scale'] is not None else 'auto'}, "
              f"on bone {spec['bone'] or 'none'}, offset {spec['offset']} mm, "
              f"yaw {spec['yaw']} deg")
    print(f"  anatomy   {len(anatomy)} post-load figure file(s)" if anatomy else "  anatomy   none")
    for asked, found in recased:
        print(f"            re-cased: {asked} is on disk as {found}")
    for gone in missing_anatomy:
        print(f"  ! the figure names a post-load file that is not in the library: {gone}")
    print(f"  materials {mat_preset_line(cfg['mat_presets'])}")
    wait_for_idle(args.no_wait)
    partial = OUT / f"{name}_scene.partial.json"
    try:
        res, wall, mem = run_blender(SCENE_SCRIPT, cfg, "DAZ_BUILD ", args.timeout, cfg["partial"])
    except (KeyboardInterrupt, Stopped):
        partial.unlink(missing_ok=True)
        raise
    report = {"date": time.strftime("%Y-%m-%d"), "container": container(),
              "argv": ["scripts/daz_import_probe.py"] + sys.argv[1:], "wall_seconds": wall,
              "docker_stats_memory": mem, "config": cfg}
    rc = 0
    if res is None:
        no_result(wall, args.timeout)
        if partial.exists():
            report["blender_partial"] = json.loads(partial.read_text())
            done = report["blender_partial"]["steps"]
            print(f"  last step that finished: {done[-1]['step'] if done else 'none'}")
        rc = 1
    else:
        props = res.pop("rig_properties", None)
        if props:
            path = OUT / f"{name}_morphs.json"
            path.write_text(json.dumps(props, indent=1) + "\n")
            print(f"  sliders   {len(props)} numeric rig properties, "
                  f"{path.relative_to(ROOT)}")
        report["blender"] = res
        rc = summarise_scene(res, args, name)
    partial.unlink(missing_ok=True)
    if res is not None and not args.no_verify and args.out.exists() and res.get("body_rig"):
        report["verify"] = verify_blend(args, args.out, res["body_rig"],
                                        [n for n, _ in args.set + args.set_dressed])
        if report["verify"] is None:
            rc = 1
    for suffix in ("_scene.json", "_build.json"):
        (OUT / f"{name}{suffix}").write_text(json.dumps(report, indent=2) + "\n")
    print(f"  memory    container {mem['baseline_gib']} GiB before, peak {mem['peak_gib']} GiB "
          f"({mem['samples']} docker stats samples)")
    in_blender = f", {res['blender_seconds']} s in Blender" if res else ""
    print(f"  report    {(OUT / (name + '_scene.json')).relative_to(ROOT)}, copied to "
          f"{name}_build.json for `render --blend`  ({wall} s wall{in_blender})")
    print(f"  log       {(OUT / (name + '_blender.log')).relative_to(ROOT)}")
    return rc


def summarise_scene(res: dict, args, name: str) -> int:
    for s in res["steps"]:
        mark = "ok" if s["ok"] else "FAILED"
        print(f"  {mark:6s} {s['seconds']:7.2f} s  {s['peak_rss_mb']:8.1f} MB peak  {s['step']}")
        if not s["ok"]:
            print(f"         {s['error']}")
        msg = (s.get("get_error_message") or "").strip()
        if msg:
            print("         get_error_message(): " + msg.replace("\n", " | ")[:400])
    if res.get("stopped_at") or res.get("fatal"):
        print(f"  ! stopped at: {res.get('stopped_at')}")
        if res.get("fatal"):
            print(res["fatal"])
        return 1
    rc = 1 if res["failures"] else 0
    for label, m in (res.get("morph_sets") or {}).items():
        if m:
            print(f"  morphs    {label}: {m['properties_added']} properties, "
                  f"{sum(m['shape_keys_added'].values())} shape keys")
    cm = res.get("custom_morphs")
    if cm:
        print(f"  custom    {cm['files']} file(s) as {cm['category']}: {cm['properties_added']} "
              f"properties, {sum(cm['shape_keys_added'].values())} shape keys")
    for key, d in (res.get("dials") or {}).items():
        if not d:
            continue
        for mesh, mv in d["moved"].items():
            if mv.get("moved"):
                print(f"  dial      {key}: {mesh} {mv['moved']}/{mv['vertices']} vertices moved, "
                      f"up to {mv['max_mm']} mm")
    for wname, w in (res.get("wearables") or {}).items():
        if not w:
            continue
        for mesh, f in w["after_merge"].items():
            print(f"  wearable  {wname}: {mesh} {f.get('vertices')} vertices, parent "
                  f"{f.get('parent')} ({f.get('parent_type')}), armature "
                  f"{f.get('armature_modifiers')}, follows the rig: {f.get('follows_rig')}")
    for oname, obj in (res.get("wear_objs") or {}).items():
        if obj.get("skipped"):
            print(f"  obj       {oname}: {obj['skipped']}")
            continue
        print(f"  obj       {oname}: {obj['vertices']} vertices, {obj['faces']} triangles, "
              f"{len(obj['uv_layers'])} UV layer(s), material(s) "
              f"{', '.join(obj['materials']) or '-'}")
        sphere = obj.get("skull_sphere")
        if sphere:
            centre = ", ".join(f"{v * 100:.1f}" for v in sphere["centre"])
            print(f"            {obj['bone']} skin {obj['skin_vertices']} vertices; sphere "
                  f"r {sphere['radius_m'] * 100:.2f} cm at ({centre}) cm, fitted to "
                  f"{sphere['points']} of them within {sphere['residual_mean_mm']:.1f} mm mean, "
                  f"{sphere['residual_max_mm']:.1f} mm worst")
            chosen = obj.get("scale_chosen", "given")
            print(f"            scale {obj['scale']} ({chosen}); "
                  f"{obj['scale_that_matches_the_sphere']} puts the roots on that sphere")
        if obj.get("parented_to"):
            print(f"            parented to {obj['parented_to']}")
        for mat, alpha in (obj.get("alpha") or {}).items():
            source = ("from " + alpha.get("alpha_image", "a node")) if alpha["alpha_linked"] \
                else str(alpha.get("alpha_value"))
            print(f"            {mat}: alpha {source}, base colour "
                  f"{alpha.get('base_colour_image', 'not from a map')}")
    p = res.get("pose")
    if p:
        print(f"  pose      {p['file']}: {p['bones_moved']} of {p['bones']} pose bones moved, "
              f"{p['keyframes']} f-curves")
        for mesh, mv in p["moved"].items():
            print(f"            {mesh}: {mv.get('moved')}/{mv.get('vertices')} vertices moved, "
                  f"up to {mv.get('max_mm')} mm")
    survey = res.get("survey", {})
    for rig, a in survey.get("armatures", {}).items():
        print(f"  rig       {rig}: {a['bones']} bones ({a['deform_bones']} deform), "
              f"{a['custom_properties'].get('object', 0)} object and "
              f"{a['custom_properties'].get('data', 0)} data properties, {a['drivers']} drivers")
    for mesh, m in survey.get("meshes", {}).items():
        print(f"  mesh      {mesh}: {m['vertices']} vertices, {m['shape_keys']} shape keys "
              f"({m['shape_key_drivers']} driven)")
    print_mat_presets(res)
    print(f"  visemes   {len(res.get('viseme_props') or {})} of {len(VISEMES)} found as rig properties")
    props = res.get("viseme_props") or {}
    if props:
        poses = OUT / f"{name}_poses.json"
        rows = [{"@props": {p: 0.0 for p in props.values()}}]
        rows += [{"@props": {p: (1.0 if p == props[v] else 0.0) for p in props.values()}}
                 for v in VISEMES if v in props]
        poses.write_text(json.dumps(rows, indent=1) + "\n")
        print(f"  poses     {poses.relative_to(ROOT)}")
    print(f"  wrote     {args.out.relative_to(ROOT)}"
          if args.out.exists() else f"  ! {args.out.relative_to(ROOT)} was not written")
    return rc if args.out.exists() else 1


# ------------------------------------------------------------------ verify

def verify_blend(args, blend: Path, rig: str, props: list) -> dict | None:
    """Open a saved .blend in a Blender with no DAZ add-on and report what is
    left: the pose, the deformed meshes and the values of `props`."""
    cfg = {"user_resources": f"{c_path(DEV)}/blender_user", "blend": c_path(blend),
           "rig": rig, "props": sorted(set(props)), "timeout": args.timeout}
    wait_for_idle(args.no_wait)
    res, wall, mem = run_blender(VERIFY_SCRIPT, cfg, "DAZ_VERIFY ", args.timeout, cfg["blend"])
    if res is None:
        no_result(wall, args.timeout)
        return None
    if "error" in res:
        # The Blender half exits 0 after printing this, so it is the only
        # report there is: no rig by that name, nothing else to measure.
        print("  ! " + res["error"])
        return None
    res["wall_seconds"] = wall
    res["docker_stats_memory"] = mem
    print(f"  verify    {blend.name} reopened with add-ons {res['daz_addons_enabled'] or 'none'}: "
          f"{res['rig']['bones']} bones, {res['rig']['pose_bones_moved']} posed, "
          f"{res['rig']['drivers']} drivers ({wall} s wall)")
    for mesh, m in res["meshes"].items():
        print(f"            {mesh}: {m['vertices']} vertices, {m['shape_keys']} shape keys "
              f"({m['shape_keys_nonzero']} not zero), armature {m['armature_modifier']}")
    for mesh, m in res["pose_cleared"].items():
        print(f"            {mesh}: clearing the pose moves {m['moved']}/{m['vertices']} "
              f"vertices, up to {m['max_mm']} mm")
    for mesh, m in res["props_zeroed"].items():
        print(f"            {mesh}: zeroing {len(cfg['props'])} slider(s) moves {m['moved']}/"
              f"{m['vertices']} vertices, up to {m['max_mm']} mm")
    return res


def cmd_verify(args) -> int:
    name = args.blend.stem
    rig = args.rig
    props = args.props or []
    for suffix in ("_scene.json", "_build.json"):
        path = OUT / f"{name}{suffix}"
        if not path.exists():
            continue
        b = json.loads(path.read_text()).get("blender") or {}
        rig = rig or b.get("body_rig")
        if not args.props:
            props = [d["property"] for d in (b.get("dials") or {}).values() if d]
        break
    if not rig:
        print(f"  ! no --rig given and no report beside {args.blend.relative_to(ROOT)} names one")
        return 1
    res = verify_blend(args, args.blend, rig, props)
    if res is None:
        return 1
    path = OUT / f"{name}_verify.json"
    path.write_text(json.dumps(
        {"date": time.strftime("%Y-%m-%d"), "container": container(),
         "argv": ["scripts/daz_import_probe.py"] + sys.argv[1:], "verify": res}, indent=2) + "\n")
    print(f"  report    {path.relative_to(ROOT)}")
    return 0


# ------------------------------------------------------------------ render

def auto_label(args) -> str:
    """The render options that differ from the defaults, joined, so that a
    narrower or different run does not overwrite the files of a full one."""
    if args.motion_only:
        return ""
    parts = []
    if args.only:
        parts.append("-".join(args.only))
    if args.sizes != SIZES:
        parts.append("-".join(str(s) for s in args.sizes))
    if args.columns != list(COLUMNS):
        parts.append("-".join(args.columns))
    if args.samples:
        parts.append(f"s{args.samples}")
    if args.materials:
        parts.append("materials")
    if args.subdivision != "off":
        parts.append(args.subdivision)
    if args.no_sheet:
        parts.append("no-sheet")
    elif args.sheet_size != 128:
        parts.append(f"sheet{args.sheet_size}")
    if args.threshold != 8:
        parts.append(f"t{args.threshold}")
    return "_".join(parts)


def cmd_render(args) -> int:
    blend = args.blend
    name = blend.stem
    build = OUT / f"{name}_build.json"
    if not blend.exists() or not build.exists():
        print(f"  ! need {blend.relative_to(ROOT)} and {build.relative_to(ROOT)}; run `build` first")
        return 1
    b = json.loads(build.read_text()).get("blender") or {}
    props = b.get("viseme_props") or {}
    if not props:
        print(f"  ! {build.relative_to(ROOT)} lists no viseme properties; nothing to render")
        return 1
    label = auto_label(args) if args.label is None else args.label
    prefix = f"{name}_{label}" if label else name
    kind = "motion" if args.motion_only else "render"
    report = {
        "date": time.strftime("%Y-%m-%d"), "container": container(), "blend": str(blend.relative_to(ROOT)),
        "argv": ["scripts/daz_import_probe.py"] + sys.argv[1:],
        "options": {
            "motion_only": args.motion_only,
            "only": args.only or "all",
            "sizes": [] if args.motion_only else args.sizes,
            "columns": args.columns,
            "samples_requested": args.samples or "Blender default",
            "materials": "imported" if args.materials else "clay",
            "subdivision": args.subdivision,
            "render_sheet": not (args.motion_only or args.no_sheet),
            "sheet_size": args.sheet_size,
            "threshold": args.threshold,
            "label": label,
            "timeout": args.timeout,
        },
    }
    print(f"  files     {(OUT / prefix).relative_to(ROOT)}_{kind}.json"
          + ("" if args.motion_only else " and its sheets"))
    rc = 0
    if args.motion_only:
        args.sizes = []
    elif not args.no_sheet:
        rc |= run_render_sheet(args, name, prefix, props, report)
    run_id = f"{os.getpid()}_{int(time.time())}"
    frames = OUT / "_frames" / run_id
    dev_c = c_path(DEV)
    cfg = {
        "user_resources": f"{dev_c}/blender_user",
        "blend": c_path(blend),
        "rig": b["body_rig"],
        "props": props,
        "body_mesh": b.get("body_mesh") or "",
        "visemes": VISEMES,
        "frame_key": "AA",
        "frames_dir": c_path(frames),
        "sizes": args.sizes,
        "columns": args.columns,
        "clay": not args.materials,
        "subdivision": args.subdivision,
        "only": args.only,
        "clay_color": [0.55, 0.54, 0.52],
        "key": 1.6,
        "ambient": 0.22,
        "samples": args.samples,
        "timeout": args.timeout,
    }
    report["probe_config"] = cfg
    wait_for_idle(args.no_wait)
    try:
        rc |= compose_render(args, cfg, frames, prefix, report)
    finally:
        if not args.keep_frames:
            shutil.rmtree(frames, ignore_errors=True)
            try:
                frames.parent.rmdir()
            except OSError:
                pass
    report_path = OUT / f"{prefix}_{kind}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"  report    {report_path.relative_to(ROOT)}")
    return rc


def remove_sheet_frames(pid: int, since: float) -> None:
    """Delete render_sheet.py's frame folders from the process `pid` started at `since`."""
    for d in sorted(SHEET_FRAMES.glob(f"{pid}_*")):
        try:
            started = int(d.name.split("_", 1)[1])
        except ValueError:
            continue
        if d.is_dir() and started >= int(since) - 1:
            n = sum(1 for _ in d.iterdir())
            shutil.rmtree(d, ignore_errors=True)
            print(f"  removed   {d.relative_to(ROOT)} ({n} file(s) render_sheet.py left)")


def run_render_sheet(args, name: str, prefix: str, props: dict, report: dict) -> int:
    rows_v = [v for v in VISEMES if v in props and (not args.only or v in args.only)]
    rows = [{"@props": {p: 0.0 for p in props.values()}}]
    rows += [{"@props": {p: (1.0 if p == props[v] else 0.0) for p in props.values()}} for v in rows_v]
    tag = os.getpid()
    poses = OUT / f"_{name}_sheet_{tag}_poses.json"
    copy = OUT / f"_{name}_sheet_{tag}.blend"
    sheet = OUT / f"{prefix}_render_sheet_{args.sheet_size}.png"
    entry = {"rows": ["neutral"] + rows_v, "subdivision": args.subdivision}
    report["render_sheet"] = entry
    try:
        poses.write_text(json.dumps(rows, indent=1) + "\n")
        opened = args.blend
        if args.subdivision == "off":
            dev_c = c_path(DEV)
            pcfg = {"user_resources": f"{dev_c}/blender_user", "blend": c_path(args.blend),
                    "copy": c_path(copy)}
            wait_for_idle(args.no_wait)
            info, wall, mem = run_blender(PREP_SCRIPT, pcfg, "DAZ_PREP ", min(args.timeout, 900),
                                          pcfg["copy"])
            if info is None:
                no_result(wall, min(args.timeout, 900))
                entry["prep"] = {"failed": True, "wall_seconds": wall}
                print("  ! could not switch Subsurf off in a copy, so render_sheet.py did not run")
                return 1
            entry["prep"] = info | {"wall_seconds": wall, "docker_stats_memory": mem}
            if info["copy"]:
                opened = copy
                print(f"  subsurf   {info['subsurf_switched_on']} of {info['subsurf_modifiers']} Subsurf "
                      f"modifiers on, levels (viewport, render) {info['levels_viewport_render']}; "
                      f"render_sheet.py opens a copy with them off ({wall} s)")
            else:
                print(f"  subsurf   none of {info['subsurf_modifiers']} Subsurf modifiers on; "
                      f"render_sheet.py opens the file as saved ({wall} s)")
        entry["opened"] = str(opened.relative_to(ROOT))
        # --engine eevee is pinned, not left to render_sheet.py's default, which
        # became Cycles on 2026-09-18. This stage is read beside stage 2, whose
        # renderer is EEVEE in this file, and every render number recorded here
        # and in docs/reference/daz-genesis.md was measured on EEVEE. Taking the
        # new default would change the pixels under those numbers without
        # re-measuring them.
        cmd = [sys.executable, str(ROOT / "scripts" / "render_sheet.py"), str(opened),
               "--poses", f"transforms:{poses}", "--angles", "1", "--size", str(args.sheet_size),
               "--engine", "eevee",
               "--out", str(sheet), "--check", "--timeout", str(args.timeout)]
        wait_for_idle(args.no_wait)
        print("  render_sheet.py " + " ".join(cmd[2:]), flush=True)
        sampler = MemSampler()
        baseline = sampler.sample()
        sampler.start()
        t = time.time()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        marker = f"{SHEET_FRAMES_C}/{proc.pid}_"
        try:
            out = proc.communicate(timeout=args.timeout + 2 * TIMEOUT_GRACE)[0]
            code = proc.returncode
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            out = (proc.communicate()[0] or "") + f"\nrender_sheet.py still running after {exc.timeout} s; ended"
            code = None
        except (KeyboardInterrupt, Stopped):
            with signals_held():
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                end_container_job(marker)
                remove_sheet_frames(proc.pid, t)
            raise
        finally:
            wall = round(time.time() - t, 1)
            sampler.halt.set()
            sampler.join(timeout=35)
        if code != 0:
            # render_sheet.py deletes its frames only when it finishes or its
            # Blender job returns no result; a crash, or this script ending it
            # after the host timeout, leaves them and can leave the job running.
            with signals_held():
                end_container_job(marker)
                remove_sheet_frames(proc.pid, t)
    finally:
        poses.unlink(missing_ok=True)
        copy.unlink(missing_ok=True)
    print("\n".join("    | " + line for line in out.strip().splitlines()[-40:]))
    entry.update({"command": ["scripts/render_sheet.py"] + cmd[2:], "exit": code, "wall_seconds": wall,
                  "sheet": str(sheet.relative_to(ROOT)) if sheet.exists() else None,
                  "docker_stats_memory": sampler.summary(baseline),
                  "output_tail": out.strip().splitlines()[-60:]})
    if code != 0 or not sheet.exists():
        print(f"  ! render_sheet.py exited {code}")
        return 1
    return 0


def compose_render(args, cfg: dict, frames: Path, prefix: str, report: dict) -> int:
    from PIL import Image, ImageChops, ImageDraw

    info, wall, mem = run_blender(RENDER_SCRIPT, cfg, "DAZ_RENDER ", args.timeout, cfg["frames_dir"])
    if info is None:
        no_result(wall, args.timeout)
        report["probe_render"] = {"failed": True, "wall_seconds": wall}
        return 1
    if info["missing"]:
        print(f"  ! viseme properties not on the rig: {', '.join(info['missing'])}")
    print(f"  opened    {args.blend.relative_to(ROOT)}; DAZ add-ons enabled: "
          f"{info['daz_addons_enabled'] or 'none'}; auto-run scripts {info['use_scripts_auto_execute']}")
    print(f"  subsurf   {info['subsurf_modifiers']} modifiers, levels (viewport, render) "
          f"{info['subsurf_levels_viewport_render']}; renders use {info['subdivision']}")
    print(f"  framing   head band {info['head_height_m']} m of {info['figure_height_m']} m "
          f"({info['chin_from']}); EEVEE {info['eevee_samples']} samples on {info['gpu_renderer']}")
    for v, m in info["motion"].items():
        if not args.motion_only and v not in info["order"]:
            continue
        k = m["pose_bones"]
        print(f"  motion    {v:3s} body {m['body_vertices_moved']:5d} vertices, max "
              f"{m['body_max_shift_m']:.4f} m; mouth {m.get('mouth_vertices_moved', '-')}; shape keys changed "
              f"body {m.get('body_shape_keys_nonzero', '-')}, mouth {m.get('mouth_shape_keys_nonzero', '-')}; "
              f"{m['pose_bones_moved']} pose bones in armature space: {len(k['helpers'])} (drv) helpers "
              f"({len(k['helpers_posed'])} posed by drivers), {len(k['posed'])} Daz bones posed, "
              f"{len(k['follow_helper'])} following a helper, {len(k['carried'])} carried")
    order, cols = info["order"], info["columns"]
    rep = {"wall_seconds": wall, "docker_stats_memory": mem, "renders": len(info["frames"]),
           "threshold": args.threshold, "sizes": {}}
    rep.update({k: info[k] for k in ("eevee_samples", "gpu_renderer", "head_height_m", "figure_height_m",
                                     "chin_from", "motion", "use_scripts_auto_execute",
                                     "daz_addons_enabled", "seconds_per_size", "peak_rss_mb", "seconds",
                                     "vertices", "subsurf_modifiers", "subsurf_levels_viewport_render",
                                     "subdivision", "order", "frame_key_used", "widest", "body", "mouth",
                                     "missing")})
    for size in cfg["sizes"]:
        sheet = Image.new("RGBA", (len(cols) * size, len(order) * size), (0, 0, 0, 0))
        cells = {}
        for ri in range(len(order)):
            for ci in range(len(cols)):
                im = Image.open(frames / f"s{size}_r{ri:02d}_c{ci}.png").convert("RGBA")
                cells[(ri, ci)] = im
                sheet.paste(im, (ci * size, ri * size))
        out = OUT / f"{prefix}_sheet_{size}.png"
        sheet.save(out)
        per = {}
        for ci, col in enumerate(cols):
            base = cells[(0, ci)]
            figure = sum(base.getchannel("A").histogram()[1:])
            rows = {}
            for ri, v in enumerate(order[1:], start=1):
                diff = ImageChops.difference(cells[(ri, ci)], base)
                bands = [bd.point(lambda x: 255 if x > args.threshold else 0) for bd in diff.split()]
                mask = bands[0]
                for bd in bands[1:]:
                    mask = ImageChops.lighter(mask, bd)
                box = mask.getbbox()
                rows[v] = {"changed_px": mask.histogram()[255],
                           "box": [box[2] - box[0], box[3] - box[1]] if box else [0, 0]}
            per[col] = {"figure_px": figure, "visemes": rows}
        rep["sizes"][str(size)] = per
        gutter = 70
        lab = Image.new("RGBA", (gutter + sheet.width, 16 + sheet.height), (255, 255, 255, 255))
        lab.alpha_composite(sheet, (gutter, 16))
        d = ImageDraw.Draw(lab)
        for ci, col in enumerate(cols):
            d.text((gutter + ci * size + 4, 2), col, fill=(0, 0, 0, 255))
        for ri, v in enumerate(order):
            d.text((4, 16 + ri * size + size // 2 - 5), v, fill=(0, 0, 0, 255))
        lab.save(OUT / f"{prefix}_sheet_{size}_labelled.png")
        print(f"  sheet     {out.relative_to(ROOT)}  ({len(cols)}x{len(order)} cells of {size} px, "
              f"{info['seconds_per_size'][str(size)]} s)")
        for col in cols:
            counts = [per[col]["visemes"][v]["changed_px"] for v in order[1:]]
            if counts:
                print(f"            {col:7s} changed px vs neutral: min {min(counts)}, max {max(counts)}, "
                      f"figure {per[col]['figure_px']} px")
    report["probe_render"] = rep
    print(f"  renders   {len(info['frames'])} in {wall} s wall; container peak {mem['peak_gib']} GiB "
          f"(before {mem['baseline_gib']} GiB)")
    return 1 if info["missing"] else 0


# ------------------------------------------------------------------ arguments

def csv_sizes(text: str) -> list[int]:
    try:
        sizes = [int(s) for s in text.split(",") if s.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected whole numbers separated by commas, such as 128,220, got {text!r}") from None
    if not sizes:
        raise argparse.ArgumentTypeError("name at least one cell size, such as 128")
    if any(not 16 <= s <= 2048 for s in sizes):
        raise argparse.ArgumentTypeError(f"cell sizes must be 16 to 2048 px, got {text!r}")
    return list(dict.fromkeys(sizes))


def csv_columns(text: str) -> list[str]:
    cols = [c.strip() for c in text.split(",") if c.strip()]
    bad = [c for c in cols if c not in COLUMNS]
    if bad:
        raise argparse.ArgumentTypeError(
            f"unknown framing {', '.join(repr(c) for c in bad)}; choose from {', '.join(COLUMNS)}")
    if not cols:
        raise argparse.ArgumentTypeError(f"name at least one of {', '.join(COLUMNS)}")
    return list(dict.fromkeys(cols))


def csv_visemes(text: str) -> list[str]:
    names = [v.strip().upper() for v in text.split(",") if v.strip()]
    bad = [v for v in names if v not in VISEMES]
    if bad:
        raise argparse.ArgumentTypeError(f"unknown viseme {', '.join(bad)}; choose from {', '.join(VISEMES)}")
    if not names:
        raise argparse.ArgumentTypeError(f"name at least one viseme, such as AA, from {', '.join(VISEMES)}")
    # In the research note's order, whatever order they were given in.
    return [v for v in VISEMES if v in names]


def label_arg(text: str) -> str:
    if text and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", text):
        raise argparse.ArgumentTypeError(
            f"expected letters, digits, _ and -, starting with a letter or digit, got {text!r}")
    return text


def bounded(lo: int, hi: int | None):
    def parse(text: str) -> int:
        try:
            v = int(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected a whole number, got {text!r}") from None
        if v < lo or (hi is not None and v > hi):
            span = f"{lo} to {hi}" if hi is not None else f"{lo} or more"
            raise argparse.ArgumentTypeError(f"expected {span}, got {v}")
        return v
    return parse


def blend_path(text: str) -> Path:
    p = Path(text)
    p = (ROOT / p) if not p.is_absolute() else p
    p = p.resolve()
    try:
        p.relative_to(OUT.resolve())
    except ValueError:
        raise argparse.ArgumentTypeError(f"--blend must be under {OUT.relative_to(ROOT)}/, got {text!r}")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download, check and unpack import_daz 5.2.0")

    def common(p, timeout):
        p.add_argument("--timeout", type=bounded(1, None), default=timeout,
                       help=f"seconds before Blender ends itself inside the container "
                            f"(default {timeout}); the host waits {TIMEOUT_GRACE} s more")
        p.add_argument("--no-wait", action="store_true",
                       help="do not wait for ComfyUI's queue or other python3 -c jobs first")

    b = sub.add_parser("build", help="import a figure with visemes and FACS: .blend, _build.json")
    common(b, 1800)
    b.add_argument("--out", type=out_path, required=True, help="output/daz/NAME.blend")
    b.add_argument("--library", type=Path, default=DEFAULT_LIBRARY,
                   help=f"host path of the Daz content library (default {DEFAULT_LIBRARY})")
    b.add_argument("--figure", type=library_relative, default=DEFAULT_FIGURE,
                   help=f".duf relative to the library, with no .. part (default {DEFAULT_FIGURE!r})")
    b.add_argument("--anatomy", type=anatomy_arg, default="auto",
                   help="auto: the files the figure .duf's post-load add-on script names, read "
                        "from a plain or gzip-compressed .duf; none; or library-relative .duf "
                        "paths, comma separated")
    b.add_argument("--content-dir", default="",
                   help="container path to give the importer as contentDirs instead of the library, "
                        "to test a wrong path; the figure still loads from --library")
    b.add_argument("--no-dir-check", action="store_true",
                   help="record the content directory checks but carry on when they fail")
    b.add_argument("--mat-preset", type=mat_preset_arg, action="append", default=[],
                   metavar="FILE[@MESH,MESH]",
                   help="a Daz material preset .duf in the library, to fill in what an imported "
                        "material is missing: its cutout opacity map, its colour map or its flat "
                        "colour, and nothing it already has. @ names the meshes it may touch "
                        "(default every mesh). Repeatable, applied in order")
    b.add_argument("--mat-replace", type=mat_preset_arg, action="append", default=[],
                   metavar="FILE[@MESH,MESH]",
                   help="a Daz material preset .duf whose maps replace the ones a material "
                        "already has, matched by what each file name says the map is for: "
                        "what a skin swap needs, where every channel changes rather than the "
                        "missing ones. Applied after --mat-preset, because that is what puts "
                        "a skin's colour map into Base Color. Repeatable")
    b.add_argument("--fit-report", action=argparse.BooleanOptionalAction, default=True,
                   help="measure how far each mesh sits inside or outside the body, which is "
                        "what says whether an outfit clips (default on)")
    b.add_argument("--auto-materials", action=argparse.BooleanOptionalAction, default=True,
                   help="also apply the presets that sit beside the figure and beside each "
                        "anatomy file, after any --mat-preset, which is what gives eyelashes, "
                        "eyebrows and eyes their maps: without them an eyelash card renders as "
                        "an opaque fan (default on)")
    b.add_argument("--visemes", action="store_true", help="run bpy.ops.daz.import_visemes()")
    b.add_argument("--facs", action="store_true", help="run bpy.ops.daz.import_facs()")
    b.add_argument("--no-textures", action="store_true",
                   help="clear every image texture node and remove the images before saving")
    b.add_argument("--subdivision", choices=("keep", "off"), default="keep",
                   help="off saves every Subsurf modifier switched off for viewport and render; "
                        "keep saves the importer's levels, 1 in the viewport and up to 3 for render "
                        "(default keep)")
    b.add_argument("--material-method", choices=MATERIAL_METHODS, default="EXTENDED_PRINCIPLED",
                   help="the importer's material method (default EXTENDED_PRINCIPLED)")
    b.add_argument("--fit", choices=FIT_METHODS, default="MORPHED",
                   help="the importer's fitMeshes; DBZFILE needs a .dbz from Daz Studio (default MORPHED)")
    b.add_argument("--verbosity", type=bounded(0, 4), default=3,
                   help="the importer's verbosity; 3 prints each path it cannot find (default 3)")

    s = sub.add_parser("scene", help="figure, morph sets, sliders, wearables and a pose: .blend, "
                                    "_scene.json, _morphs.json")
    common(s, 3600)
    s.add_argument("--out", type=out_path, required=True, help="output/daz/NAME.blend")
    s.add_argument("--library", type=Path, default=DEFAULT_LIBRARY,
                   help=f"host path of the Daz content library (default {DEFAULT_LIBRARY})")
    s.add_argument("--figure", type=library_relative, default=DEFAULT_FIGURE,
                   help="the figure or character preset .duf, relative to the library "
                        f"(default {DEFAULT_FIGURE!r})")
    s.add_argument("--anatomy", type=anatomy_arg, default="auto",
                   help="as for build: auto, none, or library-relative .duf paths")
    s.add_argument("--morphs", type=morph_sets_arg, default=[],
                   help="standard morph sets to import, comma separated, from "
                        + ", ".join(sorted(MORPH_SETS)) + "; each is one operator and loads every "
                        "file the add-on's paths table lists for the figure")
    s.add_argument("--custom-morphs", type=library_relative, default=None,
                   help="a folder of .dsf morphs in the library to import with "
                        "bpy.ops.daz.import_custom_morphs(), such as "
                        "\"data/Daz 3D/Genesis 9/Base/Morphs/Daz 3D/Base Characters 9\"")
    s.add_argument("--custom-files", type=csv_names, default=[],
                   help="file names inside --custom-morphs, comma separated (default every .dsf)")
    s.add_argument("--custom-category", default="Shapes",
                   help="the category the custom morphs are filed under (default Shapes)")
    s.add_argument("--custom-bodypart", choices=("Face", "Body", "Custom"), default="Custom",
                   help="the operator's bodypart (default Custom)")
    s.add_argument("--mat-preset", type=mat_preset_arg, action="append", default=[],
                   metavar="FILE[@MESH,MESH]",
                   help="a Daz material preset .duf in the library, to fill in what an imported "
                        "material is missing, as for build; repeatable, applied in order after "
                        "the wearables are on")
    s.add_argument("--mat-replace", type=mat_preset_arg, action="append", default=[],
                   metavar="FILE[@MESH,MESH]",
                   help="a Daz material preset .duf whose maps replace the ones a material "
                        "already has, matched by what each file name says the map is for: "
                        "what a skin swap needs, where every channel changes rather than the "
                        "missing ones. Applied after --mat-preset, because that is what puts "
                        "a skin's colour map into Base Color. Repeatable")
    s.add_argument("--hide", type=csv_names, default=[],
                   help="mesh names to keep out of the render, comma separated. They stay in "
                        "the file and keep their place: the clothes still fit what they were "
                        "fitted to, and render_sheet.py frames only what it can see")
    s.add_argument("--offset", type=offset_arg, action="append", default=[],
                   metavar="MESH=DX,DY,DZ",
                   help="move a worn mesh bodily, in millimetres along the world axes, "
                        "before anything is pushed clear of the body. For a garment that "
                        "sits where its author put it rather than where this figure needs "
                        "it. Repeatable, and refused on a posed figure")
    s.add_argument("--hide-material", type=csv_names, default=[],
                   help="material zones to render as nothing, comma separated, such as the "
                        "hood zone of a hooded cloak. Their alpha goes to zero and any link "
                        "into it is removed first")
    s.add_argument("--hide-figure", action="store_true",
                   help="hide the figure's own meshes, its body and the eyes, mouth, lashes, "
                        "tear and eyebrows a post-load script brings with it, leaving whatever "
                        "it is wearing. A costume with a skull where the face was is the case "
                        "this exists for")
    s.add_argument("--declip", type=float, default=0.0, metavar="MM",
                   help="push every worn mesh's vertices out of the body until they stand "
                        "this many millimetres clear of it, which is what stops a hip "
                        "coming through a pair of shorts authored for another figure. It "
                        "edits the rest shape, so it refuses to run on a posed figure "
                        "(default 0, off)")
    s.add_argument("--declip-max-push", type=float, default=20.0, metavar="MM",
                   help="leave a vertex where it is when moving it clear would take more "
                        "than this, because that is not cloth clipping: a hood sits around "
                        "a head and pushing it onto the scalp is what a cloak shifted down "
                        "looks like. 0 lifts the cap (default 20)")
    s.add_argument("--declip-max-verts", type=int, default=100000, metavar="N",
                   help="leave a mesh with more vertices than this alone, so a card hair "
                        "keeps its shape (default 100000)")
    s.add_argument("--declip-skip", type=csv_names, default=[],
                   help="mesh names to leave alone, comma separated")
    s.add_argument("--fit-report", action=argparse.BooleanOptionalAction, default=True,
                   help="measure how far each mesh sits inside or outside the body, which is "
                        "what says whether an outfit clips (default on)")
    s.add_argument("--auto-materials", action=argparse.BooleanOptionalAction, default=True,
                   help="also apply the presets beside the figure and beside each anatomy file, "
                        "after any --mat-preset (default on)")
    s.add_argument("--facs", action="store_true",
                   help="also run bpy.ops.daz.import_facs(), so `render --blend` has its visemes")
    s.add_argument("--set", type=dial_arg, action="append", default=[], metavar="NAME=VALUE",
                   help="set a rig property after the morphs are loaded and measure how far each "
                        "mesh moves; repeatable")
    s.add_argument("--set-dressed", type=dial_arg, action="append", default=[], metavar="NAME=VALUE",
                   help="the same, but after the wearables are on, to see whether they follow")
    s.add_argument("--wear", type=library_relative, action="append", default=[],
                   help="a clothing or hair .duf to import onto the figure already in the scene, "
                        "then merge into its rig; repeatable, in the order given")
    s.add_argument("--wear-obj", type=obj_path, action="append", default=[],
                   metavar="PATH",
                   help="a Wavefront OBJ to place on the figure and bone-parent, repeatable; "
                        "its .mtl and maps are read from beside it. scripts/make_hair.py "
                        "writes one")
    s.add_argument("--obj-bone", default="head", metavar="NAME",
                   help="fit a sphere to the upper half of this bone's skin and put each "
                        "OBJ's own origin at its centre, then parent to it (default head; "
                        "empty places at the world origin and parents to nothing)")
    s.add_argument("--obj-scale", type=obj_scale_arg, default=None, metavar="S|auto",
                   help="uniform scale for each OBJ. The default, auto, is the scale that "
                        "lands the OBJ's own roots on the sphere fitted to --obj-bone, or "
                        "0.01 for centimetres to metres when there is no bone")
    s.add_argument("--obj-offset", type=offset_arg_mm, default=[0.0, 0.0, 0.0],
                   metavar="DX,DY,DZ",
                   help="move each OBJ this far in millimetres after it is placed")
    s.add_argument("--obj-yaw", type=float, default=0.0, metavar="DEG",
                   help="turn each OBJ about the up axis before it is placed (default 0)")
    s.add_argument("--obj-radius", type=float, default=9.5, metavar="CM",
                   help="the scalp radius the OBJ was modelled on, reported against the "
                        "measured skull so --obj-scale can be set from it (default 9.5)")
    s.add_argument("--obj-forward", default="NEGATIVE_Z",
                   choices=("X", "Y", "Z", "NEGATIVE_X", "NEGATIVE_Y", "NEGATIVE_Z"),
                   help="which axis the OBJ's forward becomes (default NEGATIVE_Z)")
    s.add_argument("--obj-up", default="Y", choices=("X", "Y", "Z",
                                                     "NEGATIVE_X", "NEGATIVE_Y", "NEGATIVE_Z"),
                   help="which axis the OBJ's up becomes (default Y)")
    s.add_argument("--no-transfer", action="store_true",
                   help="do not run bpy.ops.daz.transfer_shapekeys() from the body to the wearables")
    s.add_argument("--skip-transfer", type=csv_names, default=[],
                   help="object names to leave out of the shape key transfer, such as a hair mesh")
    s.add_argument("--pose", type=library_relative, default=None,
                   help="a pose preset .duf to apply with bpy.ops.daz.import_pose()")
    s.add_argument("--subdivision", choices=("keep", "off"), default="keep",
                   help="off saves every Subsurf modifier switched off (default keep)")
    s.add_argument("--material-method", choices=MATERIAL_METHODS, default="EXTENDED_PRINCIPLED",
                   help="the importer's material method (default EXTENDED_PRINCIPLED)")
    s.add_argument("--fit", choices=FIT_METHODS, default="MORPHED",
                   help="the importer's fitMeshes; DBZFILE needs a .dbz from Daz Studio "
                        "(default MORPHED)")
    s.add_argument("--verbosity", type=bounded(0, 4), default=3,
                   help="the importer's verbosity (default 3)")
    s.add_argument("--pose-affects-morphs", action="store_true",
                   help="leave bpy.ops.daz.import_pose()'s affectMorphs at its property default, "
                        "True, which with useClearMorphs also True zeroes every morph the figure "
                        "carries; by default the probe passes affectMorphs=False, as the operator's "
                        "own invoke() does when a person picks the file")
    s.add_argument("--no-verify", action="store_true",
                   help="do not reopen the saved .blend in a Blender with no add-on")

    v = sub.add_parser("verify", help="reopen a .blend with no DAZ add-on: pose, meshes, sliders")
    common(v, 900)
    v.add_argument("--blend", type=blend_path, required=True, help="a .blend that `scene` wrote")
    v.add_argument("--rig", default="",
                   help="the armature to read (default the body_rig in the report beside the file)")
    v.add_argument("--props", type=csv_names, default=[],
                   help="rig properties to zero, to see what they still drive (default the ones "
                        "the report says were set)")

    r = sub.add_parser("render", help="viseme rows: render_sheet.py sheet, face sheets, _render.json")
    common(r, 3600)
    r.add_argument("--blend", type=blend_path, required=True, help="a .blend that `build` wrote")
    r.add_argument("--sizes", type=csv_sizes, default=list(SIZES),
                   help="cell sizes for the probe's framings (default 128,220,340)")
    r.add_argument("--columns", type=csv_columns, default=list(COLUMNS),
                   help=f"framings, comma separated, from {', '.join(COLUMNS)} (default all three)")
    r.add_argument("--sheet-size", type=bounded(16, 2048), default=128,
                   help="cell size for the render_sheet.py whole-figure sheet (default 128)")
    r.add_argument("--no-sheet", action="store_true", help="skip render_sheet.py")
    r.add_argument("--label", type=label_arg, default=None,
                   help="added to the names of the render's files as NAME_LABEL_...; by default the "
                        "options that differ from the defaults, such as AA_128_face_s16, and none "
                        "for a default run or --motion-only; \"\" for none")
    r.add_argument("--motion-only", action="store_true",
                   help="measure what each viseme moves and render nothing")
    r.add_argument("--threshold", type=bounded(0, 254), default=8,
                   help="0 to 254 channel difference that counts as a changed pixel (default 8)")
    r.add_argument("--samples", type=bounded(0, None), default=0,
                   help="EEVEE render samples for the probe's own framings; 0 keeps "
                        "Blender's default of 64. Both stages rasterise with EEVEE: "
                        "the render_sheet.py stage is pinned to --engine eevee and "
                        "does not take this number")
    r.add_argument("--subdivision", choices=("off", "as-saved"), default="off",
                   help="off renders the cage in both stages, handing render_sheet.py a copy of the "
                        ".blend with its Subsurf modifiers switched off when any is on; as-saved "
                        "renders the Subsurf levels saved in the file, up to 3 from the importer, "
                        "and is slow on llvmpipe (default off)")
    r.add_argument("--only", type=csv_visemes, default=[],
                   help="render only these visemes after the neutral row, in both stages, comma "
                        "separated, such as AA,OW (default all 17); motion and framing still cover all")
    r.add_argument("--materials", action="store_true",
                   help="render the imported materials instead of clay")
    r.add_argument("--keep-frames", action="store_true",
                   help="keep the probe's own cell PNGs under output/daz/_frames/ (render_sheet.py's "
                        "are always deleted)")
    args = ap.parse_args()

    def on_sigterm(signum, frame):
        raise Stopped("SIGTERM")

    signal.signal(signal.SIGTERM, on_sigterm)
    try:
        if args.cmd == "fetch":
            return cmd_fetch(args)
        if args.cmd == "build":
            return cmd_build(args)
        if args.cmd == "scene":
            return cmd_scene(args)
        if args.cmd == "verify":
            return cmd_verify(args)
        return cmd_render(args)
    except KeyboardInterrupt:
        print("\n  ! stopped by Ctrl-C")
        return 130
    except Stopped:
        print("\n  ! stopped by SIGTERM")
        return 143


if __name__ == "__main__":
    sys.exit(main())
