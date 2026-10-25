#!/usr/bin/env bash
set -euo pipefail
run_id=${1:?run id required}
gpu=${2:-1}
shift 2
[[ "$run_id" =~ ^arena-g1-[0-9]+$ ]] || exit 2
[[ "$gpu" =~ ^[0-7]$ ]] || exit 2
base=/mnt/nas/zhangrong/embodied-mosaic
original=/mnt/nas/zhangrong/isaac-rigidtrack-20261023
local_base=/local_nvme/zhangrong/isaac-rigidtrack-20261023
test ! -e "$base/runs/$run_id"
snapshot="$base/runs/$run_id.sources"
mkdir "$snapshot"
mkdir "$snapshot/prototypes"
cp -a "$base/prototypes/arena_navigation" "$snapshot/prototypes/arena_navigation"
cp -a "$base/scripts" "$snapshot/scripts"
python3 - "$snapshot" <<'PYHASH'
import pathlib,hashlib,json,sys
p=pathlib.Path(sys.argv[1]);files={str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
(p/'source-sha256.json').write_text(json.dumps(files,indent=2))
PYHASH
export RULEGEN_ISAAC_RUNTIME="$local_base/runtime/isaacsim510"
export LD_LIBRARY_PATH="$local_base/runtime/compat-libs"
export PYTHONPATH="$base/runtime/python-deps:$base/vendor/arena-0.1.1-mosaic:$base/vendor/IsaacLab-2.3.0/source/isaaclab:$base/vendor/IsaacLab-2.3.0/source/isaaclab_tasks:$base/vendor/IsaacLab-2.3.0/source/isaaclab_assets"
export OMNI_KIT_ACCEPT_EULA=YES OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
nohup flock "$local_base/locks/campaign-gpu-$gpu.lock" bash "$original/rulegen-diverse40/scripts/isaac_python.sh" "$snapshot/prototypes/arena_navigation/run_g1_probe.py" --output "$base/runs/$run_id" --gpu "$gpu" "$@" > "$base/runs/$run_id.log" 2>&1 < /dev/null &
echo $! | tee "$base/runs/$run_id.pid"
