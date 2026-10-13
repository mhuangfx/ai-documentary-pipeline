#!/usr/bin/env python3
"""
story_radar.py -- rank candidate space/astronomy story premises for the long_form channel.

Answers: "how should we generate a story?"
  Priority 1: timely discoveries/events (last ~90d or next ~90d) that we ALSO have free
              visuals for (`pull` + `score`).
  Priority 2: evergreen, hookable premises -- contradiction/unknown/scale-shock/recomputed
              (`evergreen`).

Every candidate gets an explicit, weighted composite score (see WEIGHTS_TIMELY /
WEIGHTS_EVERGREEN below and the README) so the shortlist is ranked, not guessed.

Design notes / research this implements:
  research note 02d (private) -- pipeline shape (pull -> normalize -> score).
  research note 14 (private) -- what a manual pull + score pass looked like.
  research note 22 (private) -- working RSS feeds + dead feeds (reused below).
  research note 24 (private) -- the editorial rule: no title a chatbot answers
      in one screen ("chatbot-test" scoring below is a proxy for this).
  research note 29 (private) / research note 31 (private) Part 2 -- hook words, spectacle-vs-dispute,
      the visual rule (no living things / no generated legible text -- space imagery is inert).
  tools/space_assets.py -- the archive fetcher, reused (subprocess) for the VISUALS check.

Dependencies: python3 stdlib + `requests` (falls back to urllib if requests is not importable).
`feedparser` is used if imported successfully, else RSS/Atom is parsed with xml.etree.
The saturation check (how crowded a topic already is on video platforms) is withheld in this
public version; it always reports 'withheld' and scores neutral.

Usage:
    python3 tools/story_radar.py pull       --days 90 --out out/39_pull_raw.json
    python3 tools/story_radar.py score      --in out/39_pull_raw.json \
                                             --out out/39_radar_run.json \
                                             --shortlist-n 40
    python3 tools/story_radar.py evergreen  --out out/39_evergreen.json
    python3 tools/story_radar.py all        --out out/39_radar_run.json
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
    HAVE_REQUESTS = True
except Exception:
    HAVE_REQUESTS = False

try:
    import feedparser  # type: ignore
    HAVE_FEEDPARSER = True
except Exception:
    HAVE_FEEDPARSER = False

HERE = os.path.dirname(os.path.abspath(__file__))
SPACE_ASSETS = os.path.join(HERE, "space_assets.py")

USER_AGENT = "story-radar/0.1 (research tool; contact: %s)" % os.environ.get("CONTACT_EMAIL", "set CONTACT_EMAIL")
TIMEOUT = 25


def log(msg: str):
    print(f"[story_radar] {msg}", file=sys.stderr)


def now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def http_get(url: str, params: Optional[dict] = None, timeout: int = TIMEOUT) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    if HAVE_REQUESTS:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.content
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_json(url: str, params: Optional[dict] = None, timeout: int = TIMEOUT) -> Any:
    return json.loads(http_get(url, params, timeout).decode("utf-8", "replace"))


# ---------------------------------------------------------------------------
# Feed config -- what worked, what didn't (verified live 2026-09-27)
# ---------------------------------------------------------------------------

FEEDS = [
    # name, url, tier(3=mission/agency press, 2=paper-with-press/secondary, 1=blog), category
    {"name": "nasa_news", "url": "https://www.nasa.gov/feed/", "tier": 3, "category": "agency_press"},
    {"name": "nasa_press_release", "url": "https://www.nasa.gov/news-release/feed/", "tier": 3, "category": "agency_press"},
    {"name": "nasa_science", "url": "https://science.nasa.gov/feed/", "tier": 3, "category": "agency_press"},
    {"name": "nasa_iotd", "url": "https://www.nasa.gov/feeds/iotd-feed/", "tier": 1, "category": "imagery_blog"},
    {"name": "apod", "url": "https://apod.nasa.gov/apod.rss", "tier": 1, "category": "imagery_blog"},
    {"name": "esahubble_news", "url": "https://esahubble.org/news/feed/", "tier": 3, "category": "agency_press"},
    {"name": "esawebb_news", "url": "https://esawebb.org/news/feed/", "tier": 3, "category": "agency_press"},
    {"name": "esa_activities", "url": "https://www.esa.int/rssfeed/Our_Activities", "tier": 3, "category": "agency_press"},
    {"name": "eso_news", "url": "https://www.eso.org/public/news/feed/", "tier": 3, "category": "agency_press"},
    {"name": "eso_announcements", "url": "https://www.eso.org/public/announcements/feed/", "tier": 2, "category": "agency_press"},
    {"name": "noirlab_news", "url": "https://noirlab.edu/public/news/feed/", "tier": 3, "category": "agency_press"},
]

ARXIV_FEEDS = [
    {"name": "arxiv_astro-ph.EP", "url": "http://export.arxiv.org/rss/astro-ph.EP", "category": "arxiv_new"},
    {"name": "arxiv_astro-ph.GA", "url": "http://export.arxiv.org/rss/astro-ph.GA", "category": "arxiv_new"},
    {"name": "arxiv_astro-ph.SR", "url": "http://export.arxiv.org/rss/astro-ph.SR", "category": "arxiv_new"},
    {"name": "arxiv_astro-ph.HE", "url": "http://export.arxiv.org/rss/astro-ph.HE", "category": "arxiv_new"},
    {"name": "arxiv_astro-ph.CO", "url": "http://export.arxiv.org/rss/astro-ph.CO", "category": "arxiv_new"},
]

# science.nasa.gov/feed/ is a sitewide "recently touched" feed (confirmed live 2026-09-27): it
# mixes real news with reference/catalog stub pages whose RSS pubDate reflects a page edit, not
# an event. URL path substrings that reliably identify those stub pages (not exhaustive).
_REFERENCE_PAGE_PATH_MARKERS = (
    "/apod/", "/exoplanets/star-catalog/", "/biological-physical/investigations/",
)


def is_reference_page(link: str) -> bool:
    return any(m in link for m in _REFERENCE_PAGE_PATH_MARKERS)


NOAA_SWPC_ALERTS_URL = "https://services.swpc.noaa.gov/products/alerts.json"
JPL_CAD_API = "https://ssd-api.jpl.nasa.gov/cad.api"

# Feeds/APIs tried and rejected, per the brief's "mark UNVERIFIED / skip and log" instruction.
# Recorded here so nobody re-tries them expecting a different result without a reason to.
DEAD_SOURCES = [
    {"name": "jpl_news_rss", "url": "https://www.jpl.nasa.gov/rss/news (and /feeds/news)",
     "reason": "HTTP 403 Forbidden on every attempt 2026-09-27. Substituted: nasa_press_release "
               "(nasa.gov/news-release/feed/) carries most JPL mission news as NASA HQ press."},
    {"name": "stsci_hubble_feed", "url": "https://science.nasa.gov/mission/hubble/feed/",
     "reason": "Returns the rendered HTML mission page (413KB), not RSS/XML -- not a real feed. "
               "Substituted: esahubble_news (esahubble.org/news/feed/) for Hubble press."},
    {"name": "nasa_svs_recent_rss", "url": "https://svs.gsfc.nasa.gov/vis/.../rss.xml",
     "reason": "404 -- SVS publishes no site-wide 'recent' RSS. Used the JSON search API "
               "(svs.gsfc.nasa.gov/api/search) instead, but only as a VISUALS source via "
               "space_assets.py, not as a news/item source (SVS visualizations aren't news items)."},
    {"name": "mpc_recent_objects", "url": "minorplanetcenter.net (RecentObjects / RecentMPECs)",
     "reason": "HTML tables only (28-45KB HTML, no RSS/JSON endpoint found for recent discoveries "
               "or new comets). Per the brief's instruction ('if none exists, skip and log'): SKIPPED. "
               "Partial substitute: JPL SSD cad.api (JSON, works) supplies close-approach flyby data, "
               "used for the mission-calendar 'flyby' category, but it is NEOs/asteroids, not comet "
               "discoveries specifically -- comet/interstellar-object DISCOVERY coverage has no "
               "automated source in this build."},
    {"name": "arxiv_api_query", "url": "http://export.arxiv.org/api/query (and https)",
     "reason": "HTTP 406 Not Acceptable on every attempt (urllib and curl, http and https, with and "
               "without a browser User-Agent) from this network, 2026-09-27. Used the plain "
               "per-category RSS feeds (rss.arxiv.org) instead -- see arXiv caveat in score()."},
]


# ---------------------------------------------------------------------------
# RSS / Atom parsing (stdlib xml.etree; feedparser used instead if importable)
# ---------------------------------------------------------------------------

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _parse_rfc822(s: str) -> Optional[datetime.datetime]:
    # e.g. "Sat, 27 Sep 2026 04:00:01 +0000" or "Sun, 27 Sep 2026 00:00:00 -0400"
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\s*([+-]\d{4})?", s)
    if not m:
        return None
    day, mon, year, hh, mm, ss, tz = m.groups()
    month = _MONTHS.get(mon)
    if not month:
        return None
    dt = datetime.datetime(int(year), month, int(day), int(hh), int(mm), int(ss), tzinfo=datetime.timezone.utc)
    if tz:
        sign = 1 if tz[0] == "+" else -1
        offset = datetime.timedelta(hours=int(tz[1:3]), minutes=int(tz[3:5]))
        dt = dt - sign * offset
    return dt


def _parse_iso8601(s: str) -> Optional[datetime.datetime]:
    s = s.strip()
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception:
        return None


def parse_date(s: Optional[str]) -> Optional[datetime.datetime]:
    if not s:
        return None
    return _parse_rfc822(s) or _parse_iso8601(s)


def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def parse_feed_xml(xml_bytes: bytes) -> List[Dict[str, Any]]:
    """Minimal RSS 2.0 / Atom parser via xml.etree. Returns list of {title, link, summary, date_raw}."""
    import xml.etree.ElementTree as ET
    items: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        log(f"XML parse error: {e}")
        return items
    # RSS: channel/item ; Atom: feed/entry
    for el in root.iter():
        tag = _strip_ns(el.tag)
        if tag not in ("item", "entry"):
            continue
        rec: Dict[str, Any] = {"title": "", "link": "", "summary": "", "date_raw": ""}
        for child in el:
            ctag = _strip_ns(child.tag)
            text = (child.text or "").strip()
            if ctag == "title":
                rec["title"] = text
            elif ctag == "link":
                href = child.get("href")
                rec["link"] = href if href else text
            elif ctag in ("description", "summary", "content"):
                if not rec["summary"]:
                    rec["summary"] = text
            elif ctag in ("pubDate", "published", "updated", "date"):
                if not rec["date_raw"]:
                    rec["date_raw"] = text
        if rec["title"]:
            items.append(rec)
    return items


def fetch_feed(feed: Dict[str, str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Returns (items, error). Never raises."""
    try:
        raw = http_get(feed["url"])
    except Exception as e:
        return [], str(e)
    if HAVE_FEEDPARSER:
        try:
            import feedparser as fp  # type: ignore
            parsed = fp.parse(raw)
            items = []
            for e in parsed.entries:
                items.append({
                    "title": e.get("title", ""),
                    "link": e.get("link", ""),
                    "summary": e.get("summary", e.get("description", "")),
                    "date_raw": e.get("published", e.get("updated", "")),
                })
            return items, None
        except Exception as e:
            log(f"feedparser failed on {feed['name']}, falling back to xml.etree: {e}")
    return parse_feed_xml(raw), None


