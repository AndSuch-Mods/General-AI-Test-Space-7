"""Machine-specific naming + observe/copy deployment checklists.
Names only for MM6: no algorithm, network number, local declaration or report offset changes.
MM4/MM5 deployment is gated by observed signals and a target-compatible donor.
A WinLC/legacy port is explicitly NOT represented as a compiled MM6 copy.
"""
from pathlib import Path
from html import escape
import copy, json, re, hashlib, os
ROOT=Path(__file__).parent
BUILD='2026-09-28-mm4-mm5-mm6-rollout-v11'
BASE_REF_BLOB='0abb12d3a0a45f0865a05bc9ff873c583641532f'
SOURCES={
 'rename':('Siemens: rename a block','https://docs.tia.siemens.cloud/r/en-us/v20/creating-and-managing-blocks/managing-blocks/renaming-blocks'),
 'copy':('Siemens: copy blocks and resolve conflicts','https://docs.tia.siemens.cloud/r/en-us/v21/creating-and-managing-blocks/creating-blocks/copying-or-moving-blocks/basics-of-copying-blocks'),
 'paste':('Siemens: copy/paste procedure','https://docs.tia.siemens.cloud/r/en-us/v20/creating-and-managing-blocks/creating-blocks/copying-or-moving-blocks/copying-or-moving-blocks'),
 'reference':('Siemens: reference projects','https://docs.tia.siemens.cloud/r/en-us/v20/editing-projects/using-reference-projects/basics-of-reference-projects'),
 'access':('Siemens: optimized and standard access','https://docs.tia.siemens.cloud/r/en-us/v20/programming-basics/blocks-in-the-user-program/blocks-with-optimized-access/basics-of-block-access'),
 'retain':('Siemens: local-tag retention','https://docs.tia.siemens.cloud/r/en-us/v21/declaring-the-block-interface/rules-for-declaring-the-block-interface/setting-the-retentivity-of-local-tags'),
 'kepware':('PTC: Siemens DB addresses','https://support.ptc.com/help/kepware/drivers/en/kepware/drivers/SIEMENSTCPIPETHERNET/Standard_S7_300_400_Item_Syntax.html'),
}
def code(x):return '<code>'+escape(str(x))+'</code>'
def p(x):return '<p>'+x+'</p>'
def steps(*xs):return '<ol>'+''.join('<li>'+x+'</li>'for x in xs)+'</ol>'
def note(x):return '<p class="note">'+x+'</p>'
def refs(*keys):return '<p class="muted">'+ ' · '.join('<a target="_blank" rel="noopener noreferrer" href="'+SOURCES[k][1]+'">'+SOURCES[k][0]+'</a>'for k in keys)+'</p>'
def panel(id,title,body):return '<details class="small manual-panel" id="'+id+'"><summary>'+escape(title)+'</summary><div class="manual-panel-body">'+body+'</div></details>'
def table(head,rows):return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+escape(h)+'</th>'for h in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>'for x in row)+'</tr>'for row in rows)+'</tbody></table></div>'
def names(m):return {'CSI_Reporting_DB':'CSI_Reporting_'+m+'_DB','CSI_Reporting':'CSI_Reporting_'+m,'CSI_Report':'CSI_Report_'+m}
def renamed(s,m):
 mapping=names(m)
 return re.sub(r'\b(?:CSI_Reporting_DB|CSI_Reporting|CSI_Report)\b',lambda x:mapping[x[0]],s)
def transform(item,m):
 if isinstance(item,str):return renamed(item,m)
 if isinstance(item,list):return [transform(x,m)for x in item]
 if isinstance(item,tuple):return tuple(transform(x,m)for x in item)
 if isinstance(item,dict):return {k:(v if k in ('id','map')else transform(v,m))for k,v in item.items()}
 return copy.deepcopy(item)
def task(m,key,title,body,**extra):return dict(id=m+'-rollout-'+key,title=title,body=body,**extra)
def report_table(schema):return table(['Name','Type','Start','Byte'],[(code(f['name']),code(f['type']),code(f['initial']),str(f['offset']))for f in schema])
def inventory(m):return table(['Item','Name'],[('Reporting DB',code('CSI_Report_'+m)),('LAD function block',code('CSI_Reporting_'+m)),('Instance DB',code('CSI_Reporting_'+m+'_DB'))])

