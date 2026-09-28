"""Manual LAD network specification. Not a TIA export or compiler-validated program.
The same rung records render the instructions and drive the Python tests.
"""
from copy import deepcopy
MAX=2147483647

def A(*items): return ['and',*items]
def O(*items): return ['or',*items]
def N(item): return ['not',item]
def C(a,op,b): return ['cmp',a,op,b]
def V(n): return '#'+n
def R(n): return '"CSI_Report".'+n
def S(n): return '"CSI_Setup".'+n

class Block:
    def __init__(self,name,kind='FB'):
        self.name=name;self.kind=kind;self.rows=[];self.networks=[];self.phase=''
    def vars(self,section,typ,names,initial=None,comment=''):
        for n in names.split():self.rows.append(dict(section=section,name=n,type=typ,initial=initial,comment=comment))
    def net(self,title,gate=True,*actions,note=''):
        self.networks.append(dict(number=len(self.networks)+1,title=title,phase=self.phase,gate=gate,actions=list(actions),note=note))
    def coil(self,title,out,gate):self.net(title,gate,dict(op='COIL',out=out))

def move(out,value):return dict(op='MOVE',out=out,inputs={'IN':value})
def bit(out,value):return dict(op='SET' if value else 'RESET',out=out)
def math(op,out,a,b,typ='DInt'):return dict(op=op,out=out,inputs={'IN1':a,'IN2':b},type=typ)
def calc(out,formula,inputs,typ='DInt'):return dict(op='CALCULATE',out=out,inputs={'IN'+str(i+1):v for i,v in enumerate(inputs)},type=typ,formula=formula)
def conv(out,value,src,dst,eno=None):return dict(op='T_CONV' if src in ('DTL','DATE','TIME') else 'CONVERT',out=out,inputs={'IN':value},type=src+' → '+dst,eno=eno)
def call(name,instance=None,**pins):return dict(op='CALL',block=name,instance=instance,inputs=pins)
def clock(name,out,ret):return dict(op=name,out=out,ret=ret)

def increment():
 b=Block('CSI_Increment','FC');b.vars('InOut','DInt','Value',comment='Count to increase once per enabled call.')
 b.net('Flag an attempted count beyond the DINT limit',C('#Value','>=',MAX),move(R('CounterSaturated'),1))
 b.net('Add one without overflowing',C('#Value','<',MAX),math('ADD','#Value','#Value',1))
 return b

def elapsed():
 b=Block('CSI_AddElapsed','FC');b.vars('Input','DInt','DeltaMs',comment='This scan’s accepted elapsed milliseconds.')
 b.vars('InOut','DInt','Seconds Millis',comment='The caller keeps these values between scans.')
 b.vars('Temp','DInt','SumMs Carry Room');b.vars('Temp','Bool','CanAdd')
 b.net('Combine the millisecond remainder',True,math('ADD','#SumMs','#Millis','#DeltaMs'))
 b.net('Find whole seconds to carry',True,math('DIV','#Carry','#SumMs',1000))
 b.net('Check room in the seconds counter',True,math('SUB','#Room',MAX,'#Carry'))
 b.coil('Remember whether this addition fits','#CanAdd',C('#Seconds','<=','#Room'))
 b.net('Accumulate whole seconds','#CanAdd',math('ADD','#Seconds','#Seconds','#Carry'))
 b.net('Keep the remaining milliseconds','#CanAdd',math('MOD','#Millis','#SumMs',1000))
 b.net('Saturate instead of wrapping',N('#CanAdd'),move('#Seconds',MAX),move('#Millis',999),move(R('TimingFault'),1))
 return b

