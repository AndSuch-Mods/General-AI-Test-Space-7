"""Current LAD guide browser regressions; no PLC or TIA compiler execution."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
import json,os,threading
R=Path(__file__).resolve().parents[1];checks=[]
def ok(n,c):assert c,n;checks.append(n)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(R)));threading.Thread(target=server.serve_forever,daemon=True).start();url='http://127.0.0.1:'+str(server.server_port)+'/'
d=json.loads((R/'content.json').read_text());size=sum(len(g['tasks'])for g in d['groups']+d['kepware'])
with sync_playwright()as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium'if Path('/usr/bin/chromium').exists()else None,headless=True,args=['--no-sandbox'])
 ctx=browser.new_context(viewport={'width':1280,'height':1000},color_scheme='light',accept_downloads=True);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));live=True
 try:page.goto(url,wait_until='networkidle',timeout=7000)
 except Exception:
  live=False
  if os.environ.get('REQUIRE_LIVE_BROWSER')=='1':raise
 def load(store=None):
  global page
  if live:
   if store is not None:page.evaluate('(s)=>{localStorage.clear();for(const [k,v]of Object.entries(s))localStorage.setItem(k,v)}',store)
   page.reload(wait_until='networkidle')
  else:
   page.close();page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   init='<script>window.__store='+json.dumps(store or {})+';Object.defineProperty(window,"localStorage",{value:{getItem:k=>window.__store[k]??null,setItem:(k,v)=>window.__store[k]=v,clear:()=>window.__store={}}});</script>'
   page.set_content(init+(R/'index.html').read_text(),wait_until='domcontentloaded')
 seed={'version':3,'done':{'MM4-start':'earlier','MM6-manual-main':'earlier','MM6-config':'earlier'},'notes':{'MM6-manual-main':'My SCL work is saved.','MM4-start':'Operator confirmed.'},'fields':{'MM6':{'reportDbV2':'950'}},'open':{'programming':True,'todo-MM6':True}}
 load({'csi-machine-reporting-checklist-v3':json.dumps(seed)})
 ok('All compact tasks render and MM6 is open',page.locator('article.task').count()==size and page.locator('#todo-MM6').get_attribute('open')is not None)
 ok('Dark appearance stays on in a light browser',page.evaluate("getComputedStyle(document.documentElement).colorScheme.includes('dark')"))
 ok('Existing machine monitoring checks survive',page.locator('#done-MM4 [data-task="MM4-start"]').count()==1 and page.locator('#done-MM6 [data-task="MM6-config"]').count()==1)
 ok('SCL completion does not mark LAD work done',not page.locator('#check-MM6-lad-main-vars').is_checked())
 ok('Retired SCL notes are preserved','My SCL work is saved.' in page.locator('#legacy-records').text_content())
 ok('Old SCL report DB number is not silently reused',page.locator('#field-MM6-reportDbLad').input_value()=='')
 ok('Main route contains no SCL import or body-paste panels',page.locator('#todo-MM6 [data-source]').count()==0 and page.locator('#todo-MM6 pre.manual-code').count()==0)
 ok('All authored LAD networks are present',page.locator('[id^="lad-CSI_Reporting-"]>summary').count()==129 and page.locator('[id^="lad-CSI_PeriodCounter-"]>summary').count()==8)
 page.locator('#how-MM6-lad-networks-3>summary').click()
 # Third phase is edge detection and synchronization.
 candidate=page.locator('#how-MM6-lad-networks-3 .manual-panel>summary').first;candidate.scroll_into_view_if_needed();y=candidate.bounding_box()['y'];candidate.click();page.wait_for_timeout(80)
 ok('Opening a rung preserves its heading position',abs(candidate.bounding_box()['y']-y)<2)
 ok('Rung shows actual contacts/coils rather than SCL',page.locator('#how-MM6-lad-networks-3 .lad-diagram').first.text_content().find('PrevClose')>=0)
 candidate.click();page.locator('#how-MM6-lad-networks-3>summary').click();page.locator('#how-MM6-lad-report>summary').click();page.locator('#field-MM6-reportDbLad').fill('951');page.locator('#note-MM6-lad-report>summary').click();page.locator('#note-MM6-lad-report textarea').fill('LAD report DB checked.')
 page.locator('#how-MM6-lad-report>summary').click();page.locator('#check-MM6-lad-report').scroll_into_view_if_needed();y=page.locator('[data-task="MM6-lad-setup"]').bounding_box()['y'];page.locator('#check-MM6-lad-report').check();page.wait_for_timeout(80)
 ok('Complete moves the task to the matching Completed folder',page.locator('#done-MM6 [data-task="MM6-lad-report"]').count()==1)
 ok('Completing a step keeps the next row anchored',abs(page.locator('[data-task="MM6-lad-setup"]').bounding_box()['y']-y)<2)
 store=page.evaluate('Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))')if live else page.evaluate('window.__store');load(store)
 ok('Completion, note and new DB field persist',page.locator('#done-MM6 [data-task="MM6-lad-report"]').count()==1 and page.locator('#note-MM6-lad-report textarea').input_value()=='LAD report DB checked.' and page.locator('#field-MM6-reportDbLad').input_value()=='951')
 page.locator('#completed>summary').click();page.locator('#completed-programming>summary').click();page.locator('#done-MM6>summary').click();page.locator('#check-MM6-lad-report').uncheck()
 ok('Restore returns the original ladder task order',page.locator('#todo-MM6>.task-list>.task').nth(1).get_attribute('data-task')=='MM6-lad-report')
 page.get_by_role('button',name='Kepware',exact=True).click();page.locator('#todo-K-MM6>summary').click();page.locator('#how-K-MM6-lad-tags>summary').click()
 ok('Kepware reads the LAD DB number with unchanged offsets','DB951,REAL40'in page.locator('#tag-map').inner_text() and 'DB951,DINT156'in page.locator('#tag-map').inner_text())
 with page.expect_download()as dl:page.get_by_role('button',name='Download complete address reference').click()
 csv=Path(dl.value.path()).read_text();ok('Address reference still exports all sixty fields',len(csv.splitlines())==61 and '"DB951,REAL40"'in csv)
 page.locator('#tools>summary').click()
 with page.expect_download()as dl:page.get_by_role('button',name='Export progress').click()
 backup=json.loads(Path(dl.value.path()).read_text());ok('Backup retains old and new notes/DB fields',backup['fields']['MM6']['reportDbV2']=='950' and backup['fields']['MM6']['reportDbLad']=='951' and backup['legacy']['notes']['MM6-manual-main']=='My SCL work is saved.')
 if live:
  page.once('dialog',lambda d:d.accept())
  with page.expect_navigation(wait_until='networkidle'):page.locator('#import').set_input_files({'name':'lad-backup.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
  ok('Progress import restores the ladder state',page.locator('#field-MM6-reportDbLad').input_value()=='951')
 load({});page.screenshot(path=str(R/'tests/ladder_desktop.png'),full_page=True)
 page.locator('#how-MM6-lad-networks-3>summary').click();candidate=page.locator('#how-MM6-lad-networks-3 .manual-panel>summary').first;candidate.click();candidate.scroll_into_view_if_needed();page.screenshot(path=str(R/'tests/ladder_rung.png'))
 page.set_viewport_size({'width':390,'height':844})
 ok('Expanded ladder content fits a mobile viewport',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.screenshot(path=str(R/'tests/ladder_mobile.png'))
 if live:
  page.wait_for_function('navigator.serviceWorker.controller!==null',timeout=15000);ctx.set_offline(True);page.reload(wait_until='domcontentloaded')
  ok('Ladder networks remain available offline',page.locator('article.task').count()==size and page.locator('[id^="lad-CSI_Reporting-"]>summary').count()==129)
 ok('No browser JavaScript errors',not errors)
 browser.close()
server.shutdown();result=dict(passed=len(checks),checks=checks,live_browser=live,plc_tested=False,scope='Live browser/localStorage/offline'if live else'Injected HTML and storage stub; live browser/persistence/offline must be checked in CI.')
(R/'tests/ladder_browser_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