def rename_mm6_note(ident="rollout-mm6-rename"):
 return panel(ident,'Rename your existing MM6 blocks once; keep your networks',steps(
  'In TIA’s <strong>Program blocks</strong>, right-click the existing new <strong>CSI_Report → Rename → CSI_Report_MM6</strong>. Do not create another reporting DB.',
  'Rename <strong>CSI_Reporting → CSI_Reporting_MM6</strong>. If the instance already exists, rename <strong>CSI_Reporting_DB → CSI_Reporting_MM6_DB</strong>. If it does not exist yet, use that name when adding the call later.',
  'Keep the same block numbers, 12 member names, data types, order and retention settings. Renaming the block updates its symbolic uses in the program; do not retype every rung. Compile and inspect the renamed references afterward.',
  'Do not replace substrings across the whole project. Search specifically for the old fully quoted name, for example <code>"CSI_Report".</code>, within the new reporting logic. An absolute DB reference, an external source file or a separately configured Kepware symbol is not renamed by a text search.',
  'Continue where you stopped. Steps 1–4 and network numbers are not redesigned. The new names shown below refer to those same block objects.')+refs('rename'))

def observations(m):
 rows=[('DB98.DBX112.7','Close-command candidate','Turns TRUE at the intended start of closing.'),('Q44.0','Close output','Should agree with the command pair while the Servo branch is active.'),('DB94.DBX29.4','Robot-permission candidate','Must be seen FALSE during the cycle, then TRUE when the robot is finished/clear.'),('I505.7','Raw robot input','Compare with DB94.DBX29.4.'),('DB200.DBX38.2','Servo selector','Confirm TRUE for this close-command candidate; do not change it.'),('DB200.DBX49.3','EUROMAP selector','Record the value. FALSE alone neither verifies nor rejects the observed robot handshake.')]
 return steps(
  f'In <strong>{m} PLC → Watch and force tables → Add new watch table</strong>, enter these six addresses in the Address column. Leave Modify value blank; click <strong>Monitor all</strong>.',
  'Have the operator describe one normal production cycle on the phone: closing starts, robot handles the part, robot clears. Record the initial readings and each observed change. A stopped/manual/open-door snapshot is not the full cycle.',
  'Pass when the close-command rising edge matches closing, and the robot bit is seen low during the sequence then returns high at the desired finish. A second close pulse within the active cycle must be ignored by our observer.',
  'If the robot bit never drops, returns at the wrong stage, or a transition was not captured: leave this check open. Record the exact states/timestamps and revise the mapping with me before putting the counter into service. Do not force anything.')+table(['Address','Read as','Expected observation'],[(code(a),b,c)for a,b,c in rows])+note(
  'These are the first-archive MM4/MM5 candidates, not a claim that the live programs are identical. '+('MM4 previously showed Servo TRUE and EUROMAP FALSE; the robot-return sequence is still to be confirmed.'if m=='MM4'else 'MM5 may be a bit-for-bit duplicate of MM4, but its commissioning check stays incomplete until it can actually cycle. Offline preparation can continue.'))

def compatibility(m):
 donor='the completed MM6 reporting addition'if m=='MM4'else 'the verified MM4 reporting addition'
 return steps(
  f'Under the actual <strong>{m} CPU → Online & diagnostics</strong>, record CPU/controller type and firmware. Record the project’s TIA version. An .ap16 project can contain a legacy WinLC controller; the editor version is not the CPU family.',
  f'Preferred donor: <strong>{donor}</strong>. MM5 should normally copy the already-adapted, tested MM4 version rather than adapting MM6 independently.',
  '<strong>Matching supported CPU family:</strong> copy the new reporting blocks below, then compile for the target CPU. Never copy a complete machine/PC station to obtain three blocks.',
  '<strong>WinLC RTX / legacy S7-300/400 target:</strong> the MM6 S7-1500 FB is not a rename-only copy. Its DTL/RD_LOC_T, conversion/CALCULATE instructions and selective retention need target-specific equivalents. Do not change the project CPU or force optimization just to make it paste.',
  'With a verified legacy MM4 donor and matching MM5 CPU, continue with that donor. Without a compatible donor, stop the executable-block transfer and record the controller and first compiler errors for a legacy adaptation. You can still create the 12-field target reporting DB from the table. No complete legacy rung conversion is supplied by this copy workflow.')+note(
  'Earlier site information points to WinLC on MM4/MM5. Treat that branch as expected unless the live CPU identification proves otherwise. Matching event bits do not make a 1500 block compatible with WinLC.')+refs('copy','access')

