"""render_demo_shots.py — render the three CHART shots from
research note 17 (private) (shots 3, 4, 14) as a
smoke test of chart_style.py. All dollar/percent figures are [VERIFY]
placeholders per the shot breakdown — not fact-checked.

Run: python3 pipeline/render_demo_shots.py
Outputs mp4s + one representative PNG per shot into tests/charts/.
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chart_style as cs

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "tests", "charts")
os.makedirs(OUT, exist_ok=True)

SOURCE = "[VERIFY] placeholder figures — research note 17 (private)"


def snapshot(frame_dir, png_path, frac=0.95):
    """Copy a late frame from an already-rendered frame directory out as the
    shot's representative still."""
    frames = sorted(f for f in os.listdir(frame_dir) if f.endswith(".png"))
    idx = min(len(frames) - 1, int(len(frames) * frac))
    shutil.copyfile(os.path.join(frame_dir, frames[idx]), png_path)


def render_shot3_route_map():
    frame_dir = os.path.join(OUT, "shot03_frames")
    mp4_path = os.path.join(OUT, "shot03_route_map.mp4")
    png_path = os.path.join(OUT, "shot03_route_map.png")
    cs.animate_route_map(
        points=[
            (1.6, 6.8, "Quebec mill"),
            (2.7, 5.35, "Border"),
            (3.9, 3.6, "US converter"),
            (5.0, 1.4, "Retailer"),
        ],
        stamp_at=1,
        stamp_text="14%",
        duration_s=12,
        out_dir=frame_dir,
        mp4_path=mp4_path,
        title="One roll's route: Quebec mill → US shelf",
        source=SOURCE,
    )
    snapshot(frame_dir, png_path)
    shutil.rmtree(frame_dir)
    return mp4_path, png_path


def render_shot4_cost_stack():
    frame_dir = os.path.join(OUT, "shot04_frames")
    mp4_path = os.path.join(OUT, "shot04_cost_stack.mp4")
    png_path = os.path.join(OUT, "shot04_cost_stack.png")
    cs.animate_bar_build(
        segments=[
            ("Pulp", 0.30),
            ("Tariff", 0.04),
            ("Converter markup", 0.45),
            ("Retail markup", 0.31),
        ],
        duration_s=15,
        out_dir=frame_dir,
        mp4_path=mp4_path,
        title="How 14% becomes 20%-plus at the register",
        source=SOURCE,
    )
    snapshot(frame_dir, png_path)
    shutil.rmtree(frame_dir)
    return mp4_path, png_path


def render_shot14_waterfall():
    frame_dir = os.path.join(OUT, "shot14_frames")
    mp4_path = os.path.join(OUT, "shot14_waterfall.mp4")
    png_path = os.path.join(OUT, "shot14_waterfall.png")
    cs.animate_waterfall(
        total=1.10,
        parts=[
            ("Retailer", 0.25),
            ("Converter", 0.45),
            ("Mill", 0.30),
            ("Tree", 0.05),
        ],
        duration_s=20,
        out_dir=frame_dir,
        mp4_path=mp4_path,
        title="One dollar-ten, decomposed",
        source=SOURCE,
    )
    snapshot(frame_dir, png_path)
    shutil.rmtree(frame_dir)
    return mp4_path, png_path


if __name__ == "__main__":
    for label, fn in [
        ("shot 3 (route map, 12s)", render_shot3_route_map),
        ("shot 4 (cost stack, 15s)", render_shot4_cost_stack),
        ("shot 14 (waterfall, 20s)", render_shot14_waterfall),
    ]:
        mp4_path, png_path = fn()
        print(f"{label}: {mp4_path} | {png_path}")
