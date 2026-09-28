"""Explain and source the five reporting pins. Do not change the 66 FB networks."""
from pathlib import Path
from html import escape
import copy, hashlib, json, os, re
ROOT=Path(__file__).parent
BUILD='2026-09-28-input-sources-v12'
DIAG_URL='https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/diagnostics-s7-1200-s7-1500/get_diag-read-diagnostic-information-s7-1200-s7-1500'
EVIDENCE='https://github.com/AndSuch-Mods/General-AI-Test-Space-7/blob/main/input_mapping_evidence.md'
def code(s):return '<code>'+escape(str(s))+'</code>'
def table(rows):return '<div class="table-wrap"><table><thead><tr><th>Input on the left</th><th>What TRUE means</th><th>Source / status</th></tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+x+'</td>'for x in row)+'</tr>'for row in rows)+'</tbody></table></div>'
def panel(id,title,body):return '<details class="small manual-panel" id="'+id+'"><summary>'+escape(title)+'</summary><div class="manual-panel-body">'+body+'</div></details>'
def steps(*xs):return '<ol>'+''.join('<li>'+x+'</li>'for x in xs)+'</ol>'
def pre(s):return '<pre>'+escape(s)+'</pre>'
def definitions(m):
 end='DB94.DBX29.6'if m=='MM6'else'DB94.DBX29.4'
 return '<p><strong>The left-hand names are our FB inputs, not existing German tags.</strong> The right-hand side is the machine bit or calculated value you connect. These inputs only affect reporting; AbortCycle does not abort the machine.</p>'+table([
 ('CloseCommand','Mold closing is commanded.',code('DB98.DBX112.7')+'; candidate checked in the supplied archive.'),
 ('RobotPermit','The robot interface permits mold closing.',code(end)+'; time the low-to-high return, not an already-high input at startup.'),
 ('ProductionEligible','This operating mode is production we intend to count.',code('M50.2')+' = semiautomatic; '+code('M50.3')+' = automatic. Proposed rule: either is TRUE. See the small OB1 expression below.'),
 ('RobotDataValid','The observed robot inputs are available and trustworthy.','<strong>No existing one-bit source verified.</strong> Not the same as RobotPermit or RunChainOK. MM6 has a candidate read-only module-diagnostic route below; legacy MM4/MM5 needs its own diagnostic mapping.'),
 ('AbortCycle','Discard the unfinished measurement because a reset/cancel applies.',code('DB20.DBX0.1')+' = class-1 immediate-stop fault used in the original sequencer-reset logic. This covers that reset source, not every possible robot cancel.')])+('<p class="muted">Sources: PF1000825 MM6 archive. These are offline findings; confirm the current project matches.</p>'if m=='MM6'else'<p class="muted">Sources: PF1000723, the supplied MM4/MM5 reference archive. MM5 is expected to duplicate MM4, but this is not a live verification of either CPU. MM4 previously displayed a different project name.</p>')
def production(m):
 t='CSI_ProductionEligible_'+m
 return steps('In <strong>OB1 → upper declaration grid → Temp</strong>, append one new row at the <strong>end</strong>: Name = '+code(t)+', Data type = <strong>Bool</strong>. Do not insert it above existing Temp declarations or add it to the reporting DB.',
 'Immediately before your existing CSI CALL in the new STL network, enter the four lines below. They only read M50.2/M50.3 and write the new local result.',
 'Set the call input <strong>ProductionEligible := '+code('#'+t)+'</strong>. Do not type “M50.2 OR M50.3” directly into the actual-parameter field.')+pre('CLR\nO     M50.2\nO     M50.3\n=     #'+t)+'<p><strong>Policy:</strong> semiautomatic plus automatic production. Manual individual operation (M50.0), manual stepping (M50.1), preheat and tool change are excluded. For automatic-only production, M50.3 alone can feed ProductionEligible. Do not change the machine mode bits to satisfy the observer.</p>'
def watch(m):
 return steps('In the existing watch table, add these read-only rows: '+code('M50.2')+', '+code('M50.3')+', '+code('DB20.DBX0.1')+'. Leave Modify value blank.',
 'Automatic mode should show M50.3 TRUE; semiautomatic should show M50.2 TRUE. DB20.DBX0.1 should normally be FALSE without a class-1 stop fault. Observe with the operator; do not create a stop or force these bits.',
 'If the live mode or reset behavior disagrees, keep the mapping unapproved and send the readings. You do not need to search German function blocks yourself.')
