import sys,subprocess,os
from PIL import Image,ImageDraw
names=sys.argv[2:]; out=sys.argv[1]
W,H=480,270; im=Image.new('RGB',(W*4,H*((len(names)+1)//2)))
d=ImageDraw.Draw(im)
for i,n in enumerate(names):
    p=f'broll/clips/{n}.mp4'
    dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p],capture_output=True,text=True).stdout)
    for k,t in enumerate((0.3,dur*0.9)):
        subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',f'{t:.2f}','-i',p,'-frames:v','1','-vf',f'scale={W}:{H}','/tmp/ck/_c.png'],check=True)
        x=((i%2)*2+k)*W; y=(i//2)*H; im.paste(Image.open('/tmp/ck/_c.png'),(x,y)); d.text((x+4,y+2),f'{n} t={t:.1f}',fill='yellow')
im.save(out,quality=80)
