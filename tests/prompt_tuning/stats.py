import re,sys
for f in sys.argv[1:]:
    t=open(f).read(); i=t.find("I'm [HOST]"); pre=t[:i].replace('[HOST]','').replace('[BEAT]','')
    s1=re.split(r'(?<=[.?!])\s',pre.strip())[0]
    sents=[x for x in re.split(r'(?<=[.?!])\s+',t.replace('[HOST]','').replace('[BEAT]','')) if x.strip()]
    lens=sorted(len(x.split()) for x in sents)
    print(f"{f}: pre-ident={len(pre.split())} s1={len(s1.split())} median_sent={lens[len(lens)//2]} total={len(t.split())}")
