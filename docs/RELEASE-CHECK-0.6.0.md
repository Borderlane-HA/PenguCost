# Release check — PenguCost 0.6.0

Baseline: previously delivered 0.5.4 Full ZIP.

- 138 backend tests passed (121 existing regressions and 17 new contract tests).
- TypeScript and Vite production build passed. The existing large-bundle advisory
  remains; it is not a build failure.
- Contract tests cover dated prices, lifetime extension, historical holders and
  accounts, future terms, metadata-only updates preserving price plans, leap-day
  allocation, one-time costs, anchored month-end renewal, renewal price priority,
  cancellation, archive/hard delete, archive restoration gaps, history deletion
  with a retained anchor, date bounds, bulk status history, catalog rename/delete
  with current and planned references, and user/admin backup round-trips.
- All calendar/history controls enforce entry ownership; the calendar returns no
  entries belonging to another signed-in user.
- Actual 0.5.4 source was used to create a legacy SQLite database with two price
  periods. Starting 0.6.0 migrated it, retained both prices and seeded one marked
  metadata baseline. A second startup did not duplicate the baseline.
- Backend and compiled frontend historical calculations agree for all 12 months
  of a generated leap-year fixture, including a mid-month price change and a
  change from expense to income. Historical holder values agree as well.
- Browser flow: year/month/week/day, hide open-ended, contract details, change-save
  assistant with selected dates, archive choice, removal from Income & Expenses,
  retained calendar history. No page JavaScript errors.
- Browser screenshots inspected for Light, Midnight, Nordic, Graphite and Emerald.
  A 390px mobile viewport has no document-width overflow; the calendar scrolls
  horizontally within its card. English contract calendar loaded successfully.
- Version is 0.6.0 in health API, VERSION and frontend package manifests.
- Both ZIPs pass integrity checks; applying Git-Changes over the 0.5.4 archive
  exactly reconstructs the Full ZIP. No source file deletion is required.

Generated fixtures were used. Docker/Proxmox were not deployed here. No live
Ollama inference or private bank statement was required or tested for this change.
Legacy metadata cannot reconstruct information that older releases did not save;
those baselines are explicitly marked. Calendar costs are day-based accruals,
not actual bank-payment events. Calendar privacy operations do not erase separate
AI analyses, chats or external backups.
