#!/usr/bin/env python3
"""Bind shotspec.py to timeline.json -> shotlist.json (+ asset resolution, ledger rows)."""
import json, os, re, sys, glob, csv
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from shotspec import S
tl = json.load(open('timeline.json')); segs = tl['segments']; words = tl['words']
pm = json.load(open('assets/raw/photos/manifest.json'))['photos']
vm_path = 'assets/raw/video/manifest.json'
vm = json.load(open(vm_path)) if os.path.exists(vm_path) else {}
vlist = vm.get('clips', [])
def norm(w): return re.sub(r'[^a-z0-9]', '', w.lower())

PHOTO_ALIAS = {'P06': 'P06_alt', 'P09s': 'P09_swpc', 'P09n': 'P09_ncar', 'P13': 'P13_artemis2_launch', 'P13e': 'P13_artemis2_eclipse', 'P13c': 'P13_artemis2_crew', 'P11': 'P11_sdo_spacecraft'}
def find_photo(ref):
    key = PHOTO_ALIAS.get(ref, ref)
    c = [p for p in pm if p['file'].startswith(key)] or [p for p in pm if p['id'] == key and p.get('role') == 'primary']
    return c[0] if c else None
VID_ALIAS = {'V03q': 'V03b', 'V03': 'V03a', 'V05': 'V05a', 'V06b': 'V06_lasco_c3', 'V06': 'V06_lasco_c2'}
START = {'V09h': 7.0, 'V10a': 0.0}
def find_video(ref):
    key = VID_ALIAS.get(ref, ref)
    for v in vlist:
        f = v.get('file', '')
        if f.startswith(key) or v.get('id') == key: return v
    return None

# per-paragraph word index
byp = {}
for w in words: byp.setdefault(w['para'], []).append(w)
def find_phrase(para, phrase, after=0):
    ws = byp[para]; joined = ''; starts = []
    for i, w in enumerate(ws): starts.append(len(joined)); joined += w['n']
    ph = norm(phrase.replace(' ', ''))
    pos = joined.find(ph, starts[after] if after < len(starts) else 0)
    if pos < 0: return None
    for i in range(len(ws) - 1, -1, -1):
        if starts[i] <= pos: return i
segd = {s['id']: s for s in segs}
order = [s['id'] for s in segs]
shots = []; warnings = []; last_idx = {}
for (n, at, lane, ref, fb, note) in S:
    seg = segd[n]; k = order.index(n); prev = segs[k - 1] if k > 0 else None
    if at is None:
        st = prev['end'] if (prev and prev['type'] == 'host') else seg['start']; wi = 0
    else:
        wi = find_phrase(n, at, last_idx.get(n, 0))
        if wi is None: warnings.append(f'PHRASE NOT FOUND {n}: {at}'); continue
        st = byp[n][wi]['start']
    last_idx[n] = wi
    shots.append(dict(para=n, start=st, lane=lane, ref=ref, fb=fb, note=note, cut_word=byp[n][wi]['w'], cut_idx=wi))
# ends
for i, s in enumerate(shots):
    nxt = shots[i + 1]['start'] if i + 1 < len(shots) else tl['total'] + 0.5
    # host in between?
    hs = [h['start'] for h in segs if h['type'] == 'host' and h['start'] >= s['start'] + 0.01 and h['start'] <= nxt + 0.01]
    s['end'] = round(min([nxt] + hs), 3); s['start'] = round(s['start'], 3)
    s['dur'] = round(s['end'] - s['start'], 3)
    s['id'] = f"S{i+1:03d}"
    s['excerpt'] = ' '.join(w['w'] for w in words if w['start'] >= s['start'] - 0.01 and w['end'] <= s['end'] + 0.3)[:160]
PH_EXTRA={'S003','S065','S098','S099','S100','S138','S150'}
for s in shots:
    if s['id'] in PH_EXTRA and s['lane']=='PS': s['lane']='PH'; s['fb']='PS:'+s['ref']; s['note']='extra: animate photo'
# resolution
ptr = {}; ledger = []
def to_fallback(s, why):
    fb = s.get('fb')
    s.setdefault('fallback_chain', []).append(why)
    if not fb: return False
    lane, ref = fb.split(':'); s['lane'] = lane; s['ref'] = ref; s['fb'] = None; return True
CARD = 'cards/clips/{}__{}.mp4'
for s in shots:
    while True:
        lane, ref = s['lane'], s['ref']
        if lane == 'DG':
            from cards_spec import CARDS
            if ref not in CARDS: print('NO CARD', ref); break
            s.update(subject='card:' + ref, source='in-house (matplotlib)', licence='n/a (own work; SILSO data CC BY-NC where charted)', final_mode='card'); break
        if lane in ('PS', 'PH'):
            p = find_photo(ref)
            if not p:
                if to_fallback(s, f'photo {ref} missing'): continue
                break
            s.update(subject=p['subject'], source=p['source_url'], licence=p['licence'], credit=p['credit'], src_file='assets/raw/photos/' + p['file'], final_mode='still', final_file='assets/raw/photos/' + p['file'])
            s['push'] = 'in' if int(s['id'][1:]) % 2 == 0 else 'out'; s['crop_y'] = 0.0 if ref == 'P01' else 0.5
            break
        if lane == 'RV':
            v = find_video(ref)
            if not v:
                if to_fallback(s, f'video {ref} missing'): continue
                break
            f = 'assets/raw/video/' + v['file']; sd = v.get('duration_s') or 10
            ss = ptr.get(f, START.get(ref, 0.0))
            if ss + s['dur'] > sd: ss = START.get(ref, 0.0)
            ptr[f] = ss + s['dur']
            s.update(subject=v['subject'], source=v['source_url'], licence=v['licence'], credit=v['credit'], src_file=f, final_mode='video', final_file=f, ss=round(ss, 2), src_dur=sd)
            break
        if lane == 'TV':
            s.update(subject=s['note'], source='H3 local text-to-video (no reference)', licence='generated', final_mode=None)
            break
        break
json.dump(dict(shots=shots, warnings=warnings), open('shotlist.json', 'w'), indent=1)
print(len(shots), 'shots;', 'warnings:', warnings)
from collections import Counter
c = Counter(); d = Counter()
for s in shots: c[s['lane']] += 1; d[s['lane']] += s['dur']
print(c, {k: round(v) for k, v in d.items()})
over = [(s['id'], s['lane'], s['dur']) for s in shots if s['lane'] in ('PH', 'TV') and s['dur'] > 9.6]
print('H3 shots >9.6s:', over)
print('long shots:', [(s['id'], s['dur']) for s in shots if s['dur'] > 14])
