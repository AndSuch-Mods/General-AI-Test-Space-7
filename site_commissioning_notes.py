"""Field-confirmed commissioning notes layered onto the existing checklist.
Documentation only: preserves task IDs, saved progress, 66-network reference and 12-field schema.
"""
from pathlib import Path
from html import escape
import copy,json,re,os

ROOT=Path(__file__).parent
BUILD='2026-09-29-field-confirmed-mm456-v14'
PTC='https://support.ptc.com/help/kepware/drivers/en/kepware/drivers/SIEMENSTCPIPETHERNET/Standard_S7_300_400_Item_Syntax.html'

def code(x): return '<code>'+escape(str(x))+'</code>'
def steps(*xs): return '<ol>'+''.join('<li>'+x+'</li>' for x in xs)+'</ol>'
def panel(ident,title,body): return '<details class="small manual-panel" id="'+ident+'"><summary>'+escape(title)+'</summary><div class="manual-panel-body">'+body+'</div></details>'
def table(head,rows):
 return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+escape(h)+'</th>' for h in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'

MM6_ROWS=[
 ('PreviousCycleSeconds','Float',0,'REAL'),
 ('BetweenCycleSeconds','Float',4,'REAL'),
 ('PreviousBetweenSeconds','Float',8,'REAL'),
 ('CyclesThisHour','Long',12,'DINT'),
 ('CyclesPreviousHour','Long',16,'DINT'),
 ('CyclesToday','Long',20,'DINT'),
 ('CyclesPreviousDay','Long',24,'DINT'),
 ('DayShiftCurrent','Long',28,'DINT'),
 ('DayShiftPrevious','Long',32,'DINT'),
 ('NightShiftCurrent','Long',36,'DINT'),
 ('NightShiftPrevious','Long',40,'DINT'),
 ('TotalCompleted','Long',44,'DINT'),
]

def mm6_address_table():
 rows=[]
 for name,kep,off,s7 in MM6_ROWS:
  rows.append((code(name),kep,str(off),code('%DB56.DBD'+str(off)),code('DB56,'+s7+str(off))))
 return table(['Tag','Kepware type','Byte','TIA absolute','Kepware item'],rows)

def clock_hmi(m):
 return panel('field-clock-'+m,'Clock + HMI parity: hunt the template before copying time logic',
  '<p><strong>Goal:</strong> the reporting hour/day/shift logic and the operator display must use the same plant-local time. Do not compensate by changing the real shift boundaries.</p>'+
  steps(
   'First check <strong>'+m+' CPU → Online & diagnostics → Functions → Set time</strong>. Compare Module time with a known-correct local clock. Record whether a cold reboot changes Module time before editing any reporting rung.',
   'In the HMI project, search for <strong>DateTimeField</strong>, <strong>Systemzeit</strong>, <strong>DB_Uhrstellen</strong>, and <strong>Uhrstellen</strong>. If the clock object is gray on ordinary screens, go to <strong>HMI_RT → Screen management → Templates</strong>. On MM6 the real date/time objects were on a later <strong>Template</strong> page and were inherited by the normal screens.',
   'Select each template Date/Time field → <strong>Properties → General</strong>. If <strong>Display system time</strong> is checked, the object shows the HMI/Windows clock and can ignore the PLC process value. For a PLC-master display, uncheck it, keep <strong>Mode = Output</strong>, and bind <strong>Process value</strong> to the verified PLC time tag.',
   'Open <strong>HMI_RT → Connections</strong> and inspect <strong>HMI time synchronization mode</strong>. Record the value; do not assume it. MM6 was found at <strong>None</strong>. An unexpected <strong>Master</strong> setting can make Runtime push HMI time toward the PLC at startup; use only a deliberately reviewed PLC-master arrangement.',
   'Cross-reference the HMI time tag into the PLC. On MM6, <code>DB_Uhrstellen_S7_Systemzeit</code> mapped to <code>"DB_Uhrstellen".S7_Systemzeit</code> at <code>%DB155.DBX36.0</code>, and its writer was traced to <code>FC_Uhr stellen [FC53]</code>. <strong>Do not assume DB155 or FC53 on '+m+'</strong>; search the actual target.',
   'If the target has an HMI-to-PLC time write such as <strong>WR_SYS_T</strong>, decide deliberately whether it belongs. The MM6 site build was changed to one-way PLC/reporting time → HMI display so the HMI could not overwrite the PLC clock. Do not delete a target write path until its caller and purpose are cross-referenced.',
   'For a legacy WinLC/S7-300/400 target, do not paste MM6 <strong>RD_LOC_T/DTL</strong> logic blindly. Use the target-supported clock instruction and prove the resulting local hour/date against the same HMI template display before enabling shift counts.',
   'After any clock/display change, power-cycle once, then recheck Module time, the PLC time tag, the HMI display, and which shift counter increments. If only the HMI display is wrong, fix the template/source; do not offset 06:30/17:00 shift boundaries.'
  )+
  '<p class="note"><strong>MM6 field lesson:</strong> the inherited template and the “Display system time” checkbox were the hidden part. Look there early on MM4/MM5 instead of assuming the visible screen owns the clock object.</p>')

