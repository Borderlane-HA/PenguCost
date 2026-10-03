"""Dated contract terms and calendar accruals; prices keep their own timeline."""
from __future__ import annotations
import calendar
import json
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from .models import ContractVersion, User

DATE_FIELDS = {'start_date', 'next_due_date', 'contract_end', 'cancellation_date', 'cancelled_on'}
CONTRACT_FIELDS = ('name', 'provider', 'provider_website', 'entry_type', 'currency', 'billing_interval', 'interval_months',
    'minimum_term_months', 'renewal_period_months', 'renewal_amount', 'category_id', 'account_id', 'start_date',
    'next_due_date', 'contract_end', 'cancellation_date', 'cancellation_notice_days', 'cancelled_on', 'auto_renew',
    'status', 'essential', 'recurrence_type', 'amount_estimated', 'contract_url', 'contract_reference', 'tags', 'notes', 'contract_holder')


def add_months(value: date, months: int) -> date:
    index = value.month - 1 + months
    year, month = value.year + index // 12, index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def snapshot(x, db=None, fields: dict | None = None, assumed=False) -> dict:
    value = {key: getattr(x, key, None) for key in CONTRACT_FIELDS}
    if fields:
        value.update({key: fields[key] for key in CONTRACT_FIELDS if key in fields})
    for key in DATE_FIELDS:
        if isinstance(value.get(key), date):
            value[key] = value[key].isoformat()
    if db:
        from .models import Account, Category
        account = db.get(Account, value['account_id']) if value['account_id'] else None
        category = db.get(Category, value['category_id']) if value['category_id'] else None
        owner = db.get(User, x.created_by) if x.created_by else None
    else:
        account, category, owner = x.account, x.category, None
    value.update(account=account.name if account else None, category=category.name if category else None,
                 category_color=category.color if category else '#7B8798',
                 account_scope=('global' if getattr(account,'created_by',None) is None else 'private') if account else None,
                 category_scope=('global' if getattr(category,'created_by',None) is None else 'private') if category else None, owner_name=(owner.display_name or owner.username) if owner else '',
                 history_assumed=assumed)
    return value


def ensure_history(db, x, assumed=False):
    if x.versions:
        return
    known = [p.valid_from for p in x.prices]
    if x.start_date:
        known.append(x.start_date)
    first = min(known) if known else (x.created_at.date() if x.created_at else date.today())
    if x.history_from:
        first = max(first, x.history_from)
    x.versions.append(ContractVersion(effective_from=first, snapshot_json=json.dumps(snapshot(x, db, assumed=assumed), ensure_ascii=False)))


def write_version(db, x, fields: dict, effective: date):
    ensure_history(db, x, assumed=True)
    value = snapshot(state_at(x, effective), db, fields)
    existing = next((v for v in x.versions if v.effective_from == effective), None)
    if existing:
        existing.snapshot_json = json.dumps(value, ensure_ascii=False)
    else:
        x.versions.append(ContractVersion(effective_from=effective, snapshot_json=json.dumps(value, ensure_ascii=False)))


def version_data(version) -> dict:
    if getattr(version, '_cache_source', None) != version.snapshot_json:
        value = json.loads(version.snapshot_json)
        for key in DATE_FIELDS:
            if value.get(key):
                value[key] = date.fromisoformat(value[key])
        version._cache_source, version._cache_value = version.snapshot_json, value
    return version._cache_value


def state_at(x, when: date):
    if getattr(x, '_state_date', None) == when:
        return x
    x = getattr(x, '_source', x)
    versions = sorted(x.versions, key=lambda v: v.effective_from)
    applicable = [v for v in versions if v.effective_from <= when]
    chosen = applicable[-1] if applicable else (versions[0] if versions else None)
    values = dict(version_data(chosen)) if chosen else snapshot(x)
    # Synthetic catalog objects are immutable dated names, not live catalog labels.
    values['category'] = SimpleNamespace(name=values['category'], color=values.get('category_color', '#7B8798')) if values.get('category') else None
    values['account'] = SimpleNamespace(name=values['account']) if values.get('account') else None
    return SimpleNamespace(**values, id=x.id, amount=x.amount, created_by=x.created_by, created_at=x.created_at,
        prices=x.prices, versions=x.versions, is_archived=bool(x.is_archived), archived_on=x.archived_on,
        history_from=x.history_from, _source=x, _state_date=when,
        _known_from=max(x.history_from or date.min, versions[0].effective_from if versions else date.min))


def end_at(x, when: date):
    x = state_at(x, when)
    end = x.contract_end
    if not end or not x.auto_renew or not x.renewal_period_months or x.cancelled_on or x.status in {'cancelled', 'ended'}:
        return end
    # Renewals are computed from the original boundary to avoid month-end drift.
    count = 0
    while end < when and count < 1200:
        count += 1
        end = add_months(x.contract_end, count * x.renewal_period_months)
    return end


def amount_at(x, when: date) -> float:
    x = state_at(x, when)
    prices = sorted(x.prices, key=lambda p: p.valid_from)
    applicable = [p for p in prices if p.valid_from <= when]
    selected = applicable[-1] if applicable else (prices[0] if prices else None)
    value = selected.amount if selected else x.amount
    if (x.auto_renew and not x.cancelled_on and x.status == 'active' and x.contract_end and when > x.contract_end
            and x.renewal_period_months and x.renewal_amount and (not selected or selected.valid_from <= x.contract_end)):
        value = x.renewal_amount
    return value


