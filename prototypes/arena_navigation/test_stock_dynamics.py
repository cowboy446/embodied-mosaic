import unittest
from stock_dynamics import summarize
class DynamicsTests(unittest.TestCase):
 def rows(self,position=0,velocity=0):
  return [{'time_s':i/30,'transforms':[[position if i else 0,0,0,0,0,0,1]],'velocities':[[velocity,0,0,0,0,0]]} for i in range(61)]
 def test_drift_rejected(self):self.assertFalse(summarize(self.rows(.1))['passed'])
 def test_motion_rejected(self):self.assertFalse(summarize(self.rows(0,.1))['passed'])
 def test_static_passes(self):self.assertTrue(summarize(self.rows())['passed'])
 def test_incomplete_rejected(self):self.assertFalse(summarize(self.rows()[:30])['passed'])
 def test_excursion_returning_to_start_rejected(self):
  r=self.rows();r[20]['transforms'][0][0]=.1;self.assertFalse(summarize(r)['passed'])
 def test_tipping_rejected(self):
  r=self.rows();r[20]['transforms'][0][3:]=[0,0,.70710678,.70710678];self.assertFalse(summarize(r)['passed'])
if __name__=='__main__':unittest.main()
