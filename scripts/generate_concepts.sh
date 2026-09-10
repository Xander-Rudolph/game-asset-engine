#!/usr/bin/env bash
# Generate concept images from a prompt directory, in the established art style.
#
#   scripts/generate_concepts.sh prompts/buildings
#   scripts/generate_concepts.sh prompts/creatures golem chimera
#   WIDTH=1472 HEIGHT=1104 scripts/generate_concepts.sh prompts/buildings
#
# A prompt directory holds one <name>.txt per subject plus underscore-prefixed
# shared files: _style.txt (the shared technique and art direction) and
# _negative.txt (passed as the negative prompt here).
#
# The style is composed with the subject AT RUN TIME, not pasted into each
# subject file. That matters: the style used to be copied into all 32 subject
# files by hand, which meant changing the art direction was a 32-file edit and
# every subject silently carried whatever project it was written for. Now
# _style.txt is the single place art direction lives.
#
# Override the style file per run with STYLE=, which is how an alternate in the
# same folder gets used:
#
#   STYLE=prompts/creatures/_hstyle.txt scripts/generate_concepts.sh prompts/creatures homunculus_a
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
STYLE_FILE="${STYLE:-$DIR/_style.txt}"
STYLE_TEXT=""; [ -f "$STYLE_FILE" ] && STYLE_TEXT=$(cat "$STYLE_FILE")
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
    # Style first, then the subject clause, matching how the prompts are written.
    subject=$(cat "$DIR/$n.txt")
    if [ -n "$STYLE_TEXT" ]; then full="$STYLE_TEXT $subject"; else full="$subject"; fi
    args=(--prompt "$full" --set "Save.filename_prefix=$(basename "$DIR")/$n")
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
