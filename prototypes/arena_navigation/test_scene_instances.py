import unittest
from pxr import Usd, UsdGeom
from scene_instances import make_environment_editable
class InstanceTests(unittest.TestCase):
 def test_source_remains_instanceable(self):
  source=Usd.Stage.CreateInMemory();UsdGeom.Xform.Define(source,'/World');UsdGeom.Xform.Define(source,'/Asset')
  UsdGeom.Mesh.Define(source,'/Asset/Mesh')
  UsdGeom.Xform.Define(source,'/World/Environment')
  inst=source.DefinePrim('/World/Environment/Item','Xform');inst.GetReferences().AddInternalReference('/Asset');inst.SetInstanceable(True)
  before=source.GetRootLayer().ExportToString()
  stage=Usd.Stage.CreateInMemory();stage.GetRootLayer().subLayerPaths=[source.GetRootLayer().identifier]
  self.assertTrue(stage.GetPrimAtPath('/World/Environment/Item/Mesh').IsInstanceProxy())
  self.assertEqual(make_environment_editable(stage,'/World/Environment'),['/World/Environment/Item'])
  self.assertFalse(stage.GetPrimAtPath('/World/Environment/Item/Mesh').IsInstanceProxy())
  self.assertEqual(source.GetRootLayer().ExportToString(),before)
  self.assertTrue(source.GetPrimAtPath('/World/Environment/Item').IsInstance())
if __name__=='__main__':unittest.main()
