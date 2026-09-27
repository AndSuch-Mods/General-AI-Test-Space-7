"""Manual Siemens editor route. Derives interface rows and body sections from V2.

No source import, no PLC writes, no change to the supplied V2 source file.
The manual main FB is CSI_Reporting; its instance remains CSI2_MM6_Instance.
"""
from pathlib import Path
from html import escape
import copy, hashlib, json, re

ROOT = Path(__file__).parent
SOURCE_HASH = 'eb709811803d67a10be673682d831cb80bf25cf814d40c612f753730e17a8b49'
ALIASES = {'CSI2_CycleMonitor': 'CSI_Reporting'}
LABELS = {'VAR_INPUT':'Input', 'VAR_OUTPUT':'Output', 'VAR_IN_OUT':'InOut', 'VAR':'Static', 'VAR_TEMP':'Temp'}


def steps(*items):
    return '<ol>'+''.join('<li>'+x+'</li>' for x in items)+'</ol>'


def panel(id, title, content):
    return '<details class="small manual-panel" id="'+escape(id)+'"><summary>'+title+'</summary><div class="manual-panel-body">'+content+'</div></details>'


def table(head, rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+escape(h)+'</th>' for h in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def code(text):
    return '<code>'+escape(text)+'</code>'


def parse_source():
    raw=(ROOT/'downloads/MM6_Reporting_V2.scl').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==SOURCE_HASH, 'V2 source changed: review the manual generator first.'
    s=raw.decode('utf-8-sig')
    starts=list(re.finditer(r'^(DATA_BLOCK|FUNCTION_BLOCK|FUNCTION) "([^"]+)"([^\n]*)\n',s,re.M))
    result={}
    for ix,match in enumerate(starts):
        typ,original,tail=match.groups()
        name=ALIASES.get(original, original)
        full=s[match.start():starts[ix+1].start() if ix+1<len(starts) else len(s)].strip()
        header,body=full.split('\nBEGIN\n',1)
        body=re.sub(r'(?:^|\n)END_(?:DATA_BLOCK|FUNCTION_BLOCK|FUNCTION)\s*$','',body)
        rows=[]
        for sec in re.finditer(r'^(VAR_INPUT|VAR_OUTPUT|VAR_IN_OUT|VAR_TEMP|VAR)\n(.*?)^END_VAR$',header,re.M|re.S):
            section=LABELS[sec[1]]
            for line in sec[2].splitlines():
                if not line.strip():continue
                item=re.fullmatch(r'\s*(\w+)\s*:\s*([^;:=]+?)(?:\s*:=\s*([^;]+))?;\s*(?://\s*(.*))?',line)
                assert item, (original,line)
                n,dtype,initial,comment=item.groups()
                rows.append(dict(section=section,name=n,type=dtype.strip(),initial=initial.strip() if initial else '',comment=comment or ''))
        instance=None
        if typ=='DATA_BLOCK' and not rows:
            inst=re.search(r'^"([^"]+)"$',header,re.M)
            assert inst, original
            instance=ALIASES.get(inst[1],inst[1])
        result[name]=dict(name=name,original=original,kind=typ,rows=rows,body=body,
            return_type=tail.split(':',1)[1].strip() if ':' in tail else None,
            optimized="S7_Optimized_Access := 'TRUE'" in header,instance=instance)
    assert len(result)==10
    return result


def create_block(b):
    typ={'FUNCTION':'Function (FC)','FUNCTION_BLOCK':'Function block (FB)','DATA_BLOCK':'Data block (DB)'}[b['kind']]
    instructions=[
        'In <strong>TIA’s left Project tree → this MM6 PLC → Program blocks</strong>, double-click <strong>Add new block</strong>. Choose <strong>'+typ+'</strong>.',
        'Enter Name = '+code(b['name'])+'. Leave block-number assignment on <strong>Automatic</strong>; record the number TIA assigns. Do not replace an occupied block.'
    ]
    if b['kind']=='DATA_BLOCK':
        instructions.append('For <strong>Type</strong>, choose <strong>Global DB</strong>. Select <strong>Add new and open</strong>, then <strong>OK</strong>.')
    else:
        instructions.append('Select <strong>Language = SCL</strong>, enable <strong>Add new and open</strong>, then <strong>OK</strong>. This only creates the new block; it does not change OB1’s language.')
    access='checked' if b['optimized'] else 'unchecked'
    if b['kind'] in ('DATA_BLOCK','FUNCTION_BLOCK'):
        instructions.append('Right-click this <em>new</em> block in the tree → <strong>Properties → Attributes</strong>. Set <strong>Optimized block access</strong> '+access+'. Confirm with OK and reopen it. Leave existing machine DBs unchanged.')
    if b['kind']=='FUNCTION' and b['return_type']!='Void':
        instructions.append('In the upper interface grid, expand <strong>Return</strong>. Change the existing return row’s <strong>Data type</strong> to '+code(b['return_type'])+'. Do not add a second Output named RET_VAL. TIA may display the return as the function name or Ret_Val.')
    elif b['kind']=='FUNCTION':
        instructions.append('Leave the function’s <strong>Return</strong> type as '+code('Void')+'; it does not return a value through its name.')
    return steps(*instructions)


def declaration_tables(b):
    intro='<p><strong>Enter these in the upper declaration grid, not the code area below.</strong> Expand the named section and click its first '+code('<Add new>')+' Name cell. Enter Name, Data type, and the shown Start/Default value. Leave a dash at the TIA default. Type names without '+code('#')+', quotation marks, or semicolons.</p>'
    out=[]
    for section in ['Input','Output','InOut','Static','Temp']:
        rows=[r for r in b['rows'] if r['section']==section]
        if not rows:continue
        groups=[rows[i:i+12] for i in range(0,len(rows),12)]
        for ix,group in enumerate(groups):
            name=section if len(groups)==1 else section+' · rows '+str(ix*12+1)+'–'+str(ix*12+len(group))
            contents=table(['Name','Data type','Start / default','Comment'],[
                (code(r['name']),code(r['type']),code(r['initial']) if r['initial'] else '—',escape(r['comment'])) for r in group])
            if any(r['type']=='"CSI2_PeriodCounter"' for r in group):
                contents+='<p>The four counter rows belong under <strong>Static</strong>. For Data type, select the existing '+code('CSI2_PeriodCounter')+' FB, not DInt and not its DB. Each row gives that counter separate memory inside this FB. Let TIA create the nested members; do not enter them again.</p>'
            if section=='Temp':contents+='<p>Temp rows have no retained/start value to enter. They are working values for this execution of the block.</p>'
            out.append(panel('manual-'+b['name']+'-'+section+'-'+str(ix),name+' · '+str(len(group))+' rows',contents))
    return intro+''.join(out)


# Split only at top-level boundaries: each shown piece is a complete SCL statement sequence.
CUTS={
 'CSI_Reporting':[
  ('1. Startup, elapsed ticks and rising edges','', 'The # names refer to this FB’s interface rows. PrevClose and PrevPermit remember the previous scan; closeRise and permitRise last only this scan.'),
  ('2. Discard an aborted or invalid observation','    // Losing trustworthy', 'This resets only the new observer’s unfinished timing. It does not reset the machine or erase held reporting history.'),
  ('3. Synchronize, time the cycle and save the completed duration','    IF #qualified AND NOT #AbortCycle THEN', 'State 10 finds a known robot-return boundary. State 20 times the wait. State 30 times the whole cycle and ignores another close pulse. := copies a value, like MOVE; PreviousCycleSeconds is copied before the live timer is cleared.'),
  ('4. Read date fields and choose calendar inputs','    #collectionOK :=', 'Production quality is kept separate from the clock. LocalStamp supplies the local date/time; UtcStamp identifies repeated daylight-saving clock hours.'),
  ('5. Detect clock changes and select the shift','    #continuity :=', '390 means 06:30; 1020 means 17:00; 360 means 06:00. Midnight does not restart the overnight shift. Do not alter these numbers while entering the code.'),
  ('6. Update hour, day and both shift counters','    // Four independent buckets.', 'All four instances receive the same one-scan complete bit. Each instance stores its previous period before adding a boundary completion to the new period.'),
  ('7. Copy results to the Kepware reporting DB','    // Publish simple flat fields.', 'These are MOVE-style assignments to the new CSI2_Report fields. Period identities and Partial flags stay paired with the counts.'),
  ('8. Remember the inputs for the next scan','    #PrevClose := #CloseCommand;', 'These two assignments must remain last, after using the old values for edge detection.')
 ],
 'CSI2_PeriodCounter':[
  ('1. Validate the period and close its previous count','', 'This code is reused for the hour, day, shift 1 and shift 2. Each call will have its own stored state.'),
  ('2. Start the new period and add a completed cycle','    IF #WindowActive THEN', 'PreviousCount receives the old CurrentCount first. The new period starts at zero, then CountPulse adds one. A TRUE held robot signal is never used as CountPulse.')
 ]
}


def body_sections(b):
    body=b['body']
    spec=CUTS.get(b['name'],[('Enter the code','',{
        'CSI2_Increment':'This is the count ADD: return Value + 1 without allowing a signed count to wrap negative.',
        'CSI2_AddElapsed':'Add the scan’s elapsed milliseconds. Carry whole seconds into Seconds and keep the remaining milliseconds in Millis.',
        'CSI2_DayNumber':'Convert a valid calendar date into a comparable day number; -1 means the date is invalid.',
        'CSI2_MM6_Run':'Read the clocks and the known MM6 bits, then run the new reporting FB through its instance DB. It reads the original machine addresses; it does not write them.',
        'CSI2_MM6_Startup':'Set the new startup flag. The cyclic call consumes and clears it after initializing its own observer.'
    }.get(b['name'],''))])
    starts=[0]
    for title,mark,explanation in spec[1:]:
        # PrevClose also occurs within startup. Choose the final top-level assignment.
        ix=body.rfind('\n'+mark) if mark=='    #PrevClose := #CloseCommand;' else body.find('\n'+mark)
        assert ix>=0,(b['name'],mark)
        starts.append(ix+1)
    assert starts==sorted(starts)
    starts.append(len(body))
    result=[]
    for i,(title,mark,explanation) in enumerate(spec):
        part=body[starts[i]:starts[i+1]]
        result.append(dict(title=title,explanation=explanation,text=part))
    assert ''.join(p['text'] for p in result)==body
    return result


def body_panels(b):
    out='<p><strong>Code goes in the large SCL editor below the interface grid.</strong> Pull the horizontal divider down if the grid is hidden. Enter the sections below in order, appending each one beneath the previous one in the <em>same block</em>. Do not replace earlier sections, create a new FB per section, or paste declarations into this area.</p>'
    for ix,p in enumerate(body_sections(b)):
        ident='manual-code-'+b['name']+'-'+str(ix)
        text='<p>'+escape(p['explanation'])+'</p>'
        text+='<pre class="manual-code" id="'+ident+'" data-block="'+b['name']+'" data-part="'+str(ix)+'"><code>'+escape(p['text'])+'</code></pre>'
        text+='<button type="button" class="small-button" data-copy-code="'+ident+'">Copy this section</button>'
        out+=panel('manual-body-'+b['name']+'-'+str(ix),p['title'],text)
    out+='<p><strong>Check:</strong> after all sections are entered, press <strong>Ctrl+S</strong>. Right-click this block in the tree → <strong>Compile → Software (only changes)</strong>. Read the Compile pane; double-click the first error to go to its line. Resolve it before moving to the next block. Saving/compiling here does not download anything.</p>'
    return out


def block_task(id,b,title):
    body=create_block(b)+declaration_tables(b)
    if b['kind']!='DATA_BLOCK':body+=body_panels(b)
    else:body+='<p>Press Ctrl+S, then compile this new DB. A global DB has a declaration grid, not executable SCL to add. Start values are offline initial values, not instructions to modify a running DB.</p>'
    return dict(id=id,title=title,body=body)


def manual_data(data):
    d=copy.deepcopy(data)
    blocks=parse_source()
    mm6=next(g for g in d['groups'] if g['id']=='MM6')
    old={t['id']:t for t in mm6['tasks']}
    inventory=table(['New block','Choose this type'],[(code(b['name']), 'Instance DB for '+code(b['instance']) if b['instance'] else {'DATA_BLOCK':'Global DB','FUNCTION_BLOCK':'FB · SCL','FUNCTION':'FC · SCL'}[b['kind']]) for b in blocks.values()])
    new=[old['MM6-config'],dict(id='MM6-manual-folder',title='Create the CSI folder for the new blocks',body=steps(
        'Work in a saved copy of the current MM6 project. In <strong>Program blocks</strong>, check the names listed below. If an earlier CSI2 installation is already present, do not create over it or change its running instance type; use a separate learning copy for review.',
        'Right-click <strong>Program blocks → Add new group</strong>. Name the new group <strong>CSI</strong> if that group name is unused. It is an organizing folder, not executable logic. If CSI is already someone else’s group, use <strong>CSI reporting</strong> without renaming theirs.',
        'The main function block you will create is '+code('CSI_Reporting')+'. The other small blocks listed below supply its clock, stored values and reusable counters. Follow the checklist in order.',
        'Create each block through <strong>Add new block</strong> as its step says. If TIA puts it at the root of Program blocks, drag only that <em>new</em> block into your CSI group. Leave all existing blocks where they are.')+
        '<p class="note">These steps use SCL for the new code and keep OB1 in its existing language. The logic is the V2 design, entered by hand; it remains uncompiled in TIA and untested on the PLC. No import is required.</p>'+panel('manual-inventory','Names to check before creating anything',inventory))]
    new.append(block_task('MM6-manual-report',blocks['CSI2_Report'],'Create CSI2_Report and enter its tags'))
    new[-1]['body']+='<p><strong>First rows:</strong> Name '+code('SchemaVersion')+', Data type '+code('DInt')+', Start value '+code('2')+'. Then '+code('Heartbeat')+', '+code('DInt')+', '+code('0')+'. Continue in the exact order shown. These are DB members, not entries in PLC tags and not the OB1 declaration grid.</p>'
    new.append(block_task('MM6-manual-setup',blocks['CSI2_Setup'],'Create the three new setup bits'))
    new.append(dict(id='MM6-manual-helpers',title='Build the three small helper functions',body='<p>Create and compile these one at a time. Each has its own interface grid and code area.</p>'+''.join(panel('helper-'+n,n,block_task('',blocks[n],'')['body']) for n in ['CSI2_DayNumber','CSI2_Increment','CSI2_AddElapsed'])))
    new.append(block_task('MM6-manual-counter',blocks['CSI2_PeriodCounter'],'Build the reusable period counter'))
    new.append(block_task('MM6-manual-main',blocks['CSI_Reporting'],'Build CSI_Reporting: timing and counting'))
    new[-1]['body']=('<p><strong>This is the main reporting FB.</strong> Enter the interface first, then its eight code sections. Input rows receive values, Static rows keep memory between scans, and Temp rows are working values for this call.</p>'+new[-1]['body'])
    new.append(dict(id='MM6-manual-instance',title='Create CSI_Reporting’s instance DB',body=steps(
        'Compile '+code('CSI_Reporting')+' first. In <strong>Program blocks → Add new block</strong>, choose <strong>Data block (DB)</strong>.',
        'Enter Name = '+code('CSI2_MM6_Instance')+'. In <strong>Type</strong>, select the function block '+code('CSI_Reporting')+' instead of Global DB. Use automatic numbering and click OK.',
        'Open '+code('CSI2_MM6_Instance')+'. TIA fills its members from CSI_Reporting’s interface; do not type those members a second time. If the fields are wrong, fix the FB interface and recompile.',
        'Keep this new instance optimized. Do not attach it to '+code('CSI2_CycleMonitor')+' from the older import route. This manual route uses '+code('CSI_Reporting')+'.')+
        '<p>This DB is the main FB’s memory. Kepware will read the separate '+code('CSI2_Report')+' DB, not this instance’s internal offsets.</p>'))
    new.append(block_task('MM6-manual-run',blocks['CSI2_MM6_Run'],'Build the clock and MM6 input call'))
    new.append(block_task('MM6-manual-startup-block',blocks['CSI2_MM6_Startup'],'Build the startup-reset helper'))
    # Keep downstream task IDs only where the task itself is genuinely unchanged.
    for ident in ['MM6-v2-tags','MM6-v2-call','MM6-v2-inputs','MM6-v2-startup','MM6-v2-retention','MM6-v2-load','MM6-v2-check','MM6-v2-enable','MM6-v2-cycles']:
        t=copy.deepcopy(old[ident])
        if ident not in ['MM6-v2-tags','MM6-v2-inputs']:
            t['id']=ident.replace('MM6-v2-','MM6-manual-')
        t['title']=t['title'].replace('Open the new reporting tags','Check report offsets and record its DB number')
        t['body']=t['body'].replace('CSI2_CycleMonitor','CSI_Reporting').replace('new CSI2 blocks','new CSI/CSI2 blocks')
        if ident=='MM6-v2-tags':
            t['body']+='<p>Confirm <strong>SchemaVersion byte 0</strong>, <strong>PreviousCycleSeconds byte 40</strong>, <strong>CyclesToday byte 156</strong> and final field <strong>LastCycleEndTime byte 236</strong>. If any offset differs, fix row order/types in this new standard DB before using the Kepware map.</p>'
        if ident=='MM6-v2-call':
            t['body']+='<p>The actual path is <strong>OB1 → CSI2_MM6_Run → CSI2_MM6_Instance (CSI_Reporting)</strong>. Add the wrapper once only; do not also call CSI_Reporting directly from OB1 or run the old imported observer in parallel.</p>'
        if ident=='MM6-v2-load':
            t['body']=t['body'].replace('the new CSI2 blocks','the new CSI/CSI2 blocks')
            t['body']+='<p>Manually typed code needs the same full compile and load review as imported code. Do not load partially entered blocks.</p>'
        new.append(t)
    mm6['tasks']=new
    mm6['hint']='Create tags and write the code by hand'
    # Replace the generic instructions that refer to the old source route.
    d['instructions']=[dict(id='manual-editor',title='Where to enter tags and code',body=
        '<p><strong>New global tags:</strong> Program blocks → your new '+code('CSI2_Report')+' DB → declaration rows.</p>'
        '<p><strong>FB/FC variables:</strong> open that new block → upper interface grid → Input, Output, InOut, Static or Temp, as its table specifies.</p>'
        '<p><strong>SCL logic:</strong> large text editor below that grid. '+code('#State')+' is a local variable; '+code('"CSI2_Report".CyclesToday')+' is a global DB member. '+code(':=')+' assigns/copies a value; '+code('=')+' compares values.</p>'
        '<p>Use the numbered MM6 tasks. Type the code or copy one section at a time. The code boxes contain executable body text only, not FUNCTION_BLOCK / VAR / BEGIN source-file wrappers.</p>')]
    d['build']='2026-09-27-manual-csi-v4'
    return d


MANUAL_CSS='''
/* Manual build: nested tables and code stay collapsed until needed. */
.manual-panel-body{padding:0 14px 14px;min-width:0}
.manual-panel>summary{font-size:14px}
.manual-code{white-space:pre-wrap;overflow-wrap:anywhere;word-break:normal;max-width:100%;font:13px/1.6 ui-monospace,Consolas,monospace;padding:14px;background:#f4f6f5;border:1px solid #dbe3de;border-radius:6px;user-select:text}
.manual-code code{padding:0;background:none;font:inherit}
.manual-panel td{font-size:13px}
.manual-panel code{overflow-wrap:anywhere}
@media(max-width:600px){.manual-panel-body{padding:0 8px 12px}.manual-code{font-size:12px;padding:10px}}
'''
MANUAL_JS='''
// Preserve retired current-version steps in the existing Earlier records folder.
const retiredCSI=[...new Set([...Object.keys(state.done),...Object.keys(state.notes)])].filter(id=>!tasks.has(id));
if(retiredCSI.length){state.legacy??={version:1,done:{},notes:{},configs:{}};state.legacy.done??={};state.legacy.notes??={};for(const id of retiredCSI){if(state.done[id])state.legacy.done[id]=state.done[id];if(state.notes[id])state.legacy.notes[id]=state.notes[id];}}
document.addEventListener('click',event=>{const button=event.target.closest('[data-copy-code]');if(button){const target=document.getElementById(button.dataset.copyCode);if(target)copyText(target.textContent);}});
'''


def install():
    """Small idempotent builder hook. Existing app state and source bytes remain intact."""
    p=ROOT/'build_html.py';s=p.read_text()
    if 'from manual_steps import manual_data' not in s:
        assert 'from checklist_data import build_data' in s
        s=s.replace('from checklist_data import build_data','from checklist_data import build_data\nfrom manual_steps import manual_data',1)
        s=s.replace('D=build_data()','D=manual_data(build_data())',1)
    s=s.replace('25 Sep · simplified','27 Sep · manual CSI build')
    s=s.replace('machine-reporting-simple-v3-20260925','machine-reporting-manual-v4-20260927')
    s=s.replace('https://docs.tia.siemens.cloud/r/en-us/v20/creating-and-managing-blocks/using-external-source-files-for-stl-and-scl/generating-blocks-from-external-source-files','https://docs.tia.siemens.cloud/r/en-us/v20/programming-basics/block-calls/instances/single-instances')
    s=s.replace('Siemens: generate blocks from source','Siemens: FBs and instance DBs')
    p.write_text(s)
    p=ROOT/'app.js';s=p.read_text()
    if '// Preserve retired current-version steps' not in s:
        assert '\nbuild();' in s
        s=s.replace('\nbuild();','\n'+MANUAL_JS+'\nbuild();',1)
    p.write_text(s)
    p=ROOT/'style.css';s=p.read_text()
    if '/* Manual build:' not in s:s+='\n'+MANUAL_CSS
    p.write_text(s)
    p=ROOT/'README.md';s=p.read_text()
    if '## Manual CSI build' not in s:
        s+='\n## Manual CSI build\n\nMM6 now uses hand-created blocks, interface grids and body-only SCL sections. Create the CSI group and main CSI_Reporting FB; CSI2_Report keeps the V2 field layout for Kepware. Do not import or run the old route alongside this one.\n\nmanual_steps.py derives every interface row and executable body from the hash-checked V2 source. Only the main FB display name changes; its instance type becomes CSI_Reporting. The original SCL download remains unchanged. `python manual_steps.py --install` installs the idempotent build hook; then run build_html.py, tests/manual_structure_test.py, tests/manual_checklist_test.py and tests/v2_model_test.py. These tests are not a TIA compiler or a live PLC test.\n'
    p.write_text(s)
    p=ROOT/'AGENTS.md';s=p.read_text()
    if 'Manual-build route' not in s:
        s+='\nManual-build route: the user now wants to enter code manually. Keep exact UI clicks, declaration tables and body-only SCL pieces. manual_steps.py patches build_data without altering the V2 source. Do not revert to source import as the main checklist task. CSI is an optional folder; CSI_Reporting is the new main FB. Verify names in TIA before creation. Preserve retired v3 progress under Earlier checklist records. Run the manual structure/browser tests and existing V2 model tests.\n'
    p.write_text(s)
    parse_source()
    print('Manual build hook installed; source hash verified.')


if __name__=='__main__':
    import sys
    if '--install' in sys.argv:install()
    else:
        b=parse_source()
        print([(n,len(x['rows']),len(x['body'].splitlines())) for n,x in b.items()])
