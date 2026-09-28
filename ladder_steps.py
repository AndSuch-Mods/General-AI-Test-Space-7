"""Build the manual, all-LAD MM6 route without modifying a PLC or archived SCL.
Keeps the existing dark checklist UI and user storage; retires SCL build check IDs.
"""
from pathlib import Path
from html import escape
import copy,json,re,itertools
from ladder_spec import BLOCKS
ROOT=Path(__file__).parent

def code(x):return '<code>'+escape(str(x))+'</code>'
def steps(*items):return '<ol>'+''.join('<li>'+i+'</li>'for i in items)+'</ol>'
def table(head,rows):return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+escape(x)+'</th>'for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>'for c in row)+'</tr>'for row in rows)+'</tbody></table></div>'
def panel(id,title,body):return '<details class="small manual-panel" id="'+id+'"><summary>'+escape(title)+'</summary><div class="manual-panel-body">'+body+'</div></details>'
def task(id,title,body,**kw):return dict(id=id,title=title,body=body,**kw)
def val(x):return 'TRUE' if x is True else 'FALSE' if x is False else str(x)
def paths(g):
 if g is True:return [[]]
 if isinstance(g,str):return [[('NO',g)]]
 if g[0]=='cmp':return [[('Compare '+g[2]+' (DInt)',val(g[1])+' | '+val(g[3]))]]
 if g[0]=='not':
  assert isinstance(g[1],str),g
  return [[('NC',g[1])]]
 if g[0]=='or':return list(itertools.chain.from_iterable(paths(x)for x in g[1:]))
 if g[0]=='and':
  result=[[]]
  for child in g[1:]:result=[a+b for a in result for b in paths(child)]
  return result
 raise ValueError(g)

def describe_action(a):
 op=a['op']
 if op=='COIL':return ['Normal coil ( )',code(a['out']),'Normal coil, not Set/Reset. It must write FALSE when the contact path is false.']
 if op in ('SET','RESET'):return [('Set coil (S)'if op=='SET'else 'Reset coil (R)'),code(a['out']),'Only this new reporting bit.']
 if op=='CALL':
  pinrows='; '.join(escape(k)+' = '+code(val(v))for k,v in a['inputs'].items())
  return [code(a['block']),('Multi-instance '+code(a['instance'])if a.get('instance')else 'FC call'),pinrows]
 if op in ('RD_LOC_T','RD_SYS_T'):return [code(op),'OUT = '+code(a['out']),'RET_VAL = '+code(a['ret'])+'; keep EN on the left rail.']
 if op=='TIME_TCK':return [code(op),'RET_VAL = '+code(a['out']),'No timer DB or PT preset. Reads the RUN-time counter.']
 pins='; '.join(escape(k)+' = '+code(val(v))for k,v in a['inputs'].items())+'; OUT'+('1'if op=='MOVE'else '')+' = '+code(a['out'])
 extra=''
 if op=='CALCULATE':extra='<br>Open its calculator icon. Expression: '+code(a['formula'])+'. Use only IN1, IN2, etc. in that expression, not tag names.'
 if a.get('eno'):extra+='<br>Connect <strong>ENO</strong> to a <strong>normal coil</strong> '+code(a['eno'])+'. It must go FALSE when the instruction does not execute successfully.'
 return [code(op),escape(a.get('type','Use the input/output data type')),pins+extra]

