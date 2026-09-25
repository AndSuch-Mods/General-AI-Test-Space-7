"""Independent behavioral model, not a Siemens SCL compiler/interpreter."""
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
MAX=2147483647
EPOCH=date(1990,1,1)
def serial(d):return (d-EPOCH).days

def day_number(year,month,day):
    if not 1990<=year<=2089 or not 1<=month<=12:return -1
    leap=year%4==0 and (year%100!=0 or year%400==0)
    y=year-1; ordinal=y*365+y//4-y//100+y//400
    for m in range(1,month+1):
        md=29 if m==2 and leap else 28 if m==2 else 30 if m in (4,6,9,11) else 31
        if m<month:ordinal+=md
    return ordinal+day-726468 if 1<=day<=md else -1

@dataclass
class Period:
    count:int=0; previous:int=0; key:int=-1; previous_key:int=-1
    label:int=0; previous_label:int=0; partial:bool=True; previous_partial:bool=True
    have:bool=False; closed:bool=False; last_ok:bool=False; last_key:int=-1
    def scan(self,clock,continuity,collection,key,label,active,pulse):
        if not clock:
            if self.have and not self.closed:self.partial=True
            self.last_ok=False; return
        if self.have and key<self.key:
            self.partial=True;self.last_ok=False;return
        cont=continuity and self.last_ok and key in (self.last_key,self.last_key+1)
        if self.have and not self.closed:
            if not cont or not collection:self.partial=True
            if key!=self.key or not active:
                self.previous=self.count;self.previous_key=self.key;self.previous_label=self.label
                self.previous_partial=self.partial;self.closed=True
        if active:
            if not self.have or key!=self.key:
                self.have=True;self.closed=False;self.count=0;self.key=key;self.label=label
                self.partial=not cont or not collection
            if not self.closed:
                if not collection or not cont:self.partial=True
                if pulse:self.count=min(MAX,self.count+1)
        self.last_key=key;self.last_ok=True

@dataclass
class Monitor:
    initialized:bool=False; state:int=0; prev_tick:int=0;prev_close:bool=False;prev_permit:bool=False
    sync_low:bool=False;cycle_low:bool=False;cycle_ms:int=0;gap_ms:int=0
    previous_cycle:float|None=None;previous_gap:float|None=None
    total:int=0;gap_count:int=0;unassigned:int=0;skipped:int=0;ignored:int=0;restarts:int=0
    timing_fault:bool=False;clock_review:bool=False;have_utc:bool=False;last_utc:int=0;last_clock:bool=False
    hour:Period=field(default_factory=Period); day:Period=field(default_factory=Period)
    s1:Period=field(default_factory=Period);s2:Period=field(default_factory=Period)
    def scan(self,tick,local,close=False,permit=True,enabled=True,signals=True,production=True,abort=False,restart=False,clock=True):
        utc=local.astimezone(timezone.utc)
        fresh=not self.initialized or restart;delta=0;tick_ok=tick>=0
        if fresh:
            self.initialized=True;self.state=0;self.sync_low=False;self.cycle_low=False
            self.cycle_ms=0;self.gap_ms=0;self.prev_close=close;self.prev_permit=permit
            self.prev_tick=tick;self.have_utc=False;self.last_clock=False;self.restarts+=1
        elif tick_ok:
            delta=(tick-self.prev_tick)%(MAX+1)
            if delta>10000:tick_ok=False;delta=0;self.timing_fault=True
        self.prev_tick=tick
        ce=close and not self.prev_close and not fresh;pe=permit and not self.prev_permit and not fresh
        qualified=enabled and signals and tick_ok and not fresh;complete=False;boundary=False
        if not qualified or abort or (self.state==30 and not production):
            if self.state==30:self.skipped+=1
            self.state=0;self.sync_low=False;self.cycle_low=False;self.cycle_ms=0;self.gap_ms=0
        if qualified and not abort:
            if self.state==0:self.state=10;self.sync_low=False
            if self.state==10:
                if production:
                    if not permit:self.sync_low=True
                    if self.sync_low and pe:
                        boundary=True;self.state=20;self.gap_ms=0;self.sync_low=False;self.skipped+=1
                else:self.sync_low=False
            elif self.state==20:
                self.gap_ms+=delta
                if not permit or (ce and not production):
                    self.state=10;self.sync_low=not permit and production;self.gap_ms=0
            elif self.state==30:
                self.cycle_ms+=delta
                if not permit:self.cycle_low=True
                complete=self.cycle_low and pe
                if complete:
                    boundary=True;self.previous_cycle=self.cycle_ms/1000
                    self.total=min(MAX,self.total+1);self.state=20;self.cycle_ms=0;self.gap_ms=0;self.cycle_low=False
                elif ce:self.ignored=min(MAX,self.ignored+1)
            if boundary and close and not ce:
                self.state=10;self.sync_low=False;self.gap_ms=0
            if self.state==20 and production and permit and ce:
                self.previous_gap=self.gap_ms/1000;self.state=30;self.cycle_ms=0;self.gap_ms=0;self.cycle_low=False
        collection=qualified and not abort and self.state in (20,30)
        d=serial(local.date());ud=serial(utc.date());h=ud*24+utc.hour;m=local.hour*60+local.minute
        k1=d if m>=390 else d-1;k2=d if m>=1020 else d-1
        continuity=self.last_clock and tick_ok and not fresh
        valid=clock and 0<=d<=36524 and 0<=ud<=36524
        date_label=local.year*10000+local.month*100+local.day
        if valid:
            utcsec=ud*86400+utc.hour*3600+utc.minute*60+utc.second
            if self.have_utc:
                step=utcsec-self.last_utc
                if step<0:valid=False;continuity=False;self.clock_review=True
                elif step>delta//1000+2:continuity=False;self.clock_review=True
            if h<self.hour.key or d<self.day.key or k1<self.s1.key or k2<self.s2.key:
                valid=False;continuity=False;self.clock_review=True
            if valid:self.last_utc=utcsec;self.have_utc=True
        if not valid:continuity=False;self.clock_review=True
        self.last_clock=valid
        a1=390<=m<1020;a2=m>=1020 or m<360
        self.hour.scan(valid,continuity,collection,h,date_label*100+local.hour,True,complete)
        self.day.scan(valid,continuity,collection,d,date_label,True,complete)
        self.s1.scan(valid,continuity,collection,k1,k1,a1,complete)
        self.s2.scan(valid,continuity,collection,k2,k2,a2,complete)
        if complete:
            if not valid:self.unassigned+=1
            elif not a1 and not a2:self.gap_count+=1
        self.prev_close=close;self.prev_permit=permit
        return complete
