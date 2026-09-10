# Models and weights

Weights live outside the repo and outside the image. `MODELS_DIR` in `.env` says
where. Expect about 200GB with everything fetched.

```sh
scripts/fetch_models.py                       # report on the core group
scripts/fetch_models.py --all                 # report on everything
scripts/fetch_models.py --download            # fetch the missing core models
scripts/fetch_models.py --download --group hunyuan --group qwen
scripts/fetch_models.py --list-groups
scripts/fetch_models.py --licenses
```

`models.json` is the manifest. The container reads it on boot and names anything
missing **before** the server starts, rather than letting it turn up as a red
node an hour later.

## Groups

| Group | What it buys you | Size |
|---|---|---|
| `core` | SDXL, TripoSR, TripoSG | ~21GB |
| `qwen` | Qwen-Image plus the 4 step Lightning LoRA. Apache 2.0, the default concept generator | ~20GB |
| `qwen_edit` | Qwen-Image-Edit, for changing one part of an image | ~19GB |
| `hunyuan` | Hunyuan3D 2.1 shape generation and texturing. Best meshes. Territory limited licence | ~25GB |
| `instantmesh` | Zero123++ multiview into InstantMesh | ~10GB |
| `trellis` | TRELLIS image to 3D | ~5GB |
| `mvadapter` | Multiview and texturing over SDXL | ~17GB |
| `unique3d` | Unique3D and CharacterGen chain | ~24GB |
| `extra` | LGM, CRM, TriplaneGaussian, PartCrafter | ~21GB |
| `gated` | StableFast3D. Accept the licence on the hub first | ~1GB |
| `noncommercial` | Excluded from `--all`, needs an explicit flag | small |

## Size matching, not existence checks

A file counts as present only when its size matches what the hub reports. A half
finished download is fetched again rather than silently loaded and crashed on.
Downloads resume.

Set `HF_TOKEN` for the gated group.

## The configs the pack expects to already exist

The fetcher also seeds a config skeleton of 231 JSON and YAML files into
`$MODELS_DIR/3d_checkpoints`.

This matters because the 3D pack downloads **weights** only and expects the
configs to be on disk already. The compose file mounts our directory over the
pack's own checkpoints tree, which would otherwise hide the configs it ships. The
pack hardcodes that path inside its node directory, which is why the mount exists
at all.

## Licences in one line each

Run `scripts/fetch_models.py --licenses` for the authoritative list. The three
that are not MIT or Apache:

- **Hunyuan3D 2 and 2.1**: royalty free but territorially limited. Does not apply
  in the EU, UK or South Korea.
- **StableFast3D**: free under 1 million dollars annual revenue.
- **RMBG-1.4**: non commercial without a paid agreement. Not needed. Hunyuan3D
  and TripoSG remove backgrounds internally with an Apache 2.0 tool.

Full detail, including why rendering to 2D does not sidestep a territory clause,
is in [licensing](/guide/licensing).