def networks(block,phase=None):
 ns=[n for n in block.networks if phase is None or n['phase']==phase];out=''
 for n in ns:
  routes=paths(n['gate']);branches=[]
  for route in routes:
   branch='--'.join(('[ '+label+' ]'if typ=='NO'else'[/ '+label+' ]'if typ=='NC'else'['+typ.replace(' (DInt)','')+': '+label+']')for typ,label in route)
   branches.append('|--'+(branch+'--'if branch else '')+(('( '+n['actions'][0]['out']+' )')if n['actions'][0]['op']=='COIL'else'[ output box(es) ]')+'--|')
  body='<pre class="lad-diagram">'+escape('\n'.join(branches))+'</pre>'
  if len(routes)>1:body+='<p><strong>'+str(len(routes))+' parallel contact paths.</strong> Each line above is an alternative route from the left rail. Join the routes BEFORE the shared output. Contacts within one line are in series.</p>'
  elif not routes[0]:body+='<p><strong>No enable contact.</strong> Connect this network directly to the left rail.</p>'
  else:body+='<p>Place the contacts/comparisons from left to right in series.</p>'
  contactrows=[(str(i+1),{'NO':'Normally open','NC':'Normally closed'}.get(typ,typ),code(label))for i,route in enumerate(routes)for typ,label in route]
  if contactrows:body+=table(['Path','Place','Tag / comparison operands'],contactrows)
  if len(n['actions'])>1:body+='<p>After the shared contact path, split into <strong>'+str(len(n['actions']))+' parallel output branches</strong>, one instruction per row below. Do not copy the upstream condition after an output has changed a tag.</p>'
  body+=table(['Instruction','Type / destination','Connect these pins'],[describe_action(a)for a in n['actions']])
  if n['note']:body+='<p class="muted">'+escape(n['note'])+'</p>'
  out+=panel('lad-'+block.name+'-'+str(n['number']),f"Network {n['number']:02d} · {n['title']}",body)
 return out

def declarations(rows,name):
 text='<p>Use the <strong>upper declaration grid</strong> of '+code(name)+'. Under each named section, click <strong>&lt;Add new&gt;</strong> and enter Name, Data type and the shown Start/default. Enter names without # or quotes. Leave a dash at its default. The # appears only when referencing a local variable in a rung.</p>'
 for section in ['Input','Output','InOut','Static','Temp']:
  subset=[r for r in rows if r['section']==section]
  for ix in range(0,len(subset),12):
   group=subset[ix:ix+12]
   body=table(['Name','Data type','Start/default','Note'],[(code(r['name']),code(r['type']),code(val(r['initial']))if r.get('initial')is not None else '—',escape(r.get('comment','')))for r in group])
   if any(r['type']=='CSI_PeriodCounter'for r in group):body+='<p>For these four Static rows select the existing LAD FB <strong>CSI_PeriodCounter</strong> as Data type. TIA adds its nested fields. These are four independent counter memories, not four more global DBs.</p>'
   text+=panel('lad-vars-'+name+'-'+section+'-'+str(ix),f'{section} · rows {ix+1}–{ix+len(group)}',body)
 return text

def newblock(name,kind,optimized=True):
 what='Function (FC)'if kind=='FC'else'Function block (FB)'if kind=='FB'else'Data block (DB)'
 return steps('Under <strong>this PLC → Program blocks</strong>, double-click <strong>Add new block</strong>. Choose <strong>'+what+'</strong>.',
  'Name = '+code(name)+'. Use <strong>Automatic</strong> numbering. '+('For Type choose <strong>Global DB</strong>.'if kind=='DB'else'Set <strong>Language = LAD</strong>, not SCL or FBD.')+' Select <strong>Add new and open → OK</strong>.',
  ('For this <em>new</em> block only: right-click it → <strong>Properties → Attributes → Optimized block access</strong> '+('ON'if optimized else'OFF')+'.'if kind!='FC'else'Leave the function Return type <strong>Void</strong>. Values use the InOut pins below; do not create a return-value tag.'),
  'Enter its declarations below. Then build its numbered ladder networks in order. Save and compile this block before continuing.'if kind!='DB'else'Enter the declaration rows below. A global DB stores data; do not add executable networks to it.')

