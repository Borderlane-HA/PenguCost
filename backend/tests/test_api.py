import json
from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete
from app import main, statements
from app.db import Base, engine, SessionLocal
from app.models import StatementJob, StatementImport, AIConversation, Expense, ExpenseChange, ReminderAction
from .test_statements import pdf_bytes


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    # Prevent the optional provider-icon timer in isolated API tests.
    main._PROVIDER_REFRESH_THREAD_STARTED = True
    with TestClient(main.app) as client:
        assert client.post('/api/auth/bootstrap',json={'username':'admin','password':'TestPassword123','display_name':'Test'}).status_code == 200
        yield client


def profile(client):
    result=client.post('/api/settings/ai/profiles',json={'name':'Local model','provider':'ollama','base_url':'http://127.0.0.1:11434/v1','model':'test'})
    assert result.status_code == 200
    return result.json()['id']


def model_rows():
    return {'transactions':[{'date':f'2026-{m:02}-05','merchant':'Netflix','reference':'','account_key':'DE123456',
        'amount':15.99,'currency':'EUR','entry_type':'expense','page':1,
        'evidence':f'2026-{m:02}-05 Netflix 15.99 EUR debit'} for m in range(1,5)]}


def upload(client, profile_id, consent='true',raw=None):
    raw = raw or pdf_bytes(['Personal statement period January - April 2026 account data',
        *[f'2026-{m:02}-05 Netflix 15.99 EUR debit' for m in range(1,5)]])
    return client.post('/api/ai/statements',data={'profile_id':str(profile_id),'consent':consent},files=[('files',('statement.pdf',raw,'application/pdf'))])


def test_upload_review_import_idempotency_and_delete(client,monkeypatch):
    monkeypatch.setattr(statements,'_call_model',AsyncMock(return_value=json.dumps(model_rows())))
    result=upload(client,profile(client))
    assert result.status_code == 202
    job_id=result.json()['id']; job=client.get(f'/api/ai/statements/{job_id}').json()
    assert job['status']=='ready' and job['completed_pages']==1
    candidate=job['candidates'][0]
    assert candidate['count']==4 and candidate['billing_interval']=='monthly'
    assert client.get('/api/expenses').json()==[]  # Analysis itself never creates entries.
    with SessionLocal() as db:
        saved=db.get(StatementJob,job_id)
        assert 'Netflix' not in saved.result_encrypted and '2026-01-05' not in saved.result_encrypted
    url=f"/api/ai/statements/{job_id}/candidates/{candidate['id']}/import"
    body={'name':'Netflix subscription','provider':'Netflix','amount':15.99,'start_date':date.today().isoformat()}
    first=client.post(url,json=body)
    assert first.status_code==200
    assert client.post(url,json=body).status_code==409
    assert len(client.get('/api/expenses').json())==1
    assert client.get(f'/api/ai/statements/{job_id}').json()['candidates'][0]['imported_expense_id']==first.json()['id']
    assert client.delete(f'/api/ai/statements/{job_id}').status_code==200
    assert len(client.get('/api/expenses').json())==1


def test_permission_isolation_and_private_catalog(client,monkeypatch):
    monkeypatch.setattr(statements,'_call_model',AsyncMock(return_value=json.dumps(model_rows())))
    job_id=upload(client,profile(client)).json()['id']
    own_account=client.post('/api/accounts',json={'name':'Private bank','scope':'private'}).json()['id']
    member_id=client.post('/api/users',json={'username':'member','password':'MemberPassword123','role':'member'}).json()['id']
    client.post('/api/auth/logout');client.post('/api/auth/login',json={'username':'member','password':'MemberPassword123'})
    assert client.get('/api/ai/statements').json()==[]
    assert client.get(f'/api/ai/statements/{job_id}').status_code==404
    assert client.delete(f'/api/ai/statements/{job_id}').status_code==404
    assert client.post(f'/api/ai/statements/{job_id}/candidates/fake/import',json={'name':'x','amount':1}).status_code==404
    result=client.post('/api/ai/statements',data={'profile_id':'1','consent':'true','account_id':str(own_account)},files={'files':('file.pdf',b'%PDF-1.4','application/pdf')})
    assert result.status_code==403


