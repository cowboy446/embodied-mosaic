import math,unittest
from pose_grid_navigation import plan_pose_grid
class PoseGridTests(unittest.TestCase):
 def test_narrow_passage_allows_forward_but_not_turn(self):
  # 0.8m-wide channel; 0.9m-long x 0.4m-wide robot fits only along X.
  def pose_free(p):
   lateral=.2 if round(p[2]/(math.pi/2))%2==0 else .45
   return abs(p[1])+lateral<.4
  def motion_free(a,b,kind):return kind=='forward' and pose_free(a) and pose_free(b)
  result=plan_pose_grid((0,0,0),(2,0),pose_free,motion_free,bounds=(-.5,-.5,2.5,.5))
  self.assertEqual(result['actions'],['forward']*20)
 def test_endpoints_do_not_replace_motion_validation(self):
  with self.assertRaisesRegex(ValueError,'no collision-free'):
   plan_pose_grid((0,0,0),(1,0),lambda p:True,lambda a,b,k:False,bounds=(-1,-1,2,1))
 def test_heading_change_is_explicit(self):
  result=plan_pose_grid((0,0,0),(0,1),lambda p:True,lambda a,b,k:True,bounds=(-1,-1,1,1))
  self.assertEqual(result['actions'][0],'turn_left')
  self.assertEqual(result['poses'][-1][:2],(0.,1.))
 def test_unaligned_yaw_rejected(self):
  with self.assertRaisesRegex(ValueError,'yaw'):
   plan_pose_grid((0,0,.3),(1,0),lambda p:True,lambda a,b,k:True,bounds=(-1,-1,2,1))
if __name__=='__main__':unittest.main()
