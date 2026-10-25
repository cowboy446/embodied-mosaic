"""Arena task-level G1/SONIC integration probe, not batch/navigation acceptance."""
import argparse,json,sys,traceback
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--gpu',type=int,default=0);p.add_argument('--route',action='store_true');p.add_argument('--seconds',type=float,default=12.);a=p.parse_args();out=Path(a.output);out.mkdir(exist_ok=False,parents=True)
import site
site.addsitedir('/mnt/nas/zhangrong/embodied-mosaic/runtime/ik-deps')
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'multi_gpu':False,'active_gpu':a.gpu,'physics_gpu':a.gpu,'extra_args':['--allow-root','--enable','isaacsim.sensors.camera']})
report={'status':'started','scope':'Arena G1 SONIC task integration, not navigation acceptance'}
try:
 import carb,torch,numpy as np
 from PIL import Image
 carb.settings.get_settings().set_bool('/isaaclab/cameras_enabled',True)
 carb.settings.get_settings().set_bool('/isaaclab/render/offscreen',True)
 from pxr import Usd,Sdf
 carb.settings.get_settings().set('/persistent/isaac/asset_root/cloud','https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1')
 root=Path('/mnt/nas/zhangrong/isaac-rigidtrack-20261023');sonic_root=root/'sonic-g1-20261024';sys.path.insert(0,str(sonic_root/'scripts'));sys.path.insert(0,'/local_nvme/zhangrong/isaac-rigidtrack-20261023/sonic-site')
 import sonic_control as sonic
 from components import G1SonicEmbodiment,NavigateTask
 from isaaclab_arena.scene.scene import Scene
 from isaaclab_arena.assets.background import Background
 from isaaclab_arena.environments.isaaclab_arena_environment import IsaacLabArenaEnvironment
 from single_episode_env import SingleEpisodeBuilder
 src=root/'rulegen-diverse40/runs/warehouse-152002-2fc99598b2/attempt-02/output/scene_initial.usda'
 bg=Usd.Stage.CreateNew(str(out/'background.usda'));bg.GetRootLayer().subLayerPaths=[str(src)];bg.SetDefaultPrim(bg.GetPrimAtPath('/World'))
 for path in ['/World/Actors','/World/physicsScene','/World/PhysicsScene']:
  prim=bg.GetPrimAtPath(path)
  if prim:prim.SetActive(False)
 bg.GetRootLayer().Save()
 asset=root/'campaign20/assets/Assets/Isaac/5.1/Isaac/Robots/Unitree/G1/g1.usd'
 rs=Usd.Stage.CreateNew(str(out/'robot.usda'));rp=rs.DefinePrim('/Robot','Xform');rp.GetReferences().AddReference(str(asset));rs.SetDefaultPrim(rp)
 for key,val in [('left_hand','ThreeFinger'),('right_hand','ThreeFinger'),('Physics','SimplifiedPhysX')]:
  if key in rp.GetVariantSets().GetNames():rp.GetVariantSet(key).SetVariantSelection(val)
 rs.GetRootLayer().Save()
 ref=np.load(sonic_root/'output/reference.npz')['qpos'];initial=ref[0];emb=G1SonicEmbodiment(str(out/'robot.usda'),(-9.1,29.05,float(initial[2])),initial[3:7],sonic)
 emb.scene_config.robot.init_state.joint_pos=dict(zip(sonic.NAMES,initial[7:].tolist()))
 descriptor=IsaacLabArenaEnvironment(name='Mosaic-G1-SONIC-Probe-v0',scene=Scene([Background(name='warehouse',usd_path=str(out/'background.usda'),object_min_z=0.)]),embodiment=emb,task=NavigateTask((-5.,29.)))
 args=argparse.Namespace(mimic=False,device=f'cuda:{a.gpu}',num_envs=1,disable_fabric=False)
 env,cfg=SingleEpisodeBuilder(descriptor,args).make_registered_and_return_cfg();report['arena_environment_constructed']=True
 obs,_=env.reset();robot=env.scene['robot'];ids,_=robot.find_joints(sonic.NAMES,preserve_order=True);ctrl=sonic.Controller();states=[]
 camera=env.scene['ego_camera'];capture=[]
 for _ in range(8):env.sim.render()
 camera.update(0.,force_recompute=True)
 route_policy=None;planner_logs=[];terminal_reason='budget_exhausted'
 if a.route:
  import collections,omni.physx
  sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
  from collision_guard import BaseCollisionGuard,Envelope
  from grid_navigation import plan_grid
  from sonic_route_reference import RouteReference
  guard=BaseCollisionGuard(omni.physx.get_physx_scene_query_interface(),Envelope(.45,.45,.04,1.7,.10),'/World/envs/env_0/Robot')
  start=robot.data.root_pos_w[0].cpu().numpy()
  plan=plan_grid(start,lambda xy:guard.blocked(xy,0.,turning=True),seed=42,minimum_path=3.,maximum_path=5.)
  (out/'grid-plan.json').write_text(json.dumps(plan,indent=2))
  route_policy=RouteReference(sonic.session('planner_sonic.onnx'),plan['route'])
  term=env.termination_manager.get_term_cfg('success');term.params['target_xy']=list(plan['route'][-1]);env.termination_manager.set_term_cfg('success',term)
  qpos=np.r_[start,robot.data.root_quat_w[0].cpu().numpy(),robot.data.joint_pos[0,ids].cpu().numpy()]
  context=collections.deque([qpos.copy() for _ in range(4)],maxlen=4)
  reference_start=0
 for step in range(round(a.seconds*150) if a.route else 300):
  if step%3==0:
   d=robot.data;q=d.joint_pos[0,ids].cpu().numpy();dq=d.joint_vel[0,ids].cpu().numpy();quat=d.root_quat_w[0].cpu().numpy();ang=d.root_ang_vel_w[0].cpu().numpy()
   frame=step//3
   if route_policy:
    if step%90==0 or (step>0 and len(ref)-(frame-reference_start)<51):
     planning_context=np.asarray(context) if step==0 else sonic.resample(ref,(frame-reference_start)+np.arange(4)*50/30)
     motion,log=route_policy.generate(planning_context,d.root_pos_w[0,:2].cpu().numpy());ref=sonic.resample(motion,np.arange(0,(len(motion)-1)*50/30)*30/50)
     reference_start=frame;planner_logs.append(dict(log,time_s=step/150));print('PLANNER',planner_logs[-1],flush=True)
    frame-=reference_start
   if len(ref[frame:frame+51])<51:raise RuntimeError('planner reference horizon too short')
   target,_,_=ctrl.step(q,dq,quat,ang,ref[frame:frame+51])
  obs,reward,terminated,truncated,info=env.step(torch.tensor(target,device=env.device)[None])
  if (step+1)%5==0:
   rgb=camera.data.output['rgb'][0].cpu().numpy()[...,:3]
   if rgb.shape!=(480,640,3):raise RuntimeError(f'invalid camera output shape {rgb.shape}')
   image_name=f'{len(capture):06d}.png';Image.fromarray(rgb).save(out/image_name)
   d=robot.data
   if route_policy:context.append(np.r_[d.root_pos_w[0].cpu().numpy(),d.root_quat_w[0].cpu().numpy(),d.joint_pos[0,ids].cpu().numpy()])
   capture.append({'time_s':(step+1)/150,'image':image_name,'position':d.root_pos_w[0].cpu().tolist(),'quaternion_wxyz':d.root_quat_w[0].cpu().tolist(),'joint_position':d.joint_pos[0].cpu().tolist(),'joint_velocity':d.joint_vel[0].cpu().tolist(),'control_target':target.tolist(),'camera_position':camera.data.pos_w[0].cpu().tolist(),'camera_quaternion_wxyz':camera.data.quat_w_world[0].cpu().tolist()})
  states.append({'time_s':(step+1)/150,'position':robot.data.root_pos_w[0].cpu().tolist(),'joint_position':robot.data.joint_pos[0].cpu().tolist()})
  if float(robot.data.root_pos_w[0,2])<.45:raise RuntimeError('fall detected')
  if route_policy and (step+1)%5==0:
   pos=robot.data.root_pos_w[0].cpu().numpy()
   if guard.blocked(pos[:2],0.,turning=True):raise RuntimeError('robot left conservative free corridor')
  if bool(terminated.any()|truncated.any()):
   terminal_reason='task_success' if bool(terminated.any()) else 'timeout'
   report['terminal_state']={'time_s':(step+1)/150,'position':robot.data.root_pos_w[0].cpu().tolist(),'linear_velocity':robot.data.root_lin_vel_w[0].cpu().tolist(),'joint_position':robot.data.joint_pos[0].cpu().tolist(),'joint_velocity':robot.data.joint_vel[0].cpu().tolist(),'automatic_reset_suppressed':bool(env._terminal_hold)}
   break
 (out/'planner-log.json').write_text(json.dumps(planner_logs,indent=2))
 (out/'capture.json').write_text(json.dumps({'fps':30,'resolution':[640,480],'mount_body':'torso_link','frames':capture},indent=2))

 report.update(status=terminal_reason if a.route else 'stepped',physics_dt=cfg.sim.dt,decimation=cfg.decimation,control_hz=50,recording_hz=30,capture_frames=len(capture),action_shape=list(env.action_manager.action.shape),joint_names=robot.joint_names,states=states)
 env.close()
except BaseException:
 report.update(status='failed',traceback=traceback.format_exc());traceback.print_exc()
 if 'capture' in locals():(out/'partial-capture.json').write_text(json.dumps(capture))
 if 'planner_logs' in locals():(out/'planner-log.json').write_text(json.dumps(planner_logs))
 if 'env' in locals():env.close()
finally:
 (out/'report.json').write_text(json.dumps(report,indent=2));print('REPORT',report['status'],flush=True);app.close()
