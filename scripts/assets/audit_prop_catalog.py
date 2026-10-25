"""Audit explicit existing asset catalog without silently dropping failures."""
import argparse,hashlib,json
from pathlib import Path
from inspect_usd_scene import inspect


def audit(catalog, asset_project):
    asset_project=Path(asset_project);rows=[]
    bases={'warehouse':asset_project/'assets/Assets/Isaac/5.1/Isaac/Environments/Simple_Warehouse/Props'}
    for key,name in [('office','Office'),('hospital','Hospital')]:
        bases[key]=asset_project/f'campaign20/assets/Assets/Isaac/5.1/Isaac/Environments/{name}/Props'
    for entry in catalog:
        row={'catalog_entry':entry,'runtime_validated':False,'license_verification':'pending'}
        try:
            if Path(entry['file']).name!=entry['file']:raise ValueError('catalog filename must be a basename')
            path=bases[entry['scene']]/entry['file'];row['source']=str(path)
            row['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            data=inspect(path)
            row['inventory']=data
            row['dimensions_m_by_root']=[{'path':r['path'],'size_m':[(b-a)*data['meters_per_unit'] for a,b in zip(r['bounds_stage_units']['min'],r['bounds_stage_units']['max'])]} for r in data['roots'] if r['bounds_stage_units']]
            row['status']='inventoried'
        except Exception as e:
            row.update(status='error',error=f'{type(e).__name__}: {e}')
        rows.append(row)
    return {'assets':rows,'total':len(rows),'inventoried':sum(r['status']=='inventoried' for r in rows),
            'scope':'source geometry/schema inventory; placement labels inherited from prior catalog and not certified'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--catalog',required=True);p.add_argument('--asset-project',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    r=audit(json.loads(Path(a.catalog).read_text()),a.asset_project)
    Path(a.output).write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:r[k] for k in ['total','inventoried']}))
