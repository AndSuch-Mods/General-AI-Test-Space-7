"""Validate manual declarations/body parity. This does not compile Siemens SCL."""
from pathlib import Path
import sys,re,json,hashlib
from html.parser import HTMLParser
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from manual_steps import parse_source,body_sections,declaration_tables,body_panels,SOURCE_HASH
R=Path(__file__).resolve().parents[1]
results=[]
def ok(label,value):
    assert value,label
    results.append(label)
class CodeParser(HTMLParser):
    def __init__(self):super().__init__();self.active=False;self.values=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='pre' and 'data-block' in a:self.active=True;self.values.append('')
    def handle_endtag(self,tag):
        if tag=='pre':self.active=False
    def handle_data(self,data):
        if self.active:self.values[-1]+=data
blocks=parse_source()
ok('Exactly ten blocks represented',len(blocks)==10)
ok('Main FB is CSI_Reporting; instance selects it',blocks['CSI_Reporting']['kind']=='FUNCTION_BLOCK' and blocks['CSI2_MM6_Instance']['instance']=='CSI_Reporting')
ok('Report has sixty four-byte fields in source order',len(blocks['CSI2_Report']['rows'])==60 and all(r['type'] in ('DInt','Real') for r in blocks['CSI2_Report']['rows']))
for i,r in enumerate(blocks['CSI2_Report']['rows']):assert r['comment'].startswith('byte '+str(4*i)+':'),r
ok('Expected report offsets are unchanged',True)
ok('Enable remains false and StartupPending starts true',{r['name']:r['initial'] for r in blocks['CSI2_Setup']['rows']}=={'Enable':'FALSE','WiringReviewed':'FALSE','StartupPending':'TRUE'})
for name,b in blocks.items():
    if b['kind']=='DATA_BLOCK':continue
    pieces=body_sections(b)
    ok(name+': all body sections reconstruct exactly',''.join(p['text'] for p in pieces)==b['body'])
    p=CodeParser();p.feed(body_panels(b))
    ok(name+': HTML preserves every executable character',''.join(p.values)==b['body'])
    allowed={r['name'].lower() for r in b['rows']}|{name.lower()}
    locals_={m.lower() for m in re.findall(r'#([A-Za-z_]\w*)',b['body'])}
    ok(name+': every local identifier declared',locals_<=allowed)
    for chunk in pieces:
        s=re.sub(r'//[^\n]*','',chunk['text']);s=re.sub(r'"[^"\n]*"','',s)
        tokens=re.findall(r'\b(?:IF|END_IF|CASE|END_CASE|FOR|END_FOR)\b',s)
        stack=[]
        for t in tokens:
            if t in ('IF','CASE','FOR'):stack.append(t)
            else:
                assert stack and stack.pop()==t[4:],(name,t)
        assert not stack,(name,stack)
        assert not re.search(r'^\s*(FUNCTION_BLOCK|FUNCTION |VAR_INPUT|VAR_TEMP|END_FUNCTION)',chunk['text'],re.M)
    ok(name+': each section has balanced control statements',True)
main=blocks['CSI_Reporting'];sections={r['name']:r['section'] for r in main['rows']}
ok('Edge history and state live in Static, not Temp',all(sections[n]=='Static' for n in ['State','PrevClose','PrevPermit','CycleSec','GapSec']))
ok('Four separate period-counter multi-instances declared',all(any(r['name']==n and r['section']=='Static' and r['type']=='"CSI2_PeriodCounter"' for r in main['rows']) for n in ['HourCounter','DayCounter','Shift1Counter','Shift2Counter']))
ok('Main FB has eight numbered body sections',len(body_sections(main))==8)
ok('Original supplied source untouched',hashlib.sha256((R/'downloads/MM6_Reporting_V2.scl').read_bytes()).hexdigest()==SOURCE_HASH)
if (R/'content.json').exists():
    d=json.loads((R/'content.json').read_text());m=next(g for g in d['groups'] if g['id']=='MM6');ids=[t['id'] for t in m['tasks']]
    ok('Old import task is no longer in current MM6 checklist','MM6-v2-source' not in ids and 'MM6-manual-main' in ids)
    ok('No source-import action in MM6 manual steps',all('data-source' not in t['body'] and 'Generate blocks from source' not in t['body'] for t in m['tasks']))
    ok('Creation comes before calling the new code',ids.index('MM6-manual-main')<ids.index('MM6-manual-instance')<ids.index('MM6-manual-run')<ids.index('MM6-manual-call'))
report=dict(passed=len(results),checks=results,scope='Manual interface extraction, exact body reconstruction and source checks only. No Siemens compilation or PLC execution.',plc_tested=False)
(R/'tests/manual_structure_results.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
