# DESIGN — ai-documentary-pipeline

An overnight pipeline that turns a space or science story into a long-form documentary rough cut
with no human step inside the run. Episode 001 (the Sun and the solar cycle forecast) went from a
fact-checked script to a complete 18-minute rough cut in one night on a single RTX 4090.

This repo is a curated snapshot. A few parts are withheld and replaced by placeholders: the
synthetic host's avatar method (model setup, reference material, prompts), the narration voice
reference, and the tuned script-writer prompts. The design below says where each one plugs in.

## 1. Goal

- Input: a story idea. Output: a watchable 15–25 minute rough cut, with every shot filled, every
  asset's licence on record, and a report of what the run measured.
- Unattended: once the run starts, nothing waits for a person; review happens on the finished cut.
- Local first: narration, host inserts, image-to-video and charts all run on one consumer GPU or
  the CPU. Hosted services were evaluated and kept as fallbacks only.
- Honest output: no claim in the script without a source, no asset without a licence line, and a
  fallback for every shot type so a failed job degrades the cut instead of stopping it.

## 2. Pipeline stages

```
topic radar -> script -> plain-language gate -> fact check -> narration -> host inserts
  -> timeline -> shot list -> b-roll + chart cards (GPU queue / CPU) -> assembly -> report
```

### 2.1 Topic radar — `tools/story_radar.py`
Pulls agency and observatory RSS feeds, arXiv astro-ph category feeds, space-weather alerts, a
near-Earth close-approach feed and a hand-kept mission calendar, then ranks candidates.
- **Decision: timely only counts if we can show it.** The timely composite weights timeliness 0.30
  and *free visuals* 0.25; the visuals score comes from running the asset search on the item's key
  nouns. A story with no public footage cannot win on news value alone.
- **Decision: reject anything a chatbot answers in one screen.** Internal research measured that
  retrieval-style explainer topics lost far more viewing at matched age than narrative
  documentaries. Titles of the "what is / how does" kind with no hook cue score low.
- **Decision: check crowding.** A saturation sub-score looks at how well the topic is already
  covered by existing videos; top hits are hand-checked before a greenlight. (This check is
  withheld in the public version; the stub scores it neutral.)
- Evergreen premises use a second composite (no timeliness) led by visuals and hook strength.
  Premises built around a named, photographable object scored far better on visuals than ones built
  around an abstract measurement, so the object comes first and the number second.
- A "lay-hook" score exists only as a low-weight tie-breaker and is marked unvalidated in the code:
  a test on several hundred titles found no significant separation.

### 2.2 Script — tuned writer prompt (withheld)
An LLM writes the full narration from a research dossier whose unconfirmed facts are tagged.
The structure rules come from internal research on reference documentaries:
- Name the subject within about 10–16 s; state what is unknown or contradictory by sentence 2–3.
- One central question held open and paid off at 55–70% of runtime; local questions answered
  within about 2 minutes; a re-hook at every chapter boundary, roughly every 2.5–3 minutes.
- The newest or strangest finding (the flip) lands at 60–70%; a callback to the cold open at
  85–92%; then a fixed close sequence ending on a tease.
- Titles and thumbnails are written **scene-first**: inventory every picturable moment in the
  story, title from the strongest scene, and require that scene in sentence 1 and in the callback.
  Titling from the thesis produced titles that only made sense to people who already knew the topic.
- Write for the ear: numbers as words, catalogue IDs and acronyms on screen only, no sentence the
  voice has to breathe through.
- **AI tells are kept out of the prompt.** A regex list of spoken-narration tells (colon reveals
  such as "here is the strange part:", signposting, "not X but Y", filler intensifiers) lives in
  `tools/prompts/ai_tells.txt` and is run as a separate checker. The writer prompt instead states
  what to do and why (the text is heard once, through TTS, with no rewind). Reason: naming banned
  phrases inside a generation prompt can prime them. During tuning the checker found 0–1 tells per
  output, and a held-out topic passed on the first try.

### 2.3 Plain-language gate — `tools/script_gate.py`
Stdlib-only, deterministic. Target listener: someone with outdated elementary-school space
knowledge and no technical vocabulary, who will not rewind. Per beat and overall it checks:
- **No unintroduced term.** A transparent list of about 170 jargon terms; each hit is INTRODUCED
  only if a definition cue appears in the same sentence or the 40 words before. Density cap: at
  most one new term per 100 words.
