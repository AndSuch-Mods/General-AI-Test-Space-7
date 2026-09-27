"""Apply CSI-only names and checklist branding without changing reporting behavior.

The hash-checked V2 source remains an immutable derivation reference. Only symbol
names change in the current guide and optional renamed source, never addresses,
field offsets, constants, executable ordering, or browser checklist IDs.
"""
from pathlib import Path
from html import escape
import copy, json, hashlib, re

NAMES = {
    'CSI2_CycleMonitor':'CSI_Reporting',
    'CSI2_MM6_Instance':'CSI_Reporting_DB',
    'CSI2_MM6_Startup':'CSI_Startup',
    'CSI2_MM6_Run':'CSI_Run',
    'CSI2_PeriodCounter':'CSI_PeriodCounter',
    'CSI2_AddElapsed':'CSI_AddElapsed',
    'CSI2_DayNumber':'CSI_DayNumber',
    'CSI2_Increment':'CSI_Increment',
    'CSI2_Report':'CSI_Report',
    'CSI2_Setup':'CSI_Setup',
}
BUILD='2026-09-27-csi-checklist-v6-dark'

def rename_text(text):
    for old,new in NAMES.items():text=text.replace(old,new)
    text=text.replace('CSI/CSI2','CSI').replace('CSI2_','CSI_').replace('CSI2','CSI')
    return text

def rename_data(original):
    d=copy.deepcopy(original)
    def visit(item):
        if isinstance(item,dict):
            # IDs/storage-field keys stay stable across the naming-only update.
            return {k:(v if k in ('id','fields') else visit(v)) for k,v in item.items()}
        if isinstance(item,list):return [visit(x) for x in item]
        if isinstance(item,str):return rename_text(item)
        return item
    d=visit(d)
    for g in d['groups']+d['kepware']:
        for t in g['tasks']:
            if 'fields' in t:t['fields']=[(k,rename_text(label),typ) for k,label,typ in t['fields']]
            if t['id']=='MM6-manual-instance':
                t['body']=t['body'].replace('Do not attach it to <code>CSI_Reporting</code> from the older import route. This manual route uses <code>CSI_Reporting</code>.','Select the new <code>CSI_Reporting</code> FB. Do not change the type of an existing instance DB that belongs to another block.')
            if t['id']=='MM6-manual-folder':
                t['body']=t['body'].replace('If an earlier CSI installation is already present, do not create over it or change its running instance type; use a separate learning copy for review.','If any listed name is already used, stop rather than overwrite it or change a running instance type. The name check is against your current TIA project.')
            if t['id']=='MM6-v2-tags':
                t['body']+='<p>Confirm any saved DB number below belongs to <code>CSI_Report</code> before using it in Kepware.</p>'
    d['build']=BUILD
    return d

def renamed_source(text):
    return rename_text(text)

ICON_SVG='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#193d50"/><stop offset="1" stop-color="#102e3b"/></linearGradient></defs><rect width="512" height="512" fill="url(#bg)"/><circle cx="438" cy="47" r="188" fill="#3d8c80" opacity=".12"/><rect x="120" y="108" width="284" height="348" rx="28" fill="#091f29" opacity=".32"/><rect x="108" y="91" width="284" height="348" rx="27" fill="#f3f8f2"/><rect x="192" y="67" width="116" height="63" rx="16" fill="#83d7b4"/><rect x="227" y="85" width="46" height="11" rx="5.5" fill="#244d4d"/><g fill="none" stroke-linecap="round" stroke-linejoin="round"><rect x="151" y="169" width="39" height="39" rx="7" stroke="#218773" stroke-width="6"/><path d="m158 187 10 10 22-27" stroke="#218773" stroke-width="8"/><path d="M216 183h122M216 203h84" stroke="#547784" stroke-width="9"/><rect x="151" y="254" width="39" height="39" rx="7" stroke="#218773" stroke-width="6"/><path d="m158 272 10 10 22-27" stroke="#218773" stroke-width="8"/><path d="M216 268h122M216 288h70" stroke="#547784" stroke-width="9"/><rect x="151" y="339" width="39" height="39" rx="7" stroke="#d8a957" stroke-width="6"/><path d="M216 353h122M216 373h94" stroke="#547784" stroke-width="9"/></g></svg>'''

