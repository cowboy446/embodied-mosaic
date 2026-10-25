"""Audit private per-frame state and image alignment; does not certify physics."""
import hashlib,json,math
from pathlib import Path

def audit(directory):
 root=Path(directory);meta=json.loads((root/'replay-metadata.json').read_text());rows=[json.loads(x) for x in (root/'replay-frames.jsonl').read_text().splitlines()]
 if len(rows)<2:raise ValueError('fewer than two frames')
 n=len(meta['joint_names']);m=len(meta['control_joint_indices'])
 for i,r in enumerate(rows):
  if r['frame']!=i:raise ValueError('frame gap')
  for k,length in [('joint_position',n),('joint_velocity',n),('control_velocity_target',m),('position',3),('quaternion_wxyz',4),('linear_velocity',3),('angular_velocity',3)]:
   if len(r[k])!=length or not all(math.isfinite(x) for x in r[k]):raise ValueError('invalid '+k)
  if Path(r['image_file']).name!=r['image_file']:raise ValueError('image path')
  if hashlib.sha256((root/r['image_file']).read_bytes()).hexdigest()!=r['image_sha256']:raise ValueError('image changed')
  if i and (abs(r['sim_time']-rows[i-1]['sim_time']-1/meta['fps'])>1e-6 or r['physics_step']<=rows[i-1]['physics_step']):raise ValueError('clock mismatch')
 return {'status':'passed','frames':len(rows),'joint_names':meta['joint_names'],'duration_s':rows[-1]['sim_time']-rows[0]['sim_time'],'joint_position_ranges':{name:max(r['joint_position'][j] for r in rows)-min(r['joint_position'][j] for r in rows) for j,name in enumerate(meta['joint_names'])},'scope':'recording consistency, not task or collision acceptance'}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('directory');a=p.parse_args();print(json.dumps(audit(a.directory),indent=2))
