"""Mosaic adapters for pinned IsaacLab-Arena 0.1.1; import after SimulationApp.
The USD inputs must be separately prepared, dependency-preserving assets.
"""
import torch
import isaaclab.sim as sim
from isaaclab.assets import ArticulationCfg
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.envs import mdp
from isaaclab.managers import TerminationTermCfg
from isaaclab.sensors import CameraCfg
from isaaclab_arena.embodiments.embodiment_base import EmbodimentBase
from isaaclab_arena.tasks.task_base import TaskBase
from isaaclab_arena.assets.background import Background
from isaaclab_arena.scene.scene import Scene
from isaaclab_arena.environments.isaaclab_arena_environment import IsaacLabArenaEnvironment
from isaaclab_arena.utils.configclass import make_configclass

def config(name,**values):
 return make_configclass(name,[(k,type(v),v) for k,v in values.items()])()

class CarterEmbodiment(EmbodimentBase):
 name='mosaic_carter'
 def __init__(self,usd_path,position,rotation):
  super().__init__(enable_cameras=True)
  robot=ArticulationCfg(prim_path='{ENV_REGEX_NS}/Robot',spawn=sim.UsdFileCfg(usd_path=usd_path),
   init_state=ArticulationCfg.InitialStateCfg(pos=tuple(position),rot=tuple(rotation)),
   actuators={'wheels':ImplicitActuatorCfg(joint_names_expr=['left_wheel','right_wheel'],stiffness=0.,damping=1000.),
              'casters':ImplicitActuatorCfg(joint_names_expr=['rear_pivot','rear_axle'],stiffness=0.,damping=0.)})
  self.scene_config=config('CarterScene',robot=robot)
  self.action_config=config('CarterActions',wheels=mdp.JointVelocityActionCfg(asset_name='robot',joint_names=['left_wheel','right_wheel'],scale=1.,use_default_offset=False))
  self.camera_config=config('CarterCameras',ego_camera=CameraCfg(
   prim_path='{ENV_REGEX_NS}/Robot/chassis_link/MosaicEgoCamera',height=480,width=640,data_types=['rgb'],update_period=1/30,
   spawn=sim.PinholeCameraCfg(focal_length=18.,horizontal_aperture=36.,vertical_aperture=27.,clipping_range=(.05,100.)),
   offset=CameraCfg.OffsetCfg(pos=(.35,0.,.85),rot=(.5,.5,-.5,-.5),convention='opengl')))

def reached(env,target_xy,tolerance):
 robot=env.scene['robot'];delta=robot.data.root_pos_w[:,:2]-torch.tensor(target_xy,device=env.device)
 pos=robot.data.root_pos_w[:,:2]
 if hasattr(env,'_mosaic_previous_xy'):
  measured_speed=torch.linalg.vector_norm(pos-env._mosaic_previous_xy,dim=-1)/env.step_dt
 else:measured_speed=torch.full((env.num_envs,),float('inf'),device=env.device)
 env._mosaic_previous_xy=pos.clone()
 valid=(torch.linalg.vector_norm(delta,dim=-1)<tolerance)&(torch.linalg.vector_norm(robot.data.root_lin_vel_w[:,:2],dim=-1)<.03)&(measured_speed<.03)
 if hasattr(env,'_mosaic_ordered_route'):
  if env.num_envs!=1:raise RuntimeError('ordered route probe requires one environment')
  valid=valid & env._mosaic_ordered_route.update(pos[0].detach().cpu().tolist())
 if not hasattr(env,'_mosaic_settle'):env._mosaic_settle=torch.zeros(env.num_envs,device=env.device)
 env._mosaic_settle=torch.where(valid,env._mosaic_settle+env.step_dt,torch.zeros_like(env._mosaic_settle))
 return env._mosaic_settle>=.3

class NavigateTask(TaskBase):
 def __init__(self,target_xy):super().__init__(episode_length_s=120.);self.target_xy=list(target_xy)
 def get_scene_cfg(self):return None
 def get_events_cfg(self):return None
 def get_termination_cfg(self):return config('NavigationTermination',time_out=TerminationTermCfg(func=mdp.time_out,time_out=True),success=TerminationTermCfg(func=reached,params={'target_xy':self.target_xy,'tolerance':.15}))
 def get_prompt(self):return 'Navigate to the marked destination and stop.'
 def get_mimic_env_cfg(self,embodiment_name):raise NotImplementedError('Navigation is not a Mimic task')
 def get_metrics(self):return []
 def modify_env_cfg(self,cfg):
  cfg.sim.enable_scene_query_support=True
  cfg.sim.dt=1/120;cfg.sim.render_interval=4;cfg.decimation=4
  return cfg

def environment(background_usd,robot_usd,position,rotation,target_xy):
 return IsaacLabArenaEnvironment(name='Mosaic-Carter-Navigation-v0',
  scene=Scene(assets=[Background(name='warehouse',usd_path=background_usd,object_min_z=0.)]),
  embodiment=CarterEmbodiment(robot_usd,position,rotation),task=NavigateTask(target_xy))


class G1SonicEmbodiment(EmbodimentBase):
 """29-body-joint target interface. SONIC policy supplies physical joint radians.
 Hand configuration is part of the prepared USD; no root kinematic drive.
 """
 name='mosaic_g1_sonic'
 def __init__(self,usd_path,position,rotation,sonic,seed=42):
  super().__init__(enable_cameras=True)
  self.seed=seed
  actuators={name:ImplicitActuatorCfg(joint_names_expr=[name],stiffness=float(sonic.KP[i]),damping=float(sonic.KD[i]),effort_limit_sim=float(sonic.EFFORT_PHYS[i]),armature=float(sonic.ARM_PHYS[i])) for i,name in enumerate(sonic.NAMES)}
  actuators['hands']=ImplicitActuatorCfg(joint_names_expr=['.*hand.*'],stiffness=8.,damping=.4,effort_limit_sim=2.,armature=.001)
  robot=ArticulationCfg(prim_path='{ENV_REGEX_NS}/Robot',spawn=sim.UsdFileCfg(usd_path=usd_path),
   init_state=ArticulationCfg.InitialStateCfg(pos=tuple(position),rot=tuple(rotation),joint_pos=dict(zip(sonic.NAMES,sonic.DEFAULT.tolist()))),actuators=actuators)
  self.scene_config=config('G1Scene',robot=robot)
  self.action_config=config('G1SonicActions',body=mdp.JointPositionActionCfg(asset_name='robot',joint_names=sonic.NAMES,preserve_order=True,scale=1.,use_default_offset=False))
  self.camera_config=config('G1EgoCameras',ego_camera=CameraCfg(
   prim_path='{ENV_REGEX_NS}/Robot/torso_link/MosaicEgoCamera',height=480,width=640,data_types=['rgb'],update_period=1/30,
   spawn=sim.PinholeCameraCfg(focal_length=18.,horizontal_aperture=36.,vertical_aperture=27.,clipping_range=(.05,100.)),
   offset=CameraCfg.OffsetCfg(pos=(.15,0.,.30),rot=(.5,.5,-.5,-.5),convention='opengl')))

 def modify_env_cfg(self,cfg):
  cfg.sim.enable_scene_query_support=True
  cfg.sim.dt=1/300;cfg.sim.render_interval=10;cfg.decimation=2;cfg.seed=self.seed
  return cfg
