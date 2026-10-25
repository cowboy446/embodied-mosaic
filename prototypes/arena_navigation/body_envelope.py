"""Runtime world AABB of authored robot collision bounds driven by measured link poses.
Conservative for authored primitive/mesh geometry; cooking approximations and contacts
still require separate verification. Does not infer collision bounds from link origins.
"""
import itertools
import numpy as np
from pxr import Usd,UsdGeom,UsdPhysics
from scipy.spatial.transform import Rotation
class BodyEnvelopeAudit:
 def __init__(self,stage,robot_root,body_names):
  root=stage.GetPrimAtPath(robot_root);cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','proxy','render','guide'],False,True);names={n:i for i,n in enumerate(body_names)};self.shapes=[];self.geometry=[];missing=[];xcache=UsdGeom.XformCache()
  for prim in Usd.PrimRange(root,Usd.TraverseInstanceProxies()):
   if not prim.HasAPI(UsdPhysics.CollisionAPI):continue
   if not UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get():continue
   body=prim
   while body and body!=root and not body.HasAPI(UsdPhysics.RigidBodyAPI):body=body.GetParent()
   name=body.GetName() if body else ''
   if name not in names:missing.append({'path':str(prim.GetPath()),'body':name,'reason':'body_not_mapped'});continue
   bound=cache.ComputeRelativeBound(prim,body).ComputeAlignedRange()
   if bound.IsEmpty():missing.append({'path':str(prim.GetPath()),'reason':'empty_bounds'});continue
   lo,hi=bound.GetMin(),bound.GetMax();corners=np.array(list(itertools.product(*[(lo[i],hi[i]) for i in range(3)])))
   if not np.isfinite(corners).all():raise ValueError('nonfinite collision bounds')
   self.shapes.append((str(prim.GetPath()),names[name],corners))
   local=np.asarray(xcache.ComputeRelativeTransform(prim,body)[0]).T
   if prim.IsA(UsdGeom.Sphere):
    radius=float(UsdGeom.Sphere(prim).GetRadiusAttr().Get());self.geometry.append(('sphere',names[name],local,radius,str(prim.GetPath())))
   elif prim.IsA(UsdGeom.Mesh):
    points=np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get());points=points@local[:3,:3].T+local[:3,3];self.geometry.append(('points',names[name],points,None,str(prim.GetPath())))
   elif prim.IsA(UsdGeom.Cube):
    h=float(UsdGeom.Cube(prim).GetSizeAttr().Get())/2;points=np.array(list(itertools.product([-h,h],repeat=3)));points=points@local[:3,:3].T+local[:3,3];self.geometry.append(('points',names[name],points,None,str(prim.GetPath())))
   else:raise RuntimeError(f'unsupported exact geometry {prim.GetTypeName()}')
  if missing or not self.shapes:raise RuntimeError(f'Unmapped collision geometry: {missing}; shapes={len(self.shapes)}')
  self.rows=[]
 def sample(self,t,positions,quaternions,root_xy,root_quaternion=None):
  matrices=Rotation.from_quat(np.asarray(quaternions)[:,[1,2,3,0]]).as_matrix();points=np.concatenate([corners@matrices[i].T+positions[i] for _,i,corners in self.shapes])
  row={'time_s':t,'max_abs_xy_from_root_m':np.max(np.abs(points[:,:2]-root_xy),axis=0).tolist(),'min_z_m':float(points[:,2].min()),'max_z_m':float(points[:,2].max())}
  if root_quaternion is not None:
   w,x,y,z=np.asarray(root_quaternion);yaw=np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z))
   c,s=np.cos(yaw),np.sin(yaw);local_xy=(points[:,:2]-root_xy)@np.array([[c,-s],[s,c]])
   row['heading_frame_xy_min_m']=local_xy.min(axis=0).tolist();row['heading_frame_xy_max_m']=local_xy.max(axis=0).tolist()
   row['root_yaw_rad']=float(yaw)
  minimum=[]
  for kind,i,value,radius,path in self.geometry:
   if kind=='sphere':
    center=matrices[i]@value[:3,3]+positions[i];z=float(center[2]-radius*np.linalg.norm((matrices[i]@value[:3,:3])[2]))
   else:z=float(np.min(value@matrices[i][2])+positions[i,2])
   minimum.append((z,path))
  row['geometry_min_z_m'],row['lowest_geometry_path']=min(minimum)
  self.rows.append(row)
  return row
 def summary(self):return {'shape_count':len(self.shapes),'collider_paths':[x[0] for x in self.shapes],'samples':self.rows,'scope':'measured link transforms applied to authored collider AABBs; excludes cooking expansion and contact-force certification'}
