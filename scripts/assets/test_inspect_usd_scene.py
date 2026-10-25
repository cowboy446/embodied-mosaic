import tempfile,unittest
from pathlib import Path
from pxr import Usd,UsdGeom,UsdPhysics
from inspect_usd_scene import inspect

class SceneTests(unittest.TestCase):
    def test_nonmeter_scene_and_collision_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'scene.usda';s=Usd.Stage.CreateNew(str(p))
            world=UsdGeom.Xform.Define(s,'/Root');s.SetDefaultPrim(world.GetPrim())
            UsdGeom.SetStageUpAxis(s,UsdGeom.Tokens.y);UsdGeom.SetStageMetersPerUnit(s,.01)
            box=UsdGeom.Cube.Define(s,'/Root/Box');box.CreateSizeAttr(100.)
            UsdPhysics.CollisionAPI.Apply(box.GetPrim());UsdPhysics.RigidBodyAPI.Apply(box.GetPrim())
            joint=UsdPhysics.RevoluteJoint.Define(s,'/Root/Hinge');joint.CreateLowerLimitAttr(-30);joint.CreateUpperLimitAttr(45)
            s.GetRootLayer().Save();r=inspect(p)
            self.assertEqual(r['default_prim'],'/Root');self.assertEqual(r['up_axis'],'Y')
            self.assertEqual(r['meters_per_unit'],.01)
            self.assertEqual(r['counts']['enabled_collision_prims'],1)
            self.assertEqual(len(r['rigid_bodies']),1)
            self.assertEqual(r['joints'][0]['physics:upperLimit'],45)
            self.assertEqual(r['roots'][0]['bounds_stage_units']['max'],[50.,50.,50.])
if __name__=='__main__':unittest.main()
