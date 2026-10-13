"""chart_style.py — house chart style + animation helpers for the long-form
economics explainer channel.

Renders 16:9 1920x1080 matplotlib charts in the channel's house style (very
dark blue-gray background, off-white text, one amber accent color, one muted
blue-gray secondary color, no gridlines, generous margins, a bottom-left
source line on every chart) as PNG frame sequences, and optionally assembles
each sequence into an mp4 with ffmpeg at 30 fps. No GPU, no display server
required (matplotlib's Agg backend).

House style at a glance
------------------------
    BG_COLOR        very dark blue-gray, "#12161f"
    TEXT_COLOR      off-white, "#e8e4da"
    ACCENT_COLOR    amber, "#e0a458"   — the ONE accent: headline numbers,
                                         the moving/answer element
    SECONDARY_COLOR muted blue-gray, "#5b7a8c" — everything else that needs
                                         a fill (bars, route lines' land
                                         shapes, baselines)
    FONT_FAMILY     "DejaVu Sans" (a single constant — change it in one
                                    place to re-skin every chart)

Usage
-----
    from chart_style import animate_bar_build, animate_waterfall, \
        animate_route_map, animate_line, still, new_figure

    animate_bar_build(
        segments=[("Pulp", 0.30), ("Tariff", 0.04),
                  ("Converter markup", 0.45), ("Retail markup", 0.31)],
        duration_s=15,
        out_dir="tests/charts/shot04_frames",
        mp4_path="tests/charts/shot04_cost_stack.mp4",
        title="Where the 14% tariff ends up",
        source="[VERIFY] figures — placeholder, not fact-checked",
    )

Every animate_* function renders its frame sequence into `out_dir` (created
fresh each call) and, if `mp4_path` is given, assembles it into an mp4 via
ffmpeg and returns that path; otherwise it returns `out_dir`. `still()`
renders one already-built figure to a single PNG for a representative frame.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# House style constants
# ---------------------------------------------------------------------------

WIDTH_PX = 1920
HEIGHT_PX = 1080
DPI = 120
FIGSIZE = (WIDTH_PX / DPI, HEIGHT_PX / DPI)  # inches, 16:9

BG_COLOR = "#12161f"
TEXT_COLOR = "#e8e4da"
ACCENT_COLOR = "#e0a458"
SECONDARY_COLOR = "#5b7a8c"
MUTED_TEXT_COLOR = "#9aa3ad"

FONT_FAMILY = "DejaVu Sans"
FPS = 30
DEFAULT_SOURCE = "[VERIFY] — figures unverified, placeholder for review"

plt.rcParams["font.family"] = FONT_FAMILY
plt.rcParams["savefig.facecolor"] = BG_COLOR
plt.rcParams["figure.facecolor"] = BG_COLOR


# ---------------------------------------------------------------------------
# Base figure / style helpers
# ---------------------------------------------------------------------------

def new_figure():
    """Return (fig, ax) at 1920x1080 in house style: dark background, no
    gridlines, no spines, generous margins, tick text in the text color."""
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=TEXT_COLOR, labelsize=13)
    fig.subplots_adjust(left=0.10, right=0.92, top=0.86, bottom=0.14)
    return fig, ax


def add_title(fig, text: str) -> None:
    fig.suptitle(text, fontsize=22, color=TEXT_COLOR, family=FONT_FAMILY,
                 fontweight="bold", x=0.08, ha="left", y=0.97)


def add_source_line(fig, text: str | None = None) -> None:
    """Small source/citation line, bottom-left. Every chart carries one."""
    fig.text(0.03, 0.03, text or DEFAULT_SOURCE, fontsize=11,
              color=MUTED_TEXT_COLOR, family=FONT_FAMILY, ha="left",
              va="bottom", alpha=0.85)


def still(fig, path: str) -> str:
    """Save an already-built figure to `path` as a single PNG frame and
    close it. Use for a representative still of any animation, or a
    one-off static chart."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    fig.savefig(path, facecolor=BG_COLOR)
    plt.close(fig)
    return path


def ease_out_cubic(t: float) -> float:
    """Standard ease-out easing for animation progress in [0, 1]."""
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


