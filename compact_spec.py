"""Compact MM6 LAD recipe. This is not TIA-compiled code or a PLC download."""
from dataclasses import dataclass, field
MAX=2147483647
BUILD='2026-09-28-compact-day-night-v8'
NAMES=['PreviousCycleSeconds','BetweenCycleSeconds','PreviousBetweenSeconds','CyclesThisHour','CyclesPreviousHour','CyclesToday','CyclesPreviousDay','DayShiftCurrent','DayShiftPrevious','NightShiftCurrent','NightShiftPrevious','TotalCompleted']
DESCRIPTIONS=['Last fully observed production cycle, seconds.','Live known wait; zero means no active known wait, not proof of uptime.','Last finished known wait, seconds.','Completions in the current local clock hour.','Last observed closed clock hour.','Completions in the current local calendar day.','Last observed closed calendar day.','Mon–Fri 06:30–17:00; holds until the next scheduled day shift starts.','The preceding day shift, copied when its next scheduled shift starts.','Mon–Thu 17:00–06:00 next day; holds until the next scheduled night shift starts.','The preceding night shift, copied when its next scheduled shift starts.','Accepted complete production cycles since initialization.']
SCHEMA=[dict(name=n,type='Real' if i<3 else 'DInt',initial='0.0' if i<3 else '0',offset=4*i,kepware_type='Float' if i<3 else 'Long',description=DESCRIPTIONS[i]) for i,n in enumerate(NAMES)]
def A(*x):return ['and',*x]
def O(*x):return ['or',*x]
def N(x):return ['not',x]
def C(a,op,b):return ['cmp',a,op,b]
def R(n):return '"CSI_Report".'+n
def S(n):return '"CSI_Setup".'+n
def move(out,value):return dict(op='MOVE',out=out,inputs={'IN':value})
def bit(out,on):return dict(op='SET' if on else 'RESET',out=out)
def math(op,out,a,b,typ='DInt'):return dict(op=op,out=out,inputs={'IN1':a,'IN2':b},type=typ)
def calc(out,formula,args,typ='DInt'):return dict(op='CALCULATE',out=out,inputs={'IN'+str(i+1):v for i,v in enumerate(args)},type=typ,formula=formula)
def conv(out,value,src,dst,eno=None):return dict(op='T_CONV' if src in ('TIME','DATE','DTL') else 'CONVERT',out=out,inputs={'IN':value},type=src+' → '+dst,eno=eno)
@dataclass
class Block:
 name:str='CSI_Reporting'
 kind:str='FB'
 rows:list=field(default_factory=list)
 networks:list=field(default_factory=list)
 phase:str=''
 def var(self,section,typ,names,initial=None,comment=''):
  for n in names.split():self.rows.append(dict(section=section,name=n,type=typ,initial=initial,comment=comment,phase=self.phase))
 def net(self,title,gate=True,*actions,note=''):
  self.networks.append(dict(number=len(self.networks)+1,title=title,phase=self.phase,gate=gate,actions=list(actions),note=note))
 def coil(self,title,out,gate):self.net(title,gate,dict(op='COIL',out=out))

