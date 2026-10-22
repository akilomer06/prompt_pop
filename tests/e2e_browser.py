"""Real Chromium journey against an isolated server and database. Never changes the event database."""
import io
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
TEMP=tempfile.TemporaryDirectory(prefix='promptpop-browser-')
SPLIT=os.getenv('E2E_SPLIT_HOSTING') == '1'
BACKEND='http://127.0.0.1:8011'
URL='https://127.0.0.1:8012' if SPLIT else BACKEND
os.environ['DATABASE_URL']='sqlite:///'+str(Path(TEMP.name)/'event.db').replace('\\','/')
os.environ['STORAGE_DIR']=str(Path(TEMP.name)/'assets')
os.environ['APP_ORIGIN']=URL
os.environ['APP_ENV']='development'
os.environ['ASSET_STORAGE']='local'
os.environ.pop('DATABASE_SCHEMA',None)
os.environ['COOKIE_SECURE']='true' if SPLIT else 'false'
os.environ['SERVE_FRONTEND']='false' if SPLIT else 'true'
for key in ('APP_ORIGINS','BOOTSTRAP_ADMIN_PASSWORD','BOOTSTRAP_ADMIN_USERNAME'): os.environ.pop(key,None)
os.environ.pop('EVALUATOR_URL',None)
from PIL import Image, ImageDraw
from backend.seed import initialize
from backend.models import Session, User, engine
from backend.security import password_hash
from playwright.sync_api import sync_playwright, expect

initialize()
PASSWORD=secrets.token_urlsafe(18)
with Session.begin() as db: db.add(User(id='browser-admin',username='director',password=password_hash(PASSWORD),role='admin'))
OUT=ROOT/'test-results'/('split' if SPLIT else 'combined');OUT.mkdir(parents=True,exist_ok=True)
AXE=(ROOT/'frontend/node_modules/axe-core/axe.min.js').read_text(encoding='utf-8')
audit_results={}
errors=[]
checks=[]

def fixture_image():
    image=Image.new('RGB',(960,720),'#e4eaf1')
    d=ImageDraw.Draw(image)
    d.rectangle((0,480,960,720),fill='#b8c6d7')
    d.ellipse((250,470,760,570),fill='#99a9bc')
    d.ellipse((280,120,680,520),fill='#3264c3')
    d.ellipse((340,155,480,255),fill='#5582d4')
    d.rectangle((135,360,310,535),fill='#edb877')
    buffer=io.BytesIO();image.save(buffer,'PNG');return buffer.getvalue()

IMAGE=fixture_image()
IMAGE_PATH=Path(TEMP.name)/'creation.png';IMAGE_PATH.write_bytes(IMAGE)

def capture(page,name,mobile=False):
    page.wait_for_load_state('networkidle')
    page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
    page.evaluate(AXE)
    result=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))}")
    audit_results[name]=result
    (OUT/'browser-report.json').write_text(json.dumps(dict(checks=checks,browser_errors=errors,accessibility=audit_results),indent=2),encoding='utf-8')
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'),name+' overflows viewport'

def login(page,username,password):
    page.goto(URL)
    page.wait_for_load_state('networkidle')
    page.get_by_label('Account',exact=True).fill(username)
    page.get_by_label('Access code',exact=True).fill(password)
    page.get_by_role('button',name='Enter the competition').click()

def post(context,path,data):
    response=context.request.post(URL+'/api'+path,data=data)
    assert response.ok,(path,response.status,response.text())
    return response.json()

def control(context,action,task_id): return post(context,'/admin/control',dict(action=action,task_id=task_id))

