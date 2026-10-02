# Bank statement assistant — 0.5.4

## Workflow

1. Open **Income & Expenses → Analyze bank statement**, or **AI Agent → Bank statements**.
2. Upload PDF, JPG/JPEG or PNG files covering several months of one account.
3. Select the AI profile and optionally the account to assign to new entries.
4. Confirm sending statement contents to this profile, then start analysis.
5. Review the results: counterparty, count, dates, amounts, cadence and evidence.
6. Filter recurring or one-time bookings. Import one result or select several for sequential review in the ordinary editor. Choose a new entry or explicitly select an existing entry to update.
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
policies when policy references differ. A recurring candidate requires two occurrences.
Single occurrences appear separately under **One-time** and can be saved as one-time entries with their booking date.

Monthly, quarterly, half-yearly and yearly intervals are determined from observed
date gaps. Month-end/leap-year shifts are allowed. Missing months, weekly payments,
multiple same-day bookings and irregular purchases are marked as uncertain.
Even a regular pattern does not prove a subscription or ongoing contract.

The latest observed amount is proposed. Different historical amounts are shown
but do not create historical price periods automatically. New entries start today
for recurring suggestions by default to avoid applying the latest price retrospectively. You can change the
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
  source evidence, or date/amount/merchant not confirmed by the excerpt. Encrypted
  results now retain sanitized editable fields, source/page, reason and a bounded
  booking excerpt, at most 2,000 rejected bookings. Whole pages/images and raw
  provider replies are not retained. Invalid date/amount values become empty fields. If all model rows were
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

## Assigning an existing entry

Choose **Update an existing entry** in the review dialog, then select an owned
entry with the same direction and currency. Suggestions respect differing known
contract references and selected accounts; all compatible entries remain available
for deliberate assignment. Names, account and contract references help distinguish
policies. The editor retains the existing contract, category, account and notes,
proposing only the observed amount/variable flag. Check every field before saving.
A changed price requires an effective date (today initially). Updates use the
existing dated price-history logic and commit atomically with the import guard.
The assistant does not copy all observed prices into history automatically.

## Reviewing rejected bookings

Expand **Review rejected bookings** to see source/page (CSV row), reason and a
bounded original text excerpt. When invalid line references can be recovered,
recovery retains a likely excerpt supported by at least two proposed booking
fields. The row remains rejected until explicit review; recovery is not acceptance.
Correct date, merchant, amount, currency/direction and optional stable reference,
confirm comparison with the original, then revalidate. Date, amount and merchant
must still be supported by the retained text. Suggestions/counts are recomputed;
this action never creates a finance entry. Image excerpts are model transcriptions,
not independently verified text: compare them with the original image and confirm.
Unavailable source/page/excerpts cannot be bypassed; upload the original again or
create an entry manually. Corrected bookings stay marked as manually reviewed in
encrypted result data. Existing imported candidate IDs retain their import guard
when recalculation adds an occurrence to the same group.

Analyses created before 0.5.4 have no retained rejected fields or singleton lists.
Upload them again to use these additions. Existing recurring candidates can still
be assigned to entries without rerunning the analysis.

## Local CSV workflow

Select **CSV import**, choose one CSV and load its preview. No AI profile,
provider request or external processing is used. Map date, counterparty and a
signed amount, or both debit and credit columns. Optional mappings are currency,
direction and stable contract reference. Currency defaults to EUR. Direction
aliases are explicit (expense/income, debit/credit, Lastschrift/Gutschrift).
Without a direction column, signed amounts use negative=expense/positive=income;
choose all-expense/all-income explicitly for an unsigned export. Separate debit
and credit require exactly one nonzero side. Check this against the preview.

Supported encodings: UTF-8 with/without BOM and Windows-1252. Delimiters: semicolon,
comma, tab and pipe, with quoted fields supported. Automatic header detection
checks the first 30 records; delimiter/encoding/header can be selected manually.
Dates default to ISO/German full dates, with an explicit US month/day/year option.
Up to 20 MB, 64 columns and 2,000 bookings. Malformed bookings become rejected
review items; invalid mappings or oversized files are rejected before job creation.
CSV creates encrypted analysis results only, then uses the normal reviewed import
workflow, one-time list and existing-entry assignment. Duplicate imports within
an analysis are blocked; a repeated CSV upload is a new analysis, so review existing
matches before creating entries. CSV row numbers refer to parsed CSV records,
which can span several physical lines when fields contain quoted line breaks.

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
| POST | `/api/ai/statements/csv/preview` | CSV file, optional delimiter/encoding/header; column mapping and five preview records |
| POST | `/api/ai/statements/csv/import` | CSV file, JSON mapping and direction/date settings; encrypted ready result, 201 |
| POST | `/api/ai/statements/{job_id}/rejected/{row_id}/review` | Corrected booking fields and `reviewed=true`; evidence revalidation and recomputed results |
| POST | `/api/ai/statements/{job_id}/candidates/{candidate_id}/import` | Reviewed `ExpenseIn` plus optional `target_expense_id`; atomic creation/update with unique import guard |

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
