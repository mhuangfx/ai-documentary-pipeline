import json,os,multiprocessing as mp
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from cards_spec import CARDS
import cardlib
sl=json.load(open('shotlist.json'))['shots']
jobs=[(s['id'],s['ref'],s['dur']) for s in sl if s['lane']=='DG']
def go(j):
    sid,ref,dur=j; out=f'cards/clips/{sid}__{ref}.mp4'
    if os.path.exists(out) and os.path.getsize(out)>2000 and os.path.exists(out+'.dur') and abs(float(open(out+'.dur').read())-dur)<0.01: return sid,'cached'
    try:
        cardlib.render_card(CARDS[ref],dur,out); open(out+'.dur','w').write(str(dur)); return sid,'ok'
    except Exception as e: return sid,repr(e)
if __name__=='__main__':
    with mp.Pool(20) as p:
        r=p.map(go,jobs)
    print([x for x in r if x[1] not in('ok','cached')], len(r))
