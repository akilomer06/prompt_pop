import io
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from PIL import Image
from sqlalchemy import select, func
from fastapi.testclient import TestClient
from backend.app import app
from backend.models import Session, Competition, Task, Submission, RequestReceipt, Evaluation, Audit

def png(color='blue'):
    buffer = io.BytesIO()
    Image.new('RGB', (128, 128), color).save(buffer, 'PNG')
    return buffer.getvalue()

def control(env, action, task=1, **extra):
    return env['admin'].post('/api/admin/control', json=dict(action=action, task_id=task, **extra))

def start_image(env):
    assert control(env, 'start').status_code == 200
    assert control(env, 'end').status_code == 200
    response = env['admin'].post('/api/admin/tasks/2/reference', files={'image':('reference.png', png(), 'image/png')})
    assert response.status_code == 200, response.text
    assert control(env, 'start', 2).status_code == 200
    return response.json()['asset_id']

def submit(env, client=None, key=None, raw=None, **extra):
    data=dict(prompt='A blue sphere with soft window lighting', request_key=key or str(uuid.uuid4()), **extra)
    return (client or env['team']).post('/api/tasks/2/submit', data=data, files={'image':('image.png', raw or png(), 'image/png')})

def test_authentication_cookie_logout_and_bad_login(env):
    outsider = TestClient(app)
    assert outsider.get('/api/state').status_code == 401
    assert outsider.post('/api/auth/login',json={'username':'no','password':'invalid'}).status_code == 401
    assert env['team'].get('/api/me').json()['team_id'] == env['a']['id']
    assert 'HttpOnly' in env['admin'].post('/api/auth/login',json={'username':'admin','password':'test-admin-pass'}).headers['set-cookie']
    env['team'].post('/api/auth/logout')
    assert env['team'].get('/api/state').status_code == 401

@pytest.mark.parametrize('method,path,payload', [
    ('post','/api/admin/teams',{'name':'Hacker'}),
    ('post','/api/admin/control',{'action':'start','task_id':1}),
    ('put','/api/admin/settings',{'title':'Changed','weights':[30,40,30],'tie_break':'quiz','integrity_threshold':3}),
    ('get','/api/admin/questions',None),('get','/api/admin/audit',None),
    ('get','/api/admin/export',None),('get','/api/admin/export-assets',None),('get','/api/admin/teams',None)])
def test_participant_cannot_admin(env,method,path,payload):
    response=env['team'].request(method,path,json=payload) if payload else env['team'].request(method,path)
    assert response.status_code == 403

def test_unreleased_questions_and_briefs_are_private(env):
    assert env['team'].get('/api/quiz').status_code == 403
    with Session.begin() as db: db.get(Task,7).brief = 'Secret brand launch'
    state=env['team'].get('/api/state').json()
    assert all('reference_id' not in t and 'brief' not in t for t in state['tasks'])
    assert env['team'].get('/api/tasks/7/work').status_code == 403

def test_quiz_fifteen_answers_autosave_and_never_leak_key(env):
    control(env,'start')
    q=env['team'].get('/api/quiz').json()
    assert len(q['questions']) == 15
    assert all('correct' not in row for row in q['questions'])
    for i in range(1,16): assert env['team'].put(f'/api/quiz/{i}',json={'choice':1}).status_code == 200
    assert len(env['team'].get('/api/quiz').json()['answers']) == 15
    assert env['other'].get('/api/quiz').json()['answers'] == {}
    assert env['team'].put('/api/quiz/1',json={'choice':7}).status_code == 422

def test_deadline_refresh_pause_resume_and_integrity(env):
    control(env,'start')
    before=env['team'].get('/api/state').json()['tasks'][0]['deadline']
    assert env['other'].get('/api/state').json()['tasks'][0]['deadline'] == before
    assert env['team'].get('/api/state').json()['tasks'][0]['deadline'] == before
    assert env['team'].post('/api/incidents',json={'type':'hidden','duration':3}).status_code == 200
    assert len(env['admin'].get('/api/admin/incidents').json()) == 1
    control(env,'pause')
    assert env['team'].put('/api/quiz/1',json={'choice':1}).status_code == 409
    assert control(env,'resume').status_code == 200
    with Session.begin() as db: db.get(Task,1).deadline = time.time()-1
    assert env['team'].put('/api/quiz/1',json={'choice':1}).status_code == 409
    assert env['team'].get('/api/quiz').json()['answers'] == {}

def test_state_machine_no_duplicate_start_skip_or_edit_live(env):
    assert control(env,'start',2).status_code == 409
    assert control(env,'start').status_code == 200
    assert control(env,'start').status_code == 409
    assert control(env,'start',2).status_code == 409
    assert control(env,'resume').status_code == 409
    assert control(env,'extend',seconds=60,reason='Network issue').status_code == 200
    assert control(env,'extend',seconds=60,reason='').status_code == 422
    question=env['admin'].get('/api/admin/questions').json()[0]
    assert env['admin'].put('/api/admin/questions',json={'questions':[question]}).status_code == 409

