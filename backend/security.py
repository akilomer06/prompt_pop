import hashlib
import hmac
import secrets
import time
from fastapi import HTTPException, Request
from sqlalchemy import select
from .models import AuthSession, User

def password_hash(value):
    salt = secrets.token_hex(16)
    return salt + ':' + hashlib.scrypt(value.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()

def verify_password(value, stored):
    salt, expected = stored.split(':')
    actual = hashlib.scrypt(value.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, expected)

def token_hash(token): return hashlib.sha256(token.encode()).hexdigest()

def current_user(request: Request, db):
    session = db.get(AuthSession, token_hash(request.cookies.get('pp_session', '')))
    if not session or session.expires < time.time(): raise HTTPException(401, 'Sign in to continue.')
    user = db.get(User, session.user_id)
    if not user or not user.active: raise HTTPException(401, 'This account has been disabled.')
    if session.seen < time.time() - 10: session.seen = time.time()
    return user

def require(user, *roles):
    if user.role not in roles: raise HTTPException(403, 'Your account cannot perform this action.')
