import unittest
from navigation_evaluator import NavigationCriterion
class EvaluationTests(unittest.TestCase):
 def setUp(self):self.c=NavigationCriterion((0.,0.))
 def samples(self):return [{'sim_time':i/30,'position':[.7,0.,.2]} for i in range(12)]
 def evaluate(self,**kw):return self.c.evaluate('agent_finish',self.samples(),collision_detected=False,safety_certified=True,**kw)
 def test_settled_target(self):self.assertTrue(self.evaluate()['success'])
 def test_finish_is_not_success(self):
  s=self.samples();s[-1]['position'][0]=1.5
  self.assertFalse(self.c.evaluate('agent_finish',s,collision_detected=False,safety_certified=True)['success'])
 def test_safety_not_silently_accepted(self):
  r=self.c.evaluate('agent_finish',self.samples(),collision_detected=False,safety_certified=False)
  self.assertTrue(r['task_success']);self.assertFalse(r['success'])
 def test_bad_clock_and_short_history(self):
  for s in [self.samples()[:2],self.samples()+[self.samples()[-1]]]:
   self.assertFalse(self.c.evaluate('agent_finish',s,collision_detected=False,safety_certified=True)['success'])
if __name__=='__main__':unittest.main()
