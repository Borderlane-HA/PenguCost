# PenguCost Architecture

## Design goals

1. Core app must continue to work without Internet access.
2. Deployment should be simple enough for a small home server or Proxmox LXC.
3. Recurring costs must remain understandable without bookkeeping knowledge.
4. AI is optional and isolated from the core data path.
5. A release must be distributable as a single offline bundle.

## Runtime

The frontend is compiled during the Docker build and copied into the backend image. FastAPI serves both `/api/*` and the SPA. SQLite stores all persistent state under `/data`.

## Persistence

`/data` contains:
- `pengucost.db`
- `.session_secret`
- `.fernet_key`

All three must be included in backups. Losing the Fernet key means an already stored AI API key can no longer be decrypted, but expense data remains readable.

## Effective-dated prices

Each expense has one or more price phases in `expense_prices`. A phase starts on `valid_from` and remains valid until the next phase begins. Editing a price creates or updates a phase instead of rewriting prior periods. This keeps historical reporting stable and also allows future price changes to be scheduled. Existing 0.1.0 expenses are migrated automatically into an initial price phase.

## Contract terms

Contracts store an exact start and end date and therefore do not assume calendar-year boundaries. `minimum_term_months` can be used to calculate an end date when one is not entered explicitly. Auto-renewing contracts can additionally store `renewal_period_months` so PenguCost can derive the next relevant end/cancellation date.

## Cost normalization

`monthly_equivalent = price_effective_on_date / interval_months`

`yearly_equivalent = monthly_equivalent * 12`

Supported presets use 1, 3, 6 and 12 months. A custom interval stores an arbitrary positive month count.

## Forecast

When `next_due_date` is available, the dashboard advances it by `interval_months` and places the full charge into the matching month using the price phase valid on that payment date. Contract start/end boundaries are respected. If no next due date is known, the UI uses the normalized monthly equivalent as an even estimate.

## AI data flow

Only when the user explicitly triggers an analysis:
1. UI sends the analysis goal and selected expense IDs to PenguCost.
2. Backend creates a reduced structured expense payload.
3. Backend calls the configured OpenAI-compatible endpoint.
4. The response is displayed; no AI result is persisted by the current application.


## Reminder state
Reminder actions are stored separately from expenses using an event key built from the reminder kind, cancellation deadline and effective contract end. This lets a user dismiss the current reminder without permanently muting the contract: when a later renewal cycle produces new dates, it produces a new event key and can notify again.

Marking a contract as cancelled disables automatic renewal and freezes the currently effective contract end. The expense remains active until that date so current cost calculations are not reduced prematurely.
