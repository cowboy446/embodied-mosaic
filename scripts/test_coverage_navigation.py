import unittest
from coverage_navigation import plan_coverage

class CoveragePlanTests(unittest.TestCase):
    def test_deterministic_budget_and_collision(self):
        blocked=lambda p: abs(p[0]-1)<.2 and p[1]<1
        args=dict(seed=9,radius=3,minimum_path=8,maximum_path=14,minimum_leg=2,stops=3)
        a=plan_coverage((0,0),blocked,**args)
        self.assertEqual(a,plan_coverage((0,0),blocked,**args))
        self.assertGreaterEqual(a['path_length_m'],8)
        self.assertLessEqual(a['path_length_m'],14)
        self.assertGreater(a['unique_route_cells'],30)
        self.assertEqual(len(a['legs']),3)
        for p,q in zip(a['route'],a['route'][1:]):
            for i in range(101):
                self.assertFalse(blocked((p[0]+(q[0]-p[0])*i/100,p[1]+(q[1]-p[1])*i/100)))
    def test_infeasible_and_excessive_grid(self):
        with self.assertRaises(ValueError): plan_coverage((0,0),lambda p:abs(p[0])>.1 or abs(p[1])>.1,radius=2)
        with self.assertRaises(ValueError): plan_coverage((0,0),lambda p:False,radius=1000)
    def test_midpoint_barrier(self):
        # Nodes are free, but every edge crossing x=.125 must still be rejected.
        p=plan_coverage((0,0),lambda p:abs(p[0]-.125)<.01,radius=2,minimum_path=4,maximum_path=6,minimum_leg=1)
        self.assertTrue(all(x<=0 for x,y in p['route']))

if __name__=='__main__':unittest.main()
