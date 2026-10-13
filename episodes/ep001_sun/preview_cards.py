import sys,multiprocessing as mp
from cards_spec import CARDS
import cardlib,numpy as np
from PIL import Image
def one(k):
    try:
        a=cardlib.frame_rgb(CARDS[k],1.0); Image.fromarray(a).resize((960,540)).save(f'cards/preview/{k}.png'); return k,None
    except Exception as e: return k,repr(e)
if __name__=='__main__':
    keys=sys.argv[1:] or list(CARDS)
    with mp.Pool(24) as p:
        for k,e in p.imap_unordered(one,keys):
            if e: print('ERR',k,e)
