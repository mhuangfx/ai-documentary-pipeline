#!/usr/bin/env python3
"""
validate_shotlist.py -- stdlib-only validator for long_form/pipeline/shotlist.schema.json

Hand-rolls the schema conformance checks (no `jsonschema` dependency) plus the
rules JSON Schema itself cannot express: shot-time ordering/overlap, total
duration vs target_duration_s, and the [VERIFY]-claim -> verified-source
fact-check gate described in research note 17 (private)
(build-list item 6) and research note 19 (private).

Usage:
  python3 validate_shotlist.py <episode.json> [--duration-tol 0.10]
                                               [--short-shot-s 3] [--long-shot-s 20]

Exit codes: 0 PASS (no errors; warnings allowed) . 1 FAIL (>=1 error) . 2 usage/load error.

Report sections:
  ERRORS    -- schema violations, bad time ranges, duration drift, missing/broken
               verify_refs, and (this is the point of the fact-check gate) every
               verify_ref that resolves to a source with verified:false, printed
               as "NEEDS VERIFICATION" so the report doubles as the outstanding
               fact-check checklist for the episode.
  WARNINGS  -- shots outside the 3-20s comfort band, and factual numbers that
               appear only in on_screen (not script_line) without a verify_ref
               (see shotlist.schema.json's $comment on the shot.if/then -- doc 17
               puts some [VERIFY] figures, e.g. shot 7's on-screen capex card,
               in on_screen rather than in the spoken script_line).
"""
import argparse
import json
import re
import sys

# ---- schema constants (kept in sync with shotlist.schema.json by hand) ----

EPISODE_REQUIRED = [
    "id", "title", "premise_id", "trigger_signal", "thesis",
    "target_duration_s", "status", "sources", "voice", "shots",
]
EPISODE_STATUS = {"draft", "verified", "rendering", "review", "approved", "published"}

SOURCE_REQUIRED = ["id", "url", "quote", "claim_it_supports", "verified"]

VOICE_REQUIRED = ["engine", "voice_id", "script_path"]
VOICE_ENGINES = {"chatterbox", "elevenlabs_v3", "seed_audio_minted"}

ASSET_TYPES = {
    "chart", "ledger", "card", "still",
    "clip_h3", "clip_hailuo", "clip_seedance",
    "archival", "screencap",
}

SHOT_REQUIRED = [
    "shot_id", "act", "t_start_s", "t_end_s", "script_line",
    "on_screen", "asset_type", "takes", "status",
]
SHOT_STATUS = {"todo", "generating", "generated", "picked", "failed"}

ID_RE = re.compile(r"^ep[0-9]{3,}_[a-z0-9]+(_[a-z0-9]+)*$")
SRC_ID_RE = re.compile(r"^src_[a-z0-9_]+$")
SHOT_ID_RE = re.compile(r"^s[0-9]{2,}$")

# The spec's literal rule is "script_line contains a factual number". Digits
# alone would miss spelled-out figures doc 17 actually uses ("Two-thirds",
# "a nickel"), so this also matches percent/cents/dollar markers and the
# handful of number-words that show up in this channel's register.
NUMBER_RE = re.compile(
    r"\b\d|\bpercent\b|\bcents?\b|\bhalf\b|\bthirds?\b|\bquarter\b|\bdozen\b|"
    r"\bnickel\b|\bdime\b|\$",
    re.IGNORECASE,
)
# \b\d (not bare \d) so an asset-name token like "H3" or "clip_h3" doesn't get
# misread as a factual figure -- the digit must start its own token.


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.needs_verification = []  # (shot_id, source_id, claim_it_supports)

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_type(rep, where, value, expected, required=True):
    if value is None:
        if required:
            rep.error(f"{where}: missing/null")
        return False
    ok = True
    if expected is str:
        ok = isinstance(value, str)
    elif expected is bool:
        ok = isinstance(value, bool)
    elif expected is dict:
        ok = isinstance(value, dict)
    elif expected is list:
        ok = isinstance(value, list)
    elif expected == "number":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected == "int":
        ok = isinstance(value, int) and not isinstance(value, bool)
    if not ok:
        label = {"number": "number", "int": "integer"}.get(expected, getattr(expected, "__name__", str(expected)))
        rep.error(f"{where}: expected {label}, got {type(value).__name__}")
        return False
    return True


