from pathlib import Path
import sys,json,re
from datetime import datetime,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ladder_spec import BLOCKS,MAX
from ladder_engine import Engine
R=Path(__file__).resolve().parents[1];schema=json.loads((R/'schema_v2.json').read_text());results=[]
def ok(name,cond):assert cond,name;results.append(name)
def fresh():
 e=Engine(schema);e.setup.update(Enable=True,WiringReviewed=True);return e
def scan(e,s,base=None,**kw):
 local=base+timedelta(seconds=s) if base else datetime(2026,9,28,8,0)+timedelta(seconds=s)
 return e.scan(int(round(s*1000))%(MAX+1),local,local+timedelta(hours=5),**kw)
def init(e,base=None):
 scan(e,0,base,CloseCommand=False,RobotPermit=True,ProductionEligible=True,RobotDataValid=True,AbortCycle=False)
 scan(e,1,base)
def simple_cycle(e,base=None,start=2):
 scan(e,start,base,RobotPermit=False,CloseCommand=False)
 scan(e,start+1,base,RobotPermit=True,CloseCommand=True)
 scan(e,start+2,base,RobotPermit=True,CloseCommand=False)
 scan(e,start+3,base,RobotPermit=False)
 scan(e,start+4,base,RobotPermit=True)

# Every reference in the authored specification must have a declaration.
e=fresh()
for block in BLOCKS.values():
 env=e.initial(block.name)
 def check_ref(v):
  if isinstance(v,str) and (v.startswith('#') or v.startswith('"CSI') or v.startswith('%')):
   if v.startswith('#') and v.split('.')[0][1:] in ('LocalStamp','UtcStamp') and '.' in v:return
   e.get(v,env)
 def walk(g):
  if isinstance(g,list):
   for x in g[1:]:walk(x)
  else:check_ref(g)
 for n in block.networks:
  walk(n['gate'])
  for a in n['actions']:
   for v in a.get('inputs',{}).values():check_ref(v)
   for k in ['out','eno','ret','instance']:
    if a.get(k):check_ref(a[k])
    if k in ('out','eno','ret') and a.get(k):assert not a[k].startswith('%')
   if a['op']=='CALL':
    target=BLOCKS[a['block']]
    names={r['name']for r in target.rows if r['section'] in ('Input','InOut')}
    assert set(a['inputs'])==names,(a,names)
ok('All network references, call pins and output destinations are declared',True)
ok('Every executable user block is specified in LAD; no SCL body is displayed',all(b.kind in ('FB','FC')for b in BLOCKS.values()))
# Screenshot timeline, filled with ordinary scans between its recorded changes.
e=fresh();base=datetime(2026,9,28,8)
events={0.0:(False,True),4.24:(False,False),14.57:(True,True),33.51:(False,True),75.36:(True,True),77.21:(False,True),90.72:(False,False),101.05:(True,True),120.47:(False,True)}
times=sorted(set([round(i/10,2)for i in range(1206)]+list(events)))
for t in times:
 kw=dict(ProductionEligible=True,RobotDataValid=True,AbortCycle=False)
 if t in events:kw.update(CloseCommand=events[t][0],RobotPermit=events[t][1])
 scan(e,t,base,**kw)
ok('Screenshot replay: one completion at 86.48 seconds',e.report['TotalCompleted']==1 and abs(e.report['PreviousCycleSeconds']-86.48)<1e-6)
ok('Additional closing pulse ignored rather than restarting the cycle',e.report['IgnoredCloseEdges']==1)
ok('Same-scan completion/start stores zero waiting interval',e.report['PreviousBetweenValid']==1 and e.report['PreviousBetweenSeconds']==0)
# Enable just before the short closing pulse: must not count it.
x=fresh();init(x);scan(x,2,CloseCommand=True);scan(x,3,CloseCommand=False);scan(x,4,RobotPermit=False);scan(x,5,RobotPermit=True)
ok('Startup before a secondary close skips the partial cycle',x.report['TotalCompleted']==0)
x=fresh();init(x);simple_cycle(x)
ok('Ordinary completion increments hour/day/shift/total once',all(x.report[k]==1 for k in ['CyclesThisHour','CyclesToday','Shift1Current','TotalCompleted']))
for t in range(7,1807):scan(x,t,ProductionEligible=False)
ok('Idle waiting continues while production eligibility is off',x.report['BetweenActive']==1 and abs(x.report['BetweenCycleSeconds']-1800)<1e-6)
scan(x,1807,ProductionEligible=True,CloseCommand=True)
ok('Next accepted start holds the 30-minute interval',abs(x.report['PreviousBetweenSeconds']-1801)<1e-6)
scan(x,1808,AbortCycle=True);scan(x,1809,AbortCycle=False,RobotPermit=True)
ok('Abort preserves held values and creates no extra completion',x.report['TotalCompleted']==1 and x.report['PreviousCycleValid']==1 and x.report['MonitorState']==10)
x=fresh();init(x);simple_cycle(x);held=x.report['PreviousCycleSeconds'];scan(x,7,RobotDataValid=False,RobotPermit=False);scan(x,8,RobotDataValid=True,RobotPermit=True)
ok('Lost data and return cannot produce a completed cycle',x.report['TotalCompleted']==1 and x.report['PreviousCycleSeconds']==held)
x=fresh();init(x);scan(x,2,RobotPermit=False);scan(x,3,RobotPermit=True,CloseCommand=True);x.setup['StartupPending']=True;scan(x,4,RobotPermit=True)
ok('Startup guard drops an unfinished observation',x.report['TotalCompleted']==0 and x.report['CycleActive']==0)
# Schedule uses exact weekday and half-open times.
for dt,s1,s2 in [(datetime(2026,9,28,6,29),False,False),(datetime(2026,9,28,6,30),True,False),(datetime(2026,9,28,17),False,True),(datetime(2026,9,29,5,59),False,True),(datetime(2026,9,29,6),False,False),(datetime(2026,10,2,5,59),False,True),(datetime(2026,10,2,17),False,False),(datetime(2026,10,3,12),False,False),(datetime(2026,10,4,12),False,False),(datetime(2026,10,5,5),False,False)]:
 x=fresh();init(x,dt);ok('Schedule '+dt.isoformat(),x.main['Shift1']==s1 and x.main['Shift2']==s2)
