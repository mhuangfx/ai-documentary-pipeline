#!/usr/bin/env python3
"""Test E (local half): ACE-Step v1-3.5B on the 4090.

Run with: vendor/ace_venv/bin/python gen_ace_step.py [cue_name ...]
Checkpoints auto-download to vendor/ace_checkpoints (Apache-2.0 weights,
HF ACE-Step/ACE-Step-v1-3.5B). Cues mirror gen_minimax.py exactly.
Set ACE_CPU_OFFLOAD=1 if VRAM is tight (ComfyUI_h3 holds ~11GB).
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LONG_FORM = os.path.dirname(os.path.dirname(HERE))
CKPT = os.path.join(LONG_FORM, "vendor", "ace_checkpoints")
OUT_DIR = os.path.join(HERE, "ace_step")

SHARED = (
    "instrumental, no vocals, documentary underscore, economics explainer, "
    "understated, sparse midrange, space for narration, clean modern "
    "production, ambient, minimal, background music"
)

CUES = [
    {
        "name": "bed_3min",
        "duration": 180.0,
        "prompt": (
            SHARED + ", soft synth pads, muted piano single notes, quiet "
            "ticking percussion pulse, 85 bpm, curious, methodical, subtle "
            "bass drone, slow chord changes, no climax, constant low "
            "intensity, loopable"
        ),
    },
    {
        "name": "sting_5s",
        "duration": 5.0,
        "prompt": (
            SHARED + ", short transition sting, rising motif, single decisive "
            "low piano note, soft timpani hit, clean tail, act break "
            "punctuation, neutral, restrained"
        ),
    },
]


def main():
    import torch
    from acestep.pipeline_ace_step import ACEStepPipeline

    os.makedirs(OUT_DIR, exist_ok=True)
    only = sys.argv[1:] or None
    cpu_offload = os.environ.get("ACE_CPU_OFFLOAD") == "1"

    t0 = time.time()
    pipe = ACEStepPipeline(
        checkpoint_dir=CKPT,
        dtype="bfloat16",
        torch_compile=False,
        cpu_offload=cpu_offload,
        overlapped_decode=False,
    )
    print(f"pipeline ready in {time.time()-t0:.1f}s (offload={cpu_offload})",
          file=sys.stderr)

    results = []
    for c in CUES:
        if only and c["name"] not in only:
            continue
        out_path = os.path.join(OUT_DIR, c["name"] + ".wav")
        if os.path.exists(out_path):
            print(f"{c['name']}: exists, skipping", file=sys.stderr)
            continue
        torch.cuda.reset_peak_memory_stats()
        t0 = time.time()
        pipe(
            format="wav",
            audio_duration=c["duration"],
            prompt=c["prompt"],
            lyrics="",
            infer_step=60,
            guidance_scale=15.0,
            scheduler_type="euler",
            cfg_type="apg",
            omega_scale=10.0,
            manual_seeds=[42],
            save_path=out_path,
        )
        wall = round(time.time() - t0, 1)
        peak_gb = round(torch.cuda.max_memory_allocated() / 2**30, 2)
        with open(os.path.join(OUT_DIR, c["name"] + "_prompt.txt"), "w") as f:
            f.write(f"model: ACE-Step-v1-3.5B (local, bf16, seed 42, "
                    f"infer_step 60, guidance 15)\nwall_time_s: {wall}\n"
                    f"peak_vram_gb: {peak_gb}\nduration_s: {c['duration']}\n"
                    f"prompt:\n{c['prompt']}\n")
        results.append({"cue": c["name"], "file": out_path, "wall_s": wall,
                        "peak_vram_gb": peak_gb})
        print(f"{c['name']}: {wall}s, peak VRAM {peak_gb} GB", file=sys.stderr)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
