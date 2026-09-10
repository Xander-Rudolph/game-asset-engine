#!/usr/bin/env bash
# Generate concept images from a prompt directory, in the established art style.
#
#   scripts/generate_concepts.sh prompts/buildings
#   scripts/generate_concepts.sh prompts/creatures golem chimera
#   WIDTH=1472 HEIGHT=1104 scripts/generate_concepts.sh prompts/buildings
#
# A prompt directory holds one <name>.txt per subject plus underscore-prefixed
# shared files: _style.txt (pasted into each subject at authoring time) and
# _negative.txt (passed as the negative prompt here).
#
# Uses txt2img_qwen.json (20 steps, cfg 4.0), NOT the 4-step fast workflow: the
# negative prompt is what keeps tatters, clutter and cartoon styling out, and at
# the fast workflow's cfg 1.0 a negative prompt does nothing at all.
#
# Buildings want landscape (isometric dioramas are wider than tall); characters
# and creatures want Qwen's 3:4 portrait, which is the workflow default.
set -euo pipefail
cd "$(dirname "$0")/.."
DIR="${1:?usage: generate_concepts.sh <prompt-dir> [name...]}"; shift
mkdir -p logs "output/$(basename "$DIR")"
LOG="logs/concepts-$(basename "$DIR")-$(date +%Y%m%d-%H%M%S).log"
NEG=""; [ -f "$DIR/_negative.txt" ] && NEG=$(cat "$DIR/_negative.txt")
# A subject can override the shared negative with <name>.neg.txt. The
# creature lair needed it: the shared building style talks about roofs,
# chimneys and lit windows, and that preamble put a cottage on top of what
# should be a bare cave mouth however firmly its own line said otherwise.
OUT="output/$(basename "$DIR")"
NAMES=("$@")
if [ ${#NAMES[@]} -eq 0 ]; then
    for f in "$DIR"/*.txt; do b=$(basename "$f" .txt);
        case "$b" in _*|*.neg) ;; *) NAMES+=("$b") ;; esac
    done
fi
echo "${#NAMES[@]} subject(s) -> $OUT/   (log: $LOG)"
for n in "${NAMES[@]}"; do
    printf '%-22s ' "$n"
    args=(--prompt "$(cat "$DIR/$n.txt")" --set "Save.filename_prefix=$(basename "$DIR")/$n")
    subneg="$NEG"; [ -f "$DIR/$n.neg.txt" ] && subneg=$(cat "$DIR/$n.neg.txt")
    [ -n "$subneg" ] && args+=(--negative "$subneg")
    [ -n "${WIDTH:-}" ] && args+=(--set "Latent.width=$WIDTH")
    [ -n "${HEIGHT:-}" ] && args+=(--set "Latent.height=$HEIGHT")
    if python3 scripts/run_workflow.py workflows/api/txt2img_qwen.json --retries 3 "${args[@]}" >>"$LOG" 2>&1; then
        echo ok
    else
        echo "FAILED (see $LOG)"
    fi
done
echo done
