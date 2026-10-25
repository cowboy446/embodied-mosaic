"""Seeded stock-pose variation and conservative initialization checks.
Existing textured assets retain their material/geometry and static/dynamic status.
This does not add grasp annotations or certify rigid-body settling.
"""
import random
from pxr import Usd,UsdGeom,UsdPhysics,Gf


def randomize_stock(stage,seed,translation_radius=.75):
    stock=stage.GetPrimAtPath('/World/Stock')
    if not stock:raise ValueError('scene has no reusable stock assets')
    rng=random.Random(seed);records=[]
    for prim in sorted(stock.GetChildren(),key=lambda p:str(p.GetPath())):
        ops={op.GetOpType():op for op in UsdGeom.Xformable(prim).GetOrderedXformOps()}
        translate=ops.get(UsdGeom.XformOp.TypeTranslate);rotate=ops.get(UsdGeom.XformOp.TypeRotateZ)
        if translate is None or rotate is None:raise ValueError(f'unsupported stock transform {prim.GetPath()}')
        before=list(translate.Get());yaw=float(rotate.Get())
        after=[before[0]+rng.uniform(-translation_radius,translation_radius),before[1]+rng.uniform(-translation_radius,translation_radius),before[2]]
        heading=rng.uniform(-180,180);translate.Set(Gf.Vec3d(*after));rotate.Set(heading)
        records.append({'path':str(prim.GetPath()),'before_xyz':before,'after_xyz':after,'before_yaw_deg':yaw,'after_yaw_deg':heading})
    if not records:raise ValueError('empty stock collection')
    return {'seed':seed,'translation_radius_m':translation_radius,'assets':records,'scope':'pose randomization; geometry validation required before rollout'}


def validate_stock(stage,query,stock_root):
    root=stage.GetPrimAtPath(stock_root)
    if not root:raise ValueError(f'missing composed stock root {stock_root}')
    cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render','proxy'],False,True)
    rows=[]
    for prim in root.GetChildren():
        bound=cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if bound.IsEmpty():raise ValueError(f'empty stock bounds: {prim.GetPath()}')
        lo=list(bound.GetMin());hi=list(bound.GetMax());path=str(prim.GetPath());hits=[]
        # Exclude only the floor-contact slab; preserve the full upper AABB.
        zlo=max(lo[2]+.04,.04);zhi=hi[2]
        if zhi<=zlo:raise ValueError('stock too thin for this floor-placement validator')
        ext=((hi[0]-lo[0])/2,(hi[1]-lo[1])/2,(zhi-zlo)/2)
        center=((hi[0]+lo[0])/2,(hi[1]+lo[1])/2,(zhi+zlo)/2)
        def overlap(hit):
            collider=str(hit.collision)
            if collider!=path and not collider.startswith(path+'/'):hits.append(collider)
            return True
        query.overlap_box(ext,center,(0.,0.,0.,1.),overlap,False)
        support=[]
        for x,y in [(center[0],center[1]),(lo[0],lo[1]),(lo[0],hi[1]),(hi[0],lo[1]),(hi[0],hi[1])]:
            found=[]
            def ray(hit):
                collider=str(hit.collision)
                if collider!=path and not collider.startswith(path+'/'):
                    if abs(float(hit.position[2]))<=.03 and float(hit.normal[2])>=.95:found.append(collider)
                return True
            query.raycast_all((x,y,.25),(0.,0.,-1.),.5,ray)
            support.append(bool(found))
        descendants=list(Usd.PrimRange(prim,Usd.TraverseInstanceProxies()))
        colliders=[str(p.GetPath()) for p in descendants if p.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get()]
        bodies=[str(p.GetPath()) for p in descendants if p.HasAPI(UsdPhysics.RigidBodyAPI) and UsdPhysics.RigidBodyAPI(p).GetRigidBodyEnabledAttr().Get()]
        rows.append({'path':path,'enabled_colliders':colliders,'rigid_bodies':bodies,'physics_kind':'dynamic_or_kinematic' if bodies else 'static','bounds':[lo,hi],'overlap_paths':sorted(set(hits)),'support_samples':support,'passed':bool(colliders) and not hits and all(support) and abs(lo[2])<=.03})
    return {'passed':bool(rows) and all(r['passed'] for r in rows),'objects':rows,'scope':'conservative initial AABB and five-ray flat-floor support checks; not contact/settling certification'}
