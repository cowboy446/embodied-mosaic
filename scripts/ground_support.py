"""Flat-floor support veto for the current G1 navigation adapter.
Five downward probes sample the support footprint; this is not a mesh coverage proof.
"""
import math
class GroundSupport:
 def __init__(self,query,own_root,ground_z=0.,half_width=.3,tolerance=.03):
  self.query=query;self.own_root=own_root.rstrip('/');self.z=ground_z;self.half=half_width;self.tolerance=tolerance;self.cache={}
 def supported(self,xy):
  if len(xy)!=2 or any(not math.isfinite(float(v)) for v in xy):raise ValueError('invalid support position')
  key=tuple(float(v) for v in xy)
  if key in self.cache:return self.cache[key]
  h=self.half
  for dx,dy in [(0,0),(-h,-h),(-h,h),(h,-h),(h,h)]:
   hits=[]
   def report(hit):
    path=str(hit.rigid_body)
    if path==self.own_root or path.startswith(self.own_root+'/'):return True
    hits.append((float(hit.position[2]),float(hit.normal[2])))
    return True
   self.query.raycast_all((key[0]+dx,key[1]+dy,self.z+.25),(0.,0.,-1.),.5,report)
   if not any(abs(z-self.z)<=self.tolerance and nz>=.95 for z,nz in hits):
    self.cache[key]=False;return False
  self.cache[key]=True;return True
