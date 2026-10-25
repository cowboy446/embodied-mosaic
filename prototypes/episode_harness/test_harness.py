import unittest,json,io,base64
from PIL import Image,PngImagePlugin
from harness import Episode,ProtocolError
buffer=io.BytesIO();Image.new('RGB',(640,480),(30,40,50)).save(buffer,format='PNG');PNG=buffer.getvalue()
class BoundaryTests(unittest.TestCase):
 def cmd(self,e,**kw):
  d={'episode':e.token,'observation_id':e.step,'skill':'move_forward','arguments':{'distance_m':.2}};d.update(kw);return json.dumps(d)
 def test_payload_whitelist(self):
  e=Episode('到达可见的红色标记');p=e.request(PNG)
  self.assertEqual(set(p['input']),{'episode','observation_id','goal','skills','recent_own_actions','image'})
  self.assertEqual(p['reasoning_effort'],'low');self.assertEqual(p['tools'],[]);self.assertEqual(p['model'],'gpt-6.1-sol')
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
 def test_image_decode_shape_and_metadata_boundary(self):
  for blob in [PNG[:20],b'\x89PNG\r\n\x1a\n']:
   with self.assertRaises(ProtocolError):Episode('A').request(blob)
  for size,mode in [((640,479),'RGB'),((640,480),'RGBA')]:
   b=io.BytesIO();Image.new(mode,size).save(b,format='PNG')
   with self.assertRaises(ProtocolError):Episode('A').request(b.getvalue())
  b=io.BytesIO();meta=PngImagePlugin.PngInfo();meta.add_text('private_pose','DO_NOT_LEAK')
  Image.new('RGB',(640,480)).save(b,format='PNG',pnginfo=meta)
  p=Episode('A').request(b.getvalue());clean=base64.b64decode(p['input']['image']['base64'])
  self.assertNotIn(b'DO_NOT_LEAK',clean)
 def test_cannot_replace_an_issued_observation(self):
  e=Episode('A');e.request(PNG)
  with self.assertRaises(ProtocolError):e.request(PNG)
 def test_skill_profiles_are_isolated_and_fail_closed(self):
  with self.assertRaises(ProtocolError):Episode('A',skill_profile='unimplemented_vla')
  a,b=Episode('A'),Episode('B');payload=a.request(PNG)
  payload['input']['skills']['move_forward']['distance_m'][1]=999
  with self.assertRaises(ProtocolError):a.accept(self.cmd(a,arguments={'distance_m':999}))
  self.assertEqual(b.request(PNG)['input']['skills']['move_forward']['distance_m'][1],.5)
if __name__=='__main__':unittest.main()
