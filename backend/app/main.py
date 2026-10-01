from __future__ import annotations
from datetime import date, datetime, timedelta
import calendar
from pathlib import Path
from typing import Optional, Literal

from fastapi import FastAPI, Depends, HTTPException, Response, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, func, inspect, text
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import User, Expense, ExpensePrice, Account, Category, Setting, ReminderAction
from .security import hash_password, verify_password, make_session, session_user_id, encrypt_secret, decrypt_secret
from .ai import analyze_costs

app = FastAPI(title='PenguCost', version='0.1.5')
Base.metadata.create_all(engine)

def migrate_schema():
    # create_all does not add columns to an existing SQLite table. Keep upgrades in-place.
    columns={c['name'] for c in inspect(engine).get_columns('expenses')}
    statements=[]
    if 'minimum_term_months' not in columns: statements.append('ALTER TABLE expenses ADD COLUMN minimum_term_months INTEGER')
    if 'renewal_period_months' not in columns: statements.append('ALTER TABLE expenses ADD COLUMN renewal_period_months INTEGER')
    if 'cancelled_on' not in columns: statements.append('ALTER TABLE expenses ADD COLUMN cancelled_on DATE')
    if statements:
        with engine.begin() as conn:
            for statement in statements: conn.execute(text(statement))
    category_columns={c['name'] for c in inspect(engine).get_columns('categories')}
    if 'color' not in category_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE categories ADD COLUMN color VARCHAR(16) DEFAULT '#5B5CF0'"))

migrate_schema()

DEFAULT_CATEGORIES = [
    ('Abos','sparkles','#7C6CF2'),('Versicherungen','shield','#4A78D0'),('Energie','zap','#E3A124'),('Wohnen','house','#CE6B4D'),
    ('Mobilität','car','#2E9B84'),('Telekommunikation','wifi','#4B91C8'),('Finanzen','landmark','#8C67B8'),('Gesundheit','heart','#D45B78'),('Sonstiges','wallet','#7B8798')
]

def seed(db: Session):
    if not db.scalar(select(func.count(Category.id))):
        db.add_all([Category(name=n, icon=i, color=c) for n, i, c in DEFAULT_CATEGORIES])
        db.commit()

class LoginIn(BaseModel): username: str; password: str
class BootstrapIn(BaseModel): username: str = Field(min_length=3); display_name: str='Administrator'; password: str = Field(min_length=8)
class UserIn(BaseModel): username: str; display_name: str=''; password: str = Field(min_length=8); role: str='member'
class UserPatch(BaseModel): display_name: Optional[str]=None; password: Optional[str]=None; role: Optional[str]=None; is_active: Optional[bool]=None
class AccountIn(BaseModel): name: str; kind: str='bank'; note: str=''
class CategoryIn(BaseModel): name: str; icon: str='wallet'; color: str='#5B5CF0'
class CategoryPatch(BaseModel): name: Optional[str]=None; icon: Optional[str]=None; color: Optional[str]=None
class ExpenseIn(BaseModel):
    name: str; provider: str=''; amount: float = Field(gt=0); currency: str='EUR'
    billing_interval: str='monthly'; interval_months: int=1; category_id: Optional[int]=None; account_id: Optional[int]=None
    start_date: Optional[date]=None; next_due_date: Optional[date]=None; contract_end: Optional[date]=None; cancellation_date: Optional[date]=None
    minimum_term_months: Optional[int]=Field(default=None, ge=1); renewal_period_months: Optional[int]=Field(default=None, ge=1)
    cancellation_notice_days: Optional[int]=None; auto_renew: bool=False; status: str='active'; essential: bool=False; tags: str=''; notes: str=''
    price_effective_from: Optional[date]=None
class AISettingsIn(BaseModel): base_url: str=''; api_key: str=''; model: str=''; enabled: bool=False
class ReminderSettingsIn(BaseModel): cancellation_reminder_days: int = Field(default=30, ge=0, le=3650)
class ReminderActionIn(BaseModel):
    action: Literal['done','cancelled','snooze']
    event_key: str = Field(min_length=1, max_length=160)
    snooze_days: Optional[int] = Field(default=None, ge=1, le=365)
class AIAnalyzeIn(BaseModel): goal: str='Reduce monthly recurring costs'; expense_ids: list[int]=[]; language: str='de'

