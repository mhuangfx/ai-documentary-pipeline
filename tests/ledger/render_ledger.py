#!/usr/bin/env python3
"""
The Ledger — three static 16:9 mockups (A: thermal receipt, B: accountant's ledger,
C: terminal ledger). Pure PIL/numpy, no GPU, no external image generation.
Palette: BG #12161f, PAPER #e8e4da, AMBER #e0a458, MUTED #5b7a8c
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, random

W, H = 1920, 1080
BG = (0x12, 0x16, 0x1f)
PAPER = (0xe8, 0xe4, 0xda)
AMBER = (0xe0, 0xa4, 0x58)
MUTED = (0x5b, 0x7a, 0x8c)
INK = (0x1a, 0x1d, 0x24)          # near-black ink for print on paper
FOUNTAIN_INK = (0x22, 0x2c, 0x3a)  # indigo-ish fountain pen ink

F_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
F_MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
F_SERIF_I = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
F_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
F_SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
F_SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
F_SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

random.seed(7)
np.random.seed(7)

TITLE = "THE TOILET PAPER TARIFF"
ITEMS = ["3 GOVERNMENTS", "1 PULP MILL", "1 TARIFF SCHEDULE"]
KEYNUM = "14%"


def font(path, size):
    return ImageFont.truetype(path, size)


def text_size(draw, txt, f):
    b = draw.textbbox((0, 0), txt, font=f)
    return b[2] - b[0], b[3] - b[1]


def letterspace(draw, xy, txt, f, fill, spacing=0, anchor_left=True):
    x, y = xy
    for ch in txt:
        draw.text((x, y), ch, font=f, fill=fill)
        w = draw.textlength(ch, font=f)
        x += w + spacing
    return x


def grain(size, amount=10, seed=0):
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, amount, size=(size[1], size[0], 1)).astype(np.int16)
    noise = np.repeat(noise, 3, axis=2)
    return noise


def apply_grain(img, amount=8, seed=0):
    arr = np.array(img).astype(np.int16)
    arr[:, :, :3] += grain(img.size, amount, seed)[:, :, :3]
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode=img.mode if img.mode != "RGBA" else "RGBA")


def vignette(img, strength=0.35):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w * 0.42, h * 0.5
    d = np.sqrt(((xx - cx) / (w * 0.75)) ** 2 + ((yy - cy) / (h * 0.75)) ** 2)
    mask = np.clip(1 - d * strength, 0.55, 1.0)
    arr = np.array(img).astype(np.float32)
    for c in range(3):
        arr[:, :, c] *= mask
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def rounded_rect(draw, box, radius, **kw):
    draw.rounded_rectangle(box, radius=radius, **kw)


# ---------------------------------------------------------------------------
# A. THERMAL RECEIPT
# ---------------------------------------------------------------------------
def render_A(path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # ambient muted glow, left of receipt
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((300, 200, 1500, 900), fill=(int(MUTED[0]*0.25), int(MUTED[1]*0.25), int(MUTED[2]*0.3)))
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    img = Image.blend(img, glow, 0.55)
    d = ImageDraw.Draw(img)

    # small persistent wordmark, top-left
    kicker_f = font(F_MONO, 22)
    letterspace(d, (90, 70), "THE LEDGER", kicker_f, MUTED, spacing=6)
    d.line((90, 108, 280, 108), fill=MUTED, width=1)

    # --- receipt geometry ---
    strip_w, strip_h = 560, 900
    rx0, ry0 = 1180, 95
    rx1, ry1 = rx0 + strip_w, ry0 + strip_h

    receipt_layer = Image.new("RGBA", (strip_w + 120, strip_h + 120), (0, 0, 0, 0))
    rd = ImageDraw.Draw(receipt_layer)

    # torn/perforated top & bottom edges (zigzag)
    def zigzag(y, up=True, teeth=26, amp=7):
        pts = []
        step = strip_w / teeth
        for i in range(teeth + 1):
            x = i * step
            yy = y + (amp if (i % 2 == 0) == up else -amp)
            pts.append((x + 60, yy))
        return pts

    top_pts = [(60, 40)] + zigzag(40, up=True) + [(strip_w + 60, 40)]
    bot_pts = [(60, strip_h + 60)] + zigzag(strip_h + 60, up=False) + [(strip_w + 60, strip_h + 60)]
    body = top_pts + [(strip_w + 60, strip_h + 60)] + list(reversed(bot_pts))[1:-1] + [(60, strip_h + 60)]

    # simple paper polygon: top zigzag, straight sides, bottom zigzag
    poly = zigzag(40, up=True, teeth=26, amp=6)
    poly += [(strip_w + 60, strip_h + 60)]
    poly += list(reversed(zigzag(strip_h + 60, up=False, teeth=26, amp=6)))
    poly += [(60, 40)]
    rd.polygon(poly, fill=PAPER + (255,))

    # subtle vertical shading for curl (darker at far edges)
    shade = Image.new("L", receipt_layer.size, 0)
    sd = ImageDraw.Draw(shade)
    for i in range(strip_w):
        t = i / strip_w
        curl = int(26 * (abs(t - 0.5) * 2) ** 2)
        sd.line((60 + i, 40, 60 + i, strip_h + 60), fill=curl)
    shaded = Image.new("RGBA", receipt_layer.size, (18, 20, 26, 255))
    receipt_layer = Image.composite(shaded, receipt_layer, shade)
    # re-punch the paper shape as alpha mask so shading only affects paper
    mask = Image.new("L", receipt_layer.size, 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    paper_only = Image.new("RGBA", receipt_layer.size, (0, 0, 0, 0))
    paper_only.paste(receipt_layer, (0, 0), mask)
    receipt_layer = paper_only

    # thermal dot-matrix grain (subtle) restricted to paper mask
    rgba = np.array(receipt_layer)
    noise = np.random.default_rng(3).normal(0, 6, size=rgba.shape[:2])
    for c in range(3):
        chan = rgba[:, :, c].astype(np.int16)
        chan += noise.astype(np.int16)
        rgba[:, :, c] = np.clip(chan, 0, 255)
    receipt_layer = Image.fromarray(rgba, "RGBA")
    rd = ImageDraw.Draw(receipt_layer)

    # drop shadow (paste a blurred dark copy behind, offset)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow_shape = Image.new("RGBA", receipt_layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow_shape).polygon(poly, fill=(0, 0, 0, 160))
    shadow.paste(shadow_shape, (rx0 - 60 + 22, ry0 - 40 + 28), shadow_shape)
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    img = Image.alpha_composite(img.convert("RGBA"), shadow)
    img.paste(receipt_layer, (rx0 - 60, ry0 - 40), receipt_layer)
    d = ImageDraw.Draw(img)

    # --- receipt content ---
    pad_x = rx0 + 46
    y = ry0 + 40

    small_caps = font(F_MONO_B, 20)
    letterspace(d, (pad_x, y), "THE LEDGER · EP.01", small_caps, INK, spacing=3)
    y += 34
    d.line((pad_x, y, rx1 - 40, y), fill=INK, width=1)
    y += 22

    title_f = font(F_MONO_B, 30)
    words = TITLE.split()
    line1, line2 = "THE TOILET", "PAPER TARIFF"
    d.text((pad_x, y), line1, font=title_f, fill=INK)
    y += 38
    d.text((pad_x, y), line2, font=title_f, fill=INK)
    y += 52

    dash_f = font(F_MONO, 20)
    d.text((pad_x, y), "-" * 34, font=dash_f, fill=INK)
    y += 40

    item_f = font(F_MONO, 26)
    for it in ITEMS:
        qty, label = it.split(" ", 1)
        d.text((pad_x, y), qty, font=font(F_MONO_B, 26), fill=INK)
        d.text((pad_x + 46, y), label, font=item_f, fill=INK)
        y += 40
    y += 6
    d.text((pad_x, y), "-" * 34, font=dash_f, fill=INK)
    y += 44

    cap_f = font(F_MONO, 18)
    letterspace(d, (pad_x, y), "RECOVERED THROUGH PRICING", cap_f, INK, spacing=1)
    y += 36

    # amber stamp box, slight rotation
    stamp = Image.new("RGBA", (300, 150), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(stamp)
    sdraw.rounded_rectangle((6, 6, 294, 144), radius=10, outline=AMBER, width=6)
    num_f = font(F_MONO_B, 62)
    tw, th = text_size(sdraw, KEYNUM, num_f)
    sdraw.text(((300 - tw) / 2, (150 - th) / 2 - 18), KEYNUM, font=num_f, fill=AMBER)
    small_f = font(F_MONO_B, 16)
    letterspace(sdraw, (60, 104), "TARIFF RATE", small_f, AMBER, spacing=3)
    stamp = stamp.rotate(-4, expand=True, resample=Image.BICUBIC)
    img.paste(stamp, (pad_x - 10, y - 4), stamp)
    y += stamp.size[1] + 10

    # decorative barcode near bottom of receipt
    bcy = ry0 + strip_h - 70
    bx = pad_x
    rngb = random.Random(11)
    for i in range(60):
        bw = rngb.choice([2, 2, 3, 5])
        bh = rngb.choice([26, 34, 40])
        d.rectangle((bx, bcy, bx + bw, bcy + bh), fill=INK)
        bx += bw + rngb.choice([3, 4, 6])
        if bx > rx1 - 60:
            break

    img = img.convert("RGB")
    img = apply_grain(img, amount=3, seed=1)
    img.save(path)
    print("saved", path)


# ---------------------------------------------------------------------------
# B. ACCOUNTANT'S LEDGER
# ---------------------------------------------------------------------------
def render_B(path):
    img = Image.new("RGB", (W, H), BG)

    # desk vignette
    img = vignette(img, strength=0.28)
    d = ImageDraw.Draw(img)

    kicker_f = font(F_SERIF, 22)
    letterspace(d, (80, 60), "THE LEDGER", kicker_f, MUTED, spacing=6)
    d.line((80, 96, 260, 96), fill=MUTED, width=1)

    # book geometry
    bx0, by0, bx1, by1 = 260, 150, 1660, 980
    book_w, book_h = bx1 - bx0, by1 - by0
    gutter = bx0 + book_w // 2

    book = Image.new("RGBA", (book_w + 80, book_h + 80), (0, 0, 0, 0))
    bd = ImageDraw.Draw(book)
    page_poly = (40, 40, book_w + 40, book_h + 40)
    bd.rectangle(page_poly, fill=PAPER + (255,))

    # foxing / aging - random soft darker blobs near edges
    fox = Image.new("L", book.size, 0)
    fd = ImageDraw.Draw(fox)
    rngf = random.Random(5)
    for _ in range(24):
        ex = rngf.choice([rngf.randint(0, 60), rngf.randint(book_w - 20, book_w + 40)])
        ey = rngf.randint(0, book_h + 40)
        r = rngf.randint(8, 26)
        fd.ellipse((ex - r, ey - r, ex + r, ey + r), fill=rngf.randint(20, 45))
    fox = fox.filter(ImageFilter.GaussianBlur(10))
    aged = Image.new("RGBA", book.size, (0xc9, 0xb8, 0x8f, 255))
    book = Image.composite(aged, book, fox)
    bd = ImageDraw.Draw(book)

    # re-apply page rectangle mask so aging doesn't spill outside
    mask = Image.new("L", book.size, 0)
    ImageDraw.Draw(mask).rectangle(page_poly, fill=255)
    tmp = Image.new("RGBA", book.size, (0, 0, 0, 0))
    tmp.paste(book, (0, 0), mask)
    book = tmp
    bd = ImageDraw.Draw(book)

    # hand-ruled horizontal lines with slight wobble
    rngw = np.random.default_rng(9)
    n_lines = 16
    line_gap = (book_h - 120) / n_lines
    for i in range(n_lines + 1):
        base_y = 40 + 100 + i * line_gap
        xs = np.linspace(40, book_w + 40, 40)
        ys = base_y + np.cumsum(rngw.normal(0, 0.3, size=xs.shape))
        ys -= ys.mean() - base_y
        pts = list(zip(xs.tolist(), ys.tolist()))
        bd.line(pts, fill=(0x8a, 0x7f, 0x66), width=1)

    # center gutter shadow (binding)
    gutter_local = gutter - bx0 + 40
    grad_w = 46
    for i in range(grad_w):
        alpha = int(90 * (1 - abs(i - grad_w / 2) / (grad_w / 2)))
        bd.line((gutter_local - grad_w // 2 + i, 40, gutter_local - grad_w // 2 + i, book_h + 40),
                fill=(0, 0, 0, alpha))

    # column divider on each page (date | description | amount style header)
    header_f = font(F_SERIF_I, 20)
    for side_x0 in (40 + 30, gutter_local + 30):
        letterspace(bd, (side_x0, 60), "DATE      DESCRIPTION                     AMOUNT",
                    font(F_SERIF_I, 16), FOUNTAIN_INK, spacing=0)

    img = img.convert("RGBA")
    img.paste(book, (bx0 - 40, by0 - 40), book)
    img = img.convert("RGB")
    d = ImageDraw.Draw(img)

    # --- handwritten-style content, left page ---
    lx = bx0 + 40
    ty = by0 + 110

    title_f = font(F_SERIF_B, 34)
    d.text((lx, ty), "The Toilet Paper Tariff", font=title_f, fill=FOUNTAIN_INK)
    ty += 50
    und_w = d.textlength("The Toilet Paper Tariff", font=title_f)
    d.line((lx, ty - 12, lx + und_w, ty - 12), fill=FOUNTAIN_INK, width=2)
    ty += 20

    item_f = font(F_SERIF_I, 27)
    for it in ITEMS:
        qty, label = it.split(" ", 1)
        line = f"{qty}   {label.title()}"
        d.text((lx, ty), line, font=item_f, fill=FOUNTAIN_INK)
        # right-aligned ditto-style running notation on the same page
        d.text((gutter - 90, ty), "· · ·", font=item_f, fill=FOUNTAIN_INK)
        ty += line_gap

    ty += 10
    d.line((lx, ty, gutter - 40, ty), fill=FOUNTAIN_INK, width=1)
    ty += 20
    letterspace(d, (lx, ty), "BALANCE CARRIED FORWARD", font(F_SERIF_I, 18), FOUNTAIN_INK, spacing=1)

    # --- right page: tally + stamp ---
    rx = gutter + 60
    ry = by0 + 110
    tally_f = font(F_MONO, 24)
    vals = ["3", "1", "1"]
    for v in vals:
        d.text((rx, ry), v, font=tally_f, fill=FOUNTAIN_INK)
        ry += line_gap
    ry += 6
    d.line((rx, ry, bx1 - 60, ry), fill=FOUNTAIN_INK, width=1)
    ry += 16
    d.text((rx, ry), "14", font=font(F_MONO_B, 24), fill=FOUNTAIN_INK)
    d.text((rx + 40, ry), "% pass-through", font=font(F_SERIF_I, 22), fill=FOUNTAIN_INK)

    # grunge amber ink stamp, bottom right of right page
    stamp_d = 260
    stamp = Image.new("RGBA", (stamp_d, stamp_d), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    cx, cy, r = stamp_d / 2, stamp_d / 2, stamp_d / 2 - 14
    rngs = random.Random(21)
    steps = 240
    pts = []
    for i in range(steps):
        a = 2 * math.pi * i / steps
        rr = r + rngs.uniform(-4, 4)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    for i in range(steps):
        if rngs.random() < 0.08:
            continue
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % steps]
        w = rngs.choice([3, 4, 5])
        sd.line((x0, y0, x1, y1), fill=AMBER, width=w)
    num_f = font(F_SERIF_B, 60)
    tw, th = text_size(sd, KEYNUM, num_f)
    sd.text(((stamp_d - tw) / 2, (stamp_d - th) / 2 - 22), KEYNUM, font=num_f, fill=AMBER)
    cap_f = font(F_SERIF_B, 15)
    letterspace(sd, (cx - 68, cy + 40), "RECOVERED", cap_f, AMBER, spacing=3)
    stamp = stamp.rotate(12, expand=True, resample=Image.BICUBIC)
    img.paste(stamp, (bx1 - stamp.size[0] - 40, by1 - stamp.size[1] - 30), stamp)

    img = apply_grain(img, amount=3, seed=2)
    img.save(path)
    print("saved", path)


# ---------------------------------------------------------------------------
# C. TERMINAL LEDGER
# ---------------------------------------------------------------------------
def render_C(path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    margin = 160
    top = 330
    rule_col = (0xe8, 0xe4, 0xda, 255)

    # kicker
    kicker_f = font(F_MONO, 22)
    letterspace(d, (margin, 200), "THE LEDGER", kicker_f, AMBER, spacing=8)
    d.line((margin, 238, margin + 220, 238), fill=AMBER, width=2)

    # episode tag, right-aligned
    tag_f = font(F_MONO, 20)
    tag = "EP.01 / RUN 03:12"
    tw = d.textlength(tag, font=tag_f)
    letterspace(d, (W - margin - tw, 208), tag, tag_f, MUTED, spacing=2)

    # top rule
    d.line((margin, top, W - margin, top), fill=PAPER, width=2)

    # title
    title_f = font(F_SANS_B, 64)
    d.text((margin, top + 40), TITLE, font=title_f, fill=PAPER)

    # sub-rule
    y2 = top + 150
    d.line((margin, y2, W - margin, y2), fill=(0x3a, 0x40, 0x4e), width=1)

    # line items row, tabular, separated by thin vertical rules
    row_y = y2 + 60
    col_w = (W - 2 * margin) / 3
    num_f = font(F_MONO_B, 46)
    label_f = font(F_MONO, 22)
    for i, it in enumerate(ITEMS):
        qty, label = it.split(" ", 1)
        cx0 = margin + i * col_w
        d.text((cx0, row_y), qty, font=num_f, fill=AMBER)
        qw = d.textlength(qty, font=num_f)
        letterspace(d, (cx0, row_y + 62), label, label_f, PAPER, spacing=1)
        if i < 2:
            vx = cx0 + col_w - 40
            d.line((vx, row_y - 4, vx, row_y + 96), fill=(0x3a, 0x40, 0x4e), width=1)

    # bottom rule
    y3 = row_y + 150
    d.line((margin, y3, W - margin, y3), fill=(0x3a, 0x40, 0x4e), width=1)

    # caption above stamp
    cap_f = font(F_MONO, 20)
    letterspace(d, (margin, y3 + 34), "RECOVERED THROUGH PRICING", cap_f, MUTED, spacing=2)

    # amber badge/stamp — crisp UI-badge-meets-rubber-stamp
    badge_w, badge_h = 300, 150
    badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(badge)
    bdraw.rounded_rectangle((0, 0, badge_w - 1, badge_h - 1), radius=18, fill=AMBER)
    inset = 10
    bdraw.rounded_rectangle((inset, inset, badge_w - 1 - inset, badge_h - 1 - inset),
                             radius=12, outline=(0x8a, 0x5a, 0x22), width=3)
    num_f2 = font(F_SANS_B, 66)
    tw, th = text_size(bdraw, KEYNUM, num_f2)
    bdraw.text(((badge_w - tw) / 2, (badge_h - th) / 2 - 22), KEYNUM, font=num_f2, fill=BG)
    small_f = font(F_MONO_B, 16)
    letterspace(bdraw, (badge_w/2 - 58, badge_h - 34), "TARIFF RATE", small_f, BG, spacing=2)
    badge = badge.rotate(-3, expand=True, resample=Image.BICUBIC)
    img.paste(badge, (margin, y3 + 70), badge)

    # footer rule + wordmark, balances composition at bottom of frame
    y4 = y3 + 70 + badge.size[1] + 60
    d.line((margin, y4, W - margin, y4), fill=(0x3a, 0x40, 0x4e), width=1)
    foot_f = font(F_MONO, 18)
    letterspace(d, (margin, y4 + 24), "THE LEDGER — SIGNATURE OPEN", foot_f, (0x3a, 0x40, 0x4e), spacing=2)

    img.save(path)
    print("saved", path)


if __name__ == "__main__":
    import os
    outdir = os.path.dirname(os.path.abspath(__file__))
    render_A(os.path.join(outdir, "A_thermal_receipt.png"))
    render_B(os.path.join(outdir, "B_accountants_ledger.png"))
    render_C(os.path.join(outdir, "C_terminal_ledger.png"))
