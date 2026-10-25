import copy, unittest
from proprioception import validate_proprioception
from harness import Episode, ProtocolError
from test_harness import PNG
class SensorBoundaryTests(unittest.TestCase):
 def packet(self):return {'sample_time_s':1.0,'joint_encoders':{'names':['left_wheel','right_wheel'],'position_rad':[.2,.3],'velocity_rad_s':[0.,0.]}}
 def test_public_encoder_payload_and_copy(self):
  s=self.packet();p=Episode('Navigate').request(PNG,s)
  s['joint_encoders']['position_rad'][0]=999
  self.assertEqual(p['input']['proprioception']['joint_encoders']['position_rad'][0],.2)
 def test_privileged_extra_fields_rejected(self):
  for key in ['world_pose','target_distance','map','body_id','success','source']:
   s=self.packet();s[key]=[1,2,3]
   with self.assertRaises(ProtocolError):Episode('Navigate').request(PNG,s)
 def test_bad_values_and_nested_fields(self):
  for value in [float('nan'),float('inf'),True]:
   s=self.packet();s['joint_encoders']['position_rad'][0]=value
   with self.assertRaises(ValueError):validate_proprioception(s)
  s=self.packet();s['joint_encoders']['world_pose']=[0,0,0]
  with self.assertRaises(ValueError):validate_proprioception(s)
 def test_imu_body_vectors(self):
  s={'sample_time_s':0,'imu':{'angular_velocity_rad_s':[0,0,.1],'specific_force_m_s2':[0,0,9.81]}}
  self.assertEqual(validate_proprioception(s),s)
if __name__=='__main__':unittest.main()