def period():
 b=Block('CSI_PeriodCounter');b.vars('Input','Bool','ClockOK WindowActive EndReached BoundaryObserved QualityGood Continuous Restart CountPulse')
 b.vars('Input','DInt','Key Label')
 b.vars('Output','DInt','CurrentCount PreviousCount CurrentLabel PreviousLabel',0)
 b.vars('Output','DInt','CurrentKey PreviousKey',-1)
 b.vars('Output','DInt','CurrentPartial PreviousPartial',1)
 b.vars('Static','Bool','Closed LastQuality',False)
 b.vars('Temp','Bool','NewPeriod CloseOld')
 b.coil('Recognize a later scheduled period','#NewPeriod',A('#ClockOK','#WindowActive',C('#Key','>','#CurrentKey')))
 b.net('Mark an interrupted current period partial',A(C('#CurrentKey','>=',0),N('#Closed'),O('#Restart',N('#ClockOK'),N('#Continuous'),N('#QualityGood'))),move('#CurrentPartial',1))
 b.coil('Decide once whether the old period must close','#CloseOld',A('#ClockOK',C('#CurrentKey','>=',0),N('#Closed'),O('#EndReached','#NewPeriod')))
 b.net('Hold the closed period’s result','#CloseOld',move('#PreviousCount','#CurrentCount'),move('#PreviousKey','#CurrentKey'),move('#PreviousLabel','#CurrentLabel'),move('#PreviousPartial','#CurrentPartial'),bit('#Closed',True),note='Parallel output branches after the same CloseOld contact. Do not clear CurrentCount here.')
 b.net('Begin this period only when its window opens','#NewPeriod',move('#CurrentCount',0),move('#CurrentKey','#Key'),move('#CurrentLabel','#Label'),move('#CurrentPartial',1),bit('#Closed',False),note='A closed shift can sit all weekend without entering this network.')
 b.net('Mark a continuously observed beginning complete',A('#NewPeriod','#BoundaryObserved','#Continuous','#QualityGood','#LastQuality',N('#Restart')),move('#CurrentPartial',0))
 b.net('Count one finished cycle in the new period',A('#ClockOK','#WindowActive','#CountPulse',N('#Closed'),C('#Key','==','#CurrentKey')),call('CSI_Increment',Value='#CurrentCount'),note='This comes AFTER period closing/reset. The completion belongs to its finishing period.')
 b.coil('Remember quality for the next scan','#LastQuality',A('#ClockOK','#QualityGood'))
 return b