def clone_steps(m,schema):
 report='CSI_Report_'+m;fb='CSI_Reporting_'+m;inst=fb+'_DB';src='MM6'if m=='MM4'else'MM4'
 donor_report='CSI_Report_'+src;donor_fb='CSI_Reporting_'+src
 out=[task(m,'observe','Observe the proposed start and robot-clear bits',observations(m),watch=['DB98.DBX112.7','Q44.0','DB94.DBX29.4','I505.7','DB200.DBX38.2','DB200.DBX49.3']),
 task(m,'target','Check the controller and choose the compatible donor',compatibility(m),fields=[('cpu','Confirmed CPU / firmware','text'),('tia','TIA version','text'),('donor','Donor project and verified CPU family','text')]),
 task(m,'backup','Save the target project and reserve the new block names',steps(
  f'Use a saved working copy of the current <strong>{m}</strong> project, not a renamed copy of a different machine’s whole project. Resolve unrelated online/offline differences before a download.',
  'Check the three names below and free FB/DB numbers under Program blocks. If a name is occupied, inspect it instead of overwriting it. A folder named CSI is fine; folder names do not provide separate block namespaces.',
  f'Keep the source project unchanged. All subsequent changes are to the new copy under <strong>{m}</strong>. Do not copy OB1, startup OBs, F-blocks, hardware configuration, PLC tag tables, IP addresses or PROFINET names.')+inventory(m)),
 task(m,'copy','Copy only the reporting DB and LAD FB',steps(
  f'After the compatibility check passes, open the <strong>{src}</strong> donor and the <strong>{m}</strong> target in compatible TIA installations. The target is the project you will edit. An existing reference-project view may also be used as a read-only donor.',
  f'In the donor’s Program blocks, select only <strong>{donor_report}</strong> and <strong>{donor_fb}</strong>. Right-click → <strong>Copy</strong>. In the target’s Program blocks/CSI group, right-click → <strong>Paste</strong>.',
  'Cancel any replace/overwrite option for an existing target block. Inspect the pasted FB and DB numbers: a number conflict is possible even when names differ. Assign verified free numbers in the new blocks’ Properties before compiling.',
  'Do not copy the instance DB or an online snapshot. A fresh instance will be created for the target FB. Do not copy source actual values into target start values.',
  'If TIA shows an unsupported-block/no-entry symbol or the source cannot be opened by the target TIA version, stop. Use the compatible donor/legacy-adaptation path, not a whole-project upgrade or CPU replacement as a workaround.')+refs('copy','paste','reference')),
 task(m,'rename','Rename the copies and check every report destination',steps(
  f'In the <strong>{m}</strong> project, rename the copied <strong>{donor_report} → {report}</strong>, then <strong>{donor_fb} → {fb}</strong>. Keep the 12 member names unchanged.',
  f'Open <strong>{fb}</strong>. All writes to the report must now use <code>"{report}".</code>. TIA updates linked symbolic uses on Rename; unresolved or previously absolute references need separate correction.',
  f'Within this new FB, search for the exact donor symbol <code>"{donor_report}"</code> and any other <code>CSI_Report_MM</code> names. No read/write to another machine’s report belongs here. Inspect the MOVE destinations, not only the displayed block title.',
  'Compile the new blocks and inspect the cross-references. Do not globally replace DB numbers or every occurrence of the machine name in the entire PLC project.')+refs('rename')),
 task(m,'report','Check the 12 tags and record this machine’s DB number',steps(
  f'Open <strong>{report}</strong>. Keep it standard/non-optimized, with all 12 fields retained. The start values for a NEW installation are zero. Do not reinitialize an existing in-service reporting DB.',
  'Verify names, types and byte offsets against this table. These are still the same 48 bytes. No SchemaVersion, setup bits, or additional diagnostic tags are added.',
  f'If a cross-family DB copy is unsupported, create <strong>Program blocks → Add new block → Data block → Global DB → {report}</strong>, then enter/copy only these declaration rows beneath Static. Do not include a runtime snapshot.',
  'Record the DB number actually assigned in this target project. DB56 on another PLC is not proof this one is DB56.')+report_table(schema),fields=[('reportDbCompact',report+' confirmed DB number','number')]),
 task(m,'adapt','Set the target event inputs and reporting condition',steps(
  f'The final OB1 call will use <strong>CloseCommand = %DB98.DBX112.7</strong> and <strong>RobotPermit = %DB94.DBX29.4</strong> on {m}. Q44.0 and I505.7 are comparison/watch rows, not extra call inputs. Do not keep MM6’s DB94.DBX29.6 or I705.7 mapping.',
  f'Open only <strong>{fb}</strong>. In a direct compatible MM6 copy, network 24 is “Run automatically when the real inputs and schedule are valid.” Its EUROMAP configuration contact must not silently reject an observed valid {m} handshake.',
  'After the observation passes, keep the Servo selector contact <code>%DB200.DBX38.2</code> and remove the <code>%DB200.DBX49.3</code> contact from THIS NEW OBSERVER’S allow path. Keep RobotDataValid, NOT AbortCycle, ClockOK, TickOK, Scheduled and the clock-continuity check. Never set or reset the original configuration bits.',
  'When copying a verified MM4 donor to MM5, preserve its already-reviewed condition. Locate the matching network by title if a legacy conversion changed numbering. Do not redesign the clock or timing networks on the fly.',
  'Record the three actual production/data-valid/abort sources. They are runtime data checks, not a temporary CSI_Setup. Do not use permanently TRUE qualifications to make the observer count.')+table(['Call input','Use'],[('ProductionEligible','Actual production sequence; exclude setup/jog.'),('RobotDataValid','Actual status showing the observed robot/input data are valid.'),('AbortCycle','Actual cycle-cancel condition; ordinary waiting is not an abort.')])+note('On a legacy controller, its clock and instruction conversion must be resolved before this step can lead to a download. This configuration-contact change alone is not a WinLC port.'),fields=[('production','ProductionEligible source','text'),('valid','RobotDataValid source','text'),('abort','AbortCycle source','text')]),
 task(m,'instance','Create a fresh instance and check startup / retention',steps(
  f'Compile the target-compatible <strong>{fb}</strong> first. In Program blocks → Add new block → Data block, name it <strong>{inst}</strong>, choose <strong>Type = {fb}</strong>, and use a free number. Do not choose Global DB for this instance.',
  'TIA supplies the instance’s members from the FB. Verify zero start values for State, CycleMs and WaitMs; FALSE for Initialized, PrevClose, PrevPermit and LowSeen; and -1 for the four saved period identities. Do not bring another machine’s live counts/state into this new instance.',
  '<strong>Supported optimized 1500 FB:</strong> retain HourSaved, DaySaved, DayShiftSaved and NightShiftSaved in the FB Static grid. Leave every other Static variable non-retentive. Keep the report DB itself fully retained.',
  '<strong>Legacy standard FB:</strong> individual retention is not available. Use its reviewed target-specific retention/startup plan. A retained instance requires an explicit startup reset of Initialized so the first reporting scan discards unfinished timing; do not assume MM6’s no-startup-OB scheme works unchanged.',
  'A required startup edit belongs in the target’s existing standard startup path, with its old instructions preserved. Do not copy the donor’s startup OB wholesale. No temporary setup DB is needed.')+panel('legacy-reset-'+m,'Legacy startup reset to include in the reviewed port',p('For a target-compatible version retaining the same first-call logic: append an unconditional reset coil <code>R</code> for <code>"'+inst+'".Initialized</code> in the applicable startup OB, plus <code>MOVE 0.0</code> into <code>"'+report+'".BetweenCycleSeconds</code>. The first cyclic call then clears State/CycleMs/WaitMs through the observer’s reset network. Preserve the four saved period keys and all held counts. Confirm the actual WinLC startup modes and retained-memory configuration before using this plan; these two actions do not convert the other 1500-only instructions.'))+refs('retain')),
 task(m,'call','Add one call at the end of this machine’s OB1',steps(
  f'Open <strong>{m} → Program blocks → OB1</strong>. Find the final normal cyclic network after the existing machine/robot processing. Use its real last network, not a guessed number copied from MM6.',
  f'Insert one new network and call <strong>{fb}</strong> with instance <strong>{inst}</strong>. In LAD/FBD drag the FB from the tree and select the existing single instance. In STL use the editor’s CALL with that FB/instance pair; keep OB1’s language.',
  'Connect the two event pins and the three verified machine conditions from the previous step. Keep the call unconditional and outside a jump/early-exit path so clock and waiting logic execute every normal scan.',
  'Check that this observer is called once, with its own instance. Do not call the donor observer as well. Leave the rest of OB1, machine outputs and safety logic untouched.')),
 task(m,'load','Compile, compare, then review the changes-only load',steps(
  'Proceed only after the signal observation, target compatibility, runtime input mapping, and startup/retention review pass. A successful paste or compile does not establish the physical timing.',
  f'Compile the target PLC software. Inspect that <strong>{fb}</strong> writes only its own instance and <strong>{report}</strong>. Resolve every error and unexpected block-number collision.',
  f'In the approved window, use <strong>Download to device → Software (only changes)</strong>. Confirm the selected device is <strong>{m}</strong>, and the load list contains only the new reporting blocks, intended OB1 call, and any reviewed legacy startup edit.',
  'Cancel an unexpected CPU STOP, hardware/F-program download, deletion or reinitialization of an existing machine DB. Review any initialization of the new reporting DB deliberately. The monitoring routine starts automatically when its call and conditions are active.',
  'Do not take an upload/download or retention behavior proven on MM6 as proof for another controller family. Follow this target’s actual Load preview.')),
 task(m,'verify','Observe the running count and save the verified donor',steps(
  f'Monitor <code>"{inst}".State</code>, <code>"{inst}".CycleMs</code>, and the 12 <strong>{report}</strong> fields. Let the first robot-low/return sequence synchronize without counting a partial cycle.',
  'Compare a complete cycle with the operator’s timing. Require one increment of TotalCompleted, a plausible PreviousCycleSeconds value, and no new count/restart from a secondary closing pulse. Confirm on the next cycle too.',
  'Observe a normal wait and its held PreviousBetweenSeconds at the next accepted start. Check that each machine’s Kepware view shows its own change, not another device’s.',
  'Leave acceptance unchecked if the machine cannot run. Counts/held values after a first installation may be partial; a watched TRUE bit is not proof of a complete cycle.',
  f'Archive the verified <strong>{m}</strong> project and record the donor revision. '+('This target-compatible MM4 addition is the preferred copy source for MM5.'if m=='MM4'else 'Record that MM5 was checked independently; keep the MM4 source project unchanged.')))]
 return out

