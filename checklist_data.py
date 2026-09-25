"""Short field checklists. Keep task IDs stable; MM6 v2 install tasks are new on purpose."""
from pathlib import Path
import json

def steps(*items):
    return '<ol>' + ''.join('<li>'+x+'</li>' for x in items) + '</ol>'
def table(head,rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def task(id,title,body,**extra):return dict(id=id,title=title,body=body,**extra)

def watch_rows(mm):
    six=mm=='MM6'
    return [('DB98.DBX112.7','Closing command'),('Q34.0' if six else 'Q44.0','Closing output'),('DB94.DBX29.6' if six else 'DB94.DBX29.4','Robot permission'),('I705.7' if six else 'I505.7','Robot input'),('DB200.DBX38.2','Servo selection'),('DB200.DBX49.3','EUROMAP selection')]
def watch(mm):
    rows=watch_rows(mm)
    return steps('In <strong>TIA’s left Project tree</strong>, under this PLC, expand <strong>Watch and force tables</strong>. Double-click <strong>Add new watch table</strong>. It is alongside Program blocks, not inside OB1.',
    'In the new table, click the first blank <strong>Address</strong> cell. Enter these six addresses, one per row. Leave <strong>Modify value</strong> blank.',
    'Click the glasses button above this grid whose tooltip says <strong>Monitor all</strong>. Read <strong>Monitor value</strong>. Press Ctrl+S to save the table; this step needs no download.')+table(['Address','Meaning'],[('<code>'+a+'</code>',b) for a,b in rows])+'<p class="note">Read only. Do not force or change any of these machine bits.</p>'

MM6=[
 task('MM6-config','Monitor the six existing bits',watch('MM6')+'<p>Your MM6 screenshots showed both selection bits TRUE. The closing pair changed together; the robot pair went FALSE and returned TRUE.</p>'),
 task('MM6-v2-source','Import the MM6 code and create its tags',
 '<p><a class="download" href="downloads/MM6_Reporting_V2.scl" data-source download>Download MM6_Reporting_V2.scl</a></p>'+steps(
 'Save a working copy of MM6. Under <strong>Program blocks</strong>, check that the names beginning <code>CSI2_</code> are not already used. If they are, stop rather than regenerate over them.',
 'In the left tree under the MM6 PLC, expand <strong>External sources</strong> (or <strong>External source files</strong>) → double-click <strong>Add new external file</strong> → select the downloaded <code>MM6_Reporting_V2.scl</code> → Open.',
 'Right-click the added source → <strong>Generate blocks from source</strong>. Then expand <strong>Program blocks</strong> to see the new <code>CSI2_</code> blocks.')+
 '<p>The import creates the reporting tags and the logic together. Do not paste the whole file into OB1 or create these tags in the PLC tags table.</p><p class="note">V2 replaces the earlier MM6 reference. It has not been compiled in TIA or tested on the PLC. It starts disabled.</p>'),
 task('MM6-v2-tags','Open the new reporting tags',steps(
 'In <strong>Program blocks</strong>, double-click <strong>CSI2_Report</strong>. Its grid contains the new tag names, types and offsets.',
 'Find <code>PreviousCycleSeconds</code>, <code>BetweenCycleSeconds</code>, <code>CyclesThisHour</code> and <code>CyclesToday</code>. Do not add, delete or reorder rows.',
 'Record the <strong>DB number</strong> shown beside CSI2_Report in the tree. Enter just that number below; Kepware needs it.'),fields=[('reportDbV2','CSI2_Report DB number','number')]),
 task('MM6-v2-call','Add one call at the bottom of OB1',steps(
 'In <strong>Program blocks</strong>, double-click <strong>OB1</strong>. Scroll to its last existing network. The analyzed MM6 has <code>RobotMain / FC900</code> in network 48; leave that network unchanged.',
 'Right-click the last network’s heading → <strong>Insert network</strong>. Check that the empty network is below the existing code and outside a conditional jump. Name it <strong>Production reporting</strong>.',
 '<strong>If it is a text/STL network:</strong> click its first empty code line, type <code>CALL "CSI2_MM6_Run"</code>, and press Enter. TIA inserts the three parameter lines.',
 '<strong>If it is a ladder/FBD network:</strong> drag <code>CSI2_MM6_Run</code> from Program blocks into the empty network. Leave its call unconditional; do not put an AUTO contact before it.')+'<p>Use the form matching the editor already open. Do not convert OB1 to another language.</p>'),
 task('MM6-v2-inputs','Fill in the call’s three input tags',
 '<p>Click beside each input on the new call and enter its verified existing BOOL tag or address:</p>'+table(['Input','Connect it to'],[
 ('<code>ProductionEligible</code>','TRUE for production to count, including approved manually started production; FALSE for setup/jog.'),
 ('<code>RobotDataValid</code>','TRUE while the robot/input data being read are valid and current.'),
 ('<code>AbortCycle</code>','TRUE when the measured cycle is canceled. Normal waiting is not an abort.')])+
 '<p>The closing and robot-permission addresses are already inside the wrapper. No extra pins are needed for them.</p><p class="note">These three machine tags are still unverified. Leave this step unchecked and reporting disabled until they are resolved. Do not guess or use permanent TRUE values.</p>'+
 '<details class="small"><summary>Offline compile values while mappings are unresolved</summary><p>Enter <code>FALSE</code> for ProductionEligible, <code>FALSE</code> for RobotDataValid, and <code>TRUE</code> for AbortCycle. These deliberately prevent reporting. Replace all three before enabling.</p></details>',
 fields=[('production','ProductionEligible source tag','text'),('valid','RobotDataValid source tag','text'),('abort','AbortCycle source tag','text')]),
 task('MM6-v2-startup','Add the startup call',steps(
 'Under <strong>Program blocks</strong>, open the existing <strong>Startup</strong> OB, normally <strong>OB100</strong>. Leave all its current logic in place.',
 'Insert a new network after its existing logic. In STL, type <code>CALL "CSI2_MM6_Startup"</code> and press Enter. In LAD/FBD, drag that FC into the new network. It has no input pins.',
 'If no startup OB exists, use <strong>Add new block → Organization block → Startup</strong> in the standard program, select an available startup OB, and insert the call there. Confirm this is the startup path for this CPU; do not create or edit an F-block.') ),
 task('MM6-v2-retention','Keep counts and times through restart',steps(
 'Open <strong>CSI2_Report</strong>. In its declaration grid, use the <strong>Retain</strong> column to retain the new report data. For this standard-access DB, retention applies to the DB as a whole.',
 'Open <strong>CSI2_CycleMonitor</strong>. Expand its <strong>Static</strong> variables and configure retention for the four period-counter instances, including counts, keys and quality. Where retention is set in the instance DB, use <strong>CSI2_MM6_Instance</strong>. Retaining the full new instance is acceptable only if the CPU has capacity and the startup call above is installed.',
 'Keep <code>CSI2_Setup.Enable</code> and <code>WiringReviewed</code> FALSE for now. Compile and check any retention errors before proceeding.')+'<p class="note">If Retain is unavailable or the compiler rejects the selection, stop at that screen. Do not change retention on existing machine blocks.</p>'),
 task('MM6-v2-load','Compile, save and review the download',steps(
 'Right-click the PLC’s <strong>Program blocks → Compile → Software (only changes)</strong>. Read the Compile results below the editor; double-click an error to open its location. Resolve every error.',
 'Press <strong>Ctrl+S</strong>. With the site-approved change window, choose <strong>Download to device → Software (only changes)</strong>.',
 'Read <strong>Load preview</strong>. Verify the correct PLC, the new CSI2 blocks, and only the intended OB-call changes. Cancel unexpected STOP, hardware/F changes, deletions or initialization of existing DBs.',
 'Proceed only after that review. Keep reporting disabled until the next checks. Avoid running the earlier CSI observer and V2 as competing reporting sources.') ),
 task('MM6-v2-check','Watch the new tags and check the PLC clock',steps(
 'Create a <strong>separate new watch table</strong> under the MM6 PLC. In <strong>Name</strong>, enter each symbolic member below, or drag that member from its DB grid into the table.',
 'Click <strong>Monitor all</strong>. Require SchemaVersion = <strong>2</strong>, ConfigurationOK = <strong>1</strong>, ClockValid = <strong>1</strong>, and the correct local date/time. The two Setup bits should still be FALSE.',
 'Check SignalsValid, ProductionMode and AbortActive against the three tags you wired. Do not turn reporting on if those meanings are wrong.'),watch=['"CSI2_Report".SchemaVersion','"CSI2_Report".ConfigurationOK','"CSI2_Report".ClockValid','"CSI2_Report".LocalDateYYYYMMDD','"CSI2_Report".LocalTimeHHMMSS','"CSI2_Report".SignalsValid','"CSI2_Report".ProductionMode','"CSI2_Report".AbortActive','"CSI2_Setup".WiringReviewed','"CSI2_Setup".Enable']),
 task('MM6-v2-enable','Enable the new reporting block',steps(
 'Only after the input mappings and checks above are complete, use the <strong>new reporting watch table</strong>. Enter TRUE in <strong>Modify value</strong> for <code>"CSI2_Setup".WiringReviewed</code> and <code>"CSI2_Setup".Enable</code>.',
 'Select only those two rows. Use the normal <strong>Modify now / Modify selected values</strong> command, checking the tooltip and target rows first. Do not use Force.',
 'Confirm both Monitor values become TRUE. Clear their Modify value cells afterward so they cannot be resent accidentally.')+'<p class="note">This is the only planned write from the watch table: two NEW CSI2_Setup bits. Do not modify any original motion, permission or configuration bit.</p>'),
 task('MM6-v2-cycles','Check the reported cycle and waiting times',steps(
 'Add the report tags below to the reporting watch table and click <strong>Monitor all</strong>.',
 'Expect MonitorState <strong>10</strong> while synchronizing, <strong>20</strong> while between cycles, and <strong>30</strong> while timing. The first unknown partial cycle is deliberately skipped.',
 'Observe at least five normal cycles with someone at the machine. Each valid completion must update PreviousCycleSeconds and add exactly one to TotalCompleted. A second closing pulse inside the cycle must not restart or count another cycle.',
 'Check BetweenCycleSeconds during a real wait and PreviousBetweenSeconds after the next start. Confirm the period counts at a boundary or in an isolated test, then archive the finished TIA project.'),watch=['"CSI2_Report".MonitorState','"CSI2_Report".TotalCompleted','"CSI2_Report".PreviousCycleSeconds','"CSI2_Report".PreviousCycleValid','"CSI2_Report".BetweenCycleSeconds','"CSI2_Report".BetweenActive','"CSI2_Report".PreviousBetweenSeconds','"CSI2_Report".CyclesThisHour','"CSI2_Report".CyclesToday'])
]

def other(mm):
    return dict(id=mm,title=mm+' programming',hint='Confirm signals'+(' when available' if mm=='MM5' else ''),tasks=[
    task(mm+'-config','Open the watch table',watch(mm)),
    task(mm+'-start','Match the closing bit to the machine',steps('Have the operator identify the start of a production cycle over the phone.', 'Watch <code>DB98.DBX112.7</code> and <code>Q44.0</code>. Record when they turn TRUE and whether there is another pulse later in the same cycle.')),
    task(mm+'-finish','Match the robot return to cycle end',steps('Watch <code>DB94.DBX29.4</code> and <code>I505.7</code>. Record the low state and the return to TRUE.', 'Have the operator confirm whether that return is when the robot is done and clear. Save your photos/times in the notes. Do not mark a robot sequence verified from manual closing alone.')),
    task(mm+'-qualify','Record the three reporting conditions','<p>Record the existing production-eligible, robot-data-valid and abort tags. Leave unresolved items blank. These machines need their own reviewed source mapping; do not import the MM6 V2 source unchanged.</p>',fields=[('production','Production-eligible tag','text'),('valid','Robot-data-valid tag','text'),('abort','Abort tag','text')])])

KP6=[
 task('K-MM6-v2-device','Select the existing MM6 device',steps('Open the Kepware server configuration and save a backup of its project.', 'In the left connection tree, select the existing <strong>MM6</strong> device. Confirm its endpoint is MM6, not another machine.', 'Use the address map here only with the <strong>Siemens TCP/IP Ethernet</strong> driver. A symbolic S7 Plus or OPC UA connection uses its own addressing. Do not change PLC security or hardware to make a connection work.')),
 task('K-MM6-v2-first','Create and test SchemaVersion',steps('Under MM6, right-click → <strong>New Tag Group</strong> → name it <strong>Production</strong>. Use the existing group if it is already there.', 'Select Production → right-click → <strong>New Tag</strong>. Enter Name = <code>SchemaVersion</code>; Address = the SchemaVersion address in the map below; Data type = <strong>Long</strong>; Client access = <strong>Read Only</strong>; Scan rate = <strong>1000 ms</strong>. Click Apply/OK.', 'Open <strong>Tools → Launch OPC Quick Client</strong> (or the installed test client). Browse the MM6 Production group. Require <strong>Good</strong> quality and value <strong>2</strong>. Stop and check the DB number, driver and access if it is not Good.')),
 task('K-MM6-v2-tags','Add the time and count tags','<p>Repeat <strong>New Tag</strong> for the rows in the address map below. Use <strong>Long</strong> for DINT counts/status and <strong>Float</strong> for REAL seconds. Keep every tag <strong>Read Only</strong>.</p><p>Add Heartbeat and compare one time value with TIA before entering the remaining rows. The CSV is an address reference; for bulk import, export one tag from this Kepware version and use its exact CSV format.</p>',map=True),
 task('K-MM6-v2-save','Check the display and save Kepware',steps('Compare current/previous hour, day and both shift counts with TIA. Check PreviousCycleSeconds and both between-cycle values.', 'Use BetweenActive for live waiting, the Valid fields for held values, and Partial/key fields for period quality. Do not display stale/bad-quality data as live.', 'Save the Kepware project and record the real channel/device/group path. Export this checklist’s progress if you are moving to another computer.'))]

def build_data():
    schema=json.loads((Path(__file__).parent/'schema_v2.json').read_text())
    groups=[other('MM4'),other('MM5'),dict(id='MM6',title='MM6 programming',hint='V2 source and installation',tasks=MM6)]
    kg=[dict(id='K-'+mm,title=mm+' tags',hint='',tasks=[task('K-'+mm+'-verified-map','Use this machine’s verified report DB','<p>After its reporting code is installed and tested, record that machine’s report DB and offsets. Do not copy MM6’s DB number or V2 map into this device. Existing server notes and earlier checklist records are preserved under Completed.</p>')]) for mm in ['MM4','MM5']]
    kg.append(dict(id='K-MM6',title='MM6 tags',hint='Read CSI2_Report',tasks=KP6))
    return dict(version=3,build='2026-09-25-simple-v3',groups=groups,kepware=kg,schema=schema,
    display_fields=['SchemaVersion','Heartbeat','CyclesThisHour','CyclesPreviousHour','CyclesToday','CyclesPreviousDay','Shift1Current','Shift1Previous','Shift2Current','Shift2Previous','TotalCompleted','PreviousCycleSeconds','BetweenCycleSeconds','PreviousBetweenSeconds'],
    instructions=[
    dict(id='where',title='Where to click in TIA',body=table(['Task','Left Project tree'],[
    ('Watch existing bits','PLC → <strong>Watch and force tables → Add new watch table</strong>'),
    ('Import the supplied code','PLC → <strong>External sources → Add new external file</strong>'),
    ('See the new report tags','PLC → <strong>Program blocks → CSI2_Report</strong>'),
    ('Add the cyclic call','PLC → <strong>Program blocks → OB1 → last network</strong>')])+'<p>A watch table displays existing values. Importing the MM6 source creates the new reporting tags in CSI2_Report. Do not type them into OB1’s declaration grid.</p>'),
    dict(id='periods',title='Count periods and units',body='<p>Shift 1: <strong>06:30–17:00</strong>. Shift 2: <strong>17:00–06:00</strong>. The 06:00–06:30 gap belongs to neither shift. Day: midnight to midnight. Count at completion; times are in seconds.</p><p>The live between-cycle timer needs <code>BetweenActive = 1</code>. It does not measure CPU STOP or power-off time.</p>')])
if __name__=='__main__':
    Path(__file__).with_name('content.json').write_text(json.dumps(build_data(),ensure_ascii=False,indent=2))
