import json
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app import statements
from app.db import SessionLocal
from app.models import StatementJob
from app.statements import csv_table, csv_transactions, correct_booking, StatementError, parse_transactions
from .test_api import client, profile, upload, model_rows


CSV = 'Buchungstag;Begünstigter/Zahlungspflichtiger;Betrag;Währung\n05.01.2026;Netflix;-15,99;EUR\n05.02.2026;Netflix;-16,99;EUR\n10.02.2026;Fahrradladen;-150,00;EUR\n28.02.2026;Gehalt;3000,00;EUR\n'


@pytest.mark.parametrize('encoding', ['utf-8-sig', 'cp1252'])
def test_csv_german_bank_headers_encodings_signed_amounts_and_singletons(encoding):
    table = csv_table(CSV.encode(encoding))
    assert table['mapping']['currency'] == 3 and table['mapping']['merchant'] == 1
    rows, rejected, diagnostics = csv_transactions(table, table['mapping'], 'bank.csv')
    assert not rejected and not diagnostics and len(rows) == 4
    assert rows[-1]['entry_type'] == 'income' and rows[0]['amount'] == 15.99
    result = statements.build_candidates(rows)
    assert len(result['candidates']) == 1 and len(result['single_candidates']) == 2
    assert result['candidates'][0]['amount'] == 16.99
    assert result['single_candidates'][0]['recurrence_type'] == 'one_time'
    assert result['candidates'][0]['occurrences'][0]['source_line'] == 2


def test_csv_preamble_quoted_delimiters_explicit_mapping_and_mdy():
    table = csv_table(b'Export\nDate,Payee,Amount,Currency\n03/04/2026,"Store, Inc",-10.50,USD\n')
    assert table['header_row'] == 2
    rows, rejected, _ = csv_transactions(table, table['mapping'], 'bank.csv', date_format='mdy')
    assert rows[0]['date'] == '2026-03-04' and rows[0]['merchant'] == 'Store, Inc'
    assert rows[0]['currency'] == 'USD' and not rejected


def test_csv_debit_credit_columns_preserve_genuine_identical_bookings():
    table = csv_table(b'Date;Merchant;Debit;Credit\n2026-01-01;Shop;10,00;\n2026-01-01;Shop;10,00;\n2026-01-02;Salary;;100,00\n')
    rows, rejected, _ = csv_transactions(table, table['mapping'], 'bank.csv')
    assert not rejected
    assert [row['entry_type'] for row in rows] == ['expense', 'expense', 'income']
    assert statements.build_candidates(rows)['transaction_count'] == 3


def test_unsigned_amount_can_explicitly_be_an_expense():
    table = csv_table(b'Date;Merchant;Amount\n2026-01-01;Shop;10,00\n')
    rows, _, _ = csv_transactions(table, table['mapping'], 'bank.csv', direction='expense')
    assert rows[0]['entry_type'] == 'expense'


@pytest.mark.parametrize('raw', [b'', b'\x00fake', b'just one column', b'Date;Merchant;Amount\n' + b'2026-01-01;Shop;10\n' * 2001])
def test_csv_invalid_or_oversized_documents_fail(raw):
    with pytest.raises(StatementError):
        csv_table(raw)


@pytest.mark.parametrize('mapping', [{'date': True}, {'date': -1}, {'unknown': 1}, {'date': 100}, []])
def test_invalid_csv_mapping_never_reads_arbitrary_columns(mapping):
    with pytest.raises(StatementError):
        csv_transactions(csv_table(CSV.encode()), mapping, 'bank.csv')


def test_rejected_booking_corrects_against_original_source_not_new_evidence():
    row = model_rows()['transactions'][0]
    original = row['evidence']
    row.update(amount=999, evidence_lines=[999])
    rejected, diagnostics = [], {}
    rows, count = parse_transactions(json.dumps({'transactions': [row]}), [{'page': 1, 'text': original}], 'bank.pdf', diagnostics, rejected)
    assert rows == [] and count == 1 and rejected[0]['evidence'] == original
    corrected = dict(rejected[0]['fields'], amount=15.99)
    with pytest.raises(StatementError):
        correct_booking(rejected[0], corrected, False)
    with pytest.raises(StatementError, match='evidence_amount'):
        correct_booking(rejected[0], dict(corrected, amount=888), True)
    fixed = correct_booking(rejected[0], corrected, True)
    assert fixed['amount'] == 15.99 and fixed['manually_reviewed']
    assert fixed['account_key'] != row['account_key']


def test_missing_source_cannot_be_bypassed_with_manual_confirmation():
    row = model_rows()['transactions'][0]
    rejected = []
    parse_transactions(json.dumps({'transactions': [dict(row, page=2)]}), [{'page': 1, 'text': row['evidence']}], 'bank.pdf', {}, rejected)
    assert not rejected[0]['evidence']
    with pytest.raises(StatementError, match='No original booking'):
        correct_booking(rejected[0], row, True)