def diag(m):
 if m!='MM6':
  return '<p><strong>Still unresolved for '+m+': the exact RobotDataValid operand.</strong> The legacy reference reads PROFINET system status using RDSYSST in FC20; RET_VAL is DB7.DBW0 and BUSY is DB7.DBX2.0. Neither alone proves the robot data are valid. The robot station entry and the diagnostic completion/freshness handling must be identified.</p><p>Do not substitute MM6 hardware ID 302, guess an I500.x address, or use a constant TRUE. Once the working MM4 diagnostic mapping is verified, copy that target-compatible method to MM5. Until then, this is a pending commissioning item, not a finished call.</p>'
 return '<p><strong>No single existing RobotDataValid bit was found.</strong> I700.5 is RunChainOK, I700.4 is robot auto mode, and I700.6 is ExecutionError. None proves PROFINET input quality. The robot’s OK_ToStart also requires motors off, so it is unsuitable while running.</p>'+steps(
 'In TIA <strong>Devices & networks → Network view</strong>, select the ABB robot station, named <strong>RobotBasicIO</strong> in the supplied archive. Open <strong>Device view → Device overview</strong>. Find its <strong>DI 32 bytes</strong> input module. Confirm that its input-address range includes <strong>I705.7</strong>. Do not edit its addresses or configuration.',
 'Under the MM6 CPU, open <strong>PLC tags → Show all tags → System constants</strong>. The archive contains '+code('RobotBasicIO~DI_32_bytes_1')+' of type HW_SUBMODULE, value <strong>302</strong>. Use the current matching symbolic constant, not a guessed number. If the names/addresses differ, capture this screen for review.',
 '<strong>Only after that match:</strong> a new read-only GET_DIAG MODE 1 query on that input submodule can produce the reporting qualification. This is additional OB1 input preparation, not an edit to your 66 FB networks. Compile/support and live Good-status checks are still required.')+panel('inputs-MM6-diag-build','After hardware confirmation: build the small read-only diagnostic',
 '<p>Append these variables under <strong>OB1 → Temp</strong>: '+code('CSI_RobotDiag_MM6')+' / <strong>DIS</strong>; '+code('CSI_RobotDiagStatus_MM6')+' / <strong>Int</strong>; '+code('CSI_RobotDiagCount_MM6')+' / <strong>UInt</strong>; '+code('CSI_RobotDataValid_MM6')+' / <strong>Bool</strong>. DIS is Siemens’ system data type; its nested fields are supplied by TIA.</p>'+steps(
 'Before the reporting CALL, use the Instructions pane to insert <strong>GET_DIAG</strong> in the STL editor and let TIA generate its formal parameters. Call it every scan, not conditionally behind a machine-running bit.',
 'Connect MODE = '+code('UINT#1')+'; LADDR = the <strong>verified</strong> input-submodule system constant; RET_VAL = '+code('#CSI_RobotDiagStatus_MM6')+'; CNT_DIAG = '+code('#CSI_RobotDiagCount_MM6')+'; DIAG = '+code('#CSI_RobotDiag_MM6')+'. Do not use the hidden DETAIL parameter.',
 'After the diagnostic call, and before the reporting call, enter the expression below. A failed diagnostic read cannot qualify the data because RET_VAL must equal zero.',
 'Then connect <strong>RobotDataValid := '+code('#CSI_RobotDataValid_MM6')+'</strong> on your existing reporting call. With the hardware healthy, require status 0 and IOState Good bit TRUE. Do not force a test value if they disagree.')+pre('L     #CSI_RobotDiagStatus_MM6\nL     0\n==I\nA     #CSI_RobotDiag_MM6.IOState.%X0\n=     #CSI_RobotDataValid_MM6')+
 '<p class="note">Proposed module-health qualification, not hardware-tested code. It cannot prove the robot application is advancing or that a part was picked. Confirm the actual I/O mapping and installed instruction support before loading. GET_DIAG only reads hardware status and writes these new local variables.</p><p><a href="'+DIAG_URL+'" target="_blank" rel="noopener noreferrer">Siemens GET_DIAG: DIS structure, return status and IOState Good bit</a></p>')