def donor_delta(m):
 return panel('field-donor-'+m,'Current MM6 commissioning deltas to carry into a compatible donor',
  steps(
   'Keep the same five reporting inputs. For the MM4/MM5 reference family the event pair remains <code>DB98.DBX112.7</code> and <code>DB94.DBX29.4</code>. The robot operating gate is expected to use <code>I500.4 AutoOn</code> AND <code>I500.5 RunChainOK</code> AND NOT <code>I500.6 ExecutionError</code>; verify TRUE / TRUE / FALSE through a complete live cycle before commissioning.',
   'Production eligibility uses <code>M50.2</code> OR <code>M50.3</code>. The class-1 reporting-abort source is <code>DB20.DBX0.1</code>. These are reads only; do not force or rewrite the original machine bits.',
   'The current MM6 site build also has a <strong>known-idle startup arm</strong>: if reporting is valid, production-eligible, State = 0, RobotPermit is TRUE now and last scan, CloseCommand is FALSE now and last scan, and LowSeen is FALSE, MOVE 1 into State. This lets the first real cycle after a normal idle startup count instead of always consuming one synchronization cycle.',
   'If the machine powers up in an uncertain/mid-cycle condition, keep the existing low→high robot-permit synchronization behavior. Do not force State = 1 just to make the first count appear.',
   'The current MM6 site build keeps a zero-offset clock-correction stage as a deliberate hook. Leave the correction at zero when the PLC clock is correct. Do not create a fixed offset merely to hide an HMI display problem.'
  )+
  '<p class="note">Copy the <strong>behavior</strong> only after the target CPU/instruction set is confirmed. MM4/MM5 may require a legacy implementation even when the machine sequence and HMI template are nearly identical.</p>')

def kepware_mm(m,ident):
 report='CSI_Report_'+m
 if m=='MM6':
  return panel(ident,'MM6 field-confirmed Kepware addresses — DB56',
   '<p><strong>Confirmed from the running TIA watch table:</strong> '+code(report)+' = <strong>DB56</strong>. The TIA absolute address is shown beside the actual Kepware item string.</p>'+
   mm6_address_table()+
   '<p>Kepware Standard S7 DB syntax is <code>DB&lt;number&gt;,&lt;S7 type&gt;&lt;byte offset&gt;</code>. Keep all 12 tags <strong>Read Only</strong>. <a href="'+PTC+'" target="_blank" rel="noopener noreferrer">PTC standard S7 item syntax</a>.</p>')
 return panel(ident,m+' Kepware: confirm the DB, then use the same 12 byte offsets',
  steps(
   'Open <strong>'+report+'</strong> in TIA and record the actual DB number assigned on this PLC. Do not reuse MM6 DB56 unless TIA on '+m+' actually says DB56.',
   'Verify byte 0 is PreviousCycleSeconds and byte 44 is TotalCompleted. All 12 members are four bytes wide in the compact layout.',
   'For each tag, the TIA absolute form is <code>%DB&lt;N&gt;.DBD&lt;byte&gt;</code>. The Kepware Standard S7 item is <code>DB&lt;N&gt;,REAL&lt;byte&gt;</code> for the first three seconds values and <code>DB&lt;N&gt;,DINT&lt;byte&gt;</code> for the counters.',
   'Enter the confirmed DB number in the live map below; the app will spell out both complete addresses. Create the tags under the '+m+' device, keep Client access Read Only, and prove PreviousCycleSeconds against TIA before bulk-adding the rest.'
  )+
  table(['Tag','Type','Byte'],[(code(n),t,str(o)) for n,t,o,_ in MM6_ROWS])+
  '<p><a href="'+PTC+'" target="_blank" rel="noopener noreferrer">PTC standard S7 item syntax</a></p>')

def mm6_site():
 return panel('field-mm6-site','MM6 field-confirmed reference for the next machines',
  '<p>This is the site-proven MM6 reference, not a replacement for the original 66-network authored guide.</p>'+
  steps(
   '<strong>Report DB:</strong> <code>CSI_Report_MM6 [DB56]</code>, standard/non-optimized, 12 retained fields / 48 bytes.',
   '<strong>Events:</strong> CloseCommand = <code>%DB98.DBX112.7</code>; RobotPermit = <code>%DB94.DBX29.6</code>.',
   '<strong>Mode:</strong> <code>M50.2</code> semiautomatic OR <code>M50.3</code> automatic.',
   '<strong>Robot operating gate:</strong> <code>I700.4 AutoOn</code> AND <code>I700.5 RunChainOK</code> AND NOT <code>I700.6 ExecutionError</code>; observed TRUE / TRUE / FALSE through a normal cycle.',
   '<strong>Abort reporting measurement:</strong> <code>DB20.DBX0.1</code>.',
   '<strong>Clock/HMI:</strong> operator clock objects were inherited from <strong>HMI_RT → Screen management → Templates → Template</strong>. “Display system time” had to be unchecked to make the PLC process value drive the display. HMI connection time synchronization mode was <strong>None</strong>.',
   '<strong>First cycle after restart:</strong> current site build includes the known-idle startup arm so a normal idle startup counts the first real cycle.'
  ))

