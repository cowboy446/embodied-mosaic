import unittest,types
from pxr import Usd,UsdGeom,UsdPhysics,Gf
from random_stock import randomize_stock,validate_stock,PlacementRejected

def scene():
 s=Usd.Stage.CreateInMemory();UsdGeom.Xform.Define(s,'/World');UsdGeom.Xform.Define(s,'/World/Stock')
 item=UsdGeom.Xform.Define(s,'/World/Stock/item');item.AddTranslateOp().Set(Gf.Vec3d(0,0,.5));item.AddRotateZOp().Set(0)
 cube=UsdGeom.Cube.Define(s,'/World/Stock/item/mesh');cube.CreateSizeAttr(1.);UsdPhysics.CollisionAPI.Apply(cube.GetPrim()).CreateCollisionEnabledAttr(True)
 return s
class Query:
 def __init__(self,collision=False):self.collision=collision
 def overlap_box(self,e,c,q,callback,anyhit):
  if self.collision:callback(types.SimpleNamespace(collision='/World/Wall'))
 def raycast_all(self,o,d,l,callback):callback(types.SimpleNamespace(collision='/World/Floor',position=(o[0],o[1],0),normal=(0,0,1)))
class StockTests(unittest.TestCase):
 def test_repeatable_randomization(self):
  a,b=scene(),scene();self.assertEqual(randomize_stock(a,10),randomize_stock(b,10))
 def test_bounded_infeasible_pair_keeps_evidence(self):
  s=scene();item=UsdGeom.Xform.Define(s,'/World/Stock/second');item.AddTranslateOp().Set(Gf.Vec3d(0,0,.5));item.AddRotateZOp().Set(0)
  cube=UsdGeom.Cube.Define(s,'/World/Stock/second/mesh');cube.CreateSizeAttr(1.)
  with self.assertRaises(PlacementRejected) as raised:randomize_stock(s,10,translation_radius=0,max_trials_per_object=3)
  self.assertEqual(len(raised.exception.evidence['attempts']),4)
 def test_environment_obstacle_rejected_before_simulation(self):
  s=scene();UsdGeom.Xform.Define(s,'/World/Environment')
  # Mesh rather than Cube matches production normalized environment meshes.
  m=UsdGeom.Mesh.Define(s,'/World/Environment/wall');m.CreatePointsAttr([(-2,-2,0),(2,2,2)])
  UsdPhysics.CollisionAPI.Apply(m.GetPrim()).CreateCollisionEnabledAttr(True)
  with self.assertRaises(PlacementRejected) as raised:randomize_stock(s,10,translation_radius=0,max_trials_per_object=2)
  self.assertIn('/World/Environment/wall',raised.exception.evidence['attempts'][0]['conflicts'])
 def test_reserved_spawn_rejected(self):
  with self.assertRaises(PlacementRejected):randomize_stock(scene(),10,translation_radius=0,max_trials_per_object=2,reserved_xy=[(0,0)])
 def test_overlap_rejected(self):
  self.assertTrue(validate_stock(scene(),Query(),'/World/Stock')['passed'])
  self.assertFalse(validate_stock(scene(),Query(True),'/World/Stock')['passed'])
if __name__=='__main__':unittest.main()