EDITOR='''<p><strong>In TIA:</strong> open the new LAD block. Tags go in its upper declaration grid; rungs go in the networks below.</p>'''+steps(
 'To add a rung, right-click the last network heading → <strong>Insert network</strong>. Put the new network BELOW it and use the exact network title shown here.',
 'Use the toolbar’s <strong>Normally open contact</strong>, <strong>Normally closed contact</strong> and <strong>Coil</strong>. Click a symbol’s tag field and type the tag. Use a normal coil unless the panel specifically says <strong>(S)</strong> or <strong>(R)</strong>.',
 'For a box: open the <strong>Instructions</strong> pane on the right. Search its exact name, such as <strong>MOVE</strong>, <strong>ADD</strong>, <strong>CALCULATE</strong>, <strong>CONVERT</strong> or <strong>T_CONV</strong>, and drag it into the network. Select the stated data type in its dropdown, then fill the named pins.',
 'For comparisons use <strong>Basic instructions → Comparator operations</strong>, choose the shown operator and <strong>DInt</strong>, and enter the two operands shown on either side of the vertical bar.',
 'Use <strong>Open branch / Close branch</strong> for parallel paths. A network panel is a wiring recipe, NOT text to paste into TIA. Multiple boxes listed as parallel output branches share the condition before their split.',
 'For a reusable block call, drag the named block from Program blocks. A CSI_PeriodCounter call inside CSI_Reporting uses <strong>Multi-instance</strong>; select the exact existing Static instance named in the panel. Keep its EN on the rail and fill every Input. Its Output pins may remain unwired because later MOVE boxes read those instance members.')

REFS=[('LAD contacts, coils and blocks','https://docs.tia.siemens.cloud/r/en-us/v20/lad-s7-1200-s7-1500'),('CALCULATE instruction','https://docs.tia.siemens.cloud/r/en-us/v20/lad-s7-1200-s7-1500/math-functions-s7-1200-s7-1500/calculate-calculate-s7-1200-s7-1500'),('T_CONV time/date conversion','https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/date-and-time-of-day-s7-1200-s7-1500/t_conv-convert-times-and-extract-s7-1200-s7-1500'),('Read elapsed RUN milliseconds','https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/date-and-time-of-day-s7-1200-s7-1500/time-of-day-functions-s7-1200-s7-1500/time_tck-read-time-counter-s7-1500'),('DTL weekday fields','https://docs.tia.siemens.cloud/r/en-us/v20/data-types/date-and-time/dtl-s7-1200-s7-1500')]

