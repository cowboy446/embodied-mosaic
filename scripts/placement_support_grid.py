"""Sampled flat-ground placement domain; runtime support checks remain mandatory."""
import math


def sample_grid(bounds, supported, resolution=.25):
    if len(bounds)!=4 or not all(math.isfinite(v) for v in bounds) or bounds[0]>=bounds[2] or bounds[1]>=bounds[3] or not math.isfinite(resolution) or resolution<=0:
        raise ValueError('invalid grid domain')
    nx=math.floor((bounds[2]-bounds[0])/resolution);ny=math.floor((bounds[3]-bounds[1])/resolution)
    if nx<1 or ny<1 or nx*ny>100000:raise ValueError('grid outside sample budget')
    cells=[]
    for i in range(nx):
        for j in range(ny):
            x=bounds[0]+(i+.5)*resolution;y=bounds[1]+(j+.5)*resolution
            if supported((x,y)):cells.append([i,j])
    return {'origin':list(bounds[:2]),'resolution_m':resolution,'shape':[nx,ny],'supported_cells':cells,
            'scope':'sampled support only; cell interiors and collisions require runtime validation'}


class PlacementDomain:
    def __init__(self, data):
        self.origin=data['origin'];self.resolution=data['resolution_m'];self.shape=data['shape']
        if len(self.origin)!=2 or not all(math.isfinite(x) for x in self.origin) or not math.isfinite(self.resolution) or self.resolution<=0 or len(self.shape)!=2 or any(type(x)!=int or x<1 for x in self.shape):raise ValueError('invalid grid metadata')
        self.cells={tuple(c) for c in data['supported_cells']}
        if not self.cells or any(len(c)!=2 or any(type(v)!=int for v in c) or not(0<=c[0]<self.shape[0] and 0<=c[1]<self.shape[1]) for c in self.cells):raise ValueError('invalid supported cells')
        self.ordered=sorted(self.cells)
    def sample_center(self,rng):
        c=rng.choice(self.ordered)
        return [self.origin[i]+(c[i]+rng.random())*self.resolution for i in (0,1)]
    def contains_footprint(self,lo,hi):
        if any(not math.isfinite(v) for v in [*lo[:2],*hi[:2]]) or any(lo[i]>hi[i] for i in (0,1)):return False
        indices=[(math.floor((lo[i]-self.origin[i])/self.resolution),math.floor((hi[i]-self.origin[i])/self.resolution)) for i in (0,1)]
        if any(a<0 or b>=self.shape[i] for i,(a,b) in enumerate(indices)):return False
        return all((x,y) in self.cells for x in range(indices[0][0],indices[0][1]+1) for y in range(indices[1][0],indices[1][1]+1))
