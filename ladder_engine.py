"""Execute the authored LAD network records in Python for checks, not PLC emulation."""
from copy import deepcopy
from datetime import date
import ast,operator
from ladder_spec import BLOCKS
EPOCH=date(1990,1,1)

def expr(text,inputs,real=False):
 text=text.replace(' MOD ',' % ')
 def go(n):
  if isinstance(n,ast.Expression):return go(n.body)
  if isinstance(n,ast.Name):return inputs[n.id]
  if isinstance(n,ast.Constant):return n.value
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):return -go(n.operand)
  if isinstance(n,ast.BinOp):
   a,b=go(n.left),go(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b if real else int(a/b)
   if isinstance(n.op,ast.Mod):return a%b
  raise ValueError(ast.dump(n))
 return go(ast.parse(text,mode='eval'))

class Engine:
 def __init__(self,schema):
  self.report={r['name']:float(r['initial']) if r['type']=='Real' else int(r['initial'])for r in schema}
  self.setup={'Enable':False,'WiringReviewed':False,'StartupPending':True}
  self.hardware={'%DB200.DBX38.2':True,'%DB200.DBX49.3':True}
  self.instances={};self.main=self.initial('CSI_Reporting');self.clock={};self.trace=[]
 def initial(self,name):
  env={}
  for r in BLOCKS[name].rows:
   env[r['name']]= self.initial(r['type']) if r['type'] in BLOCKS else (r['initial'] if r['initial'] is not None else {} if r['type']=='DTL' else False if r['type']=='Bool' else 0.0 if r['type']=='Real' else 0)
  return env
 def get(self,v,env):
  if not isinstance(v,str):return v
  if v.startswith('#'):d=env;path=v[1:]
  elif v.startswith('"CSI_Report".'):d=self.report;path=v.split('.',1)[1]
  elif v.startswith('"CSI_Setup".'):d=self.setup;path=v.split('.',1)[1]
  elif v.startswith('%'):return self.hardware[v]
  else:raise ValueError(v)
  for k in path.split('.'):d=d[k]
  return d
 def put(self,path,value,env):
  if path.startswith('#'):d=env;path=path[1:]
  elif path.startswith('"CSI_Report".'):d=self.report;path=path.split('.',1)[1]
  elif path.startswith('"CSI_Setup".'):d=self.setup;path=path.split('.',1)[1]
  else:raise AssertionError('Non-CSI output '+path)
  bits=path.split('.')
  for k in bits[:-1]:d=d[k]
  d[bits[-1]]=value
 def condition(self,g,env):
  if isinstance(g,list):
   if g[0]=='and':return all(self.condition(x,env)for x in g[1:])
   if g[0]=='or':return any(self.condition(x,env)for x in g[1:])
   if g[0]=='not':return not self.condition(g[1],env)
   if g[0]=='cmp':
    a,b=self.get(g[1],env),self.get(g[3],env)
    return {'==':operator.eq,'!=':operator.ne,'<':operator.lt,'>':operator.gt,'<=':operator.le,'>=':operator.ge}[g[2]](a,b)
   raise ValueError(g)
  return bool(self.get(g,env))
 def execute(self,name,env):
  for net in BLOCKS[name].networks:
   power=self.condition(net['gate'],env)
   for action in net['actions']:
    op=action['op']
    if op=='COIL':self.put(action['out'],power,env);continue
    if action.get('eno'):self.put(action['eno'],False,env)
    if not power:continue
    args={k:self.get(v,env)for k,v in action.get('inputs',{}).items()}
    if op=='CALL':
     block=BLOCKS[action['block']]
     sub=self.get(action['instance'],env) if action['instance'] else self.initial(block.name)
     sub.update(deepcopy(args));self.execute(block.name,sub)
     for row in block.rows:
      if row['section']=='InOut':self.put(action['inputs'][row['name']],sub[row['name']],env)
     continue
    if op in ('RD_LOC_T','RD_SYS_T','TIME_TCK'):
     if op=='TIME_TCK':self.put(action['out'],self.clock['tick'],env)
     else:
      stamp=self.clock['local' if op=='RD_LOC_T' else 'utc']
      self.put(action['out'],{'YEAR':stamp.year,'MONTH':stamp.month,'DAY':stamp.day,'WEEKDAY':(stamp.weekday()+1)%7+1,'HOUR':stamp.hour,'MINUTE':stamp.minute,'SECOND':stamp.second},env)
      self.put(action['ret'],(1 if self.clock['dst'] and op=='RD_LOC_T' else 0) if self.clock['valid'] else -32640,env)
     continue
    if op=='MOVE':value=args['IN']
    elif op in ('SET','RESET'):value=op=='SET'
    elif op in ('ADD','SUB','MUL','DIV','MOD'):
     value=expr('IN1 '+{'ADD':'+','SUB':'-','MUL':'*','DIV':'/','MOD':'%'}[op]+' IN2',args,action.get('type')=='Real')
    elif op=='CALCULATE':value=expr(action['formula'],args,action['type']=='Real')
    elif op in ('CONVERT','T_CONV'):
     t=action['type'];v=args['IN']
     if t=='DTL → DATE':
      try:value=date(v['YEAR'],v['MONTH'],v['DAY']);assert 1990<=value.year<=2168
      except Exception:continue
     elif t=='DATE → DInt':value=(v-EPOCH).days
     elif t.endswith('Real'):value=float(v)
     else:value=int(v)
     if action.get('eno'):self.put(action['eno'],True,env)
    else:raise AssertionError(op)
    if isinstance(value,int) and not isinstance(value,bool) and not -2147483648<=value<=2147483647:raise OverflowError((name,net['number'],action,value))
    self.put(action['out'],value,env)
 def scan(self,tick,local,utc,**inputs):
  self.clock=dict(tick=tick,local=local,utc=utc,valid=inputs.pop('clock_valid',True),dst=inputs.pop('dst',False))
  self.main.update(inputs);self.execute('CSI_Reporting',self.main)
  return self.report
