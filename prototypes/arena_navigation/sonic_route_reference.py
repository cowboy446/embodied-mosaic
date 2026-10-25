"""Waypoint-conditioned SONIC motion planning, separate from physical tracking.
Preserves planned motion context; uses measured position for waypoint feedback. A grid route does not itself certify body clearance.
"""
import numpy as np

class RouteReference:
 def __init__(self,planner_session,route,seed=42,speed=.75,reach_radius=.3):
  self.planner=planner_session;self.route=np.asarray(route,dtype='f4');self.index=1;self.seed=seed;self.calls=0;self.speed=speed;self.radius=reach_radius
  if self.route.ndim!=2 or self.route.shape[1]!=2 or len(self.route)<2 or not np.isfinite(self.route).all():raise ValueError('invalid route')
  if not 0<speed<=1.35:raise ValueError('speed outside initial validation range')
 def generate(self,context,measured_xy=None):
  context=np.asarray(context,dtype='f4')
  if context.shape!=(4,36) or not np.isfinite(context).all():raise ValueError('expected four measured 36D qpos samples')
  pos=context[-1,:2] if measured_xy is None else np.asarray(measured_xy,dtype='f4')
  if pos.shape!=(2,) or not np.isfinite(pos).all():raise ValueError('invalid measured position')
  while self.index<len(self.route) and np.linalg.norm(self.route[self.index]-pos)<self.radius:self.index+=1
  finished=self.index==len(self.route)
  direction=np.zeros(3,dtype='f4')
  if not finished:
   delta=self.route[self.index]-pos;direction[:2]=delta/np.linalg.norm(delta)
  facing=direction.copy() if not finished else np.array([1,0,0],dtype='f4')
  # Official planner interface, 30 Hz trajectory output; resample separately for tracker.
  inputs={'context_mujoco_qpos':context[None],'target_vel':np.array([-1. if finished else self.speed],'f4'),'mode':np.array([0 if finished else 2],'i8'),'movement_direction':direction[None],'facing_direction':facing[None],'random_seed':np.array([self.seed+self.calls],'i8'),'height':np.array([-1.],'f4'),'has_specific_target':np.zeros((1,1),'i8'),'specific_target_positions':np.zeros((1,4,3),'f4'),'specific_target_headings':np.zeros((1,4),'f4'),'allowed_pred_num_tokens':np.ones((1,11),'i8')}
  predicted,count=self.planner.run(None,inputs);self.calls+=1
  motion=predicted[0,:int(count[0])]
  if motion.ndim!=2 or motion.shape[1]!=36 or len(motion)<4 or not np.isfinite(motion).all():raise ValueError('invalid planner trajectory')
  return motion,{'waypoint_index':self.index,'route_finished':finished,'planner_calls':self.calls,'speed_command_m_s':self.speed if not finished else 0.}
