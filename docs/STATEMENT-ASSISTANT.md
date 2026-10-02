# Bank statement assistant — 0.5.3

## Workflow

1. Open **AI Agent → Bank statements**.
2. Upload PDF, JPG/JPEG or PNG files covering several months of one account.
3. Select the AI profile and optionally the account to assign to new entries.
4. Confirm sending statement contents to this profile, then start analysis.
5. Review the results: counterparty, count, dates, amounts, cadence and evidence.
6. Import one result or select several for sequential review in the ordinary editor.
7. Confirm amount, currency, direction and interval, then save each entry.

The counter advances when a page/request has finished extraction; it is not a
live token counter. Ready/error states update the selected panel automatically.
An analysis can run in the background while you navigate elsewhere. Reopen it in
the analysis list. Delete it to discard encrypted results or cancel running work;
previously imported finance entries remain. Cancelling prevents further requests
but cannot retract a request already received by the selected AI provider.

## What a count means

**Netflix 4×** means four extracted bookings for that party/account/reference,
not four simultaneous subscriptions or four times the proposed recurring amount.
Separate policy/contract references, accounts, currencies and income/expense
directions produce separate candidates. **HUK24 8×** can therefore be multiple
policies when policy references differ. A candidate requires two occurrences.
Single occurrences are counted in the summary but are not recurring suggestions.

Monthly, quarterly, half-yearly and yearly intervals are determined from observed
date gaps. Month-end/leap-year shifts are allowed. Missing months, weekly payments,
multiple same-day bookings and irregular purchases are marked as uncertain.
Even a regular pattern does not prove a subscription or ongoing contract.

The latest observed amount is proposed. Different historical amounts are shown
but do not create historical price periods automatically. New entries start today
by default to avoid applying the latest price retrospectively. You can change the
start/date/interval in the editor. Contract end and notice periods stay empty.
Non-EUR transactions retain their original currency in results; manually convert
the amount to EUR and change the draft currency before import. There is no FX API.

## Processing and limits

- Up to 10 files, 20 MB combined, 40 pages and 2,000 extracted transactions.
- One running job per user, two running jobs per installation (single worker).
- PDFium locally extracts text from text PDFs. Sparse/scanned pages and photos
  are re-encoded as JPEG at up to 2,200 pixels per edge; images are capped at
  25 megapixels. Password-protected PDFs must be unlocked first.
- Ollama processes one page per native `/api/chat` request. Automatic output
  (`statement_max_tokens: 0`) sends `options.num_predict: -1`; a manual limit
  remains available. `statement_context_tokens` defaults to 32,768 and is sent
  as `options.num_ctx`. Set 0 to use the Ollama server/model context default.
  JSON output is enabled and thinking is disabled for transaction extraction.
  These statement settings do not change normal AI chat requests.
- Other providers still process up to two pages per request and default to 8,000
  output tokens. Text PDFs can use a text model; scans/photos need image support.
- Statement requests allow up to 30 minutes of read inactivity per call (connection
  timeout: 30 seconds). An Ollama model still needs enough context for the input,
  final JSON. Increasing context requires more memory and remains subject to
  model/server capacity. Base URLs ending in `/v1` or `/v1/chat/completions` are
  mapped to `/api/chat` at the same host and proxy prefix; a proxy must expose
  that native route. HTTP 404 can mean a missing model or an inaccessible route.
- Empty final answers, reasoning without a final answer, missing response choices,
  token/context truncation and provider filtering have separate privacy-safe error
  messages. Native truncation diagnostics include requested context and numeric
  prompt/output counts when supplied by Ollama; no response content is exposed.
  Response bodies and reasoning are not stored or displayed in errors.
- Model output must be complete JSON. Unambiguous German dates (`16.01.2025`),
  grouped/comma-decimal amounts (`1.234,56`), explicit debit/credit aliases, EUR
  symbols and optional null reference/account fields are normalized.
- Text PDF input has local numbered lines. Models can cite `evidence_lines`
  (up to eight source lines spanning eight lines). The application reconstructs
  an actual source excerpt and checks the structured booking date, amount and
  merchant against it. Normalized quote matching also handles punctuation,
  whitespace and date-format differences; arbitrary paraphrases are rejected.
  A booking date with an omitted year needs supporting statement-year context.
  Relative page 1 is mapped only when the request contains exactly one page.
- Rejected rows have fixed, localized reason counts: fields, source page, missing
  source evidence, or date/amount/merchant not confirmed by the excerpt. Raw
  rejected rows and provider replies are not persisted. If all model rows were
  rejected, the UI says they failed validation rather than claiming the PDF had
  no readable transactions. Invalid/truncated JSON still fails the job.
- Exact duplicate uploads are skipped. Overlapping transactions are deduplicated
  by date, normalized party/reference/account, amount, currency and direction.
  Same-day identical payments on one page retain their multiplicity. Identical
  payments spread across separate pages can remain ambiguous and need review.

Models can miss rows, split the same merchant under different names or read a
scan incorrectly. Counts are extracted evidence, not a guarantee of completeness.
Useful input includes full booking dates/year, counterparty, amount, debit/credit
columns and account identifiers. Clear, complete statements work best.

## Privacy and persistence

Original uploads are only temporary (multipart parsing may use temporary files);
PenguCost does not retain them in its data volume. Analysis results are encrypted
using `/data/.fernet_key`. Normal endpoints only expose the authenticated user's
jobs and candidates, including for administrators. API responses use `no-store`.

External providers receive the extracted text or image pages after confirmation.
The provider may apply its own retention policy. Local Ollama profiles allow
local processing if the configured model supports the required input.

Completed results persist until deletion. Running jobs are marked interrupted
after restart because source bytes are intentionally not retained. There is no
automatic job retry that resends bank contents. Errors exclude provider response
bodies, keys and URLs. Restore/import blocks while relevant AI jobs are running.

User/admin JSON exports omit statement results; imported entries are included as
normal entries. Volume backups include results and the encryption key. A user
JSON import replaces that user's statements/results alongside their other data.
Full administrator JSON restore clears all statements/results. Existing browser
sessions are invalidated after a full administrator JSON restore.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/ai/statements` | Multipart `files`, `profile_id`, optional `account_id`, `consent=true`; returns 202 |
| GET | `/api/ai/statements` | Current user's latest 50 analysis jobs |
| GET | `/api/ai/statements/{job_id}` | Status/progress, decrypted results, existing-entry matches and imported flags |
| DELETE | `/api/ai/statements/{job_id}` | Cancel/delete analysis; keep imported entries |
| POST | `/api/ai/statements/{job_id}/candidates/{candidate_id}/import` | Reviewed `ExpenseIn` payload; atomic creation with a unique import guard |

## Upgrade

Replace the changed files or use the full source package and rebuild:

```bash
docker compose up -d --build
```

New tables are created automatically without changing existing entry IDs or
price periods. `frontend/package-lock.json` pins the tested dependency graph;
Docker uses `npm ci`. Existing Docker volumes and encryption keys are retained.
The source ZIP is not the offline Docker image bundle: initial builds need
package downloads. Runtime with a local AI endpoint needs no external AI service.
