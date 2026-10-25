"""Node43 PhysX query test with adversarial obstacles, not a policy episode."""
import argparse,json,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--gpu',type=int,required=True);p.add_argument('--output',required=True);a=p.parse_args()
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'multi_gpu':False,'active_gpu':a.gpu,'extra_args':['--allow-root']})
report={'tests':[],'status':'started'}
try:
 import omni.usd,omni.physx
 from pxr import UsdGeom,UsdPhysics,Gf
 from isaacsim.core.api import World
 from collision_guard import BaseCollisionGuard,Envelope
 world=World(stage_units_in_meters=1,physics_dt=1/120,rendering_dt=1/30)
 stage=omni.usd.get_context().get_stage()
 def cube(name,position,size):
  c=UsdGeom.Cube.Define(stage,name);c.CreateSizeAttr(1.)
  c.AddTranslateOp().Set(Gf.Vec3d(*position));c.AddScaleOp().Set(Gf.Vec3f(*size));UsdPhysics.CollisionAPI.Apply(c.GetPrim());return c.GetPrim()
 own=cube('/World/robot/self',(0,0,.4),(.7,.6,.7))
 obstacle=cube('/World/obstacle',(.85,.18,.3),(.03,.03,.2))
 guard=BaseCollisionGuard(omni.physx.get_physx_scene_query_interface(),Envelope(.45,.35,.025,1.5),'/World/robot')
 def refresh():
  for _ in range(4):world.step(render=False)
 world.reset();refresh()
 assert guard.blocked((0,0),0,.5);report['tests'].append('thin_off_axis_obstacle_detected')
 obstacle.SetActive(False);refresh()
 assert not guard.blocked((0,0),0,.5);report['tests'].append('own_body_filtered_and_clear_path')
 obstacle.SetActive(True);UsdGeom.Xformable(obstacle).GetOrderedXformOps()[0].Set(Gf.Vec3d(.3,.55,.3));refresh()
 assert not guard.blocked((0,0),0,0);assert guard.blocked((0,0),0,0,True);report['tests'].append('rotation_envelope_detects_side_obstacle')
 obstacle.SetActive(False);cube('/World/overhead',(.7,0,1.3),(.1,.1,.1));refresh()
 assert guard.blocked((0,0),0,.4);report['tests'].append('overhead_obstacle_detected')
 report['status']='passed_query_tests'
except BaseException:
 import traceback
 report.update(status='failed',traceback=traceback.format_exc())
finally:
 Path(a.output).write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True);app.close()
