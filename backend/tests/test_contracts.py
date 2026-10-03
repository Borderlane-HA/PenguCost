import json
from datetime import date, timedelta
import pytest
from sqlalchemy import select,func
from app import contracts, main
from app.db import SessionLocal
from app.models import Expense,ContractVersion,ExpensePrice,ExpenseChange
from .test_api import client


def create(client,**kwargs):
    r=client.post('/api/expenses',json={'name':'Internet','amount':31,'start_date':'2026-01-01',**kwargs})
    assert r.status_code==200,r.text
    return r.json()


def update(client,x,**kwargs):
    r=client.put(f"/api/expenses/{x['id']}",json={**x,**kwargs})
    assert r.status_code==200,r.text
    return r.json()


def periods(client,start='2026-01-01',end='2026-12-31'):
    r=client.get('/api/contracts/calendar',params={'start':start,'end':end})
    assert r.status_code==200,r.text
    return r.json()['segments']


def cost(client,start,end):
    return round(sum(p['period_cost'] for p in periods(client,start,end)),2)


def test_dated_price_assignment_and_lifetime(client):
    a=client.post('/api/accounts',json={'name':'Old bank'}).json()['id']
    b=client.post('/api/accounts',json={'name':'New bank'}).json()['id']
    x=create(client,account_id=a,contract_holder='Alice',contract_end='2026-06-30')
    x=update(client,x,amount=62,account_id=b,contract_holder='Bob',contract_end='2026-12-31',contract_effective_from='2026-04-01',price_effective_from='2026-03-16')
    assert cost(client,'2026-01-01','2026-01-31')==31
    assert cost(client,'2026-03-01','2026-03-31')==47
    rows=periods(client)
    assert rows[0]['account']=='Old bank' and rows[0]['contract_holder']=='Alice'
    assert rows[-1]['account']=='New bank' and rows[-1]['contract_holder']=='Bob'
    assert all(p['to']<'2026-04-01' for p in rows if p['account']=='Old bank')
    assert cost(client,'2026-07-01','2026-07-31')==62


def test_future_changes_do_not_change_current_or_previous(client):
    today=date.today();future=today+timedelta(days=40)
    x=create(client,start_date=(today-timedelta(days=60)).isoformat(),contract_holder='Original')
    changed=update(client,x,amount=90,contract_holder='Future',contract_effective_from=future.isoformat(),price_effective_from=future.isoformat())
    assert changed['amount']==31 and changed['contract_holder']=='Original'
    assert changed['next_contract_change']['values']['contract_holder']=='Future'
    assert changed['next_price_change']['amount']==90
    assert cost(client,today.isoformat(),today.isoformat())>0
    # Editing metadata alone must not insert a current price over a future price.
    changed=update(client,changed,name='Future name',contract_effective_from=future.isoformat(),update_price=False)
    assert changed['next_price_change']['amount']==90
    assert changed['name']=='Internet'


def test_leap_day_and_short_period_costs(client):
    create(client,amount=29,start_date='2024-02-01')
    assert cost(client,'2024-02-01','2024-02-29')==29
    assert cost(client,'2024-02-29','2024-02-29')==1
    assert cost(client,'2024-02-12','2024-02-18')==7


def test_anchored_renewal_and_renewal_price(client):
    x=create(client,amount=10,start_date='2026-01-01',contract_end='2026-01-31',auto_renew=True,renewal_period_months=1,renewal_amount=20)
    with SessionLocal() as db:
        row=db.get(Expense,x['id'])
        assert contracts.end_at(row,date(2026,3,1))==date(2026,3,31)
        assert contracts.amount_at(row,date(2026,2,1))==20
    assert cost(client,'2026-02-01','2026-02-28')==20
    update(client,x,amount=30,price_effective_from='2026-03-01',contract_effective_from='2026-03-01')
    assert cost(client,'2026-03-01','2026-03-31')==30


