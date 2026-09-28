"""Replace the large LAD route with the 12-field day/night checklist."""
from pathlib import Path
from html import escape
import copy,itertools,json,re
from compact_spec import BLOCK,SCHEMA,NAMES,BUILD
ROOT=Path(__file__).parent

def code(x):return '<code>'+escape(str(x))+'</code>'
def val(x):return 'TRUE' if x is True else 'FALSE' if x is False else str(x)
def steps(*xs):return '<ol>'+''.join('<li>'+x+'</li>'for x in xs)+'</ol>'
def table(head,rows):return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+h+'</th>'for h in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+x+'</td>'for x in row)+'</tr>'for row in rows)+'</tbody></table></div>'
def panel(id,title,body):return '<details class="small manual-panel" id="'+id+'"><summary>'+escape(title)+'</summary><div class="manual-panel-body">'+body+'</div></details>'
def task(id,title,body,**extra):return dict(id=id,title=title,body=body,**extra)
def routes(g):
 if g is True:return [[]]
 if isinstance(g,str):return [[('NO',g)]]
 if g[0]=='cmp':return [[('Compare',val(g[1])+' '+g[2]+' '+val(g[3]))]]
 if g[0]=='not':return [[('NC',g[1])]]
 if g[0]=='or':return list(itertools.chain.from_iterable(routes(x)for x in g[1:]))
 if g[0]=='and':
  out=[[]]
  for x in g[1:]:out=[a+b for a in out for b in routes(x)]
  return out
 raise ValueError(g)

def rowtable(rows):
 return table(['Section','Name','Data type','Start/default'],[(r['section'],code(r['name']),code(r['type']),code(val(r['initial']))if r.get('initial')is not None else 'Leave default')for r in rows])

def action(a):
 op=a['op']
 if op in ('COIL','SET','RESET'):
  return [dict(COIL='Normal coil ( )',SET='Set coil (S)',RESET='Reset coil (R)')[op],code(a['out']),'']
 if op in ('RD_LOC_T','TIME_TCK'):
  return [code(op),'Connect directly to the left rail',('OUT = '+code(a['out'])+'; RET_VAL = '+code(a['ret']))if a['ret']else 'RET_VAL = '+code(a['out'])]
 pins='; '.join(k+' = '+code(val(v))for k,v in a['inputs'].items())+'; '+('OUT1'if op=='MOVE'else'OUT')+' = '+code(a['out'])
 if 'formula'in a:pins+='<br>Calculator expression: '+code(a['formula'])
 if a.get('eno'):pins+='<br>Connect ENO to a <strong>normal coil</strong> '+code(a['eno'])+'.'
 return [code(op),escape(a.get('type','Match the displayed source/destination types')),pins]

def render_network(n,newrows):
 rr=routes(n['gate']);out=''
 if newrows:out+='<p><strong>First add these local variables</strong> in CSI_Reporting’s upper grid. Expand the named section; do not add them to CSI_Report.</p>'+rowtable(newrows)
 lines=[]
 for route in rr:
  contacts='--'.join('[ '+s+' ]'if t=='NO'else'[/ '+s+' ]'if t=='NC'else'[ '+s+' ]'for t,s in route)
  a=n['actions'][0];end=('( '+a['out']+' )')if a['op']=='COIL'else'[ '+a['op']+' ]'
  lines.append('|--'+(contacts+'--'if contacts else'')+end+'--|')
 out+='<pre class="lad-diagram">'+escape('\n'.join(lines))+'</pre>'
 if len(rr)>1:out+='<p>These are <strong>parallel contact paths</strong>. Join them before the shared output. Contacts on the same line are in series.</p>'
 elif not rr[0]:out+='<p><strong>No condition:</strong> start directly at the left rail.</p>'
 else:out+='<p>Place this contact/comparison path left to right. A slash means normally closed.</p>'
 if any(rr):out+=table(['Path','Place','Tag / operands'],[(str(i+1),{'NO':'Normally open','NC':'Normally closed','Compare':'Comparison box'}.get(t,t),code(s))for i,rrr in enumerate(rr)for t,s in rrr])
 if len(n['actions'])>1:out+='<p>After the common condition, use <strong>'+str(len(n['actions']))+' parallel output branches</strong>, in the order below. Each branch receives the same already-evaluated condition.</p>'
 out+=table(['Instruction','Type / destination','Pins'],[action(a)for a in n['actions']])
 if n.get('note'):out+='<p class="muted">'+escape(n['note'])+'</p>'
 return panel('compact-net-'+str(n['number']),f"Network {n['number']:02d} · {n['title']}",out)

