"""CSI naming, behavior-preserving transformation and current checklist UI checks."""
from pathlib import Path
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
import hashlib,json,re,sys,os,threading
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from csi_branding import rename_data,rename_text,renamed_source,NAMES,BUILD
checks=[]
def ok(name,v):
 assert v,name
 checks.append(name)
raw=(R/'downloads/MM6_Reporting_V2.scl').read_text(encoding='utf-8')
new=(R/'downloads/MM6_CSI_Reporting.scl').read_text(encoding='utf-8')
ok('Original V2 source remains immutable',hashlib.sha256((R/'downloads/MM6_Reporting_V2.scl').read_bytes()).hexdigest()=='eb709811803d67a10be673682d831cb80bf25cf814d40c612f753730e17a8b49')
ok('Current source changes symbol names only',new==renamed_source(raw))
restored=new
for a,b in sorted(NAMES.items(),key=lambda x:-len(x[1])):restored=re.sub(r'\b'+re.escape(b)+r'\b',a,restored)
ok('Renamed executable source reverses exactly to reference',re.sub(r'//[^\n]*','',restored)==re.sub(r'//[^\n]*','',raw))
d=json.loads((R/'content.json').read_text())
ok('No CSI2 names in active instructions or code','CSI2' not in json.dumps(d) and 'CSI2' not in new)
ok('Reporting schema stays at version 2','SchemaVersion : DInt := 2' in new)
original=(R/'previous_data.json')
if original.exists():base=json.loads(original.read_text())
else:
 from checklist_data import build_data
 from manual_steps import manual_data
 base=manual_data(build_data())
ids=lambda x:[t['id']for g in x['groups']+x['kepware']for t in g['tasks']]
ok('All 33 checklist task IDs retained',ids(d)==ids(base) and len(ids(d))==33)
ok('Report fields and offsets unchanged',d['schema']==rename_data(base)['schema'])
class P(HTMLParser):
 def __init__(self):super().__init__();self.code={};self.key=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='pre' and 'data-block' in a:self.key=(a['data-block'],a['data-part']);self.code[self.key]=''
 def handle_endtag(self,tag):
  if tag=='pre':self.key=None
 def handle_data(self,text):
  if self.key is not None:self.code[self.key]+=text
oldp=P();newp=P()
for g in base['groups']+base['kepware']:
 for t in g['tasks']:oldp.feed(t['body'])
for g in d['groups']+d['kepware']:
 for t in g['tasks']:newp.feed(t['body'])
