"""Private ordered waypoint acceptance from measured robot positions."""
import math

class OrderedRoute:
    def __init__(self, route, corner_radius=.3, final_radius=.1):
        if len(route)<2 or any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in route):
            raise ValueError('finite XY route required')
        if not 0<final_radius<=corner_radius: raise ValueError('invalid radii')
        self.route=route;self.index=1;self.corner_radius=corner_radius;self.final_radius=final_radius
    def update(self, xy):
        if len(xy)!=2 or not all(math.isfinite(v) for v in xy):raise ValueError('invalid measured position')
        while self.index<len(self.route):
            radius=self.final_radius if self.index==len(self.route)-1 else self.corner_radius
            if math.dist(xy,self.route[self.index])>=radius:break
            self.index+=1
        return self.index==len(self.route)
    def summary(self):
        return {'next_waypoint_index':self.index,'waypoint_count':len(self.route),
                'completed':self.index==len(self.route),'corner_radius_m':self.corner_radius,
                'final_radius_m':self.final_radius,'measurement':'robot root XY at environment steps'}
