"""Fixed robot/sensor metadata, not live scene state or localization."""
from copy import deepcopy
CARTER_EGO = {
 'body_axes': 'x forward, y left, z up',
 'distance_reference': 'horizontal center of the robot base body',
 'drive': {'wheel_radius_m': .2408, 'wheel_track_m': .53194},
 'camera': {
  'resolution_px': [640,480],
  'focal_length_mm': 18., 'horizontal_aperture_mm': 36., 'vertical_aperture_mm': 27.,
  'intrinsics_pixel_corner_coordinates': [[320.,0.,320.],[0.,320.,240.],[0.,0.,1.]],
  'translation_in_base_m': [.35,0.,.85],
  'optical_axes_in_base': {'right':[0.,-1.,0.], 'down':[0.,0.,-1.], 'forward':[1.,0.,0.]},
  'note': 'Mount is relative to the base body, not world or ground. No live world pose is supplied.'
 }
}

def robot_model(profile):
 if profile!='carter_base_v1':raise ValueError('no verified sensor mount for profile')
 return deepcopy(CARTER_EGO)
