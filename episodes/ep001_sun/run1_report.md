# Episode 001 (Sun) overnight run 1 report (2026-10-12 23:30 to 2026-10-13 07:18)

Deliverables: `rough_cut_1080p.mp4` (1920x1080, 24 fps, 406 MB), `rough_cut_720p.mp4` (12.98 MB, 50 kbps video + 40 kbps mono audio, so image quality is poor by design), `shotlist.json` / `shotlist_final.json`, `timeline.json`, `assets/ledger.csv`, logs in `logs/` (`gpu_log.csv` has every GPU job). No music, no captions, b-roll muted.

## Totals
- Runtime 18.14 min (1088 s): narration 937 s, host 116 s, gaps the rest. Cut is complete, every shot filled (no "missing" cards).
- 154 b-roll shots + 14 host clips = 168 cuts, 9.3 cuts/min (target about 6: **over-cut**). Median b-roll shot 6.0 s (target 6-8), mean 6.3 s, max 13.1 s, no hold over 30 s.
- Mix by share of b-roll screen time (972 s), target from research note 27 (private) in brackets:

| Lane | Shots | Seconds | Share | Target |
|---|---|---|---|---|
| DIAGRAM | 69 | 486 | 50.0% | ~42% |
| REAL_VIDEO (NASA SDO/SOHO/SVS archive) | 53 | 321 | 33.1% | ~32% (3D vis) |
| PHOTO_STILL (slow push) | 16 | 77 | 8.0% | ~21% together with PHOTO_H3 |
| PHOTO_H3 | 12 | 69 | 7.1% | (stills 15.1% total) |
| H3_T2V | 4 | 19 | 1.9% | other ~5% |

DIAGRAM is over because the script is number-dense (research note 50 (private) saw the same). About 20 DIAGRAM shots were already swapped to real video or stills during shot-list review (from 56% to 50%); further moves need more assets.

## GPU (RTX 4090, shared; ComfyUI_h3 :8199, every job through `gpu_claim.sh`, no other process held >4 GB when I started a job)
- 38 jobs, 6.62 GPU-hours, 0 job failures. Eyeball verdicts (2 frames each) in `broll/verdicts.json`.

| Lane | Jobs | Avg wall per job | Per output second |
|---|---|---|---|
| Host ref2va method C, 20 steps | 14 | 19.2 min (4.48 h total) | 2.3-2.8 min/s (7-10 s clips 15-25 min) |
| PHOTO_H3 FL2VA turbo (4 steps) | 19 (12 used + re-rolls) | 3.7 min | 0.4-0.7 min/s once the model is loaded; first job 10.3 min incl. model swap |
| H3 text-to-video, 20 steps | 4 | 9.5 min | 1.4-2.1 min/s |
| PHOTO_H3 20-step (comparison only, not in cut) | 1 | 20.6 min for 8.7 s | 2.4 min/s |
- Turbo decision: first PHOTO_H3 clip (S001 aurora over palms, 8.7 s) was photoreal, no warping, palms/framing preserved, but the aurora itself invents new content (green arcs, fresh pillars). 20-step comparison (`broll/clips/cmp_S001_20step.mp4`) keeps the photo's magenta aurora and invents less, at about 4x the GPU time. I used turbo for all PHOTO_H3 (owner can weigh in).
- Failures and re-rolls (verdict "fail" = photo content lost): S146 (green arcs replaced the pink sky; re-roll with colour-lock prompt OK), S003, S099, S065, S138 (Gran Canaria and star-trail photos: the aurora fades out, or the satellite trails vanish and the sky turns green). Re-rolls: S146r usable, S065r and S138r trim (trails kept, sky greener), S003r and S099r still fail, so those two fell back to PHOTO_STILL (Gran Canaria photo, slow push). No shot fell back to a dark card.
- Turbo is cleaner than expected on subjects with simple structure (pylons, rocket launch, palms) and weakest on faint aurora and fine star trails.
- Host: all 14 clips rendered, identity held on spot-checked frames (H01, H02), speech checked with faster-whisper small.en against the script: 13 of 14 match 0.88-1.0 (H03 0.71 is digit-versus-word spelling "115"/"233", heard text is correct). Confirmation round in `tests/host_avatar/voice_std/results.md` was PASS. Host clips are 1344x768 upscaled to 1080p.
- Fallbacks: none to dark cards; 2 PH to PHOTO_STILL (above).

