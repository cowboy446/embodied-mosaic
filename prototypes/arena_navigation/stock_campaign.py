"""Bounded multi-scene initialization trials, with separate navigation outcomes.
Run on node43; every simulator is a foreground child holding the shared GPU lock.
No retry on unknown launcher/runtime errors. Existing output is never overwritten.
"""
import argparse,json,os,subprocess,time,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


def classify(root,returncode):
    root=Path(root)
    report_path=root/'report.json';stock_path=root/'stock-initialization.json'
    if not report_path.exists():return {'decision':'stop_error','reason':'missing_terminal_report','returncode':returncode}
    report=json.loads(report_path.read_text())
    stock=json.loads(stock_path.read_text()) if stock_path.exists() else None
    rejected_path=root/'stock-randomization-rejected.json'
    if report.get('status')=='failed' and report.get('phase')=='asset_preparation' and rejected_path.exists():
        rejected=json.loads(rejected_path.read_text())
        failed=rejected.get('failed_object');attempts=[r for r in rejected.get('attempts',[]) if r.get('path')==failed]
        limit=rejected.get('max_trials_per_object')
        if failed and isinstance(limit,int) and limit>0 and len(attempts)==limit and all(r.get('conflicts') for r in attempts):
            return {'decision':'retry_layout','initial_geometry_passed':False,'reason':'bounded_placement_exhausted',
                    'rejected_objects':[failed],'attempt_count':len(attempts),'returncode':returncode}
    if stock and stock['passed']:
        dynamics_path=root/'stock-dynamics.json'
        stability=json.loads(dynamics_path.read_text()).get('summary') if dynamics_path.exists() else None
        if stability is not None and not stability.get('passed',False):
            return {'decision':'stop_stability_failure','initial_geometry_passed':True,'short_stability_passed':False,
                    'stability':stability,'navigation_status':report['status'],'returncode':returncode,'settling_certified':False}
        return {'decision':'stop_layout_pass','initial_geometry_passed':True,'navigation_status':report['status'],
                'phase':report.get('phase'),'returncode':returncode,'settling_certified':False,
                'short_stability_passed':stability.get('passed') if stability else None}
    if stock and not stock['passed'] and report.get('phase')=='stock_initialization':
        return {'decision':'retry_layout','initial_geometry_passed':False,'rejected_objects':[r['path'] for r in stock['objects'] if not r['passed']],'returncode':returncode}
    return {'decision':'stop_error','reason':'non_layout_failure','phase':report.get('phase'),'traceback':report.get('traceback'),'returncode':returncode}


def main():
    p=argparse.ArgumentParser();p.add_argument('--recipes',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    recipes=json.loads(Path(a.recipes).read_text());output=Path(a.output);output.mkdir(parents=True,exist_ok=False)
    lock=threading.Lock();manifest={'started_unix':time.time(),'recipes':recipes,'attempts':[],'scope':'bounded initial geometry trials plus navigation; physical settling not certified'}
    def save():
        tmp=output/'manifest.tmp';tmp.write_text(json.dumps(manifest,indent=2));tmp.replace(output/'manifest.json')
    save();base=Path('/mnt/nas/zhangrong/embodied-mosaic')
    def worker(recipe):
        for trial in recipe['attempts']:
            run_id=trial['run_id'];row={'scene':recipe['scene'],'run_id':run_id,'seed':trial['seed'],'status':'starting','started_unix':time.time()}
            args=['bash',str(base/'prototypes/arena_navigation/launch.sh'),run_id,str(recipe['gpu']),
                  '--route','--seconds','120','--seed',str(trial['seed']),'--spawn-xy',*map(str,recipe['spawn_xy']),
                  '--native-scene-collision','--align-spawn-floor','--random-stock','--scene-name',recipe['scene'],
                  '--scene-source',recipe['source'],'--grid-radius','15','--min-path','8','--max-path','30','--prefer-far']
            with lock:manifest['attempts'].append(row);save()
            proc=subprocess.Popen(args,env={**os.environ,'MOSAIC_FOREGROUND':'1'},stdin=subprocess.DEVNULL)
            with lock:row.update(status='running',pid=proc.pid);save()
            code=proc.wait();result=classify(base/'runs'/run_id,code)
            with lock:row.update(status='terminal',finished_unix=time.time(),result=result);save()
            if result['decision']!='retry_layout':return
    with ThreadPoolExecutor(max_workers=len(recipes)) as pool:list(pool.map(worker,recipes))
    with lock:manifest['finished_unix']=time.time();manifest['status']='finished';save()
if __name__=='__main__':main()