# ---------------------------------------------------------------------------
# NOAA space weather alerts
# ---------------------------------------------------------------------------

# Only these product-id prefixes indicate a genuinely notable (not routine-minor) event.
NOAA_NOTABLE_PREFIXES = ("WATA", "SUMX", "K06", "K07", "K08", "K09", "G3", "G4", "G5", "FLR", "ALTTP")


def fetch_noaa_alerts() -> List[Dict[str, Any]]:
    try:
        data = http_get_json(NOAA_SWPC_ALERTS_URL)
    except Exception as e:
        log(f"NOAA SWPC alerts fetch failed: {e}")
        return []
    out = []
    for row in data:
        pid = row.get("product_id", "")
        msg = row.get("message", "")
        first_line = msg.strip().splitlines()[0] if msg.strip() else pid
        notable = pid.startswith(NOAA_NOTABLE_PREFIXES) or "WARNING" in msg and ("G3" in msg or "G4" in msg or "G5" in msg)
        out.append({
            "title": f"Space weather alert {pid}: {first_line}",
            "link": "https://www.swpc.noaa.gov/products/alerts-watches-and-warnings",
            "summary": msg[:400],
            "date_raw": row.get("issue_datetime", ""),
            "source": "noaa_swpc_alerts",
            "tier": 3,
            "category": "space_weather",
            "notable": notable,
        })
    return out


# ---------------------------------------------------------------------------
# JPL SSD close-approach data (flyby calendar, next N days)
# ---------------------------------------------------------------------------

def fetch_close_approaches(days_ahead: int = 90, max_dist_au: float = 0.02) -> List[Dict[str, Any]]:
    today = now_utc().date()
    end = today + datetime.timedelta(days=days_ahead)
    try:
        data = http_get_json(JPL_CAD_API, {
            "dist-max": str(max_dist_au),
            "date-min": today.isoformat(),
            "date-max": end.isoformat(),
        })
    except Exception as e:
        log(f"JPL cad.api fetch failed: {e}")
        return []
    fields = data.get("fields", [])
    out = []
    for row in data.get("data", []):
        rec = dict(zip(fields, row))
        try:
            dist_au = float(rec.get("dist", 1))
        except Exception:
            dist_au = 1.0
        out.append({
            "title": f"Close approach: {rec.get('des','?')} passes within {dist_au:.4f} AU on {rec.get('cd','?')}",
            "link": f"https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr={urllib.parse.quote(rec.get('des','') )}",
            "summary": f"v_rel={rec.get('v_rel','?')} km/s, H={rec.get('h','?')}, dist_min={rec.get('dist_min')} AU",
            "date_raw": rec.get("cd", ""),
            "source": "jpl_cad_api",
            "tier": 3,
            "category": "flyby",
        })
    return out


# ---------------------------------------------------------------------------
# Mission calendar -- hand-maintained, next-90-days known events.
# Filled from WebFetch/WebSearch against NASA/ESA calendars 2026-09-27.
# UNVERIFIED = could not confirm against a primary/reputable source in this pass; treat as a
# lead to re-check, not a fact to script against.
# ---------------------------------------------------------------------------

