import json,os,re,subprocess,difflib,math,soundfile as sf
os.chdir(os.path.dirname(os.path.abspath(__file__)))
items=json.load(open('script_items.json'))
def norm(w):
    return re.sub(r"[^a-z0-9]","",w.lower())
def toks(text):
    text=text.replace('[BEAT]',' ').replace('-',' ').replace('—',' ')
    return [t for t in re.sub(r"[^A-Za-z0-9' ]"," ",text).replace("'"," ").split() ]
def host_dur(it):
    fr=math.ceil
    n=max(5,int(round(it['secs']*24)))
    while n%17!=5: n+=1
    p=f"host/clips/host_{it['id']}.mp4"
    if os.path.exists(p):
        return float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True,text=True).stdout)
    return n/24
t=0.0; segs=[]; words=[]; prev=None; pend_chapter=False
for it in items:
    if it['type']=='chapter': pend_chapter=True; continue
    gap=0 if prev is None else (0.9 if pend_chapter else 0.35); pend_chapter=False
    if it['type']=='host':
        st=t+gap; d=host_dur(it); segs.append({'type':'host','id':it['id'],'start':round(st,3),'end':round(st+d,3),'text':it['text'],'chapter':it['chapter'],'actual':os.path.exists(f"host/clips/host_{it['id']}.mp4")}); t=st+d
    else:
        lead=0.6 if it['parts'][0]=='' else 0
        st=t+gap+lead; info=sf.info(f"audio/para/{it['id']}.wav"); d=info.duration
        segs.append({'type':'nar','id':it['id'],'start':round(st,3),'end':round(st+d,3),'text':it['text'],'chapter':it['chapter'],'file':f"audio/para/{it['id']}.wav"}); 
        # words
        stoks=toks(it['text']); wp=f"audio/words/{it['id']}.json"
        wh=json.load(open(wp)) if os.path.exists(wp) else []
        sn=[norm(x) for x in stoks]; wn=[norm(x['w']) for x in wh]
        times=[None]*len(stoks)
        sm=difflib.SequenceMatcher(None,sn,wn,autojunk=False)
        for tag,i1,i2,j1,j2 in sm.get_opcodes():
            if tag=='equal':
                for k in range(i2-i1): times[i1+k]=(wh[j1+k]['s'],wh[j1+k]['e'])
            elif tag=='replace' and (i2-i1)==(j2-j1):
                for k in range(i2-i1): times[i1+k]=(wh[j1+k]['s'],wh[j1+k]['e'])
        # interpolate gaps
        n=len(times); last=0.0
        idx=[i for i,x in enumerate(times) if x]
        if not idx: 
            for i in range(n): times[i]=(d*i/n,d*(i+1)/n)
        else:
            for i in range(n):
                if times[i] is None:
                    lo=max([j for j in idx if j<i],default=None); hi=min([j for j in idx if j>i],default=None)
                    a=times[lo][1] if lo is not None else 0.0; b=times[hi][0] if hi is not None else d
                    l=lo if lo is not None else -1; h=hi if hi is not None else n
                    times[i]=(a+(b-a)*(i-l-1)/(h-l-1),a+(b-a)*(i-l)/(h-l-1))
        for tk,tm in zip(stoks,times): words.append({'para':it['id'],'w':tk,'n':norm(tk),'start':round(st+tm[0],3),'end':round(st+tm[1],3)})
        t=st+d
    prev=it
json.dump({'segments':segs,'words':words,'total':round(t,3)},open('timeline.json','w'),indent=0)
print('total',round(t,1),'s',len(segs),'segments',len(words),'words')
