"""Run inside the candidate PYTHONPATH overlay; never mutates installed packages."""
import argparse,json,os,time,traceback
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--gpu',type=int,required=True);a=p.parse_args()
from isaacsim import SimulationApp
app=SimulationApp({'headless':True,'multi_gpu':False,'active_gpu':a.gpu,'extra_args':['--allow-root']})
report={'status':'started','tests':[],'scope':'imports_and_minimal_world_not_full_robot_task'}
try:
 from isaaclab_arena.environments.isaaclab_arena_environment import IsaacLabArenaEnvironment
 report['tests'].append('arena_environment_config_import')
 from isaaclab_arena.scene.scene import Scene
 report['tests'].append('arena_scene_import')
 from isaaclab_arena.assets.asset_registry import AssetRegistry
 registry=AssetRegistry();report['tests'].append('arena_asset_registry_construct')
 from isaaclab.sim import SimulationContext,SimulationCfg
 sim=SimulationContext(SimulationCfg(dt=1/120,device=f'cuda:{a.gpu}'))
 import isaaclab.sim as sim_utils
 ground=sim_utils.GroundPlaneCfg();ground.func('/World/ground',ground)
 sim.reset()
 for _ in range(10):sim.step()
 report['tests'].append('isaaclab_simulation_ten_steps');report['status']='passed_scoped_probe'
except BaseException:
 report.update(status='failed',traceback=traceback.format_exc());traceback.print_exc()
finally:
 Path(a.output).write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True);app.close()
