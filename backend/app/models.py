from datetime import datetime, date
from sqlalchemy import String, Float, Boolean, Date, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), default='')
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default='member')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    session_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Account(Base):
    __tablename__ = 'accounts'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(40), default='bank')
    note: Mapped[str] = mapped_column(String(255), default='')
    # NULL = global administrator template, otherwise private to this user.
    created_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)


class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str] = mapped_column(String(40), default='wallet')
    color: Mapped[str] = mapped_column(String(16), default='#5B5CF0')
    # NULL = global administrator template, otherwise private to this user.
    created_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)


class HiddenCatalogItem(Base):
    __tablename__ = 'hidden_catalog_items'
    __table_args__ = (UniqueConstraint('user_id', 'item_type', 'item_id', name='uq_hidden_catalog_item'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    item_type: Mapped[str] = mapped_column(String(20), index=True)
    item_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Expense(Base):
    __tablename__ = 'expenses'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    provider: Mapped[str] = mapped_column(String(160), default='')
    provider_website: Mapped[str] = mapped_column(String(500), default='')
    entry_type: Mapped[str] = mapped_column(String(16), default='expense', index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default='EUR')
    billing_interval: Mapped[str] = mapped_column(String(20), default='monthly')
    interval_months: Mapped[int] = mapped_column(Integer, default=1)
    minimum_term_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    renewal_period_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    renewal_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey('categories.id'), nullable=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey('accounts.id'), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    cancellation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cancellation_notice_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancelled_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default='active')
    essential: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_type: Mapped[str] = mapped_column(String(16), default='recurring')
    amount_estimated: Mapped[bool] = mapped_column(Boolean, default=False)
    contract_url: Mapped[str] = mapped_column(String(500), default='')
    contract_reference: Mapped[str] = mapped_column(String(160), default='')
    tags: Mapped[str] = mapped_column(String(255), default='')
    notes: Mapped[str] = mapped_column(Text, default='')
    contract_holder: Mapped[str] = mapped_column(String(160), default='')
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    archived_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    history_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship(Category)
    account = relationship(Account)
    prices = relationship('ExpensePrice', back_populates='expense', cascade='all, delete-orphan', order_by='ExpensePrice.valid_from')
    versions = relationship('ContractVersion', back_populates='expense', cascade='all, delete-orphan', order_by='ContractVersion.effective_from')


class ContractVersion(Base):
    __tablename__ = 'contract_versions'
    __table_args__ = (UniqueConstraint('expense_id', 'effective_from', name='uq_contract_version_date'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id'), index=True)
    effective_from: Mapped[date] = mapped_column(Date, index=True)
    snapshot_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expense = relationship(Expense, back_populates='versions')


class ExpensePrice(Base):
    __tablename__ = 'expense_prices'
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id'), index=True)
    amount: Mapped[float] = mapped_column(Float)
    valid_from: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    expense = relationship(Expense, back_populates='prices')


class ExpenseChange(Base):
    __tablename__ = 'expense_changes'
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id'), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(32), default='updated')
    changes_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ReminderAction(Base):
    __tablename__ = 'reminder_actions'
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id'), index=True)
    event_key: Mapped[str] = mapped_column(String(160), index=True)
    action: Mapped[str] = mapped_column(String(20))
    snooze_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIProfile(Base):
    __tablename__ = 'ai_profiles'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default='AI')
    provider: Mapped[str] = mapped_column(String(40), default='custom')
    base_url: Mapped[str] = mapped_column(String(500), default='')
    model: Mapped[str] = mapped_column(String(200), default='')
    api_key: Mapped[str] = mapped_column(Text, default='')
    statement_max_tokens: Mapped[int] = mapped_column(Integer, default=8000)
    statement_context_tokens: Mapped[int] = mapped_column(Integer, default=32768)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIConversation(Base):
    __tablename__ = 'ai_conversations'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    profile_id: Mapped[int | None] = mapped_column(ForeignKey('ai_profiles.id'), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180), default='PenguCost AI')
    mode: Mapped[str] = mapped_column(String(24), default='analysis')
    target_savings: Mapped[float | None] = mapped_column(Float, nullable=True)
    selected_expense_ids: Mapped[str] = mapped_column(Text, default='[]')
    status: Mapped[str] = mapped_column(String(20), default='idle', index=True)
    last_error: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIMessage(Base):
    __tablename__ = 'ai_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey('ai_conversations.id'), index=True)
    role: Mapped[str] = mapped_column(String(20), default='user')
    content: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AIBrain(Base):
    __tablename__ = 'ai_brains'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    summary: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Setting(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default='')


class StatementJob(Base):
    __tablename__ = 'statement_jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    status: Mapped[str] = mapped_column(String(20), default='running', index=True)
    completed_pages: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    result_encrypted: Mapped[str] = mapped_column(Text, default='')
    last_error: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StatementImport(Base):
    __tablename__ = 'statement_imports'
    __table_args__ = (UniqueConstraint('job_id', 'candidate_id', name='uq_statement_import'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey('statement_jobs.id'), index=True)
    candidate_id: Mapped[str] = mapped_column(String(24))
    expense_id: Mapped[int] = mapped_column(ForeignKey('expenses.id'))
