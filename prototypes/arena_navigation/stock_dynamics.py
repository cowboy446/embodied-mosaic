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
    if len(rows)<61:return {'passed':False,'reason':'insufficient_samples_for_two_seconds'}
    times=np.asarray([r['time_s'] for r in rows]);pos=np.asarray([r['transforms'] for r in rows]);vel=np.asarray([r['velocities'] for r in rows])
    if not np.isfinite(times).all() or not np.isfinite(pos).all() or not np.isfinite(vel).all():return {'passed':False,'reason':'nonfinite_states'}
    if pos.ndim!=3 or pos.shape[1]<1 or pos.shape[2]!=7 or vel.shape!=(*pos.shape[:2],6):return {'passed':False,'reason':'invalid_state_shapes'}
    if abs(times[0])>1e-6 or times[-1]<2.-1e-6 or not np.allclose(np.diff(times),1/30,atol=1e-6):return {'passed':False,'reason':'incomplete_or_discontinuous_clock'}
    norms=np.linalg.norm(pos[:,:,3:],axis=-1)
    if np.max(np.abs(norms-1))>.001:return {'passed':False,'reason':'invalid_quaternion'}
    drift=np.linalg.norm(pos[-1,:,:3]-pos[0,:,:3],axis=1)
    peak=np.linalg.norm(pos[:,:,:3]-pos[0,:,:3],axis=-1).max(axis=0)
    q=pos[:,:,3:]/norms[:,:,None]
    angle=np.degrees(2*np.arccos(np.clip(np.abs((q*q[0]).sum(axis=-1)),0,1))).max(axis=0)
    tail=vel[times>=times[-1]-.5]
    speed=np.linalg.norm(tail[:,:,:3],axis=-1).max(axis=0)
    angular=np.linalg.norm(tail[:,:,3:],axis=-1).max(axis=0)
    return {'passed':bool((peak<=translation_limit).all() and (angle<=10.).all() and (speed<=speed_limit).all() and (angular<=.05).all()),'duration_s':float(times[-1]),'translation_drift_m':drift.tolist(),'max_translation_excursion_m':peak.tolist(),'max_orientation_change_deg':angle.tolist(),'max_tail_linear_speed_m_s':speed.tolist(),'max_tail_angular_speed_rad_s':angular.tolist(),'translation_limit_m':translation_limit,'orientation_limit_deg':10.,'speed_limit_m_s':speed_limit,'angular_speed_limit_rad_s':.05,'scope':'full recorded rigid-body drift/rotation and terminal velocity probe; contact penetration and material validation remain separate'}
