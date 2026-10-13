#!/usr/bin/env bash
# Two-pass ffmpeg loudnorm to the project's music level (-22 LUFS integrated).
# For each */<cue>.wav writes <cue>_-22lufs.wav alongside, and prints measured
# input/output loudness. Usage: ./normalize_lufs.sh [dir ...]  (default: both lanes)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET_I=-22
TARGET_TP=-1.5
TARGET_LRA=11

for dir in "${@:-$HERE/ace_step $HERE/minimax}"; do :; done
DIRS=("$@")
[ ${#DIRS[@]} -eq 0 ] && DIRS=("$HERE/ace_step" "$HERE/minimax")

for d in "${DIRS[@]}"; do
  for f in "$d"/*.wav; do
    [ -e "$f" ] || continue
    case "$f" in *_-22lufs.wav) continue;; esac
    out="${f%.wav}_-22lufs.wav"
    [ -e "$out" ] && { echo "skip (exists): $out"; continue; }
    # pass 1: measure
    json=$(ffmpeg -hide_banner -nostats -i "$f" \
      -af "loudnorm=I=$TARGET_I:TP=$TARGET_TP:LRA=$TARGET_LRA:print_format=json" \
      -f null - 2>&1 | sed -n '/{/,/}/p')
    mi=$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['input_i'], d['input_tp'], d['input_lra'], d['input_thresh'], d['target_offset'])")
    read -r II ITP ILRA ITH OFF <<< "$mi"
    # pass 2: apply with measured values (linear mode)
    ffmpeg -hide_banner -nostats -loglevel error -i "$f" \
      -af "loudnorm=I=$TARGET_I:TP=$TARGET_TP:LRA=$TARGET_LRA:measured_I=$II:measured_TP=$ITP:measured_LRA=$ILRA:measured_thresh=$ITH:offset=$OFF:linear=true" \
      -ar 48000 "$out" || { echo "FAIL: $f"; continue; }
    echo "$(basename "$f"): input_i=$II LUFS -> normalized to $TARGET_I LUFS -> $out"
  done
done
