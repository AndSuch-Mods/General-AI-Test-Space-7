from pathlib import Path
from playwright.sync_api import sync_playwright
import json
R=Path(__file__).resolve().parents[1]
checks=[]
def ok(name,val):
 assert val,name
 checks.append(name)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 ctx=b.new_context(viewport={'width':1365,'height':950},accept_downloads=True)
 page=ctx.new_page();errs=[];page.on('pageerror',lambda e:errs.append(str(e)))
 def mount(pg, store=None):
  init='<script>window.__testStore='+json.dumps(store or {})+';Object.defineProperty(window,"localStorage",{value:{getItem:k=>window.__testStore[k]??null,setItem:(k,v)=>window.__testStore[k]=String(v),clear:()=>window.__testStore={}}});</script>'
  pg.set_content(init+(R/'index.html').read_text(),wait_until='domcontentloaded')
 mount(page)
 ok('84 independent checklist tasks rendered',page.locator('article.task').count()==84)
 page.locator('#programming > summary').click()
 page.locator('#todo-MM4 > summary').click()
 page.locator('#config-MM4 > summary').click()
 page.locator('#cfg-MM4-db').fill('950')
 page.locator('#cfg-MM4-ip').fill('LOCAL-TEST-NOT-A-REAL-IP')
 page.locator('#detail-MM4-backup > summary').click()
 page.locator('#detail-MM4-backup textarea').fill('Browser test note')
 page.locator('#check-MM4-backup').check()
 ok('Completion moves only its machine task',page.locator('#done-MM4 [data-task="MM4-backup"]').count()==1 and page.locator('#todo-MM5 [data-task="MM5-backup"]').count()==1)
 ok('Progress counter updates',page.locator('#totalText').inner_text()=='1 of 84 complete')
 saved=page.evaluate('window.__testStore'); page.close(); page=ctx.new_page(); page.on('pageerror',lambda e:errs.append(str(e))); mount(page,saved)
 ok('Completion survives serialized-state rehydration',page.locator('#done-MM4 [data-task="MM4-backup"]').count()==1)
 ok('Notes and configuration survive serialized-state rehydration',page.locator('#detail-MM4-backup textarea').input_value()=='Browser test note' and page.locator('#cfg-MM4-db').input_value()=='950')
 page.locator('[data-nav="completed"]').click()
 page.locator('#completed-programming > summary').click()
 page.locator('#done-MM4 > summary').click()
 page.locator('#check-MM4-backup').uncheck()
 ok('Restoring returns task to original group and order',page.locator('#todo-MM4 .tasks > article').first.get_attribute('data-task')=='MM4-backup')
 page.locator('#collapse').click()
 page.locator('#programming > summary').click();page.locator('#kepware > summary').click();page.locator('#todo-K-MM4 > summary').click();page.locator('#addresses-K-MM4 > summary').click()
 ok('Kepware map uses chosen DB number',page.locator('#map-MM4').inner_text().find('DB950,DINT16')>=0 and page.locator('#map-MM4').inner_text().find('DB950,REAL40')>=0)
 with page.expect_download() as dl:page.locator('#map-MM4 button').click()
 csv=Path(dl.value.path()).read_text();ok('CSV quotes addresses containing commas','"DB950,REAL40"' in csv)
 page.locator('#collapse').click();page.locator('#instructions > summary').click()
 page.locator('#i-network > summary').scroll_into_view_if_needed()
 y=page.locator('#i-network > summary').bounding_box()['y']
 page.locator('#i-network > summary').click();page.wait_for_timeout(80)
 ok('Expanding instruction preserves summary position',abs(page.locator('#i-network > summary').bounding_box()['y']-y)<2)
 # Return click can be below page bottom only in exceptional edge cases; test interior collapse.
 y=page.locator('#i-network > summary').bounding_box()['y'];page.locator('#i-network > summary').click();page.wait_for_timeout(80)
 ok('Collapsing instruction preserves summary position',abs(page.locator('#i-network > summary').bounding_box()['y']-y)<2)
 page.locator('#collapse').click();page.locator('#programming > summary').click();page.locator('#todo-MM4 > summary').click()
 page.locator('#check-MM4-clock').scroll_into_view_if_needed();before=page.locator('[data-task="MM4-retention"]').bounding_box()['y'];page.locator('#check-MM4-clock').check();page.wait_for_timeout(80)
 after=page.locator('[data-task="MM4-retention"]').bounding_box()['y'];ok('Completing task preserves next-row anchor',abs(before-after)<2)
 with page.expect_download() as dl:page.locator('#export').click()
 backup=json.loads(Path(dl.value.path()).read_text());ok('Export includes independent notes and progress',backup['notes']['MM4-backup']=='Browser test note' and 'MM4-clock' in backup['done'])
 # Save clean desktop state for screenshot without test credentials.
 page.evaluate("localStorage.clear()");saved=page.evaluate('window.__testStore'); page.close(); page=ctx.new_page(); page.on('pageerror',lambda e:errs.append(str(e))); mount(page,saved)
 page.locator('#programming > summary').click();page.locator('#todo-MM4 > summary').click();page.screenshot(path=str(R/'tests/desktop.png'),full_page=True)
 # All embedded downloads really contain source, not a failed fetch URL.
 page.locator('#resources > summary').click()
 with page.expect_download() as dl:page.get_by_role('button',name='MM6 / 1500 core reference').click()
 ok('Source download contains code and disabled default','ObserverEnable : DInt := 0' in Path(dl.value.path()).read_text())
 ok('No browser JavaScript exceptions',not errs)
 mobile=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
 mp=mobile.new_page();mount(mp);mp.locator('#programming > summary').click();mp.locator('#todo-MM6 > summary').click()
 ok('Mobile layout has no horizontal page overflow',mp.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
 mp.screenshot(path=str(R/'tests/mobile.png'),full_page=True)
 b.close()
(R/'tests/browser-results.json').write_text(json.dumps({'passed':len(checks),'checks':checks,'scope':'Chromium desktop/mobile using injected document and a storage test double because container browser navigation is policy-blocked. State serialization, DOM and layout tested; live navigation, native localStorage persistence and service-worker lifecycle not tested here. No PLC execution.'},indent=2))
print('PASS',len(checks),'browser checks')