def kepware_group(m):
 report='CSI_Report_'+m
 return dict(id='K-'+m,title=m+' tags',hint=report+' · 12 fields / 48 bytes',tasks=[
 dict(id='K-'+m+'-compact-device',title='Select the '+m+' device',body=steps('Back up the Kepware project. Select or create the approved Siemens TCP/IP Ethernet device for <strong>'+m+'</strong>. Use this machine’s confirmed endpoint, model and connection settings, not an IP copied from a different machine.','Under that device, create/select <strong>Production</strong>. Do not duplicate a whole device with the old PLC address still entered. A symbolic/OPC UA driver needs its own address method.'),fields=[('devicePath','Confirmed channel/device/group path','text')]),
 dict(id='K-'+m+'-compact-tags',title='Create the 12 read-only '+m+' tags',body=steps('Enter this machine’s confirmed <strong>'+report+'</strong> DB number below. Verify byte 0 is PreviousCycleSeconds and byte 44 is TotalCompleted. Renaming a DB does not change its addresses when its number/layout stay the same.','Add a tag under '+m+'.Production with the displayed address, <strong>Float</strong> for REAL seconds or <strong>Long</strong> for DINT counts, Client access <strong>Read Only</strong>. Start at 1000 ms unless the server’s established scan policy differs.','Read PreviousCycleSeconds with Good quality and compare it to TIA before adding the others. The short member names remain identical across devices; the full device/group path distinguishes machines.')+p('Example paths: <code>Siemens.MM4.Production.DayShiftCurrent</code>, <code>Siemens.MM5.Production.DayShiftCurrent</code>, <code>Siemens.MM6.Production.DayShiftCurrent</code>. Replace Siemens with the actual channel name.')+refs('kepware'),map=m),
 dict(id='K-'+m+'-compact-save',title='Verify '+m+' readings and save the server project',body=steps('Watch a verified production cycle on '+m+' and match its PLC count/time changes in the client. Make sure it is not reading another machine’s device.','Keep held counters/times read-only. Show bad/stale communication instead of treating an old value as live. This compact layout has no extra heartbeat/validity tags.','Save the Kepware project and export checklist progress. The CSV below is an address reference, not a promised version-specific Kepware import file.'))])

