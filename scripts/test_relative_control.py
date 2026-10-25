import unittest,math
from relative_control import feedback
class ControlTests(unittest.TestCase):
 def test_wrap_boundary(self):
  p=(0,0,math.radians(179));v,w,s=feedback('turn',5,p,(0,0,math.radians(-178)),.2)
  self.assertGreater(w,0);self.assertLess(w,.2)
 def test_relative_heading(self):
  v,w,s=feedback('move_forward',.2,(1,1,math.pi/2),(1,1.198,math.pi/2),1)
  self.assertEqual(s,'reached');self.assertEqual(v,0)
 def test_safety_deviation_timeout(self):
  self.assertEqual(feedback('move_forward',.2,(0,0,0),(0,.1,0),1)[2],'lateral_deviation')
  self.assertEqual(feedback('turn',45,(0,0,0),(0,0,0),12)[2],'timeout')
if __name__=='__main__':unittest.main()
