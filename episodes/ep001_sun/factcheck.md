# Ep001 Sun: fact-check of script_v1_raw.txt

Checked 2026-10-12 against `tools/prompts/test_inputs/sun_dossier.txt` (cited as D:line), against research note 50 (private) and research note 36 (private), and with new fetches and searches on 2026-10-12. Output: `script_v1.txt`, 3,071 words before and 3,080 after (+0.3%). The [HOST], [CHAPTER] and [BEAT] marks are unchanged.

**Verdicts (84 claims):** 62 SUPPORTED · 3 DOSSIER-UNVERIFIED (2 fixed) · 7 NOT IN DOSSIER (all checked, 1 fixed) · 12 WRONG or overstated (all fixed, 18 edits).

Sources fetched or searched today:
- https://www.spaceweather.gov/products/solar-cycle-progression. Re-fetched today. It gives the 115 / Jul 2025 / 105-125 panel forecast. It says the updated prediction is "a nonlinear curve fit to the observed monthly values for the sunspot number and F10.7", is "updated every month" and "can be considered as a re-calibration of the 2019 Panel prediction". It says the update was "made available ... in February 2025, replacing the 2019 Panel prediction". It also says "Solar Cycle 26 is expected to begin some time between January 2029 and December 2032. We do not yet produce a prediction for Solar Cycle 26."
- https://www.stce.be/content/sc25-tracking. Re-fetched today; the page was updated 9 Oct 2026. It says "smoothed maximum for SC25 of 160.9 in October 2024".
- https://www.sidc.be/article/solar-cycle-25-maximum. It gives "a maximum between 138 and 161 ... between May and October 2024" and describes the 13-month smoothing. **The article has no date.** Its image path is /2024-09/, so the dossier's "early 2024" is not confirmed.
- Artemis II: AP and other coverage (e.g. https://www.whio.com/news/national/artemis-ii-crew-exits-spacecraft-after-successful-splashdown/7CQV7VBQWAZNLD3UKE5OAQ7GX4/). It launched 1 Apr 2026 and splashed down 10 Apr 2026, with a crew of four on a lunar flyby.
- Mexico aurora history: "Observations of low-latitude red aurora in Mexico during the 1859 Carrington geomagnetic storm" (https://essopenarchive.org/users/549541/articles/603610-observations-of-low-latitude-red-aurora-in-mexico-during-the-1859-carrington-geomagnetic-storm). It reports Mexico City, Querétaro and Guadalajara, so "never had northern lights" is false.
- AR3664 rotating into view about 1 May 2024: EarthSky community photos (https://ecp.earthsky.org/community-photos/entry/66806/) and NASA APOD 13 May 2024.
- Starlink, Feb 2022: NSF PAR 10523466 (https://par.nsf.gov/biblio/10523466) says 49 were launched 3 Feb 2022, 38 de-orbited, after two consecutive moderate storms on 3-4 Feb. SpaceX's own figure was "up to 40".
- A search for a terminator-team Cycle 26 number (2026-10-12) found none.

## Claim table

| # | Line | Claim | Verdict | Source | Fix |
|---|---|---|---|---|---|
| 1 | 1 | Red aurora over Mexico, spring night (10 May 2024) | SUPPORTED | D:3; Gonzalez-Esparza 2024 | — |
| 2 | 1 | "a Sun the experts had promised would stay quiet" | WRONG (overstated) | D:23 says the panel forecast 115, a modest cycle, not a quiet one. "Promised" is too strong, and the rival experts forecast 233 | E1 |
| 3 | 1 | Aurora reached Florida and the Canary Islands; "once in a lifetime" | SUPPORTED | D:3 ("perhaps once in a lifetime") | — |
| 4 | 1, 97 | One spot group about 15 Earths wide | SUPPORTED | D:3; NASA APOD (SWPC gives 16) | — |
| 5 | 5 | Mar 1989 Quebec grid collapsed in about 90 s | SUPPORTED | D:11; Hydro-Québec histories | — |
| 6 | 5 | Power out about 9 hours | SUPPORTED | D:11 | — |
| 7 | 5, 161 | More than 10,000 Starlinks working (by Mar 2026, "today") | SUPPORTED | D:12; keeptrack.space, 17 Mar 2026 | — |
| 8 | 5 | A small storm can "bring some of them down" | WRONG (misleading) | D:10. The losses were freshly launched satellites parked at about 210 km, not the working fleet that line 5 counts | E2 |
| 9 | 5 | Dec 2019 Sun at its quietest, face almost bare | SUPPORTED | D:22 (minimum, derived) | — |
| 10 | 5, 9 | Panel weighed nearly 50 methods | SUPPORTED | D:7, D:23 | — |
| 11 | 9 | The methods disagree | NOT IN DOSSIER | Inferred; a consensus panel exists because the methods give different answers. Acceptable | — |
| 12 | 11 | Sunspot = magnetism bursting through the surface | SUPPORTED | D:62 | — |
| 13 | 11 | About 11-year rise and fall; cycles numbered; Cycle 25 begins late 2019 | SUPPORTED | D:65, D:22 | — |
| 14 | 13 | More spots, more storms | NOT IN DOSSIER | Standard statistical tendency (storm rates track the cycle). Kept as a general rule | — |
| 15 | 15 | The Brussels observatory "counts the spots" | NOT IN DOSSIER (inaccurate detail) | SILSO (Royal Observatory of Belgium) compiles the International Sunspot Number from a worldwide network of observing stations | E3 |
| 16 | 15 | Averaged over 13 months | SUPPORTED | D:21; sidc.be article | — |
| 17 | 17 | Panel convened by NOAA's space-weather office with NASA and ISES | SUPPORTED | D:23 | — |
| 18 | 17 | Announced Sep 2020; 115 around Jul 2025; range 105-125 | SUPPORTED | D:23; SWPC progression page (re-fetched) | — |
| 19 | 21 | "in Boulder, Colorado, a small team of scientists" | WRONG (location) | D:24. McIntosh was at NCAR in Boulder; Leamon was at UMBC / NASA Goddard (Maryland); Chapman was at Warwick | E4 |
| 20 | 21 | The team "has just put" 233 in print (after Sep 2020) | SUPPORTED | D:24; ScienceDaily Dec 2020 (Solar Physics). The arXiv preprint dates from Jun 2020; "just" is loose but fine | — |
| 21 | 25 | 233 is double the panel's 115 | SUPPORTED | 233/115 = 2.03 | — |
| 22 | 27 | McIntosh, then deputy director of NCAR | SUPPORTED | D:24 | — |
| 23 | 27 | Leamon, UMBC, works with NASA | SUPPORTED | D:24 | — |
| 24 | 27 | Chapman is a co-author | SUPPORTED | D:24; arXiv 2006.15263v2 author list | — |
| 25 | 27 | Watching "one thing the panel's forecast doesn't rest on" | NOT IN DOSSIER | Inferred; the panel consensus was not built on the terminator method. Acceptable | — |
| 26 | 29 | Solar magnetism is "far stronger" than a fridge magnet | NOT IN DOSSIER | Background: sunspot fields are about 1,000-4,000 G against a fridge magnet's roughly 50-100 G. True at sunspots, which is the context | — |
| 27 | 31 | One band north and one south, like belts | SUPPORTED (simplified) | D:24 | — |
| 28 | 33 | New bands appear "high up near the poles" | DOSSIER-UNVERIFIED | D:24, D:78 (55° is UNVERIFIED / DO NOT SAY as a hard fact). 55° is mid-high latitude, not "near the poles" | E5 |
| 29 | 33 | Cycles overlap for years | SUPPORTED | D:24 | — |
| 30 | 37 | Opposite bands cancel at the equator | SUPPORTED | D:24 | — |
| 31 | 39 | Named "the terminator" | SUPPORTED | D:24, D:70 | — |
| 32 | 41 | Rule from old records: earlier switch-over, stronger cycle | SUPPORTED | D:24 (the "270 years" figure is correctly left out) | — |
| 33 | 43 | Bright specks trace the bands; SDO photographs them "all the time" | SUPPORTED | D:25 (the 12 s cadence is correctly left out) | — |
| 34 | 47 | Expected May 2020; 233; 204-254; 153-305 | SUPPORTED | D:24; arXiv 2006.15263v2 (2020.37) | — |
| 35 | 55 | A later date means a lower forecast | SUPPORTED | D:24 rule; Frontiers 2023 | — |
| 36 | 57 | Terminator about 13 Dec 2021, 19 months late | SUPPORTED | D:26; Frontiers 10.3389/fspas.2023.1050523 | — |
| 37 | 59 | Train "a year and a half late" | WRONG (understated) | 19 months, not 18 | E6 |
| 38 | 61 | 2022: score above the official line, gap growing | SUPPORTED | D:27 (visual check of the SWPC chart) | — |
| 39 | 63 | Feb 2022: 49 new Starlinks parked at about 210 km | SUPPORTED | D:10; NOAA noaa/53091; Baruah 2024 abstract | — |
| 40 | 63 | Storm "only moderate, near the bottom of the scale" | SUPPORTED | D:10 (G1-G2); NSF PAR 10523466 ("two moderate storms") | — |
| 41 | 65 | Heating puffed up the upper air, drag, fall | SUPPORTED | D:10 | — |
| 42 | 67 | 38 of 49 lost | SUPPORTED | D:10; NOAA noaa/53091 (SpaceX said "up to 40") | — |
| 43 | 67 | "nobody on the ground would've noticed" | WRONG (overstated) | G1-G2 storms produce aurora visible at high latitudes. Absolute claim | E7 |
| 44 | 71 | Sun "running hotter" than the panel said | WRONG (misleading word) | The forecast concerned spot counts, not temperature | E8 |
| 45 | 75 | 30 Jan 2023: McIntosh, Leamon and Egeland re-run with the real date | SUPPORTED | D:28; Frontiers 2023 | — |
| 46 | 77 | About 184 ±17; wider ±63; late 2023 to mid 2024 | SUPPORTED | D:28 (1σ / 2σ). One search snippet inverts the σ labels; the paper as fetched by review 36 gives ±17 = 1σ | — |
| 47 | 79 | Published 21 months before the peak | SUPPORTED | Jan 2023 → Oct 2024 = 21 months | — |
| 48 | 81 | 25 Oct 2023, "experimental", curve fit, redrawn monthly; "nine months later" | SUPPORTED | D:29; SWPC page (re-fetched) | — |
| 49 | 81 | "doesn't lean on the old panel's methods" | WRONG (misleading) | SWPC calls it "a re-calibration of the 2019 Panel prediction based on new observational data". It is a curve fit that does not re-run the 50 methods | E9 |
| 50 | 85 | 137-173, Jan-Oct 2024 | SUPPORTED | D:29; SWPC release 25 Oct 2023 | — |
| 51 | 87 | Brussels forecast 138-161, May-Oct 2024 | SUPPORTED | D:30; sidc.be article | — |
| 52 | 87 | Brussels forecast published "Early in 2024" | DOSSIER-UNVERIFIED | The sidc.be article is undated and its image path is /2024-09/. Timing not confirmed | E10 |
| 53 | 89-91 | Four forecasts; trial and Brussels lie between 115 and 184 | SUPPORTED | Derived | — |
| 54 | 93 | First days of May 2024, the spot group turns toward Earth | NOT IN DOSSIER | AR3664 rotated into view about 1 May 2024 (EarthSky; APOD 13 May 2024). Correct | — |
| 55 | 99 | Spots fling CMEs; most miss Earth | NOT IN DOSSIER | Standard; plain-terms definition at D:63. Acceptable | — |
| 56 | 101 | 9 May: watch for a "severe" storm, first since 2005 | SUPPORTED | D:3 (G4 = "Severe" on NOAA's scale; first G4 Watch since 2005) | — |
| 57 | 101 | About a day's notice | SUPPORTED | D:79 | — |
| 58 | 101, 113 | "That's the best anyone can do" / "a day's warning ... is about as good as it gets" | WRONG (overstated) | CME transit time sets the warning, typically 1-3 days. "Best anyone can do" at one day is too absolute | E11, E14 |
| 59 | 103 | Earth's magnetism shields us, makes compasses point north; aurora near the poles | SUPPORTED | D:61, D:64 | — |
| 60 | 105 | G5, top of the 1-5 scale | SUPPORTED | D:3 | — |
| 61 | 105 | First G5 since Oct 2003; strongest in 21 years | SUPPORTED | D:5; SWPC AR13664 | — |
| 62 | 107 | Aurora over Mexico, Florida, the Canary Islands | SUPPORTED | D:3 | — |
| 63 | 109, 173 | Places that "never had northern lights" | WRONG | Red aurora was recorded across Mexico in 1859 (Carrington). Florida saw aurora in 2003 (and in 1989) | E12, E16 |
| 64 | 111 | The Sun was busier than the official forecast allowed | SUPPORTED | D:5 | — |
| 65 | 115 | Score climbs through summer into autumn | SUPPORTED | Smoothed peak Oct 2024 (STCE) | — |
| 66 | 119 | Peak Oct 2024, 160.9; confirmed only after the smoothing lag | SUPPORTED | D:33; STCE sc25-tracking (re-fetched; updated 9 Oct 2026) | — |
| 67 | 123 | 40% higher, 9 months early; party of 100 → 140; outside 105-125 | SUPPORTED | 160.9/115 = 1.399; Jul 2025 − Oct 2024 = 9 months | — |
| 68 | 125 | 233 was about 45% too high; mirror image of 40 vs 45 | SUPPORTED | 233/160.9 = 1.448; D:50 | — |
| 69 | 125 | "That number fell outside their most likely range" | WRONG | "That number" refers to 233, the centre of 204-254. It is the real peak (160.9) that fell outside the 68% range and inside the 95% range | E13 |
| 70 | 127 | Re-run 184 was 14% high; 114 chairs for 100 | SUPPORTED | 184/160.9 = 1.144 | — |
| 71 | 129 | "Two of the most careful forecasts of our time" | WRONG (unsupported superlative) | No source ranks them | E15 |
| 72 | 129 | Missed "by almost the same amount" | SUPPORTED | Ratios 1.40 and 1.45 (D:50) | — |
| 73 | 131 | 160.9 is inside both 137-173 and 138-161 | SUPPORTED | Derived. 161 is a near-miss edge | — |
| 74 | 133 | The trial forecast is "the winner" | SUPPORTED (analysis) | D:17. Note: Brussels' range is narrower; the trial wins on being earlier. A judgment, not a fact | — |
| 75 | 133 | Feb 2025: SWPC replaces the panel forecast | SUPPORTED | D:34; SWPC page | — |
| 76 | 135 | Oct 2023 is almost 4 years into the cycle | SUPPORTED | D:22 (3.8 yr) | — |
| 77 | 141 | Within 14%; wide range held; date moved 19 months | SUPPORTED | D:17, D:33 | — |
| 78 | 147 | NOAA quote, "We do not yet produce a prediction for Solar Cycle 26." | SUPPORTED | SWPC page, re-fetched today, verbatim | — |
| 79 | 149 | Cycle 26 starts Jan 2029-Dec 2032; "almost four years wide" | SUPPORTED | SWPC page; 3 yr 11 mo | — |
| 80 | 151 | The switch-over team has filed no Cycle 26 number | DOSSIER-UNVERIFIED | D:43 (absence); today's search also found none | — (wording is safe) |
| 81 | 153 | Chapman, 22 May 2026, Warwick, co-author; spot-count clock; weak-to-moderate, ≤ or ~ Cycle 25; no number; 2.5-3.5 yr | SUPPORTED | D:36; ApJ 1003:159 | — |
| 82 | 157 | Polar field read as a precursor; weak now; Wang et al., Jul 2026: unlikely to mean an exceptionally weak Cycle 26; no number | SUPPORTED | D:44; arXiv 2607.03178 | — |
| 83 | 163 | Artemis II, Apr 2026, four astronauts around the Moon and home, during the tail of Cycle 25 | SUPPORTED | D:13; AP coverage (launch 1 Apr, splashdown 10 Apr 2026) | — |
| 84 | 175 | "That glow is the top of the Sun's rhythm ... It's 160.9" and "a line said the Sun would never get this high this soon" | WRONG (misleading + overstated) | The storm was May 2024; the smoothed peak of 160.9 was Oct 2024. The panel gave a forecast range, not "never" | E17, E18 |

The line-185 tease ("some time in the next few years ... will meet") rests on D:39, where "around 2030" is marked UNVERIFIED. It is vague enough to keep. Not counted as a separate claim.

## Edits (before → after)

- **E1** (L1): "thrown there by a Sun the experts had promised would stay quiet." → "thrown there by a Sun the official forecast said would stay modest." — and "How does a quiet Sun do that?" → "How does a modest Sun do that?"
- **E2** (L5): "a storm doesn't need to be big to bring some of them down." → "a storm doesn't need to be big to bring new ones down."
- **E3** (L15): "an observatory in Brussels counts the spots and turns them into a single number." → "an observatory in Brussels collects the world's spot counts and turns them into a single number."
- **E4** (L21): "And in Boulder, Colorado, a small team of scientists has just put" → "And a small team led from Boulder, Colorado, has just put"
- **E5** (L33): "high up near the poles" → "high up toward the poles"
- **E6** (L59): "the train shows up a year and a half late." → "the train shows up more than a year and a half late."
- **E7** (L67): "weather in space nobody on the ground would've noticed." → "weather in space most people on the ground never noticed."
- **E8** (L71): "The Sun is running hotter than the panel said." → "The Sun is running busier than the panel said."
- **E9** (L81): "This one doesn't lean on the old panel's methods." → "This one doesn't re-run the old panel's fifty methods."
- **E10** (L87): "Early in twenty twenty-four, the observatory in Brussels" → "In twenty twenty-four, the observatory in Brussels"
- **E11** (L101): "That's the best anyone can do with a single storm." → "With a single storm, a day or two is about all the warning anyone gets."
- **E12** (L109): "somewhere that's never had northern lights," → "somewhere that almost never sees northern lights,"
- **E13** (L125): "That number fell outside their most likely range." → "The real peak fell outside their most likely range."
- **E14** (L113): "A day's warning for a single storm is about as good as it gets." → "A day or two of warning for a single storm is about as good as it gets."
- **E15** (L129): "Two of the most careful forecasts of our time missed the same Sun," → "Two careful, published forecasts missed the same Sun,"
- **E16** (L173): "rooftops that have never had northern lights." → "rooftops that almost never see northern lights."
- **E17** (L175): "That glow is the top of the Sun's rhythm, made visible. It's a hundred and sixty point nine, painted across the sky." → "That glow is the Sun's rhythm near its top, made visible. It's the climb to a hundred and sixty point nine, painted across the sky."
- **E18** (L175): "a line said the Sun would never get this high this soon." → "a line said the Sun wouldn't get this high this soon."

## Not resolved

- **Brussels forecast date.** The sidc.be article is undated. If the forecast was published in about Sep 2024, the chronology "four forecasts on the table" before May 2024 (L89-93) is off. E10 removes "Early" but leaves the sequence. Confirm the date on SILSO's forecast archive before air.
- **Feb 2022 storm level.** "G1-G2" and "about 210 km" rest on the dossier's abstracts (review 36). Today's search confirmed only "moderate" (NSF PAR). An NOAA Kp record would settle G1 versus G2. The script's wording, "only moderate, near the bottom", holds either way.
- **Line 27 inference.** That the terminator was something the panel forecast "doesn't rest on" is not checked against the panel's method list (D:23 itemisation UNVERIFIED).

## Coordinator edit (2026-10-12)
Brussels (SIDC) forecast date unresolved (page undated, likely ~Sep 2024). To avoid a wrong order of events, the Brussels forecast was removed from the pre-May-2024 "forecasts on the table" scene ("four" → "three") and mentioned only in the scoring paragraph as "later in twenty twenty-four ... by then the Sun was already near the top". No date or range claimed for it.