def apply_data(base):
 d=copy.deepcopy(base);mm6=next(g for g in d['groups']if g['id']=='MM6');old=copy.deepcopy(mm6)
 mm6.update(transform(mm6,'MM6'))
 # Keep task IDs, numbers, reportDbCompact and all stored user strings stable.
 current=next(t for t in mm6['tasks']if t['id']=='MM6-compact-section-2')
 current['body']=rename_mm6_note('rollout-mm6-rename-step5')+current['body']
 mm6['hint']='CSI_Report_MM6 · continue the current LAD build'
 for g in d['groups']:
  if g['id']in ('MM4','MM5'):
   m=g['id'];g.update(title=m+' programming',hint='Observe → compatible copy → rename → verify',tasks=clone_steps(m,d['schema']))
 for i,g in enumerate(d['kepware']):d['kepware'][i]=kepware_group(g['id'][2:])
 d['instructions']=[dict(id='machine-names',title='Machine names: rename the blocks, not every tag',body=inventory('MM6')+p('Use the same pattern for MM4/MM5. Individual tags such as <code>DayShiftCurrent</code> stay unchanged. ') +rename_mm6_note())]+[transform(x,'MM6')for x in d['instructions']]
 d['build']=BUILD;d['rollout_version']=11
 assert [t['id']for t in mm6['tasks']]==[t['id']for t in old['tasks']]
 for before,after in zip(old['tasks'][:4],mm6['tasks'][:4]):assert transform(before,'MM6')==after,'MM6 completed step changed beyond names'
 assert d['schema']==base['schema']
 return d