MISSION_CALENDAR = [
    {
        "name": "Starship Flight 14 -- first orbital-class test flight, Starlink V3 deploy",
        "date": "2026-09-28", "category": "launch", "tier": 3,
        "source": "https://spaceflightnow.com/2026/09/23/spacex-stack-starship-and-super-heavy-for-first-orbital-flight/",
        "verified": True, "note": "Biggest rocket ever flown; booster catch/landing footage is the visual.",
    },
    {
        "name": "ESA JUICE -- third Earth gravity-assist flyby (~8,640 km altitude)",
        "date": "2026-09-28", "category": "flyby", "tier": 3,
        "source": "https://www.esa.int/Science_Exploration/Space_Science/Juice/Juice_to_fly_past_Earth_for_third_gravity_assist",
        "verified": True, "note": "Spacecraft-imaging-Earth/Moon footage; slingshot-physics explainer angle.",
    },
    {
        "name": "SpaceX Crew-13 launch to ISS",
        "date": "2026-10-01", "category": "launch/crew", "tier": 2,
        "source": "NASA / public launch manifests (not independently re-verified this pass)",
        "verified": True, "note": "Routine but reliable b-roll anchor, not a standalone hook by itself.",
    },
    {
        "name": "Orionids meteor shower peak",
        "date": "2026-10-21", "category": "sky_event", "tier": 1,
        "source": "IMO meteor shower calendar (standard annual date); no outburst forecast for 2026",
        "verified": True, "note": "Routine annual peak, no outburst predicted -- background item only, not a lead by itself.",
    },
    {
        "name": "JAXA MMX launch to Phobos (Mars-moon sample return, new H3 rocket)",
        "date": "2026-10-20", "date_note": "backup window to 2026-11-07",
        "category": "launch", "tier": 3,
        "source": "https://global.jaxa.jp/press/2026/08/20260820-1_e.html",
        "verified": True, "note": "New rocket + Mars-moon sample-return concept -- strong 'why Phobos' explainer hook.",
    },
    {
        "name": "Leonids meteor shower peak",
        "date": "2026-11-17", "category": "sky_event", "tier": 1,
        "source": "IMO meteor shower calendar; no outburst forecast for 2026",
        "verified": True, "note": "Routine annual peak -- background item only.",
    },
    {
        "name": "Voyager 1 reaches one light-day from Earth",
        "date": "2026-11-18", "category": "milestone", "tier": 2,
        "source": "https://earthsky.org/space/voyager-1-1-light-day-from-earth-november-17-18-2026/",
        "verified": True, "note": "First human-made object at that distance -- clean 'how far is far' visual explainer.",
    },
    {
        "name": "ESA BepiColombo -- Mercury Planetary Orbiter (MPO) insertion",
        "date": "2026-11-21", "category": "arrival", "tier": 2,
        "source": "Techtimes/Karmactive, citing ESA (secondary; NOT independently confirmed on esa.int this pass)",
        "verified": False, "note": "UNVERIFIED against ESA's own page -- confirm on esa.int before scripting. 8-year cruise ends; 'one shot, no real-time fix' tension angle.",
    },
    {
        "name": "ESA Hera -- orbital insertion at Didymos/Dimorphos (DART follow-up)",
        "date": "2026-11-15", "date_note": "'November 2026', exact day unconfirmed",
        "category": "arrival", "tier": 3,
        "source": "https://www.esa.int/Space_Safety/Hera/ESA_s_Hera_targets_early_arrival_at_Didymos_asteroids",
        "verified": False, "note": "Month confirmed, exact day UNVERIFIED. Planetary-defense payoff: did DART's asteroid strike work?",
    },
    {
        "name": "ESA Gaia Data Release 4 (DR4)",
        "date": "2026-12-02", "category": "data_release", "tier": 3,
        "source": "https://www.cosmos.esa.int/web/gaia/data-release-4",
        "verified": True, "note": "Billion-star 3D map update -- strong data-visualization segment.",
    },
    {
        "name": "NASA Europa Clipper -- Earth gravity-assist flyby",
        "date": "2026-12-03", "date_note": "~16:15 EST, window Dec 2-7",
        "category": "flyby", "tier": 3,
        "source": "https://www.jpl.nasa.gov/news/nasas-europa-clipper-uses-mars-to-go-the-distance/ (via Space Launch Schedule)",
        "verified": True, "note": "'Spacecraft swings past your backyard' visual + ocean-moon mission recap.",
    },
    {
        "name": "ESA BepiColombo -- Mio (MMO) orbiter insertion",
        "date": "2026-12-10", "category": "arrival", "tier": 2,
        "source": "Techtimes/Karmactive, citing ESA (secondary; NOT independently confirmed on esa.int this pass)",
        "verified": False, "note": "UNVERIFIED against ESA's own page -- confirm before scripting.",
    },
    {
        "name": "Geminids meteor shower peak",
        "date": "2026-12-14", "date_note": "peak ~05:44 UTC", "category": "sky_event", "tier": 1,
        "source": "IMO meteor shower calendar; no outburst forecast for 2026",
        "verified": True, "note": "Routine annual peak, near-moonless -- background item only.",
    },
    {
        "name": "Ursids meteor shower peak",
        "date": "2026-12-22", "category": "sky_event", "tier": 1,
        "source": "IMO meteor shower calendar; no outburst forecast for 2026",
        "verified": True, "note": "Minor, routine -- background item only.",
    },
    {
        "name": "Astrobotic Griffin Mission One (lunar lander, south pole, largest commercial lunar payload)",
        "date": None, "date_note": "CONFLICTING: NET July 2026 per Spaceflight Now (Oct 2025) vs 'November 2026' per Planetary Society 2026 calendar",
        "category": "launch", "tier": 2,
        "source": "https://spaceflightnow.com/2025/10/28/astrobotic-delays-griffin-1-moon-mission-to-net-july-2026/",
        "verified": False, "note": "UNVERIFIED / conflicting dates -- confirm live status before using.",
    },
    {
        "name": "Boeing Starliner-1 (pivoted to uncrewed cargo flight)",
        "date": None, "date_note": "'Q4 2026', no fixed date found",
        "category": "launch", "tier": 2,
        "source": "https://spaceflightnow.com/2025/11/24/nasa-boeing-pivot-starliner-1-mission-from-4-person-astronaut-flight-to-cargo-only/",
        "verified": False, "note": "UNVERIFIED exact date. Starliner redemption-arc angle after Crew Flight Test troubles.",
    },
    {
        "name": "ISRO Gaganyaan-1 (first uncrewed test flight)",
        "date": None, "date_note": "slipped from March 2026 to 'Q4 2026', no confirmed date",
        "category": "launch", "tier": 2,
        "source": "https://theprint.in/india/gaganyaan-uncrewed-mission-oceansat-quantum-tech-demonstration-isro-set-for-a-busy-schedule-in-2026/2812390/",
        "verified": False, "note": "UNVERIFIED exact date. India's crewed-program precursor; Vyommitra robot is a strong visual.",
    },
    {
        "name": "Artemis II crewed lunar flyby",
        "date": "2027-02-05", "date_note": "Currently outside the 90-day window (cutoff 2026-12-26); listed for prep only.",
        "category": "launch/crew", "tier": 3,
        "source": "https://www.nasa.gov/humans-in-space/artemis/ (verify exact date before scripting)",
        "verified": False, "note": "UNVERIFIED exact date -- Artemis dates have slipped repeatedly.",
    },
]