HEADER='''<header><div class="header-line"><div class="brand"><div class="brand-emblem" aria-hidden="true">'''+ICON_SVG+'''</div><div><p class="brand-label">CSI / machine reporting</p><h1>Machine checklist</h1></div></div><span class="revision">27 Sep · CSI dark</span></div><nav aria-label="Jump to checklist"><button data-open="todo-MM6" aria-pressed="true">MM6</button><button data-open="todo-MM4" aria-pressed="false">MM4</button><button data-open="todo-MM5" aria-pressed="false">MM5</button><button data-open="kepware" aria-pressed="false">Kepware</button></nav><div class="progress-row"><span id="progress-text"></span><progress id="progress" value="0" max="33" aria-label="Completed steps"></progress><span id="saved"></span></div></header>'''

APP_EXTRA='''
// Restore open declaration/code panels after a symbol-only rename; never rewrite user notes.
const csiPanelNames=__NAMES__;
for(const oldKey of Object.keys(state.open)){
 let key=oldKey;
 for(const [oldName,newName] of Object.entries(csiPanelNames))key=key.replaceAll(oldName,newName);
 if(key!==oldKey&&!(key in state.open))state.open[key]=state.open[oldKey];
}
queueMicrotask(()=>document.querySelectorAll('details[id]').forEach(d=>{if(Object.prototype.hasOwnProperty.call(state.open,d.id))d.open=state.open[d.id];}));
document.addEventListener('click',event=>{
 const button=event.target.closest('nav [data-open]');
 if(button)document.querySelectorAll('nav [data-open]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
});
'''.replace('__NAMES__',json.dumps(NAMES))

def decorate_markup(markup):
    markup=re.sub(r'<header>.*?</header>',lambda _:HEADER,markup,count=1,flags=re.S)
    icons='<link rel="icon" type="image/svg+xml" href="./checklist-icon.svg?v=5"><link rel="icon" type="image/png" sizes="32x32" href="./checklist-icon-32.png?v=5"><link rel="apple-touch-icon" sizes="180x180" href="./apple-touch-icon.png?v=5"><meta name="apple-mobile-web-app-title" content="Checklist">'
    markup=markup.replace('<link rel="manifest" href="./manifest.webmanifest">','<link rel="manifest" href="./manifest.webmanifest?v=5">'+icons,1)
    markup=markup.replace('<meta name="theme-color" content="#17675d">','<meta name="theme-color" content="#081118">',1)
    return markup

def write_assets(root):
    from PIL import Image, ImageDraw
    root=Path(root)
    (root/'checklist-icon.svg').write_text(ICON_SVG)
    # Raster icons use the same geometry as the SVG, with supersampled strokes.
    scale=3;im=Image.new('RGB',(512*scale,512*scale));pix=im.load()
    for y in range(512*scale):
        f=y/(512*scale-1);c=tuple(round(a+(b-a)*f) for a,b in zip((25,61,80),(16,46,59)))
        for x in range(512*scale):pix[x,y]=c
    p=ImageDraw.Draw(im)
    def box(coords,rad,fill,outline=None,w=1):p.rounded_rectangle(tuple(int(v*scale) for v in coords),int(rad*scale),fill=fill,outline=outline,width=w*scale)
    def line(points,fill,w):
        pts=[(int(x*scale),int(y*scale)) for x,y in points];p.line(pts,fill=fill,width=w*scale,joint='curve')
        for x,y in (pts[0],pts[-1]):p.ellipse((x-w*scale/2,y-w*scale/2,x+w*scale/2,y+w*scale/2),fill=fill)
    box((120,108,404,456),28,'#0f2934');box((108,91,392,439),27,'#f3f8f2');box((192,67,308,130),16,'#83d7b4');box((227,85,273,96),5.5,'#244d4d')
    for y,checked,short in [(169,True,84),(254,True,70),(339,False,94)]:
        box((151,y,190,y+39),7,None,'#218773' if checked else '#d8a957',6)
        if checked:line([(158,y+18),(168,y+28),(190,y+1)],'#218773',8)
        line([(216,y+14),(338,y+14)],'#547784',9);line([(216,y+34),(216+short,y+34)],'#547784',9)
    for name,size in [('checklist-icon-32.png',32),('apple-touch-icon.png',180),('checklist-icon-192.png',192),('checklist-icon-512.png',512)]:
        im.resize((size,size),Image.Resampling.LANCZOS).save(root/name,optimize=True)
    manifest=dict(name='CSI machine checklist',short_name='Checklist',start_url='./',scope='./',display='standalone',background_color='#081118',theme_color='#081118',icons=[dict(src='./checklist-icon-192.png?v=5',sizes='192x192',type='image/png',purpose='any maskable'),dict(src='./checklist-icon-512.png?v=5',sizes='512x512',type='image/png',purpose='any maskable')])
    (root/'manifest.webmanifest').write_text(json.dumps(manifest,indent=2))
    assets=['./index.html','./manifest.webmanifest','./checklist-icon.svg','./checklist-icon-32.png','./apple-touch-icon.png','./checklist-icon-192.png','./checklist-icon-512.png','./downloads/MM6_CSI_Reporting.scl']
    sw="const CACHE='machine-reporting-csi-checklist-v6-dark-20260927';\nconst HOME=new URL('./index.html',self.location.href).href;\nconst ASSETS="+json.dumps(assets)+";\n"
    sw+='''self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('machine-reporting-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method!=='GET'||u.origin!==self.location.origin||!u.pathname.startsWith(new URL(self.registration.scope).pathname))return;e.respondWith(fetch(e.request).then(r=>{if(r.ok){const clone=r.clone();e.waitUntil(caches.open(CACHE).then(c=>c.put(e.request,clone)));}return r;}).catch(()=>caches.match(e.request,{ignoreSearch:true}).then(r=>r||(e.request.mode==='navigate'?caches.match(HOME):Response.error()))));});'''
    (root/'sw.js').write_text(sw)
    raw=(root/'downloads/MM6_Reporting_V2.scl').read_text(encoding='utf-8')
    (root/'downloads/MM6_CSI_Reporting.scl').write_text(renamed_source(raw),encoding='utf-8')


