"""One authenticated image decision. Experimental: residual CLI tools remain.
No simulator action is executed; credentials are mounted read-only, never logged.
"""
import argparse,base64,json,os,pathlib,shutil,subprocess,sys,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'episode_harness'))
from harness import Episode
p=argparse.ArgumentParser();p.add_argument('--image',required=True);p.add_argument('--output',required=True);a=p.parse_args()
out=pathlib.Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
episode=Episode('Look at the current view. Choose a short forward motion only if the visible path is clear; otherwise choose a turn or wait.',max_actions=1)
payload=episode.request(pathlib.Path(a.image).read_bytes())
cache=json.loads((pathlib.Path.home()/'.codex/models_cache.json').read_text());model=next(m for m in cache['models'] if m['slug']=='gpt-6.1-sol')
model.update(supports_reasoning_summaries=False,supports_parallel_tool_calls=False,base_instructions=payload['instructions'],tool_mode='direct',multi_agent_version='disabled',shell_type='disabled',apply_patch_tool_type=None,experimental_supported_tools=[],supports_search_tool=False)
for k in ['include_skills_usage_instructions','include_plugin_usage_instructions','include_apps_usage_instructions']:model[k]=False
binary=next(pathlib.Path(shutil.which('codex')).resolve().parents[1].glob('node_modules/@openai/codex-linux-x64/vendor/*/bin/codex'))
with tempfile.TemporaryDirectory(prefix='mosaic-policy-') as td:
 root=pathlib.Path(td)
 (root/'models.json').write_text(json.dumps({'models':[model]}));(root/'instructions.txt').write_text(payload['instructions']+'\nDo not call any tools. The image is already attached. Return only the requested action JSON.')
 (root/'rgb.png').write_bytes(base64.b64decode(payload['input'].pop('image')['base64']))
 variants=payload['validation_schema']['oneOf']
 schema={'type':'object','additionalProperties':False,'properties':{'episode':{'type':'string'},'observation_id':{'type':'integer'},'skill':{'type':'string','enum':[v['properties']['skill']['enum'][0] for v in variants]},'arguments':{'anyOf':[v['properties']['arguments'] for v in variants]}},'required':['episode','observation_id','skill','arguments']}
 (root/'schema.json').write_text(json.dumps(schema))
 cmd=['/codex','exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--json','-C',td,'-m','gpt-6.1-sol','-i',str(root/'rgb.png'),'--output-schema',str(root/'schema.json')]
 overrides={'model_catalog_json':str(root/'models.json'),'model_instructions_file':str(root/'instructions.txt'),'model_reasoning_effort':'low','web_search':'disabled','mcp_servers':{},'project_doc_max_bytes':0,'skills.include_instructions':False,'include_permissions_instructions':False}
 for k,v in overrides.items():cmd+=['-c',f'{k}={json.dumps(v)}']
 for f in ['shell_tool','unified_exec','apps','plugins','hooks','multi_agent','browser_use','browser_use_external','computer_use','image_generation','in_app_browser','workspace_dependencies','tool_suggest']:cmd+=['--disable',f]
 cmd+=[json.dumps(payload['input'])]
 sandbox=['bwrap','--die-with-parent','--unshare-user','--unshare-pid','--unshare-ipc','--unshare-uts','--new-session','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir',str(pathlib.Path.home()),'--ro-bind',td,td,'--ro-bind',str(binary),'/codex','--chdir',td]
 for path in ['/etc/ssl','/etc/resolv.conf','/etc/hosts','/etc/nsswitch.conf',str(pathlib.Path.home()/'.codex/auth.json')]:
  if pathlib.Path(path).exists():sandbox+=['--ro-bind',path,path]
 env={k:v for k,v in os.environ.items() if k in ('HOME','USER','LANG','PATH') or 'proxy' in k.lower()}
 try:r=subprocess.run(sandbox+cmd,capture_output=True,text=True,env=env,timeout=90)
 except subprocess.TimeoutExpired:
  (out/'summary.json').write_text(json.dumps({'status':'timeout','simulator_action_executed':False}));raise SystemExit('Model decision timed out')
 (out/'events.jsonl').write_text(r.stdout);(out/'stderr.txt').write_text(r.stderr)
 events=[]
 for line in r.stdout.splitlines():
  try:events.append(json.loads(line))
  except ValueError:pass
 messages=[e['item']['text'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
 tool_items=[e for e in events if e.get('item',{}).get('type') not in (None,'agent_message','reasoning')]
 summary={'returncode':r.returncode,'tool_event_count':len(tool_items),'simulator_action_executed':False,'strict_no_tools_verified':False}
 if messages and not tool_items:
  try:summary['command']=episode.accept(messages[-1]);summary['status']='valid_decision'
  except ValueError:summary['status']='invalid_decision'
 else:summary['status']='no_decision_or_tool_call'
 (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
episode.close()
