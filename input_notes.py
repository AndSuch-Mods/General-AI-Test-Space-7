"""Explain and source the five reporting pins. Do not change the 66 FB networks."""
from pathlib import Path
from html import escape
import copy, hashlib, json, os, re
ROOT=Path(__file__).parent
BUILD='2026-09-28-robot-operational-gates-v13'
DIAG_URL='https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/diagnostics-s7-1200-s7-1500/get_diag-read-diagnostic-information-s7-1200-s7-1500'
EVIDENCE='https://github.com/AndSuch-Mods/General-AI-Test-Space-7/blob/main/input_mapping_evidence.md'
def code(s):return '<code>'+escape(str(s))+'</code>'
def table(rows):return '<div class="table-wrap"><table><thead><tr><th>Input on the left</th><th>What TRUE means</th><th>Source / status</th></tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+x+'</td>'for x in row)+'</tr>'for row in rows)+'</tbody></table></div>'
def panel(id,title,body):return '<details class="small manual-panel" id="'+id+'"><summary>'+escape(title)+'</summary><div class="manual-panel-body">'+body+'</div></details>'
def steps(*xs):return '<ol>'+''.join('<li>'+x+'</li>'for x in xs)+'</ol>'
def pre(s):return '<pre>'+escape(s)+'</pre>'
def definitions(m):
 end='DB94.DBX29.6'if m=='MM6'else'DB94.DBX29.4'
 if m=='MM6':
  valid=code('I700.4')+' AutoOn AND '+code('I700.5')+' RunChainOK AND NOT '+code('I700.6')+' ExecutionError. <strong>Observed live as TRUE / TRUE / FALSE through a complete normal MM6 cycle.</strong> This is a practical robot-operational reporting gate, not a PROFINET quality bit.'
 else:
  valid=code('I500.4')+' AutoOn AND '+code('I500.5')+' RunChainOK AND NOT '+code('I500.6')+' ExecutionError. These exact roles are present in the supplied MM4/MM5 reference archive. Watch TRUE / TRUE / FALSE through a normal cycle before using the gate live.'
 return '<p><strong>The left-hand names are our FB inputs, not existing German tags.</strong> The right-hand side is the machine bit or calculated value you connect. These inputs only affect reporting; AbortCycle does not abort the machine.</p>'+table([
 ('CloseCommand','Mold closing is commanded.',code('DB98.DBX112.7')+'; candidate checked in the supplied archive.'),
 ('RobotPermit','The robot interface permits mold closing.',code(end)+'; time the low-to-high return, not an already-high input at startup.'),
 ('ProductionEligible','This operating mode is production we intend to count.',code('M50.2')+' = semiautomatic; '+code('M50.3')+' = automatic. Proposed rule: either is TRUE. See the small OB1 expression below.'),
 ('RobotDataValid','The robot is in its expected operating state for this reporting observation.',valid),
 ('AbortCycle','Discard the unfinished measurement because a reset/cancel applies.',code('DB20.DBX0.1')+' = class-1 immediate-stop fault used in the original sequencer-reset logic. This covers that reset source, not every possible robot cancel.')])+('<p class="muted">Sources: PF1000825 MM6 archive plus the live MM6 watch observation. The three robot-status bits are an operational-health gate, not a dedicated network-quality diagnostic.</p>'if m=='MM6'else'<p class="muted">Sources: PF1000723, the supplied MM4/MM5 reference archive. The archive maps I500.4/5/6 to AutoOn / RunChainOK / ExecutionError. Confirm the same live behavior on the actual machine before commissioning.</p>')

def production(m):
 t='CSI_ProductionEligible_'+m
 return steps('In <strong>OB1 → upper declaration grid → Temp</strong>, append one new row at the <strong>end</strong>: Name = '+code(t)+', Data type = <strong>Bool</strong>. Do not insert it above existing Temp declarations or add it to the reporting DB.',
 'Immediately before your existing CSI CALL in the new STL network, enter the four lines below. They only read M50.2/M50.3 and write the new local result.',
 'Set the call input <strong>ProductionEligible := '+code('#'+t)+'</strong>. Do not type “M50.2 OR M50.3” directly into the actual-parameter field.')+pre('CLR\nO     M50.2\nO     M50.3\n=     #'+t)+'<p><strong>Policy:</strong> semiautomatic plus automatic production. Manual individual operation (M50.0), manual stepping (M50.1), preheat and tool change are excluded. For automatic-only production, M50.3 alone can feed ProductionEligible. Do not change the machine mode bits to satisfy the observer.</p>'
def watch(m):
 robot=('I700.4','I700.5','I700.6')if m=='MM6'else('I500.4','I500.5','I500.6')
 return steps('In the existing watch table, add these read-only rows: '+code('M50.2')+', '+code('M50.3')+', '+code('DB20.DBX0.1')+', '+code(robot[0])+', '+code(robot[1])+', '+code(robot[2])+'. Leave Modify value blank.',
 'Automatic mode should show M50.3 TRUE; semiautomatic should show M50.2 TRUE. DB20.DBX0.1 should normally be FALSE without a class-1 stop fault.',
 'For the robot operational gate, expect AutoOn = TRUE, RunChainOK = TRUE and ExecutionError = FALSE through the complete normal cycle. MM6 has already been observed doing this; MM4/MM5 still need the same live check before commissioning.',
 'If any of those robot-status bits normally changes during the cycle, do not use the proposed RobotDataValid expression unchanged. Record the states/timestamps and revise the gate. Never force these bits.')

def diag(m):
 base='700'if m=='MM6'else'500'
 t='CSI_RobotDataValid_'+m
 live_note=('<strong>MM6 live check passed:</strong> I700.4 / I700.5 / I700.6 stayed TRUE / TRUE / FALSE through a complete normal cycle.'if m=='MM6'else'<strong>'+m+' archive mapping:</strong> I500.4 = AutoOn, I500.5 = RunChainOK, I500.6 = ExecutionError. Confirm TRUE / TRUE / FALSE through a real cycle before the live download.')
 return ('<p>'+live_note+'</p>'+steps(
  'In <strong>OB1 → upper declaration grid → Temp</strong>, append Name = '+code(t)+', Data type = <strong>Bool</strong>. Do not add this to CSI_Report.',
  'Immediately before the CSI reporting CALL, add the four-line STL expression below. It reads the existing robot-status inputs and writes only the new OB1 Temp bit.',
  'Connect <strong>RobotDataValid := '+code('#'+t)+'</strong> on the reporting CALL.',
  'Before commissioning '+m+', watch the three source inputs through a normal robot cycle. They must remain AutoOn TRUE, RunChainOK TRUE and ExecutionError FALSE. If not, stop and revise this reporting gate.')+pre('CLR\nA     I'+base+'.4\nA     I'+base+'.5\nAN    I'+base+'.6\n=     #'+t)+
 '<p class="note">This is a <strong>practical robot-operational gate</strong>, not a dedicated PROFINET data-quality bit. It prevents counting while the robot is out of Auto, its run chain is not OK, or it reports an execution error. It does not prove a part was picked or that every network packet is fresh.</p>')

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
 text=re.sub(r'<span class="revision">.*?</span>','<span class="revision">28 Sep · robot gate</span>',text,count=1)
 p.write_text(text);(root/'content.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
 sw=root/'sw.js';s=sw.read_text();s=re.sub(r"const CACHE='[^']+';","const CACHE='machine-reporting-robot-gate-v13-20260928';",s,count=1);sw.write_text(s)
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
