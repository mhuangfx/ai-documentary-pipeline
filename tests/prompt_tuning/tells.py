"""Count AI tells (tools/prompts/ai_tells.txt) + colons + contractions in an output file."""
import sys, re, pathlib
root = pathlib.Path(__file__).resolve().parents[2]
pats, cat = [], ''
for l in (root/'tools/prompts/ai_tells.txt').read_text().splitlines():
    if l.startswith('#'): cat = l.lstrip('# ').strip(); continue
    if l.strip(): pats.append((cat, l.strip()))
for f in sys.argv[1:]:
    t = pathlib.Path(f).read_text(); words = len(t.split())
    hits = [(c, m.group(0)) for c, p in pats for m in re.finditer(p, t, re.I | re.M)]
    contr = len(re.findall(r"\b\w+'(s|re|ve|ll|d|t|m)\b", t))
    print(f'{f}: words={words} colons={t.count(":")} contractions={contr} tells={len(hits)}')
    for c, h in hits: print(f'   [{c}] {h!r}')