def validate_episode_shape(rep, ep):
    for field in EPISODE_REQUIRED:
        if field not in ep:
            rep.error(f"episode: missing required field '{field}'")

    if "id" in ep:
        if check_type(rep, "episode.id", ep["id"], str):
            if not ID_RE.match(ep["id"]):
                rep.error(f"episode.id '{ep['id']}' does not match ^ep[0-9]{{3,}}_[a-z0-9_]+$")

    for f in ("title", "premise_id", "trigger_signal", "thesis"):
        if f in ep:
            if check_type(rep, f"episode.{f}", ep[f], str):
                if not ep[f].strip():
                    rep.error(f"episode.{f}: must not be empty")

    if "target_duration_s" in ep:
        if check_type(rep, "episode.target_duration_s", ep["target_duration_s"], "number"):
            if ep["target_duration_s"] <= 0:
                rep.error("episode.target_duration_s: must be > 0")

    if "status" in ep:
        if check_type(rep, "episode.status", ep["status"], str):
            if ep["status"] not in EPISODE_STATUS:
                rep.error(f"episode.status '{ep['status']}' not in {sorted(EPISODE_STATUS)}")

    if "sources" in ep:
        check_type(rep, "episode.sources", ep["sources"], list)
    if "voice" in ep:
        check_type(rep, "episode.voice", ep["voice"], dict)
    if "shots" in ep:
        check_type(rep, "episode.shots", ep["shots"], list)


def validate_sources(rep, sources):
    if not isinstance(sources, list):
        return {}
    seen_ids = {}
    for i, src in enumerate(sources):
        where = f"sources[{i}]"
        if not isinstance(src, dict):
            rep.error(f"{where}: expected object")
            continue
        for field in SOURCE_REQUIRED:
            if field not in src:
                rep.error(f"{where}: missing required field '{field}'")

        sid = src.get("id")
        if sid is not None:
            if check_type(rep, f"{where}.id", sid, str):
                if not SRC_ID_RE.match(sid):
                    rep.error(f"{where}.id '{sid}' does not match ^src_[a-z0-9_]+$")
                elif sid in seen_ids:
                    rep.error(f"{where}.id '{sid}' duplicates {seen_ids[sid]}")
                else:
                    seen_ids[sid] = where

        if "url" in src:
            check_type(rep, f"{where}.url", src["url"], str)
        if "quote" in src:
            check_type(rep, f"{where}.quote", src["quote"], str)
        if "claim_it_supports" in src:
            if check_type(rep, f"{where}.claim_it_supports", src["claim_it_supports"], str):
                if not src["claim_it_supports"].strip():
                    rep.error(f"{where}.claim_it_supports: must not be empty")

        verified = src.get("verified")
        if verified is not None:
            check_type(rep, f"{where}.verified", verified, bool)
            if verified is True and not src.get("verified_date"):
                rep.error(f"{where}: verified is true but verified_date is missing")

    return {sid: src for sid, src in zip(
        (s.get("id") for s in sources if isinstance(s, dict)),
        (s for s in sources if isinstance(s, dict)),
    )}


def validate_voice(rep, voice):
    if not isinstance(voice, dict):
        return
    for field in VOICE_REQUIRED:
        if field not in voice:
            rep.error(f"voice: missing required field '{field}'")
    if "engine" in voice:
        if check_type(rep, "voice.engine", voice["engine"], str):
            if voice["engine"] not in VOICE_ENGINES:
                rep.error(f"voice.engine '{voice['engine']}' not in {sorted(VOICE_ENGINES)}")
    for f in ("voice_id", "script_path"):
        if f in voice:
            check_type(rep, f"voice.{f}", voice[f], str)