def test_cancellation_stops_renewal_not_old_costs(client):
    x=create(client,amount=10,contract_end='2026-03-31',auto_renew=True,renewal_period_months=12)
    update(client,x,auto_renew=False,status='cancelled',contract_effective_from='2026-03-01',update_price=False)
    assert cost(client,'2026-02-01','2026-02-28')==10
    assert cost(client,'2026-03-01','2026-03-31')==10
    assert cost(client,'2026-04-01','2026-04-30')==0


def test_one_time_never_repeats(client):
    create(client,amount=75,recurrence_type='one_time',start_date='2026-01-05')
    assert cost(client,'2026-01-01','2026-12-31')==75
    assert cost(client,'2026-01-06','2026-02-01')==0


def test_archive_hard_delete_and_planned_removal(client):
    x=create(client)
    future=(date.today()+timedelta(days=40)).isoformat()
    x=update(client,x,amount=55,contract_holder='Soon',contract_effective_from=future,price_effective_from=future)
    version=x['next_contract_change']['id'];price=x['price_history'][-1]['id']
    assert client.delete(f"/api/expenses/{x['id']}/versions/{version}").status_code==200
    assert client.delete(f"/api/expenses/{x['id']}/prices/{price}").status_code==200
    x=client.post(f"/api/expenses/{x['id']}/archive").json()
    assert x['is_archived'] and client.get('/api/expenses').json()==[]
    assert cost(client,'2026-01-01','2026-01-31')==31
    assert cost(client,(date.today()+timedelta(days=1)).isoformat(),(date.today()+timedelta(days=2)).isoformat())==0
    assert client.post(f"/api/expenses/{x['id']}/restore").status_code==200
    assert len(client.get('/api/expenses').json())==1
    assert client.delete(f"/api/expenses/{x['id']}").status_code==200
    with SessionLocal() as db:
        for cls in (Expense,ContractVersion,ExpensePrice,ExpenseChange):
            assert db.scalar(select(func.count()).select_from(cls))==0


def test_history_purge_keeps_anchor_and_blocks_earlier_edits(client):
    x=create(client,contract_holder='Old name')
    x=update(client,x,amount=62,contract_holder='New name',contract_effective_from='2026-04-01',price_effective_from='2026-04-01')
    r=client.post(f"/api/expenses/{x['id']}/history/purge",json={'before':'2026-05-01'})
    assert r.status_code==200,r.text
    x=r.json()
    assert cost(client,'2026-01-01','2026-04-30')==0
    assert cost(client,'2026-05-01','2026-05-31')==62
    assert all(p['valid_from']>='2026-05-01' for p in x['price_history'])
    assert 'Old name' not in json.dumps(x['contract_versions'])
    assert client.put(f"/api/expenses/{x['id']}",json={**x,'contract_effective_from':'2026-04-01'}).status_code==400
    assert client.post(f"/api/expenses/{x['id']}/history/purge",json={'before':'2300-01-01'}).status_code==400


def test_bulk_status_keeps_previous_periods(client):
    x=create(client)
    assert client.post('/api/expenses/bulk',json={'ids':[x['id']],'action':'status','value':'ended'}).status_code==200
    assert cost(client,'2026-01-01','2026-01-31')==31
    assert cost(client,date.today().isoformat(),date.today().isoformat())==0


def test_private_catalog_deletion_retains_historical_label(client):
    a=client.post('/api/accounts',json={'name':'Bank before'}).json()['id']
    x=create(client,account_id=a)
    assert client.delete(f'/api/accounts/{a}').status_code==200
    assert client.get('/api/expenses').json()[0]['account_id'] is None
    assert periods(client,'2026-01-01','2026-01-31')[0]['account']=='Bank before'


