# Attack effects

*Slashes, bolts, impacts and floor rings, drawn as light by a short script: no
model, no generated image.*

Nothing in this repo makes effects, but the sprites it renders need effects that
sit with them. A 2.5D isometric game made with the engine drew its six attack
effects with a script of its own, using numpy, scipy and Pillow, and this page
records how, and what that taught. Drawn this way, an effect brings no licence
question with it: no model and no third-party art go in.

## Store light, not colour

Each sheet holds light in three channels rather than a colour:

| Channel | Light | Colour on screen |
|---|---|---|
| R, glow | most of every effect | the tint the game gives it, such as the attack's element |
| G, core | white-hot centres and edges | white, whatever the tint |
| B, spark | sparks, readouts, small pixel blocks | halfway between the tint and white |

A shader adds `tint * R + mix(tint, white, 0.5) * B + G` to the screen, so black
is no light, and one sheet serves every colour. The game sets the tint as the
node's colour when it plays the effect, so no art is made per element, and the
tint's alpha fades the whole effect.

## Check how your engine passes the tint

The shader works only if the node's colour reaches it once. In Godot 4.6, checked
with a probe scene, a node's `modulate`, its `self_modulate` and its parents'
`modulate` are folded into the vertex colour, and are not applied again after a
fragment shader writes its colour. So the shader copies the vertex colour into a
varying, uses that as the tint and writes the final colour itself, and the core
stays white. An engine that multiplied the node's colour in again after the
shader would tint the core as well.

The probe draws a texture whose left half is pure R and right half pure G, tints
it red each of the three ways, and reads the pixels back from a real renderer.
On 2026-10-09, in Godot v4.6.stable.official.89cea1439 on lavapipe's Vulkan
under Xvfb, all three passed: the glow half read (1, 0, 0, 1) and the core half
(1, 1, 1, 1). Run it again after an engine upgrade.

## Drawing light

The game's script, read rather than measured:

- **Supersample.** Each frame is drawn at twice the cell size and shrunk at the
  end.
- **Deposit, then blur once.** Light goes in as points: dots, filled pixel blocks
  and polylines sampled every 0.3 px, into one buffer per channel and blur size.
  Each buffer is blurred once with a Gaussian. Most shapes go in three times, as
  a thin core, a glow and a wide bloom.
- **Soft-clip the sum.** The result is clipped with `1 - exp(-1.35 x)`, so
  overlapping light grows brighter without a flat plateau.
- **Clamp before a fractional power.** Rounding can leave a profile that should
  be 0 slightly negative, a fractional power of that is NaN, and the blur spreads
  one NaN into a black square. The script clamps first, and stops on any NaN.
- **Seed every random draw**, so a rerun writes the same files.

Measured on 2026-10-09 on the reference machine's CPU: two runs of the game's
script into separate folders took 5.58 s and 5.65 s, and all 19 files they wrote
matched byte for byte, between the runs and against the game's committed copies
(`sha256sum`; numpy 2.3.5, scipy 1.16.3, Pillow 12.1.1).

## Effects on the floor

- **Squash floor shapes to half height.** Under a 2:1 dimetric camera a ring on
  the floor is an ellipse twice as wide as it is tall. A horizontal swing at
  chest height squashes the same way.
- **Draw one ring and scale it.** The game drew its floor ring at a 96 px radius
  and scales it about its floor point to each ability's reach, 32, 128 and 160 px
  among them, so it stays centred where the ability lands.
- **Lift effects aimed at a figure.** The game places an effect 24 px above the
  point it is for, which is low for a player whose chest is about 46 px up. So
  the slash, the bolt and the impact carry another 22 px in the picture's own
  offset, and the floor effects carry an offset that puts their floor point back
  on the ground. Neither moves a hitbox.

## Loop only what something else ends

The game frees an effect when its animation finishes, and Godot 4.6's
documentation says of `AnimatedSprite2D`'s `animation_finished`: "This signal is
not emitted if an animation is looping" (read 2026-10-09). An effect freed that
way must not loop, or it never goes. Only the game's bolt loops, and the code
that flies it to its target frees it when it arrives.
