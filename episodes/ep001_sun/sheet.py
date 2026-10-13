import sys,glob,os
from PIL import Image,ImageDraw
fs=sorted(glob.glob('cards/preview/*.png'))
n=int(sys.argv[1]) if len(sys.argv)>1 else 12
for si in range(0,len(fs),n):
    ch=fs[si:si+n]; cols=3; rows=(len(ch)+2)//3; W,H=640,360
    im=Image.new('RGB',(W*cols,H*rows),'black'); d=ImageDraw.Draw(im)
    for i,f in enumerate(ch):
        x=Image.open(f).resize((W,H)); im.paste(x,((i%cols)*W,(i//cols)*H)); d.text(((i%cols)*W+4,(i//cols)*H+2),os.path.basename(f)[:-4],fill='yellow')
    im.save(f'cards/sheet_{si//n:02d}.jpg',quality=85)
print(len(fs))
