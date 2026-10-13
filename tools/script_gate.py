#!/usr/bin/env python3
"""
script_gate.py -- plain-language gate for long_form narration scripts (python3 stdlib only).

Answers: "will a viewer who only remembers elementary-school space facts (planets orbit the
Sun, the Sun is a star, the Moon has phases) follow this narration on first listen, with no
rewind?" Built after the owner flagged that v4's cold open is "still leaning too technical"
(research note 43 (private) §1b, rules 16-20; research note 48 (private) the failing case).

Input: a script markdown file in the format of research note 48 (private) --
beats under `### NAME -- mm:ss-mm:ss (...)` headings, narration as `> ...` blockquote
paragraphs immediately below the heading. `[HOST Ns ...]`, `[VERIFY ...]`, `[CHECK ...]`,
`[TTS: ...]`, `[PAUSE ...]` and any other `[...]` chip is stripped before analysis -- none of
that text is spoken. If the file has no beat headings (a plain transcript), the whole file is treated as one beat so a
reference narration can be run through the same gate for comparison.

Per beat and overall, reports:
  - word count, Flesch-Kincaid grade, median/max sentence length, sentences over 25 words
  - JARGON HITS: every JARGON term found, classified INTRODUCED / UNINTRODUCED against a
    definition-cue check (same sentence, or the previous 40 words)
  - COMPARISON-WITHOUT-BASELINE: sentences with a comparison word ("%", "percent", "times",
    a digit-x multiplier, "stronger", "weaker", "bigger", "faster", "record", "twice", "half")
    with no number in the current sentence (up to the trigger) or the previous 2 sentences
  - PASS/FAIL verdicts for rules 16-19 (research note 43 (private) §1b)
  - a "first 30s" check (rule 18) on the first ~70 words of the whole script
  - PACKAGING (rule 5 / research note 43 (private) §2.3b, owner correction 2026-10-12): every thumbnail text
    found in the script (a 'Thumbnail text' table column, or `Thumbnail text: "..."` lines, or
    --thumb) is checked for 2-4 words, at least one noun from the script's `**Scene nouns:**`
    line (FAIL if abstract-only), no jargon (FAIL), no thesis/irony word (FLAG), and an
    explain/reveal promise (FLAG if missing)

`--fix-suggestions` prints a plain-phrase substitute for every UNINTRODUCED term that has one
in SUBSTITUTES.

This is a heuristic word-list-and-regex tool, not a semantic one -- see the README and
research note 49 (private) for what it cannot see (a term can be "introduced" by a cue that doesn't actually
define it in plain words; a term absent from JARGON is invisible to the gate; single common
words like "forecast" are flagged every time even when the sentence is already plain).

Usage:
    python3 tools/script_gate.py path/to/script.md
    python3 tools/script_gate.py path/to/script.md --out gate_report.md
    python3 tools/script_gate.py path/to/transcript.txt --fix-suggestions
    python3 tools/script_gate.py path/to/script.md --packaging-only
    python3 tools/script_gate.py path/to/script.md --packaging-only --thumb "The Red Sky Explained"
"""

import argparse
import re
import sys
from bisect import bisect_right
from statistics import median

# ---------------------------------------------------------------------------
# Word lists (heuristic, not semantic -- see README "Limits")
# ---------------------------------------------------------------------------

