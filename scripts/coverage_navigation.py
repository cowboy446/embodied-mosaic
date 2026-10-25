"""Bounded greedy coverage tour on a static, clearance-checked grid.
Privileged rule baseline, not a visual policy or a guarantee of runtime safety.
"""
import math
import random
from collections import deque


def plan_coverage(start, blocked, seed=0, resolution=.25, radius=15.,
                  minimum_path=15., maximum_path=40., stops=3, minimum_leg=3.):
    values = (resolution, radius, minimum_path, maximum_path, minimum_leg)
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError('positive finite planning limits required')
    if minimum_path > maximum_path or stops < 1 or int(stops) != stops:
        raise ValueError('invalid route budget')
    n = int(radius / resolution)
    if n < 1 or (2*n+1)**2 > 100000:
        raise ValueError('grid size outside bounded planning budget')
    size = 2*n+1
    origin = (start[0]-n*resolution, start[1]-n*resolution)
    def xy(c): return (origin[0]+c[0]*resolution, origin[1]+c[1]*resolution)
    occupied = {(i,j) for i in range(size) for j in range(size) if blocked(xy((i,j)))}
    initial = (n,n)
    if initial in occupied: raise ValueError('spawn lacks clearance')
    edges = {}
    def connected(a,b):
        key = tuple(sorted((a,b)))
        if key not in edges:
            pa,pb = xy(a),xy(b)
            edges[key] = not blocked(((pa[0]+pb[0])/2,(pa[1]+pb[1])/2))
        return edges[key]
    def search(source, budget):
        parents={source:None}; dist={source:0}; q=deque([source])
        while q:
            c=q.popleft()
            if dist[c] >= budget: continue
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                t=(c[0]+dx,c[1]+dy)
                if not (0<=t[0]<size and 0<=t[1]<size) or t in occupied or t in parents: continue
                if not connected(c,t): continue
                parents[t]=c;dist[t]=dist[c]+1;q.append(t)
        return parents,dist
    def chain_to(target,parents):
        result=[]
        while target is not None: result.append(target);target=parents[target]
        return result[::-1]
    chain=[initial];visited={initial};legs=[];rng=random.Random(seed)
    total_budget=math.floor(maximum_path/resolution+1e-9)
    for leg_index in range(stops):
        remaining=total_budget-(len(chain)-1)
        leg_budget=remaining // (stops-leg_index)
        parents,dist=search(chain[-1],leg_budget)
        candidates=[c for c in sorted(dist) if dist[c]*resolution >= minimum_leg and c not in visited]
        if not candidates: break
        # Bound scoring cost. All candidates share the same deterministic seed.
        if len(candidates)>512: candidates=sorted(rng.sample(candidates,512))
        def score(c):
            path=chain_to(c,parents)
            return (len(set(path)-visited), min(math.dist(c,v) for v in visited), dist[c])
        target=max(candidates,key=score);leg=chain_to(target,parents)
        chain.extend(leg[1:]);visited.update(leg)
        legs.append({'target':xy(target),'length_m':dist[target]*resolution})
    length=(len(chain)-1)*resolution
    if length<minimum_path: raise ValueError('coverage tour cannot meet minimum length within constraints')
    corners=[chain[0]]
    for i in range(1,len(chain)-1):
        a,b,c=chain[i-1:i+2]
        if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):corners.append(b)
    corners.append(chain[-1])
    return {'seed':seed,'resolution_m':resolution,'origin':origin,'size':size,
            'occupied':sorted(occupied),'route':[xy(c) for c in corners],
            'path_length_m':length,'unique_route_cells':len(visited),'legs':legs,
            'requested_stops':stops,'algorithm':'bounded greedy new-cell coverage',
            'scope':'static clearance grid; runtime collision and support checks still required'}
