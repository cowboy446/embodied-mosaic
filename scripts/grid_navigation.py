"""Rule-policy baseline: conservative occupancy, seeded reachable goal, BFS route.
Uses simulator state intentionally; it is not a visual agent evaluation.
"""
import math,random
from collections import deque

def plan_grid(start, blocked, seed=0, resolution=.25, radius=5., minimum_path=4., maximum_path=8., prefer_far=False):
 n=int(radius/resolution);origin=(start[0]-n*resolution,start[1]-n*resolution);size=2*n+1
 def xy(c):return (origin[0]+c[0]*resolution,origin[1]+c[1]*resolution)
 occupied={(i,j) for i in range(size) for j in range(size) if blocked(xy((i,j)))}
 initial=(n,n)
 if initial in occupied:raise ValueError('spawn lacks full turning clearance')
 parents={initial:None};distance={initial:0};q=deque([initial])
 while q:
  c=q.popleft()
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
   t=(c[0]+dx,c[1]+dy)
   if not(0<=t[0]<size and 0<=t[1]<size) or t in occupied or t in parents:continue
   # Check the connecting midpoint as well as both footprint-expanded cells.
   a,b=xy(c),xy(t)
   if blocked(((a[0]+b[0])/2,(a[1]+b[1])/2)):continue
   parents[t]=c;distance[t]=distance[c]+resolution;q.append(t)
 candidates=sorted(c for c,d in distance.items() if minimum_path<=d<=maximum_path)
 if not candidates:raise ValueError('no reachable goal within requested path length')
 if prefer_far:
  farthest=max(distance[c] for c in candidates);candidates=[c for c in candidates if distance[c]>=.9*farthest]
 target=random.Random(seed).choice(candidates);chain=[];c=target
 while c is not None:chain.append(c);c=parents[c]
 chain.reverse()
 # Preserve corners, remove only collinear intermediate cells.
 corners=[chain[0]]
 for i in range(1,len(chain)-1):
  a,b,c=chain[i-1:i+2]
  if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):corners.append(b)
 corners.append(chain[-1])
 return {'seed':seed,'resolution_m':resolution,'origin':origin,'size':size,'occupied':sorted(occupied),'route':[xy(c) for c in corners],'path_length_m':distance[target],'scope':'static flat-ground grid with conservative turning envelope; runtime sweep still required'}

class GridPolicy:
 def __init__(self,route):self.route=route;self.index=1
 def action(self,pose):
  while self.index<len(self.route):
   target=self.route[self.index];dx,dy=target[0]-pose[0],target[1]-pose[1];d=math.hypot(dx,dy)
   if d<.06:self.index+=1;continue
   error=math.atan2(math.sin(math.atan2(dy,dx)-pose[2]),math.cos(math.atan2(dy,dx)-pose[2]))
   if abs(error)>math.radians(3):return 'turn',{'angle_deg':max(-90.,min(90.,math.degrees(error)))}
   return 'move_forward',{'distance_m':max(.05,min(.5,d))}
  return 'finish',{}
