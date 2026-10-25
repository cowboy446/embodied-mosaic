import unittest
from grid_navigation import plan_grid
class GridTests(unittest.TestCase):
 def test_route_avoids_wall(self):
  blocked=lambda p: abs(p[0]-1)<.2 and p[1]<1
  a=plan_grid((0,0,0),blocked,seed=5,radius=3,minimum_path=4,maximum_path=5)
  self.assertEqual(a,plan_grid((0,0,0),blocked,seed=5,radius=3,minimum_path=4,maximum_path=5))
  for p,q in zip(a['route'],a['route'][1:]):
   for i in range(101):self.assertFalse(blocked((p[0]+(q[0]-p[0])*i/100,p[1]+(q[1]-p[1])*i/100)))
 def test_unreachable_goal_rejected(self):
  with self.assertRaises(ValueError):plan_grid((0,0,0),lambda p:abs(p[0])>.1 or abs(p[1])>.1)
if __name__=='__main__':unittest.main()
