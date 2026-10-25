"""Offline navigation/recording audit; does not certify all contacts or geometry."""
import json,math,sys
from pathlib import Path
from PIL import Image,ImageStat
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from navigation_evaluator import NavigationCriterion
from ordered_route import audit_ordered_samples
from trajectory_coverage import measure

def audit(root):
 root=Path(root);report=json.loads((root/'report.json').read_text());plan=json.loads((root/'grid-plan.json').read_text())
 rows=report.get('states',[])
 samples=[{'sim_time':r['time_s'],'position':r['position']} for r in rows]
 criterion=NavigationCriterion(tuple(plan['route'][-1]),minimum_distance_m=0.,maximum_distance_m=.15)
 result=criterion.evaluate('agent_finish' if report['status']=='task_success' else report['status'],samples,collision_detected=False,safety_certified=False)
 ordered=audit_ordered_samples(plan['route'],rows)
 result['ordered_route_audit']=ordered
 if not ordered['completed']:
  result.update(task_success=False,success=False,reason='ordered_route_incomplete')
 if rows:result['trajectory_coverage']=measure(rows)
 image_quality=[]
 capture=json.loads((root/'capture.json').read_text());frames=capture['frames'];errors=[]
 for i,r in enumerate(frames):
  if not (root/r['image']).is_file():errors.append('missing image')
  else:
   with Image.open(root/r['image']) as image:
    if image.size!=(640,480):errors.append('incorrect image dimensions')
    gray=image.convert('L');hist=gray.histogram();black_fraction=sum(hist[:4])/(image.width*image.height)
    image_quality.append({'frame':i,'black_fraction':black_fraction,'luma_std':ImageStat.Stat(gray).stddev[0]})
    if black_fraction>.95:errors.append('almost entirely black frame')
  if i and abs(r['time_s']-frames[i-1]['time_s']-1/30)>1e-6:errors.append('frame clock discontinuity')
  if len(r['joint_position'])!=len(report['joint_names']) or len(r['joint_velocity'])!=len(report['joint_names']):errors.append('incomplete joint state')
 if report['status']=='task_success' and not report.get('terminal_state',{}).get('automatic_reset_suppressed'):errors.append('terminal state preservation not confirmed')
 result['termination']=report['status']
 if rows:
  distances=[math.dist(r['position'][:2],plan['route'][-1]) for r in rows]
  result.update(minimum_goal_distance_m=min(distances),final_goal_distance_m=distances[-1])
 if report['status']!='task_success':result['reason']='episode_ended_without_task_success'
 result.update(image_quality={'max_black_fraction':max((x['black_fraction'] for x in image_quality),default=None),'black_frames':[x['frame'] for x in image_quality if x['black_fraction']>.95]},recording_errors=sorted(set(errors)),frames=len(frames),terminal_state=report.get('terminal_state'),scope='distance/settling and recording consistency only; full collision and material acceptance still required')
 return result
if __name__=='__main__':print(json.dumps(audit(sys.argv[1]),indent=2))