EDITOR=steps('In <strong>CSI_Reporting</strong>, the upper grid is for local variables; the networks below are for ladder. Start with Network 1 and add new networks below it.',
 'For contacts/coils, use the LAD toolbar. Click each tag field and enter its name. Use a normal coil unless the recipe specifically shows <strong>(S)</strong> or <strong>(R)</strong>.',
 'For MOVE, ADD, SUB, DIV, CALCULATE, CONVERT, T_CONV, RD_LOC_T or TIME_TCK, use the right <strong>Instructions</strong> pane, find that exact instruction and drag it onto the rung. Select its stated type and fill its pins.',
 'Use comparator boxes for <code>==</code>, <code>!=</code>, <code>&lt;</code>, <code>&gt;</code>, <code>&lt;=</code> and <code>&gt;=</code>. Use DInt for the integer operands, except the ClockStatus comparisons use Int. Do not type the displayed comparison as a contact name.',
 'Use <strong>Open branch / Close branch</strong> for parallel paths. The rung drawing is a wiring recipe, not text to paste. Keep the order shown; save/compile after entering a complete section.')

REFS=[('Siemens: global DB declarations','https://docs.tia.siemens.cloud/r/en-us/v20/programming-data-blocks/basic-principles-for-programming-of-data-blocks'),('Siemens: date/time conversion types','https://docs.tia.siemens.cloud/r/simatic_s7_1200_manual_collection_enus_20/extended-instructions/date-time-of-day-and-clock-functions/date-and-time-of-day-instructions'),('Siemens: elapsed RUN counter','https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/date-and-time-of-day-s7-1200-s7-1500/time-of-day-functions-s7-1200-s7-1500/time_tck-read-time-counter-s7-1500'),('Siemens: local time','https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/date-and-time-of-day-s7-1200-s7-1500/time-of-day-functions-s7-1200-s7-1500/rd_loc_t-read-local-time-s7-1200-s7-1500'),('PTC: Siemens DB addresses','https://support.ptc.com/help/kepware/drivers/en/kepware/drivers/SIEMENSTCPIPETHERNET/Standard_S7_300_400_Item_Syntax.html')]

