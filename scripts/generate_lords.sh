#!/usr/bin/env bash
# Generate the eight guild lords from scratch (not by editing the concept art).
#
#   scripts/generate_lords.sh                # all eight
#   scripts/generate_lords.sh salt sulfur    # named ones
#
# Uses txt2img_qwen.json (20 steps, cfg 4.0) and NOT txt2img_qwen_fast.json,
# because the negative prompt is load-bearing here and the fast workflow's
# 4-step Lightning LoRA runs at cfg 1.0 where negatives do nothing.
#
# Why the forbidden things live in prompts/lords/_negative.txt and are never
# mentioned in the positive: writing "no ragged tatters, no tears, no frayed
# edges" in the POSITIVE prompt produced a MORE tattered coat every time. Naming
# a concept summons it however you negate it. The positive describes what the
# coat should be ("a smooth even curved hem… pristine, freshly tailored"); the
# negative carries what it must not be.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs output/lords_scratch
LOG="logs/lords-$(date +%Y%m%d-%H%M%S).log"
NEG=$(cat prompts/lords/_negative.txt)
LORDS=("$@")
[ ${#LORDS[@]} -eq 0 ] && LORDS=(aether aurum entropy mercury panacea salt sulfur vitriol)
echo "log: $LOG"
for name in "${LORDS[@]}"; do
    printf '%-10s ' "$name"
    if python3 scripts/run_workflow.py workflows/api/txt2img_qwen.json --retries 3 \
            --prompt "$(cat "prompts/lords/$name.txt")" --negative "$NEG" \
            --set "Save.filename_prefix=lords_scratch/$name" >>"$LOG" 2>&1; then
        echo ok
    else
        echo "FAILED (see $LOG)"
    fi
done
echo done
