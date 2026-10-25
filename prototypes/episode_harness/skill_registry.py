"""Embodiment-specific public contracts. Only implemented skill profiles are advertised.
Backend selection and actuator resources remain private to the executor.
"""
from copy import deepcopy
_PROFILES = {
 'carter_base_v1': {
  'move_forward': {'distance_m': (0.05, 0.50)},
  'turn': {'angle_deg': (-90., 90.)},
  'wait': {'duration_s': (0.1, 1.)},
  'finish': {},
 }
}

def get_profile(name):
 if not isinstance(name,str) or name not in _PROFILES:
  raise ValueError('unsupported embodiment skill profile')
 return deepcopy(_PROFILES[name])
