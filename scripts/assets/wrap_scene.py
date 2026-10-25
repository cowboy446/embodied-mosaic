"""Non-destructive scene entry adapter for the Arena navigation runner.
References one source root; never flattens or rewrites third-party assets.
"""
import argparse
import hashlib
import json
from pathlib import Path
from pxr import Usd, UsdGeom, UsdPhysics


def wrap(source, output, replace_render_settings=False):
    source=Path(source).resolve(strict=True);output=Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    stage=Usd.Stage.Open(str(source))
    if not stage:raise ValueError('cannot open source')
    roots=list(stage.GetPseudoRoot().GetChildren());replaced=[]
    if replace_render_settings:
        for prim in list(roots):
            if str(prim.GetPath())!='/Render':continue
            descendants=list(Usd.PrimRange(prim))
            if any(str(p.GetTypeName()) not in ['', 'Scope', 'RenderProduct', 'RenderSettings', 'RenderVar'] or p.GetAppliedSchemas() for p in descendants):
                raise ValueError('Render subtree contains non-render content; explicit adapter required')
            replaced=[{'path':str(p.GetPath()),'type':str(p.GetTypeName())} for p in descendants]
            roots.remove(prim)
    if len(roots)!=1:
        raise ValueError('multiple source roots need an explicit composition adapter; no roots will be dropped')
    if str(UsdGeom.GetStageUpAxis(stage))!='Z' or abs(UsdGeom.GetStageMetersPerUnit(stage)-1.)>1e-9:
        raise ValueError('explicit units/up-axis conversion required before physics integration')
    source_root=roots[0]
    if not source_root.IsA(UsdGeom.Xform):raise ValueError('source root must be an Xform')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    output.parent.mkdir(parents=True,exist_ok=True)
    wrapper=Usd.Stage.CreateNew(str(output))
    world=UsdGeom.Xform.Define(wrapper,'/World');wrapper.SetDefaultPrim(world.GetPrim())
    UsdGeom.SetStageMetersPerUnit(wrapper,1.);UsdGeom.SetStageUpAxis(wrapper,UsdGeom.Tokens.z)
    env=UsdGeom.Xform.Define(wrapper,'/World/Environment')
    env.GetPrim().GetReferences().AddReference(str(source),source_root.GetPath())
    UsdGeom.Xform.Define(wrapper,'/World/Stock')
    # Arena owns the simulation scene. Preserve the source's other physics schemas.
    disabled=[]
    for prim in list(wrapper.Traverse()):
        if prim.IsA(UsdPhysics.Scene):
            prim.SetActive(False);disabled.append(str(prim.GetPath()))
    wrapper.GetRootLayer().Save()
    if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise RuntimeError('source changed during wrapping')
    report={'source':str(source),'source_sha256':digest,'source_root':str(source_root.GetPath()),
            'output':str(output),'disabled_physics_scenes':disabled,'stock_objects_added':0,'replaced_render_settings':replaced,'render_settings_owner':'IsaacLab camera configuration',
            'scope':'scene composition only; material rendering, collision cooking and spawn support remain unverified'}
    output.with_suffix(output.suffix+'.provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--replace-render-settings',action='store_true');p.add_argument('source');p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(wrap(a.source,a.output,a.replace_render_settings)))
