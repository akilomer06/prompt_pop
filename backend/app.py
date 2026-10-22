import csv
import hashlib
import io
import json
import math
import os
import secrets
import threading
import time
import uuid
import warnings
import zipfile
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Depends, Request, Response, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, ImageOps
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError

from .models import (Session, Competition, Task, Question, Answer, Team, User, AuthSession,
                     Asset, Submission, Draft, RequestReceipt, Incident, Evaluation, Audit)
from .seed import initialize
from .security import password_hash, verify_password, token_hash, current_user, require
from .integrations import capabilities, evaluate

STORAGE = Path(os.getenv('STORAGE_DIR', './data/assets')).resolve()
STORAGE.mkdir(parents=True, exist_ok=True)
LOCK = threading.Lock()
RATE_LOCK = threading.Lock()
LIMITS = defaultdict(deque)
Image.MAX_IMAGE_PIXELS = 25_000_000

def uid(): return str(uuid.uuid4())
def abort(condition, status, message):
    if condition: raise HTTPException(status, message)

@asynccontextmanager
async def lifespan(app):
    initialize()
    with Session.begin() as db:
        for run in db.scalars(select(Evaluation).where(Evaluation.status == 'queued')):
            run.status, run.result = 'failed', {'message':'Evaluation interrupted by server restart. Retry or score manually.'}
    yield

app = FastAPI(title='Prompt Pop 2K26', lifespan=lifespan, docs_url=None, redoc_url=None)

