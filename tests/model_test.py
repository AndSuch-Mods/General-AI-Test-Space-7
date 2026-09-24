from report_model import *
from datetime import timedelta
import json
from pathlib import Path
checks=[]
def test(n,c):assert c,n;checks.append(n)
for y in range(1990,2090):
 for m in range(1,13):
  for d in [1,28]:assert day_number(y,m,d)==(date(y,m,d)-EPOCH).days
checks.append('Gregorian day-number arithmetic checked against datetime for 2400 dates')
test('Leap-day validity',day_number(2000,2,29)>=0 and day_number(2025,2,29)==-1)
a=datetime(2026,9,25,9,0,0)
test('Shift half-open boundaries and gap',[shift_at(a.replace(hour=h,minute=m))[0] for h,m in [(5,59),(6,0),(6,29),(6,30),(16,59),(17,0),(23,59)]]==[2,0,0,1,1,2,2])
test('Night shift stays assigned to its start date',shift_at(a.replace(hour=23))[1]==shift_at((a+timedelta(days=1)).replace(hour=0))[1])
test('Monotonic counter wrap',tick_delta(MAX-10,5)==16)
m=Model();m.scan(0,a,close=True,permit=True);m.scan(1000,a+timedelta(seconds=1),close=True,permit=True)
test('Startup-high input does not start or complete',not m.active and m.total==0)
m.scan(2000,a+timedelta(seconds=2),close=False);m.scan(3000,a+timedelta(seconds=3),close=True)
test('Permit already true does not immediately complete',m.active and m.total==0)
m.scan(4000,a+timedelta(seconds=4),close=False,permit=False);m.scan(5000,a+timedelta(seconds=5),close=True,permit=False)
test('Repeat close edge does not restart active timing',m.cycle_ms==2000)
m.scan(6000,a+timedelta(seconds=6),close=False,permit=True)
test('One completion captures duration and increments once',m.prev_cycle==3 and m.total==1)
m.scan(7000,a+timedelta(seconds=7),close=False,permit=True,production=False)
test('Between-cycle timer keeps running in idle manual mode',m.between_ms==1000)
m.scan(8000,a+timedelta(seconds=8),close=False,permit=True);m.scan(9000,a+timedelta(seconds=9),close=True,permit=True)
test('Next start captures held between duration',m.prev_between==3 and m.prev_cycle==3)
m.scan(10000,a+timedelta(seconds=10),close=False,permit=False,abort=True)
m.scan(11000,a+timedelta(seconds=11),close=False,permit=True)
test('Abort keeps old held values and does not count',m.total==1 and m.prev_cycle==3 and not m.active)
# Finish exactly on each boundary; setup is just prior to it.
for hour,minute,expected in [(17,0,2),(6,0,0),(6,30,1),(10,0,1),(0,0,2)]:
 boundary=a.replace(hour=hour,minute=minute,second=0);base=boundary-timedelta(seconds=4);x=Model()
 for tick,sec,c,p in [(0,0,False,True),(1000,1,False,True),(2000,2,True,True),(3000,3,False,False),(4000,4,False,True)]:x.scan(tick,base+timedelta(seconds=sec),close=c,permit=p)
 test(f'Boundary {hour:02}:{minute:02} completion credited to new hour/shift',x.hour_count==1 and (x.shift_count[expected]==1 if expected else x.gap==1))
x=Model();base=a.replace(hour=16,minute=59,second=56)
for tick,sec,c,p in [(0,0,False,True),(1000,1,False,True),(2000,2,True,True),(3000,3,False,False),(4000,4,False,True)]:x.scan(tick,base+timedelta(seconds=sec),close=c,permit=p)
test('17:00 stores shift1 without crediting boundary completion to it',x.previous_shift[1][1]==0 and x.shift_count[2]==1)
x=Model();x.scan(0,a);x.scan(1000,a+timedelta(seconds=1));x.scan(2000,a+timedelta(seconds=2),close=True);x.scan(3000,a+timedelta(seconds=3),permit=False,signals=False);x.scan(4000,a+timedelta(seconds=4),permit=True)
test('Communication loss/recovery cannot create false completion',x.total==0 and not x.active)
x=Model();x.scan(0,a);x.scan(1000,a+timedelta(seconds=1));x.scan(2000,a+timedelta(seconds=2),close=True);x.scan(3000,a+timedelta(seconds=3),permit=False);x.scan(0,a+timedelta(seconds=4),permit=True,restart=True)
test('Restart drops incomplete interval without a count',x.total==0 and not x.active)
x=Model();x.scan(0,a);x.scan(1000,a+timedelta(seconds=1));x.scan(2000,a+timedelta(seconds=2),close=True);x.scan(3000,a+timedelta(seconds=3),permit=False);x.scan(4000,a+timedelta(seconds=4),permit=True,close=True)
test('Same-scan next start captures zero gap after completion',x.total==1 and x.active and x.prev_between==0)
x=Model();x.scan(0,a);x.scan(1000,a+timedelta(seconds=1));x.scan(2000,a+timedelta(seconds=2),close=True);x.scan(3000,a+timedelta(seconds=3),permit=False);x.scan(4000,a-timedelta(minutes=30),permit=True)
test('Backward clock keeps total but avoids overwriting prior hour',x.total==1 and x.hour_count==0 and x.clock_unassigned==1)
x=Model();x.scan(MAX-3000,a);x.scan(MAX-2000,a+timedelta(seconds=1));x.scan(MAX-1000,a+timedelta(seconds=2),close=True);x.scan(0,a+timedelta(seconds=3),permit=False);x.scan(1000,a+timedelta(seconds=4),permit=True)
test('Cycle duration survives normal tick wrap',x.total==1 and abs(x.prev_cycle-2.001)<1e-9)
report={'passed':len(checks),'checks':checks,'scope':'Independent Python reference-model checks, not execution or compilation of Siemens SCL. TIA compiler, target instruction support, retention, communication qualification and real machine signals remain unvalidated.'}
Path(__file__).with_name('model-results.json').write_text(json.dumps(report,indent=2))
print('PASS',len(checks),'reference-model checks')
