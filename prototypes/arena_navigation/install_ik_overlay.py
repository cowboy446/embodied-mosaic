"""Install predownloaded pure/CPython311 wheels into an isolated overlay.
Run with Isaac Sim's Python. Never modify its bundled numpy/scipy packages.
"""
from pathlib import Path
import hashlib,json,zipfile,sys
root=Path('/mnt/nas/zhangrong/embodied-mosaic')
assert sys.version_info[:2]==(3,11)
expected=json.loads((root/'wheels/mosaic-ik-wheels.json').read_text())
for name,digest in expected.items():
 if hashlib.sha256((root/'wheels'/name).read_bytes()).hexdigest()!=digest:raise ValueError('wheel incomplete or changed: '+name)
packages=('pin_pink-','pin-','loop_rate_limiters-','qpsolvers-','quadprog-','cmeel','hpp_fcl-','eigenpy-')
dest=root/'runtime/ik-deps';dest.mkdir(exist_ok=True,parents=True);manifest=[]
for wheel in sorted((root/'wheels').glob('*.whl')):
 if not wheel.name.startswith(packages):continue
 with zipfile.ZipFile(wheel) as z:
  if z.testzip():raise ValueError('corrupt wheel '+wheel.name)
  z.extractall(dest)
 manifest.append({'wheel':wheel.name,'sha256':hashlib.sha256(wheel.read_bytes()).hexdigest()})
assert any(m['wheel'].startswith('pin_pink-3.1.0') for m in manifest)
(dest/'installed-wheels.json').write_text(json.dumps(manifest,indent=2))
print('installed',len(manifest),'wheels in',dest)
