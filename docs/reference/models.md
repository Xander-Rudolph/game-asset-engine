# Models and weights

Weights live outside the repo and outside the image. `MODELS_DIR` in `.env` says
where. Expect about 200GB for `--all`, which leaves out the `gated` and
`noncommercial` groups.

```sh
scripts/fetch_models.py                       # check the core group
scripts/fetch_models.py --all                 # check all but two groups (above)
scripts/fetch_models.py --download            # fetch the missing core models
scripts/fetch_models.py --download --group qwen --group trellis --group hunyuan
scripts/fetch_models.py --list-groups
scripts/fetch_models.py --licenses
```

Only `--download` fetches weights, but a check still writes to disk. Every mode
except `--licenses` and `--list-groups` first creates `MODELS_DIR` if it is
missing and copies in any config files it lacks, as described
[below](#the-configs-the-pack-expects-to-already-exist).

The [first asset walkthrough](/guide/first-asset) needs `qwen`, `trellis` and
`hunyuan`, which is the fourth line above. `core` holds SDXL, TripoSR and
TripoSG, and the walkthrough uses none of them.

`models.json` is the manifest. The container reads it on boot and names anything
missing **before** the server starts, rather than letting it turn up as a red
node an hour later.

## Groups

| Group | What it buys you | Size |
|---|---|---|
| `core` | SDXL, TripoSR, TripoSG | ~20GB |
| `qwen` | Qwen-Image, plus the 4 step Lightning LoRA and a pre-merged 4 step copy. Apache 2.0, the default concept generator | ~48GB |
| `qwen_edit` | Qwen-Image-Edit, for changing one part of an image | ~19GB |
| `hunyuan` | Hunyuan3D 2.1 shape generation and texturing. Best meshes. Territory limited licence | ~24GB |
| `instantmesh` | Zero123++ multiview into InstantMesh | ~10GB |
| `trellis` | TRELLIS image to 3D, both branches | ~9GB |
| `mvadapter` | Multiview and texturing over SDXL | ~17GB |
| `unique3d` | Unique3D and CharacterGen chain | ~23GB |
| `extra` | LGM, CRM, TriplaneGaussian, PartCrafter | ~21GB |
| `music` | ACE-Step 1.5 turbo, text to music. MIT, and its model card allows commercial use of the music | ~10GB |
| `gated` | StableFast3D. Accept the licence on the hub first | ~4GB |
| `noncommercial` | Excluded from `--all`, needs an explicit flag | under 1GB |

## Size matching, not existence checks

A file counts as present only when its size matches what the hub reports. A
partial download is fetched again, rather than loaded without warning and then
crashing. Downloads resume.

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

Run `scripts/fetch_models.py --licenses` for the authoritative list. Every model
not listed below is MIT, Apache 2.0 or BSD. The four that are not:

- **Hunyuan3D 2 and 2.1**: royalty free but territorially limited. Does not apply
  in the EU, UK or South Korea.
- **StableFast3D**: free under 1 million dollars annual revenue.
- **RMBG-1.4**: non commercial without a paid agreement. Not needed. Hunyuan3D
  and TRELLIS remove backgrounds internally with rembg (MIT) and its u2net model
  (Apache 2.0).
- **SDXL and SD 1.5**: OpenRAIL-M (OpenRAIL++-M for SDXL). Commercial use of the
  images is permitted. The use restrictions travel with the model.

TripoSG is listed as MIT, and it is MIT upstream. But its copy in this pack
ships a Tencent licence file with the same EU, UK and South Korea exclusion, and
which licence governs it is unresolved. See
[licensing](/guide/licensing#the-licences-of-the-tools-themselves).

Full detail, including why rendering to 2D does not sidestep a territory clause,
is in [licensing](/guide/licensing).
