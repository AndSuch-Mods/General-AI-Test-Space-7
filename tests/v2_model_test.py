from v2_reference_model import *
from datetime import timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import json,re
CENTRAL=ZoneInfo('America/Chicago')
BASE=datetime(2026,9,28,9,tzinfo=CENTRAL)
checks=[]
def check(name,value):
    assert value,name
    checks.append(name)

def replay(events,end_ms,base=BASE,start_ms=0,interval=10):
    """Drive the model continuously. Event times are screenshot observations, not PLC measurements."""
    m=Monitor();i=0;c=False;p=True
    for ms in range(start_ms,end_ms+1,interval):
        while i<len(events) and events[i][0]<=ms:
            _,c,p=events[i];i+=1
        m.scan(ms%(MAX+1),base+timedelta(milliseconds=ms),close=c,permit=p)
    return m

# All timestamps exactly represented in 10-ms sampled replay.
events=[(0,False,True),(4240,False,False),(14570,True,True),(33510,False,True),
        (75360,True,True),(77210,False,True),(90720,False,False),(101050,True,True),(120470,False,True)]
m=replay(events,121000)
check('Screenshot replay gives one complete measured cycle',m.total==1)
check('Screenshot replay held duration is 86.48 seconds',abs(m.previous_cycle-86.48)<1e-9)
check('Screenshot replay ignores the secondary closing pulse',m.ignored==1)
check('Same-observation completion and next start retain zero observed gap',m.previous_gap==0 and m.state==30)
check('First partial cycle is explicitly skipped',m.skipped==1)
late=replay(events,121000,start_ms=74000)
check('Enabling just before the short pulse cannot report a false 26-second cycle',late.total==0 and late.previous_cycle is None and late.state==30)
late2=replay(events,121000,start_ms=15000)
check('Startup with closing and permission already high does not count',late2.total==0)

# Sync, then one full measured 2-second cycle, followed by a long known idle gap.
e=[(0,False,True),(1000,False,False),(2000,True,True),(3000,False,True),
   (3500,False,False),(4000,False,True),(7000,True,True)]
x=replay(e,7000)
check('Held cycle duration survives next start',x.previous_cycle==2.0 and x.total==1)
check('Held between-cycle duration captured at next start',x.previous_gap==3.0)
x=replay(e[:6],5000)
x.scan(6000,BASE+timedelta(seconds=6),production=False)
check('Known between-cycle gap keeps timing in idle manual mode',x.state==20 and x.gap_ms==2000)
x.scan(7000,BASE+timedelta(seconds=7),close=True,production=False)
check('Manual closing does not create a production cycle',x.state==10 and x.total==1)

x=replay(e[:4],3200);old=x.total
x.scan(3300,BASE+timedelta(seconds=3.3),abort=True)
x.scan(3400,BASE+timedelta(seconds=3.4),permit=False)
x.scan(3500,BASE+timedelta(seconds=3.5),permit=True)
check('Abort cannot complete the canceled active cycle',x.total==old and x.previous_cycle is None)
x=replay(e[:4],3200)
x.scan(3300,BASE+timedelta(seconds=3.3),permit=False,signals=False)
x.scan(3400,BASE+timedelta(seconds=3.4),permit=True,signals=True)
check('Communication loss/recovery cannot create a completion',x.total==0 and x.state==10)
x=replay(e[:4],3200)
x.scan(0,BASE+timedelta(seconds=4),close=True,permit=True,restart=True)
check('CPU restart invalidates unfinished timing',x.total==0 and x.state==0 and x.restarts==2)
x=replay(e,7000);held=(x.previous_cycle,x.previous_gap,x.total)
x.scan(0,BASE+timedelta(seconds=8),restart=True)
check('Retained held values and counts survive logical startup reset',held==(x.previous_cycle,x.previous_gap,x.total))

# Late visibility of a close edge must not cause acceptance of a later secondary pulse.
early=[(0,False,True),(1000,False,False),(1900,True,False),(2000,True,True),
       (3000,False,True),(3500,True,True),(4000,False,True),(5000,False,False),(6000,True,True)]
x=replay(early,6000)
check('Already-high close at clear boundary forces resynchronization instead of guessing',x.total==0 and x.previous_cycle is None and x.state==30)

# Start/end around real clock boundaries, counting the completion into the new bucket.
for h,mi,expect in [(17,0,2),(6,0,0),(6,30,1),(10,0,1),(0,0,2)]:
    boundary=BASE.replace(hour=h,minute=mi)
    # Sync at t=2, start there; known cycle ends at t=4 exactly at boundary.
    x=replay([(0,False,True),(1000,False,False),(2000,True,True),(3000,False,False),(4000,False,True)],4000,base=boundary-timedelta(seconds=4))
    count=x.s1.count if expect==1 else x.s2.count if expect==2 else x.gap_count
    check(f'Completion at {h:02}:{mi:02} belongs to the new shift/gap and hour',x.total==1 and x.hour.count==1 and count==1)
    if h==0:check('Midnight resets calendar day without resetting night shift',x.day.count==1 and x.day.previous==0 and x.s2.key==serial((boundary-timedelta(days=1)).date()))
    if h==17:check('17:00 archives shift 1 before shift 2 completion',x.s1.previous==0 and x.s2.count==1)

