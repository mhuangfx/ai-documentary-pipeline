# script_gate.py

Answers: "will a viewer who only has outdated elementary-school space knowledge and no
technical vocabulary follow this narration on first listen, with no rewind?" Checks rules 16-20
of `research note 43 (private)` §1b, added after the owner flagged v4's cold open as "still
leaning too technical" (research note 49 (private) has the full run and reading).

python3 stdlib only. No dependencies.

## Usage

```
python3 tools/script_gate.py path/to/script.md
python3 tools/script_gate.py path/to/script.md --out gate_report.md
python3 tools/script_gate.py path/to/script.md --fix-suggestions
python3 tools/script_gate.py path/to/transcript.txt
```

- `--out PATH` writes the markdown report to a file instead of stdout.
- `--fix-suggestions` appends a table of plain-phrase substitutes (from `SUBSTITUTES`) for every
  jargon term that was used without a nearby definition.

## Input format

Two modes, auto-detected:

1. **Beat script** (the format of `research note 48 (private)`): beats are
   `### NAME — mm:ss–mm:ss (...)` headings, with narration as `> ...` blockquote paragraphs
   directly below the heading. Every `[HOST 6s — ASIDE]`, `[VERIFY: ...]`, `[CHECK ...]`,
   `[TTS: "..."]`, `[PAUSE 8s]` and any other `[...]` chip is a production tag, never spoken, and
   is stripped before analysis.
2. **Plain transcript** (the format of `out/29_transcripts/clean_txt/*.txt`): no beat
   headings, so the whole file is treated as one beat, named from its `# Title` comment line if
   present. This is what lets a reference channel's own narration run through the same gate for
   comparison — see `research note 49 (private)`.

## What it measures

Per beat and overall:

- **Word count, Flesch-Kincaid grade, median/max sentence length, sentences over 25 words**
  (quoted in the report).
- **JARGON hits.** `JARGON` is a flat list of ~170 terms: the owner's 20 "do not know" items
  (research note 43 (private) §1b) plus solar-physics, general-astronomy and mission/instrument jargon, including
  multi-word phrases ("solar cycle", "coronal mass ejection", "sunspot number"). Each hit is
  classified **INTRODUCED** if a definition cue ("which means", "that is", "in other words",
  "think of it as", "basically", "a kind of", "called", "known as", or a dash/colon gloss) appears
  in the same sentence or the 40 words before it, else **UNINTRODUCED**. A beat also fails on
  density even if every term is cued: at most one *distinct new* term per 100 words.
- **COMPARISON-WITHOUT-BASELINE.** Sentences with a comparison trigger (`%`, "percent", "times",
  a digit-multiplier like "3x", "stronger", "weaker", "bigger", "faster", "record", "twice",
  "half") are flagged unless a number appears earlier in the same sentence or in the previous 2
  sentences. Two refinements, both load-bearing for the owner's own example ("the Sun came in
  forty percent stronger"):
  - the comparison's own magnitude ("forty" in "forty percent") is stripped before the check, so
    it can't count as its own baseline;
  - dates read as number words ("twenty twenty-four", "the tenth of May") are stripped too, so a
    date doesn't get mistaken for a baseline value.
- **PASS/FAIL per rule, per beat:** rule 16 (no uncued term + density), rule 17 (no
  baseline-less comparison), rule 19 (grade 6-8, median ≤15, max ≤25). Rule 18 is checked once,
  on the first ~70 words of the whole script, for a strangeness/rarity word (weird, strange,
  rare, never, only, ...) plus a human-stake word (you, we, people, life, home, ...). Rule 20 is
  flagged as "not machine-checkable" every time — it requires a human read against the persona in
  §1b.

## Packaging check (thumbnail text) — added 2026-10-12

```
python3 tools/script_gate.py research note 50 (private) --packaging-only
python3 tools/script_gate.py research note 50 (private) --packaging-only --thumb "The Red Sky Explained"
```

Checks every thumbnail text against `research note 43 (private)` rule 5 / §2.3b (owner
correction 2026-10-12: "They Said Calm" / "The Forecast Said Weak" are too flat; "The Red Sky
Explained" is the target). Texts come from any table with a `Thumbnail text` column (first quoted
string in the cell), from `Thumbnail text: "..."` lines, or from `--thumb` (repeatable). The
script supplies its own picturable nouns on a line `**Scene nouns:** red sky, Mexico, ...`
(research note 47 (private) step 1 inventory); `--scene-nouns` overrides it; with neither, a short built-in
fallback is used and the report says so. Optional `**Thesis words:** ...` adds episode thesis words.

- **FAIL:** outside 2–4 words; no scene noun (abstract-only); any JARGON term ("aurora" fails,
  "northern lights" passes).
- **FLAG:** a thesis/irony word (said, forecast, wrong, weak, calm, quiet, they, experts, ...);
  no explain/reveal promise ("Explained", why/how/what, "?", saw/images); ALL CAPS.
- The section is appended to a normal run whenever the script contains thumbnail text, or with
  `--packaging`; `--packaging-only` prints it alone.

**Limit:** it sees nouns, not shock. "The Sky Turned Red" passes the noun check, though a red sky
alone reads as a sunset. The ranking among PASS lines is the human test in §2.3b. The template
that generates candidates is `tools/prompts/thumbnail_text.md`.

## Limits (heuristic, not semantic)

This is a word-list-and-regex tool. It counts and pattern-matches; it does not understand the
sentence. Known gaps, found while building and running it on script v4 and a reference transcript
(full discussion: research note 49 (private)):

- **A cue word can fire without doing any defining.** "Called" and "that is" are common English
  phrases outside their cue sense — "NOAA's own scientists **called** the twenty nineteen
  forecast no longer reliable" and "**Suppose that is** wrong" both trip the cue check and mark a
  nearby jargon hit INTRODUCED even though nothing was defined. This inflates the INTRODUCED count
  and can hide a real violation.
- **A common English word used as jargon is flagged every time.** "Forecast" is on the owner's own
  do-not-know list (a *solar* forecast isn't what "forecast" means to most people), but the gate
  can't tell a plain use from a technical one, so every occurrence counts — 18 of v4's 41
  UNINTRODUCED hits are "forecast." Read the term list, not just the count.
- **The baseline check can't tell a real baseline from an unrelated number.** After stripping the
  comparison's own magnitude and obvious dates, any leftover number in range still counts as a
  baseline, even if it's measuring something else entirely. This likely undercounts
  baseline-less comparisons.
- **JARGON is a fixed list.** A term that should have been plain but isn't on the list is
  invisible to the gate. The list is transparent (in the script, not hidden) precisely so it can
  be extended.
- **Sentence splitting is naive** (split on `.!?` plus whitespace) — no abbreviation handling.
  Rare in this project's narration (numbers are spelled out for TTS), but a stray "Dr." or "e.g."
  would split wrong.
- **Rules 18 and 20 are the least reliable.** Rule 18's word lists are short and literal; rule 20
  isn't checked at all, only flagged for a human to do.

None of this is a reason to skip the human read (rule 20) — the gate narrows down where to read
closely, it does not replace the read.

## SUBSTITUTES

A small dict (not exhaustive) of plain-phrase substitutes for the terms this project's scripts
actually use, e.g. `"solar cycle" -> "the Sun's roughly 11-year rhythm of getting stormy and then
calm"`. `--fix-suggestions` prints one of these for every UNINTRODUCED term that has an entry, and
says "no substitute on file" for the rest — that's a prompt to write one, not a bug.
