from pathlib import Path
import json
R=Path(__file__).parent; F=json.loads((R/'schema.json').read_text()); D=R/'downloads'
header='// REVIEW REFERENCE ONLY: not compiled in TIA or tested on a machine.\n// New standard reporting blocks only. Never replace existing OBs or F-blocks.\n// Assign unused block numbers in TIA; verify absolute report offsets after compile.\n// Configure retention on the actual CPU. ObserverEnable defaults to zero.\n\n'
core=header+'DATA_BLOCK "CSI_Report"\nVERSION : 0.1\nVAR\n'
for f in F:core+=f'    {f["name"]} : {f["type"]} := {f["initial"]}; // expected byte {f["offset"]}: {f["description"]}\n'
core+='END_VAR\nBEGIN\nEND_DATA_BLOCK\n\n'
core+='''DATA_BLOCK "CSI_IO"
VERSION : 0.1
VAR
    StartupPending : Bool := TRUE;
    EnableRun : Bool := FALSE;
    CloseCommand : Bool := FALSE;
    RobotPermit : Bool := FALSE;
    ProductionMode : Bool := FALSE;
    SignalsValid : Bool := FALSE;
    AbortCycle : Bool := FALSE;
    ClockOK : Bool := FALSE;
    TickMs : DInt := 0;
    DaySerial : DInt := -1;
    MinuteOfDay : Int := 0;
    Second : Int := 0;
    ClockStatus : Int := 0;
END_VAR
BEGIN
END_DATA_BLOCK

FUNCTION "CSI_DayNumber" : DInt
VERSION : 0.1
VAR_INPUT
    Year : Int;
    Month : Int;
    Day : Int;
END_VAR
VAR_TEMP
    y : DInt;
    m : Int;
    md : Int;
    ordinal : DInt;
    leap : Bool;
END_VAR
BEGIN
    #CSI_DayNumber := -1;
    IF (#Year < 1990) OR (#Year > 2089) OR (#Month < 1) OR (#Month > 12) THEN
        RETURN;
    END_IF;
    #leap := ((#Year MOD 4) = 0) AND (((#Year MOD 100) <> 0) OR ((#Year MOD 400) = 0));
    #y := INT_TO_DINT(#Year) - 1;
    #ordinal := #y * 365 + #y / 4 - #y / 100 + #y / 400;
    FOR #m := 1 TO #Month DO
        CASE #m OF
            4,6,9,11: #md := 30;
            2: IF #leap THEN #md := 29; ELSE #md := 28; END_IF;
            ELSE #md := 31;
        END_CASE;
        IF #m < #Month THEN
            #ordinal := #ordinal + INT_TO_DINT(#md);
        END_IF;
    END_FOR;
    IF (#Day < 1) OR (#Day > #md) THEN RETURN; END_IF;
    #CSI_DayNumber := #ordinal + INT_TO_DINT(#Day) - 726468;
END_FUNCTION

FUNCTION "CSI_Increment" : DInt
VERSION : 0.1
VAR_INPUT
    Value : DInt;
END_VAR
BEGIN
    IF #Value < 2147483647 THEN
        #CSI_Increment := #Value + 1;
    ELSE
        #CSI_Increment := 2147483647;
        "CSI_Report".CounterSaturated := 1;
    END_IF;
END_FUNCTION

FUNCTION_BLOCK "CSI_CycleMonitor"
VERSION : 0.1
VAR_INPUT
    Enable : Bool;
    Restart : Bool;
    CloseCommand : Bool;
    RobotPermit : Bool;
    ProductionMode : Bool;
    SignalsValid : Bool;
    AbortCycle : Bool;
    TickMs : DInt;
    ClockOK : Bool;
    DaySerial : DInt;
    MinuteOfDay : Int;
    Second : Int;
END_VAR
VAR
    Initialized : Bool := FALSE;
    PreviousTick : DInt := 0;
    PreviousClose : Bool := FALSE;
    PreviousPermit : Bool := FALSE;
    Armed : Bool := FALSE;
    Active : Bool := FALSE;
    BetweenKnown : Bool := FALSE;
    PermitLowSeen : Bool := FALSE;
    CycleMs : DInt := 0;
    BetweenMs : DInt := 0;
    CalendarSeeded : Bool := FALSE;
    CalendarContinuous : Bool := FALSE;
    LastDay : DInt := 0;
    LastSecondOfDay : DInt := 0;
    LastShift : Int := 0;
END_VAR
VAR_TEMP
    Fresh : Bool;
    TickGood : Bool;
    Qualified : Bool;
    CalendarGood : Bool;
    WasContinuous : Bool;
    Jump : Bool;
    CloseEdge : Bool;
    PermitEdge : Bool;
    Complete : Bool;
    Delta : DInt;
    CalendarDelta : DInt;
    SecondOfDay : DInt;
    HourKey : DInt;
    Shift : Int;
    ShiftDay : DInt;
END_VAR
BEGIN
    // Execute once per normal scan, even when disabled. This writes only new reporting data.
    "CSI_Report".SchemaVersion := 1;
    IF "CSI_Report".Heartbeat >= 2147483647 THEN
        "CSI_Report".Heartbeat := 0;
    ELSE
        "CSI_Report".Heartbeat := "CSI_Report".Heartbeat + 1;
    END_IF;
    IF #SignalsValid THEN "CSI_Report".SignalsValid := 1;
    ELSE "CSI_Report".SignalsValid := 0; END_IF;

    #Fresh := NOT #Initialized OR #Restart;
    #TickGood := (#TickMs >= 0);
    #Delta := 0;
    IF #Fresh THEN
        #Active := FALSE;
        #BetweenKnown := FALSE;
        #Armed := FALSE;
        #PermitLowSeen := FALSE;
        #CycleMs := 0;
        #BetweenMs := 0;
        #PreviousClose := #CloseCommand;
        #PreviousPermit := #RobotPermit;
        #PreviousTick := #TickMs;
        #CalendarSeeded := FALSE;
        #CalendarContinuous := FALSE;
        #Initialized := TRUE;
        "CSI_Report".ThisHourPartial := 1;
        "CSI_Report".Shift1Partial := 1;
        "CSI_Report".Shift2Partial := 1;
    ELSIF #TickGood THEN
        IF #TickMs >= #PreviousTick THEN
            #Delta := #TickMs - #PreviousTick;
        ELSE
            // Normal TIME_TCK wrap, 2147483647 -> 0.
            #Delta := (2147483647 - #PreviousTick) + #TickMs + 1;
        END_IF;
        IF (#Delta < 0) OR (#Delta > 10000) THEN
            #TickGood := FALSE;
            #Delta := 0;
            "CSI_Report".TimingFault := 1;
        END_IF;
    END_IF;
    #PreviousTick := #TickMs;
    #CloseEdge := #CloseCommand AND NOT #PreviousClose AND NOT #Fresh;
    #PermitEdge := #RobotPermit AND NOT #PreviousPermit AND NOT #Fresh;
    #Qualified := #Enable AND #SignalsValid AND #TickGood AND NOT #Fresh;

    // Calendar housekeeping happens every scan, not only on a completed cycle.
    #WasContinuous := #CalendarContinuous;
    #CalendarGood := #ClockOK AND (#DaySerial >= 0) AND (#DaySerial <= 36524)
                     AND (#MinuteOfDay >= 0) AND (#MinuteOfDay < 1440)
                     AND (#Second >= 0) AND (#Second < 60);
    #Jump := FALSE;
    #HourKey := -1;
    #Shift := 0;
    IF #CalendarGood THEN
        #SecondOfDay := INT_TO_DINT(#MinuteOfDay) * 60 + INT_TO_DINT(#Second);
        #HourKey := #DaySerial * 24 + INT_TO_DINT(#MinuteOfDay / 60);
        IF #CalendarSeeded THEN
            // Compare without multiplying an absolute date by 86400 (DINT overflow risk).
            IF ABS(#DaySerial - #LastDay) > 1 THEN
                #Jump := TRUE;
                IF #DaySerial < #LastDay THEN #CalendarGood := FALSE; END_IF;
            ELSE
                #CalendarDelta := (#DaySerial - #LastDay) * 86400 + #SecondOfDay - #LastSecondOfDay;
                IF #CalendarDelta < 0 THEN
                    // Keep the old high-water mark. Do not overwrite a prior hour on fall-back.
                    #CalendarGood := FALSE;
                    #Jump := TRUE;
                ELSIF #CalendarDelta > 5 THEN
                    #Jump := TRUE;
                END_IF;
            END_IF;
        END_IF;
        IF (#HourKey < "CSI_Report".ThisHourKey) THEN
            #CalendarGood := FALSE;
            #Jump := TRUE;
        END_IF;
    END_IF;
    IF #Jump OR NOT #CalendarGood THEN
        "CSI_Report".ClockReview := 1;
        #WasContinuous := FALSE;
    END_IF;
    IF NOT #Qualified OR #AbortCycle OR #Jump OR NOT #CalendarGood THEN
        "CSI_Report".ThisHourPartial := 1;
        "CSI_Report".Shift1Partial := 1;
        "CSI_Report".Shift2Partial := 1;
    END_IF;
    IF #CalendarGood THEN
        "CSI_Report".ClockValid := 1;
        // Capture old hour before accepting a completion in the new one.
        IF #HourKey <> "CSI_Report".ThisHourKey THEN
            IF "CSI_Report".ThisHourKey >= 0 THEN
                "CSI_Report".CyclesPreviousHour := "CSI_Report".CyclesThisHour;
                "CSI_Report".PreviousHourKey := "CSI_Report".ThisHourKey;
                "CSI_Report".PreviousHourPartial := "CSI_Report".ThisHourPartial;
                IF NOT #WasContinuous OR (#HourKey <> "CSI_Report".ThisHourKey + 1) THEN
                    "CSI_Report".PreviousHourPartial := 1;
                END_IF;
            END_IF;
            "CSI_Report".CyclesThisHour := 0;
            "CSI_Report".ThisHourPartial := 1;
            IF #WasContinuous AND #Qualified AND NOT #AbortCycle AND (#HourKey = "CSI_Report".ThisHourKey + 1) THEN
                "CSI_Report".ThisHourPartial := 0;
            END_IF;
            "CSI_Report".ThisHourKey := #HourKey;
        END_IF;
        // Close dated shifts once their end has passed, including entry into the 06:00 gap.
        IF ("CSI_Report".Shift1Day >= 0)
            AND ("CSI_Report".Shift1PreviousDay <> "CSI_Report".Shift1Day)
            AND ((#DaySerial > "CSI_Report".Shift1Day)
              OR ((#DaySerial = "CSI_Report".Shift1Day) AND (#MinuteOfDay >= 1020))) THEN
            "CSI_Report".Shift1Previous := "CSI_Report".Shift1Current;
            "CSI_Report".Shift1PreviousDay := "CSI_Report".Shift1Day;
            "CSI_Report".Shift1PreviousPartial := "CSI_Report".Shift1Partial;
            IF NOT #WasContinuous THEN "CSI_Report".Shift1PreviousPartial := 1; END_IF;
        END_IF;
        IF ("CSI_Report".Shift2Day >= 0)
            AND ("CSI_Report".Shift2PreviousDay <> "CSI_Report".Shift2Day)
            AND ((#DaySerial > "CSI_Report".Shift2Day + 1)
              OR ((#DaySerial = "CSI_Report".Shift2Day + 1) AND (#MinuteOfDay >= 360))) THEN
            "CSI_Report".Shift2Previous := "CSI_Report".Shift2Current;
            "CSI_Report".Shift2PreviousDay := "CSI_Report".Shift2Day;
            "CSI_Report".Shift2PreviousPartial := "CSI_Report".Shift2Partial;
            IF NOT #WasContinuous THEN "CSI_Report".Shift2PreviousPartial := 1; END_IF;
        END_IF;
        #ShiftDay := #DaySerial;
        IF (#MinuteOfDay >= 390) AND (#MinuteOfDay < 1020) THEN
            #Shift := 1;
        ELSIF (#MinuteOfDay >= 1020) OR (#MinuteOfDay < 360) THEN
            #Shift := 2;
            IF #MinuteOfDay < 360 THEN #ShiftDay := #DaySerial - 1; END_IF;
        ELSE
            #Shift := 0;
        END_IF;
        IF (#Shift = 1) AND ("CSI_Report".Shift1Day <> #ShiftDay) THEN
            "CSI_Report".Shift1Day := #ShiftDay;
            "CSI_Report".Shift1Current := 0;
            "CSI_Report".Shift1Partial := 1;
            IF #WasContinuous AND #Qualified AND NOT #AbortCycle AND (#LastShift = 0) AND (#MinuteOfDay = 390) THEN
                "CSI_Report".Shift1Partial := 0;
            END_IF;
        END_IF;
        IF (#Shift = 2) AND ("CSI_Report".Shift2Day <> #ShiftDay) THEN
            "CSI_Report".Shift2Day := #ShiftDay;
            "CSI_Report".Shift2Current := 0;
            "CSI_Report".Shift2Partial := 1;
            IF #WasContinuous AND #Qualified AND NOT #AbortCycle AND (#LastShift = 1) AND (#MinuteOfDay = 1020) THEN
                "CSI_Report".Shift2Partial := 0;
            END_IF;
        END_IF;
        #LastShift := #Shift;
        #LastDay := #DaySerial;
        #LastSecondOfDay := #SecondOfDay;
        #CalendarSeeded := TRUE;
        #CalendarContinuous := TRUE;
    ELSE
        "CSI_Report".ClockValid := 0;
        #CalendarContinuous := FALSE;
    END_IF;
    "CSI_Report".CurrentShift := INT_TO_DINT(#Shift);

    // Loss of trustworthy inputs discards the unknown interval, not held history.
    IF NOT #Qualified OR #AbortCycle OR (#Active AND NOT #ProductionMode) THEN
        IF #Active THEN
            "CSI_Report".ThisHourPartial := 1;
            "CSI_Report".Shift1Partial := 1;
            "CSI_Report".Shift2Partial := 1;
        END_IF;
        #Active := FALSE;
        #BetweenKnown := FALSE;
        #PermitLowSeen := FALSE;
        #Armed := FALSE;
        #CycleMs := 0;
        #BetweenMs := 0;
    END_IF;
    IF #Qualified AND #ProductionMode AND NOT #AbortCycle AND NOT #CloseCommand THEN
        #Armed := TRUE;
    END_IF;
    // Saturate elapsed storage instead of allowing signed TIME/DINT rollover.
    IF #Active THEN
        IF #CycleMs <= 2147483647 - #Delta THEN #CycleMs := #CycleMs + #Delta;
        ELSE #CycleMs := 2147483647; "CSI_Report".TimingFault := 1; END_IF;
    END_IF;
    IF #BetweenKnown THEN
        IF #BetweenMs <= 2147483647 - #Delta THEN #BetweenMs := #BetweenMs + #Delta;
        ELSE #BetweenMs := 2147483647; "CSI_Report".TimingFault := 1; END_IF;
    END_IF;
    IF #Active AND NOT #RobotPermit THEN #PermitLowSeen := TRUE; END_IF;
    #Complete := #Active AND #PermitLowSeen AND #PermitEdge
                 AND #Qualified AND #ProductionMode AND NOT #AbortCycle;
    IF #Complete THEN
        "CSI_Report".PreviousCycleSeconds := DINT_TO_REAL(#CycleMs) / 1000.0;
        "CSI_Report".PreviousCycleValid := 1;
        "CSI_Report".TotalCompleted := "CSI_Increment"(Value := "CSI_Report".TotalCompleted);
        IF #CalendarGood THEN
            "CSI_Report".CyclesThisHour := "CSI_Increment"(Value := "CSI_Report".CyclesThisHour);
            CASE #Shift OF
                1: "CSI_Report".Shift1Current := "CSI_Increment"(Value := "CSI_Report".Shift1Current);
                2: "CSI_Report".Shift2Current := "CSI_Increment"(Value := "CSI_Report".Shift2Current);
                ELSE "CSI_Report".GapCompleted := "CSI_Increment"(Value := "CSI_Report".GapCompleted);
            END_CASE;
        ELSE
            "CSI_Report".ClockUnassigned := "CSI_Increment"(Value := "CSI_Report".ClockUnassigned);
        END_IF;
        #Active := FALSE;
        #CycleMs := 0;
        #BetweenKnown := TRUE;
        #BetweenMs := 0;
        #PermitLowSeen := FALSE;
    END_IF;
    // Completion first permits a legitimate same-scan next start with a zero observed gap.
    IF #Qualified AND #ProductionMode AND NOT #AbortCycle AND #Armed AND #CloseEdge AND NOT #Active THEN
        IF #BetweenKnown THEN
            "CSI_Report".PreviousBetweenSeconds := DINT_TO_REAL(#BetweenMs) / 1000.0;
            "CSI_Report".PreviousBetweenValid := 1;
        END_IF;
        #Active := TRUE;
        #Armed := FALSE;
        #CycleMs := 0;
        #BetweenKnown := FALSE;
        #BetweenMs := 0;
        #PermitLowSeen := NOT #RobotPermit;
    END_IF;
    "CSI_Report".CycleSeconds := DINT_TO_REAL(#CycleMs) / 1000.0;
    "CSI_Report".BetweenCycleSeconds := DINT_TO_REAL(#BetweenMs) / 1000.0;
    "CSI_Report".CycleActive := 0;
    "CSI_Report".BetweenActive := 0;
    "CSI_Report".MonitorState := 0;
    IF #Active THEN
        "CSI_Report".CycleActive := 1;
        "CSI_Report".MonitorState := 2;
    ELSIF #BetweenKnown THEN
        "CSI_Report".BetweenActive := 1;
        "CSI_Report".MonitorState := 1;
    END_IF;
    #PreviousClose := #CloseCommand;
    #PreviousPermit := #RobotPermit;
END_FUNCTION_BLOCK
'''
# Give MM6 only the source access attributes supported by its family; legacy stays plain.
modern=core
for typ,name in [('DATA_BLOCK','CSI_Report'),('DATA_BLOCK','CSI_IO'),('FUNCTION_BLOCK','CSI_CycleMonitor')]:
 modern=modern.replace(typ+' "'+name+'"\n',typ+' "'+name+'"\n{ S7_Optimized_Access := \'FALSE\' }\n')
