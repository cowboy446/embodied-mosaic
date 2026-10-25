"""Conservative base envelope queries; private safety veto, never a navigator.
Bounds must enclose the measured robot. Ground support is clipped below bottom_z;
this does not certify contacts, uneven terrain, deformables or articulation motion.
"""
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class Envelope:
 half_length: float
 half_width: float
 bottom_z: float
 top_z: float
 margin: float = .05
 def __post_init__(self):
  if any(not math.isfinite(v) for v in (self.half_length,self.half_width,self.bottom_z,self.top_z,self.margin)) or min(self.half_length,self.half_width)<=0 or self.top_z<=self.bottom_z or self.margin<0:raise ValueError('invalid safety envelope')

class BaseCollisionGuard:
 def __init__(self, query, envelope, own_root):
  self.query=query;self.envelope=envelope;self.own_root=own_root.rstrip('/')
 def blocked(self, xy, yaw, travel_m=0., turning=False):
  if len(xy)!=2 or any(not math.isfinite(v) for v in (*xy,yaw,travel_m)) or travel_m<0:raise ValueError('invalid query')
  e=self.envelope;hx=e.half_length+e.margin;hy=e.half_width+e.margin
  if turning:hx=hy=math.hypot(hx,hy)
  extent=(hx,hy,(e.top_z-e.bottom_z)/2)
  center=(xy[0],xy[1],(e.top_z+e.bottom_z)/2)
  rotation=(0.,0.,math.sin(yaw/2),math.cos(yaw/2));hits=[]
  def report(hit):
   path=str(hit.rigid_body)
   if path!=self.own_root and not path.startswith(self.own_root+'/'):hits.append(path)
   return True
  self.query.overlap_box(extent,center,rotation,report,False)
  if travel_m>0:self.query.sweep_box_all(extent,center,rotation,(math.cos(yaw),math.sin(yaw),0.),travel_m,report,True)
  return bool(hits)