## Assets (every shot in `assets/ledger.csv`: shot id, file, source URL, licence, credit)
- REAL_VIDEO 53 shots from 26 distinct clips: NASA public domain 50 (SDO via Helioviewer, NASA SVS visualisations incl. May 2024 magnetosphere, Feb 2022 satellite loss, ISS aurora, Artemis II beyond the magnetosphere), ESA/NASA SOHO 3. 18 of the 53 are NASA SVS V09 clips (dynamo, PFSS field, May 2024 storm).
- Photos: 28 shots (16 still + 12 H3-animated) from Wikimedia Commons / NASA: CC BY-SA (4.0/2.0) 12, CC BY 4.0/2.0 7, CC0 3, public domain 6. CC BY and CC BY-SA need credit lines in the final video (ledger has them; not burned in this test cut). CC BY-SA applies share-alike to the photo, flagged for the owner.
- DIAGRAM 69 cards, own work. **Flag:** charts of sunspot number use SILSO/SIDC data, licence CC BY-NC 4.0. Fine for a test cut, needs an owner decision (or a switch to schematic curves) before publishing.
- H3 text-to-video 4 clips (fridge magnet, season time-lapse, dough rising, sat-nav): generated, no real asset.
- Gaps (no real asset for the narrated thing): Florida aurora (Phoenix photo substituted), Teide/Canary rooftop aurora (Gran Canaria, no town), red rooftops over Mexico (magenta palm photo), Starlink fairing/train (star-trail mosaics), portraits of McIntosh/Leamon/Chapman (none licensed; name cards used), Schwabe drawing (not used), real Orion lunar flyby (none; used launch photo, SVS simulation not cut in), polar-view magnetogram (SVS polar-field tour used), main Brussels observatory building (planetarium photo, 2.4 s + 5.9 s).

## Audio
- Narration Chatterbox Voice A, ref_all.wav, exaggeration 0.5, cfg 0.5, sentence chunks, seed 7000+paragraph index, 70 paragraphs, 2725 words, 937 s, generated in 14 min on GPU (about 1.1x real time). Raw speech-only pace averaged 203 wpm (range 163-253); atempo (0.80-1.11, no pitch change) brought every paragraph to 182-202 wpm; 7 short paragraphs hit the 0.80 clamp and still run faster than 182 (N05, N12, N13, N16, N33, N43, N64).
- Loudness: paragraphs -16.6 to -16.06 LUFS integrated (spread 0.5 LU); full mix -16.2 LUFS integrated, LRA 2.8 LU. Host audio normalised to -16 LUFS in the mix. No jump larger than 0.6 LU at any join by measurement. I have not listened; owner ears decide on the prosody and whether host-to-narration timbre joins sound consistent.
- Gaps: paragraph 0.35 s, chapter 0.9 s, BEAT 0.6 s (also leading BEAT in N52 and N67).

## What would make run 2 faster or better
1. Hosts dominated the night (4.48 of 6.62 GPU-h, 68%) and finished at 05:05, leaving 2.4 h for b-roll that only needed 1.2 h (turbo is 5x cheaper per second than ref2va). Run host clips and b-roll interleaved, or run b-roll first, so a late host failure cannot starve the rest. Host clip seconds could drop by trimming the `words/3 + 1` formula (+1 s padding on 14 clips = 14 s = 36 GPU-min).
2. GPU had about 1.5 h idle margin before 07:30: run 2 can raise PH from 12 to about 40 clips (3.7 min each) or use 20 steps (2.4 min/s) for the hero shots.
3. Over-cut: 9.3 cuts/min against a target of 6. Merge about 40 cards/shots, or hold card shots at 8-12 s.
4. DIAGRAM share 50% vs 42%: add a second real-video pass (about 45 s of SVS/SDO) for the number-light paragraphs.
5. Turbo drift: add a colour-lock and "no new content" prompt line; check the first and last frame automatically against the source photo (SSIM) to auto-fail fades (S003, S099) instead of eyeballing.
6. Assembly takes about 5 min wall (95 CPU-min), cards 2 min wall, whisper alignment about 20 min for 70 paragraphs (CPU, faster-whisper large-v3 int8): all cheap, fits in a pre-GPU window.
7. Chatterbox speaks 203 wpm raw: slowing by up to 20% worked; a lower cfg or a sentence-level pace target would remove the 0.80 clamp cases.
8. Tooling notes: `faster_whisper` fails on file input in vendor/venv_eval (av `metadata_errors`), feed arrays; `pkill -f` on a script name kills the invoking shell.
