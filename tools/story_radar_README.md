# story_radar.py

Answers "how should we generate a story?" with a ranked, scored shortlist instead of a guess.
Priority 1: timely items (news last ~90d, or events in the next ~90d) that we ALSO have free
visuals for. Priority 2: evergreen, hookable premises. See research note 39 (private) for the first real run.

## Usage

```
python3 tools/story_radar.py pull      --days 90 --out out/39_pull_raw.json
python3 tools/story_radar.py score     --in out/39_pull_raw.json \
                                        --out out/39_scored.json --shortlist-n 25
python3 tools/story_radar.py evergreen --out out/39_evergreen.json
python3 tools/story_radar.py all       --days 90 --out out/39_radar_run.json \
                                        --shortlist-n 25
```
`--no-visuals` / `--no-saturation` skip the two expensive checks (useful for a fast dry run).

## What `pull` fetches

11 RSS/Atom feeds (NASA news/press/science/IOTD, APOD, esahubble, esawebb, ESA activities, ESO
news+announcements, NOIRLab) verified live 2026-09-27; 5 arXiv astro-ph category RSS feeds
(EP/GA/SR/HE/CO); NOAA SWPC space-weather alerts (JSON, filtered to G3+/major only -- routine
K-index alerts fire dozens/day and would flood the shortlist); JPL SSD `cad.api` close-approach
data (live NEO flybys, dist < 0.02 AU, next N days); and a hand-maintained `MISSION_CALENDAR`
(launches/flybys/arrivals/data releases, WebFetch/WebSearch-sourced, UNVERIFIED items flagged).

**Dead ends (see `DEAD_SOURCES` in the script):** JPL news RSS (403), the STScI/Hubble "feed"
(HTML, not RSS), an SVS "recent" RSS (404, doesn't exist), MPC recent-discoveries (HTML table
only, no RSS/JSON -- skipped per spec), and arXiv's `api/query` endpoint (HTTP 406 from this
network, every attempt, http/https, curl/urllib) -- per-category RSS is used instead, but it
publishes nothing on weekends (`<skipDays>` excludes Sat/Sun); a Sunday run gets zero arXiv items.

## Scoring

Seven sub-scores: **timeliness** (0-10, linear decay to 0 at 90 days, either direction),
**source tier** (0-10, 3=mission/agency press -> 10, 2=paper-with-press -> 6, 1=blog -> 3),
**visuals** (0-10, runs `space_assets.py search` on the item's key nouns across nasa/svs/esahubble/
esawebb/eso/noirlab, `--min-width 1920`; 0 hits = 0, 1-2 = 4, 3-5 = 7, 6+ = 10), **hook** (0-10,
keyword hits from a contradiction/unknown/scale word list, research note 29 (private) + research note 31 (private) Part 2 --
**no longer rewards a number in the title/summary**: research note 43 (private) rule 4 / 38 T4 found only 1/20
title winners carry a number, and research note 47 (private) step 7.4 told this scorer to drop the bonus),
**chatbot-test** (0-10, proxy for research note 24 (private)'s rule: a title matching `what is/how does/why
does...` with no hook cue scores 2/10 -- likely answered in one screen; a hook cue present scores
9/10), **saturation** (0-10, how crowded the topic already is on video platforms; withheld in this
public version, so it always scores a neutral 5), and **lay_hook** (0-1, see below).

**lay_hook (UNVALIDATED, low weight).** `lay_hook = 0.6*picturability + 0.4*question-form`
(research note 46 (private) section 9's formula; word lists copied from research note 46 (private) section 2.2). research note 46 (private)
tested this against 601 titles / n=205 within-channel hit-miss pairs and found **no significant
separation**: picturability is a weak positive trend that does not clear significance (p=0.16-0.21)
and *runs backwards* in the n=12 newcomer-breakout case that matters most at zero subs;
question-form is the only feature that is even borderline significant (p=0.052). The chairman
ruling (research note 47 (private) step 7): scene-first titling is the validated **process** rule; lay_hook is a
low-weight **tie-breaker only**, explicitly marked UNVALIDATED here and in research note 46 (private) itself --
do not read a lay_hook difference as a finding.

Composite weights (sum to 1.0): **Timely** -- timeliness 0.30, visuals 0.25, tier 0.15, hook 0.10,
saturation 0.10, chatbot 0.05, lay_hook 0.05. **Evergreen** (no timeliness/tier -- not news) --
visuals 0.35, hook 0.30, chatbot 0.15, saturation 0.15, lay_hook 0.05. (lay_hook's 0.05 was carved
out of `hook`'s prior weight in both composites, so the totals still sum to 1.0. Note this is a
much lower weight than research note 47 (private) step 7.4's own proposed 0.15-0.20 for a *future, separately
validated* premise-bank composite -- that proposal is untested and not what's implemented here.)

Runtime cost bound: visuals+saturation are expensive (subprocess + network per item), so `score`
only runs them on the top N items by a cheap preliminary score (timeliness+tier+hook); items below
the cutoff keep a `null` composite score and a note, not a fabricated one.

## Scene seeds (`--scenes`)

`score`, `evergreen` and `all` all accept `--scenes`, which prints (research note 47 (private) step 1, automated
first pass) each top candidate's 3 most concrete nouns/places/colours -- e.g.
`[scene seeds] B7: Phobos, moon, spiral` -- as raw material for scene-first titling. This is a
crude heuristic (color/scene-noun/nameable-object word lists, then capitalized-word fallback), not
a replacement for the full research note 47 (private) 8-step method or an Opus judgment call.

## Known limits (see research note 39 (private), "what the radar cannot see")

No Reddit/X virality signal, no embargoed-paper visibility, no comet/interstellar-object discovery
feed (MPC has none in RSS/JSON), and the mission calendar is hand-entered, not live-scraped.
