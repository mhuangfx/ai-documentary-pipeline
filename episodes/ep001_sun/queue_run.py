#!/usr/bin/env python3
"""Sequential H3 queue. Re-reads queue_jobs.json every loop; runs first job without a result. Stops starting jobs at 07:30."""
import json,os,subprocess,time,datetime,sys,csv
os.chdir(os.path.dirname(os.path.abspath(__file__)))
# The local video-model runner is withheld (see host/README.md). Point HOST_RUNNER at your own.
H3=os.environ.get('HOST_RUNNER','withheld_host_runner.py')
FS=os.environ.get('RUNNER_DIR','.')
CLAIM=os.path.abspath('gpu_claim.sh')  # one GPU job at a time
STOP=datetime.time(7,30)
LOG='logs/gpu_log.csv'
def now(): return datetime.datetime.now()
def past_stop():
    n=now(); return datetime.time(7,30)<=n.time()<datetime.time(20,0)
def done_names():
    if not os.path.exists(LOG): return set()
    return {r['name'] for r in csv.DictReader(open(LOG))}
def log(row):
    new=not os.path.exists(LOG)
    with open(LOG,'a',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['ts','name','lane','seed','steps','secs','wall_s','status','out','note']); 
        if new: w.writeheader()
        w.writerow(row)
def gpu_ok():
    return subprocess.run(['bash','./gpu_free.sh'],capture_output=True,text=True).stdout.strip()==''
def main():
    while True:
        if os.path.exists('QUEUE_STOP'): print('QUEUE_STOP'); return
        if past_stop(): print('past 07:30, no new jobs'); return
        jobs=json.load(open('queue_jobs.json')); dn=done_names()
        todo=[j for j in jobs if j['name'] not in dn]
        if not todo:
            time.sleep(60); continue
        j=todo[0]
        while not gpu_ok():
            print('other GPU proc >4GB, waiting',flush=True); time.sleep(60)
            if past_stop(): return
        out_dir=j['out_dir']; os.makedirs(out_dir,exist_ok=True)
        cmd=[CLAIM,'python3',H3,'--name',j['name'],'--prompt-file',j['prompt_file'],'--width','1344','--height','768',
             '--seconds',str(j['secs']),'--steps',str(j.get('steps',20)),'--seed',str(j['seed']),'--out-dir',out_dir]
        for a in j.get('args',[]): cmd.append(a)
        t=time.time(); print(now(),'START',j['name'],flush=True)
        with open(f"logs/{j['name']}.stdout.log",'w') as lf:
            rc=subprocess.run(cmd,cwd=FS,stdout=lf,stderr=subprocess.STDOUT).returncode
        wall=time.time()-t
        mp4=[f for f in os.listdir(out_dir) if f.startswith(j['name']) and f.endswith('.mp4')]
        ok=rc==0 and bool(mp4)
        log({'ts':now().isoformat(timespec='seconds'),'name':j['name'],'lane':j['lane'],'seed':j['seed'],'steps':j.get('steps',20),'secs':j['secs'],'wall_s':round(wall),'status':'OK' if ok else f'FAIL rc={rc}','out':os.path.join(out_dir,mp4[0]) if mp4 else '','note':j.get('note','')})
        print(now(),'END',j['name'],'OK' if ok else 'FAIL',round(wall),flush=True)
main()
