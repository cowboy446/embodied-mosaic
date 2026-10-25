"""Explicit synthetic physical parameters for stock initialization probes."""
from pxr import Usd,UsdGeom,UsdPhysics


def enable_stock_dynamics(stage,mass_kg=5.):
    root=stage.GetPrimAtPath('/World/Stock')
    if not root:raise ValueError('missing stock')
    records=[]
    for prim in root.GetChildren():
        descendants=list(Usd.PrimRange(prim,Usd.TraverseInstanceProxies()))
        if any(p.HasAPI(UsdPhysics.RigidBodyAPI) for p in descendants):raise ValueError('nested/existing rigid-body stock requires explicit adapter')
        meshes=[p for p in descendants if p.IsA(UsdGeom.Mesh) and p.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get()]
        if not meshes:raise ValueError(f'no collider: {prim.GetPath()}')
        for mesh in meshes:
            if mesh.IsInstanceProxy():raise ValueError('stock instance must be made editable first')
            UsdPhysics.MeshCollisionAPI.Apply(mesh).CreateApproximationAttr('convexHull')
        body=UsdPhysics.RigidBodyAPI.Apply(prim);body.CreateRigidBodyEnabledAttr(True);body.CreateKinematicEnabledAttr(False)
        UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(mass_kg)
        records.append({'path':str(prim.GetPath()),'mass_kg':mass_kg,'collision_approximation':'convexHull','mass_source':'synthetic initialization-test assumption'})
    return records


def summarize(rows,translation_limit=.05,speed_limit=.02):
    import numpy as np
    if len(rows)<2:return {'passed':False,'reason':'insufficient_samples'}
    pos=np.asarray([r['transforms'] for r in rows]);vel=np.asarray([r['velocities'] for r in rows])
    if not np.isfinite(pos).all() or not np.isfinite(vel).all():return {'passed':False,'reason':'nonfinite_states'}
    drift=np.linalg.norm(pos[-1,:,:3]-pos[0,:,:3],axis=1)
    tail=vel[max(0,len(rows)-15):]
    speed=np.linalg.norm(tail[:,:,:3],axis=-1).max(axis=0)
    angular=np.linalg.norm(tail[:,:,3:],axis=-1).max(axis=0)
    return {'passed':bool((drift<=translation_limit).all() and (speed<=speed_limit).all() and (angular<=.05).all()),'translation_drift_m':drift.tolist(),'max_tail_linear_speed_m_s':speed.tolist(),'max_tail_angular_speed_rad_s':angular.tolist(),'translation_limit_m':translation_limit,'speed_limit_m_s':speed_limit,'angular_speed_limit_rad_s':.05,'scope':'2-second rigid-body drift and terminal velocity probe; contact penetration and material validation remain separate'}
