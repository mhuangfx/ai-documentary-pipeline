# CPU post: per-paragraph atempo to 182 wpm speech-only, assemble with gaps, normalise -16 LUFS. eval venv.
import json,subprocess,os,numpy as np,soundfile as sf,pyloudnorm as pln
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SR=24000; TARGET=182.0
items=json.load(open('script_items.json'))
def tempo(fn,f,out):
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',fn,'-af',f'atempo={f:.4f}','-ar',str(SR),out],check=True)
rep=[];os.makedirs('audio/para',exist_ok=True)
for it in items:
    if it['type']!='nar': continue
    d=json.load(open(f"audio/raw/{it['id']}.json")); ch=d['chunks']
    sp=sum(c['dur'] for c in ch); wpm0=sum(c['words'] for c in ch)/sp*60
    f=min(1.12,max(0.8,TARGET/wpm0))
    segs=[];prev=None
    for i,c in enumerate(ch):
        o=c['file'].replace('.wav','_t.wav'); tempo(c['file'],f,o); a,_=sf.read(o,dtype='float32')
        if prev is not None:
            gap=0.6 if c['part']!=prev else 0.28
            segs.append(np.zeros(int(SR*gap),dtype='float32'))
        segs.append(a); prev=c['part']
    a=np.concatenate(segs)
    speech=sp/f
    meter=pln.Meter(SR); l=meter.integrated_loudness(a); b=pln.normalize.loudness(a,l,-16.0)
    sf.write('tmp_g.wav',np.clip(b,-4,4).astype('float32'),SR,subtype='FLOAT')
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i','tmp_g.wav','-af','alimiter=limit=0.84:attack=2:release=50:level=0','-c:a','pcm_s16le',f"audio/para/{it['id']}.wav"],check=True)
    a2,_=sf.read(f"audio/para/{it['id']}.wav",dtype='float32')
    rep.append({'id':it['id'],'words':it['words'],'wpm_raw':round(wpm0,1),'tempo':round(f,3),'wpm_final':round(it['words']/speech*60,1),'dur':len(a2)/SR,'lufs':round(meter.integrated_loudness(a2),2) if len(a2)>SR*0.5 else None})
json.dump(rep,open('audio/para_report.json','w'),indent=1)
l=[r['lufs'] for r in rep if r['lufs'] is not None]; print(len(rep),'paras; LUFS min/max',min(l),max(l),'total dur',sum(r['dur'] for r in rep))