def patch_script(s,root):
 start=s.index('function renderMap(){');end=s.index('function legacyRecords(',start)
 s=s[:start]+(root/'machine_maps.js').read_text()+'\n'+s[end:]
 old="if(t.map){const map=e('div');map.id='tag-map';body.append(map);}"
 new="if(t.map){const map=e('div');map.id=(t.map===true||t.map==='MM6')?'tag-map':'tag-map-'+t.map;body.append(map);}"
 assert old in s, 'Map renderer changed; rebase this update'
 s=s.replace(old,new,1)
 # Helpful note above task numbers without adding/renumbering the current MM6 checklist.
 old="const list=e('div','task-list');d.append(list,e('p','empty'"
 new="const list=e('div','task-list');d.append(list,e('p','empty'"
 # Keep MM6 DOM IDs stable; user notes and old history are never renamed.
 return s

def finalize_rollout(root=None):
 root=Path(root or ROOT)
 if os.environ.get('CSI_SKIP_ROLLOUT')=='1':return
 path=root/'index.html';html=path.read_text();a=html.index('const DATA=')+len('const DATA=');base,n=json.JSONDecoder().raw_decode(html[a:])
 if base.get('rollout_version')==11:return
 raw=(root/'compact_reference.json').read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 assert blob==BASE_REF_BLOB,'Compact ladder reference changed: review before renaming'
 baseline=json.loads(raw);d=apply_data(base)
 (root/'tests').mkdir(exist_ok=True)
 (root/'tests/rollout_baseline.json').write_text(json.dumps(dict(data=base,reference=baseline),ensure_ascii=False))
 html=html[:a]+json.dumps(d,ensure_ascii=False).replace('</','<\\/')+html[a+n:]
 html=patch_script(html,root)
 html=re.sub(r'<span class="revision">.*?</span>','<span class="revision">28 Sep · MM4–MM6</span>',html,count=1)
 (root/'content.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));path.write_text(html)
 # Publish MM6 reference with exact block-symbol substitution only.
 ref=copy.deepcopy(baseline);block=ref['blocks'].pop('CSI_Reporting');ref['blocks']['CSI_Reporting_MM6']=transform(block,'MM6');ref['build']=BUILD
 ref['machine']='MM6';ref['report_db']='CSI_Report_MM6';ref['instance_db']='CSI_Reporting_MM6_DB'
 (root/'compact_reference.json').write_text(json.dumps(ref,indent=2));(root/'ladder_spec.json').write_bytes((root/'compact_reference.json').read_bytes())
 rollout=dict(build=BUILD,report_schema=d['schema'],machines={})
 for m in ('MM4','MM5','MM6'):
  rollout['machines'][m]=dict(report='CSI_Report_'+m,fb='CSI_Reporting_'+m,instance='CSI_Reporting_'+m+'_DB',close='%DB98.DBX112.7',permit='%DB94.DBX29.6'if m=='MM6'else'%DB94.DBX29.4',output='Q34.0'if m=='MM6'else'Q44.0',raw='I705.7'if m=='MM6'else'I505.7',copy_requires='Target-compatible donor and verified event behavior; WinLC requires a separately reviewed legacy adaptation.'if m!='MM6'else'Current MM6 reference, not TIA-compiled or PLC-tested.',same_member_names=True)
 (root/'machine_rollout_reference.json').write_text(json.dumps(rollout,indent=2))
 sw=root/'sw.js';s=sw.read_text();s=re.sub(r"const CACHE='[^']+';","const CACHE='machine-reporting-machines-v11-20260928';",s,count=1)
 match=re.search(r'const ASSETS=(\[.*?\]);',s)
 if match:
  assets=json.loads(match[1]);assets.append('./machine_rollout_reference.json');s=s[:match.start(1)]+json.dumps(list(dict.fromkeys(assets)))+s[match.end(1):]
 sw.write_text(s)
 print('Machine names applied; MM6 66 networks/12 fields unchanged. MM4/MM5 copy workflow requires compatible target.')

def install(root=None):
 root=Path(root or ROOT);p=root/'build_html.py';s=p.read_text()
 if 'from machine_rollout import finalize_rollout'not in s:s+='\nfrom machine_rollout import finalize_rollout\nfinalize_rollout(R)\n';p.write_text(s)
 note_text='''\n## Machine-suffixed deployment workflow\n\nCurrent final overlay: machine_rollout.py + machine_maps.js. MM6 remains the compact LAD build: only CSI_Report_MM6, CSI_Reporting_MM6 and CSI_Reporting_MM6_DB names change. Never alter the 12 field names/order/offsets or earlier network numbering to implement a naming request. User is through step 4 and working step 5. Preserve existing MM6 task IDs, notes, done state, and reportDbCompact. MM4/MM5 have new observe/copy/rename/compile/call/acceptance tasks; old observations stay as history, not automatic validation of new assumptions. Each machine has independent DB fields and Kepware maps.\n\nCopy requires matching instruction/controller support. Prior site information points to WinLC on MM4/MM5; do NOT market a renamed MM6 1500 FB as a legacy port. A verified target-compatible MM4 donor is preferred for MM5. No-entry blocks, unsupported DTL/RD_LOC_T/CALCULATE or missing retention support are stop gates. No complete legacy rung conversion is supplied by this workflow. Do not remove data-valid/production/abort qualifications, force machine bits, copy whole OBs/PC stations or bypass CPU/protection settings. The conditional removal of the EUROMAP selector is only within the NEW MM4/MM5 observer and requires waveform confirmation; leave the actual selector and MM6 logic untouched.\n\nUse CSI_SKIP_ROLLOUT=1 for prior guide regression tests, then rebuild normally and run tests/rollout_test.py for current UI/naming/copy workflow. Tests do not compile Siemens code or verify physical machine behavior. Keep Pages artifacts to one day and no extra screenshot ZIPs.\n'''
 for name in ('README.md','AGENTS.md'):
  p=root/name
  if p.exists() and '## Machine-suffixed deployment workflow'not in p.read_text():p.write_text(p.read_text()+note_text)
 print('Installed machine-name/copy guide overlay')
if __name__=='__main__':
 import sys
 if '--install'in sys.argv:install()
 else:finalize_rollout()