# ---------------------------------------------------------------------------
# frame sequence -> mp4
# ---------------------------------------------------------------------------

def _fresh_dir(out_dir: str) -> None:
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)


def frames_to_mp4(frame_dir: str, mp4_path: str, fps: int = FPS) -> str:
    """Assemble frame_00000.png, frame_00001.png, ... in `frame_dir` into an
    mp4 at `mp4_path` via ffmpeg (H.264, yuv420p, locked to 1920x1080)."""
    os.makedirs(os.path.dirname(os.path.abspath(mp4_path)) or ".", exist_ok=True)
    pattern = os.path.join(frame_dir, "frame_%05d.png")
    cmd = [
        "ffmpeg", "-y", "-framerate", str(fps), "-i", pattern,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-vf", f"scale={WIDTH_PX}:{HEIGHT_PX}",
        mp4_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return mp4_path


# ---------------------------------------------------------------------------
# animate_bar_build — stacked bar that builds segment by segment
# ---------------------------------------------------------------------------

def animate_bar_build(segments, duration_s, out_dir, mp4_path=None, fps=FPS,
                       title=None, source=None, currency="$", value_fmt="{:.2f}"):
    """Stacked bar that builds bottom-up, one segment at a time, with each
    segment's value counting up as it fills and the running total displayed
    above the bar in the accent color.

    segments: sequence of (label, value), e.g.
        [("Pulp", 0.30), ("Tariff", 0.04),
         ("Converter markup", 0.45), ("Retail markup", 0.31)]

    Returns the mp4 path if `mp4_path` is given, else the frame directory.
    """
    segments = list(segments)
    n = len(segments)
    total = sum(v for _, v in segments)
    n_frames = max(2, round(duration_s * fps))
    hold_frames = max(1, round(n_frames * 0.15))
    build_frames = n_frames - hold_frames
    frames_per_seg = max(1, build_frames // n)

    _fresh_dir(out_dir)
    ymax = total * 1.35

    def draw(seg_progress, frame_path):
        fig, ax = new_figure()
        ax.set_xlim(-1, 1.6)
        ax.set_ylim(0, ymax)
        ax.set_xticks([])
        ax.set_yticks([])
        bottom = 0.0
        running_total = 0.0
        for i, (label, value) in enumerate(segments):
            p = seg_progress[i]
            h = value * p
            alpha = 0.45 + 0.55 * (i + 1) / n
            ax.bar(0, h, bottom=bottom, width=0.6, color=SECONDARY_COLOR,
                   alpha=alpha, edgecolor=BG_COLOR, linewidth=2)
            if p > 0.02:
                ax.text(0.38, bottom + h / 2,
                        f"{label}\n{currency}{value_fmt.format(value * p)}",
                        color=TEXT_COLOR, fontsize=14, va="center", ha="left",
                        family=FONT_FAMILY)
            bottom += value
            running_total += value * p
        ax.text(0, ymax * 0.97, f"{currency}{value_fmt.format(running_total)}",
                color=ACCENT_COLOR, fontsize=34, fontweight="bold",
                va="top", ha="center", family=FONT_FAMILY)
        if title:
            add_title(fig, title)
        add_source_line(fig, source)
        still(fig, frame_path)

    frame_i = 0
    for i in range(n):
        for f in range(frames_per_seg):
            p = ease_out_cubic((f + 1) / frames_per_seg)
            seg_progress = [1.0] * i + [p] + [0.0] * (n - i - 1)
            draw(seg_progress, os.path.join(out_dir, f"frame_{frame_i:05d}.png"))
            frame_i += 1
    for _ in range(n_frames - frame_i):
        draw([1.0] * n, os.path.join(out_dir, f"frame_{frame_i:05d}.png"))
        frame_i += 1

    return frames_to_mp4(out_dir, mp4_path, fps) if mp4_path else out_dir


# ---------------------------------------------------------------------------
# animate_waterfall — a total decomposing into labeled parts
# ---------------------------------------------------------------------------

def animate_waterfall(total, parts, duration_s, out_dir, mp4_path=None, fps=FPS,
                       title=None, source=None, currency="$", value_fmt="{:.2f}",
                       auto_rounding=True, total_label="Shelf price"):
    """Waterfall chart: a total bar (accent color) with labeled part bars
    (secondary color) stepping down from it left to right, each part's value
    counting up as it reveals. If `auto_rounding` and the parts don't sum
    exactly to `total`, a trailing "Rounding" sliver is appended so the
    chart always reconciles.

    parts: sequence of (label, value) that should sum to about `total`.
    """
    parts = list(parts)
    if auto_rounding:
        residual = total - sum(v for _, v in parts)
        if abs(residual) > 0.005:
            parts.append(("Rounding", residual))

    n = len(parts)
    n_frames = max(2, round(duration_s * fps))
    hold_frames = max(1, round(n_frames * 0.15))
    build_frames = n_frames - hold_frames
    steps = n + 1  # step 0 reveals the total bar; steps 1..n reveal parts
    frames_per_step = max(1, build_frames // steps)

    _fresh_dir(out_dir)
    ymax = total * 1.25
    remaining_after = [total]
    r = total
    for _, v in parts:
        r -= v
        remaining_after.append(r)

    def draw(step, sub_progress, frame_path):
        fig, ax = new_figure()
        ax.set_xlim(-0.8, n + 0.8)
        ax.set_ylim(-ymax * 0.12, ymax)
        ax.set_xticks([])
        ax.set_yticks([])
        total_p = sub_progress if step == 0 else 1.0
        ax.bar(0, total * total_p, width=0.6, color=ACCENT_COLOR,
               edgecolor=BG_COLOR, linewidth=2)
        ax.text(0, total * total_p + ymax * 0.02,
                f"{currency}{value_fmt.format(total * total_p)}",
                color=ACCENT_COLOR, fontsize=16, fontweight="bold",
                ha="center", va="bottom", family=FONT_FAMILY)
        ax.text(0, -ymax * 0.07, total_label, color=TEXT_COLOR, fontsize=13,
                ha="center", family=FONT_FAMILY)

        target = step - 1  # index of the part currently animating
        for i, (label, value) in enumerate(parts):
            if i < target:
                p = 1.0
            elif i == target:
                p = sub_progress
            else:
                p = 0.0
            if p <= 0:
                continue
            x = i + 1
            top = remaining_after[i]
            bot = top - value * p
            lo, hi = (bot, top) if value >= 0 else (top, bot)
            ax.bar(x, hi - lo, bottom=lo, width=0.6, color=SECONDARY_COLOR,
                   edgecolor=BG_COLOR, linewidth=2)
            ax.text(x, hi + ymax * 0.02,
                    f"{currency}{value_fmt.format(abs(value * p))}",
                    color=TEXT_COLOR, fontsize=15, fontweight="bold",
                    ha="center", va="bottom", family=FONT_FAMILY)
            ax.text(x, -ymax * 0.07, label, color=TEXT_COLOR, fontsize=13,
                    ha="center", family=FONT_FAMILY)
        if title:
            add_title(fig, title)
        add_source_line(fig, source)
        still(fig, frame_path)

    frame_i = 0
    for step in range(steps):
        for f in range(frames_per_step):
            p = ease_out_cubic((f + 1) / frames_per_step)
            draw(step, p, os.path.join(out_dir, f"frame_{frame_i:05d}.png"))
            frame_i += 1
    for _ in range(n_frames - frame_i):
        draw(steps, 1.0, os.path.join(out_dir, f"frame_{frame_i:05d}.png"))
        frame_i += 1

    return frames_to_mp4(out_dir, mp4_path, fps) if mp4_path else out_dir


# ---------------------------------------------------------------------------
# animate_route_map — a route line drawn across a minimal illustrated map
# ---------------------------------------------------------------------------

# A rough, deliberately non-geographic Quebec / US shape pair. Not for
# accuracy — for a consistent illustrated-map "look" per the house style
# (see research note 15 (private): pick one map style, never mix).
DEFAULT_ROUTE_POLYGONS = {
    "quebec": [(0.5, 6.4), (1.2, 7.6), (2.8, 8.0), (4.5, 7.5), (5.6, 6.6),
               (5.0, 5.6), (3.2, 5.3), (1.3, 5.5)],
    "us": [(0.2, 5.4), (2.0, 5.2), (4.0, 5.0), (6.0, 4.6), (6.2, 2.5),
           (4.5, 0.8), (2.0, 0.6), (0.3, 1.8), (0.0, 3.8)],
}


def animate_route_map(points, stamp_at, stamp_text, duration_s, out_dir,
                       mp4_path=None, fps=FPS, title=None, source=None,
                       polygons=None, region_labels=(("QUEBEC", 0.6, 7.2),
                                                      ("UNITED STATES", 0.6, 1.0))):
    """A stylized route line draws itself across two hand-drawn landmass
    shapes (default: a rough Quebec / US outline, no basemap dependency),
    passing through `points`, with a stamp graphic landing at one node.

    points: ordered list of (x, y, label) route nodes, e.g.
        [(1.8, 6.6, "Quebec mill"), (2.6, 5.3, "Border"),
         (3.6, 3.8, "US converter"), (4.8, 1.6, "Retailer")]
    stamp_at: index into `points` where the stamp lands.
    stamp_text: e.g. "14%".
    """
    polygons = polygons or DEFAULT_ROUTE_POLYGONS
    n_frames = max(2, round(duration_s * fps))
    line_frames = max(1, round(n_frames * 0.6))
    stamp_frames = max(1, round(n_frames * 0.15))

    _fresh_dir(out_dir)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    seg_len = [float(np.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i]))
               for i in range(len(points) - 1)]
    total_len = sum(seg_len) or 1.0
    cum_len = np.cumsum([0.0] + seg_len)

    def point_at(frac):
        target = frac * total_len
        for i in range(len(seg_len)):
            if target <= cum_len[i + 1] or i == len(seg_len) - 1:
                span = seg_len[i] or 1.0
                t = min(max((target - cum_len[i]) / span, 0.0), 1.0)
                return xs[i] + t * (xs[i + 1] - xs[i]), ys[i] + t * (ys[i + 1] - ys[i])
        return xs[-1], ys[-1]

    def draw(frac, stamp_scale, frame_path):
        fig, ax = new_figure()
        ax.set_xlim(-0.5, 7)
        ax.set_ylim(-0.5, 8.5)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        for poly in polygons.values():
            ax.add_patch(plt.Polygon(poly, closed=True, facecolor=SECONDARY_COLOR,
                                      alpha=0.28, edgecolor=SECONDARY_COLOR, linewidth=1.5))
        for label, lx, ly in region_labels:
            ax.text(lx, ly, label, color=TEXT_COLOR, fontsize=13, alpha=0.7,
                    family=FONT_FAMILY)

        traced_x, traced_y, acc = [xs[0]], [ys[0]], 0.0
        target_len = frac * total_len
        for i in range(len(seg_len)):
            if acc + seg_len[i] <= target_len:
                traced_x.append(xs[i + 1]); traced_y.append(ys[i + 1])
                acc += seg_len[i]
            else:
                hx, hy = point_at(frac)
                traced_x.append(hx); traced_y.append(hy)
                break
        ax.plot(traced_x, traced_y, color=ACCENT_COLOR, linewidth=3.5,
                solid_capstyle="round")
        hx, hy = point_at(frac)
        ax.plot([hx], [hy], marker="o", color=ACCENT_COLOR, markersize=9)

        for i, (px, py, label) in enumerate(points):
            node_frac = cum_len[i] / total_len
            if frac >= node_frac - 1e-6:
                ax.plot([px], [py], marker="o", color=TEXT_COLOR, markersize=6, zorder=5)
                ax.text(px, py - 0.35, label, color=TEXT_COLOR, fontsize=12,
                        ha="center", family=FONT_FAMILY)

        if stamp_scale > 0:
            sx, sy, _ = points[stamp_at]
            ax.text(sx + 0.75, sy + 0.35, stamp_text, color=ACCENT_COLOR,
                    fontsize=max(1, 30 * stamp_scale), fontweight="bold",
                    ha="center", va="center", family=FONT_FAMILY, rotation=-12,
                    alpha=min(1.0, stamp_scale),
                    bbox=dict(boxstyle="round,pad=0.35", facecolor=BG_COLOR,
                              edgecolor=ACCENT_COLOR, linewidth=2.5,
                              alpha=min(1.0, stamp_scale)))
        if title:
            add_title(fig, title)
        add_source_line(fig, source)
        still(fig, frame_path)

    frame_i = 0
    for f in range(line_frames):
        frac = ease_out_cubic((f + 1) / line_frames)
        draw(frac, 0.0, os.path.join(out_dir, f"frame_{frame_i:05d}.png"))
        frame_i += 1
    for f in range(stamp_frames):
        scale = ease_out_cubic((f + 1) / stamp_frames)
        draw(1.0, scale, os.path.join(out_dir, f"frame_{frame_i:05d}.png"))
        frame_i += 1
    for _ in range(n_frames - frame_i):
        draw(1.0, 1.0, os.path.join(out_dir, f"frame_{frame_i:05d}.png"))
        frame_i += 1

    return frames_to_mp4(out_dir, mp4_path, fps) if mp4_path else out_dir


# ---------------------------------------------------------------------------
# animate_line — a line chart that draws itself left to right
# ---------------------------------------------------------------------------

def animate_line(series, duration_s, out_dir, mp4_path=None, fps=FPS,
                  title=None, source=None, y_label=None, x_tick_labels=None,
                  value_fmt="{:,.2f}"):
    """Line chart that draws itself left to right, with a leading dot and a
    value readout that follows the line's tip.

    series: sequence of (x, y) pairs, or plain y-values (x becomes 0..n-1).
    """
    series = list(series)
    if series and not isinstance(series[0], (tuple, list)):
        series = list(enumerate(series))
    xs = [p[0] for p in series]
    ys = [p[1] for p in series]
    n_frames = max(2, round(duration_s * fps))
    draw_frames = max(1, round(n_frames * 0.85))

    _fresh_dir(out_dir)
    ymin, ymax = min(ys), max(ys)
    pad = (ymax - ymin) * 0.25 or max(abs(ymax), 1.0) * 0.25

    def draw(frac, frame_path):
        fig, ax = new_figure()
        ax.set_xlim(min(xs), max(xs))
        ax.set_ylim(ymin - pad, ymax + pad)
        ax.axhline(ymin - pad * 0.4, color=SECONDARY_COLOR, linewidth=1.2, alpha=0.5)
        if x_tick_labels:
            ax.set_xticks(xs)
            ax.set_xticklabels(x_tick_labels, color=TEXT_COLOR, fontsize=12)
        else:
            ax.set_xticks([])
        ax.set_yticks([])
        n_show = max(2, int(round(frac * (len(xs) - 1))) + 1)
        ax.plot(xs[:n_show], ys[:n_show], color=ACCENT_COLOR, linewidth=3)
        ax.plot([xs[n_show - 1]], [ys[n_show - 1]], marker="o",
                color=ACCENT_COLOR, markersize=9)
        ax.text(xs[n_show - 1], ys[n_show - 1] + pad * 0.15,
                value_fmt.format(ys[n_show - 1]), color=TEXT_COLOR,
                fontsize=14, ha="center", family=FONT_FAMILY)
        if y_label:
            ax.text(min(xs), ymax + pad * 0.9, y_label, color=TEXT_COLOR,
                    fontsize=14, family=FONT_FAMILY)
        if title:
            add_title(fig, title)
        add_source_line(fig, source)
        still(fig, frame_path)

    frame_i = 0
    for f in range(draw_frames):
        frac = ease_out_cubic((f + 1) / draw_frames)
        draw(frac, os.path.join(out_dir, f"frame_{frame_i:05d}.png"))
        frame_i += 1
    for _ in range(n_frames - frame_i):
        draw(1.0, os.path.join(out_dir, f"frame_{frame_i:05d}.png"))
        frame_i += 1

    return frames_to_mp4(out_dir, mp4_path, fps) if mp4_path else out_dir
