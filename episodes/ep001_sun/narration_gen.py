# Chatterbox Voice A, sentence chunks, fixed seed per paragraph. Run with pipeline/venv_tts python.
import json,re,sys,time,os,numpy as np,soundfile as sf,torch
os.chdir(os.path.dirname(os.path.abspath(__file__)))
REF=os.environ['VOICE_REF']  # reference voice clip; the host voice is withheld
from chatterbox.tts import ChatterboxTTS
items=[i for i in json.load(open('script_items.json')) if i['type']=='nar']
t0=time.time(); m=ChatterboxTTS.from_pretrained('cuda'); print('load',time.time()-t0,flush=True)
meta={}
def trim(a,sr,thr=0.004,pad=0.04):
    idx=np.where(np.abs(a)>thr)[0]
    if len(idx)==0: return a
    s=max(0,idx[0]-int(pad*sr)); e=min(len(a),idx[-1]+int(pad*sr)); return a[s:e]
for k,it in enumerate(items):
    out=f"audio/raw/{it['id']}.json"
    if os.path.exists(out): continue
    torch.manual_seed(7000+k); t1=time.time(); rec=[]
    for pi,part in enumerate(it['parts']):
        sents=[s for s in re.split(r'(?<=[.?!])\s+',part) if s.strip()]
        for si,s in enumerate(sents):
            w=m.generate(s,audio_prompt_path=REF,exaggeration=0.5,cfg_weight=0.5).squeeze().cpu().numpy().astype('float32')
            w=trim(w,m.sr); fn=f"audio/raw/{it['id']}_{pi}_{si}.wav"; sf.write(fn,w,m.sr)
            rec.append({'part':pi,'file':fn,'text':s,'dur':len(w)/m.sr,'words':len(s.split())})
    json.dump({'id':it['id'],'seed':7000+k,'chunks':rec,'gen_s':time.time()-t1},open(out,'w'),indent=1)
    print(it['id'],'done',round(time.time()-t1,1),flush=True)
print('ALL DONE',time.time()-t0,flush=True)
