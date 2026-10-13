"""Structure stats for a full-episode output: length, opening, chapters, host lines, density."""
import re, sys
AWE = r'\b(staggering|astonishing|incredible|stunning|beautiful|breathtaking|impossible|extraordinary|unbelievable|mind-?blowing|terrifying|enormous|vast|immense)\b'
RECAP = r"\b(so far we|we've (seen|learned)|to recap|in summary|in conclusion|so what (have|did) we learn|let's recap)\b"
for f in sys.argv[1:]:
    t = open(f).read(); W = len(t.split())
    i = t.find("I'm [HOST] and this is"); pre = t[:i].replace('[HOST]', '').replace('[BEAT]', '') if i >= 0 else ''
    chs = [(m.start(), m.group(1)) for m in re.finditer(r'\[CHAPTER ([^\]]+)\]', t)]
    host = [l.strip()[6:].strip() for l in t.splitlines() if l.strip().startswith('[HOST]')]
    clean = re.sub(r'\[[^\]]*\]', '', t)
    sents = [s for s in re.split(r'(?<=[.?!])\s+', clean) if s.strip()]
    L = sorted(len(s.split()) for s in sents)
    you = len(re.findall(r"\byou(r|'re|'ll|'d|'ve)?\b", clean, re.I)); awe = len(re.findall(AWE, clean, re.I))
    nums = len(re.findall(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|percent|\d+)\b', clean, re.I))
    q = clean.count('?'); imag = len(re.findall(r'\b(imagine|picture)\b', clean, re.I))
    print(f'{f}\n  words={W} (~{W/182:.1f} min @182wpm, {W/150:.1f} @150) pre-ident={len(pre.split())} sentences={len(sents)} median_sent={L[len(L)//2]} max_sent={L[-1]} over25={sum(x>25 for x in L)}')
    print(f'  chapters={len(chs)} host_lines={len(host)} host_len={[len(h.split()) for h in host]}')
    print(f'  per1000: you={1000*you/W:.1f} awe={1000*awe/W:.1f} numberwords~{1000*nums/W:.1f} questions={1000*q/W:.1f} imagine/picture={imag} recap_hits={len(re.findall(RECAP, clean, re.I))}')
    for p, n in chs: print(f'   {100*len(t[:p].split())/W:5.1f}%  {n}')
    print('  last 2 lines:', ' | '.join([l for l in t.strip().splitlines() if l.strip()][-2:])[:400])