log=open(Path(TEMP.name)/'server.log','w',encoding='utf-8')
server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8011'],cwd=ROOT,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
proxy=None
try:
    import httpx
    for _ in range(100):
        try:
            if httpx.get(BACKEND+'/api/health').status_code==200: break
        except Exception: pass
        time.sleep(.15)
    else: raise RuntimeError('Browser test server did not start.')
    if SPLIT:
        from split_proxy import start_proxy
        assert httpx.get(BACKEND+'/').status_code==404,'Render must run as API only'
        proxy,proxy_thread=start_proxy(ROOT,TEMP.name,BACKEND)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        admin=browser.new_context(viewport={'width':1440,'height':1000},ignore_https_errors=SPLIT)
        page=admin.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(URL);capture(page,'login-desktop')
        # Keyboard-only authentication; labels and native form semantics.
        page.keyboard.press('Tab');expect(page.get_by_label('Account',exact=True)).to_be_focused()
        page.keyboard.type('director');page.keyboard.press('Tab');page.keyboard.type(PASSWORD);page.keyboard.press('Enter')
        page.get_by_role('heading',name='Control room',exact=True).wait_for()
        if SPLIT:
            cookie=next(c for c in admin.cookies() if c['name']=='pp_session')
            assert cookie['secure'] and cookie['httpOnly'] and cookie['sameSite']=='Strict'
            assert admin.request.get(URL+'/api/does-not-exist').status==404
            payload=io.BytesIO()
            Image.frombytes('RGB',(1500,1500),os.urandom(1500*1500*3)).save(payload,'PNG')
            assert len(payload.getvalue())>4.5*1024*1024
            uploaded=admin.request.post(URL+'/api/admin/tasks/2/reference',multipart={'image':{'name':'large.png','mimeType':'image/png','buffer':payload.getvalue()}})
            assert uploaded.ok,uploaded.text()
            assert uploaded.headers['cache-control']=='no-store'
            checks.append('Split HTTPS frontend/API topology: Secure host-only sessions, private cache policy, API 404 and multipart upload above 4.5 MB')
        capture(page,'control-empty-desktop')
        page.get_by_role('button',name='Teams',exact=True).click()
        page.get_by_role('button',name='Register team',exact=True).click()
        page.get_by_label('Team name',exact=True).fill('Studio North')
        page.get_by_label('Members',exact=False).fill('Maya, Omar')
        page.get_by_role('button',name='Create team & access code').click()
        page.locator('.credentials dd').first.wait_for()
        creds=page.locator('.credentials dd').all_text_contents()
        other_creds=post(admin,'/admin/teams',dict(name='Studio South',members=['Lea','Noah']))
        capture(page,'teams-desktop')
        checks.append('Team registration and one-time credentials through the browser')
        team=browser.new_context(viewport={'width':1440,'height':1000},ignore_https_errors=SPLIT)
        workspace=team.new_page();workspace.on('pageerror',lambda e:errors.append(str(e)))
        login(workspace,*creds)
        workspace.get_by_text('Your ideas are up next.',exact=True).wait_for()
        capture(workspace,'waiting-desktop')
        second=browser.new_context(viewport={'width':1100,'height':900},ignore_https_errors=SPLIT)
        second.request.post(URL+'/api/auth/login',data=dict(username=other_creds['username'],password=other_creds['access_code']))
        second_page=second.new_page();second_page.goto(URL)
        page.get_by_role('button',name='Rounds & content',exact=True).click()
        page.get_by_role('button',name='Release & start task',exact=True).click()
        dialog=page.get_by_role('dialog');expect(dialog).to_be_visible()
        for _ in range(5):
            page.keyboard.press('Tab')
            assert page.evaluate('document.querySelector("dialog").contains(document.activeElement)')
        dialog.get_by_role('button',name='Release & start task',exact=True).click()
        workspace.get_by_text('Question 1 of 15',exact=True).wait_for(timeout=15000)
        workspace.locator('.answer-option').nth(1).click()
        expect(workspace.get_by_text('Saved at',exact=False)).to_be_visible()
        capture(workspace,'quiz-desktop')
        official=team.request.get(URL+'/api/state').json()['tasks'][0]['deadline']
        assert second.request.get(URL+'/api/state').json()['tasks'][0]['deadline']==official
        workspace.reload();workspace.get_by_text('Question 1 of 15',exact=True).wait_for()
        assert team.request.get(URL+'/api/state').json()['tasks'][0]['deadline']==official
        team.set_offline(True)
        workspace.get_by_role('button',name='Next question',exact=True).click()
        workspace.locator('.answer-option').nth(1).click()
        expect(workspace.get_by_text('Not yet saved',exact=True)).to_be_visible()
        team.set_offline(False)
        workspace.get_by_role('button',name='Retry unsaved answers',exact=False).click()
        expect(workspace.get_by_text('Saved at',exact=False)).to_be_visible()
        control(admin,'pause',1)
        workspace.get_by_text('The organizer has paused this task.',exact=False).wait_for(timeout=15000)
        assert team.request.put(URL+'/api/quiz/3',data={'choice':1}).status==409
        control(admin,'resume',1)
        for i in range(3,16):
            response=team.request.put(URL+f'/api/quiz/{i}',data={'choice':1});assert response.ok
        # Actual browser events, with server recording checked.
        workspace.evaluate("window.dispatchEvent(new Event('blur'))")
        checks.append('Shared deadlines, persisted answers, offline retry, pause/resume, focus logging')
        workspace.set_viewport_size({'width':390,'height':844});capture(workspace,'quiz-mobile')
        control(admin,'end',1)
        for task_id in range(2,7):
            response=admin.request.post(URL+f'/api/admin/tasks/{task_id}/reference',multipart={'image':{'name':'reference.png','mimeType':'image/png','buffer':IMAGE}})
            assert response.ok,response.text()
        control(admin,'start',2)
        workspace.get_by_role('heading',name='Image recreation 1',exact=True).wait_for(timeout=15000)
        workspace.set_viewport_size({'width':1440,'height':1000})
        capture(workspace,'creative-desktop')
        workspace.get_by_label('Final generated image',exact=True).set_input_files(str(IMAGE_PATH))
        workspace.get_by_label('Final prompt',exact=False).fill('A blue ceramic sphere and a warm ochre cube, soft side lighting on a cool grey studio surface.')
        workspace.get_by_role('button',name='Submit creation',exact=True).click()
        workspace.get_by_role('dialog').get_by_role('button',name='Confirm submission',exact=True).click()
        workspace.get_by_text('Received. You’re on record.',exact=True).wait_for()
        submission=team.request.get(URL+'/api/submissions').json()[0]
        assert submission['evidence_flag'] is True
        assert second.request.get(URL+'/api/assets/'+submission['asset_id']).status==403
        workspace.reload();workspace.get_by_text('Received. You’re on record.',exact=True).wait_for()
        capture(workspace,'creative-receipt-desktop')
        workspace.set_viewport_size({'width':320,'height':850});capture(workspace,'creative-mobile-320')
        control(admin,'end',2)
        page.get_by_role('button',name='Judging studio',exact=True).click()
        page.get_by_role('button',name='Studio North',exact=False).wait_for()
        capture(page,'judging-gallery-desktop')
        page.get_by_role('button',name='Studio North',exact=False).click()
        page.get_by_role('heading',name='Rubric scoring',exact=True).wait_for()
        capture(page,'judging-review-desktop')
        for label in ['Composition and layout','Color and lighting','Subject and detail accuracy','Style and resemblance']:
            page.get_by_label(label+' score',exact=True).fill('85')
        page.get_by_label('Judge notes / override reason',exact=True).fill('Strong composition and palette; the cube placement could be closer to the reference.')
        page.get_by_role('button',name='Save review draft',exact=True).click()
        expect(page.get_by_text('Review saved as a draft.',exact=False)).to_be_visible()
        page.get_by_label('Judge notes / override reason',exact=True).fill('Temporary QA rejection to verify an audited review reversal.')
        page.get_by_role('button',name='Reject submission',exact=True).click()
        page.get_by_role('dialog').get_by_role('button',name='Reject submission',exact=True).click()
        expect(page.locator('.review-heading .badge')).to_have_text('Rejected')
        for label in ['Composition and layout','Color and lighting','Subject and detail accuracy','Style and resemblance']:
            page.get_by_label(label+' score',exact=True).fill('85')
        page.get_by_label('Judge notes / override reason',exact=True).fill('Reversed the QA rejection after checking the complete assigned brief.')
        page.get_by_role('button',name='Approve scores',exact=True).click()
        page.get_by_role('dialog').get_by_role('button',name='Approve scores',exact=True).click()
        expect(page.locator('.review-heading .badge')).to_have_text('Approved')
        page.get_by_role('button',name='Check evaluator',exact=True).click()
        expect(page.locator('.evaluation-run .badge')).to_have_text('unavailable')
        page.set_viewport_size({'width':390,'height':844});capture(page,'judging-review-mobile')
        page.set_viewport_size({'width':1440,'height':1000})
        checks.append('Independent manual upload, evidence flag, receipt recovery, private assets, draft/rejected/reversed reviews, human scoring, evaluator outage')
        for task_id in range(3,7):
            control(admin,'start',task_id);control(admin,'end',task_id)
        task=admin.request.get(URL+'/api/state').json()['tasks'][-1]
        task['brief']='Design a logo for Luma, a neighborhood repair studio making everyday objects last longer. The audience values care, craft, and practical optimism.'
        task['requirements']='Include the name Luma. Keep the mark legible at small sizes. Provide a clear single-color silhouette.'
        response=admin.request.put(URL+'/api/admin/tasks/7',data=task);assert response.ok,response.text()
        control(admin,'start',7)
        workspace.get_by_role('heading',name='The brand challenge',exact=True).wait_for(timeout=15000)
        # Optional local storage must never be a prerequisite for the manual fallback.
        workspace.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage disabled','SecurityError')}})")
        workspace.reload()
        workspace.get_by_role('heading',name='The brand challenge',exact=True).wait_for(timeout=15000)
        workspace.set_viewport_size({'width':1440,'height':1000});capture(workspace,'logo-desktop')
        workspace.get_by_label('Final generated image',exact=True).set_input_files(str(IMAGE_PATH))
        workspace.get_by_label('Final prompt',exact=False).fill('Luma repair studio logo: simple circular mark with a geometric interlocking form and readable lettering.')
        workspace.get_by_label('Design rationale',exact=False).fill('The interlocking shape expresses repair and continuity. The simple silhouette remains recognizable when reduced.')
        workspace.get_by_role('button',name='Submit creation',exact=True).click()
        workspace.get_by_role('dialog').get_by_role('button',name='Confirm submission',exact=True).click()
        workspace.get_by_text('Received. You’re on record.',exact=True).wait_for()
        control(admin,'end',7)
        logo=[s for s in team.request.get(URL+'/api/submissions').json() if s['task_id']==7][0]
        response=admin.request.put(URL+'/api/judging/'+logo['id'],data=dict(scores=[80,85,90,80,95],notes='Reviewed against the released brand case study.',approved=True,revision=logo['revision']))
        assert response.ok,response.text()
        assert post(admin,'/admin/publish',{'published':True})['published']
        page.get_by_role('button',name='Leaderboard',exact=True).click()
        page.get_by_text('The results are in.',exact=True).wait_for(timeout=15000)
        capture(page,'leaderboard-desktop')
        with page.expect_download() as download:
            page.get_by_role('link',name='Export results',exact=True).click()
        download.value.save_as(str(OUT/'e2e-results.csv'))
        workspace.get_by_role('button',name='Leaderboard',exact=True).click()
        workspace.get_by_role('cell',name='Studio North',exact=True).wait_for()
        checks.append('Logo brief release, manual submission with browser storage disabled, score aggregation, published rankings and CSV download')
        for view,title in [('rounds','Rounds & content'),('incidents','Integrity review'),('audit','Activity log'),('settings','Event settings'),('control','Control room')]:
            page.goto(URL+'?view='+view);page.get_by_role('heading',name=title,exact=True).wait_for()
            capture(page,view+'-desktop')
        page.set_viewport_size({'width':320,'height':850});capture(page,'control-mobile-320')
        expect(page.locator('.live-stage .timer > span')).to_have_text('00:00')
        expect(page.get_by_role('button',name='Review results',exact=True)).to_be_visible()
        page.get_by_role('button',name='Toggle navigation',exact=True).click()
        page.get_by_role('button',name='Teams',exact=True).click()
        assert page.get_by_role('heading',name='Teams',exact=True).is_visible()
        checks.append('Role navigation, focus-contained confirmations, mobile reflow at 320px')
        report=dict(checks=checks,browser_errors=errors,accessibility=audit_results)
        (OUT/'browser-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(dict(checks=len(checks),browser_errors=errors,accessibility_violations={k:len(v) for k,v in audit_results.items()}),indent=2))
        assert not errors,errors
        assert not any(audit_results.values()),'Accessibility findings remain in browser-report.json'
        browser.close()
except Exception:
    try:
        page.screenshot(path=str(OUT/'failure.png'),full_page=True)
        print('Browser errors:',errors)
        print('Visible page after failure:',page.locator('body').inner_text()[:2500])
    except Exception: pass
    raise
finally:
    if proxy:
        proxy.shutdown();proxy.server_close();proxy_thread.join(timeout=5)
    if os.name=='nt': subprocess.run(['taskkill','/PID',str(server.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else: server.terminate()
    try: server.wait(timeout=10)
    except subprocess.TimeoutExpired: server.kill();server.wait()
    log.close();engine.dispose();TEMP.cleanup()