def validate_shot_shape(rep, shot, i, source_ids):
    where = f"shots[{i}]"
    if not isinstance(shot, dict):
        rep.error(f"{where}: expected object")
        return

    for field in SHOT_REQUIRED:
        if field not in shot:
            rep.error(f"{where}: missing required field '{field}'")

    sid = shot.get("shot_id")
    if sid is not None and check_type(rep, f"{where}.shot_id", sid, str):
        if not SHOT_ID_RE.match(sid):
            rep.error(f"{where}.shot_id '{sid}' does not match ^s[0-9]{{2,}}$")

    if "act" in shot:
        if check_type(rep, f"{where}.act", shot["act"], "int"):
            if shot["act"] < 1:
                rep.error(f"{where}.act must be >= 1")

    for f in ("t_start_s", "t_end_s"):
        if f in shot:
            check_type(rep, f"{where}.{f}", shot[f], "number")

    if "script_line" in shot:
        check_type(rep, f"{where}.script_line", shot["script_line"], str)
    if "on_screen" in shot:
        check_type(rep, f"{where}.on_screen", shot["on_screen"], str)

    at = shot.get("asset_type")
    if at is not None and check_type(rep, f"{where}.asset_type", at, str):
        if at not in ASSET_TYPES:
            rep.error(f"{where}.asset_type '{at}' not in {sorted(ASSET_TYPES)}")

    fat = shot.get("fallback_asset_type")
    if fat is not None and fat not in ASSET_TYPES:
        rep.error(f"{where}.fallback_asset_type '{fat}' not in {sorted(ASSET_TYPES)}")

    if "takes" in shot:
        if check_type(rep, f"{where}.takes", shot["takes"], "int"):
            if shot["takes"] < 1:
                rep.error(f"{where}.takes must be >= 1")

    if "tool_params" in shot and shot["tool_params"] is not None:
        check_type(rep, f"{where}.tool_params", shot["tool_params"], dict)

    vr = shot.get("verify_refs", [])
    if vr is not None:
        if check_type(rep, f"{where}.verify_refs", vr, list, required=False):
            for j, ref in enumerate(vr):
                if not isinstance(ref, str) or not SRC_ID_RE.match(ref):
                    rep.error(f"{where}.verify_refs[{j}] '{ref}' is not a valid src_ id")
                elif ref not in source_ids:
                    rep.error(f"{where}.verify_refs[{j}] '{ref}' does not exist in sources[]")

    st = shot.get("status")
    if st is not None and check_type(rep, f"{where}.status", st, str):
        if st not in SHOT_STATUS:
            rep.error(f"{where}.status '{st}' not in {sorted(SHOT_STATUS)}")

    # --- the fact-check gate ---
    script_line = shot.get("script_line") or ""
    on_screen = shot.get("on_screen") or ""
    script_has_number = bool(NUMBER_RE.search(script_line))
    onscreen_has_number = bool(NUMBER_RE.search(on_screen))

    if script_has_number and not vr:
        rep.error(
            f"{where} (shot_id={sid}): script_line contains a factual number "
            f"but verify_refs is empty -- '{script_line.strip()}'"
        )
    elif onscreen_has_number and not script_has_number and not vr:
        rep.warn(
            f"{where} (shot_id={sid}): on_screen contains a factual number with no "
            f"verify_refs (script_line itself has none, so this is a warning, not an "
            f"error -- see shotlist.schema.json's shot.$comment) -- '{on_screen.strip()}'"
        )

    for ref in vr or []:
        src = source_ids.get(ref)
        if src is None:
            continue  # already reported above
        if src.get("verified") is not True:
            rep.needs_verification.append((sid, ref, src.get("claim_it_supports", "")))


