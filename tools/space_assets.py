#!/usr/bin/env python3
"""
space_assets.py -- search and fetch free, no-paid-stock space imagery/video for b-roll.

Sources (see tools/space_assets_README.md for endpoint notes and dead ends):
  nasa      images-api.nasa.gov      stills + video, US Gov public domain
  svs       svs.gsfc.nasa.gov        4K visualizations (video), public domain, STRIP AUDIO
  esahubble esahubble.org            stills + video, CC BY 4.0
  esawebb   esawebb.org              stills + video, CC BY 4.0
  eso       eso.org/public/images    stills + video, CC BY 4.0
  noirlab   noirlab.edu/public/images stills + video, CC BY 4.0
  hirise    uahirise.org             Mars stills, explicit public domain

Never returns a JAXA / Roscosmos / CNSA / CSA-primary / PBS asset (see BANNED_TERMS + README).

Usage:
  python3 tools/space_assets.py search "Enceladus geysers" --sources nasa,svs,esahubble,eso \
      --limit 10 --min-width 1920 --json
  python3 tools/space_assets.py fetch nasa:PIA17192 --out tests/space_broll/seeds/04_enceladus/
  python3 tools/space_assets.py shotlist shots.json --out tests/space_broll/seeds/
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any

try:
    import requests
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False

USER_AGENT = "longform-space-assets/0.1 (research tool; contact %s)" % os.environ.get("CONTACT_EMAIL", "set CONTACT_EMAIL")
RATE_SLEEP = 0.5
MAX_SINGLE_FILE_MB = 300  # safety guard, not a hard business rule

# Terms that mean "exclude this asset" per project rule: never emit JAXA / Roscosmos /
# CNSA / PBS assets, or anything whose primary agency is the Canadian Space Agency.
# NOTE: we deliberately do NOT blanket-filter the substring "CSA" out of credit lines,
# because esawebb/JWST credits routinely read "ESA/Webb, NASA & CSA, ..." (CSA is a minor
# partner, not the source archive) -- filtering that out would gut a required source.
# See README section "CSA/PBS judgement call".
BANNED_TERMS = [
    r"\bjaxa\b", r"\bhayabusa\d*\b", r"\bryugu\b", r"\bisas\b",
    r"\broscosmos\b", r"\bcnsa\b", r"chang.?e\b", r"\btianwen\b",
    r"\bcanadian space agency\b",
]
BANNED_RE = re.compile("|".join(BANNED_TERMS), re.IGNORECASE)
BANNED_DOMAINS = ("asc-csa.gc.ca", "pbs.org")


def log(msg: str):
    print(msg, file=sys.stderr)


def sleep_rate():
    time.sleep(RATE_SLEEP)


# ---------------------------------------------------------------------------
# HTTP helpers (requests if available, else urllib -- stdlib only otherwise)
# ---------------------------------------------------------------------------

def http_get(url: str, params: Optional[dict] = None, timeout: int = 25) -> bytes:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    sleep_rate()
    if HAVE_REQUESTS:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        return r.content
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_text(url: str, params: Optional[dict] = None, timeout: int = 25) -> str:
    return http_get(url, params, timeout).decode("utf-8", errors="replace")


def http_get_json(url: str, params: Optional[dict] = None, timeout: int = 25) -> Any:
    return json.loads(http_get_text(url, params, timeout))


def http_head_size(url: str, timeout: int = 20) -> Optional[int]:
    try:
        if HAVE_REQUESTS:
            r = requests.head(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, allow_redirects=True)
            cl = r.headers.get("Content-Length")
            return int(cl) if cl else None
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl else None
    except Exception:
        return None


def download_file(url: str, dest_path: str, timeout: int = 60) -> int:
    """Stream download; returns bytes written."""
    sleep_rate()
    if HAVE_REQUESTS:
        with requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, stream=True) as r:
            r.raise_for_status()
            total = 0
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    f.write(chunk)
                    total += len(chunk)
            return total
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest_path, "wb") as f:
        total = 0
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
        return total


def clean_pyrepr_bytes(raw: Any) -> str:
    """esahubble/esawebb/eso/noirlab per-image JSON leaks Python bytes-repr strings
    like "b'ESA & Someone'" or with \\xNN escapes for non-ASCII. Decode them cleanly."""
    if raw is None:
        return ""
    if not isinstance(raw, str):
        return str(raw)
    s = raw.strip()
    if (s.startswith("b'") and s.endswith("'")) or (s.startswith('b"') and s.endswith('"')):
        try:
            val = ast.literal_eval(s)
            if isinstance(val, bytes):
                return val.decode("utf-8", errors="replace")
            return str(val)
        except Exception:
            return s[2:-1]
    return s


def is_banned(*texts: str) -> bool:
    blob = " ".join(t for t in texts if t)
    return bool(BANNED_RE.search(blob))


def is_banned_domain(url: str) -> bool:
    return any(d in url for d in BANNED_DOMAINS)


# ---------------------------------------------------------------------------
# Asset row
# ---------------------------------------------------------------------------

@dataclass
class AssetRow:
    source: str
    id: str
    title: str
    media: str  # "still" | "video"
    width: Optional[int]
    height: Optional[int]
    licence: str
    credit: str
    page_url: str
    download_url: str
    date: str
    notes: str = ""

    def wh(self) -> str:
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# 1. NASA Image and Video Library
# ---------------------------------------------------------------------------

_NASA_SUFFIX_PRIORITY = ["orig", "large", "medium", "small", "mobile", "preview", "thumb"]
_STILL_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff")
_VIDEO_EXT = (".mp4", ".mov", ".m4v")


def _nasa_pick_largest(asset_hrefs: List[str], links: List[dict]) -> (Optional[str], Optional[int], Optional[int], str):
    """Return (url, width, height, media) for the best-quality file in a NASA asset manifest."""
    by_suffix = {}
    for href in asset_hrefs:
        low = href.lower()
        if low.endswith((".vtt", ".srt", ".json", ".hwshow", ".txt")):
            continue
        m = re.search(r"~([a-z]+)\.[a-z0-9]+$", low)
        suf = m.group(1) if m else "orig"
        by_suffix.setdefault(suf, href)
    for suf in _NASA_SUFFIX_PRIORITY:
        if suf in by_suffix:
            href = by_suffix[suf]
            low = href.lower()
            media = "still" if low.endswith(_STILL_EXT) else ("video" if low.endswith(_VIDEO_EXT) else "still")
            w = h = None
            base = href.rsplit("/", 1)[-1]
            for l in links:
                if l.get("href", "").rsplit("/", 1)[-1] == base:
                    w, h = l.get("width"), l.get("height")
                    break
            return href, w, h, media
    return None, None, None, "still"


def _nasa_licence(credit: str) -> str:
    """images-api.nasa.gov aggregates content from partner agencies verbatim, including
    items whose secondary_creator explicitly reads "Copyright: ESA/..." (e.g. Rosetta/OSIRIS
    comet 67P images). Do not blanket-assert public domain -- detect third-party rights
    holders and flag them for a per-asset check instead."""
    c = (credit or "").lower()
    if "copyright" in c or "esa/" in c or " esa " in c or c.startswith("esa"):
        return "CHECK: per-asset (esa.int)"
    return "Public domain (NASA)"


def search_nasa(query: str, limit: int, min_width: int) -> List[AssetRow]:
    rows: List[AssetRow] = []
    for media_type in ("image", "video"):
        try:
            data = http_get_json("https://images-api.nasa.gov/search",
                                  {"q": query, "media_type": media_type})
        except Exception as e:
            log(f"[nasa:{media_type}] search failed: {e}")
            continue
        items = data.get("collection", {}).get("items", [])[: max(limit, 3)]
        for it in items:
            if not it.get("data"):
                continue
            meta = it["data"][0]
            nasa_id = meta.get("nasa_id")
            title = meta.get("title", "")
            desc = meta.get("description", "")
            if is_banned(title, desc, meta.get("center", ""), " ".join(meta.get("keywords", []) or [])):
                continue
            try:
                manifest = http_get_json(f"https://images-api.nasa.gov/asset/{nasa_id}")
            except Exception as e:
                log(f"[nasa] asset manifest failed for {nasa_id}: {e}")
                continue
            hrefs = [x["href"] for x in manifest.get("collection", {}).get("items", [])]
            url, w, h, media = _nasa_pick_largest(hrefs, it.get("links", []) or [])
            if not url:
                continue
            if media == "still" and min_width and w and w < min_width:
                continue
            credit = meta.get("secondary_creator") or f"NASA/{meta.get('center', 'NASA')}"
            licence = _nasa_licence(credit)
            rows.append(AssetRow(
                source="nasa", id=nasa_id, title=title, media=media,
                width=w, height=h, licence=licence, credit=credit,
                page_url=f"https://images.nasa.gov/details-{nasa_id}",
                download_url=url, date=(meta.get("date_created") or "")[:10],
                notes="",
            ))
            if len(rows) >= limit:
                break
    return rows[:limit]


# ---------------------------------------------------------------------------
# 2. NASA SVS
# ---------------------------------------------------------------------------

def _svs_credit_string(main_credits: dict) -> str:
    parts = []
    for role, people in (main_credits or {}).items():
        names = []
        for p in people:
            nm = p.get("name", "")
            emp = p.get("employer", "")
            names.append(f"{nm} ({emp})" if emp else nm)
        if names:
            parts.append(f"{role} " + ", ".join(names))
    return "; ".join(parts) or "NASA/Goddard Space Flight Center"


def search_svs(query: str, limit: int, min_width: int) -> List[AssetRow]:
    rows: List[AssetRow] = []
    try:
        data = http_get_json("https://svs.gsfc.nasa.gov/api/search/",
                              {"search": query, "type": "visualization", "limit": max(limit, 3)})
    except Exception as e:
        log(f"[svs] search failed: {e}")
        return rows
    for hit in data.get("results", []):
        vid = hit.get("id")
        if is_banned(hit.get("title", ""), hit.get("description", "")):
            continue
        try:
            detail = http_get_json(f"https://svs.gsfc.nasa.gov/api/{vid}/")
        except Exception as e:
            log(f"[svs] detail failed for {vid}: {e}")
            continue
        best = None  # (w*h, url, w, h)
        for grp in detail.get("media_groups", []) or []:
            for item in grp.get("items", []):
                inst = item.get("instance", {})
                if inst.get("media_type") != "Movie":
                    continue
                w, h = inst.get("width") or 0, inst.get("height") or 0
                if best is None or w * h > best[0]:
                    best = (w * h, inst.get("url"), w, h)
        if not best or not best[1]:
            continue
        _, url, w, h = best
        if min_width and w and w < min_width:
            continue
        rows.append(AssetRow(
            source="svs", id=str(vid), title=detail.get("title", ""), media="video",
            width=w or None, height=h or None, licence="Public domain (NASA)",
            credit=_svs_credit_string(detail.get("main_credits")),
            page_url=detail.get("url", f"https://svs.gsfc.nasa.gov/{vid}/"),
            download_url=url, date=(detail.get("release_date") or "")[:10],
            notes="STRIP AUDIO before use (SVS visualizations may carry licensed music).",
        ))
        if len(rows) >= limit:
            break
    return rows


# ---------------------------------------------------------------------------
# 3/4/5. esahubble.org / esawebb.org / eso.org / noirlab.edu (shared Django "images" app)
# ---------------------------------------------------------------------------

# (domain, search_path, json_path template using {id}, id-prefix allowlist for this domain)
# NOTE: the search_path is "images/" (or "public/images/") with a ?search= query param,
# NOT "images/archive/search/" or "images/search/" -- both of those redirect to a page
# that silently ignores the query and returns the full unfiltered catalog (dead end,
# confirmed by fetching the same query twice and getting identical results both times;
# the real endpoint's result page correctly echoes "Search results for '<query>'").
_ESA_FAMILY = {
    "esahubble": ("esahubble.org", "images/", "images/{id}/api/json/", ("heic", "opo", "potw")),
    "esawebb":   ("esawebb.org",   "images/", "images/{id}/api/json/", ("weic", "potm")),
    "eso":       ("eso.org",       "public/images/", "public/images/{id}/api/json/", ("eso", "ann", "potw")),
    "noirlab":   ("noirlab.edu",   "public/images/", "public/images/{id}/api/json/", ("noirlab", "noao", "gemini", "potw")),
}


def _esa_family_ids(prefixes: tuple, html: str, limit: int) -> List[str]:
    # ids look like heic0109a, weic2216b, eso0202a, noirlab1912a, potm2208a -- a known
    # prefix followed by >=2 digits, optionally more letters/digits. A plain permissive
    # regex also matches junk paths like images/thumb300y/ or images/viewall/, so the
    # prefix must come from this source's explicit allowlist.
    prefix_alt = "|".join(re.escape(p) for p in prefixes)
    pat = re.compile(rf"images/(({prefix_alt})\d{{2,4}}[a-z0-9]*)/", re.IGNORECASE)
    seen, ids = set(), []
    for m in pat.finditer(html):
        i = m.group(1).lower()
        if i in seen:
            continue
        seen.add(i)
        ids.append(i)
        if len(ids) >= limit:
            break
    return ids


def _esa_family_licence(rights: str) -> str:
    r = (rights or "").lower()
    if "creative commons attribution 4.0" in r or "cc by 4.0" in r:
        return "CC BY 4.0"
    if not rights:
        return "CHECK: per-asset"
    return f"CHECK: per-asset ({rights[:60]})"


def search_esa_family(source_name: str, query: str, limit: int, min_width: int) -> List[AssetRow]:
    domain, search_path, json_tpl, prefixes = _ESA_FAMILY[source_name]
    rows: List[AssetRow] = []
    try:
        html = http_get_text(f"https://{domain}/{search_path}", {"search": query})
    except Exception as e:
        log(f"[{source_name}] search failed: {e}")
        return rows
    ids = _esa_family_ids(prefixes, html, limit * 2)
    for aid in ids:
        try:
            meta = http_get_json(f"https://{domain}/{json_tpl.format(id=aid)}")
        except Exception as e:
            log(f"[{source_name}] per-image json failed for {aid}: {e}")
            continue
        title = clean_pyrepr_bytes(meta.get("Title"))
        desc = clean_pyrepr_bytes(meta.get("Description"))
        subj = meta.get("Subject.Name") or []
        if is_banned(title, desc, " ".join(subj) if isinstance(subj, list) else str(subj)):
            continue
        resources = meta.get("Resources") or []
        # "Original"/full-size entries only; some records list only a Thumbnail here.
        stills = [r for r in resources if r.get("MediaType") == "Image" and r.get("Dimensions")
                  and r.get("ResourceType") != "Thumbnail"]
        videos = [r for r in resources if r.get("MediaType") == "Video" and r.get("Dimensions")]
        media = "video" if videos else "still"
        pool = videos if videos else stills
        url = w = h = None
        if pool:
            best = max(pool, key=lambda r: (r["Dimensions"][0] or 0) * (r["Dimensions"][1] or 0))
            url, w, h = best.get("URL"), best["Dimensions"][0], best["Dimensions"][1]
        if not url:
            # Fallback: Resources had nothing but a thumbnail (or was empty). Use the
            # canonical original TIFF + the AVM Spatial.ReferenceDimension pixel size,
            # falling back further to the large-JPEG formats_url.
            url = meta.get("ResourceURL")
            ref_dim = meta.get("Spatial.ReferenceDimension")
            if ref_dim and len(ref_dim) == 2:
                try:
                    w, h = int(float(ref_dim[0])), int(float(ref_dim[1]))
                except (TypeError, ValueError):
                    w = h = None
            if not url:
                formats = meta.get("formats_url") or {}
                url = formats.get("large") or formats.get("banner1920")
        if not url:
            continue
        if w:
            w, h = int(w), int(h)
        if media == "still" and min_width and w and w < min_width:
            continue
        page_url = meta.get("ReferenceURL") or f"https://{domain}/images/{aid}/"
        if is_banned_domain(url) or is_banned_domain(page_url):
            continue
        rows.append(AssetRow(
            source=source_name, id=aid, title=title, media=media,
            width=w, height=h,
            licence=_esa_family_licence(clean_pyrepr_bytes(meta.get("Rights"))),
            credit=clean_pyrepr_bytes(meta.get("Credit")),
            page_url=page_url, download_url=url,
            date=(meta.get("Date") or "")[:10], notes="",
        ))
        if len(rows) >= limit:
            break
    return rows


def search_esahubble(q, limit, min_width): return search_esa_family("esahubble", q, limit, min_width)
def search_esawebb(q, limit, min_width): return search_esa_family("esawebb", q, limit, min_width)
def search_eso(q, limit, min_width): return search_esa_family("eso", q, limit, min_width)
def search_noirlab(q, limit, min_width): return search_esa_family("noirlab", q, limit, min_width)


# ---------------------------------------------------------------------------
# 6. HiRISE
# ---------------------------------------------------------------------------

def search_hirise(query: str, limit: int, min_width: int) -> List[AssetRow]:
    rows: List[AssetRow] = []
    try:
        html = http_get_text("https://uahirise.org/results.php", {"keyword": query})
    except Exception as e:
        log(f"[hirise] search failed: {e}")
        return rows
    seen, hits = set(), []
    for m in re.finditer(r"<a href='(ESP_[0-9_]+|PSP_[0-9_]+)'><img src='([^']+)'[^>]*alt='([^']*)'", html):
        oid, thumb, alt = m.group(1), m.group(2), m.group(3)
        if oid in seen:
            continue
        seen.add(oid)
        hits.append((oid, alt))
        if len(hits) >= limit * 2:
            break
    for oid, alt in hits:
        if is_banned(alt):
            continue
        try:
            detail = http_get_text(f"https://uahirise.org/{oid}")
        except Exception as e:
            log(f"[hirise] detail failed for {oid}: {e}")
            continue
        tm = re.search(r"<title>HiRISE \| (.*?)</title>", detail)
        title = tm.group(1) if tm else alt
        cm = re.search(r"credit-text'><div align='right'>([^<]*)</div>", detail)
        credit = cm.group(1) if cm else "NASA/JPL-Caltech/UArizona"
        dm = re.search(r"Acquisition date</strong><br />([^<]+)<br", detail)
        date = dm.group(1) if dm else ""
        bm = re.search(r"href='(https?://hirise-pds[^']+_RED\.abrowse\.jpg)'", detail)
        if not bm:
            bm = re.search(r"href='(https?://hirise-pds[^']+\.abrowse\.jpg)'", detail)
        if not bm:
            bm = re.search(r"href='(https?://hirise-pds[^']+RED\.browse\.jpg)'", detail)
        if not bm:
            continue
        url = bm.group(1)
        jp2m = re.search(r"href='(https?://hirise-pds[^']+_RED\.JP2)' class='caption'>map-projected&nbsp;&nbsp; \(([\d]+MB)\)", detail)
        notes = f"Full-res JP2 available (not fetched, size {jp2m.group(2)}): {jp2m.group(1)}" if jp2m else \
            "Full-res JP2 (100s of MB-1.5GB) available on the detail page; not auto-fetched."
        rows.append(AssetRow(
            source="hirise", id=oid, title=title, media="still",
            width=None, height=None,  # browse JPEG dims not published inline; see notes
            licence="Public domain (NASA/HiRISE)", credit=credit,
            page_url=f"https://uahirise.org/{oid}", download_url=url,
            date=date, notes=notes,
        ))
        if len(rows) >= limit:
            break
    return rows


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

SOURCES = {
    "nasa": search_nasa,
    "svs": search_svs,
    "esahubble": search_esahubble,
    "esawebb": search_esawebb,
    "eso": search_eso,
    "noirlab": search_noirlab,
    "hirise": search_hirise,
}
ALL_SOURCES = list(SOURCES.keys())


def run_search(query: str, sources: List[str], limit: int, min_width: int) -> List[AssetRow]:
    out: List[AssetRow] = []
    for s in sources:
        fn = SOURCES.get(s)
        if not fn:
            log(f"unknown source '{s}', skipping")
            continue
        try:
            rows = fn(query, limit, min_width)
        except Exception as e:
            log(f"[{s}] search crashed: {e}")
            rows = []
        out.extend(rows)
    return out


def print_table(rows: List[AssetRow]):
    if not rows:
        print("(no results)")
        return
    hdr = f"{'source':10} {'id':22} {'media':6} {'wxh':13} {'licence':22} {'date':11} title"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r.source:10} {r.id:22} {r.media:6} {r.wh():13} {r.licence:22} {r.date or '?':11} {r.title[:60]}")
        print(f"           credit: {r.credit}")
        print(f"           page:   {r.page_url}")
        print(f"           dl:     {r.download_url}")
        if r.notes:
            print(f"           note:   {r.notes}")


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

def resolve_single(spec: str) -> Optional[AssetRow]:
    """spec is 'source:id' (re-searches by id/title) or a bare download URL."""
    if spec.startswith("http://") or spec.startswith("https://"):
        return AssetRow(source="url", id=spec.rsplit("/", 1)[-1], title=spec, media="unknown",
                         width=None, height=None, licence="CHECK: per-asset", credit="unknown",
                         page_url=spec, download_url=spec, date="")
    if ":" not in spec:
        log(f"cannot parse asset spec '{spec}', expected source:id or a URL")
        return None
    source, aid = spec.split(":", 1)
    if source == "nasa":
        rows = search_nasa(aid, 5, 0)
    elif source == "svs":
        rows = search_svs(aid, 5, 0)
    elif source in ("esahubble", "esawebb", "eso", "noirlab"):
        rows = search_esa_family(source, aid, 5, 0)
    elif source == "hirise":
        rows = search_hirise(aid, 5, 0)
    else:
        log(f"unknown source '{source}'")
        return None
    for r in rows:
        if r.id == aid:
            return r
    return rows[0] if rows else None


def ffmpeg_strip_audio(src: str, dst: str) -> bool:
    try:
        subprocess.run(["ffmpeg", "-y", "-i", src, "-an", "-c:v", "copy", dst],
                        check=True, capture_output=True)
        return True
    except Exception as e:
        log(f"ffmpeg strip-audio failed: {e}")
        return False


def ffmpeg_proxy_720p(src: str, dst: str) -> bool:
    try:
        subprocess.run(["ffmpeg", "-y", "-i", src, "-vf", "scale=-2:720",
                        "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-an", dst],
                        check=True, capture_output=True)
        return True
    except Exception as e:
        log(f"ffmpeg 720p proxy failed: {e}")
        return False


def fetch_one(row: AssetRow, out_dir: str) -> Dict[str, Any]:
    import os
    os.makedirs(out_dir, exist_ok=True)
    ext = row.download_url.rsplit(".", 1)[-1].split("?")[0]
    if len(ext) > 4 or "/" in ext:
        ext = "mp4" if row.media == "video" else "jpg"
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{row.source}_{row.id}")
    dest = f"{out_dir.rstrip('/')}/{base}.{ext}"

    size_hint = http_head_size(row.download_url)
    if size_hint and size_hint > MAX_SINGLE_FILE_MB * 1024 * 1024:
        log(f"SKIP (>{MAX_SINGLE_FILE_MB}MB, {size_hint/1e6:.0f}MB): {row.download_url}")
        return {"row": row.to_dict(), "downloaded": False, "reason": "too_large", "size_bytes": size_hint}

    log(f"fetching {row.source}:{row.id} -> {dest}")
    written = download_file(row.download_url, dest)
    result = {"row": row.to_dict(), "downloaded": True, "path": dest, "size_bytes": written}

    if row.source == "svs" and row.media == "video":
        noaudio = dest.replace(f".{ext}", f"_noaudio.{ext}")
        if ffmpeg_strip_audio(dest, noaudio):
            result["noaudio_path"] = noaudio
            import os as _os
            result["noaudio_size_bytes"] = _os.path.getsize(noaudio)
            proxy = dest.replace(f".{ext}", "_proxy720p.mp4")
            if ffmpeg_proxy_720p(noaudio, proxy):
                result["proxy720p_path"] = proxy
                result["proxy720p_size_bytes"] = _os.path.getsize(proxy)

    meta_path = dest + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump(result, f, indent=2)
    result["meta_path"] = meta_path
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_search(args):
    sources = args.sources.split(",") if args.sources else ALL_SOURCES
    rows = run_search(args.query, sources, args.limit, args.min_width)
    if args.json:
        print(json.dumps([r.to_dict() for r in rows], indent=2))
    else:
        print_table(rows)


def cmd_fetch(args):
    row = resolve_single(args.asset)
    if not row:
        log(f"could not resolve '{args.asset}'")
        sys.exit(1)
    result = fetch_one(row, args.out)
    print(json.dumps(result, indent=2))


def cmd_shotlist(args):
    import os
    with open(args.shotlist) as f:
        shots = json.load(f)
    manifest = []
    for shot in shots:
        sid = shot["id"]
        query = shot["query"]
        want = shot.get("want", "still")
        shot_dir = f"{args.out.rstrip('/')}/{sid}"
        os.makedirs(shot_dir, exist_ok=True)
        log(f"=== shot {sid}: '{query}' (want={want}) ===")
        candidates = run_search(query, ALL_SOURCES, args.limit, args.min_width)
        matching = [r for r in candidates if r.media == want] or candidates
        matching.sort(key=lambda r: (r.width or 0) * (r.height or 0), reverse=True)
        chosen = matching[0] if matching else None
        entry = {"shot": shot, "candidates": [r.to_dict() for r in candidates]}
        if chosen:
            entry["chosen"] = chosen.to_dict()
            entry["fetch_result"] = fetch_one(chosen, shot_dir)
        else:
            log(f"  no candidates found for shot {sid}")
        with open(f"{shot_dir}/manifest.json", "w") as f:
            json.dump(entry, f, indent=2)
        manifest.append(entry)
    print(json.dumps({"shots": len(manifest)}, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Search and fetch free space-imagery b-roll.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("search")
    sp.add_argument("query")
    sp.add_argument("--sources", default=None, help="comma list, default: all " + ",".join(ALL_SOURCES))
    sp.add_argument("--limit", type=int, default=10)
    sp.add_argument("--min-width", type=int, default=0)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_search)

    fp = sub.add_parser("fetch")
    fp.add_argument("asset", help="'source:id' e.g. nasa:PIA17192, or a bare URL")
    fp.add_argument("--out", required=True)
    fp.set_defaults(func=cmd_fetch)

    lp = sub.add_parser("shotlist")
    lp.add_argument("shotlist", help="JSON file: [{id, subject, query, want}]")
    lp.add_argument("--out", required=True)
    lp.add_argument("--limit", type=int, default=10)
    lp.add_argument("--min-width", type=int, default=0)
    lp.set_defaults(func=cmd_shotlist)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