ok('Every displayed executable section changes names only',newp.code=={(rename_text(a),b):rename_text(v) for (a,b),v in oldp.code.items()})
ok('All eight main-code sections still exist',len([1 for a,b in newp.code if a=='CSI_Reporting'])==8)
manifest=json.loads((R/'manifest.webmanifest').read_text())
ok('Home-screen manifest includes real checklist icons',len(manifest['icons'])==2 and all((R/i['src'].split('?')[0]).is_file()for i in manifest['icons']))
ok('Manifest is forced dark',manifest['background_color']=='#081118' and manifest['theme_color']=='#081118')
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(R)));threading.Thread(target=server.serve_forever,daemon=True).start();url='http://127.0.0.1:'+str(server.server_port)+'/'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None,headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1280,'height':1000},accept_downloads=True)
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));live=True
 try:page.goto(url,wait_until='networkidle',timeout=7000)
 except Exception:
  live=False
  if os.environ.get('REQUIRE_LIVE_BROWSER')=='1':raise
 def mount(store=None):
  global page
  if live:
   if store is not None:page.evaluate('(s)=>{localStorage.clear();for(const [k,v]of Object.entries(s))localStorage.setItem(k,v)}',store)
   page.reload(wait_until='networkidle')
  else:
   page.close();page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   init='<script>window.__store='+json.dumps(store or {})+';Object.defineProperty(window,"localStorage",{value:{getItem:k=>window.__store[k]??null,setItem:(k,v)=>window.__store[k]=v,clear:()=>window.__store={}}});</script>'
   page.set_content(init+(R/'index.html').read_text(),wait_until='domcontentloaded')
 seed={'version':3,'done':{'MM4-start':'test','MM6-manual-setup':'test'},'notes':{'MM6-manual-setup':'Keep this note exactly: CSI2_Setup prior name'},'fields':{'MM6':{'reportDbV2':'950'}},'open':{'programming':True,'todo-MM6':True,'manual-CSI2_Report-Static-0':True}}
 mount({'csi-machine-reporting-checklist-v3':json.dumps(seed)})
 ok('Header uses a checklist graphic, not a letter fallback',page.locator('.brand-emblem svg').count()==1)
 ok('Forced dark mode ignores a light browser preference',page.evaluate("getComputedStyle(document.documentElement).colorScheme.includes('dark') && getComputedStyle(document.body).color==='rgb(231, 239, 243)'"))
 ok('Browser and iPhone icon links are present',page.locator('link[rel="apple-touch-icon"]').count()==1 and page.locator('link[rel="icon"]').count()==2)
 ok('Old checks, notes and DB number survive',page.locator('#done-MM6 [data-task="MM6-manual-setup"]').count()==1 and page.locator('#note-MM6-manual-setup textarea').input_value()==seed['notes']['MM6-manual-setup'] and page.locator('#field-MM6-reportDbV2').input_value()=='950')
 ok('Previously opened declaration panels follow new CSI names',page.locator('#manual-CSI_Report-Static-0').get_attribute('open') is not None)
 page.locator('#how-MM6-manual-report>summary').click()
 ok('Manual report table uses CSI_Report','CSI_Report' in page.locator('#how-MM6-manual-report').inner_text() and 'CSI2_Report' not in page.locator('#how-MM6-manual-report').inner_text())
 page.locator('#how-MM6-manual-report>summary').click()
 page.locator('#how-MM6-manual-main>summary').click();summary=page.locator('#manual-body-CSI_Reporting-0>summary');summary.scroll_into_view_if_needed();y=summary.bounding_box()['y'];summary.click();page.wait_for_timeout(100)
 ok('Opening a code panel preserves screen position',abs(summary.bounding_box()['y']-y)<2)
 page.evaluate('window.__copied=null;Object.defineProperty(navigator,"clipboard",{value:{writeText:async s=>{window.__copied=s}},configurable:true})')
 page.locator('[data-copy-code="manual-code-CSI_Reporting-0"]').click()
 text=page.evaluate('window.__copied');ok('Copy button returns CSI code with no wrapper declarations','CSI2' not in text and text==newp.code[('CSI_Reporting','0')])
 summary.click();page.locator('#how-MM6-manual-main>summary').click()
 page.locator('#check-MM6-manual-report').scroll_into_view_if_needed();y=page.locator('[data-task="MM6-manual-helpers"]').bounding_box()['y'];page.locator('#check-MM6-manual-report').check();page.wait_for_timeout(100)
 ok('Checking moves only the selected task',page.locator('#done-MM6 [data-task="MM6-manual-report"]').count()==1)
 # Next incomplete row is helpers because setup was already completed in seed.
 ok('Checking keeps the next incomplete row anchored',abs(page.locator('[data-task="MM6-manual-helpers"]').bounding_box()['y']-y)<2)
 store=page.evaluate('Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))')if live else page.evaluate('window.__store');mount(store)
 ok('Completion persists after reload',page.locator('#done-MM6 [data-task="MM6-manual-report"]').count()==1)
 page.locator('#completed>summary').click();page.locator('#completed-programming>summary').click();page.locator('#done-MM6>summary').click();page.locator('#check-MM6-manual-report').uncheck()
 ok('Restore places report creation before helpers',page.locator('#todo-MM6>.task-list>.task').nth(2).get_attribute('data-task')=='MM6-manual-report')
 page.get_by_role('button',name='Kepware',exact=True).click();page.locator('#todo-K-MM6>summary').click();page.locator('#how-K-MM6-v2-tags>summary').click()
 ok('Kepware labels and addresses use CSI_Report','CSI_Report' in page.locator('#tag-map').inner_text() and 'DB950,DINT156' in page.locator('#tag-map').inner_text() and 'DB950,REAL40' in page.locator('#tag-map').inner_text())
 with page.expect_download() as downloaded:page.get_by_role('button',name='Download complete address reference').click()
 obj=downloaded.value;csv=Path(obj.path()).read_text();ok('CSV name uses CSI and retains every field','CSI2' not in obj.suggested_filename and len(csv.splitlines())==61)
 page.locator('#tools>summary').click()
 with page.expect_download() as downloaded:page.get_by_role('button',name='Export progress').click()
 backup=json.loads(Path(downloaded.value.path()).read_text());ok('Export preserves user notes verbatim',backup['notes']['MM6-manual-setup']==seed['notes']['MM6-manual-setup'])
 if live:
  page.once('dialog',lambda dialog:dialog.accept())
  with page.expect_navigation(wait_until='networkidle'):page.locator('#import').set_input_files({'name':'progress.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
  ok('Import restores the same DB field',page.locator('#field-MM6-reportDbV2').input_value()=='950')
 mount({});page.screenshot(path=str(R/'tests/csi_desktop.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(R/'tests/csi_mobile.png'),full_page=True)
 ok('Mobile checklist stays within screen width',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.locator('#how-MM6-manual-main>summary').click();page.locator('#manual-body-CSI_Reporting-0>summary').click()
 ok('Mobile expanded code stays within screen width',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.locator('#manual-body-CSI_Reporting-0').scroll_into_view_if_needed();page.screenshot(path=str(R/'tests/csi_code_mobile.png'))
 if live:
  page.wait_for_function('navigator.serviceWorker.controller!==null',timeout=15000);context.set_offline(True);page.reload(wait_until='domcontentloaded')
  ok('Checklist and copied code work offline',page.locator('article.task').count()==33 and ''.join(page.locator('pre[data-block="CSI_Reporting"]').all_text_contents())==''.join(newp.code[('CSI_Reporting',str(i))]for i in range(8)))
  context.set_offline(False)
 ok('No JavaScript exceptions',not errors)
 browser.close()
server.shutdown()
report=dict(passed=len(checks),checks=checks,live_browser=live,scope='Live browser/localStorage/offline' if live else 'Injected document and test storage; live persistence/offline checked separately in CI',plc_tested=False)
(R/'tests/csi_branding_results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
