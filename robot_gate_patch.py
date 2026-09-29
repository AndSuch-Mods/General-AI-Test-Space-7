"""Apply the live-verified robot operational gate documentation to the current checklist source.
Documentation/source patch only. It does not connect to or modify a PLC.
"""
from pathlib import Path
import re

R=Path(__file__).parent

p=R/"input_notes.py"
s=p.read_text()
s=s.replace("BUILD='2026-09-28-input-sources-v12'","BUILD='2026-09-28-robot-operational-gates-v13'")

defs=r'''def definitions(m):
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

def production(m):'''
s=re.sub(r'def definitions\(m\):.*?\ndef production\(m\):',defs,s,flags=re.S)

watch=r'''def watch(m):
 robot=('I700.4','I700.5','I700.6')if m=='MM6'else('I500.4','I500.5','I500.6')
 return steps('In the existing watch table, add these read-only rows: '+code('M50.2')+', '+code('M50.3')+', '+code('DB20.DBX0.1')+', '+code(robot[0])+', '+code(robot[1])+', '+code(robot[2])+'. Leave Modify value blank.',
 'Automatic mode should show M50.3 TRUE; semiautomatic should show M50.2 TRUE. DB20.DBX0.1 should normally be FALSE without a class-1 stop fault.',
 'For the robot operational gate, expect AutoOn = TRUE, RunChainOK = TRUE and ExecutionError = FALSE through the complete normal cycle. MM6 has already been observed doing this; MM4/MM5 still need the same live check before commissioning.',
 'If any of those robot-status bits normally changes during the cycle, do not use the proposed RobotDataValid expression unchanged. Record the states/timestamps and revise the gate. Never force these bits.')

def diag(m):'''
s=re.sub(r'def watch\(m\):.*?\ndef diag\(m\):',watch,s,flags=re.S)

diag=r'''def diag(m):
 base='700'if m=='MM6'else'500'
 t='CSI_RobotDataValid_'+m
 live_note=('<strong>MM6 live check passed:</strong> I700.4 / I700.5 / I700.6 stayed TRUE / TRUE / FALSE through a complete normal cycle.'if m=='MM6'else'<strong>'+m+' archive mapping:</strong> I500.4 = AutoOn, I500.5 = RunChainOK, I500.6 = ExecutionError. Confirm TRUE / TRUE / FALSE through a real cycle before the live download.')
 return ('<p>'+live_note+'</p>'+steps(
  'In <strong>OB1 → upper declaration grid → Temp</strong>, append Name = '+code(t)+', Data type = <strong>Bool</strong>. Do not add this to CSI_Report.',
  'Immediately before the CSI reporting CALL, add the four-line STL expression below. It reads the existing robot-status inputs and writes only the new OB1 Temp bit.',
  'Connect <strong>RobotDataValid := '+code('#'+t)+'</strong> on the reporting CALL.',
  'Before commissioning '+m+', watch the three source inputs through a normal robot cycle. They must remain AutoOn TRUE, RunChainOK TRUE and ExecutionError FALSE. If not, stop and revise this reporting gate.')+pre('CLR\\nA     I'+base+'.4\\nA     I'+base+'.5\\nAN    I'+base+'.6\\n=     #'+t)+
 '<p class="note">This is a <strong>practical robot-operational gate</strong>, not a dedicated PROFINET data-quality bit. It prevents counting while the robot is out of Auto, its run chain is not OK, or it reports an execution error. It does not prove a part was picked or that every network packet is fresh.</p>')

def body(m):'''
s=re.sub(r'def diag\(m\):.*?\ndef body\(m\):',diag,s,flags=re.S)
s=s.replace('28 Sep · input meanings','28 Sep · robot gate')
s=s.replace('machine-reporting-input-notes-v12-20260928','machine-reporting-robot-gate-v13-20260928')
p.write_text(s)

p=R/"tests/input_notes_test.py"
s=p.read_text()
s=s.replace(" ok(m+' distinguishes an unresolved existing RobotDataValid mapping','No existing one-bit source verified' in text)",
""" status=['I700.4','I700.5','I700.6']if m=='MM6'else['I500.4','I500.5','I500.6']
 ok(m+' contains the practical robot operational gate addresses',all(x in text for x in status) and 'RunChainOK' in text and 'ExecutionError' in text)""")
old=""" page.locator('#inputs-MM6-valid>summary').click();page.locator('#inputs-MM6-diag-build>summary').click()
 ok('Read-only diagnostic is conditional on actual hardware confirmation','I705.7' in page.locator('#inputs-MM6-valid').inner_text() and 'verified' in page.locator('#inputs-MM6-diag-build').inner_text())
 ok('Diagnostic recipe requires successful return and Good bit',all(s in page.locator('#inputs-MM6-diag-build').inner_text() for s in ['==I','IOState.%X0']))"""
