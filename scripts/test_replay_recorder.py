import json,tempfile,unittest
from pathlib import Path
from replay_recorder import ReplayRecorder
class ReplayTests(unittest.TestCase):
 def sample(self):return dict(frame=0,sim_time=0.,physics_step=120,position=[0.,0.,0.],quaternion_wxyz=[1.,0.,0.,0.],linear_velocity=[0.,0.,0.],angular_velocity=[0.,0.,0.],joint_position=[0.,0.,0.,0.],joint_velocity=[0.,0.,0.,0.],control_velocity_target=[0.,0.],image_file='000000.png')
 def test_complete_joint_state_and_clock(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,'000000.png').write_bytes(b'fixture');r=ReplayRecorder(d,['l','r','pivot','axle'],[0,1]);r.append(**self.sample());r.close()
   s=json.loads(Path(d,'replay-frames.jsonl').read_text());self.assertEqual(len(s['joint_position']),4);self.assertEqual(len(s['image_sha256']),64)
 def test_missing_joint_and_bad_cadence(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,'000000.png').write_bytes(b'fixture');r=ReplayRecorder(d,['l','r','pivot','axle'],[0,1]);s=self.sample();s['joint_position']=[0.,0.]
   with self.assertRaises(ValueError):r.append(**s)
   r.append(**self.sample());s=self.sample();s.update(frame=1,sim_time=.1)
   with self.assertRaises(ValueError):r.append(**s)
   r.close()
 def test_audit_detects_replaced_image(self):
  from audit_robot_replay import audit
  with tempfile.TemporaryDirectory() as d:
   Path(d,'000000.png').write_bytes(b'fixture');r=ReplayRecorder(d,['l','r','pivot','axle'],[0,1]);r.append(**self.sample())
   Path(d,'000001.png').write_bytes(b'next');s=self.sample();s.update(frame=1,sim_time=1/30,physics_step=124,image_file='000001.png');r.append(**s);r.close()
   self.assertEqual(audit(d)['frames'],2)
   Path(d,'000001.png').write_bytes(b'replaced')
   with self.assertRaisesRegex(ValueError,'image changed'):audit(d)
if __name__=='__main__':unittest.main()
