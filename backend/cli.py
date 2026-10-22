import argparse
import getpass
import secrets
from sqlalchemy import select
from .seed import initialize
from .models import Session, User
from .security import password_hash
from .app import uid

def main():
    parser = argparse.ArgumentParser(description='Create a Prompt Pop organizer account; no default passwords.')
    parser.add_argument('username')
    parser.add_argument('--role', choices=['admin', 'judge'], default='admin')
    parser.add_argument('--generate', action='store_true', help='Print a generated password once.')
    args = parser.parse_args()
    initialize()
    password = secrets.token_urlsafe(18) if args.generate else getpass.getpass('Password (at least 12 characters): ')
    if len(password) < 12: parser.error('Use at least 12 characters.')
    with Session.begin() as db:
        if db.scalar(select(User).where(User.username == args.username.lower())): parser.error('Account exists; choose another username.')
        db.add(User(id=uid(), username=args.username.strip().lower(), password=password_hash(password), role=args.role))
    print(f'Created {args.role} account: {args.username.lower()}')
    if args.generate: print(f'Password: {password}')

if __name__ == '__main__': main()
