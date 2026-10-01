import os
from pathlib import Path
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Cookie, HTTPException

ph = PasswordHasher()
DATA_DIR = Path(os.getenv('PENGUCOST_DATA_DIR', '/data'))
SECRET_FILE = DATA_DIR / '.session_secret'
FERNET_FILE = DATA_DIR / '.fernet_key'

def _load_or_create(path: Path, generator):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_text().strip()
    value = generator()
    path.write_text(value)
    os.chmod(path, 0o600)
    return value

SESSION_SECRET = _load_or_create(SECRET_FILE, lambda: os.urandom(48).hex())
FERNET_KEY = _load_or_create(FERNET_FILE, lambda: Fernet.generate_key().decode())
serializer = URLSafeTimedSerializer(SESSION_SECRET, salt='pengucost-session')
fernet = Fernet(FERNET_KEY.encode())

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except VerifyMismatchError:
        return False

def make_session(user_id: int) -> str:
    return serializer.dumps({'uid': user_id})

def session_user_id(pengucost_session: str | None = Cookie(default=None)) -> int:
    if not pengucost_session:
        raise HTTPException(401, 'Not authenticated')
    try:
        payload = serializer.loads(pengucost_session, max_age=60 * 60 * 24 * 30)
        return int(payload['uid'])
    except (BadSignature, SignatureExpired, KeyError, ValueError):
        raise HTTPException(401, 'Invalid session')

def encrypt_secret(value: str) -> str:
    return fernet.encrypt(value.encode()).decode() if value else ''

def decrypt_secret(value: str) -> str:
    if not value:
        return ''
    try:
        return fernet.decrypt(value.encode()).decode()
    except Exception:
        return ''