def compact_data(previous):
 d=copy.deepcopy(previous);d.update(build=BUILD,schema=copy.deepcopy(SCHEMA),display_fields=NAMES[:])
 mm6=next(g for g in d['groups']if g['id']=='MM6');watch=next(t for t in mm6['tasks']if t['id']=='MM6-config')
 report=table(['Tag','Type','Start','Byte'],[(code(f['name']),code(f['type']),code(f['initial']),str(f['offset']))for f in SCHEMA])
 setup=[dict(section='Static',name=n,type='Bool',initial=v)for n,v in [('Enable',False),('WiringReviewed',False),('StartupPending',True)]]
 tasks=[watch,
 task('MM6-compact-report','Enter the 12 CSI_Report tags',steps(
 'You already opened <strong>CSI_Report [DB56]</strong> in your screenshot. Use that new empty DB if it is still the one you are editing. Do not alter an already-downloaded 60-field DB in place.',
 'Click the triangle beside <strong>Static</strong>. Click <strong>&lt;Add new&gt;</strong> underneath it. <strong>Static is a heading, not tag 1.</strong> The far-left row number does not determine a byte address.',
 'Type <strong>PreviousCycleSeconds</strong> under Name, <strong>Real</strong> under Data type, and <strong>0.0</strong> under Start value. Enter the other rows below in this exact order. Do not create PLC tag-table entries.',
 'For this new DB: <strong>Properties → Attributes → Optimized block access OFF</strong>. Press Ctrl+S, then compile it. Check the generated Offset column; the first tag should be byte 0.')+report+'<p class="note">This is a new 48-byte layout. The old 60-tag ladder and Kepware addresses do not match it. DayShiftCurrent replaces Shift1Current; NightShiftCurrent replaces Shift2Current. Use the corresponding Previous names too.</p>',fields=[('reportDbCompact','Confirmed CSI_Report DB number for these 12 tags','number')]),
 task('MM6-compact-setup','Create CSI_Setup with three bits',steps(
 'Under this PLC’s <strong>Program blocks → Add new block</strong>, choose <strong>Data block → Global DB</strong>. Name it <strong>CSI_Setup</strong>, using automatic numbering. Do not overwrite an occupied name.',
 'Expand Static and add the three rows below. Leave Enable and WiringReviewed FALSE. StartupPending starts TRUE.',
 'Save the new DB. Put it in your CSI or CSI_Adders group; either folder name is fine. These are new reporting controls, not machine controls.')+rowtable(setup)),
 task('MM6-compact-fb','Create one ladder FB: CSI_Reporting',steps(
 '<strong>Program blocks → Add new block → Function block (FB)</strong>. Name = <strong>CSI_Reporting</strong>, Language = <strong>LAD</strong>, Number = Automatic, Add new and open → OK. Leave this new FB optimized.',
 'In the upper grid, expand <strong>Input</strong> and enter the five BOOL rows below. Do not add them under Static.',
 'Start with the clock section next. Each numbered network tells you which extra local variables to add just before you use them. There is no 60-row declaration list and no helper FC to build.',
 'Do not reuse a partially built old CSI_Reporting with another interface. Keep that project as a backup, and use this compact route in the new working copy.')+rowtable([r for r in BLOCK.rows if r['section']=='Input'])+panel('compact-editor','How to place a ladder instruction',EDITOR))]
 seen={r['name']for r in BLOCK.rows if r['section']=='Input'}
 phases=list(dict.fromkeys(n['phase']for n in BLOCK.networks));decl={r['name']:r for r in BLOCK.rows}
 for i,phase in enumerate(phases):
  ns=[n for n in BLOCK.networks if n['phase']==phase];body='<p>In the <strong>same CSI_Reporting FB</strong>, build networks '+str(ns[0]['number'])+'–'+str(ns[-1]['number'])+' in order. These are not OB1 network numbers.</p>'
  if i==0:body+='<p>Day shift: <strong>Mon–Fri 06:30–17:00</strong>. Night shift: <strong>Mon–Thu 17:00–06:00 next day</strong>. Weekday values are 1 Sunday through 7 Saturday. Off-schedule cycles are excluded.</p>'
  if i==1:body+='<p>State <strong>0</strong> waits for a known robot return; <strong>1</strong> times the wait; <strong>2</strong> times a cycle. ADD accumulates elapsed milliseconds. MOVE holds the result. Another close pulse in state 2 does not start a new cycle.</p>'
  if i==2:body+='<p><strong>One completion updates all applicable counts.</strong> Hour/day counts roll by the clock. Each shift stores its old count and clears Current only when that same scheduled shift next begins. Friday day shift holds until Monday 06:30; Thursday night holds until Monday 17:00.</p>'
  for n in ns:
   refs=set(re.findall(r'#([A-Za-z_]\w*)',json.dumps(n)));new=[r for r in BLOCK.rows if r['name']in refs and r['name']not in seen];seen|={r['name']for r in new};body+=render_network(n,new)
  body+='<p>Save this section. Compile after its variables and all shown networks are entered; resolve errors before proceeding. Nothing here downloads to the PLC.</p>'
  tasks.append(task('MM6-compact-section-'+str(i+1),phase,body))
 assert seen==set(decl),(seen,set(decl))
 tasks += [task('MM6-compact-call','Add the FB call after OB1’s existing logic',steps(
 'Compile CSI_Reporting. Open <strong>OB1</strong>, go to the end, and insert a new network <strong>after</strong> the existing processing. Keep the existing FC900 / RobotMain call; the analyzed project had it in network 48.',
 'In a LAD/FBD OB1, drag <strong>CSI_Reporting</strong> into the new network. In the call dialog choose <strong>Single instance</strong>, name the new instance <strong>CSI_Reporting_DB</strong>, and let TIA choose an unused DB number. TIA fills its variables from the FB; do not type those again.',
 'If OB1 is STL, keep its language. Create <strong>CSI_Reporting_DB</strong> with Add new block → Data block → Type = CSI_Reporting. Insert the FB CALL with that instance through the editor. Do not convert the existing OB1 or paste SCL.',
 'Connect CloseCommand = <strong>%DB98.DBX112.7</strong> and RobotPermit = <strong>%DB94.DBX29.6</strong>. Fill the other three pins from verified existing conditions below. Keep this call unconditional and only once per scan.')+table(['Input','Meaning'],[('ProductionEligible','Production cycles to count; exclude setup/jog.'),('RobotDataValid','The input data being observed are current and valid.'),('AbortCycle','The observed cycle has been canceled. Normal waiting is not an abort.')])+'<p class="note">Those three mappings are still unverified. Leave reporting disabled until they are resolved. Offline compile-only placeholders: ProductionEligible FALSE; RobotDataValid FALSE; AbortCycle TRUE. Do not use the old CSI_Run or a second observer call.</p>',fields=[('production','ProductionEligible source','text'),('valid','RobotDataValid source','text'),('abort','AbortCycle source','text')]),
 task('MM6-compact-startup','Add the startup reset and review retention',steps(
 'Open the existing standard <strong>Startup OB</strong>, normally OB100. Append a network without replacing its existing logic. Put an unconditional <strong>Set coil (S)</strong> on <code>"CSI_Setup".StartupPending</code>. In an existing STL network the equivalent is <code>SET</code> followed by <code>S "CSI_Setup".StartupPending</code>.',
 'If there is no startup OB, use <strong>Add new block → Organization block → Startup</strong> and choose an available standard startup OB for this CPU. Do not create or modify an F-block.',
 'For persistence, retain the new report counts/held values and the FB Static period keys <strong>HourSaved, DaySaved, DayShiftSaved, NightShiftSaved</strong> together. Keep the startup flag in place so an unfinished timer cannot span a restart.',
 'For the first RUN load, do not change existing retentivity or accept an unexpected STOP. Nonretentive commissioning is acceptable, but counts will not be promised to survive restart.') ),
 task('MM6-compact-load','Compile and review the changes-only load',steps(
 'Compile all the new blocks and intended OB edits. Double-click any error in the Compile pane and fix it. Press Ctrl+S.',
 'During the site-approved change window, choose <strong>Download to device → Software (only changes)</strong>. Read Load preview. Check the target CPU and every affected block.',
 'Expect only the new reporting blocks and intended OB edits. Cancel unexpected STOP, hardware/F-program changes, deletion or initialization of an existing machine DB. Keep the new Enable and WiringReviewed FALSE until the final checks.')+'<p class="note">The ladder recipe has not been compiled in TIA or run on the PLC. It only reads existing machine bits, but compile/load/scan effects still require review.</p>'),
 task('MM6-compact-verify','Enable reporting and check a complete cycle',steps(
 'In a new watch table add <code>"CSI_Reporting_DB".State</code>, the setup bits and the 12 report fields. Monitor the FB online to check ClockOK, Allowed and the five input pins.',
 'Confirm local time, live configuration and the three reviewed machine conditions. With site approval, modify only <code>"CSI_Setup".WiringReviewed</code> and <code>"CSI_Setup".Enable</code> to TRUE. Use normal modification, not Force; clear the Modify cells afterward.',
 'The first unknown cycle is skipped to synchronize. Observe at least five normal cycles. One completion should store approximately the observed cycle duration and add exactly one to TotalCompleted. Extra closing pulses must not count.',
 'Create a real wait and check BetweenCycleSeconds, then check PreviousBetweenSeconds at the next start. State 1 means a known live wait; zero on the live field alone does not prove the machine is running.',
 'Confirm the weekday holds and hour/day boundaries in an isolated test or at the real boundary. Do not change a running production PLC clock for testing. Archive the finished project.')+'<p class="muted">This simpler DB has no quality/history fields. The first observed hour/day/shift may be partial. After an outage, PreviousHour/PreviousDay mean the last observed period, not guaranteed consecutive history. CPU STOP/power-off time is not timed. All counters stop at their DINT limit. Held durations remain unchanged on a skipped or aborted cycle.</p>')]
 mm6.update(tasks=tasks,hint='12 reporting tags · one LAD function block')
 kp=next(g for g in d['kepware']if g['id']=='K-MM6');kp['hint']='Read the new 48-byte CSI_Report'
 kp['tasks']=[task('K-MM6-compact-device','Select the existing MM6 device','<p>Back up the Kepware project. Select the existing MM6 device under the approved <strong>Siemens TCP/IP Ethernet</strong> channel. Use the map here only with that driver; a symbolic/OPC UA connection uses its own addressing. Do not change PLC protection to make a connection work.</p>'),
 task('K-MM6-compact-tags','Create the 12 read-only tags',steps(
 'Under MM6, create or select the <strong>Production</strong> tag group. Choose <strong>New Tag</strong>. Enter its name and address from the table below, Float for REAL seconds or Long for DINT counts, Client access Read Only, and an initial 1000-ms scan rate.',
 'Start with <strong>PreviousCycleSeconds</strong>. Require Good quality in OPC Quick Client and compare its value with TIA. Then add the remaining eleven rows.',
 '<strong>Do not use the old 60-tag address table.</strong> This layout starts PreviousCycleSeconds at byte 0 and ends TotalCompleted at byte 44. Confirm the actual DB number and offsets before using any address.')+'<p>DayShiftCurrent / DayShiftPrevious are day shift. NightShiftCurrent / NightShiftPrevious are night shift. There is no SchemaVersion or Heartbeat field in this 12-tag DB.</p>',map=True),
 task('K-MM6-compact-save','Verify the displayed values and save','<p>Compare the readings with TIA, including day/night Current and Previous fields. Use bad-quality/stale indications when the PLC is unavailable. Zero live waiting does not mean uptime; the compact map has no BetweenActive flag. Save the Kepware project. The CSV is an address reference, not a promised import format.</p>')]
 d['instructions']=[dict(id='compact-static',title='Static is the heading; add tags underneath it',body='<p>In a global DB, expand <strong>Static</strong> and type each tag on its own <strong>&lt;Add new&gt;</strong> row. The heading occupying screen row 1 is normal. Your first actual tag goes at <strong>byte 0</strong>; screen row numbers and byte offsets are different.</p><p>In CSI_Reporting, local variables go in the section named by that network’s small table. Do not enter local # names in the global report DB.</p>'),dict(id='compact-ladder',title='Placing the ladder instructions',body=EDITOR)]
 return d