new=""" page.locator('#inputs-MM6-valid>summary').click()
 mm6valid=page.locator('#inputs-MM6-valid').inner_text()
 ok('MM6 operational gate shows the watched robot states and STL expression',all(x in mm6valid for x in ['I700.4','I700.5','I700.6','AN    I700.6','TRUE / TRUE / FALSE']))
 page.get_by_role('button',name='MM4',exact=True).click();page.locator('#how-MM4-rollout-adapt>summary').click();page.locator('#inputs-MM4-valid>summary').click()
 mm4valid=page.locator('#inputs-MM4-valid').inner_text()
 ok('MM4 uses the same robot gate roles at the archived 500-series addresses',all(x in mm4valid for x in ['I500.4','I500.5','I500.6','AN    I500.6']))
 page.get_by_role('button',name='MM5',exact=True).click();page.locator('#how-MM5-rollout-adapt>summary').click();page.locator('#inputs-MM5-valid>summary').click()
 mm5valid=page.locator('#inputs-MM5-valid').inner_text()
 ok('MM5 uses the same robot gate roles at the archived 500-series addresses',all(x in mm5valid for x in ['I500.4','I500.5','I500.6','AN    I500.6']))
 ok('No obsolete GET_DIAG construction is presented in the current input guide',page.locator('#inputs-MM6-diag-build').count()==0)"""
if old in s:
 s=s.replace(old,new)
elif new not in s:
 raise RuntimeError('input_notes_test.py is neither pre-patch nor already patched')
s=s.replace("scope='Documentation/DOM checks; diagnostic mapping not hardware-tested.'","scope='Documentation/DOM checks; MM6 operational gate live-observed, MM4/MM5 archive-mapped but not live-verified.'")
p.write_text(s)

p=R/"input_mapping_evidence.md"
s=p.read_text()
section=r'''## RobotDataValid: practical robot-operational gate

The reporting input name RobotDataValid is being used as a practical robot-operational qualification, not as a claim of PROFINET packet-quality or submodule diagnostic health.

MM6 uses these existing robot statuses:

| Address | Existing name | Meaning |
|---|---|---|
| I700.4 | AutoOn | Robot automatic-mode status |
| I700.5 | RunChainOK | Robot run-chain status |
| I700.6 | ExecutionError | Robot program execution error |

On 28 September 2026 these MM6 values were observed live as TRUE / TRUE / FALSE through a complete normal robot cycle. The reporting gate used for MM6 is:

    RobotDataValid = I700.4 AND I700.5 AND NOT I700.6

The supplied PF1000723 MM4/MM5 reference archive contains the same three roles at the 500-series robot input addresses. Its HMI tag map identifies:

| Address | Existing name | Meaning |
|---|---|---|
| I500.4 | AutoOn | Robot automatic-mode status |
| I500.5 | RunChainOK | Robot run-chain status |
| I500.6 | ExecutionError | Robot program execution error |

FC17 saved network 2 connects I500.4 / I500.5 / I500.6 into the legacy ABB controller call (FB2 / DB65), so these addresses are supported by the archive rather than inferred only from the MM6 offset. The proposed MM4/MM5 reporting gate is:

    RobotDataValid = I500.4 AND I500.5 AND NOT I500.6

MM4 and MM5 still require a live watch before commissioning: AutoOn and RunChainOK should remain TRUE and ExecutionError should remain FALSE through a normal cycle. If that waveform differs, revise the reporting gate rather than forcing any input.

This gate does not prove the robot picked a part, does not prove every communications packet is fresh, and is not a safety function. It only prevents the reporting observer from accepting events while the robot is out of Auto, its run chain is not OK, or the controller reports an execution error.

'''
s=re.sub(r'## RobotDataValid:.*?(?=## Provenance)',section,s,flags=re.S)
p.write_text(s)

p=R/"AGENTS.md"
s=p.read_text()
if '## Current robot operational gate' not in s:
 s += r'''
## Current robot operational gate

The current reporting qualification intentionally uses robot operating-state inputs, not a claimed PROFINET quality bit. MM6 uses I700.4 AutoOn AND I700.5 RunChainOK AND NOT I700.6 ExecutionError; those states were observed live TRUE/TRUE/FALSE through one normal cycle. PF1000723 maps the same roles to I500.4/I500.5/I500.6 for MM4/MM5; require the same live cycle check before commissioning. Keep the FB input name RobotDataValid for continuity, but describe it as a practical operational gate. Do not present it as packet freshness, safety integrity, or proof of a successful pick. No 66-network timing/counting logic or 12-field report layout changes are part of this update.
'''
p.write_text(s)

print("robot gate patch applied")
