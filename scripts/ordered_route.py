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


def audit_ordered_samples(route, samples, corner_radius=.3, final_radius=.1):
    """Scan saved samples independently of the online waypoint index."""
    OrderedRoute(route, corner_radius, final_radius)  # Validate route contract.
    previous_time=-math.inf
    for row in samples:
        if not math.isfinite(row['time_s']) or row['time_s']<=previous_time:
            raise ValueError('nonmonotonic sample clock')
        previous_time=row['time_s']
        if len(row['position'])<2 or not all(math.isfinite(v) for v in row['position'][:2]):
            raise ValueError('invalid position')
    cursor=0;visits=[]
    for index, waypoint in enumerate(route[1:],1):
        radius=final_radius if index==len(route)-1 else corner_radius
        found=next((j for j in range(cursor,len(samples))
                    if math.dist(samples[j]['position'][:2],waypoint)<radius),None)
        if found is None:
            return {'completed':False,'first_missing_waypoint':index,'visits':visits}
        visits.append({'waypoint_index':index,'sample_index':found,'time_s':samples[found]['time_s']})
        cursor=found
    return {'completed':True,'visits':visits}