def current_user(uid: int = Depends(session_user_id), db: Session = Depends(get_db)):
    user = db.get(User, uid)
    if not user or not user.is_active: raise HTTPException(401, 'Not authenticated')
    return user

def require_admin(user: User = Depends(current_user)):
    if user.role != 'admin': raise HTTPException(403, 'Admin only')
    return user

def add_months(value: date, months: int) -> date:
    idx=value.month-1+months
    year=value.year+idx//12
    month=idx%12+1
    day=min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

def price_at(x: Expense, when: date) -> float:
    prices=sorted(x.prices, key=lambda p:p.valid_from)
    applicable=[p for p in prices if p.valid_from <= when]
    if applicable: return applicable[-1].amount
    if prices: return prices[0].amount
    return x.amount

def effective_contract_end(x: Expense, today: date) -> date | None:
    end=x.contract_end
    if not end or not x.auto_renew or not x.renewal_period_months: return end
    guard=0
    while end < today and guard < 600:
        end=add_months(end, x.renewal_period_months)
        guard+=1
    return end

def is_effectively_active(x: Expense, when: date | None=None) -> bool:
    when=when or date.today()
    if x.status != 'active': return False
    end=effective_contract_end(x,when)
    return not end or end >= when

def expense_dict(x: Expense, as_of: date | None=None):
    today=as_of or date.today()
    current_amount=price_at(x, today)
    months=x.interval_months or {'monthly':1,'quarterly':3,'halfyearly':6,'yearly':12}.get(x.billing_interval,1)
    monthly=round(current_amount / months, 2)
    yearly=round(monthly * 12, 2)
    prices=sorted(x.prices, key=lambda p:p.valid_from)
    price_history=[]
    for i,p in enumerate(prices):
        valid_to=(prices[i+1].valid_from-timedelta(days=1)) if i+1 < len(prices) else None
        price_history.append({'id':p.id,'amount':p.amount,'valid_from':p.valid_from,'valid_to':valid_to})
    upcoming_price=next((p for p in prices if p.valid_from > today), None)
    next_end=effective_contract_end(x,today)
    next_cancel=x.cancellation_date
    if next_end and x.cancellation_notice_days is not None and (not next_cancel or next_cancel < today or next_end != x.contract_end):
        next_cancel=next_end-timedelta(days=max(0,x.cancellation_notice_days))
    return {
        'id':x.id,'name':x.name,'provider':x.provider,'amount':current_amount,'currency':x.currency,'billing_interval':x.billing_interval,
        'interval_months':months,'monthly_equivalent':monthly,'yearly_equivalent':yearly,'category_id':x.category_id,'category':x.category.name if x.category else None,'category_color':x.category.color if x.category else '#7B8798',
        'account_id':x.account_id,'account':x.account.name if x.account else None,'start_date':x.start_date,'next_due_date':x.next_due_date,
        'contract_end':x.contract_end,'effective_contract_end':next_end,'cancellation_date':x.cancellation_date,'effective_cancellation_date':next_cancel,
        'minimum_term_months':x.minimum_term_months,'renewal_period_months':x.renewal_period_months,
        'cancellation_notice_days':x.cancellation_notice_days,'cancelled_on':x.cancelled_on,'auto_renew':x.auto_renew,'status':x.status,'essential':x.essential,'tags':x.tags,'notes':x.notes,
        'price_history':price_history,
        'next_price_change':({'amount':upcoming_price.amount,'valid_from':upcoming_price.valid_from} if upcoming_price else None)
    }

@app.on_event('startup')
def startup():
    db = next(get_db()); seed(db)
    # Upgrade 0.1.0 data: seed a first immutable price phase for every existing expense.
    changed=False
    for item in db.scalars(select(Expense)):
        if not item.prices:
            db.add(ExpensePrice(expense_id=item.id, amount=item.amount, valid_from=item.start_date or (item.created_at.date() if item.created_at else date.today())))
            changed=True
    if changed: db.commit()
    # One-time 0.1.2 color migration: give built-in categories distinct colors,
    # while never overwriting later user customizations.
    if not db.get(Setting,'migration.category_colors_012'):
        palette={name:color for name,_icon,color in DEFAULT_CATEGORIES}
        for category in db.scalars(select(Category)):
            if category.name in palette and (not category.color or category.color.upper() == '#5B5CF0'):
                category.color=palette[category.name]
        db.add(Setting(key='migration.category_colors_012',value='done'))
        db.commit()
    db.close()

