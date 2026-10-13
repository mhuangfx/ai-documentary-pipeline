#!/usr/bin/env python3
"""Assemble rough cut from shotlist.json + timeline.json. Run with eval venv python (soundfile, pyloudnorm)."""
import json, os, subprocess, sys, numpy as np, soundfile as sf, pyloudnorm as pln
from concurrent.futures import ThreadPoolExecutor
os.chdir(os.path.dirname(os.path.abspath(__file__)))
FPS = 24; SR = 24000
tl = json.load(open('timeline.json')); shots = json.load(open('shotlist_final.json'))
os.makedirs('seg', exist_ok=True)
VF = 'scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0a0f1e,setsar=1,fps=24,format=yuv420p'
ENC = ['-c:v', 'libx264', '-crf', '17', '-preset', 'veryfast', '-r', '24', '-an']

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: print('FFERR', ' '.join(cmd)[:200], r.stderr[-400:]); return False
    return True

# frame boundaries
items = []  # (kind, id, start_frame, nframes, spec)
for s in shots['shots']:
    items.append(('shot', s['id'], s['start'], s['end'], s))
for h in tl['segments']:
    if h['type'] == 'host': items.append(('host', h['id'], h['start'], h['end'], h))
items.sort(key=lambda x: x[2])

def title_card(path, text, dur):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (1920, 1080), (10, 15, 30)); d = ImageDraw.Draw(im)
    d.text((100, 500), text, fill=(240, 240, 240)); im.save(path)

def make_seg(i, it):
    kind, id_, a, b, s = it
    fa, fb = round(a * FPS), round(b * FPS); n = max(1, fb - fa); dur = n / FPS
    out = f'seg/{i:03d}_{id_}.mp4'
    if os.path.exists(out) and os.path.getsize(out) > 1000 and not os.environ.get('REDO'): return out, n
    if kind == 'host':
        src = f"host/clips/host_{id_}.mp4"
        if os.path.exists(src):
            ok = run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-vf', VF + f',tpad=stop_mode=clone:stop_duration=1', '-t', f'{dur:.4f}'] + ENC + [out])
            return (out if ok else None), n
        s = {'lane': 'MISSING', 'final_file': None, 'subject': 'host ' + id_}
    lane = s['lane']; f = s.get('final_file'); mode = s.get('final_mode')
    if mode == 'card' or (lane == 'DG' and f):
        ok = run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f, '-vf', VF + ',tpad=stop_mode=clone:stop_duration=2', '-t', f'{dur:.4f}'] + ENC + [out])
    elif mode == 'video':
        ss = s.get('ss', 0)
        # stretch if source shorter than needed (slow-mo up to 2x), else trim
        sd = s.get('src_dur', 0)
        spd = 1.0
        if sd and sd - ss < dur: spd = min(2.5, dur / max(0.5, sd - ss))
        ok = run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{ss:.3f}', '-i', f, '-vf', f'setpts={spd}*PTS,' + VF + ',tpad=stop_mode=clone:stop_duration=3', '-t', f'{dur:.4f}'] + ENC + [out])
    elif mode == 'still':
        z = s.get('push', 'in'); frames = n
        zexpr = f"1+0.07*on/{frames}" if z == 'in' else f"1.07-0.07*on/{frames}"
        crop = s.get('crop_y', 0.5)
        vf = (f"scale=3840:2160:force_original_aspect_ratio=increase:flags=lanczos,crop=3840:2160:(iw-3840)/2:(ih-2160)*{crop},"
              f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=24,format=yuv420p")
        ok = run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f, '-vf', vf, '-frames:v', str(frames)] + ENC + [out])
    else:  # missing -> title card
        txt = f"MISSING SHOT {id_}".replace(':', ' ')
        ok = run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'color=c=0x0a0f1e:s=1920x1080:r=24:d={dur:.4f}', '-vf', f"drawtext=text='{txt}':fontcolor=white:fontsize=56:x=100:y=500,format=yuv420p", '-c:v', 'libx264', '-crf', '20', out])
    return (out if ok else None), n

if __name__ == '__main__':
    with ThreadPoolExecutor(20) as ex:
        res = list(ex.map(lambda t: make_seg(*t), enumerate(items)))
    bad = [items[i][1] for i, (o, n) in enumerate(res) if not o]
    print('seg failures', bad)
    # normalise frame counts: concat list
    lst = open('seg/list.txt', 'w'); tot = 0
    for (o, n) in res:
        if o: lst.write(f"file '{os.path.abspath(o)}'\n")
    lst.close()
    # AUDIO
    total = tl['total'] + 1.0
    A = np.zeros(int(total * SR), dtype='float32'); meter = pln.Meter(SR)
    for sg in tl['segments']:
        if sg['type'] == 'nar':
            a, sr = sf.read(sg['file'], dtype='float32'); i0 = int(sg['start'] * SR); A[i0:i0 + len(a)] += a[:len(A) - i0]
        else:
            p = f"host/clips/host_{sg['id']}.mp4"
            if not os.path.exists(p): continue
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', p, '-vn', '-ac', '1', '-ar', str(SR), 'seg/_h.wav'], check=True)
            a, _ = sf.read('seg/_h.wav', dtype='float32')
            if len(a) > SR and np.abs(a).max() > 1e-4:
                l = meter.integrated_loudness(a); a = pln.normalize.loudness(a, l, -16.0); a = np.clip(a, -0.95, 0.95)
            i0 = int(sg['start'] * SR); A[i0:i0 + len(a)] += a[:len(A) - i0]
    sf.write('audio/narration_mix.wav', A, SR)
    r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'seg/list.txt', '-i', 'audio/narration_mix.wav',
                        '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '21', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', '24', '-c:a', 'aac', '-b:a', '192k', '-shortest', 'rough_cut_1080p.mp4'])
    print('1080p rc', r.returncode)
