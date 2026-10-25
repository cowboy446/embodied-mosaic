"""Heading-aware rule planner with explicit translation and rotation validation.

The callbacks are private geometry services. `motion_free` must validate the entire
swept motion, not only its endpoints. A plan is not physical tracking acceptance.
"""
from collections import deque
import math


def plan_pose_grid(start, goal, pose_free, motion_free, *, bounds, resolution=.1,
                   max_expansions=200000):
    """Plan (x,y,yaw) states on a four-heading lattice to an explicit XY goal.

    A robot may enter a narrow passage while facing along it. Turning is a
    separate action and must pass its own swept-envelope check. Initial yaw must
    match the lattice; silently rounding a physical orientation is forbidden.
    """
    if len(start)!=3 or len(goal)!=2 or len(bounds)!=4:
        raise ValueError('invalid pose, goal, or bounds shape')
    if not all(math.isfinite(v) for v in (*start,*goal,*bounds,resolution)) or resolution<=0:
        raise ValueError('nonfinite or invalid planner inputs')
    xmin,ymin,xmax,ymax=bounds
    if xmax<=xmin or ymax<=ymin or max_expansions<1:
        raise ValueError('invalid bounds or search budget')
    yaw_index=round(start[2]/(math.pi/2))
    if abs(math.remainder(start[2]-yaw_index*math.pi/2,2*math.pi))>1e-6:
        raise ValueError('initial yaw must align to heading lattice')
    # Anchor lattice at the actual start, preserving its physical position.
    def pose(state):
        i,j,h=state
        return (start[0]+i*resolution,start[1]+j*resolution,h*math.pi/2)
    def in_bounds(p):return xmin<=p[0]<=xmax and ymin<=p[1]<=ymax
    target=(round((goal[0]-start[0])/resolution),round((goal[1]-start[1])/resolution))
    snapped=pose((*target,0))[:2]
    if math.dist(snapped,goal)>1e-6:
        raise ValueError('goal must align to start-anchored grid')
    initial=(0,0,yaw_index%4)
    if not in_bounds(start) or not in_bounds((*goal,0)) or not pose_free(pose(initial)):
        raise ValueError('invalid start or goal region')
    queue=deque([initial]);parent={initial:None};action={};expanded=0
    directions=((1,0),(0,1),(-1,0),(0,-1))
    while queue:
        current=queue.popleft();expanded+=1
        if expanded>max_expansions:raise ValueError('search budget exhausted')
        if current[:2]==target:
            chain=[];c=current
            while c is not None:chain.append(c);c=parent[c]
            chain.reverse()
            return {'poses':[pose(c) for c in chain],
                    'actions':[action[c] for c in chain[1:]],
                    'expanded_states':expanded,'resolution_m':resolution,
                    'scope':'heading-aware geometric plan; controller tracking not certified'}
        i,j,h=current;dx,dy=directions[h]
        successors=[((i+dx,j+dy,h),'forward'),((i,j,(h+1)%4),'turn_left'),((i,j,(h-1)%4),'turn_right')]
        for nxt,kind in successors:
            p=pose(nxt)
            if nxt in parent or not in_bounds(p) or not pose_free(p):continue
            if not motion_free(pose(current),p,kind):continue
            parent[nxt]=current;action[nxt]=kind;queue.append(nxt)
    raise ValueError('no collision-free pose route')
