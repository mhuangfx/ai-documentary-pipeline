# Test E — music: ACE-Step (local) vs minimax/music-3.0 (Atlas) — run log

Date: 2026-09-01. Spec: `research note 19 (private)` Test E — one ~3-min ambient bed
+ one ~5-s act-break sting per lane, instrumental, judged under Test-A narration.
All raws have a `*_-22lufs.wav` copy alongside (two-pass ffmpeg loudnorm, I=-22, TP=-1.5, LRA=11 — project music level).

## Lane 1 — ACE-Step (local, RTX 4090)

- Install: `vendor/ace_venv` (isolated venv, Python 3.12, torch 2.13.0+cu130) + `vendor/ACE-Step`
  (github.com/ace-step/ACE-Step @ 1bee4c9, 2026-02-15, ace_step 0.2.0). Weights
  `ACE-Step/ACE-Step-v1-3.5B` auto-downloaded to `vendor/ace_checkpoints`. Total vendor/: 14 GB.
- **License: code Apache-2.0 (GitHub API spdx_id), weights Apache-2.0 (HF model card tag
  `license:apache-2.0`, ACE-Step/ACE-Step-v1-3.5B). Commercial use OK — no research note 18 (private)-style blocker.**
- Settings: bf16, no cpu_offload, infer_step=60, guidance_scale=15, euler/apg, seed 42.
  Generator: `gen_ace_step.py`.
- Ran alongside action-sequence-pipeline's idle ComfyUI_h3 server (11 GB VRAM resident) — fit without offload.

| cue | file | asked | got | gen time | peak VRAM (torch) |
|---|---|---|---|---|---|
| bed | `ace_step/bed_3min.wav` | 180 s | 179.9 s | 19.8 s | 10.41 GB |
| sting | `ace_step/sting_5s.wav` | 5 s | 4.9 s | 6.4 s | 7.52 GB |

- First call pays ~119 s model load; generation itself is seconds. Duration control is exact.
- Marginal cost: $0.

## Lane 2 — minimax/music-3.0 (Atlas Cloud API)

- Lane: `POST /model/generateAudio`, model `minimax/music-3.0`, is_instrumental, wav 44.1 kHz —
  same lane as `action-sequence-pipeline/gen_music_beds.py`, but via long_form's own client `gen_minimax.py`
  (action-sequence-pipeline is read-only; own spend log `minimax_spend.jsonl`). $0.15/generation flat.

| cue | file | asked | got | wall time | cost |
|---|---|---|---|---|---|
| bed | `minimax/bed_3min.wav` | 180 s | 132.8 s | 189.8 s | $0.15 |
| sting take 1 | `minimax/sting_5s.wav` (raw) | 5 s | 76.9 s | 125.2 s | $0.15 |
| sting retry (`duration:5` param) | `minimax/sting_5s_retry.wav` | 5 s | 91.0 s | 118.6 s | $0.15 |
| sting deliverable | `minimax/sting_5s_trim.wav` | — | 5.4 s | (cut from take 1) | $0 |

- **Total API cost: $0.45** (3 × $0.15; logged in `minimax_spend.jsonl` with prediction ids).
- **Quirk: minimax ignores duration entirely** — prompt-level "5 seconds" and a `duration:5`
  payload param both produced 77–91 s tracks; the 3-min ask produced 132.8 s. Stings must be
  cut from a longer take (trim = loudest onset at 59.9 s, 0.15 s fade-in / 1 s fade-out).
  Beds shorter than asked must be looped/crossfaded to length.

## Objective read (not a verdict — owner judges by ear under narration)

| file | energy 300 Hz–3 kHz (voice band) | energy < 300 Hz |
|---|---|---|
| ACE bed | 58 % | 39 % |
| minimax bed | 20 % | 80 % |

The minimax bed sits mostly below the narration band; the ACE bed carries far more midrange
and will compete with voice-over unless EQ-ducked. ACE bed is continuous (no dropouts; only
the final fade-out second is quiet).

## Quirks summary

- ACE-Step install: pip `--no-cache-dir` needed (first install died on a wheel sha256 mismatch);
  torchaudio 2.11 needs `torchcodec` installed or `.save()` raises (added to venv).
- minimax: no duration control (see above); output loudness ~-15 LUFS, needs the normalize pass.
- ACE-Step: instrumental via empty `lyrics=""`; native output 48 kHz, minimax 44.1 kHz.
- Normalize helper: `normalize_lufs.sh` (bash sed pass is brittle on some files; python
  fallback in this log's session was used for 3 minimax files — consider porting fully to python).