MISSION_CALENDAR_CAVEAT = (
    "Populated 2026-09-27 by a WebSearch/WebFetch pass (NASA launch schedule, Spaceflight Now, "
    "JAXA, ESA JUICE/Hera/BepiColombo pages, JPL/Europa Clipper, ESA Gaia Cosmos, NASA eclipse "
    "page, IMO/Farmers' Almanac meteor forecasts, Planetary Society 2026 calendar) -- NOT scraped "
    "live, because NASA's (nasa.gov/launchschedule/) and ESA's event calendars are client-rendered "
    "HTML/JS pages with no RSS/JSON, so this table will go stale and must be re-run per pull. "
    "Checked and excluded as non-events in this window: no solar/lunar eclipse falls between "
    "2026-09-27 and 2026-12-26 (NASA's 2026 eclipse page lists only 4 eclipses all year, all "
    "outside this window); no bright/naked-eye comet perihelion found in-window (a WebSearch "
    "aggregator check, not a direct JPL SBDB query -- treat as a lead, not exhaustive); Solar "
    "Cycle 25 maximum was already jointly declared by NASA/NOAA on 2024-10-16, predating this "
    "window; JWST/Euclid have no confirmed public data-release DAY inside the window (JWST Cycle "
    "5 started July 2026, Euclid DR1 is only 'late 2026'). BepiColombo's two insertion dates and "
    "Hera's exact day are sourced from secondary aggregators, NOT esa.int directly -- confirm "
    "before scripting. The `flyby` category also appears LIVE via JPL SSD cad.api (see "
    "fetch_close_approaches) for close NEO passes; that data is NOT hand-maintained like this table."
)


# ---------------------------------------------------------------------------
# Hook / chatbot-test / scale word lists (research note 24 (private) editorial rule, research note 29 (private) hook cues)
# ---------------------------------------------------------------------------

HOOK_WORDS = [
    "unexpected", "puzzle", "puzzling", "can't explain", "cannot explain", "shouldn't", "should not",
    "first ever", "first-ever", "record", "never before", "never-before", "mystery", "mysterious",
    "surprising", "baffl", "unprecedented", "unusual", "strange", "anomaly", "anomalous", "breaks",
    "shatters", "rewrites", "redefine", "contradict", "unknown", "unexplained", "defies", "riddle",
    "wrong", "impossible", "hidden", "secret", "reveals", "discovery", "discovered",
]
SCALE_WORDS = [
    "massive", "giant", "huge", "enormous", "tiny", "tiniest", "billion", "trillion", "million",
    "light-year", "light years", "times the size", "times more", "times larger", "times bigger",
    "largest", "smallest", "biggest", "farthest", "furthest", "closest", "oldest", "youngest",
    "deepest", "brightest", "faintest", "heaviest", "lightest", "size of", "as wide as",
]
DEFINITIONAL_RE = re.compile(
    r"^\s*(what is|what are|how does|how do|why does|why do|why is|why are|what causes|"
    r"how is|how are|what happens when)\b", re.IGNORECASE)


def hook_score(text: str) -> Tuple[float, List[str]]:
    """No number bonus (research note 43 (private) rule 4 / 38 T4: only 1/20 title winners carry a number;
    research note 47 (private) step 7.4 told this scorer to drop it -- a number in the title/summary is no
    longer a positive signal here)."""
    t = text.lower()
    hits = [w for w in HOOK_WORDS if w in t]
    scale_hits = [w for w in SCALE_WORDS if w in t]
    raw = len(hits) * 1.5 + len(scale_hits) * 1.0
    return min(10.0, raw * 1.3), hits + [f"scale:{w}" for w in scale_hits]


def chatbot_test_score(title: str, hook_hits: List[str]) -> Tuple[float, str]:
    """Proxy for research note 24 (private)'s editorial rule. High = safe (provocation-shaped). Low = a chatbot
    answers this in one screen (retrieval-shaped)."""
    is_definitional = bool(DEFINITIONAL_RE.search(title))
    real_hook_hits = [h for h in hook_hits if not h.startswith("scale:") and h != "has_number"]
    if is_definitional and not real_hook_hits:
        return 2.0, "definitional framing ('what is/how does...'), no contradiction/unknown cue -- likely one-screen retrievable"
    if is_definitional and real_hook_hits:
        return 5.5, "definitional phrasing but carries a contradiction/unknown cue -- borderline, reframe the title before scripting"
    if real_hook_hits:
        return 9.0, "not definitional, carries a contradiction/unknown/record cue -- provocation-shaped"
    return 7.0, "not definitional, but no explicit hook cue detected either -- check manually"


# ---------------------------------------------------------------------------
# LAY-HOOK sub-score -- research note 46 (private), UNVALIDATED, low weight (chairman ruling, research note 47 (private) step 7).
#
# research note 46 (private) scored six "lay-hook" features (jargon, picturability, familiar-strange,
# stakes-or-person, reading grade, question-form) against 601 titles (n=205 within-channel
# hit/miss) and found NO significant separation: picturability shows a weak positive trend that
# does not clear significance (Spearman rho=+0.10, p=0.16; Fisher odds=1.53, p=0.21) and RUNS
# BACKWARDS in the n=12 newcomer-breakout case that matters most at zero subs (0.292 breakout vs
# 0.373 rest, research note 46 (private) Table 2); question-form is the only feature that is even borderline
# significant (Fisher odds=2.46, p=0.052). The chairman ruling: scene-first titling (research note 47 (private))
# is the validated PROCESS rule; this lay_hook score is a low-weight TIE-BREAKER only, not a
# measured [C]/[F] rule -- see research note 46 (private) section 8-9 for the full non-significance writeup and
# caveats (multiple comparisons, n=205-601, transparent heuristic not a trained classifier).
#
# Word lists below are copied from research note 46 (private) section 2.2's own (non-exhaustive, "...") lists,
# and the picturability logic is research note 46 (private)'s fixed (post-hand-check, 95% agreement) version,
# calibrated to its four worked examples: "the sky turned red"=1.0, "The Sun Beat Its Own
# Forecast"=0.5, "black hole"=1.0, "the universe has two ages"=0.0.
# ---------------------------------------------------------------------------

LAY_HOOK_COLOR_WORDS = ["red", "pink", "orange", "gold", "golden", "blue", "green", "purple",
                        "black", "white", "yellow"]
LAY_HOOK_EVENT_WORDS = ["explode", "exploded", "explodes", "crash", "crashed", "storm",
                        "killed", "turned", "shattered", "collision", "collisions", "collide",
                        "collided"]
LAY_HOOK_SCENE_NOUNS = ["sky", "ocean", "mountain", "ring", "rings", "cloud", "clouds"]
LAY_HOOK_NAMEABLE_OBJECTS = ["planet", "sun", "moon", "probe", "black hole", "galaxy"]
LAY_HOOK_ABSTRACT_MARKERS = ["forecast", "hypothesis", "mystery", "paradox", "tension", "beat",
                             "ignored", "vs", "universe", "cosmos"]


def picturability_score(text: str) -> float:
    """0 / 0.5 / 1.0 picturability proxy (research note 46 (private) section 2.2). UNVALIDATED: weak positive
    trend only (p=0.16-0.21), reverses sign in the newcomer-breakout case -- not a proven
    predictor, see the module note above."""
    t = text.lower()
    if (any(w in t for w in LAY_HOOK_COLOR_WORDS)
            or any(w in t for w in LAY_HOOK_EVENT_WORDS)
            or any(w in t for w in LAY_HOOK_SCENE_NOUNS)):
        return 1.0
    if any(w in t for w in LAY_HOOK_NAMEABLE_OBJECTS):
        return 0.5 if any(w in t for w in LAY_HOOK_ABSTRACT_MARKERS) else 1.0
    return 0.0


def lay_hook_score(text: str) -> float:
    """lay_hook = 0.6*picturability + 0.4*question-form (research note 46 (private) section 9 formula, its only
    two features with any positive signal at all). UNVALIDATED -- see module note above. Returns
    0-1; the composite applies a 0.05 weight (research note 47 (private)'s proposed 0.15-0.20 weights are for a
    future, separately-validated premise-bank composite, not this scorer)."""
    p = picturability_score(text)
    q = 1.0 if "?" in text else 0.0
    return round(0.6 * p + 0.4 * q, 3)


