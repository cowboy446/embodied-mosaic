"""Arena task-level G1/SONIC integration probe, not batch/navigation acceptance."""
import argparse,json,sys,traceback
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--gpu',type=int,default=0);a=p.parse_args();out=Path(a.output);out.mkdir(exist_ok=False,parents=True)
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'multi_gpu':False,'active_gpu':a.gpu,'extra_args':['--allow-root','--enable','isaacsim.sensors.camera']})
report={'status':'started','scope':'Arena G1 SONIC task integration, not navigation acceptance'}
try:
 import carb,torch,numpy as np
 from pxr import Usd,Sdf
 carb.settings.get_settings().set('/persistent/isaac/asset_root/cloud','https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1')
 root=Path('/mnt/nas/zhangrong/isaac-rigidtrack-20261023');sonic_root=root/'sonic-g1-20261024';sys.path.insert(0,str(sonic_root/'scripts'));sys.path.insert(0,'/local_nvme/zhangrong/isaac-rigidtrack-20261023/sonic-site')
 import sonic_control as sonic
 from components import G1SonicEmbodiment,NavigateTask
 from isaaclab_arena.scene.scene import Scene
 from isaaclab_arena.assets.background import Background
 from isaaclab_arena.environments.isaaclab_arena_environment import IsaacLabArenaEnvironment
 from isaaclab_arena.environments.arena_env_builder import ArenaEnvBuilder
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
 env,cfg=ArenaEnvBuilder(descriptor,args).make_registered_and_return_cfg();report['arena_environment_constructed']=True
 obs,_=env.reset();robot=env.scene['robot'];ids,_=robot.find_joints(sonic.NAMES,preserve_order=True);ctrl=sonic.Controller();states=[]
 for step in range(100):
  d=robot.data;q=d.joint_pos[0,ids].cpu().numpy();dq=d.joint_vel[0,ids].cpu().numpy();quat=d.root_quat_w[0].cpu().numpy();ang=d.root_ang_vel_w[0].cpu().numpy()
  target,_,_=ctrl.step(q,dq,quat,ang,ref[step:step+51]);obs,reward,terminated,truncated,info=env.step(torch.tensor(target,device=env.device)[None])
  states.append({'time_s':(step+1)/50,'position':robot.data.root_pos_w[0].cpu().tolist(),'joint_position':robot.data.joint_pos[0].cpu().tolist()})
  if bool(terminated.any()|truncated.any()):raise RuntimeError('unexpected task termination')
 report.update(status='stepped',physics_dt=cfg.sim.dt,decimation=cfg.decimation,action_shape=list(env.action_manager.action.shape),joint_names=robot.joint_names,states=states)
 env.close()
except BaseException:report.update(status='failed',traceback=traceback.format_exc());traceback.print_exc()
finally:
 (out/'report.json').write_text(json.dumps(report,indent=2));print('REPORT',report['status'],flush=True);app.close()
