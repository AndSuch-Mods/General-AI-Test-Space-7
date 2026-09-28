"""Clarify existing retention locations. No PLC recipe or completed-step changes."""
from copy import deepcopy
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import re

SPEC_BLOB = 'bfa2826e70716115a8e38cfa1a9470cb3ab0c444'

STEP5_NOTE = '''<div class="note" id="retention-step5"><strong>Continue here; steps 1–4 are unchanged.</strong> Leave all 12 tags in <strong>CSI_Report</strong> retained together. The local variables introduced below go in the upper grid of <strong>CSI_Reporting</strong>, the LAD function block. Its internal memory is separate from CSI_Report. Do not move or add tags to the reporting DB.</div>'''

STEP6_NOTE = '''<p><strong>Where the saved-period tags belong:</strong> <code>HourSaved</code>, <code>DaySaved</code>, <code>DayShiftSaved</code> and <code>NightShiftSaved</code> are local <strong>Static</strong> rows in <strong>CSI_Reporting</strong>, not members of CSI_Report. Set their Retain choices in that FB. Use any rows you already entered; do not create duplicates. The 12 reporting fields stay retained together.</p>'''

RETENTION_BODY = '''<p><strong>No new design or extra reporting DB is needed.</strong> Keep the code already entered. The existing plan uses these separate blocks:</p>
<div class="table-wrap"><table><thead><tr><th>Block</th><th>What it contains</th><th>Access / retention</th></tr></thead><tbody>
<tr><td><code>CSI_Report</code></td><td>The 12 readings Kepware reads</td><td>Standard (non-optimized); all 12 retained together. Leave them as entered.</td></tr>
<tr><td><code>CSI_Reporting</code></td><td>The LAD logic and its local variable declarations</td><td>Optimized FB; choose Retain separately in this block's Static declaration rows.</td></tr>
<tr><td><code>CSI_Reporting_DB</code></td><td>The instance memory belonging to that FB</td><td>Created for CSI_Reporting in the OB1-call step. TIA derives its members/access from the FB. Do not build a second copy of its variables.</td></tr>
</tbody></table></div>
<ol>
<li><strong>Leave CSI_Report alone.</strong> Keep Optimized block access OFF and Retain ON for all 12 fields. Do not try to clear individual Retain boxes here, split its fields, or change their order. Its Kepware offsets stay unchanged.</li>
<li>In the left Project tree, double-click <strong>CSI_Reporting</strong>, the <strong>FB</strong> containing your ladder. Do not open CSI_Report or CSI_Reporting_DB for the individual retention choices. In the upper declaration grid, expand <strong>Static</strong>.</li>
<li>For <strong>HourSaved, DaySaved, DayShiftSaved and NightShiftSaved</strong>, choose <strong>Retain</strong> (Retain ON) in that FB's Retain column. Keep their start/default values at <strong>-1</strong>. They remember which period each saved count belongs to. Use the existing rows, not duplicate tags.</li>
<li>For every other Static row choose <strong>Non-retain</strong> (Retain OFF). In particular, keep <strong>Initialized = FALSE</strong>, and <strong>State, CycleMs and WaitMs = 0</strong> as start/default values. Use direct Retain/Non-retain choices, not <strong>Set in IDB</strong>. Temp variables have no retention choice.</li>
<li>Save and compile the new blocks. Review the real download preview for initialization/STOP effects before loading. Do not test this by cycling production power or changing an existing machine block.</li>
</ol>
<details class="small manual-panel" id="retention-editor-help"><summary>If the Retain controls still act together</summary><div class="manual-panel-body"><p>Check the block name at the top: it must be <strong>CSI_Reporting [FB…]</strong>, not <strong>CSI_Report [DB…]</strong> or its instance DB. Right-click that new FB in the tree → <strong>Properties → Attributes</strong> and check whether <strong>Optimized block access</strong> is already enabled, as the creation step specifies.</p><p>If it is not enabled, stop and check that property before changing anything. Do not rebuild your first four steps or toggle the report DB. Changing an already-loaded FB's access type needs a separate compile/download-impact review.</p></div></details>
<p><strong>On a normal restart:</strong> non-retained Initialized becomes FALSE. The existing first-call and reset networks clear CycleMs, WaitMs, State and the retained <strong>BetweenCycleSeconds</strong> display. Retain means a value survives the restart; it does not prevent the ladder from writing zero to that live field. PreviousCycleSeconds, PreviousBetweenSeconds and the production counts are not cleared by that reset. The saved-period keys still allow normal hour/day/shift rollover when appropriate.</p>
<p>No extra setup DB, startup-OB call or replacement ladder is added. The actual PLC has not been restarted or tested here.</p>
<p class="muted">Siemens references: <a href="https://docs.tia.siemens.cloud/r/en-us/v21/programming-data-blocks/setting-retentivity/setting-retentivity-in-a-global-data-block" target="_blank" rel="noopener noreferrer">global DB retention</a> and <a href="https://docs.tia.siemens.cloud/r/en-us/v21/declaring-the-block-interface/rules-for-declaring-the-block-interface/setting-the-retentivity-of-local-tags" target="_blank" rel="noopener noreferrer">FB variable retention</a>. Use the installed target help for label differences.</p>'''

