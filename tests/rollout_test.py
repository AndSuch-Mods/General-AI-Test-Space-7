"""Current machine-suffix/copy checklists: text structure and browser regression tests.
No Siemens compiler, machine connection, live data or legacy code conversion is exercised.
"""
from pathlib import Path
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
import hashlib,json,re,sys,os,threading
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from machine_rollout import transform,names,BUILD
checks=[]
def ok(name,condition):assert condition,name;checks.append(name)
base=json.loads((ROOT/'tests/rollout_baseline.json').read_text())
d=json.loads((ROOT/'content.json').read_text());ref=json.loads((ROOT/'compact_reference.json').read_text())
oldm=next(g for g in base['data']['groups']if g['id']=='MM6');m=next(g for g in d['groups']if g['id']=='MM6')
ok('Exactly the same twelve report fields and offsets',d['schema']==base['data']['schema']and len(d['schema'])==12)
ok('MM6 FB/network/row reference differs only by approved symbol names',ref['blocks']=={'CSI_Reporting_MM6':transform(base['reference']['blocks']['CSI_Reporting'],'MM6')})
ok('All 66 MM6 networks retain their order and number',[n['number']for n in ref['blocks']['CSI_Reporting_MM6']['networks']]==list(range(1,67)))
ok('First four completed MM6 steps change names only',all(transform(a,'MM6')==b for a,b in zip(oldm['tasks'][:4],m['tasks'][:4])))
ok('All existing MM6 checklist task IDs remain unchanged',[t['id']for t in oldm['tasks']]==[t['id']for t in m['tasks']])
class Rungs(HTMLParser):
 def __init__(self):super().__init__();self.inside=False;self.text=[]
 def handle_starttag(self,tag,attrs):
  if tag=='pre'and 'lad-diagram'in dict(attrs).get('class',''):self.inside=True;self.text.append('')
 def handle_endtag(self,tag):
  if tag=='pre':self.inside=False
 def handle_data(self,s):
  if self.inside:self.text[-1]+=s
for a,b in zip(oldm['tasks'],m['tasks']):
 x,y=Rungs(),Rungs();x.feed(transform(a,'MM6')['body']);y.feed(b['body']);assert x.text==y.text,a['id']
ok('Every displayed MM6 ladder drawing is unchanged except report DB names',True)
outs=[a.get('out')for n in ref['blocks']['CSI_Reporting_MM6']['networks']for a in n['actions']if a.get('out')]
ok('MM6 only writes local state and its own report DB',all(s.startswith(('#','"CSI_Report_MM6".'))for s in outs))
for machine in ('MM4','MM5'):
 g=next(g for g in d['groups']if g['id']==machine);txt=json.dumps(g)
 ok(machine+' has full observe-to-copy-to-verification progression',len(g['tasks'])==11 and g['tasks'][0]['id']==machine+'-rollout-observe'and g['tasks'][-1]['id']==machine+'-rollout-verify')
 ok(machine+' exact candidate addresses and observed waveform gate',all(s in txt for s in ['DB98.DBX112.7','Q44.0','DB94.DBX29.4','I505.7','low','returns high']))
 ok(machine+' declares legacy compatibility limitation instead of inventing a direct port','WinLC' in txt and 'No complete legacy rung conversion' in txt and 'no-entry' in txt)
 ok(machine+' copied numbering, instance and real input review are explicit',all(s in txt for s in ['number conflict','Do not copy the instance DB','RobotDataValid','AbortCycle','ProductionEligible']))
 ok(machine+' no blanket removal of input or CPU checks','remove the <code>%DB200.DBX49.3</code> contact from THIS NEW OBSERVER' in txt and 'Never set or reset the original configuration bits' in txt)
