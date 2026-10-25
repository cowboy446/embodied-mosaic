"""Sensor/control integration diagnostic, not an agent task or acceptance run.
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
 records=[];start=time.time()
 for frame in range(90):
  speed=.12 if 15<=frame<60 else 0.;omega=.25 if 60<=frame<80 else 0.
  wheels=np.array([(speed-omega*.53194/2)/.2408,(speed+omega*.53194/2)/.2408])
  for _ in range(4):robot.apply_action(ArticulationAction(joint_velocities=wheels,joint_indices=indices));world.step(render=False)
  world.render()
  for _ in range(4 if frame==0 else 1):world.render()
  image=np.asarray(rgb.get_data())[...,:3].copy()
  if image.shape!=(480,640,3):raise RuntimeError(f'invalid RGB {image.shape}')
  Image.fromarray(image).save(out/f'{frame:06d}.png')
  pos,q=robot.get_world_pose();records.append({'frame':frame,'sim_time':(frame+1)/30,'position':pos.tolist(),'quaternion_wxyz':q.tolist(),'wheel_velocity':wheels.tolist(),'rgb_mean':float(image.mean())})
  print('EGO_FRAME',frame,round(float(image.mean()),2),flush=True)
 robot.apply_action(ArticulationAction(joint_velocities=np.zeros(2),joint_indices=indices))
 (out/'diagnostic.json').write_text(json.dumps({'status':'recorded_not_agent_validated','source':str(source),'camera':str(cam.GetPath()),'frames':records,'wall_s':time.time()-start},indent=2))
 stage.GetRootLayer().Save()
except BaseException:
 import traceback
 traceback.print_exc();os._exit(1)
finally:app.close()
