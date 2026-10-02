"""Validate a PenguCost volume backup before replacing any live files."""
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

MEMBERS = {'.pengucost-backup.db': 'pengucost.db',
           '.session_secret': '.session_secret', '.fernet_key': '.fernet_key'}


def restore(archive: str, destination: str, check_only: bool = False):
    root = Path(destination)
    with tempfile.TemporaryDirectory(prefix='pengucost-restore-', dir=root) as tmp:
        stage = Path(tmp)
        with tarfile.open(archive, 'r:gz') as bundle:
            seen = set()
            for member in bundle:
                if member.name not in MEMBERS or member.name in seen or not member.isfile():
                    raise ValueError('Backup contains unexpected, duplicate or unsafe archive entries')
                if member.size <= 0 or member.size > (2 * 1024**3 if member.name.endswith('.db') else 4096):
                    raise ValueError('Invalid backup file size')
                seen.add(member.name)
                with bundle.extractfile(member) as source, (stage / MEMBERS[member.name]).open('wb') as target:
                    shutil.copyfileobj(source, target)
            if seen != set(MEMBERS):
                raise ValueError('Backup must include database, session secret and encryption key')
        with sqlite3.connect(stage / 'pengucost.db') as database:
            if database.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Backup database failed integrity check')
            tables = {row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'users', 'expenses', 'settings'} <= tables:
                raise ValueError('Backup is not a PenguCost database')
        Fernet((stage / '.fernet_key').read_bytes().strip())
        if len((stage / '.session_secret').read_text().strip()) < 32:
            raise ValueError('Invalid session secret')
        if check_only:
            return
        # Retain previous bytes in the same volume for rollback if a replace fails.
        rollback = stage / 'previous'
        rollback.mkdir()
        names = list(MEMBERS.values()) + ['pengucost.db-wal', 'pengucost.db-shm', 'pengucost.db-journal']
        installed = []
        moved = []
        try:
            for name in names:
                live = root / name
                if live.exists():
                    os.replace(live, rollback / name)
                    moved.append(name)
            for name in MEMBERS.values():
                os.chmod(stage / name, 0o600)
                # The official container uses uid/gid 10001.
                if os.geteuid() == 0:
                    os.chown(stage / name, 10001, 10001)
                os.replace(stage / name, root / name)
                installed.append(name)
        except Exception:
            for name in installed:
                (root / name).unlink(missing_ok=True)
            for name in moved:
                os.replace(rollback / name, root / name)
            raise


if __name__ == '__main__':
    restore(sys.argv[1], sys.argv[2], '--check' in sys.argv[3:])