def install(root=None):
 root=Path(root or ROOT)
 p=root/'build_html.py';s=p.read_text()
 if 'from compact_steps import' not in s:
  s=s.replace('from ladder_steps import ladder_data, finalize','from ladder_steps import ladder_data, finalize\nfrom compact_steps import compact_data, finalize_compact')
  s=s.replace('D=ladder_data(rename_data(manual_data(build_data())))','D=compact_data(ladder_data(rename_data(manual_data(build_data()))))')
  s+='\nfinalize_compact(R)\n'
 p.write_text(s)
 p=root/'app.js';s=p.read_text().replace('reportDbLad','reportDbCompact').replace('MM6_CSI_Report_LAD_DB','MM6_CSI_Report_12tags_DB')
 start="const quality=folder('quality-map','Quality, status and period identifiers','small');"
 if start in s:
  a=s.index(start);b=s.index('const button=',a);s=s[:a]+s[b:]
 p.write_text(s)
 for name in ['README.md','AGENTS.md']:
  p=root/name
  if p.exists():
   text=p.read_text()
   if '## Compact 12-field route' not in text:text+='\n## Compact 12-field route\n\nCurrent instructions are generated by compact_spec.py and compact_steps.py. CSI_Report has exactly 12 fields / 48 bytes. DayShiftCurrent/Previous and NightShiftCurrent/Previous replace numbered shift names. Do not use the old 60-field addresses. One new LAD CSI_Reporting FB replaces the helper-heavy route. Add local variables at their first-use network instead of a large initial declaration list. Preserve the old reference files and user notes as history only. reportDbCompact is a new user-confirmed DB field; never auto-copy an old DB number or old completed build checks. Current source has NOT been TIA-compiled or PLC-tested. Use tests/compact_test.py and tests/compact_browser_test.py. Publish only current recipes, not the superseded SCL. Keep forced dark mode and local-only state.\n'
   p.write_text(text)
 print('Compact builder installed; old source retained as history.')