def ladder_data(previous):
 d=copy.deepcopy(previous);d['build']='2026-09-28-lad-weekdays-v7'
 schema=d['schema']
 schema[0].update(initial='3',description='LAD weekday-reporting contract, version 3. Same 60-field byte layout.')
 for f in schema:
  if f['name']=='GapCompleted':f.update(description='Reserved zero: off-schedule runs are excluded in LAD revision 3.')
  if f['name']=='ClockUnassigned':f.update(description='Reserved zero: invalid-clock observations are not counted in LAD revision 3.')
  if f['name']=='Shift1Current':f.update(description='Mon–Fri 06:30–17:00; holds Friday until Monday 06:30.')
  if f['name']=='Shift2Current':f.update(description='Mon–Thu 17:00 through next 06:00; holds Thursday night until Monday 17:00.')
 mm6=next(g for g in d['groups']if g['id']=='MM6');old={t['id']:t for t in mm6['tasks']}
 setup_rows=[dict(section='Static',name=n,type='Bool',initial=v,comment='')for n,v in [('Enable',False),('WiringReviewed',False),('StartupPending',True)]]
 report_rows=[dict(section='Static',name=f['name'],type=f['type'],initial=f['initial'],comment='Byte '+str(f['offset'])+': '+f['description'])for f in schema]
 tasks=[copy.deepcopy(old['MM6-config']),task('MM6-lad-prepare','Create the CSI group and choose LAD',steps(
 'Save a separate working copy of the current MM6 project. Under <strong>Program blocks</strong>, check the names below before creating anything. Do not overwrite an existing CSI block or convert an already-running block in place.',
 'Right-click <strong>Program blocks → Add new group</strong>; name it <strong>CSI</strong> if available. Create only new blocks through <strong>Add new block</strong>; move them into this group.',
 'This route creates <strong>CSI_Report</strong> and <strong>CSI_Setup</strong> global DBs; <strong>CSI_Increment</strong> and <strong>CSI_AddElapsed</strong> FCs; <strong>CSI_PeriodCounter</strong> and <strong>CSI_Reporting</strong> FBs; and <strong>CSI_Reporting_DB</strong> as the main instance. All four executable blocks use <strong>LAD</strong>.',
 'If you already built the earlier SCL version, keep that copy. This ladder build has a different FB interface and direct OB1 call. Do not mix the two versions or run both. Previous checks/notes remain under Completed → Earlier checklist records.')+'<p class="note">Manual ladder specification, not a TIA-compiled or PLC-tested project. Keep the new Enable/WiringReviewed bits FALSE until compilation, input checks and load review are complete.</p>'+panel('lad-editor','How to place contacts, boxes and branches',EDITOR)),
 task('MM6-lad-report','Create CSI_Report and enter the reporting tags',newblock('CSI_Report','DB',False)+declarations(report_rows,'CSI_Report')+'<p>Use the exact order. SchemaVersion starts at <strong>3</strong>. PreviousCycleSeconds remains byte 40; CyclesToday remains byte 156. Do not create these as PLC tag-table entries.</p>',fields=[('reportDbLad','CSI_Report DB number for this LAD build','number')]),
 task('MM6-lad-setup','Create the three CSI_Setup bits',newblock('CSI_Setup','DB',False)+declarations(setup_rows,'CSI_Setup')),
 task('MM6-lad-helpers','Build the count and elapsed-time helper FCs','<p>Create these one at a time, both in <strong>LAD</strong>. They have no instance DB. CSI_AddElapsed is the stopwatch arithmetic; it does not time only the close output’s ON duration.</p>'+''.join(panel('lad-helper-'+n,n,newblock(n,'FC')+declarations(BLOCKS[n].rows,n)+networks(BLOCKS[n]))for n in ['CSI_Increment','CSI_AddElapsed'])),
 task('MM6-lad-period','Build CSI_PeriodCounter in LAD',newblock('CSI_PeriodCounter','FB')+declarations(BLOCKS['CSI_PeriodCounter'].rows,'CSI_PeriodCounter')+networks(BLOCKS['CSI_PeriodCounter'])),
 task('MM6-lad-main-vars','Create CSI_Reporting and enter its variables',newblock('CSI_Reporting','FB')+declarations(BLOCKS['CSI_Reporting'].rows,'CSI_Reporting')+'<p>Build its networks in the following network sections. The Static rows store history between scans; Temp rows are recalculated every execution. The first network of each step continues the SAME FB.</p>')]
 main=BLOCKS['CSI_Reporting'];phases=list(dict.fromkeys(n['phase']for n in main.networks))
 for i,phase in enumerate(phases):
  group=[n for n in main.networks if n['phase']==phase]
  text='<p>Open <strong>CSI_Reporting</strong>. Enter networks <strong>'+str(group[0]['number'])+'–'+str(group[-1]['number'])+'</strong> below its preceding networks. These are new reporting networks, not OB1 network numbers.</p>'
  if i==0:text+='<p>Clock instructions are native LAD boxes. No SCL helper or source import is required. For T_CONV and CONVERT use the exact input/output type selectors shown.</p>'
  if 'weekday'in phase:text+='<p><strong>Shift 1:</strong> Monday–Friday 06:30–17:00. <strong>Shift 2:</strong> Monday–Thursday 17:00 through the following 06:00. Outside these windows no production counts or held cycle times are updated. Shift counts hold until that same shift next starts.</p>'
  if 'Time a whole'in phase:text+='<p>Do not substitute a TON driven by the closing bit. TIME_TCK + the elapsed helper keep the stopwatch running through the second close pulse.</p>'
  if 'Hold and roll'in phase:text+='<p>Current shift count is NOT cleared at shift end. Friday’s day-shift result holds until Monday 06:30; Thursday-night’s result holds until Monday 17:00. Hour/day counters still roll by the clock; weekend production adds zero.</p>'
  tasks.append(task('MM6-lad-networks-'+str(i+1),f'CSI_Reporting {group[0]["number"]}–{group[-1]["number"]}: '+phase.lower(),text+networks(main,phase)))
 tasks.extend([
 task('MM6-lad-call','Create its instance DB and add one call in OB1',steps(
 'Finish and compile all four new LAD blocks. Under <strong>Add new block → Data block</strong>, name <strong>CSI_Reporting_DB</strong>; select <strong>CSI_Reporting</strong> as its Type, NOT Global DB. Let TIA populate its members.',
 'Open <strong>OB1</strong>. Keep all existing networks. Add one new network after the current final processing, outside any conditional jump. The analyzed MM6 program ends with RobotMain/FC900 at network 48.',
 'If OB1 is LAD/FBD, drag <strong>CSI_Reporting</strong> into that empty network and select the existing single-instance <strong>CSI_Reporting_DB</strong>. Leave EN directly on the rail, with no AUTO contact.',
 'If the existing OB1 is STL, leave its language unchanged. Insert the FB call from Program blocks and select CSI_Reporting_DB. Its call is <code>CALL "CSI_Reporting", "CSI_Reporting_DB"</code>; TIA inserts the five parameter rows. Fill them as below.',
 'Connect <strong>CloseCommand</strong> to <code>DB98.DBX112.7</code> and <strong>RobotPermit</strong> to <code>DB94.DBX29.6</code>. This call does not write either bit. Do not also call the earlier CSI_Run wrapper.')+table(['Input','Connect to'],[('ProductionEligible','Verified production-to-count condition, excluding setup/jog.'),('RobotDataValid','Verified current/valid robot/input communication condition.'),('AbortCycle','Verified cancellation of the measured cycle. Normal waiting is NOT an abort.')])+'<p class="note">The three conditions above still need verified tags. For OFFLINE compilation only, FALSE / FALSE / TRUE keeps the observer disabled. Do not use permanent TRUE shortcuts or enable it with unresolved inputs.</p>',fields=[('production','ProductionEligible source','text'),('valid','RobotDataValid source','text'),('abort','AbortCycle source','text')]),
 task('MM6-lad-startup','Set the startup flag without changing the machine sequence',steps(
 'Open the existing standard startup OB, normally <strong>OB100</strong>, and preserve its code.',
 'Add one final LAD network directly on the rail with a <strong>Set coil (S)</strong> addressed to <code>"CSI_Setup".StartupPending</code>. No contact is needed.',
 'If the existing startup OB is STL, keep that language: append <code>SET</code> followed by <code>S "CSI_Setup".StartupPending</code> in a new network. If there is no startup OB, add a standard <strong>Organization block → Startup</strong> in LAD with an unused number.',
 'The last network of CSI_Reporting resets this new bit after handling the first scan. No separate CSI_Startup FC is needed in this ladder route.')),
 task('MM6-lad-load','Compile and review only the intended additions',steps(
 'Compile the new blocks, then Program blocks → <strong>Compile → Software (only changes)</strong>. Resolve every error before loading. Save the laptop project.',
 'Review retention for the NEW CSI_Report and CSI_Reporting_DB: counts/keys/quality must remain together. Without retention, do not promise history across power loss. If changing retention requires STOP, defer it to an approved window instead of accepting STOP on a running machine.',
 'At the approved commissioning point, choose <strong>Download to device → Software (only changes)</strong>. Inspect Load preview: the new CSI blocks and intended OB additions only.',
 'Cancel unexpected STOP, hardware/F-program changes, deletions, or initialization of existing machine DBs. Keep Enable and WiringReviewed FALSE. A reporting purpose does not make an incorrect download harmless.')),
 task('MM6-lad-enable','Watch the new values, then enable only CSI_Setup',steps(
 'Create a separate reporting watch table. Add the symbolic tags below in Name, or drag members from CSI_Report/CSI_Setup. Click <strong>Monitor all</strong>. Require SchemaVersion=3, correct local date/time, ClockValid=1 and ConfigurationOK=1.',
 'Verify the three call inputs with the machine. With approval, modify ONLY <code>"CSI_Setup".WiringReviewed</code> and <code>"CSI_Setup".Enable</code> to TRUE. Use normal Modify selected values, not Force. Clear their Modify cells afterward.',
 'State 10 synchronizes through a robot low/high boundary; 20 times a known wait; 30 times the cycle. The first unknown cycle is deliberately skipped. Outside the weekday schedule State=0 and production is not counted.'),watch=['"CSI_Report".SchemaVersion','"CSI_Report".ClockValid','"CSI_Report".LocalDateYYYYMMDD','"CSI_Report".LocalTimeHHMMSS','"CSI_Report".ConfigurationOK','"CSI_Report".SignalsValid','"CSI_Report".ProductionMode','"CSI_Report".AbortActive','"CSI_Setup".WiringReviewed','"CSI_Setup".Enable']),
 task('MM6-lad-verify','Check five cycles, the extra pulse and shift hold',steps(
 'Compare five normal cycles with Chris or the operator. Each qualified completion updates PreviousCycleSeconds and increments TotalCompleted once. The secondary close pulse must not restart the stopwatch.',
 'Check live BetweenCycleSeconds while waiting and PreviousBetweenSeconds after the next start. Use BetweenActive and the held Valid flags. CPU STOP/power-off time is not measured by TIME_TCK.',
 'Test weekday boundaries in an isolated test copy or with observed real boundaries, not by changing a running production PLC clock. Confirm Friday day count holds until Monday 06:30 and Thursday-night count until Monday 17:00. Weekend/manual cycles must not update production totals or held cycle time.',
 'Check Partial flags and period keys. A first or interrupted shift can be partial. Archive the verified project and export this checklist’s progress.'),watch=['"CSI_Report".MonitorState','"CSI_Report".TotalCompleted','"CSI_Report".PreviousCycleSeconds','"CSI_Report".PreviousCycleValid','"CSI_Report".BetweenCycleSeconds','"CSI_Report".BetweenActive','"CSI_Report".PreviousBetweenSeconds','"CSI_Report".CyclesThisHour','"CSI_Report".CyclesToday','"CSI_Report".Shift1Current','"CSI_Report".Shift2Current'])])
 mm6['tasks']=tasks;mm6['hint']='Manual LAD networks · weekday shift schedule'
 # Keep other machines as read-only signal checks. Their clocks/CPU family are not assumed to match MM6.
 for g in d['groups']:
  if g['id']!='MM6':
   for t in g['tasks']:
    if t['id'].endswith('-qualify'):t['body']='<p>Record production-eligible, robot-data-valid and abort conditions. Use this machine’s confirmed event bits. Do not copy the MM6 block unchanged to a legacy WinLC target; its clock instruction support and interface must be checked separately.</p>'
 kg=next(g for g in d['kepware']if g['id']=='K-MM6')
 for t in kg['tasks']:
  t['id']=t['id'].replace('v2','lad')
  t['body']=t['body'].replace('value <strong>2</strong>','value <strong>3</strong>').replace('V2','LAD').replace('CSI2','CSI')
 kg['hint']='CSI_Report · expected schema 3'
 d['instructions']=[dict(id='lad-editor',title='Place a ladder contact, coil or instruction box',body=EDITOR),dict(id='lad-schedule',title='Shift times and what holds over the weekend',body='<p>Shift 1: Mon–Fri 06:30–17:00. Shift 2: Mon–Thu 17:00 to the next 06:00. Thursday’s night shift includes Friday before 06:00. No Friday-night shift.</p><p>Shift Current values hold after ending, then reset only at their own next scheduled start. Previous holds the last closed shift. No completed cycles outside the scheduled windows enter hour/day/shift/total production counts. Held cycle/waiting results are not replaced by weekend runs. The observer resynchronizes when scheduled production resumes.</p>')]
 return d