@app.get('/api/health')
def health(): return {'status':'ok','service':'PenguCost','version':'0.1.5'}

@app.get('/api/auth/status')
def auth_status(db: Session=Depends(get_db)):
    return {'needs_bootstrap': (db.scalar(select(func.count(User.id))) or 0) == 0}

@app.post('/api/auth/bootstrap')
def bootstrap(data: BootstrapIn, response: Response, db: Session=Depends(get_db)):
    if (db.scalar(select(func.count(User.id))) or 0) > 0: raise HTTPException(409, 'Already initialized')
    user = User(username=data.username.strip().lower(), display_name=data.display_name, password_hash=hash_password(data.password), role='admin')
    db.add(user); db.commit(); db.refresh(user)
    response.set_cookie('pengucost_session', make_session(user.id), httponly=True, samesite='lax', secure=False, max_age=2592000)
    return {'id':user.id,'username':user.username,'display_name':user.display_name,'role':user.role}

@app.post('/api/auth/login')
def login(data: LoginIn, response: Response, db: Session=Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username.strip().lower()))
    if not user or not user.is_active or not verify_password(data.password, user.password_hash): raise HTTPException(401, 'Invalid credentials')
    response.set_cookie('pengucost_session', make_session(user.id), httponly=True, samesite='lax', secure=False, max_age=2592000)
    return {'id':user.id,'username':user.username,'display_name':user.display_name,'role':user.role}

@app.post('/api/auth/logout')
def logout(response: Response):
    response.delete_cookie('pengucost_session'); return {'ok':True}

@app.get('/api/me')
def me(user: User=Depends(current_user)): return {'id':user.id,'username':user.username,'display_name':user.display_name,'role':user.role}

@app.get('/api/users')
def users(_: User=Depends(require_admin), db: Session=Depends(get_db)):
    return [{'id':u.id,'username':u.username,'display_name':u.display_name,'role':u.role,'is_active':u.is_active} for u in db.scalars(select(User).order_by(User.username))]
@app.post('/api/users')
def create_user(data: UserIn, _: User=Depends(require_admin), db: Session=Depends(get_db)):
    u=User(username=data.username.lower().strip(),display_name=data.display_name,password_hash=hash_password(data.password),role=data.role); db.add(u)
    try: db.commit(); db.refresh(u)
    except Exception: db.rollback(); raise HTTPException(409,'Username already exists')
    return {'id':u.id}
@app.patch('/api/users/{user_id}')
def patch_user(user_id:int,data:UserPatch,admin:User=Depends(require_admin),db:Session=Depends(get_db)):
    u=db.get(User,user_id)
    if not u: raise HTTPException(404,'User not found')
    if data.display_name is not None: u.display_name=data.display_name
    if data.password: u.password_hash=hash_password(data.password)
    if data.role is not None: u.role=data.role
    if data.is_active is not None:
        if u.id == admin.id and not data.is_active: raise HTTPException(400,'Cannot disable current admin')
        u.is_active=data.is_active
    db.commit(); return {'ok':True}

@app.get('/api/accounts')
def get_accounts(_:User=Depends(current_user),db:Session=Depends(get_db)): return [{'id':x.id,'name':x.name,'kind':x.kind,'note':x.note} for x in db.scalars(select(Account).order_by(Account.name))]
@app.post('/api/accounts')
def add_account(data:AccountIn,_:User=Depends(current_user),db:Session=Depends(get_db)):
    x=Account(**data.model_dump());db.add(x);db.commit();db.refresh(x);return {'id':x.id}
@app.delete('/api/accounts/{item_id}')
def delete_account(item_id:int,_:User=Depends(current_user),db:Session=Depends(get_db)):
    x=db.get(Account,item_id)
    if not x: raise HTTPException(404,'Not found')
    db.delete(x);db.commit();return {'ok':True}

@app.get('/api/categories')
def get_categories(_:User=Depends(current_user),db:Session=Depends(get_db)): return [{'id':x.id,'name':x.name,'icon':x.icon,'color':x.color or '#5B5CF0'} for x in db.scalars(select(Category).order_by(Category.name))]
@app.post('/api/categories')
def add_category(data:CategoryIn,_:User=Depends(current_user),db:Session=Depends(get_db)):
    x=Category(**data.model_dump());db.add(x);db.commit();db.refresh(x);return {'id':x.id}
