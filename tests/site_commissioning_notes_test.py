"""UI/documentation checks for the field-confirmed MM6 + MM4/MM5 commissioning overlay."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import json,os,threading

R=Path(__file__).resolve().parents[1]
d=json.loads((R/'content.json').read_text())
checks=[]
def ok(name,value):
 assert value,name
 checks.append(name)

ok('Task count unchanged',sum(len(g['tasks']) for g in d['groups']+d['kepware'])==42)
ok('Twelve-field report schema unchanged',len(d['schema'])==12 and [x['offset'] for x in d['schema']]==list(range(0,48,4)))
for m in ('MM4','MM5'):
 g=next(x for x in d['groups'] if x['id']==m)
 text=json.dumps(g)
 ok(m+' includes template clock hunt',all(x in text for x in ['Screen management','Templates','Display system time','HMI time synchronization mode','DB_Uhrstellen']))
 ok(m+' includes field robot gate sources',all(x in text for x in ['I500.4','I500.5','I500.6','M50.2','M50.3','DB20.DBX0.1']))
 ok(m+' includes first-cycle known-idle arm behavior','known-idle startup arm' in text and 'first real cycle' in text)

mm6=next(x for x in d['groups'] if x['id']=='MM6')
mm6text=json.dumps(mm6)
ok('MM6 site facts include DB56 and proven clock-template path',all(x in mm6text for x in ['DB56','DB98.DBX112.7','DB94.DBX29.6','I700.4','Display system time','Template']))

class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(R)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(server.server_port)+'/'

with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None,headless=True,args=['--no-sandbox'])
 ctx=b.new_context(viewport={'width':1280,'height':950},color_scheme='light')
 page=ctx.new_page(); errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url,wait_until='networkidle',timeout=10000)
 ok('All 42 tasks render',page.locator('article.task').count()==42)
 ok('All 66 authored MM6 reference networks remain',page.locator('[id^="compact-net-"]').count()==66)
 ok('Forced dark mode remains',page.evaluate("getComputedStyle(document.documentElement).colorScheme.includes('dark')"))
 ids=page.locator('[id]').evaluate_all('(xs)=>xs.map(x=>x.id)')
 ok('No duplicate DOM IDs',len(ids)==len(set(ids)))

 page.get_by_role('button',name='Kepware',exact=True).click()
 page.locator('#todo-K-MM6>summary').click()
 page.locator('#how-K-MM6-compact-tags>summary').click()
 box=page.locator('#tag-map')
 ok('MM6 map defaults to field-confirmed DB56',box.locator('input[type=number]').input_value()=='56')
 txt=box.inner_text()
 ok('MM6 map spells out TIA absolute and Kepware items',all(x in txt for x in ['%DB56.DBD0','DB56,REAL0','%DB56.DBD44','DB56,DINT44','TIA absolute','Kepware item']))

 page.locator('#todo-K-MM4>summary').click()
 page.locator('#how-K-MM4-compact-tags>summary').click()
 box4=page.locator('#tag-map-MM4'); inp4=box4.locator('input[type=number]')
 ok('MM4 DB remains target-confirmed rather than copied from MM6',inp4.input_value()=='')
 inp4.fill('156');inp4.press('Tab')
 txt4=box4.inner_text()
 ok('MM4 map generates both full address forms',all(x in txt4 for x in ['%DB156.DBD0','DB156,REAL0','%DB156.DBD44','DB156,DINT44']))

 page.get_by_role('button',name='MM4',exact=True).click()
 page.locator('#how-MM4-rollout-adapt>summary').click()
 ok('MM4 detailed clock guide renders',page.locator('#field-clock-MM4').count()==1)
 page.locator('#field-clock-MM4>summary').click()
 c=page.locator('#field-clock-MM4').inner_text()
 ok('MM4 guide points to inherited template and display source',all(x in c for x in ['Templates','Display system time','HMI time synchronization mode','FC_Uhr stellen','DB155 or FC53']))
 page.set_viewport_size({'width':390,'height':844})
 ok('Detailed panels stay within mobile width',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 ok('No browser script errors',not errors)
 b.close()

server.shutdown()
result=dict(passed=len(checks),checks=checks,plc_tested=False,scope='Documentation/UI regression; field-confirmed MM6 address presentation and MM4/MM5 detailed commissioning notes.')
(R/'tests/site_commissioning_notes_results.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
