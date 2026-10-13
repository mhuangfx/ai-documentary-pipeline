"""House-style animated chart cards (CPU, matplotlib -> ffmpeg). 1920x1080, 24 fps, dark background.
Colour = forecaster, consistent on every card: panel=cyan, switch-over team=amber, trial forecast=green, real Sun=white/red."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np, subprocess, os, math
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch, Wedge, Polygon, FancyArrowPatch

BG = '#0a0f1e'; FG = '#f2f4f8'; DIM = '#8a93a8'; GRID = '#222b45'
PANEL = '#4cc9f0'; TEAM = '#ffb000'; TRIAL = '#6fd08c'; ACT = '#ff5964'; WHITE = '#ffffff'; SUN = '#ff9f1c'
FPS = 24
W, H = 192, 108
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def ease(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def seg(p, a, b):
    return ease((p - a) / (b - a)) if b > a else (1.0 if p >= a else 0.0)


def load_ssn():
    def rd(fn, col):
        out = []
        for ln in open(os.path.join(DATA, fn)):
            f = ln.split()
            if len(f) < 4: continue
            v = float(f[col])
            if v >= 0: out.append((float(f[2]), v))
        return np.array(out)
    return rd('SN_m_tot_V2.0.txt', 3), rd('SN_ms_tot_V2.0.txt', 3)


def new_ax():
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off'); ax.set_facecolor(BG)
    return fig, ax


def T(ax, x, y, s, size=30, color=FG, ha='center', va='center', alpha=1.0, weight='normal', **kw):
    if alpha <= 0.01: return None
    return ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, alpha=alpha, fontweight=weight, family='DejaVu Sans', **kw)


def chrome(ax, s, p):
    if s.get('kicker'): T(ax, 9, 100, s['kicker'].upper(), 24, DIM, ha='left', alpha=seg(p, 0, .1), weight='bold')
    if s.get('caption'): T(ax, W / 2, 8, s['caption'], 28, DIM, alpha=seg(p, .7, .95))
    if s.get('title'): T(ax, W / 2, 93, s['title'], 44, FG, alpha=seg(p, 0, .15), weight='bold')


# ---------------- templates ----------------
def t_text(ax, s, p):
    L = s['lines']; n = len(L); gap = s.get('gap', 16); y0 = s.get('y', 54) + (n - 1) / 2 * gap
    for i, l in enumerate(L):
        a = seg(p, 0.05 + 0.7 * i / max(n, 1), 0.05 + 0.7 * i / max(n, 1) + .2)
        T(ax, l.get('x', W / 2), y0 - i * gap + (1 - a) * -2, l['t'], l.get('size', 46), l.get('color', FG), alpha=a, weight=l.get('weight', 'bold' if i == 0 else 'normal'))


def t_bars(ax, s, p):
    it = s['items']; n = len(it); ymax = s['ymax']; base = 20; hgt = 58
    xs = np.linspace(40, 152, n) if n > 1 else [96]
    bw = s.get('bw', 22)
    ax.plot([20, 172], [base, base], color=DIM, lw=2)
    if s.get('band'):
        b = s['band']; a = seg(p, .3, .5)
        ax.add_patch(Rectangle((20, base + b[0] / ymax * hgt), 152, (b[1] - b[0]) / ymax * hgt, color=b[2], alpha=.18 * a, lw=0))
        T(ax, 174, base + (b[0] + b[1]) / 2 / ymax * hgt, b[3], 22, b[2], ha='left', alpha=a)
    for h in s.get('hlines', []):
        a = seg(p, .3, .5); y = base + h['v'] / ymax * hgt
        ax.plot([20, 172], [y, y], color=h['color'], lw=3, ls='--', alpha=a)
        T(ax, 173, y, h['label'], 22, h['color'], ha='left', alpha=a)
    for i, (x, b) in enumerate(zip(xs, it)):
        g = seg(p, .05 + .2 * i, .05 + .2 * i + .35)
        h = b['value'] / ymax * hgt * g
        ax.add_patch(Rectangle((x - bw / 2, base), bw, h, color=b['color'], lw=0))
        T(ax, x, base + h + 4.5, f"{b['value']:g}{s.get('unit','')}", 40, FG, alpha=g, weight='bold')
        T(ax, x, base - 6, b['label'], 26, FG, alpha=seg(p, .05 + .2 * i, .05 + .2 * i + .2))
        if b.get('tag'):
            ta = seg(p, .6 + .1 * i, .8 + .1 * i)
            T(ax, x, base + h + 12, b['tag'], 34, b.get('tagcolor', ACT), alpha=ta, weight='bold')


def t_ranges(ax, s, p):
    lo, hi = s['lo'], s['hi']; X0, X1, AY = 18, 174, 30
    mx = lambda v: X0 + (v - lo) / (hi - lo) * (X1 - X0)
    ax.plot([X0, X1], [AY, AY], color=DIM, lw=2)
    for v in np.arange(lo, hi + 1e-6, s['step']):
        ax.plot([mx(v)] * 2, [AY - 1.2, AY + 1.2], color=DIM, lw=2); T(ax, mx(v), AY - 5, f'{v:g}', 24, DIM)
    if s.get('axis_label'): T(ax, W / 2, AY - 12, s['axis_label'], 24, DIM)
    rows = s.get('rows', []); n = len(rows); y0 = s.get('top', 84); dy = s.get('dy', 17)
    for i, r in enumerate(rows):
        a = seg(p, .05 + .6 * i / max(n, 1), .05 + .6 * i / max(n, 1) + .25); y = y0 - i * dy
        T(ax, X0, y + 6.2, r['label'], 28, r['color'], ha='left', alpha=a, weight='bold')
        if r.get('lo') is not None:
            xa, xb = mx(r['lo']), mx(r['hi']); xb2 = xa + (xb - xa) * a
            ax.add_patch(Rectangle((xa, y - 2.5), xb2 - xa, 5, color=r['color'], alpha=r.get('alpha', .85) * 1.0, lw=0))
            if a > .9:
                T(ax, xa, y - 6.5, f"{r['lo']:g}", 22, r['color']); T(ax, xb, y - 6.5, f"{r['hi']:g}", 22, r['color'])
        if r.get('point') is not None:
            xp = mx(r['point'])
            ax.add_patch(Circle((xp, y), 2.6 * (0.4 + .6 * a), color=r['color'], zorder=5, alpha=a))
            T(ax, xp, y + 5, r.get('pt_label', f"{r['point']:g}"), 30, FG, alpha=a, weight='bold')
    for v in s.get('vlines', []):
        a = seg(p, v.get('a', .5), v.get('a', .5) + .2); x = mx(v['v'])
        ax.plot([x, x], [AY, 96], color=v['color'], lw=3.2, ls=v.get('ls', '-'), alpha=a * .9)
        T(ax, x, 99, v['label'], 26, v['color'], alpha=a, weight='bold')


def t_timeline(ax, s, p):
    t0, t1 = s['t0'], s['t1']; X0, X1, AY = 14, 178, s.get('ay', 50)
    mx = lambda t: X0 + (t - t0) / (t1 - t0) * (X1 - X0)
    ax.plot([X0, X1], [AY, AY], color=DIM, lw=3)
    for t in s.get('ticks', []):
        ax.plot([mx(t)] * 2, [AY - 1.5, AY + 1.5], color=DIM, lw=2); T(ax, mx(t), AY - 6, s.get('tickfmt', '{:g}').format(t), 24, DIM)
    ev = s.get('events', []); sp = s.get('spans', []); n = len(ev) + len(sp)
    k = 0
    for b in sp:
        a = seg(p, .05 + .65 * k / max(n, 1), .05 + .65 * k / max(n, 1) + .25); k += 1
        xa, xb = mx(b['a']), mx(b['b']); xe = xa + (xb - xa) * a
        yy = AY + b.get('dy', 12)
        ax.add_patch(Rectangle((xa, yy - 2), xe - xa, 4, color=b['color'], lw=0, alpha=.9))
        ax.plot([xa, xa], [AY, yy], color=b['color'], lw=2, alpha=a); ax.plot([xb, xb], [AY, yy], color=b['color'], lw=2, alpha=a * (a > .95))
        T(ax, (xa + xb) / 2, yy + 6.5, b['label'], 30, FG, alpha=a, weight='bold')
    for e in ev:
        a = seg(p, .05 + .65 * k / max(n, 1), .05 + .65 * k / max(n, 1) + .25); k += 1
        x = mx(e['t']); up = e.get('up', True); yy = AY + (e.get('h', 20) if up else -e.get('h', 20))
        ax.plot([x, x], [AY, AY + (yy - AY) * a], color=e['color'], lw=3)
        ax.add_patch(Circle((x, AY), 1.6, color=e['color'], zorder=5))
        T(ax, x, yy + (6 if up else -6), e['label'], e.get('size', 30), FG, alpha=a, weight='bold')
        if e.get('sub'): T(ax, x, yy + (1 if up else -12), e['sub'], 22, e['color'], alpha=a)


def t_dots(ax, s, p):
    n = sum(g['count'] for g in s['groups']); cols = s.get('cols', 10); rows = math.ceil(n / cols)
    cx, cy = s.get('cx', 96), s.get('cy', 52); sx, sy = s.get('sx', 8), s.get('sy', 8.5)
    r = s.get('r', 2.6); rng = np.random.RandomState(4)
    idx = 0
    if s.get('mode') == 'converge':
        ang = rng.rand(n) * 2 * np.pi; rad = 18 + rng.rand(n) * 34
        px = cx + np.cos(ang) * rad * 1.9; py = cy + np.sin(ang) * rad * .85
        k = seg(p, .35, .8)
        for i in range(n):
            a = seg(p, .02 + .3 * i / n, .02 + .3 * i / n + .1)
            x = px[i] + (cx - px[i]) * k; y = py[i] + (cy - py[i]) * k
            ax.add_patch(Circle((x, y), r * (1 - .3 * k), color=PANEL, alpha=.85 * a, lw=0))
        if k > .85:
            ax.add_patch(Circle((cx, cy), 9 * (k - .85) / .15, color=PANEL, alpha=.95, zorder=6))
            T(ax, cx, cy, s.get('final', '1'), 58, BG, alpha=seg(p, .9, 1.0), weight='bold', zorder=7)
        return
    for g in s['groups']:
        for j in range(g['count']):
            i = idx; idx += 1; rr, cc = divmod(i, cols)
            x = cx + (cc - (cols - 1) / 2) * sx; y = cy + ((rows - 1) / 2 - rr) * sy
            a = seg(p, g['a'] + (g['b'] - g['a']) * j / max(g['count'], 1), g['a'] + (g['b'] - g['a']) * j / max(g['count'], 1) + .05)
            col = g['color']
            if g.get('turn') and p > g['turn'][1]:
                col = g['turn'][0] if (j < g.get('turn_n', g['count'])) else col
            ax.add_patch(Circle((x, y), r, color=col, alpha=a, lw=0))
    for lb in s.get('labels', []):
        T(ax, lb['x'], lb['y'], lb['t'], lb.get('size', 34), lb.get('color', FG), alpha=seg(p, lb['a'], lb['a'] + .15), weight='bold')


def bump(t, t0, tp, A):
    u = (t - t0) / 11.0; up = (tp - t0) / 11.0
    out = np.zeros_like(t, dtype=float)
    m = (u >= 0) & (u < up); out[m] = .5 * (1 - np.cos(np.pi * u[m] / up))
    m = (u >= up) & (u <= 1); out[m] = .5 * (1 + np.cos(np.pi * (u[m] - up) / (1 - up)))
    return A * out


_SSN = None


class _ClipAx:
    def __init__(self, ax, plot): self._ax = ax; self.plot = plot
    def __getattr__(self, n): return getattr(self._ax, n)



def t_ssn(ax, s, p):
    global _SSN
    if _SSN is None: _SSN = load_ssn()
    raw, sm = _SSN
    x0, x1, ymax = s['x0'], s['x1'], s['ymax']; X0, X1, Y0, Y1 = 22, 176, 20, 84
    mx = lambda t: X0 + (np.asarray(t) - x0) / (x1 - x0) * (X1 - X0); my = lambda v: Y0 + np.asarray(v) / ymax * (Y1 - Y0)
    ax.plot([X0, X1], [Y0, Y0], color=DIM, lw=2); ax.plot([X0, X0], [Y0, Y1 + 4], color=DIM, lw=2)
    for v in np.arange(0, ymax + 1, s.get('ystep', 50)):
        ax.plot([X0, X1], [my(v)] * 2, color=GRID, lw=1.5, zorder=0); T(ax, X0 - 2, my(v), f'{v:g}', 22, DIM, ha='right')
    for t in s.get('xticks', []):
        T(ax, mx(t), Y0 - 4.5, f'{t:g}', 22, DIM)
    T(ax, X0 - 12, 90, 'Sunspot number', 22, DIM, ha='left')
    cp = Rectangle((X0, Y0 - 1), X1 - X0, Y1 - Y0 + 8, transform=ax.transData)
    _plot = ax.plot
    def plot(*a, **k):
        r = _plot(*a, **k)
        for l in r: l.set_clip_path(cp)
        return r
    ax = _ClipAx(ax, plot)
    rev = x0 + (x1 - x0) * seg(p, s.get('ra', .05), s.get('rb', .75)) if not s.get('static') else x1 + 1
    for hb in s.get('hbands', []):
        a = seg(p, hb.get('a', .5), hb.get('a', .5) + .2)
        ta, tb = hb.get('ta', x0), hb.get('tb', x1)
        ax.add_patch(Rectangle((mx(ta), my(hb['lo'])), mx(tb) - mx(ta), my(hb['hi']) - my(hb['lo']), color=hb['color'], alpha=.2 * a, lw=0))
        if hb.get('label'): T(ax, mx(tb) + 1, (my(hb['lo']) + my(hb['hi'])) / 2, hb['label'], 22, hb['color'], ha='left', alpha=a)
    for hl in s.get('hlines', []):
        a = seg(p, hl.get('a', .5), hl.get('a', .5) + .2)
        ax.plot([X0, X1], [my(hl['v'])] * 2, color=hl['color'], lw=3, ls='--', alpha=a)
        T(ax, X1 - 1, my(hl['v']) + 3.2, hl['label'], 24, hl['color'], ha='right', alpha=a, weight='bold')
    if s.get('raw'):
        m = (raw[:, 0] >= x0) & (raw[:, 0] <= min(rev, x1)); ax.plot(mx(raw[m, 0]), my(raw[m, 1]), color=s.get('rawcolor', '#5b6788'), lw=2)
    if s.get('smooth', True):
        m = (sm[:, 0] >= x0) & (sm[:, 0] <= min(rev, x1) if s.get('smooth_to') is None else sm[:, 0] <= min(rev, s['smooth_to']))
        ax.plot(mx(sm[m, 0]), my(sm[m, 1]), color=WHITE, lw=5, zorder=4, solid_capstyle='round')
    for c in s.get('curves', []):
        a = seg(p, c.get('a', .5), c.get('a', .5) + .3)
        tt = np.linspace(c['t0'], c['t0'] + 11, 200); vv = bump(tt, c['t0'], c['tp'], c['A'])
        k = int(200 * a)
        ax.plot(mx(tt[:k]), my(vv[:k]), color=c['color'], lw=5, ls=c.get('ls', '-'), zorder=3)
        if c.get('label') and a > .5: T(ax, mx(c['tp']) + c.get('lx', 0), my(c['A']) + c.get('ly', 6), c['label'], 28, c['color'], alpha=seg(p, c.get('a', .5) + .25, c.get('a', .5) + .45), weight='bold')
    for v in s.get('vlines', []):
        a = seg(p, v.get('a', .5), v.get('a', .5) + .2)
        ax.plot([mx(v['t'])] * 2, [Y0, Y1], color=v['color'], lw=2.5, ls='--', alpha=a)
        T(ax, mx(v['t']), Y1 + 3, v['label'], 22, v['color'], alpha=a)
    for pt in s.get('points', []):
        a = seg(p, pt.get('a', .6), pt.get('a', .6) + .15)
        ax.add_patch(Circle((mx(pt['t']), my(pt['v'])), 1.6 + 1.4 * a, color=pt['color'], zorder=6, alpha=a))
        T(ax, mx(pt['t']) + pt.get('lx', 0), my(pt['v']) + pt.get('ly', 7), pt['label'], pt.get('size', 30), FG, alpha=a, weight='bold', zorder=7)
    for bx in s.get('boxes', []):
        a = seg(p, bx.get('a', .5), bx.get('a', .5) + .2)
        ax.add_patch(Rectangle((mx(bx['ta']), my(bx['lo'])), mx(bx['tb']) - mx(bx['ta']), my(bx['hi']) - my(bx['lo']), fill=False, ec=bx['color'], lw=4, alpha=a))
        if bx.get('label'): T(ax, (mx(bx['ta']) + mx(bx['tb'])) / 2, my(bx['hi']) + 3.5, bx['label'], 24, bx['color'], alpha=a, weight='bold')


def sun_disc(ax, cx, cy, R):
    ax.add_patch(Circle((cx, cy), R, color=SUN, lw=0, zorder=1)); ax.add_patch(Circle((cx, cy), R * .92, color='#ffb347', lw=0, zorder=1, alpha=.55))
    ax.add_patch(Circle((cx, cy), R * .6, color='#ffd27d', lw=0, zorder=1, alpha=.25))
    c = Circle((cx, cy), R, transform=ax.transData); return c


def band(ax, cx, cy, R, lat_c, hw, color, alpha=.8, clip=None):
    """latitude strip centred on lat_c deg (north +), half-width hw deg (cosmetic: linear in latitude)"""
    y0 = cy + R * math.sin(math.radians(lat_c - hw)); y1 = cy + R * math.sin(math.radians(lat_c + hw))
    r = Rectangle((cx - R, min(y0, y1)), 2 * R, abs(y1 - y0), color=color, alpha=alpha, lw=0, zorder=3)
    ax.add_patch(r); r.set_clip_path(clip)


def t_sun(ax, s, p):
    cx, cy, R = s.get('cx', 96), s.get('cy', 52), s.get('R', 36)
    disc = sun_disc(ax, cx, cy, R); clip = Circle((cx, cy), R, transform=ax.transData)
    ax.plot([cx - R - 4, cx + R + 4], [cy, cy], color=WHITE, lw=1.5, ls=':', alpha=.5, zorder=4); T(ax, cx + R + 6, cy, 'equator', 22, DIM, ha='left')
    mode = s['mode']
    if mode == 'two_belts':
        a = seg(p, .15, .5)
        for sg in (1, -1):
            band(ax, cx, cy, R, sg * 28, 9, TEAM if False else '#7ad7ff', .85 * a, clip)
        T(ax, cx + R + 8, cy + R * .52, 'northern band', 28, '#7ad7ff', ha='left', alpha=a); T(ax, cx + R + 8, cy - R * .52, 'southern band', 28, '#7ad7ff', ha='left', alpha=a)
    elif mode == 'overlap':
        a = seg(p, .05, .35); b = seg(p, .45, .8)
        for sg in (1, -1):
            band(ax, cx, cy, R, sg * 20, 7, '#7ad7ff', .85 * a, clip)
            band(ax, cx, cy, R, sg * 52, 7, '#ff7ad7', .85 * b, clip)
        T(ax, cx - R - 6, cy + R * .3, 'old round', 28, '#7ad7ff', ha='right', alpha=a, weight='bold'); T(ax, cx - R - 6, cy + R * .78, 'new round', 28, '#ff7ad7', ha='right', alpha=b, weight='bold')
    elif mode in ('creep', 'cancel', 'await'):
        k = seg(p, .1, .85)
        lat_old = 20 - 14 * k if mode != 'await' else 20 - 9 * k; lat_new = 52 - 22 * k
        if mode == 'cancel': lat_old = 20 - 16 * k
        for sg in (1, -1):
            if mode != 'cancel' or k < .98:
                col = '#7ad7ff' if sg > 0 else '#ff9a7a'
                band(ax, cx, cy, R, sg * max(lat_old, 3), 6, col, .9, clip)
            if s.get('new', True): band(ax, cx, cy, R, sg * lat_new, 6, '#ff7ad7' if sg > 0 else '#b57aff', .7, clip)
        if mode == 'cancel':
            f = seg(p, .8, .95)
            ax.add_patch(Circle((cx, cy), R * .22 * f, color=WHITE, alpha=.5 * f, zorder=6, lw=0))
            T(ax, cx, cy - R - 8, 'opposite magnetism meets: cancels', 30, FG, alpha=f, weight='bold')
        if mode == 'await':
            T(ax, cx, cy - R - 8, 'still moving toward the equator', 30, FG, alpha=seg(p, .5, .8), weight='bold')
    elif mode == 'spot':
        sx, sy = cx + 6, cy + 8
        ax.add_patch(matplotlib.patches.Ellipse((sx, sy), 30, 11, color='#3a1a05', zorder=3, alpha=.95))
        ax.add_patch(matplotlib.patches.Ellipse((sx, sy), 22, 7, color='#150800', zorder=4))
        a = seg(p, .3, .9); n = int(15 * a)
        for i in range(n):
            ax.add_patch(Circle((sx - 14 + 2 * i + 1, sy - 11), 0.95, color='#3b8dff', zorder=6, lw=0))
        ax.annotate('', xy=(sx - 15, sy - 7.5), xytext=(sx + 15, sy - 7.5), arrowprops=dict(arrowstyle='<->', color=WHITE, lw=2), alpha=a)
        T(ax, sx, sy - 16, 'about 15 Earths across', 30, FG, alpha=a, weight='bold', zorder=8)


def t_atmos(ax, s, p):
    Cx, Cy, Re = 96, -118, 148
    ax.add_patch(Circle((Cx, Cy), Re, color='#16315e', lw=0, zorder=1))
    k = seg(p, .15, .7) if s['mode'] == 'puff' else 1.0
    thick = 3.5 + 11 * k
    ax.add_patch(Circle((Cx, Cy), Re + thick, color='#ff6b35' if s['mode'] == 'puff' else '#ff8c5a', alpha=.18 + .25 * k, lw=0, zorder=0))
    ax.add_patch(Circle((Cx, Cy), Re + 3.5, color='#2b7bd6', alpha=.5, lw=0, zorder=0))
    ax.add_patch(Circle((Cx, Cy), Re, color='#16315e', lw=0, zorder=1))
    T(ax, 30, 38 + 8 * k, 'thin air', 26, DIM, ha='left', alpha=1 - .6 * k)
    if s['mode'] == 'puff':
        T(ax, 150, 52, 'storm heats the air', 34, '#ff8c5a', alpha=seg(p, .2, .4), weight='bold')
        T(ax, 150, 44, 'and it puffs upward', 30, FG, alpha=seg(p, .4, .6))
        for x in (40, 80, 120, 160):
            ax.annotate('', xy=(x, 20 + Re + thick - 148 + 36 + 8 * k + 4), xytext=(x, 36), arrowprops=dict(arrowstyle='->', color='#ff8c5a', lw=3), alpha=seg(p, .3, .6))
    else:
        alt = Re + 8
        for i in range(6):
            ang = math.radians(112 - i * 9 - 16 * seg(p, .1, .9) * 0)
            drop = 5.0 * seg(p, .25 + .05 * i, .9)
            rr = alt - drop * (1 + i * .12)
            ax.add_patch(Circle((Cx + rr * math.cos(ang), Cy + rr * math.sin(ang)), 1.4, color=PANEL if drop < 3.5 else ACT, zorder=6, lw=0))
        T(ax, 150, 60, 'more air at the same height', 28, '#ff8c5a', alpha=seg(p, .1, .3), weight='bold')
        T(ax, 150, 52, 'satellites slow and sink', 28, FG, alpha=seg(p, .4, .6))


def t_flow(ax, s, p):
    nd = s['nodes']; n = len(nd); bh = s.get('bh', 20); y = s.get('y', 54); gap = s.get('gap', 18)
    for nn in nd:
        sz = nn.get('size', 34)
        nn['_w'] = max(len(nn['t']) * 0.082 * sz + 9, (len(nn.get('sub', '')) * 0.07 * 22 + 9), s.get('minw', 16))
    tot = sum(nn['_w'] for nn in nd) + gap * (n - 1)
    k = min(1.0, 176.0 / tot)
    x = 96 - tot * k / 2; xs = []
    for nn in nd:
        w = nn['_w'] * k; xs.append((x + w / 2, w)); x += w + gap * k
    for i, ((cx, bw), nn) in enumerate(zip(xs, nd)):
        a = seg(p, .05 + .6 * i / max(n, 1), .05 + .6 * i / max(n, 1) + .25); hl = nn.get('hl', False)
        sc = 1.0 + (.1 if hl else 0)
        ax.add_patch(FancyBboxPatch((cx - bw * sc / 2, y - bh * sc / 2), bw * sc, bh * sc, boxstyle='round,pad=0.4,rounding_size=2', fc=nn.get('fc', '#141c36'), ec=nn['color'], lw=5 if hl else 3, alpha=a))
        T(ax, cx, y + (3 if nn.get('sub') else 0), nn['t'], nn.get('size', 34) * k, FG, alpha=a, weight='bold')
        if nn.get('sub'): T(ax, cx, y - 5.5, nn['sub'], 22 * k, nn['color'], alpha=a)
        if i < n - 1 and s.get('arrows', True):
            aa = seg(p, .15 + .6 * i / max(n, 1), .35 + .6 * i / max(n, 1))
            nx = xs[i + 1][0] - xs[i + 1][1] / 2
            ax.annotate('', xy=(nx - 1.5, y), xytext=(cx + bw / 2 + 1.5, y), arrowprops=dict(arrowstyle='-|>', color=DIM, lw=4), alpha=aa)


def t_bignum(ax, s, p):
    it = s['items']; n = len(it); xs = np.linspace(48, 144, n) if n > 1 else [96]
    for i, (x, b) in enumerate(zip(xs, it)):
        a = seg(p, .05 + .3 * i, .05 + .3 * i + .3)
        if b.get('count') is not None:
            val = b['count'] * a; txt = (b.get('fmt', '{:.0f}')).format(val)
        else: txt = b['big']
        T(ax, x, 58, txt, b.get('size', 90), b['color'], alpha=a, weight='bold'); T(ax, x, 36, b['label'], 32, FG, alpha=a)
        if b.get('sub'): T(ax, x, 28, b['sub'], 24, DIM, alpha=a)
    if s.get('between'): T(ax, 96, 58, s['between'], 60, DIM, alpha=seg(p, .4, .6))


def t_table(ax, s, p):
    R = s['rows']; n = len(R); y0 = s.get('top', 78); dy = s.get('dy', 17)
    for i, r in enumerate(R):
        a = seg(p, .05 + .7 * i / max(n, 1), .05 + .7 * i / max(n, 1) + .2); y = y0 - i * dy
        ax.add_patch(FancyBboxPatch((18, y - 6), 156, 12, boxstyle='round,pad=0.3,rounding_size=2', fc='#141c36', ec=r['color'], lw=3, alpha=a))
        T(ax, 24, y + 1.2, r['name'], 32, r['color'], ha='left', alpha=a, weight='bold')
        if r.get('sub'): T(ax, 24, y - 3.6, r['sub'], 20, DIM, ha='left', alpha=a)
        T(ax, 168, y, r['verdict'], 34, r.get('vcolor', FG), ha='right', alpha=a, weight='bold')


TEMPL = dict(table=t_table, text=t_text, bars=t_bars, ranges=t_ranges, timeline=t_timeline, dots=t_dots, ssn=t_ssn, sun=t_sun, atmos=t_atmos, flow=t_flow, bignum=t_bignum)


def draw(s, p):
    fig, ax = new_ax(); chrome(ax, s, p); TEMPL[s['tpl']](ax, s, p); return fig


def frame_rgb(s, p):
    fig = draw(s, p); fig.canvas.draw(); buf = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy(); plt.close(fig); return buf


def render_card(s, dur, out, build=None):
    """Build animation over `build` s (default min(0.6*dur, 4.5)), then hold last frame to `dur`."""
    build = build or min(dur * 0.75, 6.5); nb = max(2, int(round(build * FPS))); total = int(round(dur * FPS))
    hold = (total - nb) / FPS
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1920x1080', '-r', str(FPS), '-i', '-',
           '-vf', f'tpad=stop_mode=clone:stop_duration={hold:.3f},format=yuv420p', '-t', f'{dur:.3f}', '-c:v', 'libx264', '-crf', '18', '-preset', 'fast', '-r', str(FPS), out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(nb):
        pr.stdin.write(frame_rgb(s, i / (nb - 1)).tobytes())
    pr.stdin.close(); pr.wait()