- **Baseline before comparison.** Any "% / times / stronger / record / twice" sentence fails
  unless a number appears in it or the two before it. The comparison's own magnitude and spoken
  dates are stripped first so they cannot count as their own baseline.
- **Why care in the first 30 s.** The opening ~70 words need a strangeness/rarity word and a
  human-stake word.
- **Reading level.** Flesch-Kincaid grade 6–8 per beat, median sentence ≤15 words, none over 25.
- **The 12-year-old test** is flagged on every run as not machine-checkable. The gate narrows down
  where a human should read; it does not replace the read.
- `--fix-suggestions` prints plain-phrase substitutes; `--packaging` / `--packaging-only` check thumbnail text (2–4
  words, a picturable scene noun, no jargon).

The gate exists because an earlier draft passed every structural rule and still lost its listener
in sentence two. Its first run showed the problem was undefined vocabulary and one ungrounded
number, not sentence length, so the rewrite spent its effort on definitions, not on shortening.
Known limits (cue words that fire without defining anything, a fixed term list, naive sentence
splitting) are listed in `tools/script_gate_README.md`.

### 2.4 Fact check — `episodes/ep001_sun/factcheck.md`
A separate LLM pass, independent of the writer, checks every claim against the dossier and fresh
primary sources and edits the script. Episode 001: 84 claims, 62 supported, 12 wrong or overstated
and all fixed. Shot lists carry the same rule in code: `pipeline/validate_shotlist.py` fails any
shot whose `[VERIFY]` claim resolves to a source not yet marked verified, so the report doubles as
the open fact-check list.

### 2.5 Narration — local TTS (voice reference withheld)
`episodes/ep001_sun/split.py` splits the script into narration paragraphs and host lines;
`narration_gen.py` renders each paragraph with a local open-weights TTS model and a fixed seed.
`narration_post.py` then:
- time-stretches each paragraph (no pitch change) toward a target speaking rate, so narration and
  host clips join without a pace jump;
- inserts fixed gaps (paragraph 0.35 s, chapter 0.9 s, scripted beat 0.6 s);
- normalises every paragraph to -16 LUFS integrated.

The TTS licence screen came first: models with non-commercial weights were excluded however good
they sounded.

### 2.6 Host inserts — local video model (method withheld)
Short on-camera host lines (14 in episode 001, 116 s in total) are rendered on the local GPU. Clip
length is derived from word count. A host check (withheld with the host) transcribes every clip with
faster-whisper and scores the heard text against the script line. Camera grammar, taken from a
shot-level study of hosted science videos: one camera per host setup, static by default; when a
move is used, either a small slow punch-in (about +7.5% over ~4 s) or a rare large hard crop
(~30%) at the cut. All of these are post-only (ffmpeg crop/zoompan/overlay), so no second camera
angle has to be generated.

### 2.7 Timeline — `whisper_words.py`, `timeline_build.py`
faster-whisper word timestamps for every narration word, plus host clip in/out points, are written
to `timeline.json`. Every later stage cuts against real spoken word times, not estimates.

### 2.8 Shot list — `shotspec.py`, `shotlist_build.py`, `finalize_shotlist.py`
Every second of narration is covered by a shot with a lane, subject, source and licence (or a
prompt), and the noun it cuts on. B-roll grammar, from a shot-level study of reference documentaries:
- **Cut on the noun.** Measured cuts landed a median 0.24 s from the named word.
- **A spoken number pulls a chart.** Number-heavy passages go to the DIAGRAM lane.
- **A named object gets a literal image** in the same shot or the next one.
- **Real photography when the subject was photographed; motion or visualisation when it never was**
  (no photo exists of a probe in flight).
- Targets by screen time: charts ~42%, 3D/visualisation ~32%, stills ~21%; about 6 cuts per
  minute; median shot 6–8 s; no hold over 30 s.

Lanes, in order of preference: real archive video → real photo animated by local image-to-video
(small camera move, no new content) → real photo with a slow push → local text-to-video for a
generic visual when no real asset exists. Numbers and comparisons always go to code-drawn charts,
because a video model cannot draw correct numbers.