def validate_time_ranges(rep, shots, target_duration_s, tol, short_s, long_s):
    timed = []
    for i, shot in enumerate(shots):
        if not isinstance(shot, dict):
            continue
        t0, t1 = shot.get("t_start_s"), shot.get("t_end_s")
        sid = shot.get("shot_id", f"[{i}]")
        if not isinstance(t0, (int, float)) or isinstance(t0, bool) or \
           not isinstance(t1, (int, float)) or isinstance(t1, bool):
            continue  # already reported as a type error
        if t1 <= t0:
            rep.error(f"shot {sid}: t_end_s ({t1}) must be > t_start_s ({t0})")
            continue
        dur = t1 - t0
        if dur > long_s:
            rep.warn(f"shot {sid}: duration {dur:.1f}s exceeds the {long_s}s comfort ceiling")
        if dur < short_s:
            rep.warn(f"shot {sid}: duration {dur:.1f}s is under the {short_s}s comfort floor")
        timed.append((t0, t1, sid))

    in_order = sorted(timed, key=lambda x: x[0])
    if in_order != timed:
        rep.error("shots[] is not sorted by ascending t_start_s (compare shot_id order to time order)")

    for (t0a, t1a, sida), (t0b, t1b, sidb) in zip(in_order, in_order[1:]):
        if t0b < t1a:
            rep.error(f"shots {sida} and {sidb} overlap: {sida} ends at {t1a}, {sidb} starts at {t0b}")

    if in_order:
        total = in_order[-1][1] - in_order[0][0]
        if isinstance(target_duration_s, (int, float)) and not isinstance(target_duration_s, bool) \
           and target_duration_s > 0:
            drift = abs(total - target_duration_s) / target_duration_s
            if drift > tol:
                rep.error(
                    f"total shot duration {total:.1f}s vs target_duration_s "
                    f"{target_duration_s:.1f}s drifts {drift * 100:.1f}% (tolerance {tol * 100:.0f}%)"
                )
        return total
    return 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode_json")
    ap.add_argument("--duration-tol", type=float, default=0.10, help="fractional tolerance vs target_duration_s (default 0.10 = 10%%)")
    ap.add_argument("--short-shot-s", type=float, default=3.0)
    ap.add_argument("--long-shot-s", type=float, default=20.0)
    args = ap.parse_args()

    try:
        ep = load(args.episode_json)
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL to load {args.episode_json}: {e}", file=sys.stderr)
        return 2

    rep = Report()
    validate_episode_shape(rep, ep)
    source_ids = validate_sources(rep, ep.get("sources", []))
    validate_voice(rep, ep.get("voice", {}))

    shots = ep.get("shots", [])
    if isinstance(shots, list):
        for i, shot in enumerate(shots):
            validate_shot_shape(rep, shot, i, source_ids)
        total = validate_time_ranges(
            rep, shots, ep.get("target_duration_s"),
            args.duration_tol, args.short_shot_s, args.long_shot_s,
        )
    else:
        total = 0.0

    # ---- report ----
    print(f"validate_shotlist.py -- {args.episode_json}")
    print(f"episode: {ep.get('id', '?')}  status={ep.get('status', '?')}  "
          f"shots={len(shots) if isinstance(shots, list) else '?'}  "
          f"total={total:.1f}s target={ep.get('target_duration_s', '?')}s")
    print()

    if rep.needs_verification:
        print(f"NEEDS VERIFICATION ({len(rep.needs_verification)} claim(s) still resting on unverified sources):")
        for sid, ref, claim in rep.needs_verification:
            print(f"  - shot {sid}: {ref} (verified=false) -- supports: {claim}")
        print()

    if rep.errors:
        print(f"ERRORS ({len(rep.errors)}):")
        for e in rep.errors:
            print(f"  - {e}")
        print()
    else:
        print("ERRORS: none")
        print()

    if rep.warnings:
        print(f"WARNINGS ({len(rep.warnings)}):")
        for w in rep.warnings:
            print(f"  - {w}")
        print()
    else:
        print("WARNINGS: none")
        print()

    if rep.errors:
        print(f"RESULT: FAIL ({len(rep.errors)} error(s), {len(rep.warnings)} warning(s))")
        return 1

    print(f"RESULT: PASS ({len(rep.warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
