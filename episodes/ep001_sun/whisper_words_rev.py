# faster-whisper large-v3 word timestamps per narration paragraph (CPU). eval venv.
import json,os,re,sys,glob,soundfile as sf,numpy as np,subprocess
from faster_whisper import WhisperModel
os.chdir(os.path.dirname(os.path.abspath(__file__)))
m=WhisperModel('large-v3',device='cpu',compute_type='int8',cpu_threads=24)
for f in sorted(glob.glob('audio/para/N*.wav'),reverse=True):
    nid=os.path.basename(f)[:-4]; out=f'audio/words/{nid}.json'
    if os.path.exists(out): continue
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',f,'-ac','1','-ar','16000','/tmp/_w2.wav'],check=True); a,_=sf.read('/tmp/_w2.wav',dtype='float32')
    segs,info=m.transcribe(a,language='en',word_timestamps=True,beam_size=5,vad_filter=False)
    ws=[]
    for s in segs:
        for w in s.words: ws.append({'w':w.word.strip(),'s':round(w.start,3),'e':round(w.end,3)})
    json.dump(ws,open(out,'w')); print(nid,len(ws),flush=True)