### 2.9 B-roll assets — `tools/space_assets.py`
Searches seven free archives (NASA images, NASA SVS, ESA/Hubble, ESA/Webb, ESO, NOIRLab, HiRISE)
and returns licence, credit and source URL per result. Ground-level photos come from Wikimedia
Commons, filtered to permitted licences. Archive video (NASA SVS visualisations, SDO via
Helioviewer) is the motion spine. Generation fills gaps; it does not carry the show.

### 2.10 Chart cards — `pipeline/chart_style.py`, `episodes/ep001_sun/cardlib.py`, `cards_spec.py`
Rendered headless on the CPU with matplotlib and ffmpeg. One house style lives in module constants
(dark background, one accent colour, no gridlines, one idea per card), so a single change re-skins
every card. Every chart carries a source line; the default reads as an obvious `[VERIFY]`
placeholder so an unchecked chart can't pass for a finished one.

### 2.11 Assembly — `episodes/ep001_sun/assemble.py`
1920x1080, 24 fps. Narration track, host clips with their own audio, b-roll muted, cuts at shot
boundaries. Any shot without a finished clip becomes a still with a slow push, or as a last resort
a dark title card naming the missing shot, so the cut is always complete.

### 2.12 Music (not in run 1)
Planned as a general principle from measured reference documentaries: one continuous low bed about
15–25 dB under the voice for nearly all narration, a few slow texture changes at chapter
boundaries, and deliberate silence kept for the very end.

## 3. Quality gates

| Gate | What is checked | How |
|---|---|---|
| Topic | Timely *and* showable; not chatbot-answerable; not crowded | `story_radar.py` composite + hand check of top saturation hits |
| Script language | Jargon, baselines, hook, reading grade | `script_gate.py`, per beat, PASS/FAIL per rule |
| AI tells | Spoken-narration tells | regex checker over `ai_tells.txt`, outside the writer prompt |
| Facts | Every claim vs dossier and primary sources | independent LLM pass → `factcheck.md`; `[VERIFY]` gate in `validate_shotlist.py` |
| Shot list | Schema, time ordering and overlap, total duration, 3–20 s shot band | `pipeline/validate_shotlist.py` against `pipeline/shotlist.schema.json` |
| Host speech | Heard text matches the script line | faster-whisper + sequence match (host check, withheld) |
| B-roll clips | Photo content preserved, no invented objects | two-frame visual verdict per clip in `broll/verdicts.json`; one re-roll, then fall back a lane |
| Audio | Loudness per paragraph and at joins, speaking rate | LUFS and wpm measured in `narration_post.py` |
| Licences | Every shot has source URL, licence, credit | a licence ledger built from the shot list (kept private) |

## 4. Asset and licence policy

- Allowed: public domain, CC0, CC BY, CC BY-SA, and agency terms that allow reuse with credit.
  Licences are read for the strictest case, commercial publication.
- Never: footage lifted from news broadcasts, documentaries or other videos; agency insignia or
  observatory logos; archives whose terms forbid reuse or state no terms at all.
- **Per-asset, not per-archive.** NASA's image API mirrors partner imagery with its original
  copyright, so `space_assets.py` flags any credit line containing a copyright or ESA token as
  "check per asset" instead of public domain. esa.int carries two licences side by side; the field
  is read on every asset. Where the same image exists on a NASA page (public domain) and an ESA page
  (CC BY with fixed credit wording), the NASA path is preferred.
- NASA SVS visualisations are public domain but some carry licensed music: audio is always stripped.
- Paper figures are not a safe source; arXiv's default licence does not grant reuse.
- Every shot's source, licence and credit line goes into a licence ledger. CC BY and CC BY-SA
  credits must appear on screen in a published cut (not burned into the run 1 test cut).

## 5. Local-first GPU scheduling — `episodes/ep001_sun/queue_run.py`

One RTX 4090, shared with other projects, so the queue is built to be a polite guest:
- **Sequential, file-driven queue.** It re-reads `queue_jobs.json` every loop and runs the first
  job without a logged result, so jobs can be added mid-run and a restart resumes where it stopped.
- **Lock and courtesy check.** Every job runs through a shared GPU claim wrapper. Before each start,
  `gpu_free.sh` lists any other process holding more than 4 GB of VRAM; if there is one, the queue
  waits and polls. It never kills or pre-empts another job.
- **Stop time.** No new job starts after 07:30, so the GPU is free by morning; a `QUEUE_STOP` file
  stops it on demand.
- **Everything is logged** to `logs/gpu_log.csv` (lane, seed, steps, seconds, wall time, status,
  output).