# Period helper semantics and quality.
p=Period();p.scan(True,False,False,10,10,True,False)
check('First observed bucket is partial',p.partial)
p.scan(True,True,True,11,11,True,True)
check('Natural next boundary opens a complete new bucket before increment',p.previous==0 and p.count==1 and not p.partial and p.previous_partial)
p.scan(True,True,True,11,11,False,False)
check('Inactive shift window archives exactly once',p.previous==1 and p.closed)
p.scan(True,True,True,11,11,False,False)
check('Repeated inactive scans do not erase held shift',p.previous==1)
p.scan(True,True,True,12,12,True,False)
check('Next shift clears current count, not held count',p.count==0 and p.previous==1)
p.count=MAX;p.scan(True,True,True,12,12,True,True)
check('Counters saturate instead of wrapping negative',p.count==MAX)
p.scan(True,False,True,15,15,True,False)
check('Skipped periods keep actual held key and mark quality partial',p.previous_key==12 and p.previous_partial and p.partial)

# Wrap modeled under continuous valid clock; time wrap has no event effect.
x=Monitor()
wrap_events=[(0,False,True),(1000,False,False),(2000,True,True),(3000,False,False),(4000,False,True)]
c=False;pm=True;i=0
for ms in range(0,4001,10):
    while i<len(wrap_events) and wrap_events[i][0]<=ms:_,c,pm=wrap_events[i];i+=1
    x.scan((MAX-2500+ms)%(MAX+1),BASE+timedelta(milliseconds=ms),close=c,permit=pm)
check('TIME_TCK wrap preserves elapsed cycle',x.total==1 and x.previous_cycle==2.0 and not x.timing_fault)

# Daylight saving repeats a local hour, not a UTC hour. No PLC clock writes.
a=datetime(2026,11,1,6,59,59,tzinfo=timezone.utc);b=a+timedelta(seconds=1)
x=Monitor();x.scan(0,a.astimezone(CENTRAL));x.state=20
x.scan(1000,b.astimezone(CENTRAL))
check('DST fall-back produces distinct hourly keys but the same local hour label',x.hour.previous_key+1==x.hour.key and x.hour.previous_label==x.hour.label)
check('DST fall-back does not invalidate the UTC-based clock',not x.clock_review)
x=Monitor();x.scan(0,BASE);x.scan(1000,BASE+timedelta(seconds=1));x.state=30;x.cycle_low=True;x.prev_permit=False
x.scan(2000,BASE-timedelta(minutes=10),permit=True)
check('Real UTC clock rollback preserves total and flags unassigned period count',x.total==1 and x.unassigned==1 and x.clock_review)
x=Monitor();x.scan(0,BASE);x.scan(1000,BASE+timedelta(seconds=1));x.state=30;x.cycle_low=True;x.prev_permit=False
x.scan(2000,BASE+timedelta(seconds=2),permit=True,clock=False)
check('Invalid calendar does not erase a valid measured cycle',x.total==1 and x.unassigned==1 and x.previous_cycle==1.0)

for yr in range(1990,2090):
    for mo in range(1,13):
        for da in (1,28):assert day_number(yr,mo,da)==serial(date(yr,mo,da))
check('Calendar arithmetic matches Python for 2400 dates',True)
check('Calendar rejects nonexistent leap day',day_number(2025,2,29)==-1)

# Source-level checks do not substitute for a Siemens compiler.
r=Path(__file__).resolve().parents[1];source=(r/'downloads/MM6_Reporting_V2.scl').read_text(encoding='utf-8-sig')
check('Source never assigns to an existing absolute PLC operand',not re.search(r'%[IQM]|%DB', '\n'.join(line.split(':=')[0] for line in source.splitlines() if ':=' in line)))
check('Source does not define/replace an organization block','ORGANIZATION_BLOCK' not in source)
check('Source uses isolated CSI2 block namespace',all(n.startswith('CSI2_') for n in re.findall(r'^(?:DATA_BLOCK|FUNCTION_BLOCK|FUNCTION)\s+"([^"]+)"',source,re.M)))
check('Commissioning defaults remain disabled','Enable : Bool := FALSE;' in source and 'WiringReviewed : Bool := FALSE;' in source)
schema=json.loads((r/'schema_v2.json').read_text())
check('Flat reporting layout is 60 four-byte fields, 240 bytes',len(schema)==60 and all(x['offset']==4*i for i,x in enumerate(schema)))
check('Expected source declarations match exported schema',all(re.search(r'\b'+f['name']+r'\s*:\s*'+f['type']+r'\s*:=',source) for f in schema))
report={'passed':len(checks),'checks':checks,'replay':{'observations':'User supplied MM6 screenshots','measured_cycle_seconds':86.48,'complete_cycles':1,'ignored_secondary_closing_edges':1},'scope':'Independent Python reference-model and source-structure checks only. The Siemens SCL was NOT compiled, simulated or executed. Hardware, retentivity, scan ordering and communications require TIA/site validation.'}
(r/'tests/v2_model_results.json').write_text(json.dumps(report,indent=2));print('PASS',len(checks),'checks')
