"""Export collider world AABBs from the immutable background used by a probe."""
from pxr import Usd,UsdGeom,UsdPhysics
from pathlib import Path
import json,sys
p=Path(sys.argv[1]);s=Usd.Stage.Open(str(p/'background.usda'));cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render','proxy']);rows=[]
for prim in Usd.PrimRange(s.GetDefaultPrim(),Usd.TraverseInstanceProxies()):
 if prim.HasAPI(UsdPhysics.CollisionAPI):
  b=cache.ComputeWorldBound(prim).ComputeAlignedRange()
  if not b.IsEmpty():rows.append({'path':str(prim.GetPath()),'min':list(b.GetMin()),'max':list(b.GetMax()),'type':prim.GetTypeName()})
(p/'scene-bounds.json').write_text(json.dumps({'colliders':rows,'source':'background.usda; identity Arena warehouse placement in env_0; world-axis-aligned bounds'},indent=2));print('colliders',len(rows));print(rows[:3])
