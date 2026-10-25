"""Private relative-motion feedback; never uses a task goal or planned route."""
import math

def wrap(angle):
 return math.atan2(math.sin(angle), math.cos(angle))

def feedback(skill, value, origin, pose, elapsed, timeout=12.0):
 """Return (linear m/s, angular rad/s, result). Poses are x,y,yaw.
 These private measurements are for execution only, never agent observations.
 Caller must additionally enforce contact/clearance stops and settling checks.
 """
 if not all(math.isfinite(v) for v in (*origin,*pose,value,elapsed,timeout)):
  raise ValueError('nonfinite control state')
 if elapsed>=timeout:return 0.,0.,'timeout'
 if skill=='turn':
  err=wrap(origin[2]+math.radians(value)-pose[2])
  if abs(err)<math.radians(1.):return 0.,0.,'reached'
  return 0.,max(-.55,min(.55,2.5*err)),'running'
 if skill=='move_forward':
  dx,dy=pose[0]-origin[0],pose[1]-origin[1]
  progress=dx*math.cos(origin[2])+dy*math.sin(origin[2])
  lateral=-dx*math.sin(origin[2])+dy*math.cos(origin[2])
  if abs(lateral)>.08:return 0.,0.,'lateral_deviation'
  remaining=value-progress
  if remaining<.008:return 0.,0.,'reached'
  return min(.18,max(.025,.8*remaining)),max(-.4,min(.4,3*wrap(origin[2]-pose[2]))),'running'
 if skill=='wait':return 0.,0.,'reached' if elapsed>=value else 'running'
 raise ValueError('unsupported relative skill')
