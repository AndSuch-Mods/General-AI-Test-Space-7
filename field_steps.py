"""Concrete read-only field steps. Applied by build_html.py; no PLC code changes."""
from html import escape

CREATE = 'https://docs.tia.siemens.cloud/r/en-us/v20/testing-the-user-program/testing-with-the-watch-table/creating-and-editing-watch-tables/creating-a-watch-table'
MONITOR = 'https://docs.tia.siemens.cloud/r/en-us/v20/testing-the-user-program/testing-with-the-watch-table/monitoring-tags-in-the-watch-table/introduction-to-monitoring-tags-in-the-watch-table'


def watch_guide(m):
    name = m['id']
    rows = [
        (m['start'], 'Close command', 'The candidate start of your cycle timer.'),
        (m['output'], 'Associated close output', 'Compare with the close-command bit; this is not motion feedback.'),
        (m['end'], 'Robot close permission', 'The candidate end of your cycle, after permission has gone low and returned high.'),
        (m['raw'], 'Raw robot input', 'Compare with the robot-permission DB bit.'),
        ('DB200.DBX38.2', 'Servo hydraulic selection', 'Read TRUE / 1 before adopting the Servo closing-command candidate.'),
        ('DB200.DBX49.3', 'EUROMAP interface selection', 'Read whether the traced robot-interface branch is selected.'),
    ]
    table = '<div class="table-scroll"><table><thead><tr><th>Type in Address</th><th>Optional Comment</th><th>Why it is here</th></tr></thead><tbody>'
    table += ''.join('<tr><td><code>'+escape(a)+'</code></td><td>'+escape(b)+'</td><td>'+escape(c)+'</td></tr>' for a,b,c in rows)
    table += '</tbody></table></div>'
    warning = ''
    if name == 'MM6':
        warning = '<div class="callout"><strong>MM6 is different.</strong> Do not enter DB94.DBX29.4 as the end signal; that is a reserve input here. I705.7 is named RobotInMouldNotClear, but the recovered code copies it without inversion into the positive permission. Observe what happens. Do not add NOT or change the original program based on the name.</div>'
    return {
        'id': 'watch-'+name,
        'title': name+': already online in OB1? Start here',
        'summary': 'Exact clicks and six watch-table rows. Read only; no download.',
        'html': f'''<p><strong>Goal:</strong> verify which bit starts your cycle timer and which bit ends it. You are not creating timers or changing the running program yet.</p>
<div class="callout"><strong>Where you are:</strong> TIA Portal, online with {name}, with OB1 open. The networks in the middle belong to OB1. The declaration/tag grid at the top belongs to that block. Neither is where you add a watch table. Leave both unchanged.</div>
<h3>1. Open the watch-table folder in TIA</h3>
<ol><li>Look at the <strong>Project tree on the left</strong>, not the networks in the middle. Find the PLC node that contains the OB1 you already opened. Its project name might be a machine number, WinLC RTX, or another configured name; it does not have to say {name}.</li>
<li>Under that same PLC, find <strong>Watch and force tables</strong>. It is a sibling of <strong>Program blocks</strong>, not a network inside OB1. Collapse Program blocks to shorten the tree if necessary. Do not select the HMI or another PLC.</li>
<li>Expand <strong>Watch and force tables</strong>, then double-click <strong>Add new watch table</strong>. A table opens with columns such as Name, Address, Display format, Monitor value and Modify value. This is a list of existing values to observe, not a new set of PLC variables.</li>
<li>Optional: select the new Watch table_1 entry in the tree, press F2, and rename it <code>{name}_Cycle_Check</code>. Keep the default name if renaming is inconvenient.</li></ol>
<pre>Your project\n  Your {name} PLC\n    Program blocks\n      OB1                  (leave unchanged)\n    Watch and force tables\n      Add new watch table  (double-click this)</pre>
<p>If that folder is missing, stop and capture the left-hand tree for troubleshooting. Do not create a PLC, change a device, or download anything to make the folder appear.</p>
<h3>2. Enter these six rows</h3>
<p>Click the first blank cell in the <strong>Address</strong> column. Type the first address below and press Enter. Repeat in the next row for each address. Do not type the explanatory text into Name. If TIA fills Name with an existing German symbol, leave it alone. These six entries are Boolean bits, shown as TRUE/FALSE or 1/0.</p>
{table}
<p>Keep <strong>Modify value</strong> blank. You are not defining new PLC tags. If TIA adds a leading percent sign to an address, that is normal. If a row is rejected, record its exact error rather than changing DB settings. Press Ctrl+S to save the watch table in your laptop project. <strong>No PLC download is required for this read-only step.</strong></p>
<h3>3. Turn on live readings</h3>
<ol><li>In the toolbar directly above the watch-table grid, find <strong>Monitor all</strong>, usually the glasses icon. Hover over the button to read its tooltip before clicking.</li><li>Click <strong>Monitor all</strong> once. Read the <strong>Monitor value</strong> column. Since you are already online, values should appear; blank/error values are not FALSE.</li><li>Do not click Modify, Force, Modify to 0, Modify to 1, or Enable peripheral outputs. Do not accept a download prompt for this task.</li></ol>
<h3>4. Read the two configuration rows first</h3>
<p>Write down the live values of <code>DB200.DBX38.2</code> and <code>DB200.DBX49.3</code>. They tell us whether the hydraulic and robot-interface paths used to choose these addresses apply. For this proposed pair, we expect both TRUE / 1. This does not by itself prove the physical timing.</p>
<p><strong>If either is FALSE, do not change it.</strong> Record the result and pause selection of the timer bits. For a FALSE Servo selector, you may add <code>DB200.DBX38.0</code>, <code>DB200.DBX38.1</code> and <code>DB200.DBX38.3</code> as three more read-only rows to identify Bucher, A_Line or Vickers. That result calls for the correct branch, not a selector change.</p>
{warning}
<h3>5. Watch one normal cycle with the operator</h3>
<ol><li><strong>At closing start:</strong> watch <code>{m['start']}</code>. It should change from FALSE to TRUE when the machine commands the mold/plates to close. Compare <code>{m['output']}</code>; the two are assigned together in the traced Servo network, though a polling table is not a simultaneous trace.</li>
<li><strong>During robot access:</strong> watch <code>{m['end']}</code>. It needs to become FALSE during the cycle. It may already be FALSE at the accepted start; do not require that it begins TRUE.</li>
<li><strong>When the robot is done and clear:</strong> watch <code>{m['end']}</code> return to TRUE. Check that this happens at the physical event you intend to use as cycle end. Compare <code>{m['raw']}</code>, which feeds that permission bit.</li>
<li>Record what you actually saw. If a change is too fast for the table, record <em>not captured</em>, not <em>confirmed</em>. A watch table can miss short transitions. Do not force the machine signals to test them.</li></ol>
<p>The candidate sequence is: <strong>closing-command rising edge starts timing; robot permission has been observed low; its later return high finishes timing.</strong> A permission already high at closing start must not finish a new cycle immediately.</p>
<h3>6. Save the result in this web app</h3>
<p>Now switch from TIA to <strong>this web app</strong>. Open <strong>Programming → {name} programming</strong>. The tasks about configuration, closing start and robot return have <strong>Details and notes</strong> sections. Record your observations there. Check off only the observations you have actually verified.</p>
<p><strong>Stop here for this stage.</strong> Your finished result is a saved watch table plus observed signal behavior. Do not add networks, import SCL, or download yet. The automatic-mode, communication-valid and abort inputs are a separate, still-unresolved mapping task.</p>
<details class="subfolder"><summary>Why the old instructions mentioned FC200, FC166 and FC452</summary><div class="instruction-body"><p>Those are existing function blocks, not tasks you have to perform. FC452 contains the Servo close-output assignment. FC200 maps the raw robot input into the DB. FC166 copies the robot permission onward. Their code provided the offline evidence for the addresses above. <strong>You do not need to follow them or run a cross-reference search to do this watch-table check.</strong> Cross-reference investigation is only needed if your live project or observed behavior disagrees with the saved analysis. Do not confuse FC166 with FC160.</p></div></details>
<p class="muted">TIA operations: <a href="{CREATE}" target="_blank" rel="noopener noreferrer">Siemens watch-table creation</a> and <a href="{MONITOR}" target="_blank" rel="noopener noreferrer">monitoring commands</a>. Online documentation shown is V20; use your installed V15/V16 help if a label differs. Machine addresses come from the earlier archive analysis and still require live verification.</p>'''
    }