def reporting():
 b=Block('CSI_Reporting')
 b.vars('Input','Bool','CloseCommand RobotPermit ProductionEligible RobotDataValid AbortCycle')
 b.vars('Static','Bool','Initialized HaveClock PrevClose PrevPermit LowSeen',False)
 b.vars('Static','DInt','State PrevTick LastUtcMinute LastUtcSecond CycleSec CycleMs GapSec GapMs',0)
 b.vars('Static','CSI_PeriodCounter','HourCounter DayCounter Shift1Counter Shift2Counter',comment='Multi-instance of the LAD FB created earlier; do not re-enter its nested fields.')
 b.vars('Temp','DTL','LocalStamp UtcStamp');b.vars('Temp','DATE','LocalDate UtcDate');b.vars('Temp','TIME','TickTime')
 b.vars('Temp','Int','LocalStatus UtcStatus')
 b.vars('Temp','DInt','Day UtcDay Year Month DayOfMonth Weekday Hour Minute Second UtcHour UtcMinute UtcSecond MinuteOfDay UtcMinuteKey HourKey ShiftDay DateLabel TimeLabel HourLabel Delta TickNow OldState ClockStep Shift1EndDay Shift2EndDay')
 b.vars('Temp','Bool','LocalDateOK UtcDateOK LocalDayOK UtcDayOK RawClock Backward ClockJump ClockOK Continuous Fresh TickOK S1Days S2EveningDays S2MorningDays Shift1 Shift2 Scheduled ConfigOK Enabled BaseGood AllowRun CloseRise PermitRise Drop SkippedActive SyncPulse Complete StartPulse Ambiguous ResyncGap QualityGood EndHour EndDay EndShift1 EndShift2 BoundaryHour BoundaryDay BoundaryShift1 BoundaryShift2')
 b.vars('Temp','Real','CycleWhole CycleFrac CycleValue GapWhole GapFrac GapValue')
 b.phase='Read the clock and elapsed scan time'
 b.net('Identify this LAD reporting revision',True,move(R('SchemaVersion'),3),note='Same 60-field byte layout; revision 3 identifies the weekday-only LAD behavior.')
 b.net('Wrap the heartbeat before incrementing',C(R('Heartbeat'),'>=',MAX),move(R('Heartbeat'),0))
 b.net('Advance the heartbeat',True,math('ADD',R('Heartbeat'),R('Heartbeat'),1))
 b.net('Read plant-local time',True,clock('RD_LOC_T','#LocalStamp','#LocalStatus'))
 b.net('Read UTC for a unique clock-hour key',True,clock('RD_SYS_T','#UtcStamp','#UtcStatus'))
 b.net('Read elapsed RUN milliseconds',True,clock('TIME_TCK','#TickTime',None))
 b.net('Convert elapsed TIME to integer milliseconds',True,conv('#TickNow','#TickTime','TIME','DInt'))
 b.net('Extract the local date',True,conv('#LocalDate','#LocalStamp','DTL','DATE','#LocalDateOK'))
 b.net('Extract the UTC date',True,conv('#UtcDate','#UtcStamp','DTL','DATE','#UtcDateOK'))
 b.net('Convert local date to days since 1990','#LocalDateOK',conv('#Day','#LocalDate','DATE','DInt','#LocalDayOK'))
 b.net('Convert UTC date to days since 1990','#UtcDateOK',conv('#UtcDay','#UtcDate','DATE','DInt','#UtcDayOK'))
 for dest,src,typ in [('Year','LocalStamp.YEAR','UInt'),('Month','LocalStamp.MONTH','USInt'),('DayOfMonth','LocalStamp.DAY','USInt'),('Weekday','LocalStamp.WEEKDAY','USInt'),('Hour','LocalStamp.HOUR','USInt'),('Minute','LocalStamp.MINUTE','USInt'),('Second','LocalStamp.SECOND','USInt'),('UtcHour','UtcStamp.HOUR','USInt'),('UtcMinute','UtcStamp.MINUTE','USInt'),('UtcSecond','UtcStamp.SECOND','USInt')]:
  b.net('Convert '+dest+' to DINT',True,conv('#'+dest,'#'+src,typ,'DInt'))
 b.net('Calculate the local minute of day',True,calc('#MinuteOfDay','IN1 * 60 + IN2',['#Hour','#Minute']))
 b.net('Build UTC minute identity',True,calc('#UtcMinuteKey','IN1 * 1440 + IN2 * 60 + IN3',['#UtcDay','#UtcHour','#UtcMinute']))
 b.net('Build UTC hour identity',True,calc('#HourKey','IN1 * 24 + IN2',['#UtcDay','#UtcHour']))
 b.net('Build a readable local date',A(C('#Year','>=',1990),C('#Year','<=',2089)),calc('#DateLabel','IN1 * 10000 + IN2 * 100 + IN3',['#Year','#Month','#DayOfMonth']))
 b.net('Build a readable local time',True,calc('#TimeLabel','IN1 * 10000 + IN2 * 100 + IN3',['#Hour','#Minute','#Second']))
 b.net('Build the displayed local-hour label',A(C('#Year','>=',1990),C('#Year','<=',2089)),calc('#HourLabel','IN1 * 100 + IN2',['#DateLabel','#Hour']))
 b.coil('Check that the two calendar reads are usable','#RawClock',A(O(C('#LocalStatus','==',0),C('#LocalStatus','==',1)),C('#UtcStatus','==',0),'#LocalDayOK','#UtcDayOK',C('#Year','>=',1990),C('#Year','<=',2089),C('#Minute','==','#UtcMinute')))
 b.coil('Recognize first execution or PLC restart','#Fresh',O(N('#Initialized'),S('StartupPending')))
 b.net('Default elapsed scan time to zero',True,move('#Delta',0))
 b.net('Normal tick difference',A(N('#Fresh'),C('#TickNow','>=','#PrevTick')),math('SUB','#Delta','#TickNow','#PrevTick'))
 b.net('Tick difference across its normal wrap',A(N('#Fresh'),C('#TickNow','<','#PrevTick')),calc('#Delta','2147483647 - IN1 + IN2 + 1',['#PrevTick','#TickNow']))
 b.coil('Accept a plausible scan delta','#TickOK',A(N('#Fresh'),C('#TickNow','>=',0),C('#Delta','>=',0),C('#Delta','<=',10000)))
 b.net('Flag an elapsed-clock discontinuity',A(N('#Fresh'),N('#TickOK')),move(R('TimingFault'),1))
 b.coil('Detect a backward UTC correction','#Backward',A('#RawClock','#HaveClock',O(C('#UtcMinuteKey','<','#LastUtcMinute'),A(C('#UtcMinuteKey','==','#LastUtcMinute'),C('#UtcSecond','<','#LastUtcSecond')))))
 b.net('Default calendar separation to unknown',True,move('#ClockStep',999))
 b.net('Calculate a short calendar separation',A('#RawClock','#HaveClock',C('#UtcMinuteKey','>=','#LastUtcMinute'),C('#UtcMinuteKey','<=',['+','#LastUtcMinute',1])),calc('#ClockStep','(IN1 - IN2) * 60 + IN3 - IN4',['#UtcMinuteKey','#LastUtcMinute','#UtcSecond','#LastUtcSecond']),note='For the upper comparison use ADD LastUtcMinute + 1 into an intermediate tag first. The builder expands that comparison value below.')
 b.coil('Mark a forward calendar gap','#ClockJump',A('#RawClock','#HaveClock',N('#Backward'),C('#ClockStep','>',2),N('#Fresh')))
 b.coil('Allow calendar assignment without reversing a stored period','#ClockOK',A('#RawClock',N('#Backward'),C('#HourKey','>=','#HourCounter.CurrentKey'),C('#Day','>=','#DayCounter.CurrentKey')))
 b.coil('Recognize continuously observed time','#Continuous',A('#ClockOK','#HaveClock',N('#Fresh'),'#TickOK',C('#ClockStep','>=',0),C('#ClockStep','<=',2)))
 b.net('Latch a calendar warning',O(N('#RawClock'),'#Backward','#ClockJump'),move(R('ClockReview'),1))
 b.phase='Set the weekday shifts'
 b.coil('Monday through Friday','#S1Days',A(C('#Weekday','>=',2),C('#Weekday','<=',6)))
 b.coil('Monday through Thursday evenings','#S2EveningDays',A(C('#Weekday','>=',2),C('#Weekday','<=',5)))
 b.coil('Tuesday through Friday mornings','#S2MorningDays',A(C('#Weekday','>=',3),C('#Weekday','<=',6)))
 b.coil('Shift 1: weekdays 06:30 to 17:00','#Shift1',A('#ClockOK','#S1Days',C('#MinuteOfDay','>=',390),C('#MinuteOfDay','<',1020)))
 b.coil('Shift 2: evening OR following morning','#Shift2',A('#ClockOK',O(A('#S2EveningDays',C('#MinuteOfDay','>=',1020)),A('#S2MorningDays',C('#MinuteOfDay','<',360)))))
 b.coil('Production schedule is open','#Scheduled',O('#Shift1','#Shift2'))
 b.net('Use today as the shift start date',True,move('#ShiftDay','#Day'))
 b.net('Use yesterday for the overnight morning half',A('#Shift2',C('#MinuteOfDay','<',360)),math('SUB','#ShiftDay','#Day',1))
 b.coil('Expected MM6 configuration','#ConfigOK',A('%DB200.DBX38.2','%DB200.DBX49.3'))
 b.coil('Reporting is deliberately enabled','#Enabled',A(S('Enable'),S('WiringReviewed'),'#ConfigOK'))
 b.coil('Inputs, clock and execution are usable','#BaseGood',A('#Enabled','#RobotDataValid','#ClockOK','#TickOK',N('#Fresh'),N('#AbortCycle'),N('#ClockJump')))
 b.coil('Only observe production within the schedule','#AllowRun',A('#BaseGood','#Scheduled'))
 b.phase='Detect edges and synchronize'
 b.coil('One-scan closing rising edge','#CloseRise',A('#CloseCommand',N('#PrevClose'),N('#Fresh')))
 b.coil('One-scan robot-permission rising edge','#PermitRise',A('#RobotPermit',N('#PrevPermit'),N('#Fresh')))
 b.net('Snapshot the old observation state',True,move('#OldState','#State'))
 b.coil('Discard an untrustworthy or unscheduled observation','#Drop',O(N('#AllowRun'),A(C('#State','==',30),N('#ProductionEligible'))))
 b.coil('Remember an active cycle being discarded','#SkippedActive',A('#Drop',C('#State','==',30)))
 b.net('Count the discarded active observation','#SkippedActive',call('CSI_Increment',Value=R('PartialObservationsSkipped')))
 b.net('Discard only the observer’s live state','#Drop',move('#State',0),bit('#LowSeen',False),move('#CycleSec',0),move('#CycleMs',0),move('#GapSec',0),move('#GapMs',0),note='Held cycle/waiting values and production counters are not reset.')
 b.net('Begin synchronization',A('#AllowRun','#ProductionEligible',C('#State','==',0)),move('#State',10),bit('#LowSeen',False))
 b.net('Remember permission low while synchronizing',A('#AllowRun','#ProductionEligible',C('#State','==',10),N('#RobotPermit')),bit('#LowSeen',True))
 b.coil('Known robot-clear boundary, not a counted cycle','#SyncPulse',A('#AllowRun','#ProductionEligible',C('#State','==',10),'#LowSeen','#PermitRise'))
 b.net('Start a known gap after synchronization','#SyncPulse',move('#State',20),bit('#LowSeen',False),move('#GapSec',0),move('#GapMs',0))
 b.net('Record the skipped unknown first cycle','#SyncPulse',call('CSI_Increment',Value=R('PartialObservationsSkipped')))
 b.phase='Time a whole cycle and save it'
 b.net('Add elapsed time while the cycle is active',A('#AllowRun','#ProductionEligible',C('#State','==',30)),call('CSI_AddElapsed',DeltaMs='#Delta',Seconds='#CycleSec',Millis='#CycleMs'))
 b.net('Add elapsed time during a known wait',A('#AllowRun',C('#State','==',20),N('#SyncPulse')),call('CSI_AddElapsed',DeltaMs='#Delta',Seconds='#GapSec',Millis='#GapMs'),note='ProductionEligible may be FALSE during a normal wait; do not use it as an enable contact here.')
 b.net('Remember robot permission low inside this cycle',A('#AllowRun','#ProductionEligible',C('#State','==',30),N('#RobotPermit')),bit('#LowSeen',True))
 b.coil('One completed cycle pulse','#Complete',A('#AllowRun','#ProductionEligible',C('#State','==',30),'#LowSeen','#PermitRise'))
 b.net('Convert whole cycle seconds',True,conv('#CycleWhole','#CycleSec','DInt','Real'))
 b.net('Convert remaining cycle milliseconds',True,conv('#CycleFrac','#CycleMs','DInt','Real'))
 b.net('Assemble cycle seconds for display',True,calc('#CycleValue','IN1 + IN2 / 1000.0',['#CycleWhole','#CycleFrac'],'Real'))
 b.net('Store the completed duration before clearing it','#Complete',move(R('PreviousCycleSeconds'),'#CycleValue'),move(R('PreviousCycleValid'),1),move(R('LastCycleEndDate'),'#DateLabel'),move(R('LastCycleEndTime'),'#TimeLabel'))
 b.net('Add exactly one total production cycle','#Complete',call('CSI_Increment',Value=R('TotalCompleted')))
 b.net('End this cycle and begin its waiting interval','#Complete',move('#State',20),bit('#LowSeen',False),move('#GapSec',0),move('#GapMs',0),move('#CycleSec',0),move('#CycleMs',0))
 b.net('Record but ignore a secondary closing pulse',A('#AllowRun',C('#OldState','==',30),'#CloseRise',N('#Complete')),call('CSI_Increment',Value=R('IgnoredCloseEdges')))
 b.coil('Reject a close that was already high before the boundary','#Ambiguous',A(O('#SyncPulse','#Complete'),'#CloseCommand',N('#CloseRise')))
 b.net('Resynchronize rather than accept a later repress pulse','#Ambiguous',move('#State',10),bit('#LowSeen',False),move('#GapSec',0),move('#GapMs',0))
 b.phase='Capture the waiting interval and start the next cycle'
 b.coil('Accept the next closing start once','#StartPulse',A('#AllowRun','#ProductionEligible',C('#State','==',20),'#CloseRise'))
 b.net('Convert whole waiting seconds',True,conv('#GapWhole','#GapSec','DInt','Real'))
 b.net('Convert remaining waiting milliseconds',True,conv('#GapFrac','#GapMs','DInt','Real'))
 b.net('Assemble waiting seconds for display',True,calc('#GapValue','IN1 + IN2 / 1000.0',['#GapWhole','#GapFrac'],'Real'))
 b.net('Hold the finished waiting interval','#StartPulse',move(R('PreviousBetweenSeconds'),'#GapValue'),move(R('PreviousBetweenValid'),1))
 b.net('Begin the new measured cycle','#StartPulse',move('#State',30),move('#CycleSec',0),move('#CycleMs',0),move('#GapSec',0),move('#GapMs',0),bit('#LowSeen',False))
 b.net('Allow a start whose permission is already low',A('#StartPulse',N('#RobotPermit')),bit('#LowSeen',True))
 b.coil('Detect an unmeasured movement during a waiting interval','#ResyncGap',A('#AllowRun',C('#State','==',20),N('#SyncPulse'),N('#Complete'),O(N('#RobotPermit'),'#CloseRise')))
 b.net('Discard an ambiguous waiting interval','#ResyncGap',move('#State',10),bit('#LowSeen',False),move('#GapSec',0),move('#GapMs',0))
 b.phase='Hold and roll the hour, day and shift counters'
 b.coil('Whether the current observation is complete enough for period totals','#QualityGood',A('#ClockOK','#TickOK',N('#Fresh'),N('#ClockJump'),O(N('#Scheduled'),A('#BaseGood',N('#SkippedActive'),N('#Ambiguous'),N('#ResyncGap'),C('#State','!=',10),C('#State','!=',0)))))
 b.coil('The previous clock hour has ended','#EndHour',C('#HourKey','>','#HourCounter.CurrentKey'))
 b.coil('The previous calendar day has ended','#EndDay',C('#Day','>','#DayCounter.CurrentKey'))
 b.net('Calculate the night shift’s following date',True,math('ADD','#Shift2EndDay','#Shift2Counter.CurrentKey',1))
 b.coil('The stored day shift has ended','#EndShift1',O(C('#Day','>','#Shift1Counter.CurrentKey'),A(C('#Day','==','#Shift1Counter.CurrentKey'),C('#MinuteOfDay','>=',1020))))
 b.coil('The stored night shift has ended','#EndShift2',O(C('#Day','>','#Shift2EndDay'),A(C('#Day','==','#Shift2EndDay'),C('#MinuteOfDay','>=',360))))
 b.coil('Observed the start of a clock hour','#BoundaryHour',A(C('#Minute','==',0),C('#Second','<',3)))
 b.coil('Observed the start of a calendar day','#BoundaryDay',A(C('#MinuteOfDay','==',0),C('#Second','<',3)))
 b.coil('Observed 06:30 on a scheduled day','#BoundaryShift1',A('#Shift1',C('#MinuteOfDay','==',390),C('#Second','<',3)))
 b.coil('Observed 17:00 on a scheduled night','#BoundaryShift2',A('#Shift2',C('#MinuteOfDay','==',1020),C('#Second','<',3)))
 for inst,window,key,label,end,boundary in [('HourCounter',True,'#HourKey','#HourLabel','#EndHour','#BoundaryHour'),('DayCounter',True,'#Day','#DateLabel','#EndDay','#BoundaryDay'),('Shift1Counter','#Shift1','#Day','#Day','#EndShift1','#BoundaryShift1'),('Shift2Counter','#Shift2','#ShiftDay','#ShiftDay','#EndShift2','#BoundaryShift2')]:
  b.net('Update '+inst+' through its own multi-instance',True,call('CSI_PeriodCounter','#'+inst,ClockOK='#ClockOK',WindowActive=window,Key=key,Label=label,EndReached=end,BoundaryObserved=boundary,QualityGood='#QualityGood',Continuous='#Continuous',Restart='#Fresh',CountPulse='#Complete'),note='Call every scan, with EN directly on the rail. An inactive shift HOLDS CurrentCount; it does not reset it.')
 b.phase='Publish reporting tags and remember the inputs'
 mapping={'HourCounter':{'CurrentCount':'CyclesThisHour','PreviousCount':'CyclesPreviousHour','CurrentKey':'ThisHourKeyUTC','PreviousKey':'PreviousHourKeyUTC','CurrentLabel':'CurrentHourLocalLabel','PreviousLabel':'PreviousHourLocalLabel','CurrentPartial':'ThisHourPartial','PreviousPartial':'PreviousHourPartial'},'DayCounter':{'CurrentCount':'CyclesToday','PreviousCount':'CyclesPreviousDay','CurrentKey':'TodayKeyLocal','PreviousKey':'PreviousDayKeyLocal','CurrentPartial':'TodayPartial','PreviousPartial':'PreviousDayPartial'},'Shift1Counter':{'CurrentCount':'Shift1Current','PreviousCount':'Shift1Previous','CurrentKey':'Shift1Day','PreviousKey':'Shift1PreviousDay','CurrentPartial':'Shift1Partial','PreviousPartial':'Shift1PreviousPartial'},'Shift2Counter':{'CurrentCount':'Shift2Current','PreviousCount':'Shift2Previous','CurrentKey':'Shift2Day','PreviousKey':'Shift2PreviousDay','CurrentPartial':'Shift2Partial','PreviousPartial':'Shift2PreviousPartial'}}
 for inst,fields in mapping.items():b.net('Publish '+inst+' results',True,*[move(R(target),'#'+inst+'.'+field)for field,target in fields.items()])
 b.net('Default live duration displays to zero',True,move(R('CycleSeconds'),0.0),move(R('BetweenCycleSeconds'),0.0))
 b.net('Publish a live cycle, except on its starting scan',A(C('#State','==',30),N('#StartPulse')),move(R('CycleSeconds'),'#CycleValue'))
 b.net('Publish a live known waiting interval',C('#State','==',20),move(R('BetweenCycleSeconds'),'#GapValue'))
 b.net('Publish current state and readable clock',True,move(R('MonitorState'),'#State'),move(R('LocalDateYYYYMMDD'),'#DateLabel'),move(R('LocalTimeHHMMSS'),'#TimeLabel'),move(R('GapCompleted'),0),move(R('ClockUnassigned'),0),note='GapCompleted and ClockUnassigned are reserved zero in LAD revision 3; off-schedule or invalid-clock cycles are not counted.')
 flagmap={'CurrentShift':None,'SignalsValid':'#RobotDataValid','ClockValid':'#ClockOK','CycleActive':C('#State','==',30),'BetweenActive':C('#State','==',20),'ObserverEnabled':'#Enabled','ConfigurationOK':'#ConfigOK','ProductionMode':'#ProductionEligible','AbortActive':'#AbortCycle','CloseCommand':'#CloseCommand','RobotPermit':'#RobotPermit','Synchronized':O(C('#State','==',20),C('#State','==',30))}
 b.net('Clear integer status fields before setting their TRUE values',True,*[move(R(n),0)for n in flagmap])
 for field,g in flagmap.items():
  if g is not None:b.net('Set '+field+' status',g,move(R(field),1))
 b.net('Show shift 1 only inside its window','#Shift1',move(R('CurrentShift'),1))
 b.net('Show shift 2 only inside its window','#Shift2',move(R('CurrentShift'),2))
 b.net('Record initialization/restart','#Fresh',call('CSI_Increment',Value=R('RestartEvents')))
 b.net('Remember the latest non-backward UTC time',A('#RawClock',N('#Backward')),move('#LastUtcMinute','#UtcMinuteKey'),move('#LastUtcSecond','#UtcSecond'),bit('#HaveClock',True))
 b.coil('Remember the closing input LAST','#PrevClose','#CloseCommand')
 b.coil('Remember the robot input LAST','#PrevPermit','#RobotPermit')
 b.net('Seed the next scan and consume startup',True,move('#PrevTick','#TickNow'),bit('#Initialized',True),bit(S('StartupPending'),False))
 # Expand arithmetic operand in a comparison into a named temp and native ADD network.
 out=[]
 b.vars('Temp','DInt','LastUtcMinutePlusOne')
 for net in b.networks:
  if net['title']=='Calculate a short calendar separation':
   out.append(dict(number=0,title='Prepare the UTC minute comparison limit',phase=net['phase'],gate=True,actions=[math('ADD','#LastUtcMinutePlusOne','#LastUtcMinute',1)],note=''))
   net['gate']=A('#RawClock','#HaveClock',C('#UtcMinuteKey','>=','#LastUtcMinute'),C('#UtcMinuteKey','<=','#LastUtcMinutePlusOne'));net['note']=''
  out.append(net)
 for i,net in enumerate(out):net['number']=i+1
 b.networks=out
 return b

BLOCKS={b.name:b for b in [increment(),elapsed(),period(),reporting()]}