# The owner's 20 "do not know" items, plus ~150 more astronomy/physics/space-weather terms.
# Multi-word phrases are matched as phrases first (longest match wins at each position).
JARGON = [
    # --- the owner's 20 -----------------------------------------------------
    "solar cycle", "sunspot", "forecast", "geomagnetic storm", "aurora",
    "coronal mass ejection", "cme", "magnetic field", "light-year", "redshift",
    "exoplanet", "kp index", "g5", "plasma", "ion", "orbit insertion", "flyby",
    "spectrum", "parsec", "au",
    # --- solar physics / space weather --------------------------------------
    "sunspot number", "smoothed sunspot number", "solar maximum", "solar minimum",
    "solar dynamo", "dynamo", "corona", "coronal hole", "solar flare",
    "x-class flare", "m-class flare", "c-class flare", "geomagnetic storm scale",
    "g4 storm", "g3 storm", "g2 storm", "g1 storm", "terminator", "polar field",
    "polar magnetic field", "hale cycle", "schwabe cycle", "13-month smoothing",
    "panel forecast", "precursor method", "curve-fit forecast", "solar wind",
    "heliosphere", "ionosphere", "magnetosphere", "auroral oval", "airglow",
    "radiation belt", "van allen belt", "euv", "extreme ultraviolet",
    "bright point", "active region", "sunspot group", "umbra", "penumbra",
    "photosphere", "chromosphere", "prominence", "filament", "solar cycle 25",
    "solar cycle 26", "space weather", "swpc", "sidc", "silso",
    "magnetic reconnection", "solar irradiance", "total solar irradiance",
    "butterfly diagram", "tachocline", "differential rotation", "faculae",
    "spicule", "sigmoid", "cycle minimum", "cycle maximum",
    # --- astronomy / astrophysics general ------------------------------------
    "astronomical unit", "blueshift", "spectroscopy", "spectral line",
    "perihelion", "aphelion", "gravity assist", "escape velocity", "apogee",
    "perigee", "occultation", "transit", "radial velocity", "doppler shift",
    "luminosity", "magnitude", "parallax", "main sequence", "red giant",
    "white dwarf", "neutron star", "black hole", "event horizon", "singularity",
    "accretion disk", "supernova", "nebula", "protostar", "dark matter",
    "dark energy", "cosmic microwave background", "gravitational wave",
    "exosphere", "magnetotail", "bow shock", "heliopause",
    "interplanetary medium", "cosmic ray", "sidereal", "synodic", "ephemeris",
    "epoch", "declination", "right ascension", "ecliptic", "equinox",
    "solstice", "libration", "tidal locking", "roche limit", "hill sphere",
    "lagrange point", "delta-v", "orbital mechanics", "orbital period",
    "semi-major axis", "eccentricity", "inclination", "apsis", "planetesimal",
    "protoplanetary disk", "kuiper belt", "oort cloud", "asteroid belt",
    "near-earth object", "albedo", "regolith", "spectral type",
    "habitable zone", "tidal heating", "stellar wind", "solar sail",
    # --- mission / instrument jargon -----------------------------------------
    "solar dynamics observatory", "sdo", "james webb space telescope", "jwst",
    "hubble space telescope", "atmospheric imaging assembly", "aia instrument",
    "cadence", "telemetry", "downlink", "ground track", "payload",
    "spacecraft bus", "flare classification", "ncar", "umbc",
]

# A small dict of plain-language substitutes for the terms this project's scripts actually use.
# Not exhaustive -- see README. Only terms with an entry here get a --fix-suggestions line.
SUBSTITUTES = {
    "solar cycle": "the Sun's roughly 11-year rhythm of getting stormy and then calm",
    "geomagnetic storm": "a burst from the Sun hitting Earth's magnetic shield",
    "sunspot": "dark blotches on the Sun's face",
    "sunspot number": "a running count of how many dark blotches are on the Sun",
    "smoothed sunspot number": "the blotch count averaged over about a year so one busy week can't fake a peak",
    "coronal mass ejection": "a giant cloud of charged particles the Sun throws into space",
    "cme": "a giant cloud of charged particles the Sun throws into space",
    "aurora": "the glowing lights in the sky when the Sun's particles hit the air",
    "solar flare": "a sudden flash of light and energy off the Sun's surface",
    "solar maximum": "the stormiest point in the Sun's cycle",
    "solar minimum": "the calmest point in the Sun's cycle",
    "magnetic field": "the invisible force field that steers charged particles",
    "dynamo": "the churning motion inside the Sun that generates its magnetism",
    "terminator": "the moment the old cycle's magnetic bands meet and cancel out",
    "kp index": "a 0-to-9 scale for how disturbed Earth's magnetic field is",
    "g5": "the strongest rank on the 1-to-5 storm scale",
    "plasma": "a superheated gas of charged particles",
    "ion": "an atom carrying an electric charge",
    "light-year": "the distance light travels in one year, about 9.5 trillion kilometres",
    "parsec": "an astronomer's distance unit, about 3.26 light-years",
    "au": "the distance from Earth to the Sun, used as a ruler for the solar system",
    "astronomical unit": "the distance from Earth to the Sun, used as a ruler for the solar system",
    "redshift": "how light stretches and reddens when its source is moving away",
    "exoplanet": "a planet orbiting a star other than our Sun",
    "flyby": "a spacecraft passing close to a world without stopping",
    "orbit insertion": "the maneuver that slows a spacecraft so a planet's gravity catches it",
    "spectrum": "light broken out into its rainbow of colours",
    "polar field": "the Sun's magnetism measured at its north and south poles",
    "polar magnetic field": "the Sun's magnetism measured at its north and south poles",
    "corona": "the Sun's faint outer atmosphere",
    "active region": "a patch of the Sun tangled up with strong magnetism",
    "euv": "a kind of light more energetic than what our eyes can see",
    "extreme ultraviolet": "a kind of light more energetic than what our eyes can see",
    "forecast": "a prediction",
}

