"""Browser regression checks for the compact LAD checklist. No PLC access."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
import threading,os,json
R=Path(__file__).resolve().parents[1];checks=[]
def ok(name,c):assert c,name;checks.append(name)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(R)));threading.Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(server.server_port)+'/'
d=json.loads((R/'content.json').read_text());count=sum(len(g['tasks'])for g in d['groups']+d['kepware'])
with sync_playwright()as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium'if Path('/usr/bin/chromium').exists()else None,headless=True,args=['--no-sandbox'])
 ctx=b.new_context(viewport={'width':1280,'height':960},color_scheme='light',accept_downloads=True)
 page=ctx.new_page();errs=[];page.on('pageerror',lambda e:errs.append(str(e)));live=True
 try:page.goto(url,wait_until='networkidle',timeout=7000)
 except Exception:
  live=False
  if os.environ.get('REQUIRE_LIVE_BROWSER')=='1':raise
 def load(store=None):
  global page
  if live:
   if store is not None:page.evaluate('(s)=>{localStorage.clear();for(const[k,v]of Object.entries(s))localStorage.setItem(k,v)}',store)
   page.reload(wait_until='networkidle')
  else:
   page.close();page=ctx.new_page();page.on('pageerror',lambda e:errs.append(str(e)))
   init='<script>window.__store='+json.dumps(store or {})+';Object.defineProperty(window,"localStorage",{value:{getItem:k=>window.__store[k]??null,setItem:(k,v)=>window.__store[k]=v}});</script>'
   page.set_content(init+(R/'index.html').read_text(),wait_until='domcontentloaded')
 seed={'version':3,'done':{'MM6-lad-report':'past','MM4-start':'past'},'notes':{'MM6-lad-report':'Old layout note','MM6-compact-setup':'Saved setup note'},'fields':{'MM6':{'reportDbLad':'123','reportDbV2':'124'}},'open':{'programming':True,'todo-MM6':True}}
 load({'csi-machine-reporting-checklist-v3':json.dumps(seed)})
 ok('All current tasks render',page.locator('article.task').count()==count)
 ok('Removed setup task keeps its old note',page.locator('#check-MM6-compact-setup').count()==0 and 'Saved setup note' in page.locator('#legacy-records').text_content())
 ok('No setup DB or write-to-enable step remains', 'CSI_Setup' not in page.locator('#todo-MM6').text_content() and page.locator('#check-MM6-compact-retention').count()==1)
 ok('Forced dark theme remains on',page.evaluate("getComputedStyle(document.documentElement).colorScheme.includes('dark')"))
 ok('Old monitoring checks and retired notes survive',page.locator('#done-MM4 [data-task="MM4-start"]').count()==1 and 'Old layout note'in page.locator('#legacy-records').text_content())
 ok('Old layout completion does not mark the 12-tag layout done',not page.locator('#check-MM6-compact-report').is_checked())
 ok('No old DB number is automatically reused',page.locator('#field-MM6-reportDbCompact').input_value()=='')
 page.locator('#how-MM6-compact-report>summary').click()
 ok('Report table has exactly twelve entries',page.locator('#how-MM6-compact-report tbody tr').count()==12)
 txt=page.locator('#how-MM6-compact-report').inner_text()
 ok('Static heading and byte-zero explanation present','Static is a heading'in txt and 'byte 0'in txt)
 ok('Day and night shift names are shown',all(x in txt for x in ['DayShiftCurrent','DayShiftPrevious','NightShiftCurrent','NightShiftPrevious']))
 page.locator('#field-MM6-reportDbCompact').fill('56')
 page.locator('#note-MM6-compact-report>summary').click();page.locator('#note-MM6-compact-report textarea').fill('DB56 confirmed, compact layout')
 page.locator('#how-MM6-compact-report>summary').click();page.locator('[data-task="MM6-compact-report"]').evaluate('(n)=>n.scrollIntoView({block:"start"})');page.wait_for_timeout(100);y=page.locator('[data-task="MM6-compact-fb"]').bounding_box()['y'];page.locator('#check-MM6-compact-report').check();page.wait_for_timeout(80)
 ok('Completing preserves the following row position',abs(y-page.locator('[data-task="MM6-compact-fb"]').bounding_box()['y'])<2)
 ok('Completed task moves to its matching folder',page.locator('#done-MM6 [data-task="MM6-compact-report"]').count()==1)
 store=page.evaluate('Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))')if live else page.evaluate('window.__store');load(store)
 ok('Note, completed state and compact DB survive reload',page.locator('#done-MM6 [data-task="MM6-compact-report"]').count()==1 and page.locator('#field-MM6-reportDbCompact').input_value()=='56' and 'DB56 confirmed'in page.locator('#note-MM6-compact-report textarea').input_value())
 page.locator('#completed>summary').click();page.locator('#completed-programming>summary').click();page.locator('#done-MM6>summary').click();page.locator('#check-MM6-compact-report').uncheck()
 ok('Restore puts report step back before the FB',page.locator('#todo-MM6>.task-list>.task').nth(1).get_attribute('data-task')=='MM6-compact-report')
 page.get_by_role('button',name='Kepware',exact=True).click();page.locator('#todo-K-MM6>summary').click();page.locator('#how-K-MM6-compact-tags>summary').click()
 text=page.locator('#tag-map').inner_text()
 ok('Kepware table uses compact 12-field offsets',page.locator('#tag-map tbody tr').count()==12 and 'DB56,REAL0'in text and 'DB56,DINT28'in text and 'DB56,DINT36'in text and 'DB56,DINT44'in text)
 with page.expect_download()as dl:page.get_by_role('button',name='Download complete address reference').click()
 csv=Path(dl.value.path()).read_text();ok('CSV has 12 data rows with day/night names',len(csv.splitlines())==13 and 'DayShiftCurrent'in csv and 'NightShiftPrevious'in csv and 'Shift1Current'not in csv)
 page.locator('#tools>summary').click()
 with page.expect_download()as dl:page.get_by_role('button',name='Export progress').click()
 export=json.loads(Path(dl.value.path()).read_text());ok('Export preserves old notes and new DB separately',export['fields']['MM6']['reportDbCompact']=='56' and export['fields']['MM6']['reportDbLad']=='123' and export['legacy']['notes']['MM6-lad-report']=='Old layout note')
 if live:
  page.once('dialog',lambda dialog:dialog.accept())
  with page.expect_navigation(wait_until='networkidle'):page.locator('#import').set_input_files({'name':'progress.json','mimeType':'application/json','buffer':json.dumps(export).encode()})
  ok('Import restores compact progress',page.locator('#field-MM6-reportDbCompact').input_value()=='56')
 page.get_by_role('button',name='MM6',exact=True).click();page.locator('#how-MM6-compact-section-1>summary').click();summ=page.locator('#compact-net-1>summary');summ.scroll_into_view_if_needed();y=summ.bounding_box()['y'];summ.click();page.wait_for_timeout(100)
 ok('Expanding rung preserves its heading',abs(y-summ.bounding_box()['y'])<2)
 ok('Local variables are introduced at their first rung','First add these local variables'in page.locator('#compact-net-1').inner_text() and page.locator('#compact-net-1 tbody tr').count()<8)
 ok('No old helpers or SCL import in active MM6 checklist',not page.locator('#todo-MM6 [data-source]').count() and 'Build CSI_PeriodCounter'not in page.locator('#todo-MM6').inner_text())
 load({});page.locator('#how-MM6-compact-report>summary').click();page.screenshot(path=str(R/'tests/compact_report.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.get_by_role('button',name='MM6',exact=True).click();ok('Mobile layout fits viewport',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.screenshot(path=str(R/'tests/compact_mobile.png'),full_page=True)
 if live:
  page.wait_for_function('navigator.serviceWorker.controller!==null',timeout=15000);ctx.set_offline(True);page.reload(wait_until='domcontentloaded');ok('Compact checklists and rungs remain available offline',page.locator('article.task').count()==count and page.locator('[id^="compact-net-"]').count()==66)
 ok('No browser script errors',not errs);b.close()
server.shutdown()
report=dict(passed=len(checks),checks=checks,live_browser=live,plc_tested=False,scope='Live browser/localStorage/offline'if live else 'Injected HTML and storage stub: native offline lifecycle not tested locally.')
(R/'tests/compact_browser_results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
