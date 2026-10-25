"""Coordinator-only SSH bridge. Never provide this file or transport to the policy agent."""
import argparse,base64,json,os,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('action',choices=['fetch','send']);p.add_argument('--run',required=True);p.add_argument('--local',required=True);p.add_argument('--command');a=p.parse_args()
if not a.run.replace('-','').isalnum():raise SystemExit('Invalid run name')
remote='/mnt/nas/zhangrong/embodied-mosaic/runs/'+a.run
helper=pathlib.Path(__file__).resolve().parents[2]/'isaac-rigidtrack-20261023/scripts/remote.py'
if a.action=='fetch':
 code=f'''import pathlib,json,base64
p=pathlib.Path({remote!r});o=json.loads((p/'observation.json').read_text());name=o['image']['file']
assert pathlib.Path(name).name==name and name.endswith('.png')
print(json.dumps({{'observation':o,'rgb':base64.b64encode((p/name).read_bytes()).decode()}}))'''
else:
 command=json.loads(pathlib.Path(a.command).read_text());step=command['observation_id']
 if type(step) is not int or not 0<=step<100:raise SystemExit('Invalid observation index')
 encoded=base64.b64encode(json.dumps(command).encode()).decode()
 code=f'''import pathlib,base64,json
p=pathlib.Path({remote!r});c=json.loads(base64.b64decode({encoded!r}));o=json.loads((p/'observation.json').read_text())
assert c['episode']==o['episode'] and c['observation_id']==o['observation_id']
f=p/'action-{step:03d}.json'
assert not f.exists()
tmp=f.with_suffix('.tmp');tmp.write_text(json.dumps(c));tmp.rename(f)
print('submitted')'''
r=subprocess.run(['python3',str(helper),'node43'],input="python3 - <<'PYREMOTE'\n"+code+"\nPYREMOTE\n",capture_output=True,text=True,env=dict(os.environ,ISAAC_SSH_CONTROL_PATH='/tmp/isaac-rulegen-view-%C'))
if r.returncode:raise SystemExit(r.stderr)
if a.action=='fetch':
 data=json.loads(r.stdout);out=pathlib.Path(a.local);out.mkdir(parents=True,exist_ok=True)
 (out/'observation.json').write_text(json.dumps(data['observation'],indent=2));(out/'rgb.png').write_bytes(base64.b64decode(data['rgb']))
 print(json.dumps(data['observation'],indent=2))
else:print(r.stdout.strip())