# Definition-cue phrases. A jargon hit counts as INTRODUCED if one of these appears in the
# same sentence, or in the 40 words before the hit.
CUES = [
    "which means", "that is", "in other words", "think of it as", "basically",
    "a kind of", "called", "known as",
]

# "First 30s" (rule 18) word lists.
STRANGE_WORDS = [
    "weird", "strange", "bizarre", "odd", "rare", "unusual", "never",
    "only", "impossible", "astonishing", "extraordinary", "once in a lifetime",
    "can't explain", "couldn't explain", "nobody can",
]
STAKE_WORDS = [
    "you", "your", "yours", "we", "us", "our", "people", "family", "families",
    "life", "home", "city", "kids", "children", "town", "planet", "world",
    "everyone", "anyone", "someone", "viewer", "friend", "sky",
]

# Comparison triggers (rule 17). "x " from the spec is implemented as a digit-multiplier
# pattern (e.g. "3x") rather than a bare literal "x " substring, which would false-hit on
# ordinary words like "box the" -- see README.
COMPARISON_RE = re.compile(
    r"%|\bpercent\b|\btimes\b|\d+\s*x\b|\bstronger\b|\bweaker\b|\bbigger\b|"
    r"\bfaster\b|\brecord\b|\btwice\b|\bhalf\b",
    re.IGNORECASE,
)

# Spelled-out and digit numbers, used as the "baseline" check for rule 17.
NUMBER_RE = re.compile(
    r"\d|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|"
    r"million|billion|dozen)\b",
    re.IGNORECASE,
)

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
BRACKET_RE = re.compile(r"\[[^\]]*\]")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

MAX_SENT_WORDS = 25
FK_GRADE_MIN = 6.0
FK_GRADE_MAX = 8.0
MEDIAN_SENT_MAX = 15
NEW_TERM_WORDS_PER_TERM = 100  # "at most one new term per 100 words" (rule 16)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

BEAT_HEADING_RE = re.compile(
    r"^###\s+(?P<name>.+?)\s+—\s+\d{1,2}:\d{2}\s*[–-]\s*\d{1,2}:\d{2}"
)


def parse_beats_markdown(text):
    """Return [(beat_name, raw_narration_text), ...] from a research note 48 (private)-style script."""
    lines = text.splitlines()
    beats = []
    i = 0
    n = len(lines)
    while i < n:
        m = BEAT_HEADING_RE.match(lines[i])
        if not m:
            i += 1
            continue
        name = m.group("name").strip()
        i += 1
        collected = []
        # skip blank lines, collect consecutive "> " lines, stop at first non-blank
        # non-"> " line (an italic beat-note, a table, or the next heading).
        while i < n:
            line = lines[i]
            if line.strip() == "":
                i += 1
                continue
            if line.startswith(">"):
                collected.append(line[1:].lstrip())
                i += 1
                continue
            break
        beats.append((name, "\n".join(collected)))
    return beats


def parse_as_single_beat(text, fallback_name):
    """Treat a plain transcript file as one beat. Strips a leading '# ...' header block."""
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    body = "\n".join(lines).strip()
    name = fallback_name
    for ln in text.splitlines():
        if ln.startswith("# "):
            name = ln[2:].strip()
            break
    return [(name, body)]


