import json,csv,statistics as st,collections,os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sh=json.load(open('shotlist_final.json'))['shots']; tl=json.load(open('timeline.json'))
tot=tl['total']; host=sum(s['end']-s['start'] for s in tl['segments'] if s['type']=='host')
nb=sum(s['dur'] for s in sh)
c=collections.Counter(); t=collections.Counter()
for s in sh: c[s['final_lane']]+=1; t[s['final_lane']]+=s['dur']
print('runtime',round(tot,1),'s =',round(tot/60,2),'min; host',round(host,1),'s; b-roll screen time',round(nb,1))
for k in c: print(k,c[k],round(t[k]),f"{100*t[k]/nb:.1f}%")
d=[s['dur'] for s in sh]
n=len(sh)+sum(1 for s in tl['segments'] if s['type']=='host')
print('shots(+host)',n,'per min',round(n/(tot/60),2),'median b-roll shot',round(st.median(d),2),'mean',round(st.mean(d),2),'max',max(d))
# group
vis=t['RV']+t['RV_fallback']; stills=t['PS']+t['PH']
print('DIAGRAM %.1f VIS %.1f STILLS(+H3 photo) %.1f OTHER %.1f'%tuple(100*x/nb for x in (t['DG'],vis,stills,t['TV'])))
pr=json.load(open('audio/para_report.json'))
print('narration s',round(sum(r['dur'] for r in pr),1),'words',sum(r['words'] for r in pr),'LUFS',min(r['lufs'] for r in pr),max(r['lufs'] for r in pr),'wpm_final',min(r['wpm_final'] for r in pr),max(r['wpm_final'] for r in pr),'tempo clamp 0.8 paras',[r['id'] for r in pr if r['tempo']<=0.801])
if os.path.exists('logs/gpu_log.csv'):
    rows=list(csv.DictReader(open('logs/gpu_log.csv')))
    by=collections.defaultdict(list)
    for r in rows: by[r['lane']].append(r)
    for k,v in by.items(): print('GPU',k,len(v),'jobs, avg min',round(sum(float(x['wall_s']) for x in v)/len(v)/60,1),'total h',round(sum(float(x['wall_s']) for x in v)/3600,2),'fails',sum(1 for x in v if x['status']!='OK'))
