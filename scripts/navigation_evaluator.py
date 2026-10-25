"""Private navigation acceptance. Never serialize this state into policy observations."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class NavigationCriterion:
 target_xy: tuple
 minimum_distance_m: float = .45
 maximum_distance_m: float = .85
 maximum_speed_m_s: float = .03
 settling_s: float = .3

 def __post_init__(self):
  values=(*self.target_xy,self.minimum_distance_m,self.maximum_distance_m,self.maximum_speed_m_s,self.settling_s)
  if len(self.target_xy)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('invalid criterion')
  if not 0<=self.minimum_distance_m<self.maximum_distance_m or self.maximum_speed_m_s<=0 or self.settling_s<=0:raise ValueError('invalid criterion bounds')

 def evaluate(self, termination, samples, *, collision_detected, safety_certified):
  result={'success':False,'task_success':False,'safety_certified':bool(safety_certified),'termination':termination}
  if termination!='agent_finish':return dict(result,reason='agent_did_not_finish')
  if collision_detected:return dict(result,reason='collision')
  if len(samples)<2:return dict(result,reason='insufficient_samples')
  try:
   ts=[s['sim_time'] for s in samples];xy=[s['position'][:2] for s in samples]
   if any(not math.isfinite(v) for v in ts) or any(len(p)!=2 or any(not math.isfinite(v) for v in p) for p in xy):raise ValueError()
   if any(b<=a for a,b in zip(ts,ts[1:])):raise ValueError()
  except (KeyError,TypeError,ValueError):return dict(result,reason='invalid_samples')
  start=next((i for i,t in enumerate(ts) if t>=ts[-1]-self.settling_s-1e-8),None)
  if start is None or ts[-1]-ts[start]<self.settling_s-1e-8:return dict(result,reason='insufficient_settling_window')
  distances=[math.dist(p,self.target_xy) for p in xy[start:]]
  speeds=[math.dist(xy[i],xy[i-1])/(ts[i]-ts[i-1]) for i in range(start+1,len(ts))]
  result.update(final_distance_m=distances[-1],maximum_settling_speed_m_s=max(speeds,default=float('inf')))
  task_ok=all(self.minimum_distance_m<=d<=self.maximum_distance_m for d in distances) and all(v<=self.maximum_speed_m_s for v in speeds)
  result.update(task_success=task_ok,success=task_ok and safety_certified,reason='passed' if task_ok and safety_certified else ('task_reached_safety_unverified' if task_ok else 'outside_target_or_not_settled'))
  return result
