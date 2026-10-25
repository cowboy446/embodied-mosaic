import hashlib,tempfile,unittest
from pathlib import Path
from pxr import Usd,UsdGeom
from stock_assets import populate_stock

class StockAssetTests(unittest.TestCase):
 def test_seeded_choice_grounding_and_source_hash(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);catalog={'assets':[]}
   for i in range(5):
    path=p/f'{i}.usda';s=Usd.Stage.CreateNew(str(path));UsdGeom.Xform.Define(s,'/Root');box=UsdGeom.Cube.Define(s,'/Root/Box');box.CreateSizeAttr(i+1)
    UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.SetStageUpAxis(s,UsdGeom.Tokens.z);s.GetRootLayer().Save()
    catalog['assets'].append({'status':'inventoried','catalog_entry':{'key':str(i),'floor':True},'source':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
   def create(seed):
    stage=Usd.Stage.CreateInMemory();r=populate_stock(stage,catalog,[(2,3),(4,5)],seed)
    for item in r['assets']:
     bound=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default']).ComputeWorldBound(stage.GetPrimAtPath(item['path'])).ComputeAlignedRange()
     self.assertAlmostEqual(bound.GetMin()[2],0)
     self.assertAlmostEqual((bound.GetMin()[0]+bound.GetMax()[0])/2,item['anchor_xy'][0])
    return r
   self.assertEqual(create(4),create(4));self.assertNotEqual(create(4)['assets'],create(5)['assets'])
   catalog['assets'][0]['source_sha256']='bad'
   with self.assertRaises(ValueError):populate_stock(Usd.Stage.CreateInMemory(),catalog,[(0,0)]*5,1)
if __name__=='__main__':unittest.main()
