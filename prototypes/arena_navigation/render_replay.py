"""Third-person kinematic replay from recorded root pose and all joint angles."""
import argparse,json,traceback
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--gpu',type=int,required=True);a=p.parse_args();root=Path(a.run);out=root/'third-person';out.mkdir(exist_ok=False)
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'renderer':'RaytracedLighting','multi_gpu':False,'active_gpu':a.gpu,'physics_gpu':a.gpu,'extra_args':['--allow-root']})
result={'status':'started'}
try:
 import numpy as np,omni.usd,omni.replicator.core as rep,carb
 from scipy.spatial.transform import Rotation
 from pxr import Usd,UsdGeom,UsdPhysics,Gf,Sdf
 from PIL import Image
 data=json.loads((root/'capture.json').read_text());frames=data['frames'];names=json.loads((root/'report.json').read_text())['joint_names']
 layer=Sdf.Layer.CreateNew(str(out/'replay.usda'));layer.subLayerPaths=[str(root/'background.usda')];layer.Save();omni.usd.get_context().open_stage(str(out/'replay.usda'));stage=omni.usd.get_context().get_stage()
 actor=stage.DefinePrim('/World/ReplayG1','Xform');actor.GetReferences().AddReference(str(root/'robot.usda'))
 for _ in range(8):app.update()
 def transform(pos,quat):
  m=np.eye(4);m[:3,:3]=Rotation.from_quat([quat[1],quat[2],quat[3],quat[0]]).as_matrix();m[:3,3]=pos;return m
 def anchor(j,i):
  pos=getattr(j,f'GetLocalPos{i}Attr')().Get();q=getattr(j,f'GetLocalRot{i}Attr')().Get();return transform(list(pos),[q.GetReal(),*q.GetImaginary()])
 bodies={};edges=[]
 for prim in Usd.PrimRange(actor,Usd.TraverseInstanceProxies()):
  if prim.HasAPI(UsdPhysics.RigidBodyAPI):
   bodies[str(prim.GetPath())]=prim;UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
  if prim.IsA(UsdPhysics.Joint):
   j=UsdPhysics.Joint(prim);b0=j.GetBody0Rel().GetTargets();b1=j.GetBody1Rel().GetTargets()
   if not b0 or not b1:continue
   kind='fixed';axis=None
   if prim.IsA(UsdPhysics.RevoluteJoint):kind='revolute';axis=UsdPhysics.RevoluteJoint(prim).GetAxisAttr().Get()
   elif not prim.IsA(UsdPhysics.FixedJoint):raise RuntimeError(f'unsupported joint {prim.GetPath()}')
   edges.append((prim.GetName(),str(b0[0]),str(b1[0]),anchor(j,0),anchor(j,1),kind,axis))
 children={e[2] for e in edges};roots=set(bodies)-children
 if len(roots)!=1:raise RuntimeError(f'ambiguous root bodies {roots}')
 base=next(iter(roots));missing=[e[0] for e in edges if e[5]=='revolute' and e[0] not in names]
 if missing:raise RuntimeError(f'missing recorded joint angles {missing}')
 ops={}
 for path,prim in bodies.items():
  x=UsdGeom.Xformable(prim);x.ClearXformOpOrder();op=x.AddTransformOp();x.SetResetXformStack(True);ops[path]=op
 cam=UsdGeom.Camera.Define(stage,'/World/ReplayCamera');cam.CreateFocalLengthAttr(23.);cam.CreateHorizontalApertureAttr(36.);cam.CreateVerticalApertureAttr(20.25);cam.CreateClippingRangeAttr(Gf.Vec2f(.05,100));camop=UsdGeom.Xformable(cam).AddTransformOp()
 # Camera follows from the aisle side (negative Y), above the robot, with a fixed offset.
 settings=carb.settings.get_settings();settings.set_bool('/rtx/post/histogram/enabled',False)
 product=rep.create.render_product(str(cam.GetPath()),(960,540));rgb=rep.AnnotatorRegistry.get_annotator('rgb');rgb.attach(product);rep.orchestrator.set_capture_on_play(False)
 stats=[]
 for i,f in enumerate(frames):
  angles=dict(zip(names,f['joint_position']));poses={base:transform(f['position'],f['quaternion_wxyz'])};pending=edges[:]
  while pending:
   remaining=[]
   for name,b0,b1,l0,l1,kind,axis in pending:
    if b0 not in poses:remaining.append((name,b0,b1,l0,l1,kind,axis));continue
    motion=np.eye(4)
    if kind=='revolute':motion[:3,:3]=Rotation.from_rotvec(np.eye(3)['XYZ'.index(axis)]*angles[name]).as_matrix()
    poses[b1]=poses[b0]@l0@motion@np.linalg.inv(l1)
   if len(remaining)==len(pending):raise RuntimeError('joint tree cannot be resolved')
   pending=remaining
  if set(poses)!=set(bodies):raise RuntimeError('incomplete body reconstruction')
  for path,m in poses.items():ops[path].Set(Gf.Matrix4d(m.T.tolist()))
  pos=np.array(f['position']);eye=pos+np.array([0.,-1.4,1.6]);target=pos+np.array([0,0,.0]);camop.Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse())
  if i==0:
   for _ in range(6):rep.orchestrator.step(rt_subframes=8,delta_time=0,pause_timeline=True)
  rep.orchestrator.step(rt_subframes=2,delta_time=0,pause_timeline=True)
  pixels=np.asarray(rgb.get_data())[...,:3].copy()
  if pixels.shape!=(540,960,3):raise RuntimeError('invalid render dimensions')
  Image.fromarray(pixels).save(out/f'{i:06d}.png');stats.append(float(pixels.mean()))
  if float(np.mean(np.max(pixels,axis=2)<4))>.95:raise RuntimeError(f'black replay frame {i}; camera needs correction')
  if i%30==0:print('FRAME',i,len(frames),flush=True)
 result.update(status='rendered',frames=len(frames),fps=30,resolution=[960,540],body_count=len(bodies),joint_count=len(names),root_body=base,mean_luma_range=[min(stats),max(stats)],scope='USD joint-frame FK from recorded root and all joint positions; kinematic replay, not physics resimulation',camera='following offset (0,-1.4,+1.6)m in world coordinates')
except BaseException:
 result.update(status='failed',traceback=traceback.format_exc());traceback.print_exc()
finally:
 (out/'report.json').write_text(json.dumps(result,indent=2));app.close()
