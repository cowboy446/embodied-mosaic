import unittest
from stock_dynamics import summarize
class DynamicsTests(unittest.TestCase):
 def rows(self,position=0,velocity=0):
  return [{'transforms':[[0,0,0,0,0,0,1]],'velocities':[[0]*6]}, {'transforms':[[position,0,0,0,0,0,1]],'velocities':[[velocity,0,0,0,0,0]]}]
 def test_drift_rejected(self):self.assertFalse(summarize(self.rows(.1))['passed'])
 def test_motion_rejected(self):self.assertFalse(summarize(self.rows(0,.1))['passed'])
 def test_static_passes(self):self.assertTrue(summarize(self.rows())['passed'])
if __name__=='__main__':unittest.main()