def test_mdy_csv_correction_keeps_original_date_format():
    table = csv_table(b'Date;Merchant;Amount;Currency\n03/04/2026;Shop;-10,00;xyz\n')
    rows, rejected, _ = csv_transactions(table, table['mapping'], 'bank.csv', date_format='mdy')
    assert not rows and len(rejected) == 1
    fixed = correct_booking(rejected[0], dict(rejected[0]['fields'], currency='EUR'), True)
    assert fixed['date'] == '2026-03-04' and '03/04/2026' in fixed['evidence']


def import_csv(client, content=CSV):
    mapping = csv_table(content.encode())['mapping']
    return client.post('/api/ai/statements/csv/import', data={'mapping': json.dumps(mapping)},
                       files={'file': ('bank.csv', content.encode(), 'text/csv')})


def test_csv_preview_and_import_need_no_profile_and_create_no_entries(client, monkeypatch):
    model = AsyncMock(side_effect=AssertionError('CSV must not use AI'))
    monkeypatch.setattr(statements, '_call_model', model)
    preview = client.post('/api/ai/statements/csv/preview', files={'file': ('bank.csv', CSV.encode(), 'text/csv')})
    assert preview.status_code == 200 and preview.json()['row_count'] == 4
    response = import_csv(client)
    assert response.status_code == 201
    result = response.json()
    assert result['source_kind'] == 'csv' and result['transaction_count'] == 4
    assert 'transactions' not in result and client.get('/api/expenses').json() == []
    assert not model.called
    with SessionLocal() as db:
        assert 'Netflix' not in db.get(StatementJob, result['id']).result_encrypted
    single = next(c for c in result['single_candidates'] if c['name'] == 'Fahrradladen')
    url = f"/api/ai/statements/{result['id']}/candidates/{single['id']}/import"
    response = client.post(url, json={'name': single['name'], 'amount': single['amount'], 'recurrence_type': 'one_time', 'start_date': single['last_date'], 'next_due_date': single['last_date']})
    assert response.status_code == 200 and response.json()['recurrence_type'] == 'one_time'
    assert response.json()['next_due_date'] == '2026-02-10'
    assert client.post(url, json={'name': 'Duplicate', 'amount': 150}).status_code == 409


def test_linked_entry_update_retains_contract_and_price_history_and_guards_retries(client):
    existing = client.post('/api/expenses', json={'name': 'My Netflix', 'provider': 'Netflix', 'amount': 10, 'start_date': '2025-01-01', 'contract_end': '2027-12-31', 'notes': 'Keep these notes'}).json()
    job = import_csv(client).json()
    candidate = job['candidates'][0]
    assert candidate['existing_matches'][0]['id'] == existing['id']
    url = f"/api/ai/statements/{job['id']}/candidates/{candidate['id']}/import"
    data = {**existing, 'target_expense_id': existing['id'], 'amount': 16.99}
    assert client.post(url, json=data).status_code == 400
    data['price_effective_from'] = '2026-02-05'
    response = client.post(url, json=data)
    assert response.status_code == 200
    updated = response.json()
    assert updated['id'] == existing['id'] and updated['contract_end'] == '2027-12-31'
    assert updated['notes'] == 'Keep these notes'
    assert [p['amount'] for p in updated['price_history']] == [10, 16.99]
    assert updated['price_history'][0]['valid_to'] == '2026-02-04'
    assert client.post(url, json=data).status_code == 409
    assert len(client.get('/api/expenses').json()) == 1


def test_rejected_api_review_updates_counts_and_cannot_inject_unverified_amount(client, monkeypatch):
    rows = model_rows()
    rows['transactions'][0]['amount'] = 999
    monkeypatch.setattr(statements, '_call_model', AsyncMock(return_value=json.dumps(rows)))
    job_id = upload(client, profile(client)).json()['id']
    job = client.get('/api/ai/statements/' + job_id).json()
    row = job['rejected_rows'][0]
    assert row['source'] == '1. statement.pdf' and row['page'] == 1
    assert 'account_key' not in row and 'year_context' not in row
    url = f"/api/ai/statements/{job_id}/rejected/{row['id']}/review"
    assert client.post(url, json={**row['fields'], 'reviewed': True}).status_code == 400
    fixed = client.post(url, json={**row['fields'], 'amount': 15.99, 'reviewed': True})
    assert fixed.status_code == 200 and fixed.json()['transaction_count'] == 4
    assert fixed.json()['rejected_transactions'] == 0 and fixed.json()['rejected_rows'] == []
    assert fixed.json()['candidates'][0]['count'] == 4
    assert client.post(url, json={**row['fields'], 'amount': 15.99, 'reviewed': True}).status_code == 404
    assert client.get('/api/expenses').json() == []


