"""Create the first organizer from private provider environment configuration."""
import os
import time
import uuid
from sqlalchemy import select
from .models import Session, User, Audit
from .security import password_hash


def bootstrap_admin():
    with Session.begin() as db:
        # Redeploying must never reset an existing organizer's credentials.
        if db.scalar(select(User.id).where(User.role == 'admin').limit(1)):
            return
        password = os.getenv('BOOTSTRAP_ADMIN_PASSWORD', '')
        if not password:
            if os.getenv('APP_ENV') == 'production':
                raise RuntimeError('Set BOOTSTRAP_ADMIN_PASSWORD before the first production startup.')
            return
        username = os.getenv('BOOTSTRAP_ADMIN_USERNAME', 'organizer').strip().lower()
        if not username or len(username) > 100 or not 16 <= len(password) <= 200:
            raise RuntimeError('Bootstrap needs a username of 1–100 characters and a password of 16–200 characters.')
        if db.scalar(select(User.id).where(User.username == username)):
            raise RuntimeError('The bootstrap organizer username is already assigned to another account.')
        user_id = str(uuid.uuid4())
        db.add(User(id=user_id, username=username, password=password_hash(password), role='admin'))
        db.flush()
        db.add(Audit(id=str(uuid.uuid4()), actor=user_id, action='admin_bootstrapped',
                     timestamp=time.time(), details={'username': username}))