def body(m):
 return '<section id="input-guide-'+m+'">'+definitions(m)+panel('inputs-'+m+'-production','ProductionEligible: exact mode bits and OB1 entry',production(m))+panel('inputs-'+m+'-abort','AbortCycle: use the class-1 reset source, not an ordinary stop',
 '<p>The supplied program reads '+code('DB20.DBX0.1')+' in <strong>FC40, network 14</strong> to reset the sequencer. Its MM6 name is '+code('DB Störungen.Klasse_1_NotStop')+'. The same address appears in the first MM4/MM5 archive.</p><p>For that defined cancellation case, connect <strong>AbortCycle := '+code('DB20.DBX0.1')+'</strong>. This is a read of a standard fault flag, not a safety function or an output to the machine.</p><p>It does not cover every robot restart/cancel. Do not replace it with NOT M40.4, a generic warning, a motor-off bit, or the whole sequencer-reset expression: normal pauses/end-of-cycle processing could then erase the wait you want to measure.</p>')+panel('inputs-'+m+'-valid','RobotDataValid: what is still needed',diag(m))+panel('inputs-'+m+'-watch','Check these three known source bits',watch(m))+'<p class="muted"><a href="'+EVIDENCE+'" target="_blank" rel="noopener noreferrer">Archive evidence, English translations and remaining limits</a>. The current call is not ready for service until its data-valid mapping is confirmed. No existing bit is forced, and the report layout and existing ladder networks stay unchanged.</p></section>'
def apply_notes(data):
 d=copy.deepcopy(data)
 for m in ('MM4','MM5','MM6'):
  group=next(g for g in d['groups']if g['id']==m)
  tid='MM6-compact-call'if m=='MM6'else m+'-rollout-adapt'
  target=next(t for t in group['tasks']if t['id']==tid)
  if 'id="input-guide-'+m+'"' not in target['body']:
   target['body']=body(m)+target['body']
  target['body']=target['body'].replace('These three real machine conditions are still unverified.','The mode and class-1 reset sources above are traced in the archives; current-machine validation and RobotDataValid remain pending.')
 d['input_notes_version']=BUILD
 return d

def finalize_inputs(root=ROOT):
 if os.environ.get('CSI_SKIP_ROLLOUT')=='1' or os.environ.get('CSI_SKIP_INPUT_NOTES')=='1':return
 root=Path(root);p=root/'index.html';text=p.read_text();pos=text.index('const DATA=')+len('const DATA=');original,n=json.JSONDecoder().raw_decode(text[pos:]);d=apply_notes(original)
 assert d['schema']==original['schema'] and d['kepware']==original['kepware']
 before=next(g for g in original['groups']if g['id']=='MM6');after=next(g for g in d['groups']if g['id']=='MM6')
 assert before['tasks'][:7]==after['tasks'][:7], 'Completed work or timing/counting sections changed'
 assert [t['id']for g in original['groups']for t in g['tasks']]==[t['id']for g in d['groups']for t in g['tasks']]
 text=text[:pos]+json.dumps(d,ensure_ascii=False).replace('</','<\\/')+text[pos+n:]
 text=re.sub(r'<span class="revision">.*?</span>','<span class="revision">28 Sep · input meanings</span>',text,count=1)
 p.write_text(text);(root/'content.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
 sw=root/'sw.js';s=sw.read_text();s=re.sub(r"const CACHE='[^']+';","const CACHE='machine-reporting-input-notes-v12-20260928';",s,count=1);sw.write_text(s)
 print('Added evidence-backed input notes: core networks, report layout, task IDs and saved data unchanged.')

def install(root=ROOT):
 root=Path(root);p=root/'build_html.py';s=p.read_text()
 if 'from input_notes import finalize_inputs'not in s:s+='\nfrom input_notes import finalize_inputs\nfinalize_inputs(R)\n';p.write_text(s)
 p=root/'AGENTS.md';s=p.read_text()
 if '## Input source notes'not in s:s+='\n## Input source notes\n\ninput_notes.py appends English pin explanations and traced mode/reset sources to the existing call/adapt tasks only. M50.2 (semiauto) OR M50.3 (auto) is a proposed production policy; DB20.DBX0.1 is a class-1 sequencer-reset source, not every possible abort. RobotDataValid is NOT a verified existing bit. MM6 includes a conditional new GET_DIAG input-submodule recipe after current hardware confirmation; MM4/MM5 legacy diagnostic mapping remains unresolved. Never label RunChainOK as communication quality, silently set TRUE, or call the optional recipe machine-tested. Keep the first seven MM6 tasks, all 66 authored networks, five FB pins and 12 fields unchanged. Source evidence is in input_mapping_evidence.md. Use tests/input_notes_test.py after the normal build.\n';p.write_text(s)
if __name__=='__main__':
 import sys
 if '--install'in sys.argv:install()
 else:finalize_inputs()
