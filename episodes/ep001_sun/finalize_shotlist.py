import json,os,csv,subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))
d=json.load(open('shotlist.json')); sh=d['shots']
log={}
if os.path.exists('logs/gpu_log.csv'):
    for r in csv.DictReader(open('logs/gpu_log.csv')): log[r['name']]=r
verd={}
if os.path.exists('broll/verdicts.json'): verd=json.load(open('broll/verdicts.json'))
def dur(p): return float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True,text=True).stdout)
fbptr=0.0
for s in sh:
    s['final_lane']=s['lane']
    if s['lane']=='DG':
        s['final_mode']='card'; s['final_file']=f"cards/clips/{s['id']}__{s['ref']}.mp4"
    elif s['lane'] in('PH','TV'):
        nm='b_'+s['id']; r=log.get(nm); v=verd.get(nm,'usable')
        if v=='fail' and (nm+'r') in log: nm=nm+'r'; r=log[nm]; v=verd.get(nm,'usable')
        if r and r['status']=='OK' and v!='fail' and r['out'] and os.path.exists(r['out']):
            s['final_mode']='video'; s['final_file']=r['out']; s['src_dur']=dur(r['out']); s['ss']=0; s['h3_wall_s']=int(r['wall_s']); s['h3_verdict']=v
            s['licence']=(s.get('licence') or '')+' | H3 derivative of the photo' if s['lane']=='PH' else 'generated'
        else:
            if s['lane']=='PH':
                s['final_lane']='PS'; s['fallback_reason']='no finished H3 clip' if not r else f"H3 {r['status']}/{v}"
            else:
                s['final_lane']='RV_fallback'; s['fallback_reason']='no finished H3 clip'
                f='assets/raw/video/V09c_svs5344_pfss_field_2020_2024.mp4'; s['final_mode']='video'; s['final_file']=f; s['ss']=round(fbptr,1); s['src_dur']=220; fbptr+=s['dur']+1
                s['source']='NASA SVS 5344'; s['licence']='NASA public domain'; s['credit']='NASA Scientific Visualization Studio'
    if s['final_lane']=='PS' and s.get('final_mode')!='still':
        pass
json.dump(dict(shots=sh,warnings=d['warnings']),open('shotlist_final.json','w'),indent=1)
from collections import Counter
c=Counter();t=Counter()
for s in sh: c[s['final_lane']]+=1;t[s['final_lane']]+=s['dur']
print(c,{k:round(v) for k,v in t.items()})
