"""Arena-compatible single-episode execution without implicit reset on termination.
Explicit reset remains supported. A terminal step cannot be followed by another step.
"""
from isaaclab.envs import ManagerBasedRLEnv
from isaaclab_arena.environments.arena_env_builder import ArenaEnvBuilder

class SingleEpisodeEnv(ManagerBasedRLEnv):
 def reset(self,*args,**kwargs):
  self._terminal_hold=False;self._inside_step=False
  if hasattr(self,'_mosaic_settle'):del self._mosaic_settle
  if hasattr(self,'_mosaic_previous_xy'):del self._mosaic_previous_xy
  return super().reset(*args,**kwargs)
 def step(self,action):
  if getattr(self,'_terminal_hold',False):raise RuntimeError('episode ended; explicit reset required')
  self._inside_step=True
  try:return super().step(action)
  finally:self._inside_step=False
 def _reset_idx(self,env_ids):
  if getattr(self,'_inside_step',False):
   self._terminal_hold=True
   return
  return super()._reset_idx(env_ids)

class SingleEpisodeBuilder(ArenaEnvBuilder):
 def get_entry_point(self):return SingleEpisodeEnv
