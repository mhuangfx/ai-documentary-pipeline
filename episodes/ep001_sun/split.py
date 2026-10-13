import re,json,math
txt=open('script_v1.txt').read()
items=[];pid=0;chapter=None
blocks=[b.strip() for b in re.split(r'\n\s*\n',txt) if b.strip()]
for b in blocks:
    m=re.match(r'\[CHAPTER (.+)\]$',b)
    if m: chapter=m.group(1); items.append({'type':'chapter','title':chapter}); continue
    if b.startswith('[HOST]'):
        t=b[6:].strip(); w=len(t.split())
        items.append({'type':'host','id':'H%02d'%(sum(1 for i in items if i['type']=='host')+1),'text':t,'words':w,'secs':max(4,math.ceil(w/3.0+1.0)),'chapter':chapter}); continue
    # narration, may contain [BEAT]
    parts=[p.strip() for p in re.split(r'\[BEAT\]',b)]
    items.append({'type':'nar','id':'N%02d'%(sum(1 for i in items if i['type']=='nar')+1),'parts':parts,'text':b,'words':len(b.replace('[BEAT]','').split()),'chapter':chapter})
json.dump(items,open('script_items.json','w'),indent=1)
h=[i for i in items if i['type']=='host']
print(len(h),'host',sum(i['secs'] for i in h),'s',sum(i['words'] for i in h),'words')
n=[i for i in items if i['type']=='nar'];print(len(n),'nar paras',sum(i['words'] for i in n),'words')
for i in h: print(i['id'],i['words'],i['secs'],i['text'][:70])
