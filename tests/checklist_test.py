"""Browser checks; live localhost in CI, injected page fallback for restricted containers."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import threading,json,os,hashlib
R=Path(__file__).resolve().parents[1];results=[]
def ok(label,condition):
    assert condition,label
    results.append(label)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(R)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base='http://127.0.0.1:'+str(server.server_port)+'/'
old={'version':1,'done':{'MM4-start':'yesterday','MM6-source':'yesterday'},'notes':{'MM4-start':'Call with operator','MM6-source':'Old source notes'},'configs':{'MM6':{'db':'123'}}}
with sync_playwright() as p:
    path='/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None
    browser=p.chromium.launch(executable_path=path,headless=True,args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
    live=True
    try:page.goto(base,wait_until='networkidle',timeout=10000)
    except Exception:
        live=False
        if os.environ.get('REQUIRE_LIVE_BROWSER')=='1':raise
        page.close();page=ctx.new_page();page.on('pageerror',lambda err:errors.append(str(err)))
    def load(store=None):
        global page
        if live:
            if store is not None:
                page.evaluate('(s)=>{localStorage.clear();for(const [k,v]of Object.entries(s))localStorage.setItem(k,v)}',store)
            page.reload(wait_until='networkidle')
        else:
            if page.locator('body').count():
                page.close();page=ctx.new_page();page.on('pageerror',lambda err:errors.append(str(err)))
            init='<script>window.__store='+json.dumps(store or {})+';Object.defineProperty(window,"localStorage",{value:{getItem:k=>window.__store[k]??null,setItem:(k,v)=>window.__store[k]=v,clear:()=>window.__store={}}});</script>'
            page.set_content(init+(R/'index.html').read_text(),wait_until='domcontentloaded')
    load({ 'csi-machine-reporting-checklist-v1':json.dumps(old)})
    ok('25 compact steps, not the former 84',page.locator('article.task').count()==25)
    ok('MM6 is open by default',page.locator('#todo-MM6').get_attribute('open') is not None)
    ok('Relevant old completed check is preserved',page.locator('#done-MM4 [data-task="MM4-start"]').count()==1)
    ok('Old source completion does not mark MM6 V2 installed',not page.locator('#check-MM6-v2-source').is_checked())
    ok('Old reporting DB number is not reused for new V2 layout',page.locator('#field-MM6-reportDbV2').input_value()=='')
    ok('Retired checks and notes remain available',page.locator('#legacy-records').count()==1 and 'Old source notes' in page.locator('#legacy-records').text_content())
    page.locator('#how-MM6-v2-source > summary').click()
    ok('Source and reporting tag creation use exact location', 'External sources' in page.locator('#how-MM6-v2-source').inner_text() and 'Generate blocks from source' in page.locator('#how-MM6-v2-source').inner_text())
    with page.expect_download() as dl:page.locator('[data-source]').click()
    ok('Downloaded V2 source is byte-for-byte unchanged',Path(dl.value.path()).read_bytes()==(R/'downloads/MM6_Reporting_V2.scl').read_bytes())
    page.locator('#how-MM6-v2-source > summary').click()
    page.locator('#how-MM6-v2-tags > summary').click();page.locator('#field-MM6-reportDbV2').fill('950')
    page.locator('#note-MM6-v2-tags > summary').click();page.locator('#note-MM6-v2-tags textarea').fill('Compiled number confirmed in test')
    page.locator('#check-MM6-v2-tags').scroll_into_view_if_needed();y=page.locator('[data-task="MM6-v2-call"]').bounding_box()['y']
    page.locator('#check-MM6-v2-tags').check();page.wait_for_timeout(100)
    ok('Check moves the task into matching Completed folder',page.locator('#done-MM6 [data-task="MM6-v2-tags"]').count()==1)
    ok('Checking does not move the next step on screen',abs(page.locator('[data-task="MM6-v2-call"]').bounding_box()['y']-y)<2)
    store=page.evaluate('Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))') if live else page.evaluate('window.__store')
    load(store)
    ok('Completion and note survive reload/serialized rehydration',page.locator('#done-MM6 [data-task="MM6-v2-tags"]').count()==1 and page.locator('#note-MM6-v2-tags textarea').input_value()=='Compiled number confirmed in test')
    page.locator('#completed>summary').click();page.locator('#completed-programming>summary').click();page.locator('#done-MM6>summary').click();page.locator('#check-MM6-v2-tags').uncheck()
    ok('Unchecking restores original order',page.locator('#todo-MM6 .task-list > .task').nth(2).get_attribute('data-task')=='MM6-v2-tags')
    page.get_by_role('button',name='MM6',exact=True).click()
    page.locator('#how-MM6-v2-call>summary').scroll_into_view_if_needed();y=page.locator('#how-MM6-v2-call>summary').bounding_box()['y'];page.locator('#how-MM6-v2-call>summary').click();page.wait_for_timeout(80)
    ok('Expanding instructions preserves summary position',abs(page.locator('#how-MM6-v2-call>summary').bounding_box()['y']-y)<2)
    page.get_by_role('button',name='Kepware',exact=True).click();page.locator('#todo-K-MM6>summary').click();page.locator('#how-K-MM6-v2-tags>summary').click()
    ok('Kepware map uses entered DB and V2 daily-count offset','DB950,DINT156' in page.locator('#tag-map').inner_text() and 'DB950,REAL40' in page.locator('#tag-map').inner_text())
    with page.expect_download() as dl:page.get_by_role('button',name='Download complete address reference').click()
    csv=Path(dl.value.path()).read_text()
    ok('CSV quotes addresses and includes all 60 fields','"DB950,REAL40"' in csv and len(csv.splitlines())==61)
    page.locator('#tools>summary').click()
    with page.expect_download() as dl:page.get_by_role('button',name='Export progress').click()
    exported=json.loads(Path(dl.value.path()).read_text())
    ok('Backup retains previous checklist and new field values',exported['legacy']['configs']['MM6']['db']=='123' and exported['fields']['MM6']['reportDbV2']=='950')
    if live:
        page.once('dialog',lambda d:d.accept())
        with page.expect_navigation(wait_until='networkidle'):
            page.locator('#import').set_input_files({'name':'backup.json','mimeType':'application/json','buffer':json.dumps(exported).encode()})
        ok('Import restores the exported progress',page.locator('#field-MM6-reportDbV2').input_value()=='950')
    # Clean screenshot on the actual new layout.
    load({});page.set_viewport_size({'width':1280,'height':1000});page.screenshot(path=str(R/'tests/desktop.png'),full_page=True)
    page.locator('#how-MM6-v2-call>summary').click();page.locator('#how-MM6-v2-call').scroll_into_view_if_needed();page.screenshot(path=str(R/'tests/how.png'))
    page.set_viewport_size({'width':390,'height':844});page.get_by_role('button',name='MM6',exact=True).click()
    ok('Mobile document has no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    page.screenshot(path=str(R/'tests/mobile.png'),full_page=True)
    if live:
        page.wait_for_function('navigator.serviceWorker.controller!==null',timeout=15000)
        ctx.set_offline(True);page.reload(wait_until='domcontentloaded')
        ok('App reloads offline using its current cache',page.locator('article.task').count()==25)
        with page.expect_download() as dl:page.locator('#how-MM6-v2-source>summary').click();page.locator('[data-source]').click()
        ok('Correct source remains downloadable offline',Path(dl.value.path()).read_bytes()==(R/'downloads/MM6_Reporting_V2.scl').read_bytes())
    ok('No JavaScript errors',not errors)
    browser.close()
server.shutdown()
report={'passed':len(results),'checks':results,'live_browser':live,'scope':'Live localhost browser, native localStorage and service worker' if live else 'Injected HTML and storage test double due to browser navigation restriction; native persistence/offline lifecycle not verified in this run','plc_tested':False}
(R/'tests/checklist_results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
