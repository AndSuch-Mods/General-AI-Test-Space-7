"""Execute compact LAD recipe records in Python. NOT a Siemens compiler/runtime."""
from pathlib import Path
from datetime import datetime,date,timedelta
import json,sys,re,ast,operator,struct
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from compact_spec import BLOCK,SCHEMA,NAMES,MAX
CHECKS=[]
def ok(name,condition):assert condition,name;CHECKS.append(name)
def arithmetic(s,vals,real=False):
 def f(n):
  if isinstance(n,ast.Expression):return f(n.body)
  if isinstance(n,ast.Constant):return n.value
  if isinstance(n,ast.Name):return vals[n.id]
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):return -f(n.operand)
  if isinstance(n,ast.BinOp):
   a,b=f(n.left),f(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b if real else int(a/b)
  raise ValueError(ast.dump(n))
 return f(ast.parse(s,mode='eval'))
class Engine:
 def __init__(self):
  self.report={r['name']:float(r['initial'])if r['type']=='Real'else int(r['initial'])for r in SCHEMA}
  self.local={r['name']:self.default(r)for r in BLOCK.rows};self.hardware={'%DB200.DBX38.2':True,'%DB200.DBX49.3':True};self.valid=True
 def default(self,r):return r['initial'] if r['initial']is not None else {}if r['type']=='DTL'else False if r['type']=='Bool'else 0
 def get(self,v):
  if not isinstance(v,str):return v
  if v.startswith('#'):d=self.local;key=v[1:]
  elif v.startswith('"CSI_Report".'):d=self.report;key=v.split('.',1)[1]
  elif v.startswith('%'):return self.hardware[v]
  else:raise ValueError(v)
  for k in key.split('.'):d=d[k]
  return d
 def put(self,v,x):
  if v.startswith('#'):d=self.local;key=v[1:]
  elif v.startswith('"CSI_Report".'):d=self.report;key=v.split('.',1)[1]
  else:raise AssertionError('Non-report output '+v)
  assert '.'not in key
  if isinstance(x,int) and not isinstance(x,bool):assert -2147483648<=x<=MAX,(v,x)
  if isinstance(x,float):x=struct.unpack('f',struct.pack('f',x))[0]
  d[key]=x
 def cond(self,g):
  if isinstance(g,list):
   if g[0]=='and':return all(self.cond(x)for x in g[1:])
   if g[0]=='or':return any(self.cond(x)for x in g[1:])
   if g[0]=='not':return not self.cond(g[1])
   return {'==':operator.eq,'!=':operator.ne,'<':operator.lt,'>':operator.gt,'<=':operator.le,'>=':operator.ge}[g[2]](self.get(g[1]),self.get(g[3]))
  return bool(self.get(g))
 def scan(self,now,tick,close=False,permit=True,production=True,valid=True,abort=False,restart=False,clock=True):
  for r in BLOCK.rows:
   if r['section']=='Temp':self.local[r['name']]=self.default(r)
  self.local.update(CloseCommand=close,RobotPermit=permit,ProductionEligible=production,RobotDataValid=valid,AbortCycle=abort)
  if restart:
   for r in BLOCK.rows:
    if r['section']=='Static' and not r.get('retain',False):self.local[r['name']]=self.default(r)
  for n in BLOCK.networks:
   power=self.cond(n['gate'])
   for a in n['actions']:
    op=a['op']
    if op=='COIL':self.put(a['out'],power);continue
    if a.get('eno'):self.put(a['eno'],False)
    if not power:continue
    args={k:self.get(v)for k,v in a.get('inputs',{}).items()}
    if op=='RD_LOC_T':self.put(a['ret'],0 if clock else -1);self.put(a['out'],dict(YEAR=now.year,MONTH=now.month,DAY=now.day,WEEKDAY=(now.weekday()+1)%7+1,HOUR=now.hour,MINUTE=now.minute));continue
    if op=='TIME_TCK':self.put(a['out'],tick);continue
    if op=='MOVE':x=args['IN']
    elif op in ('SET','RESET'):x=op=='SET'
    elif op in ('ADD','SUB','DIV'):x=arithmetic('IN1 '+{'ADD':'+','SUB':'-','DIV':'/'}[op]+' IN2',args,a['type']=='Real')
    elif op=='CALCULATE':x=arithmetic(a['formula'],args,a['type']=='Real')
    elif op in ('T_CONV','CONVERT'):
     v=args['IN'];typ=a['type']
     if typ=='DTL → DATE':x=date(v['YEAR'],v['MONTH'],v['DAY'])
     elif typ=='DATE → DInt':x=(v-date(1990,1,1)).days
     else:x=float(v)if typ.endswith('Real')else int(v)
     if a.get('eno'):self.put(a['eno'],True)
    else:raise AssertionError(op)
    self.put(a['out'],x)
  return self.report

def ready(t):
 e=Engine();e.scan(t-timedelta(milliseconds=100),0);e.scan(t,100);return e
base=datetime(2026,9,28,9)
events=[(0,False,True),(4240,False,False),(14570,True,True),(33510,False,True),(75360,True,True),(77210,False,True),(90720,False,False),(101050,True,True),(120470,False,True)]
e=Engine();close=False;permit=True;ev=dict((t,(c,p))for t,c,p in events)
for ms in sorted(set(range(0,120471,100))|set(ev)):
 if ms in ev:close,permit=ev[ms]
 e.scan(base+timedelta(milliseconds=ms),ms,close=close,permit=permit)
ok('Exactly 12 report fields, 48 bytes, requested day/night names',len(SCHEMA)==12 and [x['offset']for x in SCHEMA]==list(range(0,48,4)) and NAMES[7:11]==['DayShiftCurrent','DayShiftPrevious','NightShiftCurrent','NightShiftPrevious'])
ok('Screenshot sequence counts exactly one complete cycle',e.report['TotalCompleted']==1)
ok('Screenshot timing is 86.48 seconds within REAL precision',abs(e.report['PreviousCycleSeconds']-86.48)<0.0001)
ok('Secondary close pulse is ignored and next cycle remains active',e.local['State']==2 and e.report['CyclesThisHour']==1)
ok('Same-scan next start holds zero between-cycle time',e.report['PreviousBetweenSeconds']==0)
e=ready(base);e.scan(base+timedelta(seconds=1),1100,close=True);e.scan(base+timedelta(seconds=2),2100,close=False);ok('Startup at an extra closing pulse cannot count a short cycle',e.local['State']==0 and e.report['TotalCompleted']==0)
e=ready(base);e.scan(base+timedelta(seconds=1),1100,permit=False);e.scan(base+timedelta(seconds=2),2100,permit=True)
for i in range(3,1803):e.scan(base+timedelta(seconds=i),100+i*1000,production=False)
ok('Known idle wait survives production mode off for 30 minutes',abs(e.report['BetweenCycleSeconds']-1800)<0.01)
e.scan(base+timedelta(seconds=1803),1803100,close=True);ok('Next start holds that waiting interval',e.report['PreviousBetweenSeconds']>1800 and e.report['BetweenCycleSeconds']==0)
e.report['PreviousCycleSeconds']=87;e.scan(base+timedelta(seconds=1804),1804100,abort=True);ok('Abort discards unfinished cycle and preserves held time',e.local['State']==0 and e.report['PreviousCycleSeconds']==87 and e.report['TotalCompleted']==0)
for mode in ['valid','clock','restart']:
 x=ready(base);x.local.update(State=2,LowSeen=True,PrevPermit=False,CycleMs=5000)
 x.scan(base+timedelta(milliseconds=100),200,permit=True,**({mode:False}if mode!='restart'else{'restart':True}))
 ok(mode+' fault/restart cannot create a false completion',x.report['TotalCompleted']==0 and x.local['State']==0)
# Normal wrap still contributes only its actual elapsed milliseconds.
x=ready(base);x.local.update(State=2,CycleMs=1000,PrevTick=MAX-10)
x.scan(base+timedelta(milliseconds=16),5,close=False,permit=False)
ok('TIME_TCK wrap adds 16 ms',x.local['CycleMs']==1016)
# Complete across a boundary, using completion time rather than cycle start.
for when,daycount,nightcount,total in [(datetime(2026,9,28,17),0,1,1),(datetime(2026,9,29,0),0,1,1),(datetime(2026,9,29,6),0,0,0),(datetime(2026,9,29,6,30),1,0,1)]:
 x=ready(when-timedelta(milliseconds=100));x.local.update(State=2,LowSeen=True,PrevPermit=False,CycleMs=5000)
 x.scan(when,200,permit=True)
 ok(str(when)+' credits completion only to active scheduled window',x.report['DayShiftCurrent']==daycount and x.report['NightShiftCurrent']==nightcount and x.report['TotalCompleted']==total)
# Shift totals hold over weekend, including ignored manual weekend cycles.
fri=datetime(2026,10,2,16,59,59);x=ready(fri);x.report.update(DayShiftCurrent=287,NightShiftCurrent=190,PreviousCycleSeconds=87)
x.local['NightShiftSaved']=(date(2026,10,1)-date(1990,1,1)).days
for t in [datetime(2026,10,2,17),datetime(2026,10,3,10),datetime(2026,10,4,10),datetime(2026,10,5,6,29,59)]:
 x.scan(t,500,close=True,permit=False);x.scan(t+timedelta(milliseconds=100),600,close=True,permit=True)
ok('Weekend cycles excluded; both shift totals and held cycle time stay put',x.report['DayShiftCurrent']==287 and x.report['NightShiftCurrent']==190 and x.report['TotalCompleted']==0 and x.report['PreviousCycleSeconds']==87)
x.scan(datetime(2026,10,5,6,30),700)
ok('Monday 06:30 replaces only the day shift',x.report['DayShiftCurrent']==0 and x.report['DayShiftPrevious']==287 and x.report['NightShiftCurrent']==190)
x.scan(datetime(2026,10,5,17),800)
ok('Monday 17:00 replaces the held night shift',x.report['NightShiftCurrent']==0 and x.report['NightShiftPrevious']==190)
x=ready(datetime(2026,9,29,23,59,59));x.report['NightShiftCurrent']=100;x.scan(datetime(2026,9,30),1100)
ok('Midnight does not reset the overnight shift',x.report['NightShiftCurrent']==100)
x=ready(base);x.report['TotalCompleted']=MAX;x.local.update(State=2,LowSeen=True,PrevPermit=False)
x.scan(base+timedelta(milliseconds=100),200)
ok('Total counter saturates without overflow',x.report['TotalCompleted']==MAX)
# Metadata: no phantom old DB fields or writes to existing addresses.
locals_=set(r['name']for r in BLOCK.rows);references=set(re.findall(r'#([A-Za-z_]\w*)',json.dumps(BLOCK.networks)))
ok('Every rung local has a declaration',references<=locals_)
refs=set(re.findall(r'"CSI_Report"\.(\w+)',json.dumps(BLOCK.networks).replace('\\"','"')))
ok('All report references point to the 12-field layout',refs<=set(NAMES) and set(NAMES)<=refs)
outputs=[a['out']for n in BLOCK.networks for a in n['actions']if 'out'in a]
ok('No writes to original machine or input pins',all(v.startswith(('#','"CSI_Report".'))for v in outputs) and not any(v in ['#CloseCommand','#RobotPermit','#ProductionEligible','#RobotDataValid','#AbortCycle']for v in outputs))
ok('Only one new executable block, no helper FB/FC chain',BLOCK.name=='CSI_Reporting' and len(BLOCK.networks)==66)
report=dict(passed=len(CHECKS),checks=CHECKS,scope='Python execution of authored LAD records and structural checks only; not Siemens compilation or PLC execution.',plc_tested=False)
Path(__file__).with_name('compact_results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