def active_at(x, when: date, historical=False) -> bool:
    x = state_at(x, when)
    if x.history_from and when < x.history_from or when < x._known_from:
        return False
    if x.is_archived and (not historical or not x.archived_on or when > x.archived_on):
        return False
    if x.status in {'paused', 'ended'} or (x.start_date and when < x.start_date):
        return False
    if x.recurrence_type == 'one_time':
        return when == (x.next_due_date or x.start_date)
    end = end_at(x, when)
    return end is None or when <= end


def daily_cost(x, when: date) -> Decimal:
    state = state_at(x, when)
    if not active_at(state, when, historical=True):
        return Decimal(0)
    amount = Decimal(str(amount_at(state, when)))
    if state.recurrence_type == 'one_time':
        return amount
    months = max(1, state.interval_months or 1)
    return amount / Decimal(months) / Decimal(calendar.monthrange(when.year, when.month)[1])


def period_total(x, start: date, end: date) -> Decimal:
    total = Decimal(0)
    day = start
    while day <= end:
        total += daily_cost(x, day)
        day += timedelta(days=1)
    return total


def period_cost(x, start: date, end: date) -> float:
    return float(period_total(x,start,end).quantize(Decimal('0.01')))


def timeline(x) -> list[dict]:
    versions = sorted(x.versions, key=lambda v: v.effective_from)
    result = []
    for i, version in enumerate(versions):
        values = json.loads(version.snapshot_json)
        result.append({'id': version.id, 'effective_from': version.effective_from.isoformat(),
                       'effective_to': (versions[i+1].effective_from - timedelta(days=1)).isoformat() if i+1 < len(versions) else None,
                       'values': values})
    return result


def calendar_segments(x, start: date, end: date) -> list[dict]:
    points = {start, end + timedelta(days=1)}
    points.update(v.effective_from for v in x.versions if start < v.effective_from <= end)
    points.update(p.valid_from for p in x.prices if start < p.valid_from <= end)
    # Split a bar when renewal price/end state changes; no daily bar explosion.
    for version in x.versions:
        data = version_data(version)
        raw_end = data.get('contract_end')
        if raw_end and start < raw_end + timedelta(days=1) <= end:
            points.add(raw_end + timedelta(days=1))
    ordered, result = sorted(points), []
    today = date.today()
    for i in range(len(ordered)-1):
        left, right = ordered[i], ordered[i+1] - timedelta(days=1)
        state = state_at(x, left)
        first = max(left, state.start_date or left, state._known_from)
        last = min(right, x.archived_on or right) if x.is_archived else right
        if state.history_from:
            first = max(first, state.history_from)
        if state.recurrence_type == 'one_time':
            due = state.next_due_date or state.start_date
            if not due or not first <= due <= last:
                continue
            first = last = due
        elif state.contract_end:
            if not state.auto_renew or not state.renewal_period_months or state.cancelled_on or state.status in {'cancelled', 'ended'}:
                last = min(last, state.contract_end)
        if first > last or state.status in {'paused', 'ended'}:
            continue
        data = next((v for v in reversed(sorted(x.versions, key=lambda v:v.effective_from)) if v.effective_from <= first), None)
        values = json.loads(data.snapshot_json) if data else snapshot(x)
        amount = amount_at(x, first)
        months = max(1, state.interval_months or 1)
        total=period_total(x,first,last)
        result.append({'id': f'{x.id}:{first.isoformat()}', 'expense_id': x.id, 'version_id': data.id if data else None,
            'from': first.isoformat(), 'to': last.isoformat(), 'name': state.name, 'provider': state.provider,
            'entry_type': state.entry_type, 'currency': state.currency, 'contract_holder': state.contract_holder or '',
            'account': values.get('account'), 'category': values.get('category'), 'category_color': values.get('category_color'),
            'owner_name': values.get('owner_name'), 'history_assumed': values.get('history_assumed', False),
            'amount': amount, 'monthly': amount / months if state.recurrence_type != 'one_time' else amount,
            'yearly': amount * 12 / months if state.recurrence_type != 'one_time' else amount,
            'period_cost': float(total.quantize(Decimal('0.01'))), 'period_cost_unrounded': float(total), 'has_term': bool(state.contract_end),
            'archived': bool(x.is_archived), 'historical': bool(right < today or (data and any(v.effective_from > data.effective_from and v.effective_from <= today for v in x.versions))),
            'planned': first > today, 'values': values})
    return result


def archive_record(db,x,when=None):
    when = when or date.today()
    if x.is_archived:
        return
    ensure_history(db,x,assumed=True)
    x.is_archived=True
    x.archived_on=when


def restore_record(db,x,when=None):
    when=when or date.today()
    if not x.is_archived:
        return
    boundary=x.archived_on
    ordered=sorted(x.versions,key=lambda v:v.effective_from)
    chosen=next((v for v in reversed(ordered) if v.effective_from<=when),ordered[0])
    current=dict(version_data(chosen))
    # Materialize the archival gap only when restoring; archive itself preserves
    # all submitted future plans while the archive boundary suppresses accruals.
    if boundary and boundary+timedelta(days=1)<when:
        for v in x.versions:
            if boundary<v.effective_from<when:
                values=json.loads(v.snapshot_json);values['status']='paused';v.snapshot_json=json.dumps(values,ensure_ascii=False)
        write_version(db,x,{'status':'paused'},boundary+timedelta(days=1))
    write_version(db,x,current,when)
    x.is_archived=False
    x.archived_on=None


def sync_latest(x):
    """Keep storage columns consistent with the latest retained dated version."""
    if x.versions:
        latest=max(x.versions,key=lambda v:v.effective_from)
        for key,value in version_data(latest).items():
            if key in CONTRACT_FIELDS:
                setattr(x,key,value)
