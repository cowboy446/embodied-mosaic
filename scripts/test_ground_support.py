import unittest
from types import SimpleNamespace
from ground_support import GroundSupport
class Query:
 def __init__(self,ground):self.ground=ground
 def raycast_all(self,origin,direction,distance,callback):
  callback(SimpleNamespace(rigid_body='/Robot/foot',position=(0,0,0),normal=(0,0,1)))
  if self.ground(origin):callback(SimpleNamespace(rigid_body='/Floor',position=(origin[0],origin[1],0),normal=(0,0,1)))
class SupportTests(unittest.TestCase):
 def test_robot_is_not_ground(self):self.assertFalse(GroundSupport(Query(lambda p:False),'/Robot').supported((0,0)))
 def test_corner_over_hole_rejected(self):self.assertFalse(GroundSupport(Query(lambda p:p[0]<.2),'/Robot').supported((0,0)))
 def test_supported_flat_floor(self):self.assertTrue(GroundSupport(Query(lambda p:True),'/Robot').supported((0,0)))
if __name__=='__main__':unittest.main()