def apply_notes(data):
 d=copy.deepcopy(data)
 for m in ('MM4','MM5'):
  g=next(x for x in d['groups'] if x['id']==m)
  adapt=next(t for t in g['tasks'] if t['id']==m+'-rollout-adapt')
  if 'id="field-clock-'+m+'"' not in adapt['body']:
   adapt['body'] += clock_hmi(m)+donor_delta(m)
  report=next(t for t in g['tasks'] if t['id']==m+'-rollout-report')
  report_marker='field-kepware-report-'+m
  if 'id="'+report_marker+'"' not in report['body']:
   report['body'] += kepware_mm(m,report_marker)
 mm6=next(x for x in d['groups'] if x['id']=='MM6')
 target=next(t for t in mm6['tasks'] if t['id']=='MM6-compact-call')
 if 'id="field-mm6-site"' not in target['body']:
  target['body'] += mm6_site()
 for m in ('MM4','MM5','MM6'):
  kg=next(x for x in d['kepware'] if x['id']=='K-'+m)
  kt=next(t for t in kg['tasks'] if t['id']=='K-'+m+'-compact-tags')
  marker='field-kepware-map-'+m
  if 'id="'+marker+'"' not in kt['body']:
   kt['body'] += kepware_mm(m,marker)
 d['field_notes_version']=BUILD
 return d

def finalize_site_notes(root=ROOT):
 if os.environ.get('CSI_SKIP_SITE_NOTES')=='1': return
 root=Path(root); p=root/'index.html'; txt=p.read_text()
 pos=txt.index('const DATA=')+len('const DATA=')
 base,n=json.JSONDecoder().raw_decode(txt[pos:])
 d=apply_notes(base)
 assert [t['id'] for g in base['groups']+base['kepware'] for t in g['tasks']] == [t['id'] for g in d['groups']+d['kepware'] for t in g['tasks']]
 assert d['schema']==base['schema']
 txt=txt[:pos]+json.dumps(d,ensure_ascii=False).replace('</','<\\/')+txt[pos+n:]
 txt=re.sub(r'<span class="revision">.*?</span>','<span class="revision">29 Sep · MM6 proven / MM4–MM5 field guide</span>',txt,count=1)
 p.write_text(txt); (root/'content.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
 sw=root/'sw.js'; s=sw.read_text(); s=re.sub(r"const CACHE='[^']+';","const CACHE='machine-reporting-field-notes-v14-20260929';",s,count=1); sw.write_text(s)
 print('Added field-confirmed MM6 addresses and detailed MM4/MM5 clock/HMI commissioning notes.')

def install(root=ROOT):
 root=Path(root); p=root/'build_html.py'; s=p.read_text()
 if 'from site_commissioning_notes import finalize_site_notes' not in s:
  s += '\nfrom site_commissioning_notes import finalize_site_notes\nfinalize_site_notes(R)\n'
  p.write_text(s)
 p=root/'AGENTS.md'; s=p.read_text()
 if '## Field-confirmed MM6 and MM4/MM5 commissioning delta' not in s:
  s += '''\n## Field-confirmed MM6 and MM4/MM5 commissioning delta\n\nsite_commissioning_notes.py is the final documentation overlay. It must not change task IDs, the 12-field schema, saved progress, or the 66-network reference. MM6 is field-confirmed as CSI_Report_MM6 DB56; show both TIA absolute %DB56.DBDx addresses and Kepware DB56,REALx / DB56,DINTx items. MM4/MM5 must still record their own DB numbers. The detailed field guide must include the HMI template lesson: inherited date/time objects can be gray on normal screens; inspect HMI_RT -> Screen management -> Templates -> Template, turn off Display system time when using a PLC process value, and verify HMI connection time synchronization mode. MM6 was None. Do not copy MM6 DB155/FC53/RD_LOC_T assumptions blindly to legacy MM4/MM5. Preserve the known-idle startup-arm behavior as a site delta so the first real cycle can count after a normal idle restart.\n'''
  p.write_text(s)

if __name__=='__main__':
 import sys
 if '--install' in sys.argv: install()
 else: finalize_site_notes()