# Finish exactly at a Monday 17:00 boundary; current cycle stays active across it.
x=fresh();base=datetime(2026,9,28,16,59,54);init(x,base);simple_cycle(x,base)
ok('17:00 completion belongs to new hour and shift 2',x.report['Shift1Previous']==0 and x.report['Shift2Current']==1 and x.report['CyclesThisHour']==1 and x.report['CyclesPreviousHour']==0)
x=fresh();base=datetime(2026,9,28,23,59,54);init(x,base);simple_cycle(x,base)
ok('Midnight rolls day but does not restart the night shift',x.report['CyclesPreviousDay']==0 and x.report['CyclesToday']==1 and x.report['Shift2Current']==1 and x.report['Shift2Day']==(base.date()-datetime(1990,1,1).date()).days)
# Seed plausible closed/open shift buckets; move the calendar while executing enough end scans.
x=fresh();base=datetime(2026,10,2,5,59,57);init(x,base)
x.main['Shift2Counter']['CurrentCount']=173
for t in range(2,5):scan(x,t,base)
ok('Thursday-night shift holds at Friday 06:00',x.report['Shift2Current']==173 and x.report['Shift2Previous']==173)
# Travel to Friday's day shift, then complete a count and close it.
base=datetime(2026,10,2,16,59,56);init(x,base);x.main['Shift1Counter']['CurrentCount']=287
for t in range(2,6):scan(x,t,base)
ok('Friday day shift holds on Friday evening',x.report['Shift1Current']==287 and x.report['Shift1Previous']==287)
for dt in [datetime(2026,10,3,12),datetime(2026,10,4,12),datetime(2026,10,5,6,29)]:
 x.main['PrevTick']=0;scan(x,1,dt,CloseCommand=True,RobotPermit=False);scan(x,2,dt,RobotPermit=True);scan(x,3,dt,CloseCommand=False)
 ok('Weekend/off-schedule hold '+dt.isoformat(),x.report['Shift1Current']==287 and x.report['Shift2Current']==173 and x.report['TotalCompleted']==0)
base=datetime(2026,10,5,6,29,58);x.main['PrevTick']=0
for t in range(4):scan(x,t,base)
ok('Monday 06:30 replaces only shift 1 current',x.report['Shift1Current']==0 and x.report['Shift1Previous']==287 and x.report['Shift2Current']==173)
base=datetime(2026,10,5,16,59,58);x.main['PrevTick']=0
for t in range(4):scan(x,t,base)
ok('Monday 17:00 replaces shift 2 current and holds its previous',x.report['Shift2Current']==0 and x.report['Shift2Previous']==173)
# UTC rollback is quarantined, not counted into an earlier hour.
x=fresh();init(x);simple_cycle(x);current=x.report['ThisHourKeyUTC'];r=scan(x,7,datetime(2026,9,28,7),RobotPermit=False)
ok('Backward UTC clock keeps the current period key and inhibits observation',r['ThisHourKeyUTC']==current and r['ClockValid']==0 and r['ClockReview']==1 and r['TotalCompleted']==1)
x=fresh();init(x);scan(x,2,clock_valid=False)
ok('Bad calendar cannot create scheduled production',x.report['ClockValid']==0 and x.report['CurrentShift']==0)
# Native tick wraps, with an active cycle already synchronized.
x=fresh();init(x);scan(x,2,RobotPermit=False);scan(x,3,RobotPermit=True,CloseCommand=True);x.main['PrevTick']=MAX-9
x.scan(10,datetime(2026,9,28,8,0,4),datetime(2026,9,28,13,0,4),RobotPermit=False)
x.scan(1010,datetime(2026,9,28,8,0,5),datetime(2026,9,28,13,0,5),RobotPermit=True)
ok('Tick wrap keeps duration without an overflow',abs(x.report['PreviousCycleSeconds']-1.020)<1e-6 and x.report['TotalCompleted']==1)
# Counter saturation and elapsed accumulation are run from the same helper rungs.
x=fresh();env=x.initial('CSI_Increment');env['Value']=MAX;x.execute('CSI_Increment',env)
ok('A saturated DINT counter never becomes negative',env['Value']==MAX and x.report['CounterSaturated']==1)
env=x.initial('CSI_AddElapsed');env.update(Seconds=2000000,Millis=950,DeltaMs=100);x.execute('CSI_AddElapsed',env)
ok('Long waits keep integer seconds and millisecond remainder',env['Seconds']==2000001 and env['Millis']==50)
print('PASS',len(results));(R/'tests/ladder_results.json').write_text(json.dumps(dict(passed=len(results),checks=results,scope='Authored LAD network records executed by a Python interpreter, not TIA compilation, native instruction emulation or PLC testing.',plc_tested=False),indent=2))
