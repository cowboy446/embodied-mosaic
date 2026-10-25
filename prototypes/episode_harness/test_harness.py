import unittest,json
from harness import Episode,ProtocolError
PNG=b'\x89PNG\r\n\x1a\n' # protocol fixture only, not a rendered observation
class BoundaryTests(unittest.TestCase):
 def cmd(self,e,**kw):
  d={'episode':e.token,'observation_id':e.step,'skill':'move_forward','arguments':{'distance_m':.2}};d.update(kw);return json.dumps(d)
 def test_payload_whitelist(self):
  e=Episode('到达可见的红色标记');p=e.request(PNG)
  self.assertEqual(set(p['input']),{'episode','observation_id','goal','skills','recent_own_actions','image'})
  self.assertEqual(p['tools'],[]);self.assertEqual(p['model'],'gpt6.1-sol-light')
 def test_cross_episode_and_stale(self):
  a,b=Episode('A'),Episode('B');a.request(PNG);b.request(PNG)
  with self.assertRaises(ProtocolError):b.accept(self.cmd(a))
  raw=self.cmd(a);c=a.accept(raw);a.executed(c)
  with self.assertRaises(ProtocolError):a.accept(raw)
 def test_reject_injection_and_out_of_bounds(self):
  e=Episode('A');e.request(PNG)
  for update in [{'skill':'shell','arguments':{'cmd':'cat secret'}},{'arguments':{'distance_m':999}},{'arguments':{'distance_m':True}},{'world_pose':[1,2,3]}]:
   with self.assertRaises(ProtocolError):e.accept(self.cmd(e,**update))
  with self.assertRaises(ProtocolError):e.accept('{"skill":"wait","skill":"finish"}')
 def test_pending_finish_and_budget(self):
  e=Episode('A',max_actions=1);e.request(PNG);c=e.accept(self.cmd(e))
  with self.assertRaises(ProtocolError):e.accept(self.cmd(e))
  e.executed(c);self.assertTrue(e.closed)
  with self.assertRaises(ProtocolError):e.request(PNG)
 def test_history_not_shared_or_mutable(self):
  e=Episode('A');e.request(PNG);c=e.accept(self.cmd(e));e.executed(c);p=e.request(PNG)
  p['input']['recent_own_actions'][0]['arguments']['distance_m']=999
  self.assertEqual(e.history[0]['arguments']['distance_m'],.2)
  self.assertEqual(Episode('B').request(PNG)['input']['recent_own_actions'],[])
  e.close();self.assertFalse(e.history)
 def test_receipt_and_missing_image(self):
  e=Episode('A')
  with self.assertRaises(ProtocolError):e.accept(self.cmd(e))
  e.request(PNG);c=e.accept(self.cmd(e));c['arguments']['distance_m']=.4
  with self.assertRaises(ProtocolError):e.executed(c)
if __name__=='__main__':unittest.main()