(D/'CSI_Core_Legacy.scl').write_text(core,encoding='utf-8-sig')
(D/'CSI_Core_1500.scl').write_text(modern,encoding='utf-8-sig')
clock1500=header+'''FUNCTION "CSI_Clock" : Void
VERSION : 0.1
VAR_TEMP
    stamp : DTL;
    rc : Int;
END_VAR
BEGIN
    "CSI_IO".TickMs := TIME_TO_DINT(TIME_TCK());
    #rc := RD_LOC_T(OUT => #stamp);
    "CSI_IO".ClockStatus := #rc;
    "CSI_IO".ClockOK := (#rc = 0) OR (#rc = 1); // 1 = daylight-saving time, not failure.
    IF "CSI_IO".ClockOK THEN
        "CSI_IO".DaySerial := "CSI_DayNumber"(Year := UINT_TO_INT(#stamp.YEAR),
            Month := USINT_TO_INT(#stamp.MONTH), Day := USINT_TO_INT(#stamp.DAY));
        "CSI_IO".MinuteOfDay := USINT_TO_INT(#stamp.HOUR) * 60 + USINT_TO_INT(#stamp.MINUTE);
        "CSI_IO".Second := USINT_TO_INT(#stamp.SECOND);
        "CSI_IO".ClockOK := ("CSI_IO".DaySerial >= 0);
    END_IF;
END_FUNCTION
'''
legacy=header+'''FUNCTION "CSI_Clock" : Void
VERSION : 0.1
VAR_TEMP
    stamp : Date_And_Time;
    octets AT stamp : Array[0..7] of Byte;
    decoded : Array[0..5] of Int;
    rc : Int;
    i : Int;
    n : Int;
    yr : Int;
    validBCD : Bool;
END_VAR
BEGIN
    // Verify READ_CLK (SFC1), TIME_TCK (SFC64) and AT syntax with target F1 help.
    "CSI_IO".TickMs := TIME_TO_DINT(TIME_TCK());
    #rc := READ_CLK(CDT => #stamp);
    "CSI_IO".ClockStatus := #rc;
    "CSI_IO".ClockOK := (#rc = 0);
    IF "CSI_IO".ClockOK THEN
        #validBCD := TRUE;
        FOR #i := 0 TO 5 DO
            #n := BYTE_TO_INT(#octets[#i]);
            IF ((#n / 16) > 9) OR ((#n MOD 16) > 9) THEN #validBCD := FALSE; END_IF;
            #decoded[#i] := (#n / 16) * 10 + (#n MOD 16);
        END_FOR;
        #yr := #decoded[0];
        IF #yr >= 90 THEN #yr := #yr + 1900; ELSE #yr := #yr + 2000; END_IF;
        "CSI_IO".DaySerial := "CSI_DayNumber"(Year := #yr, Month := #decoded[1], Day := #decoded[2]);
        "CSI_IO".MinuteOfDay := #decoded[3] * 60 + #decoded[4];
        "CSI_IO".Second := #decoded[5];
        "CSI_IO".ClockOK := #validBCD AND ("CSI_IO".DaySerial >= 0)
            AND (#decoded[3] < 24) AND (#decoded[4] < 60) AND (#decoded[5] < 60);
    END_IF;
END_FUNCTION
'''
(D/'CSI_Clock_1500.scl').write_text(clock1500,encoding='utf-8-sig')
(D/'CSI_Clock_Legacy.scl').write_text(legacy,encoding='utf-8-sig')
call='''CALL RECIPE, NOT A SOURCE FILE TO IMPORT OVER OB1

1. Add the call to CSI_Clock at the approved end of OB1.
2. Map verified existing conditions INTO the new CSI_IO fields:
   CloseCommand, RobotPermit, ProductionMode, SignalsValid, AbortCycle.
3. Insert CSI_CycleMonitor as an FB call; TIA creates a new unused single-instance DB.
   Enable       = CSI_IO.EnableRun
   Before the call, calculate CSI_IO.EnableRun from CSI_Report.ObserverEnable = 1.
   Restart      = CSI_IO.StartupPending
   CloseCommand = CSI_IO.CloseCommand
   RobotPermit  = CSI_IO.RobotPermit
   ProductionMode = CSI_IO.ProductionMode
   SignalsValid = CSI_IO.SignalsValid
   AbortCycle   = CSI_IO.AbortCycle
   TickMs       = CSI_IO.TickMs
   ClockOK      = CSI_IO.ClockOK
   DaySerial    = CSI_IO.DaySerial
   MinuteOfDay  = CSI_IO.MinuteOfDay
   Second       = CSI_IO.Second
4. AFTER that call, write FALSE to CSI_IO.StartupPending.
5. In the applicable existing startup OB(s), append a write of TRUE to CSI_IO.StartupPending.
   Do not overwrite the existing startup program. Confirm CPU startup modes.
6. ObserverEnable stays 0 until compilation, mapping and commissioning checks are complete.

No motion, output, robot-permission, existing counter, safety or hardware configuration is written.
New block names are examples; verify they are unused before source generation.
Core + correct adapter requires actual TIA compilation and online validation.
'''
(D/'Call_recipe.txt').write_text(call)
print('SCL reference files written',len(core),'chars core')
