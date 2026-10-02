import copy
import io
import json
from datetime import date

import pytest
from PIL import Image
from app.statements import (StatementError, build_candidates, document_pages,
                            parse_transactions, detect_interval)
from app.ai import _anthropic_content


def pdf_bytes(lines):
    """Small valid text PDF fixture, generated without extra dependencies."""
    stream = 'BT /F1 11 Tf 40 790 Td 15 TL '
    for i, line in enumerate(lines):
        escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        stream += ('T* ' if i else '') + f'({escaped}) Tj '
    stream += 'ET'
    stream = stream.encode('latin-1')
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    output, offsets = b'%PDF-1.4\n', [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(output)); output += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(output)
    output += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    for offset in offsets[1:]: output += f'{offset:010} 00000 n \n'.encode()
    return output + f'trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()


def tx(day='2026-01-05', merchant='Netflix', amount=15.99, **kw):
    return dict(date=day, merchant=merchant, reference='', account_key='account-a',
        amount=amount, currency='EUR', entry_type='expense', page=1,
        evidence=f'{day} {merchant} {amount:.2f}', source='a.pdf', vision=False, **kw)


def test_regular_recurrence_and_duplicate_uploads():
    rows = [tx(f'2026-{m:02}-05') for m in range(1,5)]
    duplicate = [dict(x, source='copy.pdf') for x in rows]
    result = build_candidates(rows + duplicate)
    item = result['candidates'][0]
    assert item['count'] == 4 and item['interval_months'] == 1
    assert item['confidence'] == 'high'
    assert item['total_amount'] == 63.96
    assert result['duplicates_removed'] == 4


def test_same_day_real_duplicates_are_not_erased():
    rows = [tx(), tx(), tx('2026-02-05')]
    result = build_candidates(rows + [dict(x, source='copy') for x in rows])
    assert result['candidates'][0]['count'] == 3
    assert result['candidates'][0]['interval_months'] is None


def test_policies_accounts_currencies_and_directions_stay_separate():
    rows = []
    for key, value in [('reference','policy-a'),('reference','policy-b'),('account_key','account-b'),('currency','USD'),('entry_type','income')]:
        rows += [dict(tx(day, 'HUK24'), **{key:value}) for day in ['2026-01-05','2026-02-05']]
    assert len(build_candidates(rows)['candidates']) == 5


def test_variable_amounts_use_latest_not_sum_or_average():
    candidate = build_candidates([tx('2026-01-05',amount=10), tx('2026-02-05',amount=11), tx('2026-03-05',amount=20)])['candidates'][0]
    assert candidate['amount'] == 20 and candidate['variable_amount']
    assert candidate['min_amount'] == 10 and candidate['max_amount'] == 20
    assert candidate['confidence'] == 'medium'


@pytest.mark.parametrize('days,expected', [(['2026-01-31','2026-02-28','2026-03-31'],1),
    (['2025-01-05','2025-04-05','2025-07-05'],3), (['2025-01-05','2025-07-05'],6),
    (['2024-02-29','2025-02-28'],12), (['2026-01-05','2026-01-12'],None),
    (['2026-01-05','2026-03-05'],None)])
def test_intervals(days, expected):
    assert detect_interval([date.fromisoformat(d) for d in days]) == expected


def test_single_occurrences_have_no_recurring_candidate():
    result = build_candidates([tx()])
    assert result['single_occurrences'] == 1 and result['candidates'] == []


def test_text_pdf_and_scanned_pdf_and_image_processing():
    raw = pdf_bytes(['Statement period 2026 personal account information',
        '2026-01-05 Netflix 15.99 EUR debit', '2026-02-05 Netflix 15.99 EUR debit'])
    pages = document_pages('statement.pdf',raw)
    assert 'Netflix' in pages[0]['text'] and 'image' not in pages[0]
    scan = document_pages('scan.pdf',pdf_bytes(['Scanned statement']))
    assert scan[0]['image'].startswith('data:image/jpeg;base64,')
    image = Image.new('RGBA', (200,300),(255,255,255,0))
    buf = io.BytesIO(); image.save(buf,format='PNG')
    assert document_pages('test.png',buf.getvalue())[0]['image'].startswith('data:image/jpeg;base64,')


def test_invalid_document_and_fake_extensions():
    for name,raw in [('fake.pdf',b'not pdf'),('fake.png',b'%PDF-1.4'),('x.txt',b'hi')]:
        with pytest.raises(StatementError): document_pages(name,raw)
    with pytest.raises(StatementError): document_pages('broken.pdf',b'%PDF-1.4 broken')


def test_json_requires_valid_fields_and_verifiable_pdf_evidence():
    row = {k:v for k,v in tx().items() if k not in {'source','vision'}}
    pages = [{'page':1,'text':row['evidence']}]
    valid,skipped = parse_transactions('```json\n'+json.dumps({'transactions':[row]})+'\n```',pages,'source.pdf')
    assert len(valid) == 1 and skipped == 0
    assert valid[0]['account_key'] != row['account_key']
    for change in [{'amount':-1},{'page':2},{'date':'tomorrow'},{'evidence':'invented'},{'currency':'xyz'},{'merchant':'   '}]:
        valid,skipped = parse_transactions(json.dumps({'transactions':[dict(row,**change)]}),pages,'x')
        assert valid == [] and skipped == 1
    with pytest.raises(StatementError): parse_transactions('{"transactions":[',pages,'x')


def test_anthropic_image_adapter():
    result = _anthropic_content([{'type':'text','text':'page'}, {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,YQ=='}}])
    assert result[1] == {'type':'image','source':{'type':'base64','media_type':'image/jpeg','data':'YQ=='}}


@pytest.mark.parametrize('finish,content', [('length','{"transactions": []}'),('stop',None),('content_filter','')])
def test_incomplete_or_empty_provider_output_is_not_silently_accepted(monkeypatch,finish,content):
    import asyncio
    import httpx
    from app import ai
    original=httpx.AsyncClient
    def handler(request):
        return httpx.Response(200,json={'choices':[{'finish_reason':finish,'message':{'content':content}}]})
    monkeypatch.setattr(ai.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),trust_env=False,**kwargs))
    with pytest.raises(RuntimeError):
        asyncio.run(ai._call_model('custom','https://model.test/v1','','model','system',[{'role':'user','content':'test'}],require_complete=True))