ok('MM5 prefers the verified target-compatible MM4 donor','verified MM4' in json.dumps(next(g for g in d['groups']if g['id']=='MM5')))
ok('Each Kepware machine has its own map',set(t['map']for g in d['kepware']for t in g['tasks']if t.get('map'))=={'MM4','MM5','MM6'})
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start();url='http://127.0.0.1:'+str(server.server_port)+'/'
with sync_playwright()as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium'if Path('/usr/bin/chromium').exists()else None,headless=True,args=['--no-sandbox'])
 ctx=b.new_context(viewport={'width':1280,'height':980},color_scheme='light',accept_downloads=True)
 page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));live=True
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
   page.close();page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   init='<script>window.__store='+json.dumps(store or {})+';Object.defineProperty(window,"localStorage",{value:{getItem:k=>window.__store[k]??null,setItem:(k,v)=>window.__store[k]=v}});</script>'
   page.set_content(init+(ROOT/'index.html').read_text(),wait_until='domcontentloaded')
 first4=[t['id']for t in oldm['tasks'][:4]]
 seed={'version':3,'done':{**{i:'today'for i in first4},'MM4-start':'earlier'},'notes':{'MM6-compact-report':'Do not rewrite this CSI_Report user note','MM4-start':'Three dots seen previously'},'fields':{'MM6':{'reportDbCompact':'56'}},'open':{'programming':True,'todo-MM6':True}}
 load({'csi-machine-reporting-checklist-v3':json.dumps(seed)})
 ok('Dark mode preserved even with light browser preference',page.evaluate("getComputedStyle(document.documentElement).colorScheme.includes('dark')"))
 count=sum(len(g['tasks'])for g in d['groups']+d['kepware'])
 ok('All 42 current tasks render',page.locator('article.task').count()==count==42)
 ok('All first four MM6 completion checks survive',all(page.locator('#done-MM6 [data-task="'+i+'"]').count()==1 for i in first4))
 ok('User notes are never renamed',page.locator('#note-MM6-compact-report textarea').input_value()==seed['notes']['MM6-compact-report'])
 ok('Previous MM4 observation retained as history not a false new pass','Three dots seen previously'in page.locator('#legacy-records').text_content()and not page.locator('#check-MM4-rollout-observe').is_checked())
 ids=page.locator('[id]').evaluate_all('(ns)=>ns.map(n=>n.id)')
 ok('No duplicated DOM IDs in instructions, rungs or maps',len(ids)==len(set(ids)))
 page.locator('#how-MM6-compact-section-2>summary').click()
 ok('MM6 step five includes existing-block rename without a new numbering step','Rename your existing MM6'in page.locator('#how-MM6-compact-section-2').inner_text())
 page.locator('#rollout-mm6-rename-step5>summary').click()
 ok('New main, report and instance names are explicit',all(s in page.locator('#rollout-mm6-rename-step5').inner_text()for s in ['CSI_Report_MM6','CSI_Reporting_MM6','CSI_Reporting_MM6_DB']))
 summary=page.locator('#compact-net-25>summary');summary.scroll_into_view_if_needed();y=summary.bounding_box()['y'];summary.click();page.wait_for_timeout(100)
 ok('Expanding an existing rung preserves heading position',abs(y-summary.bounding_box()['y'])<2)
 page.get_by_role('button',name='MM4',exact=True).click();page.locator('#how-MM4-rollout-observe>summary').click()
 ok('MM4 opens directly to a six-row watch check',page.locator('#how-MM4-rollout-observe tbody tr').count()==6)
 page.locator('#how-MM4-rollout-observe>summary').click();page.locator('#check-MM4-rollout-observe').scroll_into_view_if_needed()
 y=page.locator('[data-task="MM4-rollout-target"]').bounding_box()['y'];page.locator('#check-MM4-rollout-observe').check();page.wait_for_timeout(100)
 ok('New machine checklist complete/anchor behavior preserved',page.locator('#done-MM4 [data-task="MM4-rollout-observe"]').count()==1 and abs(page.locator('[data-task="MM4-rollout-target"]').bounding_box()['y']-y)<2)
 page.get_by_role('button',name='Kepware',exact=True).click()
 for machine,db in [('MM4','156'),('MM5','256'),('MM6','56')]:
  page.locator('#todo-K-'+machine+'>summary').click();page.locator('#how-K-'+machine+'-compact-tags>summary').click()
  box=page.locator('#'+('tag-map'if machine=='MM6'else'tag-map-'+machine))
  inp=box.locator('input[type=number]')
  if machine!='MM6':ok(machine+' does not inherit MM6 DB56',inp.input_value()=='')
  inp.fill(db);inp.press('Tab')
  txt=box.inner_text()
  ok(machine+' map has independent DB and matching twelve offsets',box.locator('tbody tr').count()==12 and 'DB'+db+',REAL0'in txt and 'DB'+db+',DINT44'in txt and 'CSI_Report_'+machine in txt)
  with page.expect_download()as dl:box.get_by_role('button',name='Download complete address reference').click()
  f=dl.value;csv=Path(f.path()).read_text()
  ok(machine+' CSV uses its machine and DB only',f.suggested_filename.startswith('CSI_Report_'+machine+'_DB'+db)and len(csv.splitlines())==13 and '"'+machine+'"'in csv and '"DB'+db+',DINT28"'in csv)
 ok('All three entered DBs remain independent',page.locator('#kepware-db-MM4').input_value()=='156'and page.locator('#kepware-db-MM5').input_value()=='256'and page.locator('#kepware-db').input_value()=='56')
 page.locator('#tools>summary').click()
 with page.expect_download()as dl:page.get_by_role('button',name='Export progress',exact=True).click()
 backup=json.loads(Path(dl.value.path()).read_text())
 ok('Export preserves notes, MM6 progress and three separate DB values',backup['notes']==seed['notes']and backup['fields']['MM4']['reportDbCompact']=='156'and backup['fields']['MM5']['reportDbCompact']=='256'and backup['fields']['MM6']['reportDbCompact']=='56')
 if live:
  page.once('dialog',lambda dialog:dialog.accept())
  with page.expect_navigation(wait_until='networkidle'):page.locator('#import').set_input_files({'name':'progress.json','mimeType':'application/json','buffer':json.dumps(backup).encode()})
 else:load({'csi-machine-reporting-checklist-v3':json.dumps(backup)})
 ok('Progress reload/import keeps machine DBs and completion',page.locator('#field-MM6-reportDbCompact').input_value()=='56'and page.locator('#done-MM4 [data-task="MM4-rollout-observe"]').count()==1)
 page.locator('#completed>summary').click();page.locator('#completed-programming>summary').click();page.locator('#done-MM4>summary').click();page.locator('#check-MM4-rollout-observe').uncheck()
 ok('Restore returns observation to the first MM4 step',page.locator('#todo-MM4>.task-list>.task').first.get_attribute('data-task')=='MM4-rollout-observe')
 load({});page.get_by_role('button',name='MM4',exact=True).click();page.locator('#how-MM4-rollout-observe>summary').click();page.screenshot(path=str(ROOT/'tests/rollout_desktop.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':844})
 ok('Expanded machine watch/checklist stays within mobile width',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.screenshot(path=str(ROOT/'tests/rollout_mobile.png'),full_page=True)
 if live:
  page.wait_for_function('navigator.serviceWorker.controller!==null',timeout=15000);ctx.set_offline(True);page.reload(wait_until='domcontentloaded')
  ok('Current machine guides and references work offline',page.locator('article.task').count()==42 and page.locator('#tag-map-MM4').count()==1)
 ok('No browser JavaScript exceptions',not errors)
 b.close()
server.shutdown()
result=dict(passed=len(checks),checks=checks,live_browser=live,scope='Live browser/storage/offline'if live else'Injected HTML/storage fallback; true browser persistence/offline validated in CI only',plc_tested=False,legacy_port_supplied=False)
(ROOT/'tests/rollout_results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