@app.patch('/api/categories/{item_id}')
def patch_category(item_id:int,data:CategoryPatch,_:User=Depends(current_user),db:Session=Depends(get_db)):
    x=db.get(Category,item_id)
    if not x: raise HTTPException(404,'Not found')
    if data.name is not None: x.name=data.name.strip()
    if data.icon is not None: x.icon=data.icon
    if data.color is not None:
        color=data.color.strip()
        if not (len(color)==7 and color.startswith('#') and all(c in '0123456789abcdefABCDEF' for c in color[1:])):
            raise HTTPException(400,'Color must be a hex value like #5B5CF0')
        x.color=color.upper()
    db.commit();return {'ok':True}

@app.get('/api/expenses')
def get_expenses(_:User=Depends(current_user),db:Session=Depends(get_db)):
    return [expense_dict(x) for x in db.scalars(select(Expense).order_by(Expense.name))]
def normalized_expense_data(data: ExpenseIn):
    payload=data.model_dump(exclude={'price_effective_from'})
    if not payload.get('contract_end') and payload.get('start_date') and payload.get('minimum_term_months'):
        payload['contract_end']=add_months(payload['start_date'],payload['minimum_term_months'])-timedelta(days=1)
    if not payload.get('cancellation_date') and payload.get('contract_end') and payload.get('cancellation_notice_days') is not None:
        payload['cancellation_date']=payload['contract_end']-timedelta(days=max(0,payload['cancellation_notice_days']))
    return payload

def upsert_price(db: Session, x: Expense, amount: float, effective_from: date):
    existing=next((p for p in x.prices if p.valid_from == effective_from),None)
    if existing:
        existing.amount=amount
    else:
        x.prices.append(ExpensePrice(expense_id=x.id,amount=amount,valid_from=effective_from))

