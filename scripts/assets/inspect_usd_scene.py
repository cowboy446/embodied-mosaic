"""Read-only scene inventory before any Isaac-specific authoring."""
import argparse
import json
import math
from collections import Counter
from pathlib import Path
from pxr import Usd, UsdGeom, UsdPhysics


def inspect(source):
    source=Path(source).resolve(strict=True)
    stage=Usd.Stage.Open(str(source))
    if not stage: raise ValueError('USD stage could not be opened')
    counts=Counter(); joints=[]; roots=[]; dynamic=[]; materials=[]
    for prim in Usd.PrimRange.Stage(stage,Usd.TraverseInstanceProxies()):
        counts['prims']+=1
        if prim.IsInstanceProxy():counts['instance_proxy_prims']+=1
        if prim.IsA(UsdGeom.Mesh):counts['meshes']+=1
        if prim.GetTypeName()=='Material':materials.append(str(prim.GetPath()))
        if any(str(rel.GetName()).startswith('material:binding') and rel.GetTargets() for rel in prim.GetRelationships()):
            counts['prims_with_authored_material_binding']+=1
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            counts['collision_api_prims']+=1
            if UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get():counts['enabled_collision_prims']+=1
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            body=UsdPhysics.RigidBodyAPI(prim)
            dynamic.append({'path':str(prim.GetPath()),'enabled':body.GetRigidBodyEnabledAttr().Get(),
                            'kinematic':body.GetKinematicEnabledAttr().Get()})
        if prim.IsA(UsdPhysics.Joint):
            record={'path':str(prim.GetPath()),'type':str(prim.GetTypeName())}
            for name in ['physics:lowerLimit','physics:upperLimit','physics:axis','physics:jointEnabled']:
                attr=prim.GetAttribute(name)
                if attr:
                    v=attr.Get()
                    record[name]=str(v) if isinstance(v,float) and not math.isfinite(v) else v
            joints.append(record)
    cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),[UsdGeom.Tokens.default_,UsdGeom.Tokens.render,UsdGeom.Tokens.proxy],useExtentsHint=True)
    for prim in stage.GetPseudoRoot().GetChildren():
        bound=cache.ComputeWorldBound(prim).ComputeAlignedRange()
        bounds=None if bound.IsEmpty() else {'min':list(bound.GetMin()),'max':list(bound.GetMax())}
        roots.append({'path':str(prim.GetPath()),'type':str(prim.GetTypeName()),'bounds_stage_units':bounds})
    return {'source':str(source),'default_prim':str(stage.GetDefaultPrim().GetPath()) if stage.GetDefaultPrim() else None,
            'up_axis':str(UsdGeom.GetStageUpAxis(stage)), 'meters_per_unit':UsdGeom.GetStageMetersPerUnit(stage),
            'counts':dict(counts),'roots':roots,'material_paths':materials,'rigid_bodies':dynamic,'joints':joints,
            'scope':'composed authored scene at default time; no rendering or physics validation',
            'limitations':['Material binding counts do not prove shader or texture correctness.',
                           'Bounds include visible-purpose geometry, not swept robot clearance.',
                           'Collision schemas do not prove successful PhysX cooking.',
                           'Unit and up-axis differences require explicit conversion before integration.']}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--output',required=True);a=p.parse_args()
    result=inspect(a.source)
    Path(a.output).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['default_prim','up_axis','meters_per_unit','counts']}))