def test_manual_submission_receipt_isolation_evidence_and_revisions(env):
    reference=start_image(env)
    assert env['team'].get('/api/assets/'+reference).status_code == 403
    assert env['other'].get('/api/assets/'+reference).status_code == 403
    assert env['judge'].get('/api/assets/'+reference).status_code == 200
    response=submit(env)
    assert response.status_code == 200, response.text
    row=response.json()
    assert row['receipt'] and row['evidence_flag'] and row['team_id']==env['a']['id']
    assert env['team'].get('/api/assets/'+row['asset_id']).status_code == 200
    assert env['other'].get('/api/assets/'+row['asset_id']).status_code == 403
    assert env['other'].get('/api/submissions').json() == []
    assert env['team'].get('/api/judging/'+row['id']).status_code == 403
    revised=submit(env).json()
    assert revised['id'] == row['id'] and revised['revision'] == 2
    assert len(env['admin'].get('/api/submissions').json()) == 1

def test_idempotency_retry_after_deadline_and_key_content_conflict(env):
    start_image(env)
    key=str(uuid.uuid4())
    first=submit(env,key=key).json()
    with Session.begin() as db: db.get(Task,2).deadline=time.time()-1000
    assert submit(env,key=key).json() == first
    assert submit(env,key=key,raw=png('red')).status_code == 409
    assert submit(env).status_code == 409
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(Submission)) == 1
        assert db.scalar(select(func.count()).select_from(RequestReceipt)) == 1

def test_grace_deadline_policy(env):
    start_image(env)
    with Session.begin() as db: db.get(Task,2).deadline=time.time()-20
    row=submit(env).json()
    assert row['late'] is True
    with Session.begin() as db: db.get(Task,2).deadline=time.time()-121
    assert submit(env).status_code == 409

def test_upload_validation_and_private_draft(env):
    start_image(env)
    assert submit(env,raw=b'<svg onload="alert(1)"></svg>').status_code == 422
    assert submit(env,raw=b'a'*(12*1024*1024+1)).status_code == 413
    assert submit(env,link='https://evil.example/x').status_code == 422
    assert env['team'].put('/api/tasks/2/draft',json={'prompt':'private draft'}).status_code == 200
    assert env['team'].get('/api/tasks/2/work').json()['draft']['prompt'] == 'private draft'
    assert env['other'].get('/api/tasks/2/work').json()['draft'] is None

def test_concurrent_team_submissions_and_duplicate_requests(env):
    start_image(env)
    key=str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses=list(pool.map(lambda pair: submit(env,client=pair[0],key=pair[1]),[(env['team'],key),(env['team'],key),(env['other'],str(uuid.uuid4()))]))
    assert all(r.status_code == 200 for r in responses)
    assert responses[0].json()['receipt'] == responses[1].json()['receipt']
    assert len(env['admin'].get('/api/submissions').json()) == 2

def test_judge_override_audit_evaluator_retry_and_publication(env):
    start_image(env)
    s=submit(env).json()
    body={'scores':[80,90,70,100],'notes':'Composition matches with minor differences.','approved':True,'revision':1}
    assert env['team'].put('/api/judging/'+s['id'],json=body).status_code == 403
    assert env['judge'].put('/api/judging/'+s['id'],json=body).status_code == 409
    control(env,'end',2)
    assert env['judge'].put('/api/judging/'+s['id'],json=body).status_code == 200
    body['scores']=[90,90,90,90]
    assert env['judge'].put('/api/judging/'+s['id'],json=body).status_code == 200
    for _ in range(2): assert env['judge'].post('/api/judging/'+s['id']+'/evaluate').json()['status'] == 'unavailable'
    detail=env['judge'].get('/api/judging/'+s['id']).json()
    assert len(detail['evaluations']) == 2
    assert len([h for h in detail['history'] if h['action']=='score_reviewed']) == 2
    assert env['team'].get('/api/leaderboard').json()['rows'] == []
    assert env['admin'].post('/api/admin/publish',json={'published':True}).status_code == 409
    with Session.begin() as db:
        for task in db.scalars(select(Task)): task.status='ended'
    assert env['admin'].post('/api/admin/publish',json={'published':True}).status_code == 200
    assert env['team'].get('/api/leaderboard').json()['published'] is True
    leaderboard=env['admin'].get('/api/leaderboard').json()['rows']
    assert leaderboard[0]['team_id']==env['a']['id']
    assert leaderboard[0]['rounds'][1] == 18 # 90 averaged across five tasks; missing work zero.
    assert leaderboard[0]['total']==7.2
    assert env['judge'].put('/api/judging/'+s['id'],json=body).status_code == 200
    assert env['team'].get('/api/leaderboard').json()['published'] is False