@app.post('/api/expenses')
def add_expense(data:ExpenseIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    payload=normalized_expense_data(data)
    initial_amount=payload['amount']
    x=Expense(**payload,created_by=user.id);db.add(x);db.flush()
    db.add(ExpensePrice(expense_id=x.id,amount=initial_amount,valid_from=data.price_effective_from or data.start_date or date.today()))
    db.commit();db.refresh(x);return expense_dict(x)
@app.put('/api/expenses/{item_id}')
def update_expense(item_id:int,data:ExpenseIn,_:User=Depends(current_user),db:Session=Depends(get_db)):
    x=db.get(Expense,item_id)
    if not x: raise HTTPException(404,'Not found')
    old_contract_end=x.contract_end
    old_cancellation_date=x.cancellation_date
    payload=normalized_expense_data(data)
    # If the UI carries forward an auto-derived old cancellation date while the
    # contract end changes, derive the new deadline instead of keeping it stale.
    if (payload.get('contract_end') != old_contract_end and data.cancellation_date == old_cancellation_date
        and payload.get('contract_end') and payload.get('cancellation_notice_days') is not None):
        payload['cancellation_date']=payload['contract_end']-timedelta(days=max(0,payload['cancellation_notice_days']))
    requested_amount=payload.pop('amount')
    effective=data.price_effective_from or date.today()
    if round(price_at(x,effective),2) != round(requested_amount,2):
        upsert_price(db,x,requested_amount,effective)
    for k,v in payload.items(): setattr(x,k,v)
    if x.auto_renew and x.cancelled_on is not None:
        x.cancelled_on=None
    # Keep the legacy amount column aligned with the amount effective today.
    x.amount=price_at(x,date.today())
    db.commit();db.refresh(x);return expense_dict(x)

@app.delete('/api/expenses/{item_id}')
def delete_expense(item_id:int,_:User=Depends(current_user),db:Session=Depends(get_db)):
    x=db.get(Expense,item_id)
    if not x: raise HTTPException(404,'Not found')
    db.delete(x);db.commit();return {'ok':True}

@app.get('/api/dashboard')
def dashboard(ids: str = Query(default=''), _:User=Depends(current_user), db:Session=Depends(get_db)):
    items=[x for x in db.scalars(select(Expense).where(Expense.status=='active')) if is_effectively_active(x)]
    if ids:
        selected={int(x) for x in ids.split(',') if x.isdigit()}; items=[x for x in items if x.id in selected]
    rows=[expense_dict(x) for x in items]
    monthly=round(sum(x['monthly_equivalent'] for x in rows),2); yearly=round(sum(x['yearly_equivalent'] for x in rows),2)
    categories={}
    category_colors={}
    for x in rows:
        key=x['category'] or 'Uncategorized'
        categories[key]=round(categories.get(key,0)+x['monthly_equivalent'],2)
        category_colors[key]=x.get('category_color') or '#7B8798'
    today=date.today(); soon=today+timedelta(days=60)
    expiring=[x for x in rows if x['effective_contract_end'] and today <= x['effective_contract_end'] <= soon]
    cancellation=[x for x in rows if x['effective_cancellation_date'] and today <= x['effective_cancellation_date'] <= soon]
    upcoming=[x for x in rows if x['next_due_date'] and today <= x['next_due_date'] <= today+timedelta(days=31)]
    return {'monthly_total':monthly,'yearly_total':yearly,'count':len(rows),'categories':categories,'category_colors':category_colors,'expiring':expiring,'cancellation_due':cancellation,'upcoming_payments':upcoming}

def setting_value(db: Session, key: str, default: str='') -> str:
    row=db.get(Setting,key)
    return row.value if row else default

def set_setting_value(db: Session, key: str, value: str):
    row=db.get(Setting,key)
    if row: row.value=value
    else: db.add(Setting(key=key,value=value))

@app.get('/api/settings/reminders')
def reminder_settings(_:User=Depends(current_user),db:Session=Depends(get_db)):
    return {'cancellation_reminder_days':int(setting_value(db,'reminders.cancellation_days','30'))}

@app.put('/api/settings/reminders')
def save_reminder_settings(data:ReminderSettingsIn,_:User=Depends(current_user),db:Session=Depends(get_db)):
    set_setting_value(db,'reminders.cancellation_days',str(data.cancellation_reminder_days))
    db.commit();return {'ok':True}

def reminder_event(x: Expense, today: date, days: int):
    until=today+timedelta(days=days)
    row=expense_dict(x,today)
    end=row['effective_contract_end']
    deadline=row['effective_cancellation_date']
    renewed=bool(x.auto_renew and x.contract_end and x.contract_end < today and end and end > x.contract_end)
    due=bool(deadline and today <= deadline <= until)
    extension_risk=bool(due and x.auto_renew)
    if not (due or renewed):
        return None
    if renewed:
        kind='auto_renewed'; label='Automatisch verlängert'
    elif extension_risk:
        kind='renewal_risk'; label='Verlängerung droht'
    else:
        kind='cancellation_due'; label='Kündigungsfrist läuft'
    remaining=(deadline-today).days if deadline else None
    event_key=f"{kind}:{deadline.isoformat() if deadline else '-'}:{end.isoformat() if end else '-'}"
    return {
        'expense_id':x.id,'name':x.name,'provider':x.provider,'kind':kind,'label':label,'event_key':event_key,
        'cancellation_date':deadline,'contract_end':end,'days_remaining':remaining,'cancelled_on':x.cancelled_on,
        'auto_renew':x.auto_renew,'renewal_period_months':x.renewal_period_months,
        'category':x.category.name if x.category else None,'category_color':x.category.color if x.category else '#7B8798'
    }

def reminder_action_for(db: Session, expense_id: int, event_key: str):
    return db.scalar(select(ReminderAction).where(ReminderAction.expense_id==expense_id, ReminderAction.event_key==event_key).order_by(ReminderAction.id.desc()))

def save_reminder_action(db: Session, expense_id: int, event_key: str, action: str, user_id: int, snooze_until: date | None=None):
    row=reminder_action_for(db,expense_id,event_key)
    if row:
        row.action=action;row.snooze_until=snooze_until;row.created_by=user_id;row.updated_at=datetime.utcnow()
    else:
        db.add(ReminderAction(expense_id=expense_id,event_key=event_key,action=action,snooze_until=snooze_until,created_by=user_id))

@app.get('/api/reminders')
def reminders(_:User=Depends(current_user),db:Session=Depends(get_db)):
    today=date.today()
    days=int(setting_value(db,'reminders.cancellation_days','30'))
    result=[]
    for x in db.scalars(select(Expense).where(Expense.status=='active').order_by(Expense.name)):
        if not is_effectively_active(x,today):
            continue
        item=reminder_event(x,today,days)
        if not item:
            continue
        state=reminder_action_for(db,x.id,item['event_key'])
        if state:
            if state.action in {'done','cancelled'}:
                continue
            if state.action=='snooze' and state.snooze_until and state.snooze_until > today:
                continue
        result.append(item)
    result.sort(key=lambda r:(r['cancellation_date'] or date.max,r['name'].lower()))
    return {'count':len(result),'reminder_days':days,'items':result}

@app.post('/api/reminders/{expense_id}/action')
def reminder_action(expense_id:int,data:ReminderActionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    x=db.get(Expense,expense_id)
    if not x: raise HTTPException(404,'Not found')
    today=date.today()
    days=int(setting_value(db,'reminders.cancellation_days','30'))
    current=reminder_event(x,today,days)
    if not current or current['event_key'] != data.event_key:
        raise HTTPException(409,'Reminder changed; refresh and try again')
    if data.action=='snooze':
        if current['cancellation_date'] and current['cancellation_date'] <= today:
            raise HTTPException(400,'The cancellation deadline has been reached; this reminder cannot be snoozed')
        snooze_until=today+timedelta(days=data.snooze_days or 7)
        if current['cancellation_date'] and snooze_until > current['cancellation_date']:
            snooze_until=current['cancellation_date']
        save_reminder_action(db,x.id,current['event_key'],'snooze',user.id,snooze_until)
    elif data.action=='done':
        save_reminder_action(db,x.id,current['event_key'],'done',user.id)
    else:
        # Keep the contract cost active until the end of the current term, but
        # prevent another automatic renewal after the user confirms cancellation.
        effective_end=current['contract_end']
        if effective_end:
            x.contract_end=effective_end
        x.auto_renew=False
        x.cancelled_on=today
        updated=reminder_event(x,today,days)
        event_key=updated['event_key'] if updated else current['event_key']
        save_reminder_action(db,x.id,event_key,'cancelled',user.id)
        if event_key != current['event_key']:
            save_reminder_action(db,x.id,current['event_key'],'cancelled',user.id)
    db.commit()
    return {'ok':True}

@app.get('/api/settings/ai')
def ai_settings(_:User=Depends(require_admin),db:Session=Depends(get_db)):
    def v(k,d=''): return (db.get(Setting,k).value if db.get(Setting,k) else d)
    return {'base_url':v('ai.base_url'),'model':v('ai.model'),'enabled':v('ai.enabled','false')=='true','has_api_key':bool(v('ai.api_key'))}
@app.put('/api/settings/ai')
def save_ai_settings(data:AISettingsIn,_:User=Depends(require_admin),db:Session=Depends(get_db)):
    values={'ai.base_url':data.base_url,'ai.model':data.model,'ai.enabled':'true' if data.enabled else 'false'}
    if data.api_key: values['ai.api_key']=encrypt_secret(data.api_key)
    for k,v in values.items():
        row=db.get(Setting,k)
        if row: row.value=v
        else: db.add(Setting(key=k,value=v))
    db.commit();return {'ok':True}
@app.post('/api/ai/analyze')
async def ai_analyze(data:AIAnalyzeIn,_:User=Depends(current_user),db:Session=Depends(get_db)):
    def v(k,d=''): return (db.get(Setting,k).value if db.get(Setting,k) else d)
    if v('ai.enabled','false')!='true': raise HTTPException(400,'AI is disabled')
    rows=[expense_dict(x) for x in db.scalars(select(Expense).where(Expense.status=='active')) if is_effectively_active(x)]
    if data.expense_ids: rows=[x for x in rows if x['id'] in set(data.expense_ids)]
    summary={'monthly_total':round(sum(x['monthly_equivalent'] for x in rows),2),'yearly_total':round(sum(x['yearly_equivalent'] for x in rows),2),'expenses':rows}
    try:
        text=await analyze_costs(v('ai.base_url'),decrypt_secret(v('ai.api_key')),v('ai.model'),summary,data.goal,data.language)
        return {'analysis':text}
    except Exception as e:
        raise HTTPException(502,f'AI request failed: {e}')

STATIC_DIR=Path(__file__).parent/'static'
if STATIC_DIR.exists():
    app.mount('/assets',StaticFiles(directory=STATIC_DIR/'assets'),name='assets')
    @app.get('/{full_path:path}')
    def spa(full_path:str):
        candidate=STATIC_DIR/full_path
        if full_path and candidate.is_file(): return FileResponse(candidate)
        return FileResponse(STATIC_DIR/'index.html')