def test_upload_consent_format_and_disabled_profile(client):
    p=profile(client)
    assert upload(client,p,consent='false').status_code==400
    assert upload(client,p,raw=b'fake pdf').status_code==400
    client.put(f'/api/settings/ai/profiles/{p}',json={'enabled':False})
    assert upload(client,p).status_code==400


def test_admission_limits(client):
    p=profile(client)
    with SessionLocal() as db:
        db.add(StatementJob(id='existing',user_id=1,status='running'));db.commit()
    assert upload(client,p).status_code==409


def test_bad_model_reply_is_error_without_partial_success(client,monkeypatch):
    monkeypatch.setattr(statements,'_call_model',AsyncMock(return_value='{"transactions":['))
    result=upload(client,profile(client));job=client.get('/api/ai/statements/'+result.json()['id']).json()
    assert job['status']=='error' and 'JSON' in job['last_error']
    assert client.get('/api/expenses').json()==[]


def test_restart_clears_running_statement_and_chat_jobs(client):
    with SessionLocal() as db:
        db.add(StatementJob(id='restart',user_id=1,status='running'))
        db.add(AIConversation(user_id=1,status='running'));db.commit()
    main.startup()
    with SessionLocal() as db:
        assert db.get(StatementJob,'restart').status=='error'
        assert db.scalar(select(AIConversation)).status=='error'


def test_future_start_and_fixed_interval_are_correct(client):
    future=(date.today()+timedelta(days=45)).isoformat()
    expense=client.post('/api/expenses',json={'name':'Insurance','amount':120,'billing_interval':'yearly','start_date':future}).json()
    assert expense['monthly_equivalent']==10 and expense['interval_months']==12
    assert client.get('/api/dashboard').json()['monthly_expenses']==0


@pytest.mark.parametrize('fields',[{'name':'  ','amount':1},{'name':'x','amount':-1},{'name':'x','amount':1,'interval_months':0},
    {'name':'x','amount':1,'status':'bad'},{'name':'x','amount':1,'contract_url':'javascript:alert(1)'},
    {'name':'x','amount':1,'billing_interval':'weekly'},{'name':'x','amount':1,'currency':'xx'}])
def test_invalid_entries_are_rejected(client,fields):
    assert client.post('/api/expenses',json=fields).status_code==422


def test_import_replaces_statement_results_and_history_cleanly(client,monkeypatch):
    monkeypatch.setattr(statements,'_call_model',AsyncMock(return_value=json.dumps(model_rows())))
    result=upload(client,profile(client));job_id=result.json()['id']
    exported=client.get('/api/export/user').json()
    assert client.post('/api/import/user',json=exported).status_code==200
    assert client.get(f'/api/ai/statements/{job_id}').status_code==404


def test_results_disable_browser_cache(client):
    assert client.get('/api/ai/statements').headers['cache-control']=='no-store'


def test_admin_restore_invalidates_old_sessions(client):
    exported=client.get('/api/export/admin').json()
    assert client.post('/api/import/admin',json=exported).status_code==200
    assert client.get('/api/me').status_code==401
    assert client.post('/api/auth/login',json={'username':'admin','password':'TestPassword123'}).status_code==200


def test_corrupt_password_hash_fails_auth_without_server_error(client):
    from app.models import User
    with SessionLocal() as db:
        db.get(User,1).password_hash='invalid';db.commit()
    assert client.post('/api/auth/login',json={'username':'admin','password':'TestPassword123'}).status_code==401


