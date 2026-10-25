"""Offline request audit. Dummy localhost provider; never sends credentials or calls a model."""
import argparse,json,subprocess,tempfile,threading,http.server,pathlib,os,shutil
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--isolate',action='store_true');a=p.parse_args()
out=pathlib.Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
cache=json.loads((pathlib.Path.home()/'.codex/models_cache.json').read_text())
model=next(m for m in cache['models'] if m['slug']=='gpt-6.1-sol')
# Transport metadata only: retain model identity and supported reasoning levels.
model['supports_reasoning_summaries']=False
model['supports_parallel_tool_calls']=False
model['base_instructions']='You are a visual robot policy. Return JSON only.'
model.update(tool_mode='direct',multi_agent_version='disabled',shell_type='disabled',apply_patch_tool_type=None,experimental_supported_tools=[],supports_search_tool=False)
for k in ['include_skills_usage_instructions','include_plugin_usage_instructions','include_apps_usage_instructions']:model[k]=False
requests=[]
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_POST(self):
  raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
  try: body=json.loads(raw)
  except Exception: body={'decode_failed':True,'content_encoding':self.headers.get('Content-Encoding'),'length':len(raw)}
  requests.append(body) # Deliberately do NOT store request headers.
  self.send_response(400);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b'{"error":{"message":"offline audit complete","type":"invalid_request_error"}}')
server=http.server.HTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
with tempfile.TemporaryDirectory(prefix='mosaic-cli-audit-') as td:
 root=pathlib.Path(td);catalog=root/'models.json';catalog.write_text(json.dumps({'models':[model]}))
 instructions=root/'instructions.txt';instructions.write_text('You are a visual robot policy. Return JSON only. No tools are permitted.')
 cmd=['codex','exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--json','-C',td,'-m','gpt-6.1-sol']
 overrides={'model_provider':'offline_audit','model_providers.offline_audit.name':'Offline audit','model_providers.offline_audit.base_url':f'http://127.0.0.1:{server.server_port}/v1','model_providers.offline_audit.wire_api':'responses','model_providers.offline_audit.requires_openai_auth':False,'model_catalog_json':str(catalog),'model_instructions_file':str(instructions),'model_reasoning_effort':'low','web_search':'disabled','tools.update_plan':False,'tools.view_image':False,'tools.experimental_request_user_input.enabled':False,'mcp_servers':{},'project_doc_max_bytes':0,'skills.include_instructions':False,'include_permissions_instructions':False}
 disabled=['shell_tool','unified_exec','apps','plugins','hooks','multi_agent','browser_use','browser_use_external','computer_use','image_generation','in_app_browser','workspace_dependencies','tool_suggest','enable_request_compression']
 for k,v in overrides.items():cmd+=['-c',f'{k}={json.dumps(v)}']
 for f in disabled:cmd+=['--disable',f]
 cmd+=['Return {"skill":"wait","parameters":{"duration_s":0.1}}.']
 env={k:v for k,v in os.environ.items() if 'proxy' not in k.lower()}
 env['NO_PROXY']='127.0.0.1,localhost'
 if a.isolate:
  # Locate the installed native binary without importing any user configuration.
  binary=next(pathlib.Path(shutil.which('codex')).resolve().parents[1].glob('node_modules/@openai/codex-linux-x64/vendor/*/bin/codex'))
  sandbox=['bwrap','--die-with-parent','--unshare-user','--unshare-pid','--unshare-ipc','--unshare-uts','--new-session','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir',str(pathlib.Path.home()),'--ro-bind',td,td,'--ro-bind',str(binary),'/codex','--chdir',td]
  env={k:v for k,v in env.items() if k in ('HOME','USER','LANG','PATH','NO_PROXY')}
  # Verify the actual mount namespace, independently of the model's compliance.
  forbidden=[str(pathlib.Path.home()/'.codex/auth.json'),str(pathlib.Path.cwd()),'/mnt/nas']
  check='; '.join('[ ! -e '+__import__('shlex').quote(x)+' ] || exit 42' for x in forbidden)
  probe=subprocess.run(sandbox+['/usr/bin/bash','-c',check],capture_output=True,text=True)
  if probe.returncode:raise RuntimeError('sandbox exposes a forbidden host path')
  cmd=sandbox+['/codex']+cmd[1:]
 try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=50,env=env)
 except subprocess.TimeoutExpired as e:r=None
 server.shutdown()
 (out/'requests.json').write_text(json.dumps(requests,indent=2))
 if r:(out/'cli-output.txt').write_text(r.stdout+'\n'+r.stderr)
 summary={'scope':'offline_transport_request_only','model_called':False,'host_path_probe_passed':bool(a.isolate),'request_count':len(requests),'returncode':r.returncode if r else 'timeout','tools':[x.get('name',x.get('type')) for x in requests[0].get('tools',[])] if requests else None}
 (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
