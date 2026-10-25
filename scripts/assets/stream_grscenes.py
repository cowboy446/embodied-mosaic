"""Stream official GRScenes commercial archive directly to NAS; no local archive."""
import hashlib,json,pathlib,shlex,subprocess,time,urllib.request
URL='https://huggingface.co/datasets/InternRobotics/GRScenes/resolve/main/scenes/GRScenes-100/commercial_scenes.zip'
SIZE=23792807959
SHA='853f8d7fcb67d0db0f97c6c4a486d558220babb4b57f9f614295c362663e5205'
DEST='/mnt/nas/zhangrong/embodied-mosaic/assets/grscenes/commercial_scenes.zip'
STATUS=pathlib.Path(__file__).resolve().parents[2]/'evidence/grscenes-stream-status.json'
SSH=['ssh','-o','BatchMode=yes','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3','4090cluster']

def remote_python(code,**kwargs):
    command='ssh -o BatchMode=yes node43 '+shlex.quote('python3 -c '+shlex.quote(code))
    return subprocess.Popen(SSH+[command],**kwargs)

def status(**data):
    STATUS.parent.mkdir(parents=True,exist_ok=True);tmp=STATUS.with_suffix('.tmp');tmp.write_text(json.dumps({'url':URL,'nas_path':DEST,'expected_bytes':SIZE,'expected_sha256':SHA,'updated_unix':time.time(),**data},indent=2));tmp.replace(STATUS)

def main():
    inspect="from pathlib import Path;import json;p=Path("+repr(DEST)+");print(json.dumps({'complete':p.exists(),'partial_bytes':p.with_suffix('.zip.part').stat().st_size if p.with_suffix('.zip.part').exists() else 0}))"
    proc=remote_python(inspect,stdout=subprocess.PIPE);out,_=proc.communicate()
    if proc.returncode:raise RuntimeError('NAS inspection failed')
    state=json.loads(out)
    if state['complete']:status(state='already_present_requires_verification');return
    offset=state['partial_bytes']
    if not 0<=offset<=SIZE:raise RuntimeError('invalid partial size')
    req=urllib.request.Request(URL,headers={'Range':f'bytes={offset}-'} if offset else {})
    with urllib.request.urlopen(req,timeout=60) as response:
        if offset and (response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {offset}-')):raise RuntimeError('server did not honor resume offset')
        code="""import sys,pathlib,hashlib,json,os
p=pathlib.Path(DEST);p.parent.mkdir(parents=True,exist_ok=True);part=p.with_suffix('.zip.part')
if (part.stat().st_size if part.exists() else 0)!=OFFSET:raise RuntimeError('partial changed')
with part.open('ab') as f:
 while True:
  b=sys.stdin.buffer.read(1024*1024)
  if not b:break
  f.write(b)
 f.flush();os.fsync(f.fileno())
if part.stat().st_size!=SIZE:raise RuntimeError('incomplete transfer; retained part')
h=hashlib.sha256()
with part.open('rb') as f:
 for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
if h.hexdigest()!=SHA:raise RuntimeError('checksum mismatch; retained part')
part.rename(p)
p.with_suffix('.zip.verified.json').write_text(json.dumps({'bytes':SIZE,'sha256':h.hexdigest(),'source':URL,'license':'CC-BY-NC-SA-4.0'},indent=2))
"""
        code='DEST='+repr(DEST)+'\nOFFSET='+repr(offset)+'\nSIZE='+repr(SIZE)+'\nSHA='+repr(SHA)+'\nURL='+repr(URL)+'\n'+code
        proc=remote_python(code,stdin=subprocess.PIPE);total=offset;last=0
        try:
            while True:
                block=response.read(1024*1024)
                if not block:break
                proc.stdin.write(block);total+=len(block)
                if time.monotonic()-last>5:status(state='streaming',streamed_bytes=total);last=time.monotonic()
        finally:
            proc.stdin.close()
        status(state='verifying_on_nas',streamed_bytes=total)
        if proc.wait()!=0:raise RuntimeError('NAS writer failed; partial preserved')
        status(state='verified',streamed_bytes=total)
if __name__=='__main__':
    try:main()
    except Exception as exc:
        status(state='failed',error=type(exc).__name__+': '+str(exc));raise