def install(root=None):
    root=Path(root or Path(__file__).parent)
    p=root/'build_html.py';s=p.read_text()
    if 'from csi_branding import' not in s:
        s=s.replace('from manual_steps import manual_data','from manual_steps import manual_data\nfrom csi_branding import rename_data, renamed_source, decorate_markup, write_assets',1)
        assert 'D=manual_data(build_data())' in s
        s=s.replace('D=manual_data(build_data())','D=rename_data(manual_data(build_data()))',1)
        s=s.replace("source=(R/'downloads/MM6_Reporting_V2.scl').read_text(encoding='utf-8')","source=renamed_source((R/'downloads/MM6_Reporting_V2.scl').read_text(encoding='utf-8'))",1)
        s=s.replace("css=(R/'style.css').read_text()","css=(R/'style.css').read_text()+'\\n'+(R/'csi_theme.css').read_text()",1)
        s=s.replace("(R/'index.html').write_text(markup)","(R/'index.html').write_text(decorate_markup(markup))",1)
        s+='\nwrite_assets(R)\n'
        p.write_text(s)
    p=root/'app.js';s=p.read_text()
    if '// Restore open declaration/code panels' not in s:
        s=rename_text(s).replace('MM6_Reporting_V2.scl','MM6_CSI_Reporting.scl')
        assert '\nbuild();' in s
        s=s.replace('\nbuild();','\n'+APP_EXTRA+'\nbuild();',1);p.write_text(s)
    # Existing UI tests retain every old assertion; expected body receives only the same rename.
    p=root/'tests/manual_checklist_test.py'
    if p.exists():
        s=p.read_text()
        if 'from csi_branding import rename_text' not in s:
            s=s.replace('from manual_steps import parse_source,body_sections','from manual_steps import parse_source,body_sections\nfrom csi_branding import rename_text',1)
            s=s.replace("b=parse_source()['CSI_Reporting'];texts=", "b=dict(parse_source()['CSI_Reporting']);b['body']=rename_text(b['body']);texts=")
            p.write_text(s)
    note='''\n## CSI naming and checklist identity\n\nThe active manual route now uses CSI_Report, CSI_Setup, CSI_Reporting, CSI_Reporting_DB, CSI_Run, CSI_Startup and CSI_ helpers. csi_branding.py applies a symbol-only mapping after manual_steps.py; field offsets, schema version 2 and all executable behavior are unchanged. The immutable V2 file is retained for derivation/tests only. The optional current source is downloads/MM6_CSI_Reporting.scl, not the old import route. Do not restore CSI2 names in the active page or copied code.\n\nThe clipboard/checkmark identity is provided as SVG favicon, PNG favicon, iOS touch icon and installable-app icons. csi_theme.css styles the existing compact checklist without adding tasks. Keep the existing localStorage key, task IDs, notes and recorded DB fields; verify a recorded number belongs to CSI_Report before using it. Test scrolling, persistence, copying and offline operation. Do not change billing settings or enable paid runners. The publishing workflow retains no extra screenshot artifacts.\n'''
    for name in ['README.md','AGENTS.md']:
        p=root/name
        if p.exists():
            text=p.read_text()
            if '## CSI naming and checklist identity' not in text:p.write_text(text+note)
    print('CSI names and checklist branding hook installed.')

if __name__=='__main__':
    import sys
    if '--install' in sys.argv:install()
