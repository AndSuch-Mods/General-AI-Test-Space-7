"""Configured retention and automatic startup checks for the authored LAD records.
Imports/runs the existing compact test suite. Not a Siemens compiler/CPU test.
"""
from pathlib import Path
from datetime import datetime, timedelta, date
import json, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compact_spec import BLOCK, SCHEMA, NAMES, RETAINED_KEYS
from compact_test import Engine, ready, CHECKS as BASE_CHECKS
checks=[]
def ok(name, value):
    assert value, name
    checks.append(name)
base=datetime(2026,9,28,9)
rows={r['name']:r for r in BLOCK.rows}
ok('Only the four period identities are retained in the optimized FB',set(r['name'] for r in BLOCK.rows if r.get('retain'))=={'HourSaved','DaySaved','DayShiftSaved','NightShiftSaved'})
ok('Initialized is non-retentive FALSE; live timers/state are non-retentive zero',rows['Initialized']['initial'] is False and not rows['Initialized']['retain'] and all(rows[n]['initial']==0 and not rows[n]['retain'] for n in ['State','CycleMs','WaitMs']))
ok('No setup DB or commissioning enable bit remains in executable records','CSI_Setup' not in json.dumps(BLOCK.networks) and 'StartupPending' not in json.dumps(BLOCK.networks))
ok('First-call detector is the non-retentive Initialized bit',BLOCK.networks[10]['gate']==['not','#Initialized'])
ok('Report names and fixed 48-byte layout remain unchanged',len(SCHEMA)==12 and [r['offset']for r in SCHEMA]==list(range(0,48,4)) and NAMES[7:11]==['DayShiftCurrent','DayShiftPrevious','NightShiftCurrent','NightShiftPrevious'])

for state in (1,2):
    x=ready(base)
    for i,name in enumerate(NAMES):x.report[name]=(100+i if i>=3 else 87.5+i)
    x.local.update(State=state,CycleMs=15000,WaitMs=1800000,PrevClose=False,PrevPermit=False,LowSeen=True)
    before=dict(x.report)
    x.scan(base+timedelta(seconds=10),0,close=True,permit=True,restart=True)
    ok(('Waiting' if state==1 else 'Active cycle')+' reboot clears live timers and live display',x.local['State']==0 and x.local['CycleMs']==0 and x.local['WaitMs']==0 and x.report['BetweenCycleSeconds']==0)
    ok(('Waiting' if state==1 else 'Active cycle')+' reboot preserves all eleven held/count fields',all(x.report[n]==v for n,v in before.items()if n!='BetweenCycleSeconds'))
    x.scan(base+timedelta(seconds=11),1000,close=True,permit=True)
    ok(('Waiting' if state==1 else 'Active cycle')+' startup-high signals do not create a completion',x.local['State']==0 and x.report['TotalCompleted']==before['TotalCompleted'])

x=ready(base)
x.report['PreviousCycleSeconds']=87
x.local.update(State=2,CycleMs=10000,LowSeen=True,PrevPermit=False)
x.scan(base+timedelta(seconds=1),0,close=True,permit=True,restart=True)
x.scan(base+timedelta(seconds=2),1000,close=False,permit=False)
x.scan(base+timedelta(seconds=3),2000,close=True,permit=True)
ok('First qualified robot return synchronizes and starts without counting the unknown cycle',x.local['State']==2 and x.report['TotalCompleted']==0 and x.report['PreviousCycleSeconds']==87)
x.scan(base+timedelta(seconds=4),3000,close=False,permit=True)
x.scan(base+timedelta(seconds=5),4000,close=True,permit=True)
x.scan(base+timedelta(seconds=6),5000,close=False,permit=False)
x.scan(base+timedelta(seconds=7),6000,close=True,permit=True)
ok('Following full observed cycle counts once and ignores its extra closing pulse',x.report['TotalCompleted']==1 and abs(x.report['PreviousCycleSeconds']-4)<0.001)

x=ready(datetime(2026,9,28,23,59,50))
x.report.update(CyclesThisHour=7,CyclesToday=101,NightShiftCurrent=40,TotalCompleted=500,PreviousCycleSeconds=86.48)
x.scan(datetime(2026,9,29,0,1),0,restart=True)
ok('Restart into a new day rolls hour/day counts but preserves the same night shift',x.report['CyclesPreviousHour']==7 and x.report['CyclesThisHour']==0 and x.report['CyclesPreviousDay']==101 and x.report['CyclesToday']==0 and x.report['NightShiftCurrent']==40 and x.report['TotalCompleted']==500)

x=ready(datetime(2026,10,2,16,59,59))
x.local['NightShiftSaved']=(date(2026,10,1)-date(1990,1,1)).days
x.report.update(DayShiftCurrent=287,NightShiftCurrent=190,TotalCompleted=700)
x.scan(datetime(2026,10,3,10),0,restart=True)
ok('Power loss and weekend restart do not zero held shift totals',x.report['DayShiftCurrent']==287 and x.report['NightShiftCurrent']==190 and x.report['TotalCompleted']==700)
x.scan(datetime(2026,10,5,6,30),0,restart=True)
ok('Monday restart resets only the new day shift and holds the prior night shift',x.report['DayShiftPrevious']==287 and x.report['DayShiftCurrent']==0 and x.report['NightShiftCurrent']==190)
x.scan(datetime(2026,10,5,17),1000)
ok('Next Monday night shift replaces the held night count',x.report['NightShiftPrevious']==190 and x.report['NightShiftCurrent']==0)

x=ready(base)
x.report.update(CyclesThisHour=9,TotalCompleted=20)
x.scan(base-timedelta(hours=1),0,restart=True)
x.local.update(State=2,LowSeen=True,PrevPermit=False,CycleMs=5000)
x.scan(base-timedelta(hours=1)+timedelta(seconds=1),1000,permit=True)
ok('Retained hour/day identities block backward-clock assignment after restart',not x.local['ClockOK'] and x.report['CyclesThisHour']==9 and x.report['TotalCompleted']==20)

root=Path(__file__).resolve().parents[1]
if(root/'content.json').exists():
    d=json.loads((root/'content.json').read_text())
    mm=next(g for g in d['groups']if g['id']=='MM6')
    ids={t['id']for t in mm['tasks']}
    text=json.dumps(mm)
    ok('Current guide has retention instructions but no setup/startup-OB task','MM6-compact-retention' in ids and not {'MM6-compact-setup','MM6-compact-startup'}&ids and 'CSI_Setup' not in text)
    ok('Guide keeps the report DB identity and all twelve names','reportDbCompact' in text and all(n in text for n in NAMES))
    ok('Guide explains retained period identities and non-retained live state',all(n in text for n in RETAINED_KEYS) and 'Retain OFF' in text and 'Initialized' in text)
report=dict(passed=len(checks),base_compact_checks=len(BASE_CHECKS),checks=checks,scope='Python execution of authored LAD records with simulated non-retentive resets; not TIA compilation, live CPU restart, or power-loss testing.',plc_tested=False)
(root/'tests/restart_results.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