# ---------------------------------------------------------------------------
# VISUALS check -- reuse tools/space_assets.py (subprocess), per research note 22 (private).
# ---------------------------------------------------------------------------

VISUALS_SOURCES = "nasa,svs,esahubble,esawebb,eso,noirlab"
STOPWORDS = set("""
a an the of in on at to for and or with from into over under new found is are was were has have had
just first this that its their his her been being be by as it we our discovery discovered nasa esa
release photo photos science press image video images announcement update reveals revealed stunning
panorama spots secret chaotic extremely record records smashes proto distance out sync partner
win wins winning week weeks ahead tests test provide provides welcomes welcome welcomed partners
partnering three two four five six seven eight nine ten high middle school challenge challenges
guidance material materials exhibition dual mode design engineering industry participation signing
signs sign trip witness arrive arrives arriving go goes going forward candidates candidate days ago
""".split())
# Boilerplate title prefixes ESO/NOIRLab/ESA use ("Photo Release: ...", "Science Release: ...") --
# strip before extracting nouns, else the two capitalized boilerplate words win over the real subject.
_BOILERPLATE_PREFIX_RE = re.compile(
    r"^\s*(photo|science|press|image|video)\s+release\s*:\s*", re.IGNORECASE)


def _noun_score(w: str) -> float:
    """Higher = more likely to be the real subject, not a headline function word. NASA/ESA press
    titles are Title-Case-d ('NASA Tests Dual Mode Propulsion CubeSat'), so 'is capitalized' alone
    doesn't distinguish a proper noun from an ordinary headline verb -- this also rewards internal
    mixed case / all-caps acronyms (CubeSat, BepiColombo, JWST) and raw length, both of which track
    specificity better than capitalization does in Title Case text."""
    s = 0.0
    if re.search(r"[a-z][A-Z]", w) or (w.isupper() and len(w) >= 3):
        s += 5.0  # CubeSat, BepiColombo, JWST-style -- strong proper-noun/mission-name signal
    if w[0].isupper():
        s += 1.0
    s += min(len(w), 12) * 0.3  # longer words tend to be more specific than headline filler
    return s


def key_nouns(title: str, n: int = 2) -> str:
    """Extract a SHORT (default 2-word) query for the archive search endpoints. These endpoints
    do literal/AND-of-all-words matching (confirmed empirically -- a 5-7 word phrase reliably
    returns 0 hits even for well-illustrated subjects like 'Saturn rings Chrysalis shattered moon',
    while 'Saturn rings' returns 33), so fewer, more generic words beat more, more specific ones."""
    title = _BOILERPLATE_PREFIX_RE.sub("", title)
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-']*", title)
    kept = [w for w in words if w.lower() not in STOPWORDS and len(w) > 2]
    ranked = sorted(kept, key=_noun_score, reverse=True)
    ordered = []
    for w in ranked:
        if w not in ordered:
            ordered.append(w)
    return " ".join(ordered[:n]) or title[:60]


# Auxiliary/function words that show up capitalized in Title-Case headlines but aren't a place,
# object or colour -- excluded from scene_seeds()'s proper-noun fallback pass.
_SCENE_SEED_FUNCTION_WORDS = set("""
shouldn't wouldn't couldn't didn't doesn't isn't wasn't weren't won't can't nobody everyone every
still then after before always never only about there it's that this which who what why how when
where might may could would was were has have had did does the its their his her they we you
found gone yet universe cosmos
""".split())


