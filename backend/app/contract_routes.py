"""Owned contract calendar, archival and privacy controls."""
import json
from datetime import date, timedelta
from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from .models import Expense, ExpensePrice, ExpenseChange, StatementImport, ReminderAction
from . import contracts

class HistoryCut(BaseModel):
    before: date


def register_contract_routes(app, current_user, get_db, owned, serialize):
    @app.get('/api/contracts/calendar')
    def calendar(start: date, end: date, user=Depends(current_user), db=Depends(get_db)):
        if start > end or (end-start).days > 366 or start.year < 1900 or end.year > 2200:
            raise HTTPException(400, 'Select a period of at most 367 days between 1900 and 2200.')
        rows = list(db.scalars(select(Expense).where(Expense.created_by == user.id).order_by(Expense.name)))
        return {'start':start, 'end':end, 'segments':[segment for x in rows for segment in contracts.calendar_segments(x,start,end)]}

    @app.post('/api/expenses/{item_id}/archive')
    def archive(item_id: int, user=Depends(current_user), db=Depends(get_db)):
        x = owned(db,user,item_id)
        contracts.archive_record(db,x)
        db.commit()
        return serialize(x)

    @app.post('/api/expenses/{item_id}/restore')
    def restore(item_id: int, user=Depends(current_user), db=Depends(get_db)):
        x = owned(db,user,item_id)
        contracts.restore_record(db,x)
        db.commit()
        return serialize(x)

    @app.post('/api/expenses/{item_id}/history/purge')
    def purge(item_id: int, data: HistoryCut, user=Depends(current_user), db=Depends(get_db)):
        x = owned(db,user,item_id)
        if data.before > date.today() or (x.history_from and data.before <= x.history_from):
            raise HTTPException(400, 'Choose a later history boundary no later than today.')
        contracts.ensure_history(db,x,assumed=True)
        state = contracts.state_at(x,data.before)
        value = dict(next((p['values'] for p in reversed(contracts.timeline(x)) if p['effective_from'] <= data.before.isoformat()), contracts.snapshot(state,db)))
        amount = contracts.amount_at(x,data.before)
        for v in list(x.versions):
            if v.effective_from < data.before:
                x.versions.remove(v)
        if not any(v.effective_from == data.before for v in x.versions):
            from .models import ContractVersion
            x.versions.append(ContractVersion(effective_from=data.before,snapshot_json=json.dumps(value,ensure_ascii=False)))
        for p in list(x.prices):
            if p.valid_from < data.before:
                x.prices.remove(p)
        if not any(p.valid_from == data.before for p in x.prices):
            x.prices.append(ExpensePrice(amount=amount,valid_from=data.before))
        contracts.sync_latest(x)
        x.history_from = data.before
        # Audit records and statement links can still contain old names/amounts.
        db.execute(delete(ExpenseChange).where(ExpenseChange.expense_id==x.id))
        db.execute(delete(StatementImport).where(StatementImport.expense_id==x.id))
        db.execute(delete(ReminderAction).where(ReminderAction.expense_id==x.id))
        db.commit()
        return serialize(x)

    @app.delete('/api/expenses/{item_id}/versions/{version_id}')
    def remove_plan(item_id:int,version_id:int,user=Depends(current_user),db=Depends(get_db)):
        x = owned(db,user,item_id)
        v = next((v for v in x.versions if v.id==version_id),None)
        if not v:
            raise HTTPException(404,'Not found')
        if v.effective_from <= date.today() or len(x.versions)<2:
            raise HTTPException(400,'Only future contract versions can be removed.')
        x.versions.remove(v); contracts.sync_latest(x); db.commit()
        return serialize(x)

    @app.delete('/api/expenses/{item_id}/prices/{price_id}')
    def remove_price(item_id:int,price_id:int,user=Depends(current_user),db=Depends(get_db)):
        x=owned(db,user,item_id)
        p=next((p for p in x.prices if p.id==price_id),None)
        if not p:
            raise HTTPException(404,'Not found')
        if p.valid_from<=date.today() or len(x.prices)<2:
            raise HTTPException(400,'Only future prices can be removed.')
        x.prices.remove(p);db.commit()
        return serialize(x)