def test_price_changes_preserve_historical_amounts(client):
    item=client.post('/api/expenses',json={'name':'Netflix','amount':10,'start_date':'2025-01-01'}).json()
    result=client.put('/api/expenses/'+str(item['id']),json={'name':'Netflix','amount':20,'start_date':'2025-01-01','price_effective_from':'2026-09-01'}).json()
    assert [p['amount'] for p in result['price_history']]==[10,20]
    assert result['price_history'][0]['valid_to']=='2026-08-31'


def test_original_upload_not_retained_in_data_directory(client,monkeypatch):
    from app.db import DATA_DIR
    monkeypatch.setattr(statements,'_call_model',AsyncMock(return_value=json.dumps(model_rows())))
    assert upload(client,profile(client)).status_code==202
    assert not list(DATA_DIR.rglob('*.pdf')) and not list(DATA_DIR.rglob('*.jpg'))


def test_invalid_json_finance_entry_rolls_back_existing_data(client):
    client.post('/api/expenses',json={'name':'Keep me','amount':12})
    exported=client.get('/api/export/user').json()
    exported['expenses'][0]['amount']=-20
    assert client.post('/api/import/user',json=exported).status_code==400
    assert client.get('/api/expenses').json()[0]['name']=='Keep me'


def test_duplicate_import_guard_is_atomic_under_concurrent_requests(client,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(statements,'_call_model',AsyncMock(return_value=json.dumps(model_rows())))
    job_id=upload(client,profile(client)).json()['id']
    candidate=client.get(f'/api/ai/statements/{job_id}').json()['candidates'][0]
    url=f"/api/ai/statements/{job_id}/candidates/{candidate['id']}/import"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:client.post(url,json={'name':'Concurrent','amount':15.99}).status_code,[0,1]))
    assert sorted(results)==[200,409]
    assert len(client.get('/api/expenses').json())==1


def test_unconverted_foreign_currency_statement_import_is_blocked(client,monkeypatch):
    monkeypatch.setattr(statements,'_call_model',AsyncMock(return_value=json.dumps(model_rows())))
    job_id=upload(client,profile(client)).json()['id']
    candidate=client.get(f'/api/ai/statements/{job_id}').json()['candidates'][0]
    url=f"/api/ai/statements/{job_id}/candidates/{candidate['id']}/import"
    assert client.post(url,json={'name':'Foreign draft','amount':10,'currency':'USD'}).status_code==400
    assert client.get('/api/expenses').json()==[]


def test_profile_statement_output_limit_is_used_and_roundtrips(client,monkeypatch):
    p=profile(client)
    assert client.put(f'/api/settings/ai/profiles/{p}',json={'statement_max_tokens':12000}).status_code==200
    model=AsyncMock(return_value=json.dumps(model_rows()))
    monkeypatch.setattr(statements,'_call_model',model)
    assert upload(client,p).status_code==202
    assert model.call_args.kwargs['max_tokens']==12000
    exported=client.get('/api/export/admin').json()
    assert exported['ai_profiles'][0]['statement_max_tokens']==12000


def test_upgrade_adds_profile_limit_without_losing_existing_data(client):
    from sqlalchemy import text
    from app.models import AIProfile
    p=profile(client)
    expense=client.post('/api/expenses',json={'name':'Existing contract','amount':42}).json()
    with engine.begin() as connection:
        connection.execute(text('ALTER TABLE ai_profiles DROP COLUMN statement_max_tokens'))
    # An actual upgrade starts a fresh process with no pre-migration pooled handles.
    engine.dispose()
    main.migrate_schema()
    with SessionLocal() as db:
        assert db.get(AIProfile,p).statement_max_tokens==0
        assert db.get(Expense,expense['id']).name=='Existing contract'


