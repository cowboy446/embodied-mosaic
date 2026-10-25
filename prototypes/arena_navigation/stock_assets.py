"""Compose seeded prop choices at explicit placement anchors, retaining provenance."""
import hashlib,math,random
from pathlib import Path
from pxr import Usd,UsdGeom,UsdPhysics,Gf


def populate_stock(stage, catalog, anchors, seed):
    if not anchors or any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in anchors):
        raise ValueError('finite XY anchors required')
    candidates=sorted([r for r in catalog['assets'] if r.get('status')=='inventoried' and r['catalog_entry'].get('floor')],key=lambda r:r['catalog_entry']['key'])
    if len(candidates)<len(anchors):raise ValueError('not enough distinct floor candidates')
    selected=random.Random(seed).sample(candidates,len(anchors))
    stock=stage.GetPrimAtPath('/World/Stock')
    if stock and list(stock.GetChildren()):raise ValueError('stock must be empty; do not overwrite existing assets')
    UsdGeom.Xform.Define(stage,'/World/Stock');prepared=[]
    # Validate every chosen source before authoring any object.
    for record in selected:
        path=Path(record['source']).resolve(strict=True)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['source_sha256']:raise ValueError(f'asset changed: {path}')
        source=Usd.Stage.Open(str(path));roots=list(source.GetPseudoRoot().GetChildren())
        if len(roots)!=1 or not roots[0].IsA(UsdGeom.Xform):raise ValueError('explicit source root adapter required')
        if UsdGeom.GetStageUpAxis(source)!='Z' or abs(UsdGeom.GetStageMetersPerUnit(source)-1)>1e-9:raise ValueError('units adapter required')
        if any(p.HasAPI(UsdPhysics.RigidBodyAPI) or p.IsA(UsdPhysics.Joint) for p in source.Traverse()):raise ValueError('articulated/dynamic asset requires dedicated adapter')
        prepared.append((record,path,roots[0].GetPath()))
    rows=[]
    for i,((record,path,source_root),xy) in enumerate(zip(prepared,anchors)):
        target=f'/World/Stock/item{i:02d}';obj=UsdGeom.Xform.Define(stage,target)
        translation=obj.AddTranslateOp();translation.Set(Gf.Vec3d(0,0,0));obj.AddRotateZOp().Set(0.)
        centered=UsdGeom.Xform.Define(stage,target+'/Centered')
        geometry=UsdGeom.Xform.Define(stage,target+'/Centered/Asset');geometry.GetPrim().GetReferences().AddReference(str(path),source_root)
        bounds=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render','proxy']).ComputeWorldBound(obj.GetPrim()).ComputeAlignedRange()
        if bounds.IsEmpty():raise ValueError('empty source geometry')
        lo,hi=bounds.GetMin(),bounds.GetMax()
        centered.AddTranslateOp().Set(Gf.Vec3d(-(lo[0]+hi[0])/2,-(lo[1]+hi[1])/2,-lo[2]))
        offset=(float(xy[0]),float(xy[1]),0.)
        translation.Set(Gf.Vec3d(*offset))
        rows.append({'path':target,'asset_key':record['catalog_entry']['key'],'source':str(path),'source_sha256':record['source_sha256'],'anchor_xy':list(xy),'translation':list(offset)})
    return {'seed':seed,'candidate_count':len(candidates),'assets':rows,'scope':'seeded composition; placement and runtime stability not yet validated'}
