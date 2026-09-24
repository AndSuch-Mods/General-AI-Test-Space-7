"""Independent Python reference for reviewing the SCL event/calendar rules.
This is not a Siemens compiler or an execution of the SCL source.
"""
from datetime import datetime, date
MAX=2147483647
EPOCH=date(1990,1,1)
def day_number(year,month,day):
    if not 1990<=year<=2089 or not 1<=month<=12:return -1
    leap=year%4==0 and (year%100!=0 or year%400==0)
    y=year-1
    result=y*365+y//4-y//100+y//400
    for m in range(1,month+1):
        md=29 if leap and m==2 else 28 if m==2 else 30 if m in (4,6,9,11) else 31
        if m<month:result+=md
    return result+day-726468 if 1<=day<=md else -1

def shift_at(now):
    d=(now.date()-EPOCH).days; minute=now.hour*60+now.minute
    if 390<=minute<1020:return 1,d
    if minute>=1020:return 2,d
    if minute<360:return 2,d-1
    return 0,d

def tick_delta(previous,current):return current-previous if current>=previous else MAX-previous+current+1

class Model:
    def __init__(self):
        self.initialized=False; self.active=False; self.between=False; self.armed=False
        self.low=False; self.cycle_ms=0; self.between_ms=0; self.last_tick=0
        self.close=False; self.permit=False; self.prev_cycle=None; self.prev_between=None
        self.total=0; self.gap=0; self.clock_unassigned=0
        self.hour_key=-1;self.hour_count=0;self.previous_hour=None
        self.shift_count={1:0,2:0};self.shift_day={1:-1,2:-1};self.previous_shift={1:None,2:None}
        self.high_water=None
    def scan(self,tick,now,close=False,permit=True,production=True,signals=True,enable=True,abort=False,restart=False,clock=True):
        fresh=not self.initialized or restart
        if fresh:
            self.active=False;self.between=False;self.armed=False;self.low=False
            self.cycle_ms=0;self.between_ms=0;self.close=close;self.permit=permit
            self.last_tick=tick;self.initialized=True;self.high_water=None
        delta=0 if fresh else tick_delta(self.last_tick,tick)
        tick_good=tick>=0 and 0<=delta<=10000
        if not tick_good:delta=0
        self.last_tick=tick
        qualified=enable and signals and tick_good and not fresh
        ce=close and not self.close and not fresh;pe=permit and not self.permit and not fresh
        h=(now.date()-EPOCH).days*24+now.hour
        calendar=clock and (self.high_water is None or now>=self.high_water) and h>=self.hour_key
        s=0
        if calendar:
            self.high_water=now
            d=(now.date()-EPOCH).days;mins=now.hour*60+now.minute
            if h!=self.hour_key:
                if self.hour_key>=0:self.previous_hour=(self.hour_key,self.hour_count)
                self.hour_key=h;self.hour_count=0
            if self.shift_day[1]>=0 and (self.previous_shift[1] is None or self.previous_shift[1][0]!=self.shift_day[1]) and (d>self.shift_day[1] or (d==self.shift_day[1] and mins>=1020)):
                self.previous_shift[1]=(self.shift_day[1],self.shift_count[1])
            if self.shift_day[2]>=0 and (self.previous_shift[2] is None or self.previous_shift[2][0]!=self.shift_day[2]) and (d>self.shift_day[2]+1 or (d==self.shift_day[2]+1 and mins>=360)):
                self.previous_shift[2]=(self.shift_day[2],self.shift_count[2])
            s,sd=shift_at(now)
            if s and self.shift_day[s]!=sd:self.shift_day[s]=sd;self.shift_count[s]=0
        if not qualified or abort or (self.active and not production):
            self.active=False;self.between=False;self.armed=False;self.low=False;self.cycle_ms=0;self.between_ms=0
        if qualified and production and not abort and not close:self.armed=True
        if self.active:self.cycle_ms=min(MAX,self.cycle_ms+delta)
        if self.between:self.between_ms=min(MAX,self.between_ms+delta)
        if self.active and not permit:self.low=True
        complete=self.active and self.low and pe and qualified and production and not abort
        if complete:
            self.prev_cycle=self.cycle_ms/1000;self.total=min(MAX,self.total+1)
            if calendar:
                self.hour_count=min(MAX,self.hour_count+1)
                if s:self.shift_count[s]=min(MAX,self.shift_count[s]+1)
                else:self.gap=min(MAX,self.gap+1)
            else:self.clock_unassigned=min(MAX,self.clock_unassigned+1)
            self.active=False;self.cycle_ms=0;self.between=True;self.between_ms=0;self.low=False
        if qualified and production and not abort and self.armed and ce and not self.active:
            if self.between:self.prev_between=self.between_ms/1000
            self.active=True;self.armed=False;self.cycle_ms=0;self.between=False;self.between_ms=0;self.low=not permit
        self.close=close;self.permit=permit
        return complete
