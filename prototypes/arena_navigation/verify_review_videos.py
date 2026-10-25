"""Verify both encoded views against captured episode frame counts."""
from pathlib import Path
import json,subprocess,sys,hashlib
p=Path(sys.argv[1]);rows=[]
for n in range(14,20):
 name=f'arena-g1-{n:03d}';root=p/name;a=json.loads((root/'audit.json').read_text())
 for view,size in [('ego',(640,480)),('third-person',(960,540))]:
  f=root/(view+'.mp4');d=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=nb_frames,width,height,r_frame_rate,duration','-of','json',str(f)]))['streams'][0]
  assert int(d['nb_frames'])==a['frames'],(name,view,d)
  assert (d['width'],d['height'])==size and d['r_frame_rate']=='30/1'
  assert abs(float(d['duration'])-a['frames']/30)<.002
  subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(f),'-f','null','-'],stdin=subprocess.DEVNULL,check=True)
  rows.append({'episode':name,'view':view,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),**d})
(p/'media-verification.json').write_text(json.dumps({'status':'passed','videos':rows},indent=2));print('verified',len(rows),'videos;',sum(x['bytes'] for x in rows),'bytes')