LAD_CSS='''\n/* LAD diagrams are wiring notes, not pasted SCL. */
.lad-diagram{white-space:pre;overflow:auto;max-width:100%;color:#9be0cb;background:#08151c;border-left:3px solid #4dd6b7;font-size:12px;line-height:1.8}
.manual-panel-body{min-width:0}.manual-panel>summary{font-variant-numeric:tabular-nums}
'''

def finalize(root):
 root=Path(root);p=root/'index.html';s=p.read_text();s=s.replace('27 Sep · CSI dark','28 Sep · LAD').replace('27 Sep · CSI</span>','28 Sep · LAD</span>')
 refs='<div class="references">'+''.join('<a target="_blank" rel="noopener noreferrer" href="'+u+'">'+escape(t)+'</a>'for t,u in REFS)+'</div>'
 s=re.sub(r'<div class="references">.*?</div>',lambda _:refs,s,count=1,flags=re.S)
 if 'LAD diagrams are wiring notes'not in s:s=s.replace('</style>',LAD_CSS+'</style>',1)
 # No import/download of stale SCL in the current ladder route.
 s=re.sub(r'const SOURCE=.*?;\n\x27use strict\x27;',"const SOURCE='';\n'use strict';",s,count=1,flags=re.S)
 s=s.replace("const y=anchor.getBoundingClientRect().top;if(value)","const anchorY=anchor.getBoundingClientRect().top;const y=(anchorY>=0&&anchorY<innerHeight-25)?anchorY:Math.max(16,Math.min(innerHeight-70,n.getBoundingClientRect().top));if(value)")
 p.write_text(s)
 p=root/'sw.js';s=p.read_text();s=re.sub(r"const CACHE='[^']+'", "const CACHE='machine-reporting-lad-v7-20260928'",s,1);
 m=re.search(r'const ASSETS=(\[.*?\]);',s)
 if m:
  assets=[x for x in json.loads(m.group(1))if not x.endswith('.scl')]
  if './ladder_spec.json'not in assets:assets.append('./ladder_spec.json')
  s=s[:m.start(1)]+json.dumps(assets)+s[m.end(1):]
 p.write_text(s)
 (root/'ladder_spec.json').write_text(json.dumps({n:dict(kind=b.kind,rows=b.rows,networks=b.networks)for n,b in BLOCKS.items()},indent=2))
 print('Built all-LAD route:',[(n,len(b.networks))for n,b in BLOCKS.items()])

