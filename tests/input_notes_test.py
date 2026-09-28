"""Documentation/DOM checks, not a Siemens compiler or hardware test."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import json,os,sys,threading
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from input_notes import apply_notes
checks=[]
def ok(n,v):assert v,n;checks.append(n)
d=json.loads((R/'content.json').read_text())
ok('Applying notes twice does not duplicate them',apply_notes(d)==d)
for m in ('MM4','MM5','MM6'):
 g=next(g for g in d['groups']if g['id']==m);text=json.dumps(g)
 ok(m+' contains exact production-mode and reset source addresses',all(s in text for s in ['M50.2','M50.3','DB20.DBX0.1']))
 ok(m+' distinguishes an unresolved existing RobotDataValid mapping','No existing one-bit source verified' in text)
 ok(m+' explains all five input meanings',all(s in text for s in ['CloseCommand','RobotPermit','ProductionEligible','RobotDataValid','AbortCycle']))
ok('Existing twelve report members and offsets unchanged',len(d['schema'])==12 and [x['offset']for x in d['schema']]==list(range(0,48,4)))
ok('No permanent-TRUE data-valid recipe is presented','RobotDataValid := TRUE'not in json.dumps(d))
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(R)));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright()as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium'if Path('/usr/bin/chromium').exists()else None,headless=True,args=['--no-sandbox']);ctx=b.new_context(viewport={'width':1280,'height':950},color_scheme='light');page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));live=True
 try:page.goto('http://127.0.0.1:'+str(server.server_port)+'/',wait_until='networkidle',timeout=7000)
 except Exception:
  live=False
  if os.environ.get('REQUIRE_LIVE_BROWSER')=='1':raise
  page.close();page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content('<script>window.__store={};Object.defineProperty(window,"localStorage",{value:{getItem:k=>window.__store[k]??null,setItem:(k,v)=>window.__store[k]=v}});</script>'+(R/'index.html').read_text(),wait_until='domcontentloaded')
 ok('All 42 existing checklist tasks remain',page.locator('article.task').count()==42)
 ok('All 66 existing ladder networks remain',page.locator('[id^="compact-net-"]').count()==66)
 ok('Dark mode unchanged',page.evaluate("getComputedStyle(document.documentElement).colorScheme.includes('dark')"))
 for m in ('MM4','MM5','MM6'):
  ok(m+' has one definition table with five rows',page.locator('#input-guide-'+m+'>.table-wrap tbody tr').count()==5)
 page.get_by_role('button',name='MM6',exact=True).click();page.locator('#how-MM6-compact-call>summary').click();page.locator('#inputs-MM6-production>summary').click()
 ok('OB1 TEMP declaration and OR expression are visible','O     M50.2' in page.locator('#inputs-MM6-production').inner_text() and 'Temp' in page.locator('#inputs-MM6-production').inner_text())
 page.locator('#inputs-MM6-valid>summary').click();page.locator('#inputs-MM6-diag-build>summary').click()
 ok('Read-only diagnostic is conditional on actual hardware confirmation','I705.7' in page.locator('#inputs-MM6-valid').inner_text() and 'verified' in page.locator('#inputs-MM6-diag-build').inner_text())
 ok('Diagnostic recipe requires successful return and Good bit',all(s in page.locator('#inputs-MM6-diag-build').inner_text() for s in ['==I','IOState.%X0']))
 ids=page.locator('[id]').evaluate_all('(xs)=>xs.map(x=>x.id)');ok('No duplicate element IDs',len(ids)==len(set(ids)))
 page.set_viewport_size({'width':390,'height':844});ok('Expanded instructions stay within mobile page width',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 ok('No browser script errors',not errors)
 if live:
  page.wait_for_function('navigator.serviceWorker.controller!==null',timeout=15000);ctx.set_offline(True);page.reload(wait_until='domcontentloaded');ok('Input notes work offline',page.locator('#input-guide-MM6').count()==1)
 b.close()
server.shutdown();result=dict(passed=len(checks),checks=checks,live_browser=live,plc_tested=False,scope='Documentation/DOM checks; diagnostic mapping not hardware-tested.');(R/'tests/input_notes_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
