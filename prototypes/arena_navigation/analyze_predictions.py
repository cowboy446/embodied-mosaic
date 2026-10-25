"""Compare saved SONIC reference chunks with measured rollout, without changing control."""
import argparse,json
from pathlib import Path
import numpy as np

def analyze(root):
 root=Path(root)
 report=json.loads((root/'report.json').read_text())
 states=report['states'];times=np.array([r['time_s'] for r in states]);positions=np.array([r['position'][:2] for r in states])
 goal=np.array(json.loads((root/'grid-plan.json').read_text())['route'][-1])
 rows=[]
 for file in sorted((root/'planner-predictions').glob('*.npz')):
  t=int(file.stem)/150
  with np.load(file) as z:
   motion=z['motion'];context=z['context'];measured=z['measured_xy']
   horizon=min(1.,(len(motion)-1)/30,times[-1]-t)
   if horizon<=0:continue
   observed_end=np.array([np.interp(t+horizon,times,positions[:,i]) for i in range(2)])
   predicted_end=np.array([np.interp(horizon,np.arange(len(motion))/30,motion[:,i]) for i in range(2)])
   rows.append(dict(time_s=t,horizon_s=horizon,goal_distance_m=float(np.linalg.norm(goal-measured)),reference_offset_m=float(np.linalg.norm(context[0,:2]-measured)),predicted_velocity_xy=((predicted_end-motion[0,:2])/horizon).tolist(),measured_velocity_xy=((observed_end-measured)/horizon).tolist(),reference_joint_range_rms_rad=float(np.sqrt(np.mean(np.ptp(motion[:min(31,len(motion)),7:],axis=0)**2)))))
 return dict(status=report['status'],minimum_goal_distance_m=float(np.linalg.norm(positions-goal,axis=1).min()),final_goal_distance_m=float(np.linalg.norm(positions[-1]-goal)),chunks=rows,note='Overlapping prediction horizons can span a later replan; this comparison is diagnostic, not a control or safety certificate.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root');a=p.parse_args();print(json.dumps(analyze(a.root),indent=2))
