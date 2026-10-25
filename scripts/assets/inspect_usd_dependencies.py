"""Inventory resolver-visible USD dependencies; no simulator startup required."""
import argparse
import json
from pathlib import Path
from pxr import Sdf, UsdUtils


def inspect(source):
    source = Path(source).resolve(strict=True)
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(Sdf.AssetPath(str(source)))
    layer_records = sorted(({
        'identifier': layer.identifier,
        'resolved_path': layer.realPath,
    } for layer in layers), key=lambda row: row['identifier'])
    missing = sorted(set(str(path) for path in unresolved))
    return {
        'source': str(source),
        'layers': layer_records,
        'assets': sorted(set(str(path) for path in assets)),
        'unresolved': missing,
        'usd_dependency_resolution_passed': not missing,
        'scope': 'USD resolver-visible dependencies, including authored asset attributes',
        'limitations': [
            'Does not inspect imports inside MDL or other external shader source files.',
            'Standalone USD may leave runtime-provided shader modules unresolved; verify these in Kit.',
            'Does not certify rendered appearance, collision geometry or runtime compatibility.',
            'Variant-dependent and runtime-generated references require separate inspection.',
        ],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = inspect(args.source)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: len(result[key]) for key in ('layers', 'assets', 'unresolved')}))
    raise SystemExit(0 if result['usd_dependency_resolution_passed'] else 2)