def scene_seeds(text: str, n: int = 3) -> List[str]:
    """research note 47 (private)'s step 1 (scene inventory), automated to a crude first pass: the `n` most
    concrete nouns/places/colours found in a candidate's title+summary, as raw material for
    scene-first titling -- NOT a replacement for the full 8-step method. Two passes, in order of
    appearance: (1) a colour/scene-noun/nameable-object word (the LAY_HOOK_* lists above -- the
    most reliably "concrete" hits); (2) fills any remaining slots with capitalized proper nouns
    (a place, a named probe/mission), skipping common headline function words."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-']*", text)
    concrete_pool = set(LAY_HOOK_COLOR_WORDS + LAY_HOOK_SCENE_NOUNS + LAY_HOOK_NAMEABLE_OBJECTS)
    seeds: List[str] = []
    seen_lower = set()
    for w in words:
        wl = w.lower()
        if len(w) > 2 and wl in concrete_pool and wl not in seen_lower:
            seeds.append(wl)
            seen_lower.add(wl)
        if len(seeds) >= n:
            return seeds
    for w in words:
        wl = w.lower()
        if (len(w) > 2 and w[0].isupper() and wl not in STOPWORDS
                and wl not in _SCENE_SEED_FUNCTION_WORDS and wl not in seen_lower):
            seeds.append(w)
            seen_lower.add(wl)
        if len(seeds) >= n:
            break
    return seeds


def visuals_check_with_fallback(title: str, timeout: int = 90) -> Dict[str, Any]:
    """Try a 2-word query; if that's 0 hits (and not an error), retry with just the single most
    prominent word before concluding VISUALS FAIL -- guards against AND-logic over-specification."""
    q2 = key_nouns(title, n=2)
    vc = visuals_check(q2, timeout=timeout)
    if vc.get("hits", 0) == 0 and not vc.get("error"):
        q1 = key_nouns(title, n=1)
        if q1 and q1 != q2:
            vc1 = visuals_check(q1, timeout=timeout)
            if vc1.get("hits", 0) > 0:
                vc1["fallback_from"] = q2
                return vc1
    return vc


def visuals_check(query: str, timeout: int = 90) -> Dict[str, Any]:
    """Runs space_assets.py search and counts hits with width>=1920 across the 6 archive sources."""
    cmd = [sys.executable, SPACE_ASSETS, "search", query,
           "--sources", VISUALS_SOURCES, "--limit", "8", "--min-width", "1920", "--json"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"query": query, "hits": 0, "by_source": {}, "error": "timeout", "pass": False}
    except Exception as e:
        return {"query": query, "hits": 0, "by_source": {}, "error": str(e), "pass": False}
    rows = []
    try:
        # cmd_search prints log() lines to stderr and the JSON array to stdout
        rows = json.loads(p.stdout) if p.stdout.strip() else []
    except Exception as e:
        return {"query": query, "hits": 0, "by_source": {}, "error": f"bad json: {e}", "pass": False}
    qualifying = [r for r in rows if (r.get("width") or 0) >= 1920]
    by_source: Dict[str, int] = {}
    for r in qualifying:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
    return {"query": query, "hits": len(qualifying), "by_source": by_source,
            "total_returned": len(rows), "error": None, "pass": len(qualifying) > 0}


def visuals_score(vc: Dict[str, Any]) -> float:
    n = vc.get("hits", 0)
    if vc.get("error"):
        return 0.0
    if n == 0:
        return 0.0
    if n <= 2:
        return 4.0
    if n <= 5:
        return 7.0
    return 10.0


# ---------------------------------------------------------------------------
# SATURATION check -- withheld in the public version.
# ---------------------------------------------------------------------------

def saturation_check(query: str, sleep_s: float = 1.0) -> Dict[str, Any]:
    return {"query": query, "skipped": "withheld", "n_hits": 0, "max_views": None}


def saturation_score(sc: Dict[str, Any]) -> float:
    if sc.get("skipped"):
        return 5.0  # neutral/unknown -- don't punish or reward what we couldn't check
    mv = sc.get("max_views")
    if mv is None:
        return 8.0  # essentially nothing found -- white space
    if mv < 50_000:
        base = 10.0
    elif mv < 200_000:
        base = 7.0
    elif mv < 1_000_000:
        base = 4.0
    else:
        base = 1.0
    if (sc.get("recent_14d_of_top5_checked") or 0) >= 2:
        base = max(0.0, base - 2.0)
    return base


# ---------------------------------------------------------------------------
# PULL
# ---------------------------------------------------------------------------

def pull(days: int) -> Dict[str, Any]:
    cutoff_past = now_utc() - datetime.timedelta(days=days)
    items: List[Dict[str, Any]] = []
    feed_status: List[Dict[str, Any]] = []

    for feed in FEEDS:
        raw_items, err = fetch_feed(feed)
        if err:
            feed_status.append({"name": feed["name"], "url": feed["url"], "ok": False, "error": err, "n": 0})
            continue
        n_kept = 0
        n_excluded_reference = 0
        for it in raw_items:
            dt = parse_date(it.get("date_raw"))
            if dt is not None and dt < cutoff_past:
                continue
            link = it.get("link", "")
            if feed["name"] == "nasa_science" and is_reference_page(link):
                # science.nasa.gov/feed/ is a SITEWIDE "recently touched" feed, not press-only --
                # it mixes in reference/catalog stub pages (APOD contributor bios, exoplanet
                # star-catalog entries, biological-physical investigation stubs) whose feed
                # timestamp updates whenever the page is touched, not when something happened.
                # These scored as false "same-day news" until this filter was added -- see
                # research note 39 (private) for the before/after example (David N. Spergel, MVP-Plant-02, etc).
                n_excluded_reference += 1
                continue
            items.append({
                "title": it["title"], "link": link, "summary": it.get("summary", ""),
                "date_raw": it.get("date_raw", ""), "date_iso": dt.isoformat() if dt else None,
                "source": feed["name"], "tier": feed["tier"], "category": feed["category"],
            })
            n_kept += 1
        feed_status.append({"name": feed["name"], "url": feed["url"], "ok": True,
                             "n_total": len(raw_items), "n_kept": n_kept,
                             "n_excluded_reference_pages": n_excluded_reference})
        time.sleep(0.3)

    # arXiv
    arxiv_status = []
    for feed in ARXIV_FEEDS:
        raw_items, err = fetch_feed(feed)
        arxiv_status.append({"name": feed["name"], "n": len(raw_items), "error": err})
        for it in raw_items:
            items.append({
                "title": it["title"], "link": it.get("link", ""), "summary": it.get("summary", ""),
                "date_raw": it.get("date_raw", ""), "date_iso": None,
                "source": feed["name"], "tier": 2, "category": "arxiv_new",
            })
        time.sleep(0.3)
    arxiv_note = (
        "arXiv per-category RSS feeds (rss.arxiv.org) returned an empty <channel> for all 5 "
        "categories on this run (2026-09-27, a Sunday) -- arXiv's own <skipDays> tag lists "
        "Saturday and Sunday as non-publishing days, so this is an expected weekend gap, not a "
        "feed failure. The brief's press-cross-reference filter (drop arXiv items with no press "
        "match / no press cue) is implemented in score() but had zero input this run. "
        "export.arxiv.org/api/query (the fuller, date-range-queryable API) returned HTTP 406 on "
        "every attempt from this network -- see DEAD_SOURCES. Re-run on a weekday for real arXiv "
        "coverage."
    )

    # NOAA space weather -- only keep NOTABLE alerts (G3+/major) as story candidates; routine
    # K-index/minor alerts fire dozens of times a day and would flood the shortlist with noise.
    noaa_items_all = fetch_noaa_alerts()
    noaa_notable = [it for it in noaa_items_all if it.get("notable")]
    items.extend(noaa_notable)
    noaa_status = {"n_total": len(noaa_items_all), "n_notable_kept": len(noaa_notable)}

    # JPL close approaches (next `days` days)
    flyby_items = fetch_close_approaches(days_ahead=days)
    items.extend(flyby_items)

    return {
        "pulled_at": now_utc().isoformat(),
        "days_window": days,
        "items": items,
        "feed_status": feed_status,
        "arxiv_status": arxiv_status,
        "arxiv_note": arxiv_note,
        "noaa_status": noaa_status,
        "dead_sources": DEAD_SOURCES,
        "mission_calendar": MISSION_CALENDAR,
        "mission_calendar_caveat": MISSION_CALENDAR_CAVEAT,
    }


# ---------------------------------------------------------------------------
# SCORE
# ---------------------------------------------------------------------------

# lay_hook carved out of "hook" at 0.05 (UNVALIDATED tie-breaker -- see lay_hook_score() note
# above / research note 46 (private) / research note 47 (private) step 7). Sums still 1.0.
WEIGHTS_TIMELY = {"timeliness": 0.30, "tier": 0.15, "visuals": 0.25, "hook": 0.10,
                  "chatbot": 0.05, "saturation": 0.10, "lay_hook": 0.05}
WEIGHTS_EVERGREEN = {"hook": 0.30, "visuals": 0.35, "chatbot": 0.15, "saturation": 0.15,
                     "lay_hook": 0.05}

TIER_SCORE = {3: 10.0, 2: 6.0, 1: 3.0}


def timeliness_score(date_iso: Optional[str]) -> Tuple[float, Optional[int]]:
    if not date_iso:
        return 4.0, None  # unknown date -- mild penalty, not a hard fail
    try:
        dt = datetime.datetime.fromisoformat(date_iso)
    except Exception:
        return 4.0, None
    days = (now_utc() - dt).days  # negative = future
    score = max(0.0, 10.0 - (abs(days) / 90.0) * 10.0)
    return score, days


def dedup(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = (it.get("title", "").strip().lower(), it.get("link", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def score_timely(pulled: Dict[str, Any], shortlist_n: int, do_visuals: bool, do_saturation: bool) -> Dict[str, Any]:
    items = dedup(pulled["items"])
    scored = []
    for it in items:
        text = f"{it.get('title','')} {it.get('summary','')}"
        h_score, h_hits = hook_score(text)
        lh_score = lay_hook_score(text)  # 0-1, UNVALIDATED tie-breaker -- see lay_hook_score() note
        t_score, days = timeliness_score(it.get("date_iso"))
        tier = it.get("tier", 1)
        tr_score = TIER_SCORE.get(tier, 3.0)
        cb_score, cb_note = chatbot_test_score(it.get("title", ""), h_hits)
        prelim = 0.5 * t_score + 0.3 * tr_score + 0.2 * h_score
        rec = dict(it)
        rec.update({
            "days_from_now": days, "timeliness_score": round(t_score, 2),
            "tier_score": tr_score, "hook_score": round(h_score, 2), "hook_hits": h_hits,
            "lay_hook_score": lh_score,
            "chatbot_score": cb_score, "chatbot_note": cb_note, "prelim_score": round(prelim, 2),
            "visuals": None, "visuals_score": None, "saturation": None, "saturation_score": None,
        })
        scored.append(rec)

    scored.sort(key=lambda r: r["prelim_score"], reverse=True)
    shortlist = scored[:shortlist_n]
    rest = scored[shortlist_n:]

    for rec in shortlist:
        yt_query = key_nouns(rec["title"], n=5)  # longer phrase is fine (good) for YT search relevance
        if do_visuals:
            vc = visuals_check_with_fallback(rec["title"])  # short 2-word (then 1-word) query -- see fn docstring
            rec["visuals"] = vc
            rec["visuals_score"] = visuals_score(vc)
        if do_saturation:
            sc = saturation_check(yt_query)
            rec["saturation"] = sc
            rec["saturation_score"] = saturation_score(sc)
        w = WEIGHTS_TIMELY
        parts = {
            "timeliness": rec["timeliness_score"], "tier": rec["tier_score"],
            "visuals": rec["visuals_score"] if rec["visuals_score"] is not None else 0.0,
            "hook": rec["hook_score"], "chatbot": rec["chatbot_score"],
            "saturation": rec["saturation_score"] if rec["saturation_score"] is not None else 5.0,
            "lay_hook": rec["lay_hook_score"] * 10.0,  # rescale 0-1 -> 0-10 to match the other parts
        }
        rec["composite_score"] = round(sum(w[k] * parts[k] for k in w), 2)

    shortlist.sort(key=lambda r: r["composite_score"], reverse=True)
    for rec in rest:
        rec["composite_score"] = None
        rec["note"] = "below shortlist cutoff -- visuals/saturation not checked (runtime bound)"

    return {"scored_at": now_utc().isoformat(), "weights": WEIGHTS_TIMELY,
            "shortlist_n": shortlist_n, "shortlist": shortlist, "rest": rest,
            "feed_status": pulled.get("feed_status"), "arxiv_status": pulled.get("arxiv_status"),
            "arxiv_note": pulled.get("arxiv_note"), "noaa_status": pulled.get("noaa_status"),
            "dead_sources": pulled.get("dead_sources"),
            "mission_calendar": pulled.get("mission_calendar"),
            "mission_calendar_caveat": pulled.get("mission_calendar_caveat")}


# ---------------------------------------------------------------------------
# EVERGREEN
# ---------------------------------------------------------------------------

# 15 from research note 31 (private) Part 1 (K1-5, O1-5, F1-5). `query` = longer phrase for the saturation
# check (withheld); `vis_query` = short 2-word query for the archive VISUALS check, because
# the archive endpoints do literal AND-of-all-words matching (confirmed empirically: see
# key_nouns() docstring) -- a long phrase reliably returns 0 hits even for well-illustrated
# subjects. Every vis_query below was live-tested 2026-09-27 and returns >0 hits (count noted).
EVERGREEN_SEED_31 = [
    {"id": "K1", "title": "The Mars That Only Exists at Night (methane: Curiosity vs TGO)",
     "query": "Mars methane Curiosity Trace Gas Orbiter disagreement", "vis_query": "Mars methane"},  # 8 hits
    {"id": "K2", "title": "The Sun Is Ignoring the Forecast (Solar Cycle 25 vs the panel)",
     "query": "Solar Cycle 25 forecast wrong terminator event", "vis_query": "solar cycle"},  # 11 hits
    {"id": "K3", "title": "Saturn's Rings Are Lying About Their Age (Cassini ring rain vs Chrysalis)",
     "query": "Saturn rings young ring rain Chrysalis shattered moon", "vis_query": "Saturn rings"},  # 26 hits
    {"id": "K4", "title": "The Darkness Past Pluto Is Too Bright (New Horizons dust + sky-glow excess)",
     "query": "New Horizons LORRI cosmic optical background excess dust", "vis_query": "New Horizons"},  # 14 hits
    {"id": "K5", "title": "The Raft That Challenged the First Stars (EDGES vs SARAS3)",
     "query": "EDGES 21cm signal SARAS3 cosmic dawn dispute", "vis_query": "cosmic dawn"},  # 27 hits (see caveat: keyword match, not verified on-topic)
    {"id": "O1", "title": "The Universe Has Two Ages, and Nobody Can Agree Which Is Wrong (Hubble tension)",
     "query": "Hubble tension Planck SH0ES JWST Cepheid", "vis_query": "Hubble tension"},  # 10 hits
    {"id": "O2", "title": "NASA Found Flowing Water on Mars. It Was Wrong. Then It Was Right.",
     "query": "Mars recurring slope lineae dry flows InSight liquid water 2024", "vis_query": "Mars water"},  # 18 hits
    {"id": "O3", "title": "Why Is the Sun's Atmosphere 200 Times Hotter Than Its Surface?",
     "query": "coronal heating problem Parker Solar Probe switchbacks", "vis_query": "solar corona"},  # 19 hits
    {"id": "O4", "title": "Webb Found Galaxies That Shouldn't Exist. Then They Stopped Being Galaxies.",
     "query": "JWST little red dots black hole star 2025", "vis_query": "Webb galaxies"},  # 29 hits
    {"id": "O5", "title": "We Photographed Every Spacecraft That Died on the Moon",
     "query": "LRO photographed crash site Moon Vikram found amateur", "vis_query": "Moon crater"},  # 24 hits
    {"id": "F1", "title": "The Photograph That Shouldn't Exist (Pale Blue Dot mistake + reprocessing)",
     "query": "Pale Blue Dot Voyager reprocessed Kevin Gill", "vis_query": "Pale Dot"},  # 22 hits
    {"id": "F2", "title": "Case File: The Neutrino That Came From Nowhere (IceCube-170922A)",
     "query": "IceCube neutrino blazar TXS 0506+056", "vis_query": "IceCube neutrino"},  # 8 hits
    {"id": "F3", "title": "The Instrument That Lied for 30 Years (Hubble mirror flaw + COSTAR)",
     "query": "Hubble mirror flaw spherical aberration COSTAR repair", "vis_query": "Hubble mirror"},  # 21 hits
    {"id": "F4", "title": "The Sky Is Being Paved (satellite streaks vs the archive)",
     "query": "satellite streaks astronomical images Starlink ZTF Rubin", "vis_query": "satellite streaks"},  # 7 hits
    {"id": "F5", "title": "The Sun Has a Rhythm Nobody Predicted (Solar Cycle 25 panel miss)",
     "query": "Solar Cycle 25 prediction panel wrong Gannon storm", "vis_query": "solar storm"},  # 16 hits
]

# +10 new evergreen premises, "recomputed/revised in the last 5 years" angle (brief's own list,
# minus Saturn ring age / Mars methane / Hubble tension -- already covered above, deduped so the
# same premise isn't scored twice under two names).
EVERGREEN_SEED_NEW = [
    {"id": "E1", "title": "Betelgeuse's Great Dimming (2019-20): dust cloud or pre-supernova?",
     "query": "Betelgeuse great dimming dust cloud supernova", "vis_query": "Betelgeuse star"},  # 14 hits
    {"id": "E2", "title": "Venus's Phosphine Signal: detected, disputed, retracted, reargued",
     "query": "Venus phosphine detection dispute atmosphere", "vis_query": "Venus atmosphere"},  # 15 hits
    {"id": "E3", "title": "The Milky Way Weighs Less Than We Thought (Gaia mass revisions)",
     "query": "Milky Way mass revised Gaia lighter estimate", "vis_query": "Milky Way"},  # 40 hits
    {"id": "E4", "title": "Planet Nine: the orbital clustering nobody can rule out",
     "query": "Planet Nine orbital clustering evidence search", "vis_query": "Kuiper belt"},  # 30 hits
    {"id": "E5", "title": "Europa's Plumes: seen once, archived twice, still contested",
     "query": "Europa water plume Galileo magnetometer JWST", "vis_query": "Europa plume"},  # 18 hits
    {"id": "E6", "title": "The Moon Is Older Than We Thought (Apollo zircon redate)",
     "query": "Moon age Apollo zircon dating older formation", "vis_query": "Moon Apollo"},  # 20 hits
    {"id": "E7", "title": "Enceladus's Missing Ingredient for Life, Found in Old Cassini Data",
     "query": "Enceladus phosphates plume ice grains Cassini", "vis_query": "Enceladus plume"},  # 4 hits
    {"id": "E8", "title": "The Wow! Signal, Reanalyzed",
     "query": "Wow signal reanalysis hydrogen cloud explanation", "vis_query": "Wow signal"},  # 4 hits (see caveat: keyword match, not verified on-topic)
    {"id": "E9", "title": "'Oumuamua: the interstellar object that still won't resolve",
     "query": "Oumuamua interstellar object hydrogen outgassing hypothesis", "vis_query": "interstellar object"},  # 42 hits
    {"id": "E10", "title": "The Universe Is Glowing More Than the Galaxies Can Explain",
     "query": "cosmic optical background excess galaxies unexplained light", "vis_query": "cosmic background"},  # 39 hits
]


def score_evergreen(seed: List[Dict[str, str]], do_visuals: bool, do_saturation: bool) -> List[Dict[str, Any]]:
    out = []
    for s in seed:
        h_score, h_hits = hook_score(s["title"])
        lh_score = lay_hook_score(s["title"])  # 0-1, UNVALIDATED tie-breaker -- see lay_hook_score() note
        cb_score, cb_note = chatbot_test_score(s["title"], h_hits)
        rec = dict(s)
        rec.update({"hook_score": round(h_score, 2), "hook_hits": h_hits,
                    "lay_hook_score": lh_score,
                    "chatbot_score": cb_score, "chatbot_note": cb_note,
                    "visuals": None, "visuals_score": None, "saturation": None, "saturation_score": None})
        if do_visuals:
            vc = visuals_check(s.get("vis_query") or s["query"])
            rec["visuals"] = vc
            rec["visuals_score"] = visuals_score(vc)
        if do_saturation:
            sc = saturation_check(s["query"])
            rec["saturation"] = sc
            rec["saturation_score"] = saturation_score(sc)
        w = WEIGHTS_EVERGREEN
        parts = {"hook": rec["hook_score"], "chatbot": rec["chatbot_score"],
                 "visuals": rec["visuals_score"] if rec["visuals_score"] is not None else 0.0,
                 "saturation": rec["saturation_score"] if rec["saturation_score"] is not None else 5.0,
                 "lay_hook": rec["lay_hook_score"] * 10.0}  # rescale 0-1 -> 0-10 to match the other parts
        rec["composite_score"] = round(sum(w[k] * parts[k] for k in w), 2)
        out.append(rec)
    out.sort(key=lambda r: r["composite_score"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_scene_seeds(candidates: List[Dict[str, Any]], top_n: int = 10) -> None:
    """--scenes flag (research note 47 (private) step 1, automated first pass): for each of the top N scored
    candidates, print its 3 most concrete nouns/places/colours as scene seeds for titling. Not a
    replacement for the full 8-step scene-first method."""
    for rec in candidates[:top_n]:
        text = f"{rec.get('title', '')} {rec.get('summary', '')}"
        seeds = scene_seeds(text, n=3)
        label = rec.get("id") or rec.get("title", "?")
        print(f"[scene seeds] {label}: {', '.join(seeds) if seeds else '(none found)'}")


def cmd_pull(args):
    data = pull(args.days)
    with open(args.out, "w") as f:
        json.dump(data, f, indent=2)
    log(f"pulled {len(data['items'])} items -> {args.out}")


def cmd_score(args):
    with open(args.__dict__["in"]) as f:
        pulled = json.load(f)
    result = score_timely(pulled, args.shortlist_n, not args.no_visuals, not args.no_saturation)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    log(f"scored {len(result['shortlist'])} shortlisted + {len(result['rest'])} rest -> {args.out}")
    if getattr(args, "scenes", False):
        print_scene_seeds(result["shortlist"])


def cmd_evergreen(args):
    seed = EVERGREEN_SEED_31 + EVERGREEN_SEED_NEW
    result = score_evergreen(seed, not args.no_visuals, not args.no_saturation)
    with open(args.out, "w") as f:
        json.dump({"scored_at": now_utc().isoformat(), "weights": WEIGHTS_EVERGREEN,
                    "candidates": result}, f, indent=2)
    log(f"scored {len(result)} evergreen candidates -> {args.out}")
    if getattr(args, "scenes", False):
        print_scene_seeds(result)


def cmd_all(args):
    pulled = pull(args.days)
    timely = score_timely(pulled, args.shortlist_n, not args.no_visuals, not args.no_saturation)
    seed = EVERGREEN_SEED_31 + EVERGREEN_SEED_NEW
    evergreen = score_evergreen(seed, not args.no_visuals, not args.no_saturation)
    out = {
        "run_at": now_utc().isoformat(), "days_window": args.days,
        "weights_timely": WEIGHTS_TIMELY, "weights_evergreen": WEIGHTS_EVERGREEN,
        "timely_shortlist": timely["shortlist"], "timely_rest": timely["rest"],
        "evergreen_candidates": evergreen,
        "feed_status": pulled["feed_status"], "arxiv_status": pulled["arxiv_status"],
        "arxiv_note": pulled["arxiv_note"], "noaa_status": pulled["noaa_status"],
        "dead_sources": pulled["dead_sources"],
        "mission_calendar": pulled["mission_calendar"],
        "mission_calendar_caveat": pulled["mission_calendar_caveat"],
        "close_approach_note": "flyby items in timely_shortlist/rest with source=jpl_cad_api are "
                                "live NEO close-approach data (dist < 0.02 AU, next N days), not "
                                "hand-maintained -- see MISSION_CALENDAR for the hand-maintained list.",
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    log(f"full run complete -> {args.out}")
    if getattr(args, "scenes", False):
        print_scene_seeds(timely["shortlist"])
        print_scene_seeds(evergreen)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("pull", help="fetch last N days of feeds + calendar into a raw JSON file")
    pp.add_argument("--days", type=int, default=90)
    pp.add_argument("--out", required=True)
    pp.set_defaults(func=cmd_pull)

    sp = sub.add_parser("score", help="score a pulled raw JSON file into a ranked shortlist")
    sp.add_argument("--in", dest="in", required=True)
    sp.add_argument("--out", required=True)
    sp.add_argument("--shortlist-n", type=int, default=40)
    sp.add_argument("--no-visuals", action="store_true")
    sp.add_argument("--no-saturation", action="store_true")
    sp.add_argument("--scenes", action="store_true",
                     help="print each shortlisted candidate's 3 scene seeds (research note 47 (private) step 1)")
    sp.set_defaults(func=cmd_score)

    ep = sub.add_parser("evergreen", help="score the hand-maintained evergreen premise list")
    ep.add_argument("--out", required=True)
    ep.add_argument("--no-visuals", action="store_true")
    ep.add_argument("--no-saturation", action="store_true")
    ep.add_argument("--scenes", action="store_true",
                     help="print each candidate's 3 scene seeds (research note 47 (private) step 1)")
    ep.set_defaults(func=cmd_evergreen)

    ap_all = sub.add_parser("all", help="pull + score + evergreen in one pass -> single JSON")
    ap_all.add_argument("--days", type=int, default=90)
    ap_all.add_argument("--out", required=True)
    ap_all.add_argument("--shortlist-n", type=int, default=40)
    ap_all.add_argument("--no-visuals", action="store_true")
    ap_all.add_argument("--no-saturation", action="store_true")
    ap_all.add_argument("--scenes", action="store_true",
                        help="print scene seeds for top timely+evergreen candidates (research note 47 (private) step 1)")
    ap_all.set_defaults(func=cmd_all)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
