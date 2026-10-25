"""USD-only geometry checks; run with Isaac's pxr and numpy/scipy runtime."""
import unittest
import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics, Gf
from body_envelope import BodyEnvelopeAudit

class EnvelopeTests(unittest.TestCase):
 def test_guide_sphere_rotates_in_link_frame(self):
  stage=Usd.Stage.CreateInMemory()
  UsdGeom.Xform.Define(stage,'/Robot')
  body=UsdGeom.Xform.Define(stage,'/Robot/link')
  UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
  sphere=UsdGeom.Sphere.Define(stage,'/Robot/link/collision')
  sphere.CreateRadiusAttr(.1)
  sphere.CreatePurposeAttr('guide')
  sphere.AddTranslateOp().Set(Gf.Vec3d(.2,0,0))
  UsdPhysics.CollisionAPI.Apply(sphere.GetPrim()).CreateCollisionEnabledAttr(True)
  audit=BodyEnvelopeAudit(stage,'/Robot',['link'])
  # +90 deg around Y takes local +X toward world -Z.
  q=np.array([[2**-.5,0,2**-.5,0]])
  row=audit.sample(0,np.array([[3,4,1.]]),q,np.array([3,4]))
  self.assertAlmostEqual(row['geometry_min_z_m'],.7,places=6)
  self.assertEqual(audit.summary()['shape_count'],1)
  heading=audit.sample(1,np.array([[3,4,1.]]),np.array([[1,0,0,0]]),np.array([3,4]),np.array([2**-.5,0,0,2**-.5]))
  np.testing.assert_allclose(heading['heading_frame_xy_min_m'],[-.1,-.3],atol=1e-6)
  np.testing.assert_allclose(heading['heading_frame_xy_max_m'],[.1,-.1],atol=1e-6)
 def test_mesh_lower_bound_uses_vertices_not_rotated_aabb(self):
  stage=Usd.Stage.CreateInMemory();UsdGeom.Xform.Define(stage,'/Robot')
  body=UsdGeom.Xform.Define(stage,'/Robot/link');UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
  mesh=UsdGeom.Mesh.Define(stage,'/Robot/link/collision')
  mesh.CreatePointsAttr([(-1,0,0),(0,0,-1),(1,0,0)])
  mesh.CreateFaceVertexCountsAttr([3]);mesh.CreateFaceVertexIndicesAttr([0,1,2])
  UsdPhysics.CollisionAPI.Apply(mesh.GetPrim()).CreateCollisionEnabledAttr(True)
  audit=BodyEnvelopeAudit(stage,'/Robot',['link'])
  # Rotate Y by 45 degrees, then translate up by 2m.
  q=np.array([[np.cos(np.pi/8),0,np.sin(np.pi/8),0]])
  row=audit.sample(0,np.array([[0,0,2.]]),q,np.array([0,0]))
  self.assertAlmostEqual(row['geometry_min_z_m'],2-2**-.5,places=6)
if __name__=='__main__':unittest.main()