def test_user_backup_roundtrip_preserves_history_and_archive(client):
    x=create(client,contract_holder='Alice')
    x=update(client,x,amount=62,contract_holder='Bob',contract_effective_from='2026-04-01',price_effective_from='2026-04-01')
    client.post(f"/api/expenses/{x['id']}/archive")
    before=periods(client)
    backup=client.get('/api/export/user').json()
    r=client.post('/api/import/user',json=backup)
    assert r.status_code==200,r.text
    after=periods(client)
    assert [(s['from'],s['to'],s['period_cost'],s['contract_holder']) for s in before]==[(s['from'],s['to'],s['period_cost'],s['contract_holder']) for s in after]
    assert client.get('/api/expenses?include_archived=true').json()[0]['is_archived']


def test_calendar_bounds_and_user_isolation(client):
    x=create(client)
    assert client.get('/api/contracts/calendar?start=2026-01-01&end=2028-01-01').status_code==400
    client.post('/api/users',json={'username':'other','password':'OtherPassword123','role':'member'})
    client.post('/api/auth/logout');client.post('/api/auth/login',json={'username':'other','password':'OtherPassword123'})
    assert periods(client)==[]
    for action in ('archive','restore','history/purge'):
        assert client.post(f"/api/expenses/{x['id']}/{action}",json={'before':'2026-02-01'}).status_code==404


def test_restore_does_not_fill_archival_gap(client):
    x=create(client)
    with SessionLocal() as db:
        row=db.get(Expense,x['id'])
        contracts.archive_record(db,row,date(2026,2,28))
        contracts.restore_record(db,row,date(2026,5,1))
        db.commit()
    assert cost(client,'2026-01-01','2026-01-31')==31
    assert cost(client,'2026-03-01','2026-04-30')==0
    assert cost(client,'2026-05-01','2026-05-31')==31


def test_catalog_rename_keeps_previous_name(client):
    a=client.post('/api/accounts',json={'name':'Previous name'}).json()['id']
    create(client,account_id=a)
    assert client.patch(f'/api/accounts/{a}',json={'name':'New name'}).status_code==200
    assert client.get('/api/expenses').json()[0]['account']=='New name'
    assert periods(client,'2026-01-01','2026-01-31')[0]['account']=='Previous name'


def test_admin_backup_restores_all_contract_versions(client):
    x=create(client,contract_holder='Alice')
    update(client,x,amount=62,contract_holder='Bob',contract_effective_from='2026-04-01',price_effective_from='2026-04-01')
    before=periods(client)
    backup=client.get('/api/export/admin').json()
    r=client.post('/api/import/admin',json=backup)
    assert r.status_code==200,r.text
    client.post('/api/auth/login',json={'username':'admin','password':'TestPassword123'})
    after=periods(client)
    assert [(s['from'],s['to'],s['period_cost'],s['contract_holder']) for s in before]==[(s['from'],s['to'],s['period_cost'],s['contract_holder']) for s in after]


def test_catalog_delete_accounts_for_scheduled_versions(client):
    a=client.post('/api/accounts',json={'name':'Current account'}).json()['id']
    b=client.post('/api/accounts',json={'name':'Future account'}).json()['id']
    x=create(client,account_id=a)
    future=(date.today()+timedelta(days=40)).isoformat()
    x=update(client,x,account_id=b,contract_effective_from=future,update_price=False)
    assert x['account_id']==a
    assert client.delete(f'/api/accounts/{a}').status_code==200
    x=client.get('/api/expenses').json()[0]
    assert x['account_id'] is None
    assert x['next_contract_change']['values']['account_id']==b
    assert client.delete(f'/api/accounts/{b}').status_code==200
    x=client.get('/api/expenses').json()[0]
    assert x['next_contract_change']['values']['account_id'] is None
    assert periods(client,'2026-01-01','2026-01-31')[0]['account']=='Current account'


def test_removing_plan_updates_storage_columns(client):
    x=create(client,contract_holder='Original')
    future=(date.today()+timedelta(days=40)).isoformat()
    x=update(client,x,contract_holder='Planned',contract_effective_from=future,update_price=False)
    assert client.delete(f"/api/expenses/{x['id']}/versions/{x['next_contract_change']['id']}").status_code==200
    with SessionLocal() as db:
        assert db.get(Expense,x['id']).contract_holder=='Original'