def make_block():
 b=Block();b.phase='Clock and schedule'
 b.var('Input','Bool','CloseCommand RobotPermit ProductionEligible RobotDataValid AbortCycle',comment='Use the five call pins shown in the OB1 step.')
 b.var('Static','Bool','Initialized',False)
 b.var('Static','DInt','PrevTick',0)
 b.var('Static','DInt','LastClockMinute',-1)
 b.var('Temp','DTL','LocalNow')
 b.var('Temp','DATE','DateOnly')
 b.var('Temp','TIME','TickTime')
 b.var('Temp','Int','ClockStatus')
 b.var('Temp','DInt','DayNumber HourNumber MinuteNumber Weekday MinuteOfDay ClockMinute HourKey ShiftDate TickNow DeltaMs NextMinute')
 b.var('Temp','Bool','DateOK DayOK ClockOK Fresh TickOK DayShift NightShift Scheduled Allowed')
 b.net('Read the PLC local clock',True,dict(op='RD_LOC_T',out='#LocalNow',ret='#ClockStatus'))
 b.net('Extract the date',True,conv('#DateOnly','#LocalNow','DTL','DATE','#DateOK'))
 b.net('Convert the date to a day number','#DateOK',conv('#DayNumber','#DateOnly','DATE','DInt','#DayOK'))
 for dest,member in [('HourNumber','HOUR'),('MinuteNumber','MINUTE'),('Weekday','WEEKDAY')]:b.net('Read '+dest,True,conv('#'+dest,'#LocalNow.'+member,'USInt','DInt'))
 b.net('Calculate minutes since midnight',True,calc('#MinuteOfDay','IN1 * 60 + IN2',['#HourNumber','#MinuteNumber']))
 b.net('Give each local minute its own number',True,calc('#ClockMinute','IN1 * 1440 + IN2',['#DayNumber','#MinuteOfDay']))
 b.net('Give each local hour its own number',True,calc('#HourKey','IN1 * 24 + IN2',['#DayNumber','#HourNumber']))
 b.coil('Check clock validity and prevent backwards period assignment','#ClockOK',A(O(C('#ClockStatus','==',0),C('#ClockStatus','==',1)),'#DateOK','#DayOK',C('#ClockMinute','>=','#LastClockMinute'),C('#Weekday','>=',1),C('#Weekday','<=',7)))
 b.coil('Detect first call or restart','#Fresh',O(N('#Initialized'),S('StartupPending')))
 b.net('Read elapsed RUN milliseconds',True,dict(op='TIME_TCK',out='#TickTime',ret=None))
 b.net('Convert that counter to DINT',True,conv('#TickNow','#TickTime','TIME','DInt'))
 b.net('Start with zero elapsed time for this scan',True,move('#DeltaMs',0))
 b.net('Subtract the previous tick',A(N('#Fresh'),C('#TickNow','>=','#PrevTick')),math('SUB','#DeltaMs','#TickNow','#PrevTick'))
 b.net('Handle the counter returning to zero at its normal limit',A(N('#Fresh'),C('#TickNow','<','#PrevTick')),calc('#DeltaMs','2147483647 - IN1 + IN2 + 1',['#PrevTick','#TickNow']))
 b.coil('Reject restart and implausible elapsed time','#TickOK',A(N('#Fresh'),C('#TickNow','>=',0),C('#DeltaMs','>=',0),C('#DeltaMs','<=',10000)))
 b.coil('Day shift: Monday–Friday 06:30–17:00','#DayShift',A('#ClockOK',C('#Weekday','>=',2),C('#Weekday','<=',6),C('#MinuteOfDay','>=',390),C('#MinuteOfDay','<',1020)))
 b.coil('Night shift: Monday–Thursday evenings and following mornings','#NightShift',A('#ClockOK',O(A(C('#Weekday','>=',2),C('#Weekday','<=',5),C('#MinuteOfDay','>=',1020)),A(C('#Weekday','>=',3),C('#Weekday','<=',6),C('#MinuteOfDay','<',360)))))
 b.coil('A scheduled shift is open','#Scheduled',O('#DayShift','#NightShift'))
 b.net('Default the shift start date to today',True,move('#ShiftDate','#DayNumber'))
 b.net('Use yesterday for the night shift after midnight',A('#NightShift',C('#MinuteOfDay','<',360)),math('SUB','#ShiftDate','#DayNumber',1))
 b.net('Find the next expected minute',True,math('ADD','#NextMinute','#LastClockMinute',1))
 b.coil('Allow monitoring only with valid reviewed inputs','#Allowed',A(S('Enable'),S('WiringReviewed'),'%DB200.DBX38.2','%DB200.DBX49.3','#RobotDataValid',N('#AbortCycle'),'#ClockOK','#TickOK','#Scheduled',O(C('#LastClockMinute','==',-1),C('#ClockMinute','<=','#NextMinute'))))

 b.phase='Cycle and between-cycle timing'
 b.var('Static','Bool','PrevClose PrevPermit LowSeen',False)
 b.var('Static','DInt','State CycleMs WaitMs',0,comment='State: 0 synchronize, 1 between cycles, 2 timing a cycle.')
 b.var('Temp','Bool','CloseRise PermitRise Drop Sync Complete Boundary Start')
 b.var('Temp','Real','MsReal SecondsValue')
 b.coil('One-scan closing edge','#CloseRise',A('#CloseCommand',N('#PrevClose'),N('#Fresh')))
 b.coil('One-scan robot permission edge','#PermitRise',A('#RobotPermit',N('#PrevPermit'),N('#Fresh')))
 b.coil('Discard an uncertain interval, not held history','#Drop',O(N('#Allowed'),A(C('#State','!=',1),N('#ProductionEligible')),A(C('#State','==',1),O(N('#RobotPermit'),A('#CloseRise',N('#ProductionEligible')))),C('#CycleMs','>',86400000),C('#WaitMs','>',86400000)))
 b.net('Reset only the live observation','#Drop',move('#State',0),move('#CycleMs',0),move('#WaitMs',0),bit('#LowSeen',False),note='This does not reset any held time or production counter.')
 b.net('Remember robot permission low in a qualified sequence',A('#Allowed','#ProductionEligible',N('#RobotPermit'),O(C('#State','==',0),C('#State','==',2))),bit('#LowSeen',True))
 b.net('Add this scan to the active cycle',A('#Allowed',C('#State','==',2)),math('ADD','#CycleMs','#CycleMs','#DeltaMs'))
 b.net('Add this scan to the known wait',A('#Allowed',C('#State','==',1)),math('ADD','#WaitMs','#WaitMs','#DeltaMs'))
 b.coil('Find the first known robot return without counting a partial cycle','#Sync',A('#Allowed','#ProductionEligible',C('#State','==',0),'#LowSeen','#PermitRise'))
 b.coil('Make exactly one complete-cycle pulse','#Complete',A('#Allowed','#ProductionEligible',C('#State','==',2),'#LowSeen','#PermitRise'))
 b.net('Convert the completed milliseconds to REAL','#Complete',conv('#MsReal','#CycleMs','DInt','Real'))
 b.net('Convert them to seconds','#Complete',math('DIV','#SecondsValue','#MsReal',1000.0,'Real'))
 b.net('Hold the completed cycle time','#Complete',move(R('PreviousCycleSeconds'),'#SecondsValue'))
 b.coil('A known cycle boundary was reached','#Boundary',O('#Sync','#Complete'))
 b.net('Start the between-cycle interval','#Boundary',move('#State',1),move('#CycleMs',0),move('#WaitMs',0),bit('#LowSeen',False))
 b.net('Do not treat an already-high closing command as a fresh start',A('#Boundary','#CloseCommand',N('#CloseRise')),move('#State',0),note='Synchronize again rather than count the later secondary closing pulse as a new production cycle.')
 b.coil('Accept a closing edge only while waiting at a known boundary','#Start',A('#Allowed','#ProductionEligible',C('#State','==',1),'#CloseRise','#RobotPermit'))
 b.net('Convert the known waiting interval',C('#State','==',1),conv('#MsReal','#WaitMs','DInt','Real'))
 b.net('Publish live waiting seconds',C('#State','==',1),math('DIV',R('BetweenCycleSeconds'),'#MsReal',1000.0,'Real'))
 b.net('Hold the waiting interval at the next start','#Start',move(R('PreviousBetweenSeconds'),R('BetweenCycleSeconds')))
 b.net('Start timing the next cycle','#Start',move('#State',2),move('#CycleMs',0),move('#WaitMs',0),bit('#LowSeen',False))
 b.net('Show no active wait outside the waiting state',C('#State','!=',1),move(R('BetweenCycleSeconds'),0.0),note='A zero is not a validity flag. Check the new instance State for commissioning; never interpret this alone as uptime.')

 b.phase='Hourly, daily and shift counts'
 b.var('Static','DInt','HourSaved DaySaved DayShiftSaved NightShiftSaved',-1,comment='Keep these with the reporting counts if configuring retention.')
 b.var('Temp','Bool','NewHour NewDay NewDayShift NewNightShift')
 for label,key,saved,window,current,previous,pulse in [
 ('hour','#HourKey','#HourSaved',True,'CyclesThisHour','CyclesPreviousHour','#NewHour'),
 ('calendar day','#DayNumber','#DaySaved',True,'CyclesToday','CyclesPreviousDay','#NewDay'),
 ('day shift','#DayNumber','#DayShiftSaved','#DayShift','DayShiftCurrent','DayShiftPrevious','#NewDayShift'),
 ('night shift','#ShiftDate','#NightShiftSaved','#NightShift','NightShiftCurrent','NightShiftPrevious','#NewNightShift')]:
  b.coil('Detect the next '+label,pulse,A('#ClockOK',window,C(key,'>',saved)))
  b.net('Hold the preceding '+label,A(pulse,C(saved,'>=',0)),move(R(previous),R(current)))
  b.net('Start the new '+label+' count',pulse,move(R(current),0),move(saved,key),note='For shifts this runs only at their NEXT scheduled start, never merely because the previous shift ended.')
 for current,window in [('CyclesThisHour',True),('CyclesToday',True),('DayShiftCurrent','#DayShift'),('NightShiftCurrent','#NightShift'),('TotalCompleted',True)]:
  b.net('Add one to '+current,A('#Complete',window,C(R(current),'<',MAX)),math('ADD',R(current),R(current),1),note='Count the completion AFTER storing/resetting the relevant periods. Stop at the DINT limit rather than wrap negative.')
 b.phase='Remember inputs for the next scan'
 b.net('Remember both inputs and the elapsed counter',True,move('#PrevTick','#TickNow'),dict(op='BOOL_COPY',out='#PrevClose',inputs={'IN':'#CloseCommand'}),dict(op='BOOL_COPY',out='#PrevPermit',inputs={'IN':'#RobotPermit'}),bit('#Initialized',True),bit(S('StartupPending'),False))
 b.net('Remember the last valid local minute','#ClockOK',move('#LastClockMinute','#ClockMinute'))
 return b
BLOCK=make_block()
# Give BOOL copies their own normal-coil networks. Normal coils must update even when FALSE.
last=BLOCK.networks[-2];copies=[x for x in last['actions'] if x['op']=='BOOL_COPY'];last['actions']=[x for x in last['actions'] if x['op']!='BOOL_COPY']
for a in copies:BLOCK.coil('Remember '+a['out']+' for the next scan',a['out'],a['inputs']['IN'])
for i,n in enumerate(BLOCK.networks):n['number']=i+1
BLOCKS={BLOCK.name:BLOCK}
if __name__=='__main__':
 print(len(SCHEMA),'report fields;',len(BLOCK.rows),'internal/interface rows;',len(BLOCK.networks),'networks')
