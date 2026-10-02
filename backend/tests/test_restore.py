import importlib.util
import io
import sqlite3
import tarfile
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

spec=importlib.util.spec_from_file_location('restore_data',Path(__file__).resolve().parents[2]/'scripts/restore-data.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@pytest.fixture(autouse=True)
def portable_owner_change(monkeypatch):
    # The workspace filesystem has no container UID mapping. Docker owns this operation.
    monkeypatch.setattr(module.os, 'chown', lambda *args: None)


def backup(tmp_path, change=None):
    db_path=tmp_path/'source.db'
    with sqlite3.connect(db_path) as db:
        db.executescript('CREATE TABLE users(id INTEGER); CREATE TABLE expenses(id INTEGER); CREATE TABLE settings(key TEXT); INSERT INTO users VALUES(42);')
    values={'.pengucost-backup.db':db_path.read_bytes(),'.session_secret':b'a'*96,'.fernet_key':Fernet.generate_key()}
    values.update(change or {})
    archive=tmp_path/'backup with spaces.tar.gz'
    with tarfile.open(archive,'w:gz') as bundle:
        for name,content in values.items():
            info=tarfile.TarInfo(name);info.size=len(content);bundle.addfile(info,io.BytesIO(content))
    return archive


def test_restore_precheck_does_not_modify_existing_files(tmp_path):
    data=tmp_path/'data';data.mkdir();(data/'pengucost.db').write_bytes(b'current database')
    archive=backup(tmp_path)
    module.restore(str(archive),str(data),check_only=True)
    assert (data/'pengucost.db').read_bytes()==b'current database'
    module.restore(str(archive),str(data))
    with sqlite3.connect(data/'pengucost.db') as db:
        assert db.execute('SELECT id FROM users').fetchone()==(42,)


@pytest.mark.parametrize('change',[{'.pengucost-backup.db':b'corrupt'}, {'.fernet_key':b'invalid'}, {'../outside':b'unsafe'}])
def test_invalid_backup_cannot_destroy_live_data(tmp_path,change):
    data=tmp_path/'data';data.mkdir();(data/'pengucost.db').write_bytes(b'live')
    with pytest.raises(Exception): module.restore(str(backup(tmp_path,change)),str(data))
    assert (data/'pengucost.db').read_bytes()==b'live'
    assert not (tmp_path/'outside').exists()


def test_replacement_failure_restores_previous_database_and_keys(tmp_path,monkeypatch):
    data=tmp_path/'data';data.mkdir()
    for name in ['pengucost.db','.session_secret','.fernet_key']:(data/name).write_bytes(b'original '+name.encode())
    archive=backup(tmp_path);original_replace=module.os.replace;failed=False
    def fail_once(source,destination):
        nonlocal failed
        if not failed and Path(destination)==data/'.session_secret':
            failed=True;raise OSError('simulated disk failure')
        return original_replace(source,destination)
    monkeypatch.setattr(module.os,'replace',fail_once)
    with pytest.raises(OSError):module.restore(str(archive),str(data))
    for name in ['pengucost.db','.session_secret','.fernet_key']:assert (data/name).read_bytes()==b'original '+name.encode()