- **CPU work runs alongside.** Chart cards, word alignment and assembly need no GPU and fill the
  time around the queue.
- **Why local:** a failed take costs only GPU time, so re-rolls are routine and a high failure rate
  becomes a scheduling problem, not a blocker. Hosted generation stays the fallback for shots the
  local models can't do.

## 6. What run 1 showed (episode 001, 23:30 → 07:18)

All numbers from `episodes/ep001_sun/run1_report.md`.

| Measure | Run 1 | Target |
|---|---|---|
| Runtime | 18.14 min (narration 937 s, host 116 s) | 15–25 min |
| Cuts | 168 (154 b-roll + 14 host), 9.3/min | ~6/min |
| B-roll shot length | median 6.0 s, mean 6.3 s, max 13.1 s | median 6–8 s, none > 30 s |
| Charts / real archive video / stills share | 50.0% / 33.1% / 15.1% | ~42% / ~32% / ~21% |
| GPU jobs / GPU-hours / job failures | 38 / 6.62 / 0 | — |
| Shots with no finished clip (dark cards) | 0 | 0 |

- **Hosts dominated the GPU:** 14 clips at an average 19.2 min each, 4.48 of 6.62 GPU-hours (68%).
  Animated photos in the fast few-step mode averaged 3.7 min per clip, text-to-video 9.5 min.
- **Few-step vs full-step photo animation:** the fast mode kept framing and simple subjects clean
  but invented new content in faint aurora and fine star trails; the full 20-step mode stayed
  closer to the photo at about 4x the GPU time. Fast mode was used for every animated photo.
- **Content-loss fails:** 5 on the first try; after one re-roll 1 was usable, 2 were trimmed, and
  2 fell back to a still with a slow push.
- **Host speech check:** 13 of 14 clips matched the script at 0.88–1.0; the 14th scored 0.71 only
  because numbers were heard as digits rather than words.
- **Audio:** 70 paragraphs, 2,725 words, rendered in 14 min. The raw TTS spoke at about 203 wpm;
  time-stretching brought every paragraph to 182–202 wpm, but 7 short paragraphs hit the 0.80
  stretch limit. Paragraph loudness spread 0.5 LU, full mix -16.2 LUFS, no jump above 0.6 LU at
  any join. These are measurements only; a listening review was still to come.
- **Assets:** 53 real-video shots from 26 clips (50 NASA public domain, 3 ESA/NASA SOHO); 28 photo
  shots (12 CC BY-SA, 7 CC BY, 3 CC0, 6 public domain); 69 chart cards made in-house.
- **CPU stages are cheap:** assembly ~5 min wall, cards ~2 min, word alignment ~20 min.

## 7. Known limits and next steps

- **Over-cut.** 9.3 cuts/min against ~6: hold chart cards 8–12 s and merge about 40 shots.
- **Chart-heavy.** A number-dense script pushed charts to 50%; add a second pass of real archive
  video for the number-light paragraphs.
- **Queue order.** Hosts ran first and finished at 05:05, leaving 2.4 h for b-roll that needed
  1.2 h. Interleave host and b-roll jobs (or run b-roll first) so one late failure can't starve
  the rest, and trim the +1 s padding on host clip length.
- **Spare GPU time.** ~1.5 h was left before the stop time: room for more animated photos or
  full-step renders for hero shots.
- **Eyeball verdicts don't scale.** Auto-fail animated photos by comparing first and last frames to
  the source photo (SSIM), and add colour-lock / "no new content" lines to the prompts.
- **Pace clamp.** The TTS reads fast; a sentence-level pace target or lower guidance would remove
  the clamp cases.
- **Licence decisions before publishing.** The sunspot-number charts use data under CC BY-NC 4.0:
  get a ruling or switch to schematic curves. The 12 CC BY-SA photos carry share-alike.
- **Real gaps.** Some narrated scenes had no licensed asset (some ground-level aurora locations, the
  real lunar flyby, portraits of the scientists named in the script); the nearest real photo or a
  name card stood in. Music, captions and on-screen credits were not in run 1.
- **Gate limits.** `script_gate.py` is word lists and regex: cue words can fire without defining
  anything, the term list is fixed, and two of its five rules are weak or human-only.
- **Radar blind spots.** No social virality signal, no embargoed papers, no discovery feed for
  comets or interstellar objects; the mission calendar is entered by hand.