def apply(data):
    """Idempotent text-only update. Preserve task IDs, state keys and SCL files."""
    before = [t['id'] for g in data['machines']+data['kepware'] for t in g['tasks']]
    by_id = {x['id']: x for x in data['instructions']}
    find = by_id['find-code']
    find.update(title='Find the right screen: TIA versus this web app',
        summary='Already online in OB1? Use the machine-specific watch steps, not a code search.',
        html='''<p><strong>Two different places:</strong> <em>Programming → MM5 programming</em> is a section in this web app. It is not a Siemens folder. In TIA, work under the PLC in the left-hand Project tree.</p><p>OB1 is the main cyclic block. Its networks and the declaration grid at its top are not where you add a watch table. Leave OB1 unchanged for the signal check.</p><p>Open the exact guide for the machine you are connected to:</p><p><a href="#i-watch-MM4">MM4: already online in OB1? Start here</a><br><a href="#i-watch-MM5">MM5: already online in OB1? Start here</a><br><a href="#i-watch-MM6">MM6: already online in OB1? Start here</a></p><p>Each guide gives the clicks, the addresses to type, the expected readings, and when to stop. You do not need to search FC200/FC166/FC452 to start. They are evidence locations in the existing program.</p>''')
    data['instructions'] = [x for x in data['instructions'] if not x['id'].startswith('watch-MM')]
    at = next(i for i,x in enumerate(data['instructions']) if x['id']=='find-code')+1
    data['instructions'][at:at] = [watch_guide(m) for m in data['machines']]
    for m in data['machines']:
        for t in m['tasks']:
            suffix=t['id'][len(m['id'])+1:]
            if suffix in ('config','start','finish','qualify'):
                t['topic']='watch-'+m['id']
            if suffix=='config':
                t['title']='Create the watch table; read the Servo and EUROMAP selectors'
                t['detail']='In TIA: this PLC → Watch and force tables → Add new watch table. Open instructions for the six exact rows. Record DB200.DBX38.2 and DB200.DBX49.3. Never change these selector values.'
            elif suffix=='start':
                t['title']='Watch '+m['start']+' turn on when closing starts'
                t['detail']='With the verified Servo selection, monitor '+m['start']+' and '+m['output']+' during a normal operator-run cycle. Check this only when the closing-command edge matches the intended timer start. No search or program edit is needed.'
            elif suffix=='finish':
                t['title']='Watch '+m['end']+' go low, then high when the robot clears'
                t['detail']='Monitor '+m['end']+' and '+m['raw']+'. Record the low state during the cycle and the return to TRUE when the robot is done and clear. A startup-high value alone is not a completed cycle.'
            elif suffix=='qualify':
                t['title']='Resolve the remaining auto, communication and abort mappings'
                t['detail']='Not supplied by the six-row check. Leave this task unchecked and the new observer disabled until these exact inputs are traced and verified. Do not guess addresses or set them permanently TRUE. Bring the live project or relevant screen for a separate mapping review.'
    after = [t['id'] for g in data['machines']+data['kepware'] for t in g['tasks']]
    assert before==after, 'Task IDs changed'
    return data
