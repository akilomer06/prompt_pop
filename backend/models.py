import os
from pathlib import Path
from sqlalchemy import create_engine, String, Float, Integer, ForeignKey, JSON, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import database_url

Path('data').mkdir(exist_ok=True)
DATABASE_URL = database_url(os.getenv('DATABASE_URL', 'sqlite:///./data/promptpop.db'))
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False, 'timeout': 30} if DATABASE_URL.startswith('sqlite') else {'connect_timeout': 10}, pool_pre_ping=True)
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_settings(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')

Session = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class Team(Base):
    __tablename__ = 'teams'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    members: Mapped[list] = mapped_column(JSON, default=list)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    team_id: Mapped[str | None] = mapped_column(ForeignKey('teams.id'), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)

class AuthSession(Base):
    __tablename__ = 'sessions'
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    expires: Mapped[float] = mapped_column(Float)
    seen: Mapped[float] = mapped_column(Float)

class Competition(Base):
    __tablename__ = 'competitions'
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    title: Mapped[str] = mapped_column(String(100), default='Prompt Pop 2K26')
    current: Mapped[int] = mapped_column(default=0)
    published: Mapped[bool] = mapped_column(default=False)
    weights: Mapped[list] = mapped_column(JSON, default=lambda: [30, 40, 30])
    tie_break: Mapped[str] = mapped_column(String(20), default='quiz')
    integrity_threshold: Mapped[int] = mapped_column(default=3)

class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(primary_key=True)
    round: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(150))
    brief: Mapped[str] = mapped_column(String(20000), default='')
    requirements: Mapped[str] = mapped_column(String(10000), default='')
    duration: Mapped[int] = mapped_column(default=600)
    grace: Mapped[int] = mapped_column(default=0)
    attempt_limit: Mapped[int] = mapped_column(default=3)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    deadline: Mapped[float | None] = mapped_column(Float, nullable=True)
    remaining: Mapped[float | None] = mapped_column(Float, nullable=True)
    rubric: Mapped[list] = mapped_column(JSON, default=list)
    reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

class Question(Base):
    __tablename__ = 'questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(String(3000))
    options: Mapped[list] = mapped_column(JSON)
    correct: Mapped[int] = mapped_column(Integer)
    points: Mapped[float] = mapped_column(Float, default=1)

class Answer(Base):
    __tablename__ = 'answers'
    __table_args__ = (UniqueConstraint('team_id', 'question_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey('teams.id'), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'))
    choice: Mapped[int] = mapped_column(Integer)
    saved: Mapped[float] = mapped_column(Float)

class Asset(Base):
    __tablename__ = 'assets'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str | None] = mapped_column(ForeignKey('teams.id'), nullable=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'))
    kind: Mapped[str] = mapped_column(String(20))
    mime: Mapped[str] = mapped_column(String(80))
    filename: Mapped[str] = mapped_column(String(200))

class Submission(Base):
    __tablename__ = 'submissions'
    __table_args__ = (UniqueConstraint('team_id', 'task_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey('teams.id'), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'), index=True)
    prompt: Mapped[str] = mapped_column(String(20000))
    link: Mapped[str] = mapped_column(String(2000), default='')
    rationale: Mapped[str] = mapped_column(String(10000), default='')
    asset_id: Mapped[str] = mapped_column(ForeignKey('assets.id'))
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey('assets.id'), nullable=True)
    submitted: Mapped[float] = mapped_column(Float)
    revision: Mapped[int] = mapped_column(default=1)
    receipt: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(30), default='awaiting_evaluation')
    late: Mapped[bool] = mapped_column(default=False)
    evidence_flag: Mapped[bool] = mapped_column(default=True)
    scores: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str] = mapped_column(String(10000), default='')
    approved: Mapped[bool] = mapped_column(default=False)

class Draft(Base):
    __tablename__ = 'drafts'
    __table_args__ = (UniqueConstraint('team_id', 'task_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey('teams.id'))
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'))
    content: Mapped[dict] = mapped_column(JSON)

class RequestReceipt(Base):
    __tablename__ = 'request_receipts'
    __table_args__ = (UniqueConstraint('team_id', 'key'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey('teams.id'))
    key: Mapped[str] = mapped_column(String(100))
    fingerprint: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)

class Incident(Base):
    __tablename__ = 'incidents'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(ForeignKey('teams.id'), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'))
    type: Mapped[str] = mapped_column(String(40))
    timestamp: Mapped[float] = mapped_column(Float)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewed: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str] = mapped_column(String(2000), default='')

class Evaluation(Base):
    __tablename__ = 'evaluations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey('submissions.id'), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    created: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))
    method: Mapped[str] = mapped_column(String(100))
    result: Mapped[dict] = mapped_column(JSON, default=dict)

class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor: Mapped[str] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(100))
    timestamp: Mapped[float] = mapped_column(Float, index=True)
    details: Mapped[dict] = mapped_column(JSON)
