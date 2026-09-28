"""One-time staging migration. Rename authored tags, never browser/user notes."""
from pathlib import Path
R=Path.cwd()
files=['compact_spec.py','compact_engine.py','compact_update.py','tests/compact_test.py','tests/compact_browser_test.py']
for name in files:
    p=R/name
    s=p.read_text()
    s=s.replace('Shift1','DayShift').replace('Shift2','NightShift')
    s=s.replace('Shift 1','Day shift').replace('Shift 2','Night shift')
    s=s.replace('shift 1','day shift').replace('shift 2','night shift')
    s=s.replace('2026-09-28-compact-lad-v8','2026-09-28-compact-day-night-v8')
    s=s.replace('machine-reporting-compact-14-v8-20260928','machine-reporting-compact-day-night-v8-20260928')
    s=s.replace("r['Shift'+str(want)+'Current']", "r[{1:'DayShiftCurrent',2:'NightShiftCurrent'}[want]]")
    s=s.replace('LastHour/LastDay/LastShift dates','LastHour, LastDay, LastDayShift and LastNightShift values')
    p.write_text(s)
p=R/'tests/compact_test.py';s=p.read_text()
needle="ok('Only fourteen flat report fields',len(REPORT)==14 and REPORT[-1]['offset']==52)"
add="""
ok('Day and night tags match the requested names',[(f['name'],f['offset'])for f in REPORT[8:12]]==[('DayShiftCurrent',32),('DayShiftPrevious',36),('NightShiftCurrent',40),('NightShiftPrevious',44)])
ok('No numbered-shift identifiers remain in the authored compact ladder',not any(word in json.dumps(SPEC) for word in ['Shift1','Shift2']))
"""
if 'Day and night tags match the requested names' not in s:s=s.replace(needle,needle+add)
p.write_text(s)
p=R/'tests/compact_browser_test.py';s=p.read_text()
needle="ok('New first tag and data type correct',report.locator('tbody tr').first.inner_text().startswith('CycleSeconds\\tReal'))"
add="""
 ok('Day/night declaration names are visible',all(name in report.inner_text()for name in ['DayShiftCurrent','DayShiftPrevious','NightShiftCurrent','NightShiftPrevious']) and 'Shift1Current' not in report.inner_text())
"""
if 'Day/night declaration names are visible' not in s:s=s.replace(needle,needle+add)
needle="ok('Kepware map matches new offsets','DB56,REAL4' in text and 'DB56,DINT52' in text and 'DB56,DINT156' not in text)"
add="""
 ok('Kepware uses the same four day/night names',all(name in text for name in ['DayShiftCurrent','DayShiftPrevious','NightShiftCurrent','NightShiftPrevious']) and 'Shift1Current' not in text)
"""
if 'Kepware uses the same four day/night names' not in s:s=s.replace(needle,needle+add)
p.write_text(s)
print('Compact day/night names updated. User notes, task IDs and memory layout are unchanged.')