def test_other_user_cannot_link_existing_entry_or_review_foreign_job(client):
    existing = client.post('/api/expenses', json={'name': 'Private Netflix', 'amount': 10}).json()
    own_job = import_csv(client).json()
    client.post('/api/users', json={'username': 'member', 'password': 'MemberPassword123', 'role': 'member'})
    client.post('/api/auth/logout'); client.post('/api/auth/login', json={'username': 'member', 'password': 'MemberPassword123'})
    job = import_csv(client).json()
    candidate = job['candidates'][0]
    url = f"/api/ai/statements/{job['id']}/candidates/{candidate['id']}/import"
    assert client.post(url, json={'name': 'Netflix', 'amount': 16.99, 'target_expense_id': existing['id'], 'price_effective_from': '2026-02-05'}).status_code == 404
    assert client.post(f"/api/ai/statements/{own_job['id']}/rejected/fake/review", json={'date': '2026-01-01', 'merchant': 'Shop', 'amount': 1, 'currency': 'EUR', 'entry_type': 'expense', 'reviewed': True}).status_code == 404


def test_existing_contract_match_does_not_suggest_a_different_policy(client):
    client.post('/api/expenses', json={'name': 'Netflix policy A', 'provider': 'Netflix', 'amount': 10, 'contract_reference': 'policy-a'})
    matching = client.post('/api/expenses', json={'name': 'Netflix policy B', 'provider': 'Netflix', 'amount': 10, 'contract_reference': 'policy-b'}).json()
    content = 'Date;Merchant;Amount;Reference\n2026-01-01;Netflix;-10;policy-b\n2026-02-01;Netflix;-10;policy-b\n'
    job = import_csv(client, content).json()
    assert [x['id'] for x in job['candidates'][0]['existing_matches']] == [matching['id']]


def test_correcting_a_singleton_into_a_recurring_group_retains_import_guard(client):
    content = 'Date;Merchant;Amount;Currency\n2026-01-05;Netflix;-10,00;EUR\n2026-02-05;Netflix;-10,00;xyz\n'
    job = import_csv(client, content).json()
    single = job['single_candidates'][0]
    url = f"/api/ai/statements/{job['id']}/candidates/{single['id']}/import"
    saved = client.post(url, json={'name': 'Netflix', 'amount': 10, 'recurrence_type': 'one_time', 'start_date': '2026-01-05'})
    assert saved.status_code == 200
    row = job['rejected_rows'][0]
    reviewed = client.post(f"/api/ai/statements/{job['id']}/rejected/{row['id']}/review", json={**row['fields'], 'currency': 'EUR', 'reviewed': True})
    assert reviewed.status_code == 200
    result = reviewed.json()
    assert result['single_candidates'] == [] and result['candidates'][0]['count'] == 2
    assert result['candidates'][0]['imported_expense_id'] == saved.json()['id']
    assert client.post(url, json={'name': 'Netflix', 'amount': 10}).status_code == 409


def test_concurrent_existing_update_creates_one_price_period_and_import(client):
    from concurrent.futures import ThreadPoolExecutor
    existing = client.post('/api/expenses', json={'name': 'Netflix', 'amount': 10, 'start_date': '2025-01-01'}).json()
    job = import_csv(client).json()
    url = f"/api/ai/statements/{job['id']}/candidates/{job['candidates'][0]['id']}/import"
    data = {**existing, 'amount': 16.99, 'target_expense_id': existing['id'], 'price_effective_from': '2026-02-05'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: client.post(url, json=data).status_code, [0, 1]))
    assert sorted(results) == [200, 409]
    updated = client.get('/api/expenses').json()
    assert len(updated) == 1 and [p['amount'] for p in updated[0]['price_history']] == [10, 16.99]


def test_csv_rejects_ambiguous_debit_credit_and_preserves_no_raw_file(client):
    from app.db import DATA_DIR
    content = 'Date;Merchant;Debit;Credit\n2026-01-01;Shop;10,00;20,00\n'
    job = import_csv(client, content).json()
    assert job['transaction_count'] == 0 and job['rejection_reasons'] == {'schema_amount': 1}
    assert not list(DATA_DIR.rglob('*.csv'))


def test_image_correction_requires_explicit_original_review():
    row = model_rows()['transactions'][0]
    rejected = []
    parse_transactions(json.dumps({'transactions': [dict(row, currency='xyz')]}), [{'page': 1, 'image': 'data:image/jpeg;base64,YQ==', 'text': ''}], 'scan.png', {}, rejected)
    assert rejected[0]['vision']
    with pytest.raises(StatementError, match='Confirm'):
        correct_booking(rejected[0], dict(rejected[0]['fields'], currency='EUR'), False)
    value = correct_booking(rejected[0], dict(rejected[0]['fields'], currency='EUR'), True)
    assert value['vision'] and value['manually_reviewed']
