"""Public sensor boundary. Producers must be audited; labels cannot prove provenance.
Only encoder/IMU readings are exposed here. Global poses and task state have no fields.
Units: radians, rad/s, m/s², seconds. IMU vectors use robot-body axes.
"""
import math

def _numbers(values, size=None):
 if not isinstance(values,(list,tuple)) or len(values)>128 or (size is not None and len(values)!=size):
  raise ValueError('invalid sensor vector')
 if any(type(x) not in (int,float) or not math.isfinite(x) for x in values):
  raise ValueError('sensor values must be finite numbers')
 return list(values)

def validate_proprioception(packet):
 if not isinstance(packet,dict) or not set(packet)<= {'sample_time_s','joint_encoders','imu'}:
  raise ValueError('unknown proprioception channel')
 if 'sample_time_s' not in packet or type(packet['sample_time_s']) not in (int,float) or not math.isfinite(packet['sample_time_s']) or packet['sample_time_s']<0:
  raise ValueError('invalid sensor time')
 result={'sample_time_s':packet['sample_time_s']}
 if 'joint_encoders' in packet:
  j=packet['joint_encoders']
  if not isinstance(j,dict) or set(j)!={'names','position_rad','velocity_rad_s'}:raise ValueError('invalid encoder fields')
  names=j['names']
  if not isinstance(names,list) or not 0<len(names)<=128 or any(not isinstance(n,str) or not n or len(n)>64 or not all(c.isalnum() or c=='_' for c in n) for n in names) or len(set(names))!=len(names):raise ValueError('invalid joint names')
  result['joint_encoders']={'names':list(names),'position_rad':_numbers(j['position_rad'],len(names)),'velocity_rad_s':_numbers(j['velocity_rad_s'],len(names))}
 if 'imu' in packet:
  imu=packet['imu']
  if not isinstance(imu,dict) or set(imu)!={'angular_velocity_rad_s','specific_force_m_s2'}:raise ValueError('invalid IMU fields')
  result['imu']={k:_numbers(v,3) for k,v in imu.items()}
 if len(result)==1:raise ValueError('no sensor channel')
 return result