def test_ollama_automatic_output_roundtrips_through_export_restore(client,monkeypatch):
    p=profile(client)
    assert client.put(f'/api/settings/ai/profiles/{p}',json={'statement_context_tokens':65536}).status_code==200
    assert client.get('/api/settings/ai/profiles').json()[0]['statement_max_tokens']==0
    model=AsyncMock(return_value=json.dumps(model_rows()))
    monkeypatch.setattr(statements,'_call_model',model)
    assert upload(client,p).status_code==202
    assert model.call_args.kwargs['max_tokens']==0
    assert model.call_args.kwargs['ollama_context_tokens']==65536
    exported=client.get('/api/export/admin').json()
    assert exported['ai_profiles'][0]['statement_max_tokens']==0
    assert exported['ai_profiles'][0]['statement_context_tokens']==65536
    response=client.post('/api/import/admin',json=exported)
    assert response.status_code==200
    # Restore invalidates browser sessions; verify stored data directly.
    from app.models import AIProfile
    with SessionLocal() as db:
        assert db.get(AIProfile,p).statement_max_tokens==0
        assert db.get(AIProfile,p).statement_context_tokens==65536


def test_upgrade_adds_context_setting_without_changing_profile_or_expense(client):
    from sqlalchemy import text
    from app.models import AIProfile
    p=profile(client)
    assert client.put(f'/api/settings/ai/profiles/{p}',json={'statement_max_tokens':24000}).status_code==200
    expense=client.post('/api/expenses',json={'name':'Existing contract','amount':42}).json()
    with engine.begin() as connection:
        connection.execute(text('ALTER TABLE ai_profiles DROP COLUMN statement_context_tokens'))
    engine.dispose();main.migrate_schema()
    with SessionLocal() as db:
        assert db.get(AIProfile,p).statement_context_tokens==32768
        assert db.get(AIProfile,p).statement_max_tokens==24000
        assert db.get(Expense,expense['id']).amount==42


def test_ollama_default_migration_is_once_only_and_preserves_custom_limits(client):
    from sqlalchemy import text
    from app.models import AIProfile
    old=profile(client);custom=profile(client)
    assert client.put(f'/api/settings/ai/profiles/{old}',json={'statement_max_tokens':8000}).status_code==200
    assert client.put(f'/api/settings/ai/profiles/{custom}',json={'statement_max_tokens':24000}).status_code==200
    other=client.post('/api/settings/ai/profiles',json={'name':'Other','provider':'custom','base_url':'https://example.test/v1','model':'test'}).json()['id']
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM settings WHERE key='migration_051_ollama_automatic_output'"))
    main.migrate_schema()
    with SessionLocal() as db:
        assert db.get(AIProfile,old).statement_max_tokens==0
        assert db.get(AIProfile,custom).statement_max_tokens==24000
        assert db.get(AIProfile,other).statement_max_tokens==8000
    assert client.put(f'/api/settings/ai/profiles/{old}',json={'statement_max_tokens':8000}).status_code==200
    main.migrate_schema()
    with SessionLocal() as db:
        assert db.get(AIProfile,old).statement_max_tokens==8000


def test_statement_error_preserves_safe_diagnostic_message(client,monkeypatch):
    from app.ai import AIResponseError
    monkeypatch.setattr(statements,'_call_model',AsyncMock(side_effect=AIResponseError('thinking_only')))
    job_id=upload(client,profile(client)).json()['id']
    job=client.get(f'/api/ai/statements/{job_id}').json()
    assert job['status']=='error'
    assert 'reasoning but no final answer' in job['last_error']


def test_rejected_model_rows_expose_safe_counts_not_false_no_bookings(client,monkeypatch):
    rows=model_rows();rows['transactions'][0]['amount']='INVALID PRIVATE VALUE'
    rows['transactions'][1]['date']='INVALID PRIVATE DATE'
    monkeypatch.setattr(statements,'_call_model',AsyncMock(return_value=json.dumps(rows)))
    job_id=upload(client,profile(client)).json()['id']
    job=client.get(f'/api/ai/statements/{job_id}').json()
    assert job['status']=='ready' and job['transaction_count']==2
    assert job['rejected_transactions']==2
    assert job['rejection_reasons']=={'schema_amount':1,'schema_date':1}
    assert 'PRIVATE' not in json.dumps(job)
