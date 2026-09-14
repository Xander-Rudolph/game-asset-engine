# What this is

A pipeline that turns a written description into a finished game asset, running
entirely on your own machine.

You type a brief. It draws the concept art, builds a 3D model from that
drawing, paints texture maps onto the model, fits a skeleton inside it, and
renders the model to flat animation frames at the camera angle your game uses.

Every stage is a script with its settings already decided. You choose subjects
and judge results. You are not tuning samplers.

## The stages

| Stage | What happens | Roughly how long |
|---|---|---|
| Concept art | A text prompt becomes an illustration | 30 seconds fast, 2 minutes careful |
| Shape | The illustration becomes untextured geometry | 1 minute |
| Texture | Colour, metal and roughness maps are painted on | 2 to 4 minutes |
| Rig | A skeleton is fitted and the mesh bound to it | 3 to 6 minutes |
| Frames | The rigged model is posed and rendered to a sheet | under a minute |

You can stop at any stage. Plenty of assets never need a rig. Ground textures
never even need a mesh.

## What makes this different from a web service

You keep the intermediate files. That matters more than it sounds.

A service hands you a finished model. This hands you the concept image, the
untextured shape, the textured model, the texture maps as separate files, the
rig, and the frames. When something is wrong three stages later, you can go back
to the stage that caused it instead of starting again.

It also means you can regenerate a model with a different generator from the same
concept image. That is not a nicety. Some generators cannot legally ship in some
countries, and being able to rebuild the mesh from the saved concept image is the
escape hatch. See [licensing](/guide/licensing).

## Why every default is what it is

Almost every number here was chosen because something failed during development.

The face budget is 18,000 because the skeleton is solved against a decimated
(simplified) mesh, and that mesh has to match the one you saved. The concept
workflow uses 20 sampling steps instead of 4 because the fast graph has to run
at guidance scale 1.0, and at that setting negative prompts do nothing.
The camera sits at 30 degrees because that's the only elevation that matches
a 2 to 1 isometric tile.

Each guide page gives the number and explains what went wrong before it was
chosen. If you want to change a default, read that explanation first.

## Requirements

- A CUDA GPU with 12GB or more of memory (less fails during mesh generation)
- About 200GB of disk for model weights, plus about 28GB for the prebuilt image
- Docker with the NVIDIA container toolkit
- Linux (only tested on Linux)

## Getting going

[Install and first run](/guide/install) covers setup, and there is a health
check that tells you exactly what is missing rather than failing later in a
confusing way.