def test_config_validation_access_reset_and_csrf(env):
    a=env['admin']
    assert a.put('/api/admin/settings',json={'title':'Event','weights':[30,30,30],'tie_break':'quiz','integrity_threshold':3}).status_code == 422
    assert a.post('/api/admin/control',headers={'origin':'https://evil.example'},json={'action':'start','task_id':1}).status_code == 403
    assert a.post('/api/admin/control',headers={'sec-fetch-site':'cross-site'},json={'action':'start','task_id':1}).status_code == 403
    reset=a.post('/api/admin/teams/'+env['a']['id'],json={'action':'reset'}).json()
    assert env['team'].get('/api/me').status_code == 401
    assert env['team'].post('/api/auth/login',json={'username':reset['username'],'password':reset['access_code']}).status_code == 200
    a.post('/api/admin/teams/'+env['a']['id'],json={'action':'disable'})
    assert env['team'].get('/api/me').status_code == 401

def test_csv_scores_and_formula_injection_protection(env):
    env['make_team']('=DANGEROUS()')
    csv=env['admin'].get('/api/admin/export?kind=results')
    assert csv.status_code == 200 and csv.headers['content-type'].startswith('text/csv')
    assert "'=DANGEROUS()" in csv.text
    assert 'approved_creative_criteria' in csv.text

def test_start_requires_private_reference_and_logo_brief(env):
    control(env,'start');control(env,'end')
    assert control(env,'start',2).status_code == 422
    with Session.begin() as db:
        db.get(Competition,1).current=6
        for task in db.scalars(select(Task).where(Task.id<7)): task.status='ended'
    assert control(env,'start',7).status_code == 422

def test_configurable_task_count_and_rubric_validation(env):
    body=dict(title='Prompt Pop',weights=[30,40,30],tie_break='shared',integrity_threshold=3,image_task_count=3)
    response=env['admin'].put('/api/admin/settings',json=body)
    assert response.status_code==200,response.text
    state=env['admin'].get('/api/state').json()
    assert len([t for t in state['tasks'] if t['round']==2])==3
    assert state['tasks'][-1]['id']==5 and state['tasks'][-1]['round']==3
    task=state['tasks'][1]
    task['rubric'][0]['weight']=60
    assert env['admin'].put('/api/admin/tasks/2',json=task).status_code==422
    control(env,'start')
    body['image_task_count']=2
    assert env['admin'].put('/api/admin/settings',json=body).status_code==409

def test_private_asset_export_contains_images_and_manifest(env):
    import zipfile
    start_image(env)
    submit(env)
    response=env['admin'].get('/api/admin/export-assets')
    assert response.status_code==200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert 'submissions.json' in archive.namelist()
        assert any(n.endswith('.png') for n in archive.namelist())

def test_evaluator_outage_does_not_lock_live_submissions(env,monkeypatch):
    import threading
    import backend.app as module
    start_image(env)
    first=submit(env).json()
    started,release=threading.Event(),threading.Event()
    def slow_evaluation(*args):
        started.set()
        assert release.wait(5)
        return 'failed', {'message':'Evaluator offline. Use manual review.'}
    monkeypatch.setenv('EVALUATOR_URL','https://authorized.example/evaluate')
    monkeypatch.setattr(module,'evaluate',slow_evaluation)
    with ThreadPoolExecutor(max_workers=2) as pool:
        future=pool.submit(env['admin'].post,'/api/judging/'+first['id']+'/evaluate')
        assert started.wait(5)
        try:
            before=time.monotonic()
            assert env['other'].get('/api/state').status_code==200
            assert submit(env,client=env['other']).status_code==200
            assert time.monotonic()-before<2
        finally: release.set()
        assert future.result().json()['status']=='queued'
    run=env['admin'].get('/api/judging/'+first['id']).json()['evaluations'][0]
    assert run['status']=='failed'
    assert len(env['admin'].get('/api/submissions').json())==2

def test_rejection_and_draft_review_preserve_audit_and_zero_score(env):
    start_image(env)
    s=submit(env).json()
    control(env,'end',2)
    body=dict(scores=[90,90,90,90],notes='Review saved for second opinion.',approved=False,revision=1)
    assert env['judge'].put('/api/judging/'+s['id'],json=body).json()['approved'] is False
    body.update(reject=True,notes='The uploaded image does not answer the assigned challenge.')
    rejected=env['judge'].put('/api/judging/'+s['id'],json=body).json()
    assert rejected['status']=='rejected' and rejected['approved'] is True
    assert rejected['scores']==[0,0,0,0]
    assert env['team'].get('/api/assets/'+s['asset_id']).status_code==200
    body.update(reject=False,approved=True,notes='Decision reversed after reviewing the organizer brief.')
    assert env['judge'].put('/api/judging/'+s['id'],json=body).json()['scores']==[90,90,90,90]
    assert len([h for h in env['judge'].get('/api/judging/'+s['id']).json()['history'] if h['action']=='score_reviewed'])==3

def test_image_upload_preserves_exif_orientation_before_stripping_metadata(env):
    start_image(env)
    image=Image.new('RGB',(96,32),'blue')
    metadata=Image.Exif();metadata[274]=6;metadata[315]='Private camera owner'
    raw=io.BytesIO();image.save(raw,'JPEG',exif=metadata)
    row=submit(env,raw=raw.getvalue()).json()
    stored=Image.open(io.BytesIO(env['team'].get('/api/assets/'+row['asset_id']).content))
    assert stored.size==(32,96)
    assert not stored.getexif()
