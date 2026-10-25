"""Kinematic review replay from recorded base poses; wheel articulation is not replayed."""
import argparse,json,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--gpu',type=int,required=True);a=p.parse_args();root=Path(a.run);out=root/'third-person';out.mkdir(exist_ok=False)
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'renderer':'RaytracedLighting','multi_gpu':False,'active_gpu':a.gpu,'extra_args':['--allow-root']})
try:
 import numpy as np,omni.usd,omni.replicator.core as rep,carb
 from pxr import UsdGeom,Gf,Sdf
 from PIL import Image,ImageDraw
 d=json.loads((root/'result.json').read_text());frames=d['frames'];target=d['target_xy']
 layer=Sdf.Layer.CreateNew(str(out/'replay.usda'));layer.subLayerPaths=[str(root/'scene.usda')];layer.Save()
 assert omni.usd.get_context().open_stage(str(out/'replay.usda'))
 stage=omni.usd.get_context().get_stage();stage.SetEditTarget(stage.GetRootLayer())
 actor=stage.GetPrimAtPath('/World/Actors/ego');base=stage.GetPrimAtPath('/World/Actors/ego/chassis_link')
 cache=UsdGeom.XformCache();root_world=cache.GetLocalToWorldTransform(actor);base_world=cache.GetLocalToWorldTransform(base);parent_world=cache.GetLocalToWorldTransform(actor.GetParent())
 xform=UsdGeom.Xformable(actor);xform.ClearXformOpOrder();op=xform.AddTransformOp()
 pts=np.array([f['position'] for f in frames]);center=(pts[0,:2]+np.array(target))/2
 eye=np.array([center[0]+1.5,center[1]-4.0,3.2]);look=np.array([center[0],center[1],.55]);back=(eye-look);back/=np.linalg.norm(back);right=np.cross([0,0,1],back);right/=np.linalg.norm(right);up=np.cross(back,right)
 mat=np.eye(4);mat[:3,:3]=np.stack([right,up,back],axis=1);mat[:3,3]=eye
 cam=UsdGeom.Camera.Define(stage,'/World/ReviewCamera');cam.AddTransformOp().Set(Gf.Matrix4d(mat.T.tolist()));cam.CreateFocalLengthAttr(25.);cam.CreateHorizontalApertureAttr(36.);cam.CreateVerticalApertureAttr(20.25);cam.CreateClippingRangeAttr(Gf.Vec2f(.05,100.))
 def curve(name,points,color,width):
  c=UsdGeom.BasisCurves.Define(stage,name);c.CreateTypeAttr('linear');c.CreateCurveVertexCountsAttr([len(points)]);c.CreatePointsAttr([Gf.Vec3f(*p) for p in points]);c.CreateWidthsAttr([width]);c.SetWidthsInterpolation('constant');c.CreateDisplayColorAttr([Gf.Vec3f(*color)])
 curve('/World/ReviewPath',[(p[0],p[1],.035) for p in pts[::5]],(.1,1,.3),.035)
 curve('/World/ReviewRemaining',[(pts[-1,0],pts[-1,1],.045),(target[0],target[1],.045)],(1,.7,.05),.025)
 settings=carb.settings.get_settings();settings.set_bool('/rtx/post/histogram/enabled',False)
 product=rep.create.render_product(str(cam.GetPath()),(960,540));rgb=rep.AnnotatorRegistry.get_annotator('rgb');rgb.attach(product);rep.orchestrator.set_capture_on_play(False)
 for i,f in enumerate(frames):
  q=f['quaternion_wxyz'];desired=Gf.Matrix4d(1.);desired.SetRotate(Gf.Quatd(q[0],Gf.Vec3d(*q[1:])));desired.SetTranslateOnly(Gf.Vec3d(*f['position']))
  op.Set(root_world*base_world.GetInverse()*desired*parent_world.GetInverse())
  rep.orchestrator.step(rt_subframes=8 if i==0 else 2,delta_time=0,pause_timeline=True)
  im=Image.fromarray(np.asarray(rgb.get_data())[...,:3].copy());draw=ImageDraw.Draw(im);distance=float(np.linalg.norm(np.array(f['position'][:2])-target))
  draw.rectangle((12,12,690,58),fill=(16,20,25));draw.text((22,20),f'KINEMATIC BASE REPLAY | t={f["sim_time"]:.2f}s | base-center distance={distance:.2f}m',fill='white');draw.text((22,38),'Green: executed path  Yellow: remaining distance  Blue: goal marker',fill='white');im.save(out/f'{i:06d}.png')
  if i%30==0:print('REPLAY_FRAME',i,flush=True)
 (out/'report.json').write_text(json.dumps({'status':'rendered','frames':len(frames),'fps':30,'resolution':[960,540],'scope':'recorded_base_pose_replay; final articulation held fixed; no physics re-simulation','camera_eye':eye.tolist(),'camera_target':look.tolist()},indent=2))
except BaseException:
 import traceback
 traceback.print_exc();os._exit(1)
finally:app.close()
