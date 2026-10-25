"""Provider-independent episode boundary. No model or simulator is launched here.
A production transport must separately enforce tools=[] and isolated credentials/files.
"""
from dataclasses import dataclass, field
from pathlib import Path
import base64, json, math, secrets, io
from PIL import Image

SKILLS = {
 'move_forward': {'distance_m': (0.05, 0.50)},
 'turn': {'angle_deg': (-90., 90.)},
 'wait': {'duration_s': (0.1, 1.)},
 'finish': {},
}
class ProtocolError(ValueError): pass

def parse(raw):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d: raise ProtocolError('duplicate key')
   d[k]=v
  return d
 try:
  if not isinstance(raw,str) or len(raw)>4096: raise ProtocolError('invalid response size')
  return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ProtocolError('nonfinite number')))
 except (ValueError,TypeError) as e: raise ProtocolError('invalid JSON response') from e

@dataclass
class Episode:
 goal: str
 token: str = field(default_factory=lambda:secrets.token_hex(16),init=False)
 step: int = field(default=0,init=False)
 closed: bool = field(default=False,init=False)
 pending: bool = field(default=False,init=False)
 issued: bool = field(default=False,init=False)
 pending_command: dict = field(default_factory=dict,init=False)
 history: list = field(default_factory=list,init=False)
 max_actions: int = 100

 def __post_init__(self):
  if not isinstance(self.goal,str) or not 0<len(self.goal)<=512: raise ProtocolError('goal length')
  if type(self.max_actions) is not int or self.max_actions<1: raise ProtocolError('action budget')

 def request(self,rgb_png:bytes):
  if self.closed or self.step>=self.max_actions: raise ProtocolError('episode closed or budget exhausted')
  if self.pending or self.issued: raise ProtocolError('observation already issued or action awaiting execution')
  if not isinstance(rgb_png,bytes) or not rgb_png.startswith(b'\x89PNG\r\n\x1a\n') or len(rgb_png)>4_000_000: raise ProtocolError('expected bounded RGB PNG')
  try:
   with Image.open(io.BytesIO(rgb_png)) as im:
    if im.format!='PNG' or im.size!=(640,480) or im.mode!='RGB' or getattr(im,'n_frames',1)!=1:
     raise ProtocolError('expected one 640x480 RGB observation')
    im.verify()
   with Image.open(io.BytesIO(rgb_png)) as im:
    im.load()
    # Rebuild pixels so text chunks, EXIF and other nonvisual metadata cannot leak.
    clean=Image.frombytes('RGB',im.size,im.tobytes())
    buffer=io.BytesIO();clean.save(buffer,format='PNG');rgb_png=buffer.getvalue()
  except (OSError,ValueError,SyntaxError) as exc:
   raise ProtocolError('invalid RGB observation') from exc
  self.issued=True
  # Explicitly constructed public fields; never merge a simulator state dictionary.
  return {'model':'gpt-6.1-sol','reasoning_effort':'low','tools':[], 'instructions':Path(__file__).with_name('agent_instructions.txt').read_text(),
   'input':{'episode':self.token,'observation_id':self.step,'goal':self.goal,
     'skills':json.loads(json.dumps(SKILLS)),
     'recent_own_actions':json.loads(json.dumps(self.history[-8:])),
     'image':{'mime_type':'image/png','base64':base64.b64encode(rgb_png).decode()}},
   'validation_schema':response_schema(), 'session_scope':self.token, 'new_session':self.step==0}

 def accept(self,raw):
  if self.closed or self.pending or not self.issued or self.step>=self.max_actions: raise ProtocolError('inactive decision slot')
  d=parse(raw)
  if not isinstance(d,dict) or set(d)!={'episode','observation_id','skill','arguments'}: raise ProtocolError('unexpected response fields')
  if d['episode']!=self.token or type(d['observation_id']) is not int or d['observation_id']!=self.step: raise ProtocolError('foreign or stale observation')
  skill=d['skill'];args=d['arguments']
  if not isinstance(skill,str) or skill not in SKILLS or not isinstance(args,dict) or set(args)!=set(SKILLS[skill]): raise ProtocolError('unknown skill or arguments')
  for key,(lo,hi) in SKILLS[skill].items():
   v=args[key]
   if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi: raise ProtocolError('argument outside skill bounds')
  self.pending=True
  self.pending_command=json.loads(json.dumps(d))
  return json.loads(json.dumps(d))

 def executed(self,command):
  # Caller invokes only after the simulator skill runner returns; no privileged result fed back.
  if not self.pending or command!=self.pending_command: raise ProtocolError('unexpected execution receipt')
  self.history.append({'skill':command['skill'],'arguments':command['arguments']})
  self.history=self.history[-8:];self.step+=1;self.pending=False;self.issued=False;self.pending_command={}
  if command['skill']=='finish' or self.step>=self.max_actions:self.closed=True

 def close(self):
  self.closed=True;self.pending=False;self.issued=False;self.pending_command={};self.history.clear();self.goal=''

def response_schema():
 variants=[]
 for name,params in SKILLS.items():
  variants.append({'type':'object','additionalProperties':False,
   'properties':{'episode':{'type':'string'},'observation_id':{'type':'integer'},'skill':{'type':'string','enum':[name]},
    'arguments':{'type':'object','additionalProperties':False,'properties':{k:{'type':'number','minimum':v[0],'maximum':v[1]} for k,v in params.items()},'required':list(params)}},
   'required':['episode','observation_id','skill','arguments']})
 return {'oneOf':variants}
