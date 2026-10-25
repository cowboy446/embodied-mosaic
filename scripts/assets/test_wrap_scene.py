import hashlib,tempfile,unittest
from pathlib import Path
from pxr import Usd,UsdGeom,UsdPhysics
from wrap_scene import wrap

class WrapperTests(unittest.TestCase):
    def make_source(self,p):
        s=Usd.Stage.CreateNew(str(p));UsdGeom.Xform.Define(s,'/Root')
        UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.SetStageUpAxis(s,UsdGeom.Tokens.z)
        UsdGeom.Cube.Define(s,'/Root/Box');UsdPhysics.Scene.Define(s,'/Root/Physics')
        s.GetRootLayer().Save();return s
    def test_preserves_source_and_geometry(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);s=self.make_source(p/'source.usda');before=(p/'source.usda').read_bytes()
            r=wrap(p/'source.usda',p/'out.usda');w=Usd.Stage.Open(str(p/'out.usda'))
            self.assertTrue(w.GetPrimAtPath('/World/Environment/Box'))
            self.assertFalse(w.GetPrimAtPath('/World/Environment/Physics').IsActive())
            self.assertTrue(s.GetPrimAtPath('/Root/Physics').IsActive())
            self.assertEqual(before,(p/'source.usda').read_bytes())
            self.assertEqual(r['stock_objects_added'],0)
            with self.assertRaises(FileExistsError):wrap(p/'source.usda',p/'out.usda')
    def test_rejects_silent_conversion_and_dropped_roots(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);s=self.make_source(p/'source.usda')
            UsdGeom.SetStageMetersPerUnit(s,.01);s.GetRootLayer().Save()
            with self.assertRaises(ValueError):wrap(p/'source.usda',p/'bad.usda')
            UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.Xform.Define(s,'/Other');s.GetRootLayer().Save()
            with self.assertRaises(ValueError):wrap(p/'source.usda',p/'bad.usda')
            self.assertFalse((p/'bad.usda').exists())
if __name__=='__main__':unittest.main()