def strip_chips(raw):
    """Remove [HOST ...], [VERIFY ...], [CHECK ...], [TTS ...], [PAUSE ...] and any other
    bracket chip; these are production tags, never spoken."""
    cleaned = BRACKET_RE.sub(" ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# ---------------------------------------------------------------------------
# Sentence / word metrics
# ---------------------------------------------------------------------------

def split_sentences(text):
    """Return [(sentence_text, char_start, char_end), ...]."""
    if not text.strip():
        return []
    out = []
    pos = 0
    for piece in SENT_SPLIT_RE.split(text):
        piece_stripped = piece.strip()
        if not piece_stripped:
            continue
        idx = text.find(piece_stripped, pos)
        if idx == -1:
            idx = pos
        out.append((piece_stripped, idx, idx + len(piece_stripped)))
        pos = idx + len(piece_stripped)
    return out


def words_with_spans(text):
    return [(m.group(0), m.start(), m.end()) for m in WORD_RE.finditer(text)]


def count_syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in w:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if w.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def flesch_kincaid_grade(word_list, sentences):
    n_words = len(word_list)
    n_sents = max(len(sentences), 1)
    if n_words == 0:
        return 0.0
    n_syll = sum(count_syllables(w[0]) for w in word_list)
    return 0.39 * (n_words / n_sents) + 11.8 * (n_syll / n_words) - 15.59


# ---------------------------------------------------------------------------
# JARGON matching
# ---------------------------------------------------------------------------

def build_jargon_regex():
    terms = sorted(set(JARGON), key=lambda t: (-len(t.split()), -len(t)))
    escaped = [re.escape(t) for t in terms]
    pattern = r"\b(" + "|".join(escaped) + r")\b"
    return re.compile(pattern, re.IGNORECASE), terms


JARGON_RE, JARGON_TERMS_SORTED = build_jargon_regex()


def sentence_index_for_pos(sent_spans, pos):
    starts = [s[1] for s in sent_spans]
    idx = bisect_right(starts, pos) - 1
    return max(idx, 0) if sent_spans else -1


def word_index_for_pos(word_spans, pos):
    starts = [w[1] for w in word_spans]
    return bisect_right(starts, pos) - 1


def has_cue(snippet):
    low = snippet.lower()
    return any(c in low for c in CUES)


def has_dash_or_colon_gloss(sentence_text):
    return ("—" in sentence_text) or (" - " in sentence_text) or (":" in sentence_text)


def find_jargon_hits(beat_name, text, word_spans, sent_spans):
    """Return list of hit dicts: term, sentence, introduced(bool), first_use(bool)."""
    hits = []
    seen_first_use_introduced = {}  # term -> bool, set on first occurrence only
    for m in JARGON_RE.finditer(text):
        term = m.group(1).lower()
        start, end = m.start(), m.end()
        s_idx = sentence_index_for_pos(sent_spans, start)
        sentence_text = sent_spans[s_idx][0] if sent_spans else text
        # same-sentence cue or dash/colon gloss
        same_sentence_ok = has_cue(sentence_text) or has_dash_or_colon_gloss(sentence_text)
        # previous-40-words window
        w_idx = word_index_for_pos(word_spans, start)
        window_start = max(0, w_idx - 40)
        window_words = word_spans[window_start:w_idx]
        window_text = " ".join(w[0] for w in window_words)
        prev_ok = has_cue(window_text)
        introduced = same_sentence_ok or prev_ok
        is_first_use = term not in seen_first_use_introduced
        if is_first_use:
            seen_first_use_introduced[term] = introduced
        hits.append({
            "beat": beat_name,
            "term": term,
            "sentence": sentence_text,
            "introduced": introduced,
            "first_use": is_first_use,
        })
    return hits, seen_first_use_introduced


# Trigger types whose own magnitude number sits immediately before them ("forty percent",
# "3 times", "3x") -- that adjacent number is the comparison's own figure, not a baseline, so
# it is stripped before the baseline check. Word-type triggers (stronger/twice/half/record/...)
# don't have this pattern, so nothing is stripped for them.
MAGNITUDE_ADJACENT_TRIGGERS = ("%", "percent", "times")
ADJACENT_NUMBER_RE = re.compile(
    r"(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|"
    r"million|billion|dozen)\s*$",
    re.IGNORECASE,
)

# Dates read out as number words ("twenty twenty-four", "the tenth of May") are not baselines
# for a comparison -- they answer "when", not "compared to what". Stripped before the baseline
# check only; this is the fix for the owner's own cold-open example (see README).
YEAR_PHRASE_RE = re.compile(
    r"\b(?:nineteen|twenty)[\s-]+(?:oh[\s-]+)?(?:ten|eleven|twelve|thirteen|fourteen|fifteen|"
    r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)"
    r"(?:-(?:one|two|three|four|five|six|seven|eight|nine))?\b",
    re.IGNORECASE,
)
FOUR_DIGIT_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
ORDINAL_DATE_RE = re.compile(
    r"\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|"
    r"thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth|"
    r"thirtieth)\b",
    re.IGNORECASE,
)


def strip_dates(text):
    text = YEAR_PHRASE_RE.sub(" ", text)
    text = FOUR_DIGIT_YEAR_RE.sub(" ", text)
    text = ORDINAL_DATE_RE.sub(" ", text)
    return text