def install(root=ROOT):
 root=Path(root);p=root/'build_html.py';s=p.read_text()
 if 'from ladder_steps import'not in s:
  s=s.replace('from checklist_data import build_data','from checklist_data import build_data\nfrom ladder_steps import ladder_data, finalize',1)
  s=s.replace('D=rename_data(manual_data(build_data()))','D=ladder_data(rename_data(manual_data(build_data())))',1)
  s+='\nfinalize(R)\n';p.write_text(s)
 p=root/'app.js';s=p.read_text();s=s.replace('reportDbV2','reportDbLad').replace('MM6_CSI_Report_DB','MM6_CSI_Report_LAD_DB');s=s.replace("const y=anchor.getBoundingClientRect().top;if(value)","const anchorY=anchor.getBoundingClientRect().top;const y=(anchorY>=0&&anchorY<innerHeight-25)?anchorY:Math.max(16,Math.min(innerHeight-70,n.getBoundingClientRect().top));if(value)");p.write_text(s)
 for name in ['README.md','AGENTS.md']:
  p=root/name;s=p.read_text()
  if '## Current LAD route'not in s:s+='''\n## Current LAD route\n\nThe active MM6 guide is now ladder (LAD) throughout: CSI_Increment and CSI_AddElapsed FCs, CSI_PeriodCounter and CSI_Reporting FBs, CSI_Reporting_DB, CSI_Report and CSI_Setup. No SCL import or body-pasting step is active. Do not mix this interface/direct OB1 call with the old CSI_Run wrapper. ladder_spec.py owns the ordered network records; ladder_steps.py renders their contacts, boxes, pins and declarations. ladder_engine.py runs those records for Python checks only, not Siemens compilation. Run tests/ladder_test.py and tests/ladder_browser_test.py.\n\nSchemaVersion is 3; the 60 field names/types/offsets stay in the same order. Counts now obey Mon–Fri day shifts and Mon–Thu night shifts; Thursday night continues into Friday. Shift current/previous counts hold through weekends until their respective next scheduled instance. Off-schedule cycles are excluded. Hour/day periods still roll by clock. The default new observer is disabled, and ProductionEligible/RobotDataValid/AbortCycle remain site-verified pins. Keep the three known configuration/event reads read-only. Preserve existing SCL and old tests as history, not as the active guide.\n\nPreserve the forced dark theme, all user notes and storage, and retired checklist history. New LAD task IDs do not inherit SCL completion; reportDbLad is not copied from an old reportDbV2 value. Do not re-add long background tutorials or retained screenshot artifacts.\n'''
  p.write_text(s)
 print('Installed LAD guide hook')

if __name__=='__main__':
 import sys
 if '--install'in sys.argv:install()
