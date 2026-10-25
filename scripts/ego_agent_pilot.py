"""Prompt-constrained agent pilot; strict tool isolation is NOT established.
Runs only inside Isaac Sim on the server. Uses a frozen scene from the existing
accepted Carter episode, with every other robot removed in a new USD layer.
"""
import argparse,json,os,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);p.add_argument('--gpu',type=int,required=True);a=p.parse_args()
source=Path(a.source);out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'renderer':'RaytracedLighting','multi_gpu':False,'active_gpu':a.gpu,'extra_args':['--allow-root']})
try:
 import numpy as np
 import omni.usd,omni.replicator.core as rep,carb
 from pxr import Sdf,UsdGeom,UsdLux,Gf
 from PIL import Image
 from isaacsim.core.api import World
 from isaacsim.core.api.robots import Robot
 from isaacsim.core.utils.types import ArticulationAction
 meta=json.loads((source/'output/rollout.json').read_text());ego=meta['actors'][0]
 if ego['asset']!='carter':raise ValueError('diagnostic requires accepted Carter source')
 layer=Sdf.Layer.CreateNew(str(out/'scene.usda'));layer.subLayerPaths=[str(source/'output/scene_initial.usda')];layer.Save()
 assert omni.usd.get_context().open_stage(str(out/'scene.usda'))
 stage=omni.usd.get_context().get_stage();stage.SetEditTarget(stage.GetRootLayer())
 for other in meta['actors'][1:]:stage.GetPrimAtPath(other['root']).SetActive(False)
 world=World(stage_units_in_meters=1,physics_dt=1/120,rendering_dt=1/30)
 robot=world.scene.add(Robot(ego['root'],name='ego'))
 cam=UsdGeom.Camera.Define(stage,ego['base_body_path']+'/MosaicEgoCamera')
 cam.CreateFocalLengthAttr(18.);cam.CreateHorizontalApertureAttr(36.);cam.CreateVerticalApertureAttr(27.);cam.CreateClippingRangeAttr(Gf.Vec2f(.05,100.))
 # USD camera: right=-body Y, up=body Z, backward=-body X.
 M=np.eye(4);M[:3,:3]=np.array([[0,0,-1],[-1,0,0],[0,1,0]]);M[:3,3]=[.35,0,.85]
 cam.AddTransformOp().Set(Gf.Matrix4d(M.T.tolist()))
 light=UsdLux.DomeLight.Define(stage,'/World/MosaicFill');light.CreateIntensityAttr(250.)
 settings=carb.settings.get_settings();settings.set_bool('/physics/updateToUsd',True);settings.set_bool('/rtx/post/histogram/enabled',False)
 product=rep.create.render_product(str(cam.GetPath()),(640,480));rgb=rep.AnnotatorRegistry.get_annotator('rgb');rgb.attach(product);rep.orchestrator.set_capture_on_play(False)
 world.reset();names=list(robot.dof_names);indices=np.array([names.index(n) for n in ['left_wheel','right_wheel']])
 for _ in range(120):robot.apply_action(ArticulationAction(joint_velocities=np.zeros(2),joint_indices=indices));world.step(render=False)
 from relative_control import feedback
 import sys
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'prototypes/episode_harness'))
 from harness import Episode
 from pxr import UsdShade
 import math
 def pose2():
  pos,q=robot.get_world_pose();return (float(pos[0]),float(pos[1]),math.atan2(2*(q[0]*q[3]+q[1]*q[2]),1-2*(q[2]**2+q[3]**2)))
 # Private target generated from the initial robot pose; never exported to the agent.
 x,y,yaw=pose2();target=np.array([x+1.8*math.cos(yaw),y+1.8*math.sin(yaw)])
 marker=UsdGeom.Cube.Define(stage,'/World/MosaicGoalMarker');marker.CreateSizeAttr(.3)
 marker.AddTranslateOp().Set(Gf.Vec3d(float(target[0]),float(target[1]),.6))
 marker.AddScaleOp().Set(Gf.Vec3f(1,1,4));marker.CreateDisplayColorAttr([Gf.Vec3f(.03,.3,1.)])
 goal='Approach the blue upright rectangular marker. Stop roughly 0.6 to 0.8 meters from it, then declare finish. Avoid obstacles.'
 episode=Episode(goal,max_actions=16)
 records=[];actions=[];frame=0;terminal_reason='action_budget';wall_start=time.time()
 def capture():
  rep.orchestrator.step(rt_subframes=8 if frame==0 else 2,delta_time=0,pause_timeline=False)
  im=np.asarray(rgb.get_data())[...,:3].copy()
  if im.shape!=(480,640,3):raise RuntimeError('invalid observation shape')
  path=out/f'{frame:06d}.png';Image.fromarray(im).save(path);return path
 def zero():robot.apply_action(ArticulationAction(joint_velocities=np.zeros(2),joint_indices=indices))
 def blocked(speed,omega):
  # Conservative forward ray fan. This is a pilot gate, not full swept-volume certification.
  if speed<=0:return False
  import omni.physx
  xx,yy,angle=pose2()
  for lateral in (-.34,0,.34):
   origin_ray=(xx-lateral*math.sin(angle),yy+lateral*math.cos(angle),.35)
   # Start in front of the robot; do not classify its own shell as an obstacle.
   origin_ray=(origin_ray[0]+.45*math.cos(angle),origin_ray[1]+.45*math.sin(angle),origin_ray[2])
   hit=omni.physx.get_physx_scene_query_interface().raycast_closest(origin_ray,(math.cos(angle),math.sin(angle),0),.4)
   if hit.get('hit') and not str(hit.get('rigidBody','')).startswith(ego['root']):return True
  return False
 while not episode.closed:
  image_path=capture()
  sensor={'sample_time_s':frame/30,'joint_encoders':{'names':['left_wheel','right_wheel'],'position_rad':robot.get_joint_positions()[indices].tolist(),'velocity_rad_s':robot.get_joint_velocities()[indices].tolist()}}
  public=episode.request(image_path.read_bytes(),sensor)
  # Only public packet and RGB are eligible for the external policy input.
  public['input']['image']={'file':image_path.name}
  (out/'observation.tmp').write_text(json.dumps(public['input']))
  (out/'observation.json').unlink(missing_ok=True);(out/'observation.tmp').rename(out/'observation.json')
  print('AWAIT_ACTION',episode.step,frame,flush=True)
  command_path=out/f'action-{episode.step:03d}.json';deadline=time.monotonic()+600
  while not command_path.exists():
   zero()
   if time.monotonic()>deadline:raise TimeoutError('policy action timeout')
   time.sleep(.2)
  command=episode.accept(command_path.read_text());skill=command['skill'];args=command['arguments']
  if skill=='finish':
   zero();episode.executed(command);terminal_reason='agent_finish';break
  value=next(iter(args.values()));origin=pose2();start_frame=frame;status='running';settle=0
  while frame-start_frame<390:
   speed,omega,result=feedback(skill,value,origin,pose2(),(frame-start_frame)/30)
   if blocked(speed,omega):result='safety_stop';speed=omega=0
   if status=='running' and result!='running':status=result;settle=12
   if status!='running':speed=omega=0
   wheels=np.array([(speed-omega*.53194/2)/.2408,(speed+omega*.53194/2)/.2408])
   for _ in range(4):robot.apply_action(ArticulationAction(joint_velocities=wheels,joint_indices=indices));world.step(render=False)
   frame+=1;capture()
   pos,q=robot.get_world_pose();records.append({'frame':frame,'sim_time':frame/30,'position':pos.tolist(),'quaternion_wxyz':q.tolist()})
   if status!='running':
    settle-=1
    if settle<=0:break
  zero();actions.append({'command':command,'execution_status':status});episode.executed(command)
  if status!='reached':terminal_reason='execution_'+status;break
 zero();distance=float(np.linalg.norm(np.array(pose2()[:2])-target))
 success=terminal_reason=='agent_finish' and .45<=distance<=.85
 (out/'result.json').write_text(json.dumps({'status':'prompt_constrained_pilot','strict_tool_isolation':False,'success':success,'termination':terminal_reason,'final_distance_m':distance,'target_xy':target.tolist(),'actions':actions,'frames':records,'wall_s':time.time()-wall_start,'safety_scope':'forward_ray_fan_only_not_full_collision_certification'},indent=2))
 episode.close();stage.GetRootLayer().Save()
except BaseException:
 import traceback
 traceback.print_exc();os._exit(1)
finally:app.close()