@app.middleware('http')
async def security_headers(request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        allowed = {os.getenv('APP_ORIGIN', 'http://localhost:5173'), str(request.base_url).rstrip('/')}
        if origin and origin not in allowed:
            return Response('Cross-origin action rejected.', status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return Response('Cross-site action rejected.', status_code=403)
        length = request.headers.get('content-length', '0')
        if not length.isdigit() or int(length) > 27 * 1024 * 1024:
            return Response('Upload is too large.', status_code=413)
    response = await call_next(request)
    response.headers.update({'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'same-origin',
                             'X-Frame-Options': 'DENY', 'Cache-Control': 'no-store',
                             'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
                             'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"})
    if os.getenv('COOKIE_SECURE', 'false').lower() == 'true': response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response

def database():
    # Serializes local SQLite mutations and state reads. PostgreSQL row lock also protects state.
    with LOCK, Session() as db:
        try:
            yield db
            db.commit()
        except IntegrityError:
            db.rollback()
            for path in db.info.get('new_assets', []): path.unlink(missing_ok=True)
            raise HTTPException(409, 'This record already exists. Refresh and try again.')
        except Exception:
            db.rollback()
            for path in db.info.get('new_assets', []): path.unlink(missing_ok=True)
            raise

def auth(request: Request, db=Depends(database, scope='function')): return current_user(request, db)

def competition(db): return db.scalar(select(Competition).where(Competition.id == 1).with_for_update())
def audit(db, user, action, details):
    db.add(Audit(id=uid(), actor=user.id, action=action, timestamp=time.time(), details=details))
def task_or_404(db, task_id):
    task = db.get(Task, task_id)
    abort(not task, 404, 'Task not found.')
    return task

def task_view(task, privileged):
    result = {k: getattr(task, k) for k in ('id', 'round', 'title', 'duration', 'grace', 'attempt_limit', 'status', 'deadline', 'remaining', 'rubric')}
    if privileged or task.status != 'pending': result.update(brief=task.brief, requirements=task.requirements)
    if privileged: result['reference_id'] = task.reference_id
    return result

def submission_view(row):
    return {k: getattr(row, k) for k in ('id', 'team_id', 'task_id', 'prompt', 'link', 'rationale', 'asset_id', 'evidence_id', 'submitted', 'revision', 'receipt', 'status', 'late', 'evidence_flag', 'scores', 'notes', 'approved')}

def gate(db, task, creative=False):
    comp = competition(db)
    abort(comp.current != task.id or task.status != 'running', 409, 'This task is not accepting work. Check the official round status.')
    now = time.time()
    abort(task.deadline is None or now >= task.deadline + (task.grace if creative else 0), 409, 'The official submission deadline has passed.')
    return now

def limit(key, maximum=120, seconds=60):
    now = time.monotonic()
    with RATE_LOCK:
        q = LIMITS[key]
        while q and q[0] < now - seconds: q.popleft()
        abort(len(q) >= maximum, 429, 'Too many requests. Wait a minute and try again.')
        q.append(now)

class Login(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)

@app.post('/api/auth/login')
def login(body: Login, request: Request, response: Response, db=Depends(database, scope='function')):
    limit(('login', request.client.host), 12)
    user = db.scalar(select(User).where(User.username == body.username.strip().lower()))
    valid = verify_password(body.password, user.password if user else DUMMY_PASSWORD)
    abort(not user or not valid or not user.active, 401, 'The account or access code is incorrect.')
    token = secrets.token_urlsafe(40)
    now = time.time()
    db.add(AuthSession(token=token_hash(token), user_id=user.id, expires=now + int(os.getenv('SESSION_HOURS', '12')) * 3600, seen=now))
    response.set_cookie('pp_session', token, httponly=True, secure=os.getenv('COOKIE_SECURE', 'false').lower() == 'true', samesite='strict', max_age=int(os.getenv('SESSION_HOURS', '12')) * 3600, path='/')
    team = db.get(Team, user.team_id) if user.team_id else None
    return dict(id=user.id, username=user.username, role=user.role, team_id=user.team_id, team_name=team.name if team else None)

DUMMY_PASSWORD = password_hash(secrets.token_urlsafe(20))

@app.post('/api/auth/logout')
def logout(request: Request, response: Response, db=Depends(database, scope='function')):
    db.execute(delete(AuthSession).where(AuthSession.token == token_hash(request.cookies.get('pp_session', ''))))
    response.delete_cookie('pp_session', path='/')
    return {'ok': True}

@app.get('/api/me')
def me(user=Depends(auth), db=Depends(database, scope='function')):
    team = db.get(Team, user.team_id) if user.team_id else None
    return dict(id=user.id, username=user.username, role=user.role, team_id=user.team_id, team_name=team.name if team else None)

@app.get('/api/state')
def state(user=Depends(auth), db=Depends(database, scope='function')):
    comp = competition(db)
    tasks = db.scalars(select(Task).order_by(Task.id)).all()
    return dict(title=comp.title, current=comp.current, published=comp.published, weights=comp.weights, tie_break=comp.tie_break, integrity_threshold=comp.integrity_threshold, quiz_question_count=db.scalar(select(func.count()).select_from(Question)), server_time=time.time(), tasks=[task_view(t, user.role != 'participant') for t in tasks], integration=capabilities())

class TeamInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    members: list[str] = Field(default_factory=list, max_length=20)

@app.post('/api/admin/teams')
def create_team(body: TeamInput, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin')
    abort(not body.name.strip() or any(len(n) > 100 for n in body.members), 422, 'Use a team name and member names under 100 characters.')
    team = Team(id=uid(), name=body.name.strip(), members=body.members)
    code = secrets.token_urlsafe(12)
    username = 'team-' + team.id[:8]
    db.add(team)
    db.flush()
    db.add(User(id=uid(), username=username, password=password_hash(code), role='participant', team_id=team.id))
    audit(db, user, 'team_created', {'team_id': team.id, 'name': team.name})
    return dict(id=team.id, name=team.name, username=username, access_code=code)

@app.get('/api/admin/teams')
def teams(user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin', 'judge')
    result = []
    for team in db.scalars(select(Team).order_by(Team.name)):
        account = db.scalar(select(User).where(User.team_id == team.id))
        sessions = db.scalars(select(AuthSession).where(AuthSession.user_id == account.id, AuthSession.expires > time.time())).all() if account else []
        subs = db.scalars(select(Submission).where(Submission.team_id == team.id)).all()
        result.append(dict(id=team.id, name=team.name, members=team.members, username=account.username if account else '', active=account.active if account else False, online=any(s.seen > time.time()-20 for s in sessions), submissions=len(subs), late=sum(s.late for s in subs), answers=db.scalar(select(func.count()).select_from(Answer).where(Answer.team_id == team.id)), incidents=db.scalar(select(func.count()).select_from(Incident).where(Incident.team_id == team.id))))
    return result

class TeamAction(BaseModel): action: str

@app.post('/api/admin/teams/{team_id}')
def team_action(team_id: str, body: TeamAction, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin')
    account = db.scalar(select(User).where(User.team_id == team_id))
    abort(not account, 404, 'Team not found.')
    result = {'ok': True}
    if body.action == 'reset':
        code = secrets.token_urlsafe(12)
        account.password = password_hash(code)
        result = dict(username=account.username, access_code=code)
    elif body.action == 'disable': account.active = False
    elif body.action == 'enable': account.active = True
    else: raise HTTPException(422, 'Unknown team action.')
    db.execute(delete(AuthSession).where(AuthSession.user_id == account.id))
    audit(db, user, 'team_' + body.action, {'team_id': team_id})
    return result

class TaskConfig(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    brief: str = Field(max_length=20000)
    requirements: str = Field(default='', max_length=10000)
    duration: int = Field(ge=30, le=14400)
    grace: int = Field(ge=0, le=600)
    attempt_limit: int = Field(ge=1, le=100)
    rubric: list[dict] = Field(max_length=12)

def validate_rubric(rubric):
    abort(not rubric or any(not isinstance(r.get('name'), str) or not 1 <= len(r['name']) <= 100 or isinstance(r.get('weight'), bool) or not isinstance(r.get('weight'), (int, float)) or not math.isfinite(r['weight']) or r['weight'] <= 0 for r in rubric), 422, 'Each criterion needs a name and positive weight.')
    abort(abs(sum(r['weight'] for r in rubric)-100) > .001, 422, 'Rubric weights must total 100.')
    abort(len({r['name'] for r in rubric}) != len(rubric), 422, 'Criterion names must be unique.')

@app.put('/api/admin/tasks/{task_id}')
def configure(task_id: int, body: TaskConfig, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin')
    competition(db)
    task = task_or_404(db, task_id)
    abort(len(body.title.strip()) < 2, 422, 'Give the challenge a readable title.')
    abort(task.status != 'pending', 409, 'Only unreleased tasks can be configured.')
    if task.round != 1: validate_rubric(body.rubric)
    for k, v in body.model_dump().items(): setattr(task, k, v)
    if task.round == 1: task.grace = 0
    audit(db, user, 'task_configured', {'task_id': task_id, **body.model_dump()})
    return task_view(task, True)

class QuestionInput(BaseModel):
    text: str = Field(min_length=5, max_length=3000)
    options: list[str] = Field(min_length=2, max_length=8)
    correct: int = Field(ge=0)
    points: float = Field(gt=0, le=100)
class Bank(BaseModel): questions: list[QuestionInput] = Field(min_length=1, max_length=100)

@app.get('/api/admin/questions')
def question_bank(user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin')
    return [dict(id=q.id, text=q.text, options=q.options, correct=q.correct, points=q.points) for q in db.scalars(select(Question).order_by(Question.id))]

@app.put('/api/admin/questions')
def save_bank(body: Bank, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin')
    competition(db)
    abort(db.get(Task, 1).status != 'pending', 409, 'The quiz has already been released.')
    for q in body.questions:
        abort(len(q.text.strip()) < 5 or q.correct >= len(q.options) or any(not x.strip() or len(x) > 1000 for x in q.options) or len(set(q.options)) != len(q.options), 422, 'Every question needs readable text, unique options, and a valid answer index.')
    db.execute(delete(Question))
    for i, q in enumerate(body.questions): db.add(Question(id=i+1, **q.model_dump()))
    audit(db, user, 'question_bank_updated', {'count': len(body.questions)})
    return {'ok': True}

class Control(BaseModel):
    action: str
    task_id: int
    reason: str = Field(default='', max_length=2000)
    seconds: int = Field(default=0, ge=0, le=3600)

@app.post('/api/admin/control')
def control(body: Control, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin')
    comp = competition(db)
    task = task_or_404(db, body.task_id)
    before = task_view(task, True)
    now = time.time()
    if body.action == 'start':
        abort(task.status != 'pending' or task.id != comp.current + 1, 409, 'Release the next task in sequence. A task can only start once.')
        if comp.current: abort(db.get(Task, comp.current).status != 'ended', 409, 'Close the current task before advancing.')
        abort(task.round == 2 and not task.reference_id, 422, 'Upload the private reference before releasing this task.')
        abort(task.round == 3 and not task.brief.strip(), 422, 'Write and preview the brand brief before releasing it.')
        task.status, task.deadline, comp.current = 'running', now + task.duration, task.id
    else:
        abort(comp.current != task.id, 409, 'Choose the active task.')
        if body.action == 'pause':
            abort(task.status != 'running' or now >= task.deadline, 409, 'Only a running creation period can be paused.')
            task.remaining, task.deadline, task.status = task.deadline - now, None, 'paused'
        elif body.action == 'resume':
            abort(task.status != 'paused', 409, 'Only a paused task can resume.')
            task.deadline, task.remaining, task.status = now + task.remaining, None, 'running'
        elif body.action == 'end':
            abort(task.status not in ('running', 'paused'), 409, 'This task is already closed.')
            task.status, task.remaining = 'ended', None
        elif body.action == 'extend':
            abort(task.status not in ('running', 'paused') or not body.reason.strip() or body.seconds < 1, 422, 'A time adjustment needs an active task, added seconds, and a reason.')
            if task.status == 'paused': task.remaining += body.seconds
            else: task.deadline += body.seconds
        else: raise HTTPException(422, 'Unknown control action.')
    comp.published = False
    audit(db, user, 'task_' + body.action, {'task_id': task.id, 'before': before, 'after': task_view(task, True), 'reason': body.reason, 'seconds': body.seconds})
    return task_view(task, True)

class Settings(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    weights: list[float] = Field(min_length=3, max_length=3)
    tie_break: str
    integrity_threshold: int = Field(ge=1, le=100)
    image_task_count: int | None = Field(default=None, ge=1, le=20)

@app.put('/api/admin/settings')
def settings(body: Settings, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin')
    abort(len(body.title.strip()) < 2, 422, 'Give the event a readable name.')
    abort(any(not math.isfinite(v) or v < 0 for v in body.weights) or abs(sum(body.weights)-100)>.001 or body.tie_break not in ('quiz', 'logo', 'shared'), 422, 'Choose a valid tie-break and round weights totaling 100.')
    comp = competition(db)
    existing = db.scalars(select(Task).where(Task.round == 2).order_by(Task.id)).all()
    if body.image_task_count is not None and body.image_task_count != len(existing):
        abort(comp.current != 0 or db.scalar(select(func.count()).select_from(Asset)) > 0, 409, 'Change challenge count before starting the event or uploading assets.')
        from .seed import IMAGE_RUBRIC
        logo = db.scalar(select(Task).where(Task.round == 3))
        logo_data = {k: getattr(logo, k) for k in ('title', 'brief', 'requirements', 'duration', 'grace', 'attempt_limit', 'rubric')}
        db.delete(logo)
        for item in existing: db.delete(item)
        db.flush()
        for i in range(body.image_task_count):
            old = existing[min(i, len(existing)-1)]
            db.add(Task(id=i+2, round=2, title=f'Image recreation {i+1}', brief=old.brief, duration=old.duration, grace=old.grace, attempt_limit=old.attempt_limit, rubric=old.rubric or IMAGE_RUBRIC))
        db.add(Task(id=body.image_task_count+2, round=3, **logo_data))
    for k, v in body.model_dump(exclude={'image_task_count'}).items(): setattr(comp, k, v)
    comp.published = False
    audit(db, user, 'settings_updated', body.model_dump())
    return {'ok': True}

@app.get('/api/quiz')
def quiz(user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'participant')
    task = task_or_404(db, 1)
    abort(task.status == 'pending', 403, 'The quiz has not been released.')
    answers = {a.question_id: dict(choice=a.choice, saved=a.saved) for a in db.scalars(select(Answer).where(Answer.team_id == user.team_id))}
    return dict(questions=[dict(id=q.id, text=q.text, options=q.options, points=q.points) for q in db.scalars(select(Question).order_by(Question.id))], answers=answers)

class Choice(BaseModel): choice: int = Field(ge=0, le=7)
@app.put('/api/quiz/{question_id}')
def answer(question_id: int, body: Choice, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'participant')
    limit(('answer', user.id))
    saved = gate(db, task_or_404(db, 1))
    q = db.get(Question, question_id)
    abort(not q or body.choice >= len(q.options), 422, 'Choose one of the available answers.')
    row = db.scalar(select(Answer).where(Answer.team_id == user.team_id, Answer.question_id == question_id))
    if row: row.choice, row.saved = body.choice, saved
    else: db.add(Answer(id=uid(), team_id=user.team_id, question_id=question_id, choice=body.choice, saved=saved))
    return dict(choice=body.choice, saved=saved)

class IncidentInput(BaseModel):
    type: str
    duration: float | None = Field(default=None, ge=0, le=86400)
@app.post('/api/incidents')
def log_incident(body: IncidentInput, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'participant')
    limit(('incident', user.id), 90)
    comp = competition(db)
    abort(comp.current != 1 or db.get(Task, 1).status != 'running', 409, 'Integrity monitoring is active only during the quiz.')
    abort(body.type not in ('hidden', 'visible', 'blur', 'focus', 'fullscreen_exit', 'fullscreen_enter'), 422, 'Unknown incident type.')
    db.add(Incident(id=uid(), team_id=user.team_id, task_id=1, type=body.type, duration=body.duration, timestamp=time.time()))
    return {'ok': True}

@app.get('/api/admin/incidents')
def incidents(user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin', 'judge')
    return [dict(id=i.id, team_id=i.team_id, type=i.type, timestamp=i.timestamp, duration=i.duration, reviewed=i.reviewed, notes=i.notes) for i in db.scalars(select(Incident).order_by(Incident.timestamp.desc()).limit(500))]

class Note(BaseModel): notes: str = Field(max_length=2000)
@app.put('/api/admin/incidents/{incident_id}')
def review_incident(incident_id: str, body: Note, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin', 'judge')
    row = db.get(Incident, incident_id)
    abort(not row, 404, 'Incident not found.')
    row.reviewed, row.notes = True, body.notes
    audit(db, user, 'incident_reviewed', {'id': incident_id, 'notes': body.notes})
    return {'ok': True}

def store_image(db, raw, filename, team_id, task_id, kind):
    abort(not raw or len(raw) > 12*1024*1024, 413, 'Choose an image under 12 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(raw))
            abort(image.format not in ('PNG', 'JPEG', 'WEBP') or getattr(image, 'is_animated', False), 422, 'Use a still PNG, JPEG, or WebP image.')
            image.load()
            image = ImageOps.exif_transpose(image)
            abort(image.width < 16 or image.height < 16 or image.width * image.height > 25_000_000, 422, 'Image dimensions must be at least 16 pixels and under 25 megapixels.')
            output = io.BytesIO()
            normalized = image.convert('RGBA')
            normalized.info.clear()
            normalized.save(output, format='PNG')
    except HTTPException: raise
    except Exception: raise HTTPException(422, 'This file could not be decoded as a supported image.')
    asset = Asset(id=uid(), team_id=team_id, task_id=task_id, kind=kind, mime='image/png', filename=Path(filename or 'image.png').name[:200])
    (STORAGE / asset.id).write_bytes(output.getvalue())
    db.info.setdefault('new_assets', []).append(STORAGE / asset.id)
    db.add(asset)
    db.flush()
    return asset

@app.post('/api/admin/tasks/{task_id}/reference')
def reference(task_id: int, image: UploadFile = File(...), user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin')
    competition(db)
    task = task_or_404(db, task_id)
    abort(task.status != 'pending' or task.round != 2, 409, 'References can be changed only on unreleased image tasks.')
    asset = store_image(db, image.file.read(12*1024*1024+1), image.filename, None, task.id, 'reference')
    task.reference_id = asset.id
    audit(db, user, 'reference_uploaded', {'task_id': task_id, 'asset_id': asset.id})
    return dict(asset_id=asset.id)

@app.get('/api/assets/{asset_id}')
def get_asset(asset_id: str, user=Depends(auth), db=Depends(database, scope='function')):
    asset = db.get(Asset, asset_id)
    abort(not asset, 404, 'Asset not found.')
    abort(user.role == 'participant' and (asset.kind == 'reference' or asset.team_id != user.team_id), 403, 'This asset is private.')
    abort(not (STORAGE / asset.id).is_file(), 404, 'Asset file is unavailable. Contact an organizer.')
    return FileResponse(STORAGE / asset.id, media_type=asset.mime, filename=asset.filename, content_disposition_type='inline')

class DraftInput(BaseModel):
    prompt: str = Field(default='', max_length=20000)
    link: str = Field(default='', max_length=2000)
    rationale: str = Field(default='', max_length=10000)
@app.put('/api/tasks/{task_id}/draft')
def save_draft(task_id: int, body: DraftInput, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'participant')
    task = task_or_404(db, task_id)
    abort(task.round == 1, 422, 'Use quiz autosave for answers.')
    gate(db, task, True)
    row = db.scalar(select(Draft).where(Draft.team_id == user.team_id, Draft.task_id == task_id))
    if row: row.content = body.model_dump()
    else: db.add(Draft(id=uid(), team_id=user.team_id, task_id=task_id, content=body.model_dump()))
    return {'saved': time.time()}

@app.get('/api/tasks/{task_id}/work')
def work(task_id: int, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'participant')
    abort(task_or_404(db, task_id).status == 'pending', 403, 'This task is not released.')
    draft = db.scalar(select(Draft).where(Draft.team_id == user.team_id, Draft.task_id == task_id))
    submission = db.scalar(select(Submission).where(Submission.team_id == user.team_id, Submission.task_id == task_id))
    return dict(draft=draft.content if draft else None, submission=submission_view(submission) if submission else None)

@app.post('/api/tasks/{task_id}/submit')
def submit(task_id: int, prompt: str = Form(..., max_length=20000), link: str = Form('', max_length=2000), rationale: str = Form('', max_length=10000), request_key: str = Form(..., min_length=10, max_length=100), image: UploadFile = File(...), evidence: UploadFile | None = File(None), user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'participant')
    limit(('submit', user.id), 20)
    competition(db)
    task = task_or_404(db, task_id)
    abort(task.round == 1 or not prompt.strip(), 422, 'An image and your final prompt are required.')
    if link:
        parsed = urlparse(link)
        abort(parsed.scheme != 'https' or parsed.hostname != 'chatgpt.com' or not parsed.path.startswith('/share/'), 422, 'Use a ChatGPT share link, or leave it blank for review.')
    raw = image.file.read(12*1024*1024+1)
    evidence_raw = evidence.file.read(12*1024*1024+1) if evidence and evidence.filename else b''
    fingerprint = hashlib.sha256(json.dumps([task_id, prompt, link, rationale]).encode()+raw+evidence_raw).hexdigest()
    receipt = db.scalar(select(RequestReceipt).where(RequestReceipt.team_id == user.team_id, RequestReceipt.key == request_key))
    if receipt:
        abort(receipt.fingerprint != fingerprint, 409, 'This request key was used for different work. Refresh before retrying.')
        return receipt.response
    now = gate(db, task, True)
    abort(db.scalar(select(Submission).where(Submission.team_id == user.team_id, Submission.task_id == task_id, Submission.approved == True)) is not None, 409, 'This submission has already been approved. Contact an organizer.')
    asset = store_image(db, raw, image.filename, user.team_id, task_id, 'submission')
    evidence_asset = store_image(db, evidence_raw, evidence.filename, user.team_id, task_id, 'evidence') if evidence_raw else None
    row = db.scalar(select(Submission).where(Submission.team_id == user.team_id, Submission.task_id == task_id))
    if row:
        audit(db, user, 'submission_revised', {'previous': submission_view(row)})
        row.revision += 1
    else:
        row = Submission(id=uid(), team_id=user.team_id, task_id=task_id, revision=1)
        db.add(row)
    row.prompt, row.link, row.rationale = prompt.strip(), link, rationale
    row.asset_id, row.evidence_id = asset.id, evidence_asset.id if evidence_asset else None
    row.submitted, row.receipt, row.status = now, uid(), 'awaiting_evaluation'
    row.late, row.evidence_flag = now >= task.deadline, not bool(link or evidence_asset)
    row.scores, row.approved, row.notes = None, False, ''
    db.flush()
    result = submission_view(row)
    db.add(RequestReceipt(id=uid(), team_id=user.team_id, key=request_key, fingerprint=fingerprint, response=result))
    audit(db, user, 'submission_received', {'submission_id': row.id, 'revision': row.revision, 'receipt': row.receipt})
    return result

@app.get('/api/submissions')
def submissions(user=Depends(auth), db=Depends(database, scope='function')):
    query = select(Submission).order_by(Submission.submitted.desc())
    if user.role == 'participant': query = query.where(Submission.team_id == user.team_id)
    return [submission_view(s) for s in db.scalars(query)]

@app.get('/api/judging/{submission_id}')
def judging_detail(submission_id: str, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin', 'judge')
    row = db.get(Submission, submission_id)
    abort(not row, 404, 'Submission not found.')
    return dict(submission=submission_view(row), evaluations=[dict(id=e.id, created=e.created, revision=e.revision, status=e.status, method=e.method, result=e.result) for e in db.scalars(select(Evaluation).where(Evaluation.submission_id == row.id).order_by(Evaluation.created.desc()))], history=[dict(action=a.action, timestamp=a.timestamp, actor=a.actor, details=a.details) for a in db.scalars(select(Audit).where(Audit.action.in_(['score_reviewed', 'submission_revised', 'submission_received'])).order_by(Audit.timestamp.desc())) if a.details.get('submission_id') == row.id or a.details.get('previous', {}).get('id') == row.id])

class Review(BaseModel):
    scores: list[float] = Field(min_length=1, max_length=12)
    notes: str = Field(min_length=3, max_length=10000)
    approved: bool
    revision: int
    reject: bool = False

@app.put('/api/judging/{submission_id}')
def review(submission_id: str, body: Review, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin', 'judge')
    comp = competition(db)
    row = db.get(Submission, submission_id)
    abort(not row, 404, 'Submission not found.')
    task = db.get(Task, row.task_id)
    abort(len(body.notes.strip()) < 3, 422, 'Explain the scoring decision in your review notes.')
    abort(task.status != 'ended', 409, 'Close this task before approving scores.')
    abort(row.revision != body.revision, 409, 'The team revised this submission. Reload before reviewing.')
    abort(len(body.scores) != len(task.rubric) or any(not math.isfinite(v) or not 0 <= v <= 100 for v in body.scores), 422, 'Score every criterion from 0 to 100.')
    final_scores = [0.0] * len(task.rubric) if body.reject else body.scores
    audit(db, user, 'score_reviewed', {'submission_id': row.id, 'previous_scores': row.scores, 'scores': final_scores, 'previous_notes': row.notes, 'notes': body.notes, 'approved': body.approved or body.reject, 'rejected':body.reject, 'revision': row.revision})
    row.scores, row.notes, row.approved, row.status = final_scores, body.notes, body.approved or body.reject, 'rejected' if body.reject else 'manually_reviewed'
    comp.published = False
    return submission_view(row)

def evaluation_job(submission_id, revision, run_id):
    # Never keep the competition transaction locked while waiting for an external service.
    with LOCK, Session() as db:
        row = db.get(Submission, submission_id)
        task, asset = db.get(Task, row.task_id), db.get(Asset, row.asset_id)
        db.expunge_all()
    status, result = evaluate(row, task, asset, STORAGE)
    with LOCK, Session.begin() as db:
        run, current = db.get(Evaluation, run_id), db.get(Submission, submission_id)
        if current.revision != revision:
            run.status, run.result = 'superseded', {'message':'The team replaced its submission during evaluation. Evaluate the current revision.'}
        else:
            run.status, run.result = status, result
            if status == 'evaluated' and not current.approved: current.status = 'evaluated'

@app.post('/api/judging/{submission_id}/evaluate')
def run_evaluation(submission_id: str, background_tasks: BackgroundTasks, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin', 'judge')
    limit(('evaluation', user.id), 10)
    row = db.get(Submission, submission_id)
    abort(not row, 404, 'Submission not found.')
    task = db.get(Task, row.task_id)
    abort(db.scalar(select(Evaluation).where(Evaluation.submission_id == row.id, Evaluation.revision == row.revision, Evaluation.status == 'queued')) is not None, 409, 'This revision already has an evaluation in progress.')
    if capabilities()['evaluator_configured']:
        status, result = 'queued', {'message':'Evaluation queued. Teams can continue submitting while it runs.'}
    else:
        status, result = evaluate(row, task, db.get(Asset, row.asset_id), STORAGE)
    run = Evaluation(id=uid(), submission_id=row.id, revision=row.revision, created=time.time(), status=status, method='authorized_vision_adapter', result=result)
    db.add(run)
    if status == 'queued': background_tasks.add_task(evaluation_job, row.id, row.revision, run.id)
    audit(db, user, 'evaluation_requested', {'submission_id': row.id, 'status': status})
    return dict(status=status, result=result)

def results(db):
    comp = competition(db)
    questions = db.scalars(select(Question)).all()
    quiz_closed = db.get(Task, 1).status == 'ended'
    total_points = sum(q.points for q in questions)
    correct = {q.id: q for q in questions}
    rows = []
    for team in db.scalars(select(Team)):
        points = sum(correct[a.question_id].points for a in db.scalars(select(Answer).where(Answer.team_id == team.id)) if a.choice == correct[a.question_id].correct) if quiz_closed else 0
        scores = [100 * points / total_points if total_points else 0, 0, 0]
        for s in db.scalars(select(Submission).where(Submission.team_id == team.id, Submission.approved == True)):
            task = db.get(Task, s.task_id)
            scores[task.round-1] += sum(v * c['weight'] / 100 for v, c in zip(s.scores or [], task.rubric)) / (db.scalar(select(func.count()).select_from(Task).where(Task.round == task.round)) or 1)
        rows.append(dict(team_id=team.id, team=team.name, rounds=[round(v, 4) for v in scores], total=round(sum(v*w/100 for v, w in zip(scores, comp.weights)), 4)))
    tie_index = 0 if comp.tie_break == 'quiz' else 2
    rows.sort(key=lambda r: (-r['total'], -(r['rounds'][tie_index] if comp.tie_break != 'shared' else 0), r['team'].lower()))
    previous, rank = None, 0
    for i, row in enumerate(rows):
        key = (row['total'], row['rounds'][tie_index] if comp.tie_break != 'shared' else 0)
        if key != previous: rank = i+1
        row['rank'], previous = rank, key
    return rows

@app.get('/api/leaderboard')
def leaderboard(user=Depends(auth), db=Depends(database, scope='function')):
    comp = competition(db)
    if user.role == 'participant' and not comp.published: return dict(published=False, rows=[])
    return dict(published=comp.published, rows=results(db))

class Publish(BaseModel): published: bool
@app.post('/api/admin/publish')
def publish(body: Publish, user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin')
    comp = competition(db)
    if body.published:
        abort(db.scalar(select(func.count()).select_from(Task).where(Task.status != 'ended')) > 0, 409, 'Close all tasks before publishing final results.')
        abort(db.scalar(select(func.count()).select_from(Submission).where(Submission.approved == False)) > 0, 409, 'Approve all received submissions before publishing results.')
    comp.published = body.published
    audit(db, user, 'results_published' if body.published else 'results_unpublished', {})
    return {'published': comp.published}

@app.get('/api/admin/export')
def export(kind: str = 'results', user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin', 'judge')
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    def safe(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value
    if kind == 'results':
        writer.writerow(['rank', 'team_id', 'team', 'quiz', 'recreation', 'logo', 'weighted_total', 'approved_creative_criteria'])
        for row in results(db):
            criteria = {str(s.task_id): s.scores for s in db.scalars(select(Submission).where(Submission.team_id == row['team_id'], Submission.approved == True))}
            writer.writerow([row['rank'], row['team_id'], safe(row['team']), *row['rounds'], row['total'], json.dumps(criteria)])
    elif kind == 'submissions':
        writer.writerow(['submission_id', 'team_id', 'task_id', 'timestamp_utc_epoch', 'receipt', 'revision', 'prompt', 'conversation_link', 'asset_id', 'evidence_id', 'late', 'approved', 'status', 'scores', 'judge_notes'])
        for s in db.scalars(select(Submission)): writer.writerow([s.id, s.team_id, s.task_id, s.submitted, s.receipt, s.revision, safe(s.prompt), safe(s.link), s.asset_id, s.evidence_id, s.late, s.approved, s.status, json.dumps(s.scores), safe(s.notes)])
    else: raise HTTPException(422, 'Choose results or submissions.')
    return Response('\ufeff' + output.getvalue(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="promptpop-{kind}.csv"'})

@app.get('/api/admin/export-assets')
def export_assets(user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin', 'judge')
    # A spooled temporary file avoids holding large events entirely in memory.
    import tempfile
    bundle = tempfile.SpooledTemporaryFile(max_size=8*1024*1024)
    manifest = []
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for s in db.scalars(select(Submission)):
            for asset_id in [s.asset_id, s.evidence_id]:
                if not asset_id: continue
                asset = db.get(Asset, asset_id)
                path = STORAGE / asset.id
                if path.is_file(): archive.write(path, f'{s.team_id}/task-{s.task_id}/{asset.kind}-{asset.id}.png')
            manifest.append(submission_view(s))
        archive.writestr('submissions.json', json.dumps(manifest, indent=2))
    bundle.seek(0)
    def chunks():
        try:
            while chunk := bundle.read(64*1024): yield chunk
        finally: bundle.close()
    return StreamingResponse(chunks(), media_type='application/zip', headers={'Content-Disposition':'attachment; filename="promptpop-submissions.zip"'})

@app.get('/api/admin/audit')
def audit_log(user=Depends(auth), db=Depends(database, scope='function')):
    require(user, 'admin')
    names = {u.id: u.username for u in db.scalars(select(User))}
    return [dict(id=a.id, actor=names.get(a.actor, a.actor), action=a.action, timestamp=a.timestamp, details=a.details) for a in db.scalars(select(Audit).order_by(Audit.timestamp.desc()).limit(500))]

@app.get('/api/health')
def health(): return {'status': 'ok'}

if Path('frontend/dist').is_dir():
    app.mount('/assets', StaticFiles(directory='frontend/dist/assets'), name='static-assets')
    @app.get('/{path:path}')
    def frontend(path: str):
        abort(path.startswith('api/'), 404, 'API endpoint not found.')
        candidate = (Path('frontend/dist') / path).resolve()
        root = Path('frontend/dist').resolve()
        if candidate.is_relative_to(root) and candidate.is_file(): return FileResponse(candidate)
        return FileResponse(root / 'index.html')