def find_comparison_hits(beat_name, sent_spans):
    """Return list of dicts for sentences with a comparison trigger and no nearby baseline."""
    hits = []
    for i, (sent, start, end) in enumerate(sent_spans):
        m = COMPARISON_RE.search(sent)
        if not m:
            continue
        trigger = m.group(0)
        before_trigger = sent[: m.start()]
        trigger_is_magnitude = trigger.lower() in MAGNITUDE_ADJACENT_TRIGGERS or re.match(r"^\d+\s*x$", trigger, re.I)
        if trigger_is_magnitude:
            adj = ADJACENT_NUMBER_RE.search(before_trigger)
            if adj:
                before_trigger = before_trigger[: adj.start()]
        prev_text = ""
        for j in (i - 2, i - 1):
            if j >= 0:
                prev_text += " " + sent_spans[j][0]
        combined = strip_dates(prev_text + " " + before_trigger)
        if not NUMBER_RE.search(combined):
            hits.append({"beat": beat_name, "sentence": sent, "trigger": trigger})
    return hits


# ---------------------------------------------------------------------------
# Per-beat analysis
# ---------------------------------------------------------------------------

class BeatResult:
    def __init__(self, name, text):
        self.name = name
        self.text = text
        self.word_spans = words_with_spans(text)
        self.words = len(self.word_spans)
        self.sent_spans = split_sentences(text)
        self.n_sent = len(self.sent_spans)
        sent_lens = [len(words_with_spans(s[0])) for s in self.sent_spans]
        self.sent_lens = sent_lens
        self.median_sent = median(sent_lens) if sent_lens else 0
        self.max_sent = max(sent_lens) if sent_lens else 0
        self.over25 = [s[0] for s, l in zip(self.sent_spans, sent_lens) if l > MAX_SENT_WORDS]
        self.grade = flesch_kincaid_grade(self.word_spans, self.sent_spans)
        self.jargon_hits, self.first_use_map = find_jargon_hits(
            self.name, self.text, self.word_spans, self.sent_spans
        )
        self.comparison_hits = find_comparison_hits(self.name, self.sent_spans)
        self.uninitiated_terms = {t for t, ok in self.first_use_map.items() if not ok}
        self.new_terms_count = len(self.first_use_map)
        allowed = max(1, self.words // NEW_TERM_WORDS_PER_TERM + (1 if self.words % NEW_TERM_WORDS_PER_TERM else 0))
        self.density_allowed = allowed
        self.density_ok = self.new_terms_count <= allowed

    def rule16_pass(self):
        return (not self.uninitiated_terms) and self.density_ok

    def rule17_pass(self):
        return not self.comparison_hits

    def rule19_pass(self):
        grade_ok = FK_GRADE_MIN <= self.grade <= FK_GRADE_MAX
        return grade_ok and (self.median_sent <= MEDIAN_SENT_MAX) and (self.max_sent <= MAX_SENT_WORDS)


def first_30s_check(all_text):
    words = words_with_spans(all_text)
    first70 = " ".join(w[0] for w in words[:70])
    low = first70.lower()
    strange_hit = next((w for w in STRANGE_WORDS if w in low), None)
    stake_hit = next((w for w in STAKE_WORDS if re.search(r"\b" + re.escape(w) + r"\b", low)), None)
    ok = bool(strange_hit) and bool(stake_hit)
    return {
        "snippet": first70,
        "strange_hit": strange_hit,
        "stake_hit": stake_hit,
        "pass": ok,
    }


# ---------------------------------------------------------------------------
# Packaging: thumbnail text (research note 43 (private) rule 5 / §2.3b, owner correction 2026-10-12)
# ---------------------------------------------------------------------------
# The owner rejected "They Said Calm" / "The Forecast Said Weak" (thesis and irony, nothing to
# picture) and gave "The Red Sky Explained" as the target: 2-4 words, a concrete thing the viewer
# can picture, a promise of an explanation or reveal. The script supplies its own noun list on a
# line `**Scene nouns:** red sky, Mexico, northern lights, ...` (and, optionally, extra banned
# thesis words on `**Thesis words:** ...`). Heuristic, like the rest of this file: it can see
# whether a picturable noun is present, not whether the line is strange or shocking.

THUMB_MIN_WORDS = 2
THUMB_MAX_WORDS = 4

# Fallback when the script supplies no scene-noun list. Deliberately short and lay.
DEFAULT_VISUAL_NOUNS = [
    "sky", "sun", "moon", "earth", "mars", "jupiter", "saturn", "venus", "mercury", "pluto",
    "uranus", "neptune", "northern lights", "star", "comet", "asteroid", "crater", "volcano",
    "ocean", "ice", "fire", "storm", "city", "satellite", "satellites", "rocket", "rings",
    "black hole", "planet", "galaxy", "cloud", "clouds",
]

# Words that carry the thesis / irony / dispute instead of the scene. A hit is a FLAG.
THESIS_WORDS = [
    "said", "says", "thought", "predicted", "prediction", "predict", "forecast", "expected",
    "experts", "expert", "scientists", "wrong", "right", "weak", "calm", "quiet", "we were",
    "nobody", "they", "lied", "official",
]

# Explanation / reveal promise (the "Explained" form, questions, look-words).
PROMISE_RE = re.compile(
    r"\?|\bexplain(?:ed|s)?\b|\bwhy\b|\bhow\b|\bwhat\b|\breveal(?:ed|s)?\b|\bsecret\b|"
    r"\btruth\b|\breally\b|\banswer(?:ed)?\b|\bsaw\b|\bseen\b|\bimages?\b|\bfootage\b|"
    r"\bthis is\b",
    re.IGNORECASE,
)

THUMB_QUOTE_RE = re.compile(r"[\"“]([^\"”]{1,80})[\"”]")
SCENE_NOUNS_LINE_RE = re.compile(r"^\W*scene nouns:?\W*(.+)$", re.IGNORECASE)
THESIS_WORDS_LINE_RE = re.compile(r"^\W*thesis words:?\W*(.+)$", re.IGNORECASE)
THUMB_LINE_RE = re.compile(r"thumbnail text:?\**\s*\**[\"“]([^\"”]{1,80})[\"”]", re.IGNORECASE)


def _split_list(s):
    return [t.strip(" .*`").lower() for t in s.split(",") if t.strip(" .*`")]


def parse_packaging(text):
    """Return (scene_nouns, extra_thesis_words, thumbnail_texts) found in a script file.

    Thumbnail texts come from (a) any markdown table whose header has a 'Thumbnail text' column
    (first quoted string in that cell) and (b) lines like `Thumbnail text: "X"`."""
    nouns, thesis, thumbs = [], [], []
    lines = text.splitlines()
    col = None
    for ln in lines:
        s = ln.strip()
        m = SCENE_NOUNS_LINE_RE.match(s)
        if m:
            nouns += _split_list(m.group(1))
            continue
        m = THESIS_WORDS_LINE_RE.match(s)
        if m:
            thesis += _split_list(m.group(1))
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            header_hit = [i for i, c in enumerate(cells) if re.search(r"thumbnail text", c, re.I)]
            if header_hit:
                col = header_hit[0]
                continue
            if col is not None and col < len(cells) and not set(cells[col]) <= set("-: "):
                q = THUMB_QUOTE_RE.search(cells[col])
                if q:
                    thumbs.append(q.group(1).strip())
            continue
        col = None
        for m in THUMB_LINE_RE.finditer(s):
            thumbs.append(m.group(1).strip())
    seen = set()
    thumbs = [t for t in thumbs if not (t.lower() in seen or seen.add(t.lower()))]
    return nouns, thesis, thumbs


def _find_terms(text, terms):
    low = text.lower()
    return [t for t in terms if re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", low)]


def check_thumbnail(thumb, scene_nouns, extra_thesis):
    words = WORD_RE.findall(thumb)
    n = len(words)
    nouns_used = _find_terms(thumb, scene_nouns)
    jargon = sorted({m.group(1).lower() for m in JARGON_RE.finditer(thumb)})
    thesis = _find_terms(thumb, THESIS_WORDS + extra_thesis)
    promise = PROMISE_RE.search(thumb)
    all_caps = thumb.upper() == thumb and any(c.isalpha() for c in thumb)

    fails, flags = [], []
    if not (THUMB_MIN_WORDS <= n <= THUMB_MAX_WORDS):
        fails.append(f"{n} words (want {THUMB_MIN_WORDS}-{THUMB_MAX_WORDS})")
    if not nouns_used:
        fails.append("abstract-only: no scene noun the viewer can picture")
    if jargon:
        fails.append("jargon: " + ", ".join(jargon))
    if thesis:
        flags.append("thesis/irony word: " + ", ".join(thesis))
    if not promise:
        flags.append("no explain/reveal promise (OK only if the words carry the shock -- human check)")
    if all_caps:
        flags.append("ALL CAPS (runs backwards in 42c: 53% hits vs 66% misses)")
    verdict = "FAIL" if fails else ("FLAG" if flags else "PASS")
    return {
        "text": thumb, "words": n, "nouns": nouns_used, "promise": promise.group(0) if promise else "",
        "fails": fails, "flags": flags, "verdict": verdict,
    }


def packaging_report(scene_nouns, extra_thesis, thumbs):
    out = ["## Packaging: thumbnail text (rule 5 / §2.3b)\n"]
    if scene_nouns:
        out.append(f"Scene nouns (from the script): {', '.join(scene_nouns)}\n")
    else:
        scene_nouns = DEFAULT_VISUAL_NOUNS
        out.append("No `**Scene nouns:**` line in the script -- using the short built-in fallback list. "
                   "Add the episode's own list (research note 47 (private) step 1) for a real check.\n")
    if not thumbs:
        out.append("No thumbnail text found (no 'Thumbnail text' table column, no `Thumbnail text: \"...\"` line, "
                   "no --thumb).\n")
        return "\n".join(out), True
    out.append("| Thumbnail text | Words | Scene noun | Promise | Verdict | Why |")
    out.append("|---|---|---|---|---|---|")
    all_ok = True
    for t in thumbs:
        r = check_thumbnail(t, scene_nouns, extra_thesis)
        all_ok &= r["verdict"] != "FAIL"
        why = "; ".join(r["fails"] + r["flags"]) or "--"
        out.append(f"| {esc(r['text'])} | {r['words']} | {', '.join(r['nouns']) or 'none'} | "
                   f"{esc(r['promise']) or 'none'} | **{r['verdict']}** | {esc(why)} |")
    out.append("\nThe gate sees nouns and words, not shock: a line like \"The Sky Turned Red\" passes the noun "
               "check although a red sky alone reads as a sunset. Rank PASS lines by the human test in "
               "research note 43 (private) §2.3b (is the strange part of the scene in the words?).\n")
    return "\n".join(out), all_ok


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def fmt_pass(ok):
    return "PASS" if ok else "FAIL"


def esc(s):
    """Escape '|' so a beat name or sentence snippet can't break a markdown table row."""
    return s.replace("|", "\\|")


def make_report(source_path, beats, fix_suggestions):
    results = [BeatResult(name, strip_chips(raw)) for name, raw in beats]
    overall_text = " ".join(r.text for r in results)
    overall = BeatResult("OVERALL", overall_text)

    out = []
    out.append(f"# Script gate report: `{source_path}`\n")
    out.append(f"Beats found: {len(results)}. Overall: {overall.words} words, "
               f"{overall.n_sent} sentences, FK grade {overall.grade:.1f}.\n")

    out.append("## Per-beat metrics\n")
    out.append("| Beat | Words | FK grade | Median sent | Max sent | >25-word sents | "
               "Jargon (uninit/hit) | Baseline-less comparisons | R16 | R17 | R19 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        out.append(
            f"| {esc(r.name)} | {r.words} | {r.grade:.1f} | {r.median_sent} | {r.max_sent} | "
            f"{len(r.over25)} | {len(r.uninitiated_terms)}/{r.new_terms_count} | "
            f"{len(r.comparison_hits)} | {fmt_pass(r.rule16_pass())} | "
            f"{fmt_pass(r.rule17_pass())} | {fmt_pass(r.rule19_pass())} |"
        )
    out.append(
        f"| **OVERALL** | {overall.words} | {overall.grade:.1f} | {overall.median_sent} | "
        f"{overall.max_sent} | {len(overall.over25)} | "
        f"{len(overall.uninitiated_terms)}/{overall.new_terms_count} | "
        f"{len(overall.comparison_hits)} | {fmt_pass(overall.rule16_pass())} | "
        f"{fmt_pass(overall.rule17_pass())} | {fmt_pass(overall.rule19_pass())} |\n"
    )

    out.append("## Rule 20 (curious-12-year-old test)\n")
    out.append("Not machine-checkable -- read every FAIL row above plus the jargon/comparison "
               "detail below against the persona in research note 43 (private) §1b, beat by beat.\n")

    out.append("## First 30s check (rule 18)\n")
    f30 = first_30s_check(overall_text)
    out.append(f"First ~70 words: \"{f30['snippet']}\"\n")
    out.append(f"- strangeness/rarity word found: **{f30['strange_hit'] or 'none'}**")
    out.append(f"- human-stake word found: **{f30['stake_hit'] or 'none'}**")
    out.append(f"- verdict: **{fmt_pass(f30['pass'])}**\n")

    out.append("## Sentences over 25 words\n")
    any_over = False
    for r in results:
        if r.over25:
            any_over = True
            out.append(f"**{r.name}** ({len(r.over25)}):")
            for s in r.over25:
                out.append(f"> {s}")
            out.append("")
    if not any_over:
        out.append("None.\n")

    out.append("## JARGON hits\n")
    for r in results:
        if not r.jargon_hits:
            continue
        out.append(f"**{r.name}**")
        out.append("| Term | Introduced? | Sentence |")
        out.append("|---|---|---|")
        for h in r.jargon_hits:
            snippet = h["sentence"]
            if len(snippet) > 160:
                snippet = snippet[:157] + "..."
            out.append(f"| {h['term']} | {'INTRODUCED' if h['introduced'] else 'UNINTRODUCED'} | {esc(snippet)} |")
        out.append("")
        if r.uninitiated_terms:
            out.append(f"Uncued at first use in this beat: {', '.join(sorted(r.uninitiated_terms))}")
        out.append(f"Distinct new terms: {r.new_terms_count} (density budget: {r.density_allowed} per beat "
                    f"at {NEW_TERM_WORDS_PER_TERM} words/term -- {'OK' if r.density_ok else 'OVER'})\n")

    out.append("## Baseline-less comparisons (rule 17)\n")
    any_cmp = False
    for r in results:
        if r.comparison_hits:
            any_cmp = True
            out.append(f"**{r.name}**")
            for h in r.comparison_hits:
                out.append(f"- trigger `{h['trigger']}`: {h['sentence']}")
            out.append("")
    if not any_cmp:
        out.append("None.\n")

    if fix_suggestions:
        out.append("## --fix-suggestions\n")
        all_uninit = set()
        for r in results:
            all_uninit |= r.uninitiated_terms
        if not all_uninit:
            out.append("No uncued-at-first-use terms found.\n")
        else:
            out.append("| Uncued term | Suggested plain-phrase substitute |")
            out.append("|---|---|")
            for t in sorted(all_uninit):
                sub = SUBSTITUTES.get(t, "(no substitute on file -- write a plain-words gloss)")
                out.append(f"| {t} | {sub} |")
            out.append("")

    out.append("## Verdict\n")
    beat_pass = all(r.rule16_pass() and r.rule17_pass() and r.rule19_pass() for r in results)
    out.append(f"Rules 16/17/19 across all beats: **{fmt_pass(beat_pass)}**. "
                f"Rule 18 (first 30s): **{fmt_pass(f30['pass'])}**. Rule 20 requires a human read.\n")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Plain-language gate for long_form narration scripts.")
    ap.add_argument("input", help="script markdown (beats under '### NAME -- mm:ss-mm:ss') or a plain transcript .txt")
    ap.add_argument("--out", help="write the markdown report here instead of stdout")
    ap.add_argument("--fix-suggestions", action="store_true", help="append plain-phrase substitutes for uncued terms")
    ap.add_argument("--packaging", action="store_true",
                    help="append the thumbnail-text check (rule 5 / §2.3b); runs anyway if the script has thumbnail text")
    ap.add_argument("--packaging-only", action="store_true", help="print only the thumbnail-text check")
    ap.add_argument("--thumb", action="append", default=[], help="extra thumbnail text to check (repeatable)")
    ap.add_argument("--scene-nouns", help="comma list; overrides the script's **Scene nouns:** line")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    nouns, thesis, thumbs = parse_packaging(text)
    if args.scene_nouns:
        nouns = _split_list(args.scene_nouns)
    thumbs = thumbs + [t for t in args.thumb if t.lower() not in {x.lower() for x in thumbs}]
    pkg_md, _ = packaging_report(nouns, thesis, thumbs)

    if args.packaging_only:
        report = f"# Packaging check: `{args.input}`\n\n" + pkg_md
    else:
        beats = parse_beats_markdown(text)
        if not beats:
            import os
            beats = parse_as_single_beat(text, fallback_name=os.path.basename(args.input))
        report = make_report(args.input, beats, args.fix_suggestions)
        if args.packaging or thumbs:
            report += "\n\n" + pkg_md

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
