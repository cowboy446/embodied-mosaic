"""Private, append-only synchronized robot replay log. Not an agent observation API."""
import hashlib,json,math
from pathlib import Path

class ReplayRecorder:
 def __init__(self, directory, joint_names, control_joint_indices, fps=30):
  self.root=Path(directory);self.names=list(joint_names);self.indices=list(control_joint_indices);self.fps=fps;self.count=0;self.last_time=None
  if not self.names or len(set(self.names))!=len(self.names) or fps<=0:raise ValueError('invalid replay metadata')
  if any(type(i) is not int or not 0<=i<len(self.names) for i in self.indices):raise ValueError('invalid control joints')
  (self.root/'replay-metadata.json').write_text(json.dumps({'schema':'mosaic.robot-replay.v1','joint_names':self.names,'control_joint_indices':self.indices,'fps':fps,'quaternion_order':'wxyz','state_frame':'world','control_mode':'joint_velocity_target','scope':'kinematic articulated replay, not deterministic physics restart'},indent=2))
  self.stream=(self.root/'replay-frames.jsonl').open('x')
 def append(self, *, frame, sim_time, physics_step, position, quaternion_wxyz, linear_velocity, angular_velocity, joint_position, joint_velocity, control_velocity_target, image_file):
  if type(frame) is not int or frame!=self.count:raise ValueError('non-contiguous replay frame')
  if not isinstance(sim_time,(int,float)) or not math.isfinite(sim_time) or sim_time<0:raise ValueError('invalid time')
  if self.last_time is not None and abs(sim_time-self.last_time-1/self.fps)>1e-6:raise ValueError('capture cadence mismatch')
  if type(physics_step) is not int or physics_step<0:raise ValueError('invalid physics step')
  arrays={'position':(position,3),'quaternion_wxyz':(quaternion_wxyz,4),'linear_velocity':(linear_velocity,3),'angular_velocity':(angular_velocity,3),'joint_position':(joint_position,len(self.names)),'joint_velocity':(joint_velocity,len(self.names)),'control_velocity_target':(control_velocity_target,len(self.indices))}
  data={}
  for k,(v,n) in arrays.items():
   v=list(v)
   if len(v)!=n or any(type(x) not in (int,float) or not math.isfinite(x) for x in v):raise ValueError('invalid '+k)
   data[k]=v
  if abs(sum(x*x for x in data['quaternion_wxyz'])-1)>1e-3:raise ValueError('invalid quaternion norm')
  if Path(image_file).name!=image_file:raise ValueError('invalid image path')
  image=self.root/image_file
  data.update(frame=frame,sim_time=sim_time,physics_step=physics_step,image_file=image_file,image_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
  self.stream.write(json.dumps(data,allow_nan=False)+'\n');self.stream.flush();self.count+=1;self.last_time=sim_time
 def close(self):self.stream.close()
