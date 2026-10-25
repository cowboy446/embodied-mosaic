import random,unittest
from placement_support_grid import sample_grid,PlacementDomain
class GridTests(unittest.TestCase):
 def test_hole_and_outside_rejected(self):
  grid=sample_grid([0,0,4,4],lambda p:not(1<p[0]<2 and 1<p[1]<2),resolution=1)
  domain=PlacementDomain(grid)
  self.assertTrue(domain.contains_footprint([.1,.1],[.9,.9]))
  self.assertFalse(domain.contains_footprint([.1,.1],[2.1,2.1]))
  self.assertFalse(domain.contains_footprint([-1,0],[.1,.1]))
  self.assertEqual(domain.sample_center(random.Random(4)),domain.sample_center(random.Random(4)))
 def test_no_ground_and_invalid_budget(self):
  with self.assertRaises(ValueError):PlacementDomain(sample_grid([0,0,1,1],lambda p:False))
  with self.assertRaises(ValueError):sample_grid([0,0,1e6,1e6],lambda p:True)
if __name__=='__main__':unittest.main()
