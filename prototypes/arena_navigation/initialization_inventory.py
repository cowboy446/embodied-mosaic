"""Summarize explicitly selected initialization trials without treating them as a benchmark."""
import argparse,json
from pathlib import Path


def summarize(root, run_ids):
    root=Path(root);rows=[]
    for run_id in run_ids:
        if not run_id.startswith('arena-g1-') or not run_id[len('arena-g1-'):].isdigit():raise ValueError('invalid run ID')
        p=root/run_id
        def read(name):
            f=p/name
            return json.loads(f.read_text()) if f.exists() else None
        config=read('run-config.json');report=read('report.json');selection=read('stock-selection.json')
        placement=read('stock-randomization.json');rejected=read('stock-randomization-rejected.json')
        geometry=read('stock-initialization.json');dynamics=read('stock-dynamics.json')
        row={'run_id':run_id,'scene':config.get('scene_name') if config else None,
             'seed':config.get('seed') if config else None,'source_scene':config.get('scene_source') if config else None,
             'terminal_report_present':report is not None,'status':report.get('status') if report else 'unverified_live_state',
             'wall_seconds':report.get('wall_seconds') if report else None,
             'asset_keys':[r['asset_key'] for r in selection['assets']] if selection else None,
             'layout_check_passed':geometry.get('passed') if geometry else None,
             'short_stability_passed':dynamics.get('summary',{}).get('passed') if dynamics else None,
             'body_index_mapping_present':bool(dynamics and dynamics.get('body_paths')),
             'placement_trials':len((placement or rejected or {}).get('attempts',[])),
             'phase':report.get('phase') if report else None,
             'runtime_acceptance_complete':False}
        if rejected:row['rejection']={'kind':'bounded_placement','object':rejected.get('failed_object')}
        elif geometry and not geometry['passed']:row['rejection']={'kind':'initial_geometry','objects':[r['path'] for r in geometry['objects'] if not r['passed']]}
        elif dynamics and not dynamics['summary'].get('passed'):row['rejection']={'kind':'short_physical_stability','summary':dynamics['summary']}
        elif report and report.get('status')=='failed':row['rejection']={'kind':'runtime','traceback':report.get('traceback')}
        rows.append(row)
    assets=sorted({key for r in rows for key in (r['asset_keys'] or [])})
    return {'runs':rows,'observed_distinct_replacement_assets':assets,
            'scope':'selected development trials; no unbiased success rate or full runtime certification',
            'selected_run_ids':run_ids}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runs-root',required=True);p.add_argument('--output',required=True);p.add_argument('run_ids',nargs='+');a=p.parse_args()
    result=summarize(a.runs_root,a.run_ids);Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'trials':len(result['runs']),'distinct_replacement_assets':len(result['observed_distinct_replacement_assets'])}))
