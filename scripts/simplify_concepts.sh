#!/usr/bin/env bash
# Simplify existing concept art into game-ready versions, one file per source.
#
#   scripts/simplify_concepts.sh ../concept_art/singles/unit_*.png
#   DENOISE=0.93 scripts/simplify_concepts.sh ../concept_art/singles/hero_*.png
#
# Outputs land in output/simplified/<source name>.png — named after the source,
# not the edit counter, because ComfyUI's SaveImage counter (edit_00001_,
# edit_00002_ …) records nothing about which input or settings produced it and
# becomes unreadable within a dozen runs.
#
# DENOISE is the style knob and it behaves as a cliff, not a slider:
#   <= 0.70  the source dominates; almost nothing is simplified
#   0.85     painterly rendering kept, clutter genuinely reduced   <- default
#   0.93     pushed further to clean game-ready forms, still shaded
#   1.00     the model's style prior takes over and returns flat vector art,
#            no matter how many times the prompt says "not cartoon"
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs output/simplified
DENOISE="${DENOISE:-0.85}"
LOG="logs/simplify-$(date +%Y%m%d-%H%M%S).log"
PROMPT_TEXT=""
[ -n "${PROMPT_FILE:-}" ] && PROMPT_TEXT=$(cat "$PROMPT_FILE")

# The prompt can be overridden for sources that need a harder push:
#   PROMPT_FILE=/path/to/prompt.txt DENOISE=0.93 scripts/simplify_concepts.sh ...
# The cliff moves with how busy the source is. The four unit portraits simplify
# well at 0.85 and go flat at 1.0; the eight lords are so dense with chains and
# filigree that 0.85 barely touches them, 0.93 is right, and 0.97 is already flat
# vector art with the goggles and lantern gone. Test one before batching.
PROMPT='Redraw this character as a cleaner game-ready version of the same illustration, keeping it recognisably the same person. Reduce the clutter: cut the many small glass vials, pouches, chains and hanging ornaments down to a few larger ones, replace the tiny buckles, rivets and engraved filigree with a few larger clean shapes, and give every cloth edge a straight clean hem with no ragged torn tatters. Simplify the armour and clothing into fewer, larger, bolder forms with a clear readable silhouette. KEEP the same face, hair and expression, the same standing pose, the same held items, the same colour palette and the same background. KEEP the full painterly rendering with real material contrast between metal, leather and cloth, with proper shading, highlights and surface texture. Do NOT flatten it into untextured plastic, do NOT remove the colours, do NOT make it a cartoon or a smooth clay toy.'

echo "denoise=$DENOISE  ->  output/simplified/   (log: $LOG)"
for src in "$@"; do
    name=$(basename "$src"); name="${name%.*}"
    printf '%-22s ' "$name"
    if python3 scripts/run_workflow.py workflows/api/img_edit_qwen.json \
            --image "$src" \
            --set "Positive.prompt=${PROMPT_TEXT:-$PROMPT}" \
            --set "denoise=$DENOISE" \
            --set "Save.filename_prefix=simplified/$name" >>"$LOG" 2>&1; then
        echo "ok"
    else
        echo "FAILED (see $LOG)"
    fi
done
echo "done"
