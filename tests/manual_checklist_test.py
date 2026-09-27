"""Manual-build UI regressions. Real localhost browser in CI; no PLC execution."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import threading,json,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from manual_steps import parse_source,body_sections
R=Path(__file__).resolve().parents[1];results=[]
def ok(label,condition):
    assert condition,label
    results.append(label)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(R)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base='http://127.0.0.1:'+str(server.server_port)+'/'
d=json.loads((R/'content.json').read_text());expected=sum(len(g['tasks']) for g in d['groups']+d['kepware'])
mm6=next(g for g in d['groups'] if g['id']=='MM6');order=[t['id'] for t in mm6['tasks']]
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
            if store is not None:page.evaluate('(s)=>{localStorage.clear();for(const [k,v]of Object.entries(s))localStorage.setItem(k,v)}',store)
            page.reload(wait_until='networkidle')
        else:
            page.close();page=ctx.new_page();page.on('pageerror',lambda err:errors.append(str(err)))
            init='<script>window.__store='+json.dumps(store or {})+';Object.defineProperty(window,"localStorage",{value:{getItem:k=>window.__store[k]??null,setItem:(k,v)=>window.__store[k]=v,clear:()=>window.__store={}}});</script>'
            page.set_content(init+(R/'index.html').read_text(),wait_until='domcontentloaded')
    load({'csi-machine-reporting-checklist-v1':json.dumps(old)})
    ok('All current tasks render; MM6 opens by default',page.locator('article.task').count()==expected and page.locator('#todo-MM6').get_attribute('open') is not None)
    ok('MM4 prior completion survives',page.locator('#done-MM4 [data-task="MM4-start"]').count()==1)
    ok('Old import completion does not mark manual code built',not page.locator('#check-MM6-manual-main').is_checked())
    ok('V1 DB number is not assumed to match the new reporting DB',page.locator('#field-MM6-reportDbV2').input_value()=='')
    ok('V1 retired notes are still visible in Earlier records','Old source notes' in page.locator('#legacy-records').text_content())
    current={'version':3,'done':{'MM6-v2-source':'yesterday','MM4-start':'yesterday'},'notes':{'MM6-v2-source':'Imported source review note'},'fields':{'MM6':{'reportDbV2':'950'}},'open':{'programming':True,'todo-MM6':True},'legacy':old}
    load({'csi-machine-reporting-checklist-v3':json.dumps(current)})
    ok('Retired v3 import notes are not lost','Imported source review note' in page.locator('#legacy-records').text_content())
    ok('New manual build starts unchecked after an imported build',not page.locator('#check-MM6-manual-main').is_checked())
    page.locator('#how-MM6-manual-folder > summary').click()
    ok('Folder creation and main FB names are explicit','Add new group' in page.locator('#how-MM6-manual-folder').inner_text() and 'CSI_Reporting' in page.locator('#how-MM6-manual-folder').inner_text())
    page.locator('#how-MM6-manual-folder > summary').click()
    page.locator('#how-MM6-manual-main > summary').click()
    ok('Main declaration sections are distinguished',all(page.locator('#manual-CSI_Reporting-'+name+'-0').count()==1 for name in ['Input','Static','Temp']))
    ok('Eight actual body-only code sections are present',page.locator('pre[data-block="CSI_Reporting"]').count()==8)
    b=parse_source()['CSI_Reporting'];texts=page.locator('pre[data-block="CSI_Reporting"]').all_text_contents()
    ok('Rendered main logic exactly reconstructs the reference body',''.join(texts)==b['body'])
    summary=page.locator('#manual-body-CSI_Reporting-0 > summary');summary.scroll_into_view_if_needed();y=summary.bounding_box()['y'];summary.click();page.wait_for_timeout(100)
    ok('Opening a code section does not move its heading',abs(summary.bounding_box()['y']-y)<2)
    page.evaluate('window.__copied=null;Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async text=>{window.__copied=text}}})')
    page.locator('[data-copy-code="manual-code-CSI_Reporting-0"]').click()
    ok('Copy section copies body only, not declarations',page.evaluate('window.__copied')==body_sections(b)[0]['text'])
    summary.click();page.locator('#how-MM6-manual-main > summary').click()
    page.locator('#how-MM6-v2-tags > summary').click();page.locator('#field-MM6-reportDbV2').fill('950')
    page.locator('#note-MM6-v2-tags > summary').click();page.locator('#note-MM6-v2-tags textarea').fill('Manually entered DB verified')
    following=order[order.index('MM6-v2-tags')+1]
    page.locator('#check-MM6-v2-tags').scroll_into_view_if_needed();y=page.locator('[data-task="'+following+'"]').bounding_box()['y'];page.locator('#check-MM6-v2-tags').check();page.wait_for_timeout(100)
    ok('Checking moves the task into its matching Completed folder',page.locator('#done-MM6 [data-task="MM6-v2-tags"]').count()==1)
    ok('Checking keeps the following task anchored',abs(page.locator('[data-task="'+following+'"]').bounding_box()['y']-y)<2)
    store=page.evaluate('Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))') if live else page.evaluate('window.__store')
    load(store)
    ok('Completion and typed notes survive reload',page.locator('#done-MM6 [data-task="MM6-v2-tags"]').count()==1 and page.locator('#note-MM6-v2-tags textarea').input_value()=='Manually entered DB verified')
    page.locator('#completed>summary').click();page.locator('#completed-programming>summary').click();page.locator('#done-MM6>summary').click();page.locator('#check-MM6-v2-tags').uncheck()
    ok('Restore preserves original task order',page.locator('#todo-MM6>.task-list>.task').nth(order.index('MM6-v2-tags')).get_attribute('data-task')=='MM6-v2-tags')
    page.get_by_role('button',name='Kepware',exact=True).click();page.locator('#todo-K-MM6>summary').click();page.locator('#how-K-MM6-v2-tags>summary').click()
    ok('Manual path keeps correct V2 Kepware offsets','DB950,DINT156' in page.locator('#tag-map').inner_text() and 'DB950,REAL40' in page.locator('#tag-map').inner_text())
    with page.expect_download() as dl:page.get_by_role('button',name='Download complete address reference').click()
    csv=Path(dl.value.path()).read_text();ok('CSV still includes all sixty fields and quoted addresses',len(csv.splitlines())==61 and '"DB950,REAL40"' in csv)
    page.locator('#tools>summary').click()
    with page.expect_download() as dl:page.get_by_role('button',name='Export progress').click()
    exported=json.loads(Path(dl.value.path()).read_text())
    ok('Export retains old notes, new notes and DB fields',exported['legacy']['notes']['MM6-v2-source']=='Imported source review note' and exported['notes']['MM6-v2-tags']=='Manually entered DB verified' and exported['fields']['MM6']['reportDbV2']=='950')
    if live:
        page.once('dialog',lambda dialog:dialog.accept())
        with page.expect_navigation(wait_until='networkidle'):page.locator('#import').set_input_files({'name':'backup.json','mimeType':'application/json','buffer':json.dumps(exported).encode()})
        ok('Import restores manual-build progress',page.locator('#field-MM6-reportDbV2').input_value()=='950')
    load({});page.set_viewport_size({'width':1280,'height':1000});page.screenshot(path=str(R/'tests/manual_desktop.png'),full_page=True)
    page.locator('#how-MM6-manual-main>summary').click();page.locator('#manual-body-CSI_Reporting-0>summary').click();page.locator('#manual-body-CSI_Reporting-0').scroll_into_view_if_needed();page.screenshot(path=str(R/'tests/manual_code.png'))
    page.set_viewport_size({'width':390,'height':844})
    ok('Mobile page has no horizontal overflow with code open',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    page.screenshot(path=str(R/'tests/manual_mobile.png'))
    if live:
        page.wait_for_function('navigator.serviceWorker.controller!==null',timeout=15000);ctx.set_offline(True);page.reload(wait_until='domcontentloaded')
        ok('Manual instructions and code remain available offline',page.locator('article.task').count()==expected and ''.join(page.locator('pre[data-block="CSI_Reporting"]').all_text_contents())==b['body'])
    ok('No JavaScript errors',not errors)
    browser.close()
server.shutdown()
report=dict(passed=len(results),checks=results,live_browser=live,scope='Live localhost UI, storage and offline tests; clipboard handler checked with a browser stub.' if live else 'Injected document/storage fallback. Native persistence and service-worker lifecycle not tested.',plc_tested=False)
(R/'tests/manual_checklist_results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
