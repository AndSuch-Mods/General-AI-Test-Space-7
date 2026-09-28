"""One-time reviewed update: no setup DB; selective state retention.
Run before build_html.py. Source changes are prepared before writing any file.
This is a guide/model change, not a Siemens compiler or PLC write.
"""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parent
VERSION = '2026-09-28-compact-autostart-v9'
EXPECTED = {
    'compact_spec.py': 'd1f84ac8ce64215286648b073686e246771559cb',
    'compact_steps.py': 'ef71cd524fe90e159146422dbdb421682bc4f9e4',
    'tests/compact_test.py': '147067aefda1ae79f85cceca72f616e69ebf0241',
    'tests/compact_browser_test.py': '8e15f29a8af8277027c133a3f546dccf5754b6fe',
}
def once(text, old, new):
    assert text.count(old) == 1, ('Expected one matching edit', old[:160], text.count(old))
    return text.replace(old, new, 1)

def install(root=ROOT):
    root = Path(root)
    if VERSION in (root / 'compact_spec.py').read_text():
        print('Automatic restart update already installed.')
        return
    texts = {}
    for name, expected in EXPECTED.items():
        raw = (root/name).read_bytes()
        sha = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        assert sha == expected, ('Concurrent source change: review before updating', name, sha)
        texts[name] = raw.decode('utf-8')
    s = texts['compact_spec.py']
    s = once(s, "BUILD='2026-09-28-compact-day-night-v8'", "BUILD='"+VERSION+"'")
    s = once(s, 'def S(n):return \'"CSI_Setup".\'+n\n', '')
    s = once(s, "O(N('#Initialized'),S('StartupPending'))", "N('#Initialized')")
    s = once(s, "A(S('Enable'),S('WiringReviewed'),'%DB200.DBX38.2'", "A('%DB200.DBX38.2'")
    s = once(s, "'Allow monitoring only with valid reviewed inputs'", "'Run automatically when the real inputs and schedule are valid'")
    s = once(s, ",bit(S('StartupPending'),False)", '')
    s = once(s, "move('#WaitMs',0),bit('#LowSeen',False),note='This does not reset any held time or production counter.'", "move('#WaitMs',0),bit('#LowSeen',False),move(R('BetweenCycleSeconds'),0.0),note='First call after startup clears only live timing. Held times and counts are not cleared here.'")
    # Retained period identities prevent a reboot after a backwards clock correction
    # from crediting an old hour/day into a later retained count.
    s = once(s, "C('#ClockMinute','>=','#LastClockMinute'),C('#Weekday'", "C('#ClockMinute','>=','#LastClockMinute'),C('#HourKey','>=','#HourSaved'),C('#DayNumber','>=','#DaySaved'),C('#Weekday'")
    s = once(s, 'BLOCKS={BLOCK.name:BLOCK}', "RETAINED_KEYS=('HourSaved','DaySaved','DayShiftSaved','NightShiftSaved')\nfor row in BLOCK.rows:\n if row['section']=='Static':row['retain']=row['name'] in RETAINED_KEYS\nBLOCKS={BLOCK.name:BLOCK}")
    assert 'CSI_Setup' not in s and 'StartupPending' not in s
    texts['compact_spec.py'] = s

    s = texts['compact_steps.py']
    start = s.index('def rowtable(rows):')
    end = s.index('\ndef action(a):', start)
    s = s[:start]+'''def rowtable(rows):
 return table(['Section','Name','Data type','Start/default','Retain'],[(r['section'],code(r['name']),code(r['type']),code(val(r['initial']))if r.get('initial')is not None else 'Leave default',('ON'if r.get('retain')else 'OFF')if r['section']=='Static'else 'Not applicable')for r in rows])
''' + s[end:]
    line = " setup=[dict(section='Static',name=n,type='Bool',initial=v)for n,v in [('Enable',False),('WiringReviewed',False),('StartupPending',True)]]\n"
    s = once(s, line, '')
    start = s.index(" task('MM6-compact-setup'")
    end = s.index(" task('MM6-compact-fb'", start)
    s = s[:start]+s[end:]
    s = once(s, " 'For this new DB: <strong>Properties → Attributes → Optimized block access OFF</strong>. Press Ctrl+S, then compile it. Check the generated Offset column; the first tag should be byte 0.'", " 'For this new DB: <strong>Properties → Attributes → Optimized block access OFF</strong>. Turn <strong>Retain ON</strong> for this whole new DB. Press Ctrl+S and compile. Check the Offset column: the first tag is byte 0. The live BetweenCycleSeconds field is explicitly cleared after restart; the other values are preserved until their normal updates.'")
    s = once(s, " 'Start with the clock section next. Each numbered network tells you which extra local variables to add just before you use them. There is no 60-row declaration list and no helper FC to build.'", " 'Start with the clock section next. Add local variables when each network introduces them. Follow its Retain column: only the four saved period keys are ON; the live state is OFF. There is no setup DB, enable switch or helper FC to build.'")
    s = once(s, 'Those three mappings are still unverified. Leave reporting disabled until they are resolved.', 'These three real machine conditions are still unverified. Complete their mapping before putting the observer into service. They are runtime inputs, not temporary test controls.')
    start = s.index(" task('MM6-compact-startup'")
    end = s.index(" task('MM6-compact-load'", start)
    retention = ''' task('MM6-compact-retention','Keep totals; reset live timing automatically',steps(
 'Open <strong>CSI_Report</strong>. Turn <strong>Retain ON</strong> for all 12 fields in this new standard DB. Do not change existing machine DBs.',
 'Open <strong>CSI_Reporting → upper declaration grid → Static</strong>. Set <strong>Retain ON</strong> for only <strong>HourSaved, DaySaved, DayShiftSaved and NightShiftSaved</strong>. Keep their declared start/default value <strong>-1</strong>. These four tags identify which periods the retained counts belong to.',
 'Set <strong>Retain OFF</strong> for all other Static tags. In particular, <strong>Initialized</strong> must be OFF with default <strong>FALSE</strong>. State, CycleMs and WaitMs must be OFF with default <strong>0</strong>. Keep the main FB optimized so these choices are separate.',
 'Do not create a setup DB and do not add a startup-OB call for this version. After a normal CPU restart, Initialized returns to FALSE. Network 11 recognizes the first call; network 28 clears live timing and BetweenCycleSeconds. The observer then waits for a new qualified robot-return sequence.',
 'Save and compile. Review the actual download preview for retention/initialization effects. Cancel an unexpected STOP or an existing-machine DB change.')+'<p>PreviousCycleSeconds, PreviousBetweenSeconds and the nine counters are not zeroed by the startup-reset network. Hour/day/shift counters still perform their normal dated rollover if a new period has begun. Power-off time and an interrupted cycle are not added to a valid duration.</p>'),
'''
    s = s[:start]+retention+s[end:]
    s = once(s, 'Keep the new Enable and WiringReviewed FALSE until the final checks.', 'This version starts observing automatically from its OB1 call when the mapped conditions and schedule permit. There is no later setup-bit write. Review the real inputs before loading it.')
    s = once(s, "'Enable reporting and check a complete cycle'", "'Watch automatic startup and a complete cycle'")
    s = once(s, 'the setup bits and the 12 report fields.', 'the 12 report fields, plus <code>"CSI_Reporting_DB".Initialized</code>, <code>"CSI_Reporting_DB".CycleMs</code> and <code>"CSI_Reporting_DB".WaitMs</code>.')
    s = once(s, 'Confirm local time, live configuration and the three reviewed machine conditions. With site approval, modify only <code>"CSI_Setup".WiringReviewed</code> and <code>"CSI_Setup".Enable</code> to TRUE. Use normal modification, not Force; clear the Modify cells afterward.', 'Confirm local time, live configuration and the three real machine conditions. Only monitor these values; do not force or modify them. A freshly started observer should first show State 0, then synchronize before measuring a complete cycle.')
    s = once(s, " mm6.update(tasks=tasks,hint='12 reporting tags · one LAD function block')", " mm6.update(tasks=tasks,hint='12 reporting tags · automatic restart reset')")
    s = s.replace('28 Sep · 12 tags', '28 Sep · auto reset').replace('machine-reporting-compact-v8-20260928', 'machine-reporting-compact-v9-autostart-20260928')
    s = once(s, "REFS=[", "REFS=[('Siemens: what resets after CPU restart','https://docs.tia.siemens.cloud/r/en-us/v20/functional-description-of-s7-1500-cpus-s7-1500/operating-modes-s7-1500/startup-operating-mode-s7-1500/warm-restart-s7-1500'),('Siemens: individual FB tag retention','https://docs.tia.siemens.cloud/r/en-us/v21/declaring-the-block-interface/rules-for-declaring-the-block-interface/setting-the-retentivity-of-local-tags'),")
    assert 'CSI_Setup' not in s and 'StartupPending' not in s
    texts['compact_steps.py'] = s

    s = texts['tests/compact_test.py']
    s = once(s, "  self.setup={'Enable':True,'WiringReviewed':True,'StartupPending':True}\n", '')
    branch = '  elif v.startswith(\'"CSI_Setup".\'):d=self.setup;key=v.split(\'.\',1)[1]\n'
    assert s.count(branch)==2, ('Expected get/put setup branches', s.count(branch))
    s=s.replace(branch, '')
    s = once(s, "  if restart:self.setup['StartupPending']=True", "  if restart:\n   for r in BLOCK.rows:\n    if r['section']=='Static' and not r.get('retain',False):self.local[r['name']]=self.default(r)")
    s = s.replace("('#','\"CSI_Report\".','\"CSI_Setup\".')", "('#','\"CSI_Report\".')")
    texts['tests/compact_test.py'] = s

    s = texts['tests/compact_browser_test.py']
    s = s.replace('MM6-compact-setup', 'MM6-compact-fb').replace('Restore puts report step back before setup','Restore puts report step back before the FB')
    # Keep the user's retired setup notes as a migration test, not active instructions.
    s = once(s, "'notes':{'MM6-lad-report':'Old layout note'}", "'notes':{'MM6-lad-report':'Old layout note','MM6-compact-setup':'Saved setup note'}")
    s = once(s, " ok('All current tasks render',page.locator('article.task').count()==count)", " ok('All current tasks render',page.locator('article.task').count()==count)\n ok('Removed setup task keeps its old note',page.locator('#check-MM6-compact-setup').count()==0 and 'Saved setup note' in page.locator('#legacy-records').text_content())\n ok('No setup DB or write-to-enable step remains', 'CSI_Setup' not in page.locator('#todo-MM6').text_content() and page.locator('#check-MM6-compact-retention').count()==1)")
    texts['tests/compact_browser_test.py'] = s

    # All assertions pass before the first write.
    for name, text in texts.items():
        compile(text, name, 'exec')
    for name, text in texts.items():
        (root/name).write_text(text)
    note = '''\n## Current automatic restart handling\n\nThe compact route has only CSI_Report, CSI_Reporting (LAD) and CSI_Reporting_DB. No CSI_Setup, enable/review bit, StartupPending or new startup-OB call is required. The user rejected temporary test setup. The five machine input pins remain runtime qualifications and are not guessed or forced.\n\nRetain the whole 12-field reporting DB. In the optimized FB retain only HourSaved, DaySaved, DayShiftSaved and NightShiftSaved. All other Static state, especially Initialized (FALSE), State, CycleMs and WaitMs (0), is non-retentive. Fresh = NOT Initialized; the first cyclic call clears live timing and the retained live wait display without clearing held times/counts. Period keys must remain paired with counters; legitimate date/hour/shift rollover is not suppressed after restart. No runtime state resumes an interrupted cycle.\n\nPreserve the report layout, field names, task IDs for unchanged tasks, user notes and dark mode. Retired setup/startup task notes remain in Earlier records. Tests simulate configured retention and run the authored LAD records; they are not a TIA compilation or hardware restart test. Run tests/restart_test.py plus the compact browser test.\n'''
    for name in ('README.md','AGENTS.md'):
        p=root/name
        if p.exists() and '## Current automatic restart handling' not in p.read_text():
            p.write_text(p.read_text()+note)
    print('Removed setup DB; retained period keys; automatic first-call reset installed.')

if __name__ == '__main__':
    install()
