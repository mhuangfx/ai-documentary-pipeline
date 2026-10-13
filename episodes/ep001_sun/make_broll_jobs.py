import json,os,math,sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sl=json.load(open('shotlist.json'))['shots']
TURBO=os.environ.get('TURBO','1')=='1'
LORA='minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors'
STYLE='Live-action documentary footage, photographic realism, preserving every detail of the reference photograph exactly, fine natural grain, not an illustration, not CG. '
PH={
 'P01':('The photograph shows a magenta and pink aurora glowing over a line of silhouetted palm trees under a starry night sky. The aurora slowly shimmers and its curtains drift gently; the palms stay still. The camera pushes in with small amplitude at slow speed.','Soft night ambience, a faint warm breeze through palm leaves, distant crickets.'),
 'P02':('The photograph shows a red and pink aurora rising over a dark desert horizon with faint town lights. The red pillars of light shift and pulse slowly. The camera drifts slowly to the right with small amplitude.','Quiet night air, a faint distant dog bark, soft wind.'),
 'P04':('The photograph shows a magenta aurora filling the whole night sky. The rays slowly ripple and shift. The camera pushes in with small amplitude at slow speed.','Deep quiet night silence with a very faint wind.'),
 'P07':('The photograph shows tall steel high-voltage transmission pylons and power lines crossing a snowy winter landscape at dusk. Thin snow blows lightly across the ground; the lines hang still. The camera trucks slowly left with small amplitude.','Cold wind over snow and a faint electrical hum.'),
 'P06':('The photograph shows a night sky full of long star trails and straight bright satellite streaks above a dark horizon with an orange glow. The stars wheel very slowly. The camera holds almost still with a very slow push in.','Quiet night wind.'),
 'P13':('The photograph shows a large rocket lifting off from a launch pad on a column of bright flame and billowing white smoke. The smoke rolls outward and the rocket rises slowly. The camera tilts up slowly with small amplitude.','A deep rolling rocket roar and crackle.'),
 'P03':('The photograph shows a faint pink aurora glow low over a dark silhouetted hillside with a pine tree under a starry sky. Stars twinkle softly. The camera pushes in with small amplitude at slow speed.','Quiet night wind.'),
}
TV={
 'dough':('Live-action documentary cinematography, photographic realism, shot on a 50mm macro lens, warm morning window light in a home kitchen, real flour dusting and dough texture, fine film grain, not an illustration, not CG. A smooth ball of bread dough sits in a clear glass bowl on a wooden counter by a sunny window; over the length of the shot the dough slowly swells and domes up above the rim of the bowl. The camera pushes in slowly with small amplitude. No cuts: the entire video is a single unbroken shot.','A quiet warm kitchen, a faint clock tick.'),
 'seasons':('Live-action documentary time-lapse cinematography, photographic realism, shot on a 24mm lens, a single large oak tree on a grassy hill under moving clouds. Over the length of the shot the green summer leaves turn gold and fall, the hill browns, and snow settles over bare branches; clouds race across the sky. The camera holds locked off. No cuts: the entire video is a single unbroken shot.','Soft wind that grows colder.'),
 'satnav':('Live-action documentary cinematography, photographic realism, shot on a 35mm lens, night. Close shot of a car dashboard navigation screen showing an abstract blue route line on a dark map; the glowing route redraws itself as the car drives along a dark rural road seen through the windshield with passing road lights. The camera holds steady with a very slow push in. No readable text. No cuts: the entire video is a single unbroken shot.','A low engine hum and soft tyre noise on the road.'),
 'magnet':('Live-action documentary cinematography, photographic realism, shot on a 50mm macro lens, soft kitchen light. A small colorful round magnet clings to the door of a white refrigerator holding up a paper note. The camera trucks slowly right with small amplitude. No cuts: the entire video is a single unbroken shot.','A faint refrigerator hum.'),
}
jobs=[]
os.makedirs('broll/prompts',exist_ok=True)
def sec(s): return min(10.0,round(s['dur']+0.5,1))
for s in sl:
    if s['lane']=='PH':
        ref=s['ref']; key={'P06':'P06','P04':'P04'}.get(ref,ref)
        txt,snd=PH[key]
        ffmap={'P01':'P01_aurora_mazatlan','P02':'P02_aurora_phoenix','P04':'P04_aurora_magenta','P07':'P07_hydroquebec_pylons_snow','P06':'P06_alt_starlink','P13':'P13_artemis2_launch','P03':'P03_aurora_gran'}
        ff=os.path.abspath(f'broll/ff/{ffmap[key]}.png'); secs=sec(s)
        align=f'How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video. '
        p=align+'integrated_multimodal_description: [Shot 1] '+STYLE+txt+' No cuts: the entire video is a single unbroken shot.\noverall_soundscape: '+snd+'\nnon_diegetic_music: N/A\n'
        pf=os.path.abspath(f"broll/prompts/{s['id']}.txt"); open(pf,'w').write(p)
        args=['--first-frame',ff]+(['--lora',LORA] if TURBO else [])
        jobs.append(dict(name='b_'+s['id'],lane='PHOTO_H3'+('_turbo' if TURBO else '_20'),prompt_file=pf,secs=secs,seed=770809,steps=4 if TURBO else 20,out_dir=os.path.abspath('broll/clips'),args=args,shot=s['id'],note=s['note']))
    elif s['lane']=='TV':
        txt,snd=TV[s['ref']]; secs=sec(s)
        p='integrated_multimodal_description: [Shot 1] '+txt+'\noverall_soundscape: '+snd+'\nnon_diegetic_music: N/A\n'
        pf=os.path.abspath(f"broll/prompts/{s['id']}.txt"); open(pf,'w').write(p)
        jobs.append(dict(name='b_'+s['id'],lane='H3_T2V',prompt_file=pf,secs=secs,seed=770809,steps=20,out_dir=os.path.abspath('broll/clips'),args=[],shot=s['id'],note=s['note']))
json.dump(jobs,open('broll_jobs_all.json','w'),indent=1)
for j in jobs: print(j['name'],j['lane'],j['secs'],j['note'])
