# chart_style.py — house charting stack

Charting for the long-form economics explainer channel: matplotlib renders
each frame headlessly (Agg backend, no GPU/display needed), ffmpeg
assembles the PNG sequence into an mp4. $0 per chart, no external services.

See `research note 15 (private)` (tooling survey) and
`research note 17 (private)` (the shots this was
built to serve — shots 3, 4, 14 are CHART shots).

## Install

Already present on this box as user-site packages (no venv needed here):

```
pip install --user matplotlib numpy
```

`ffmpeg` must be on `PATH` (`/usr/bin/ffmpeg` here) for the `animate_*`
helpers' mp4 assembly step; `still()` and frame rendering work without it.

## House style

Everything lives as module-level constants in `chart_style.py` — change one
value there and every chart, past and future, re-skins:

| Constant | Value | Use |
|---|---|---|
| `WIDTH_PX` / `HEIGHT_PX` | 1920 / 1080 | 16:9, matches the episode canvas |
| `BG_COLOR` | `#12161f` | very dark blue-gray background |
| `TEXT_COLOR` | `#e8e4da` | off-white body/label text |
| `ACCENT_COLOR` | `#e0a458` | amber — the ONE accent: headline numbers, the "answer," a stamp, a route line |
| `SECONDARY_COLOR` | `#5b7a8c` | muted blue-gray — everything else needing a fill (bars, land shapes, baselines) |
| `MUTED_TEXT_COLOR` | `#9aa3ad` | dim text for the source line |
| `FONT_FAMILY` | `"DejaVu Sans"` | single constant, change in one place |
| `FPS` | 30 | frame rate for every assembled mp4 |

No gridlines, no chart spines, generous margins (`new_figure()` sets
`subplots_adjust`), and every chart gets a small source-line credit
bottom-left via `add_source_line()` — pass your own text or it falls back to
`DEFAULT_SOURCE`, which reads as an obvious placeholder ("[VERIFY]...") so an
un-fact-checked chart is never mistaken for a finished one.

## Functions

- `new_figure() -> (fig, ax)` — a blank 1920x1080 canvas already in house
  style. Build anything custom on top of it, then call `still()`.
- `still(fig, path)` — save one already-built figure to a PNG, close it.
- `add_title(fig, text)` / `add_source_line(fig, text=None)` — the two text
  furnishings every chart should carry.
- `frames_to_mp4(frame_dir, mp4_path, fps=30)` — assemble a `frame_%05d.png`
  sequence into an h264/yuv420p mp4 at 1920x1080.
- `animate_bar_build(segments, duration_s, out_dir, mp4_path=None, ...)` —
  a stacked bar that builds bottom-up, one segment at a time, values
  counting up, running total in the accent color. `segments` is a list of
  `(label, value)` pairs, e.g. the cost-stack shot:
  `[("Pulp", 0.30), ("Tariff", 0.04), ("Converter markup", 0.45), ("Retail markup", 0.31)]`.
- `animate_waterfall(total, parts, duration_s, out_dir, mp4_path=None, ...)` —
  a total (accent bar) decomposing left-to-right into labeled parts
  (secondary bars). Auto-appends a "Rounding" sliver if the parts don't sum
  exactly to `total` (`auto_rounding=True`, the default), so the chart
  always reconciles visually.
- `animate_route_map(points, stamp_at, stamp_text, duration_s, out_dir, mp4_path=None, ...)` —
  an accent-colored route line draws itself across two simplified,
  deliberately non-geographic landmass polygons (default: a rough
  Quebec/US outline baked in as `DEFAULT_ROUTE_POLYGONS` — no basemap
  dependency, no internet access needed). `points` is an ordered list of
  `(x, y, label)` nodes; a stamp (e.g. "14%") lands at `points[stamp_at]`
  once the line reaches it.
- `animate_line(series, duration_s, out_dir, mp4_path=None, ...)` — a line
  chart that draws itself left to right with a leading dot and a value
  readout tracking the tip. `series` is `(x, y)` pairs or plain y-values.

Every `animate_*` function renders its frames into a fresh `out_dir`
(existing contents are wiped first) and, if `mp4_path` is given, assembles
them via `frames_to_mp4()` and returns that path; otherwise it returns
`out_dir` so you can inspect frames or assemble later. Pass `title=` /
`source=` on any of them for the header and the bottom-left credit line.

## Rendering the demo shots

`render_demo_shots.py` renders the three CHART shots from the toilet-paper
tariff episode's shot breakdown (shots 3, 4, 14) with `[VERIFY]` placeholder
numbers, writing an mp4 + a representative PNG per shot to `tests/charts/`:

```
python3 pipeline/render_demo_shots.py
```

Rendering ~47s of animation at 30fps (~1,400 frames) took about 2.5 minutes
on this box — budget render time accordingly for a full episode's chart
shots.

## Known deviation from spec

`chart_style.py` is ~490 lines, over the "~400 lines" target in the build
brief. The overage is docstrings/usage comments and the four animation
functions' per-frame draw closures (each animate_* needs its own `draw()`
to stay readable) — no shared logic was duplicated to get there. Trim
docstrings first if a hard line cap matters more than the inline usage
examples.
