# space_assets.py

Searches free, no-paid-stock space-imagery archives for b-roll and fetches picks into a
per-shot folder. See `research note 22 (private)` for the licence research this
tool implements.

## Usage

```
python3 tools/space_assets.py search "Enceladus geysers" \
    --sources nasa,svs,esahubble,esawebb,eso,noirlab,hirise --limit 10 --min-width 1920 --json
python3 tools/space_assets.py fetch nasa:PIA17192 --out tests/space_broll/seeds/04_enceladus/
python3 tools/space_assets.py fetch svs:5675 --out tests/space_broll/seeds/05_volcano/
python3 tools/space_assets.py shotlist shots.json --out tests/space_broll/seeds/
```
`shots.json`: `[{"id": "04_enceladus", "subject": "...", "query": "...", "want": "still|video"}]`.
Every result row carries source, id, title, media, width x height (or "unknown"), licence,
credit, page URL, download URL, date. Dependencies: `requests` if importable, else stdlib
`urllib` (checked at import time). Rate limit: 0.5s sleep + a descriptive User-Agent on every
request. `fetch` skips (does not download) any single file over 300MB as a safety net.

## Dead ends found while building this (do not repeat)

- **SVS: `q=` is silently ignored.** `svs.gsfc.nasa.gov/api/search/?q=<term>&type=visualization`
  returns `count: 10586` (the full catalog) for *any* `q` value, including nonsense strings. The
  working param is **`search=`**. Verified: `?search=Enceladus+geysers` -> `count: 3`, relevant
  hits; `?q=Enceladus+geysers` -> `count: 10586`, unrelated recent items.
- **esahubble/esawebb/eso/noirlab: `/images/archive/search/?search=...` and `/images/search/?search=...`
  both ignore the query.** They redirect to a page that always lists the full unfiltered catalog
  (confirmed: two different queries against `images/archive/search/` returned byte-identical
  result sets, and the page literally renders "Search results for 'images.'" instead of the
  query). **The real endpoint is `/images/?search=<term>` (eso/noirlab: `/public/images/?search=`)**
  -- that page correctly echoes "Search results for '<term>'" and returns a single relevant page.
- **NASA images-api licence is not blanket public domain.** `images-api.nasa.gov` mirrors partner
  imagery verbatim; several Rosetta/67P records' `secondary_creator` reads literally
  `"Copyright: ESA/Rosetta/MPS for OSIRIS Team ..."`. The tool now detects `copyright`/`esa` tokens
  in the credit line and emits `CHECK: per-asset (esa.int)` instead of `Public domain (NASA)`.
  Caught by testing the required "comet nucleus 67P" case -- don't trust `images-api.nasa.gov`
  results as PD without checking `secondary_creator`.
- **esahubble/esawebb/eso/noirlab per-image JSON leaks Python bytes-repr strings**, e.g.
  `"Credit": "b'ESA & Someone\\xc2\\xa0Acknowledgement...'"`. Fixed with
  `ast.literal_eval` + `.decode('utf-8')`; do not treat these fields as plain strings.
  Some records' `Resources` array holds only a `Thumbnail` entry (no `Original`); fall back to
  `ResourceURL` + `Spatial.ReferenceDimension` (a float pixel-size pair) for width/height.
- **HiRISE has no JSON API.** Scraped from `uahirise.org/results.php?keyword=` (HTML) and the
  per-observation page for credit, acquisition date, and the `*.abrowse.jpg` browse URL. The
  full-resolution JP2 (100MB-1.5GB) is linked but never auto-fetched; its pixel dimensions are
  not published inline, so width/height are reported "unknown" for HiRISE stills.
- **CSA/PBS judgement call**: the brief says never emit a CSA asset, but esawebb/JWST credit
  lines routinely read "...NASA & CSA..." (CSA is a minor mission partner, not the source
  archive). Blanket-filtering the substring "CSA" would gut esawebb entirely, so the banned-term
  filter excludes JAXA/Hayabusa/Ryugu/ISAS/Roscosmos/CNSA/Chang'e/Tianwen by keyword, and CSA/PBS
  only by source domain (`asc-csa.gc.ca`, `pbs.org`), which none of the seven connectors query.
- **Not implemented** (optional in the brief): SDO/Helioviewer, JunoCam, LRO QuickMap as
  standalone connectors -- `nasa` (images-api) covers their public releases as a byproduct.