class Rungs(HTMLParser):
    def __init__(self):
        super().__init__(); self.active = False; self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == 'pre' and 'lad-diagram' in dict(attrs).get('class', '').split():
            self.active = True; self.text.append('')
    def handle_endtag(self, tag):
        if tag == 'pre': self.active = False
    def handle_data(self, text):
        if self.active: self.text[-1] += text

def clarify_retention(previous):
    """Documentation only. Preserve task order, first four steps, schema and rungs."""
    d = deepcopy(previous)
    old = next(g for g in previous['groups'] if g['id'] == 'MM6')
    mm6 = next(g for g in d['groups'] if g['id'] == 'MM6')
    assert [t['id'] for t in old['tasks'][:4]] == [
        'MM6-config','MM6-compact-report','MM6-compact-fb','MM6-compact-section-1']
    ids = {t['id']: t for t in mm6['tasks']}
    ids['MM6-compact-section-2']['body'] = STEP5_NOTE + ids['MM6-compact-section-2']['body']
    ids['MM6-compact-section-3']['body'] = STEP6_NOTE + ids['MM6-compact-section-3']['body']
    ids['MM6-compact-retention']['body'] = RETENTION_BODY
    assert mm6['tasks'][:4] == old['tasks'][:4], 'Completed steps changed'
    assert [t['id'] for t in mm6['tasks']] == [t['id'] for t in old['tasks']]
    assert d['schema'] == previous['schema'] and len(d['schema']) == 12
    assert d['kepware'] == previous['kepware']
    for before, after in zip(old['tasks'], mm6['tasks']):
        a, b = Rungs(), Rungs(); a.feed(before['body']); b.feed(after['body'])
        assert a.text == b.text, ('Rung drawing changed', before['id'])
        for key in ('title','fields','watch','map'):
            assert before.get(key) == after.get(key), ('Task metadata changed', before['id'], key)
    return d

def finalize_retention(root):
    root = Path(root)
    raw = (root/'compact_spec.py').read_bytes()
    blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    assert blob == SPEC_BLOB, 'Ladder recipe changed: review this documentation-only update first'
    p = root/'index.html'; text = p.read_text()
    text = re.sub(r'<span class="revision">.*?</span>', '<span class="revision">28 Sep · retention guide</span>', text, count=1)
    p.write_text(text)
    p = root/'sw.js'; text = p.read_text()
    text = re.sub(r"const CACHE='[^']+';", "const CACHE='machine-reporting-retention-guide-v10-20260928';", text, count=1)
    p.write_text(text)
    print('PASS retention clarification: first four tasks, all rungs, tag layout and Kepware map unchanged.')
