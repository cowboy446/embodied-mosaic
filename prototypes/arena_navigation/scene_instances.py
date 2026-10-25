"""Author editable instance overrides in a per-run stage, preserving source assets."""
from pxr import Usd


def make_environment_editable(stage, root_path, max_rounds=32):
    root=stage.GetPrimAtPath(root_path)
    if not root:raise ValueError(f'missing scene root: {root_path}')
    overrides=[]
    for _ in range(max_rounds):
        instances=[p for p in Usd.PrimRange(root) if p.IsInstance()]
        if not instances:
            proxies=[str(p.GetPath()) for p in Usd.PrimRange(root,Usd.TraverseInstanceProxies()) if p.IsInstanceProxy()]
            if proxies:raise RuntimeError(f'unresolved instance proxies: {proxies[:8]}')
            return overrides
        for prim in instances:
            overrides.append(str(prim.GetPath()));prim.SetInstanceable(False)
    raise RuntimeError('nested instance expansion exceeded bounded rounds')