def finalize_compact(root):
 root=Path(root)
 p=root/'index.html';s=p.read_text();s=re.sub(r'<span class="revision">.*?</span>','<span class="revision">28 Sep · 12 tags</span>',s,count=1)
 # Superseded source is never a second executable download inside this page.
 a=s.find('const SOURCE=')
 if a>=0:
  decoder=json.JSONDecoder();pos=a+len('const SOURCE=');n=2 if s[pos:pos+2]=="''" else decoder.raw_decode(s[pos:])[1];s=s[:pos]+'""'+s[pos+n:]
 s=s.replace('Machine mappings and V2 installation details come from the supplied project analyses and MM6 V2 source package.','MM6 signal candidates come from the supplied project analysis and observed watch tables. Compact LAD remains uncompiled in TIA.')
 s=s.replace('</div><p>Installed V15/V16 labels',''.join('<a href="'+url+'" target="_blank" rel="noopener noreferrer">'+title+'</a>'for title,url in REFS)+'</div><p>Installed V15/V16 labels')
 p.write_text(s)
 (root/'compact_reference.json').write_text(json.dumps(dict(build=BUILD,schema=SCHEMA,blocks={BLOCK.name:dict(kind=BLOCK.kind,rows=BLOCK.rows,networks=BLOCK.networks)}),indent=2))
 (root/'ladder_spec.json').write_bytes((root/'compact_reference.json').read_bytes())
 p=root/'sw.js';s=p.read_text();s=re.sub(r"const CACHE='[^']+';","const CACHE='machine-reporting-compact-v8-20260928';",s);s=s.replace('./ladder_spec.json','./compact_reference.json');p.write_text(s)
 print('Compact guide finalized:',len(SCHEMA),'fields;',len(BLOCK.networks),'LAD networks')
if __name__=='__main__':
 import sys
 if '--install'in sys.argv:install()
