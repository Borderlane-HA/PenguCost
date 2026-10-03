# Changelog

## 0.6.0

- Add dated contract versions, retaining provider, term, account, category, holder, user assignment and cancellation/renewal rules alongside existing price history.
- Add a save assistant with separate effective dates for prices and terms, a before/after preview and editable cancellation/renewal settings. Scheduled terms are editable/removable without changing current values.
- Add a year/month/week/day contract calendar with phase bars, period costs, per-entry visibility, open-ended filtering and archived/expired contract management.
- Prorate recurring costs by actual calendar days; keep renewal calculations anchored to the original month-end boundary and respect explicitly scheduled prices. Historical dashboard totals/categories now use dated terms.
- Offer archive or permanent deletion for individual and bulk removals. Restoring an archive retains the intervening inactive period.
- Add bounded history deletion with a retained price/term anchor, and ownership checks on all calendar/history controls. Separate statement analyses, chats and backups remain independently managed.
- Include contract timelines and archival state in user/admin JSON backups; seed legacy metadata once with an explicit incomplete-history marker.

## 0.5.4

- Open the bank statement assistant directly from Income & Expenses beside New entry.
- Explicitly choose a new entry or an existing owned entry during reviewed import. Existing updates preserve prefilled contract fields and use dated price history in the same transaction as the duplicate-import guard.
- Show one-time bookings in a separate result filter and prefill one-time entries with their booking date.
- Retain bounded review fields, source/page, original excerpts and reasons for rejected bookings in encrypted results. Correct and revalidate against the retained text excerpt, or explicitly review image transcriptions against the original. Recalculate suggestions after a valid correction.
- Add a local CSV preview and mapped import without an AI profile: UTF-8/Windows-1252, delimiter/header selection, signed amounts or separate debit/credit, explicit direction/date formats and optional currency/reference. Imports remain review-only until each finance entry is saved.
- Separate matching suggestions for known differing contract references/accounts, and show these identifiers in the existing-entry selector.

## 0.5.3

- Normalize unambiguous German booking dates, decimal/grouped amounts, explicit debit/credit aliases, EUR symbols, optional null fields and floating-point serialization noise before validation.
- Add line-numbered PDF input and evidence line references. Recover actual source excerpts instead of requiring the model to reproduce a multi-line booking as one contiguous formatted quote.
- Verify normalized date, amount and merchant against the bounded source excerpt. Invented/unverifiable rows remain excluded.
- Map relative page 1 to the real source page for single-page requests; page labels explicitly request the source page number.
- Show per-reason rejection counts in German/English. Distinguish model-returned bookings that failed validation from a document containing no readable bookings.

## 0.5.2

- Ollama bank statements now use native `/api/chat` requests with an explicit context setting (default 32,768 tokens), `num_predict: -1` in Automatic mode, JSON output and thinking disabled. Normal chat/provider paths remain unchanged.
- Process Ollama statements one page per request to reduce input/output size and advance completed-page progress per page.
- Store and export/restore the new statement context setting; existing profiles receive the default during upgrade. A context of 0 uses the server default.
- Fix a polling race that could update the history to failed/ready while leaving the selected result panel stuck on running. Display failures immediately in the result panel.
- Include only safe numeric request/token counts in native Ollama truncation errors for troubleshooting.
- Start the login and first-user setup username field empty instead of prefilled with admin.

## 0.5.1

- Added Automatic / no fixed output limit for Ollama bank statement analysis; this is the default for new Ollama profiles. Manual limits remain available.
- Once per installation, existing Ollama profiles using the old 8,000-token default switch to Automatic. Explicit custom values such as 24,000 are preserved; choose Automatic in Settings for those profiles.
- Preserved Automatic through profile editing, exports and administrator restore.
- Extended statement request read timeout to 30 minutes while retaining model/server context limits.
- Replaced the generic response error with separate safe messages for empty answers, reasoning-only answers, missing choices, truncation and filtering.
- Validated with backend regression tests and a frontend production build. No live Ollama model or private bank statement was available; these changes do not establish the cause of every provider failure.

## 0.5.0

- Add a bank statement assistant for multiple PDF/JPG/PNG uploads with recurring debit and income detection, transaction counts, amounts, cadence, confidence and source evidence.
- Add reviewed one-at-a-time or sequential import into the normal finance editor, existing-entry warnings and atomic duplicate-import protection.
- Add a configurable statement output-token limit per AI profile (default 8,000), preserved across upgrades and JSON export/restore.
- Support text PDFs with text models and scans/photos with image-capable OpenAI-compatible/Claude profiles; validate and bound documents and AI output.
- Keep original uploads ephemeral, store results encrypted, isolate jobs per user and allow deleting/cancelling analyses without deleting imported entries.
- Recover interrupted chat/document jobs after server restart and block data restore during active analyses.
- Fix future-start reporting, preset billing normalization, input/link validation, local editor dates, multipart headers, save-error feedback and Graphite primary-button contrast.
- Validate JSON financial imports, invalidate sessions on full JSON restore, clean stale reminder/history rows and handle corrupt password hashes safely.
- Harden backup filenames/permissions and validate archive/database/keys before restore; stage files and roll back replacement failures.
- Pin frontend dependencies with a lockfile and npm ci; add backend regression tests to CI and document project review findings.

## 0.4.11

- Improve readability of the **Income & Expenses** table with subtle alternating row backgrounds (zebra striping).
- Zebra colors follow the active PenguCost theme and keep a clear hover highlight across the whole row.

## 0.4.10

- Fixed the TypeScript production-build error in saved-view migration (`TS1117`: duplicate `types` property).
- Update preflight now requires 5 GB of free root-disk space before starting a Docker/Node build.
- Update cleanup explicitly prunes Docker BuildKit cache and unused images before the build and again after the safety backup.
- Pre-update backup retention keeps the newest 10 automatic backups to avoid silent disk growth.

## 0.4.9

- Moved the **All / Expenses / Income** selection from the top toolbar into the filter menu of the **Type** column.
- The top toolbar now stays intentionally minimal with global search, **Reset filters** and **Columns**.
- Moved the remaining advanced filters into their matching table columns: tags under Name, monthly range under Month, uncategorized under Category and auto-renew under Status.
- Saved views remain backward compatible with the previous top-level type filter.
- Hardened Proxmox updates against `ENOSPC`: the updater clears stale Docker/BuildKit caches before building and prunes obsolete build cache/images after a successful update.
- Moved the Proxmox update logic into a standalone source-controlled helper that refreshes itself after successful updates, so future updater fixes no longer require reinstalling the LXC helper.
- Added a free-space preflight before and after the automatic pre-update backup with a clear resize hint when the LXC is too small.
- Increased the Proxmox Quick Setup default root disk from 8 GB to **16 GB** for safer Docker/npm builds.
- The frontend build now removes the npm download cache from the build layer after dependency installation.

## 0.4.8

- Dashboard values are now month-focused: clicking a month in the income-vs-expenses chart updates all KPI cards, category charts, contract counts and monthly date information to that point in time.
- Added **Current month** next to the year picker to jump back to the current year and month at any time.
- The selected month is highlighted in the yearly chart while the full year stays visible for navigation.
- Added **Top 10 expenses** and **Top 10 income** for the selected month, sorted from highest to lowest.
- Category donuts now always reflect the selected month instead of an annual average.
- Reworked **Included in analysis** into a compact summary with a searchable/filterable selection popover, keeping per-entry inclusion without consuming large dashboard space.
- The current-year graph now considers all entries relevant during the year, so contracts that ended earlier in the year can still appear in their historical months.
- Cancellation and contract-end cards follow the selected month.

## 0.4.7

- Added pagination to **Income & Expenses** with 15 rows per page by default and 50 / 100 / All options.
- Filters, saved views and sorting now stay active across page changes; changing filters or sorting returns to page 1.
- Select-all now applies to the currently visible page instead of unexpectedly selecting hidden pages.
- Refined provider logos: downloaded logos render without the old surrounding tile, while fallback initials are precisely centered in a lighter modern monogram.
- Provider icon resolution now triggers a background refresh when an icon is missing or stale and retries in the UI, improving newly added websites such as Amazon.
- Website favicon lookups now use the provider website through Google's favicon service when a branded icon is unavailable.

## 0.4.6

- Fix the TypeScript production build in the cloned-cancellation deadline logic (`TS2367`).
- Keep clone deadline recalculation behavior unchanged while using the correctly typed nullable numeric cancellation notice value.
- Fix validated against the failing typed expression; the complete local production build still depends on npm dependencies being available.

## 0.4.5

- Fix cloning of contract cancellation dates: cloned deadlines are now recalculated from contract end and cancellation notice instead of remaining tied to the original entry.
- Contract end or cancellation-notice changes update the derived "cancel by" date immediately in the editor.
- A manually edited cancellation date intentionally disables automatic recalculation for that draft.
- The backend clone endpoint now applies the same derived-deadline rule.

## 0.4.4

- Cloning is useful again: a clone opens as an unsaved draft named `Kopie von …` / `Copy of …` and keeps provider, amount, category, account/payment method, contract dates, renewal settings, tags, AI context and other useful fields.
- Added optional **provider website** to entries so PenguCost can resolve the right logo even for providers that are not in the built-in catalog.
- Provider icons are centered more consistently and the built-in provider catalog was expanded (including HUK24, ACTALIS, American Express, Vattenfall, fraenk, Rundfunkbeitrag, Sparkasse, CARIAD and Stadtwerke Ingolstadt).
- When external provider icons are enabled, PenguCost checks the affected provider after every create/save and refreshes the complete icon cache automatically every 24 hours.
- Provider icon settings now show the timestamp of the last full refresh.
- Provider website values are included in user/admin JSON export and restore.

## 0.4.3

- Reworked the New/Edit Entry dialog around a compact core form with collapsible Contract & Term, Renewal & Cancellation, More Details and AI Context sections.
- Moved price history out of the main form flow; historical phases are now shown only in a collapsed detail section and only when history actually exists.
- Price edits now create a new dated price phase without visually overwhelming normal entry editing.
- Kept optional renewal pricing for automatic renewals and grouped it with renewal/cancellation settings.
- Added inline private category and account/payment-method creation with compact + controls directly in the entry editor.
- Shortened the sidebar label back to **Accounts & Categories / Konten & Rubriken** while keeping the full catalog title on the page.
- Added optional administrator-controlled provider/brand icons with a local cache. External downloads are off by default and can be enabled/refreshed from Settings.
- Added provider icon matching for common services such as Apple, Spotify, Netflix, Amazon, OpenAI/ChatGPT, Telekom, ADAC, Microsoft, Adobe, Dropbox, GitHub, PayPal and others.
- Provider icons are rendered in provider fields and entry lists, with the existing letter avatar as an offline fallback.
- Added validation hints for inconsistent contract dates (active but already ended, or contract end before next due date).

## 0.4.2

- Added self-service password changes under Settings for every user.
- Users must confirm their current password before setting a new one.
- Added administrator password reset controls for every local account, including the currently signed-in administrator.
- Password reset and change endpoints enforce the existing minimum length, store only Argon2 password hashes and invalidate older login sessions.

## 0.4.1

- Added private per-user accounts, cards/payment methods and categories alongside global administrator templates.
- Global templates can still be hidden per user without affecting anyone else.
- Users can create, edit and delete their own catalog items; private items are never exposed to other users in the normal UI.
- Added direct private category and account/payment-method creation from the New/Edit Entry form.
- Added account/payment-method types for bank accounts, credit/debit cards, PayPal, direct debit, cash and other methods.
- Renamed the catalog workspace to **Accounts, Cards & Categories** and added global/private ownership badges.
- Clarified the estimated amount option as **estimated / variable**, with explanatory help text.
- Extended personal JSON export/import and full administrator backup/restore to preserve private catalogs and catalog ownership.
- Hardened expense and bulk-update ownership checks so users cannot attach another user’s private catalog IDs.

## 0.4.0

- Added Excel-style sorting and per-column filters for income and expenses.
- Added saved table views, configurable columns and bulk actions.
- Added optional renewal prices for automatic contract renewals and forecast calculations.
- Added direct category creation from the entry form for administrators.
- Fixed the dashboard year picker being clipped by the hero panel.
- Added previous-year comparison and explainable forecast drivers to the dashboard.
- Added recurring vs. one-time entries, estimated amounts, contract/customer references and portal URLs.
- Added duplicate warnings and per-entry change history.
- Improved the PenguCost AI Agent with stronger finance prompts, contextual quick questions, global background-job status and more selective Brain memory.
- Added a new README hero image and refreshed documentation.

## 0.3.1

- Fix AI Agent compatibility with local/Ollama chat templates that could ignore FINANCE_DATA_JSON when it was sent in an earlier conversation turn.
- Send the selected current-user finance payload together with the active user request in the latest user message.
- Add FINANCE_ENTRY_COUNT and an explicit guard that prevents models from claiming the payload is absent when entries are present.
- Add one automatic single-turn retry when a model explicitly reports that FINANCE_DATA_JSON was not supplied.

## 0.3.0

- Replaced the one-shot AI analysis screen with the persistent **PenguCost AI Agent**: per-user conversations, follow-up chat, history and editable Brain memory.
- AI requests now run as persisted background jobs; leaving the AI page no longer loses the running state or completed result.
- Added guided AI start modes for a general recurring-finance check or a concrete monthly savings target.
- Strengthened the AI Agent prompt with exact selected-income/expense/delta context, protected essential entries, realistic savings contribution/cumulative-gap logic and structured JSON finance context.
- Reworked the AI data selector into a searchable modal with expense/income filters and collapsible category groups for large datasets.
- Extended personal JSON export/import and administrator full backup/restore with AI conversations, messages and Brain memory.
- Added a modern local SVG PenguCost favicon.
- Simplified the dashboard year menu to year numbers only while keeping the real current year as the default after login.
- Hardened deterministic history/forecast projection to continue from the latest effective renewal cycle, use known price phases and contract dates, and default newly enabled automatic renewal to a 12-month period until changed explicitly.
- Administrators can create a missing global category directly while creating/editing an entry.
- Changed cloning into **Use as template**: opening a clone creates only an unsaved draft, clears identity/contract-specific fields and does not imply a relationship to the source entry. Closing the modal with X or Cancel never creates data.
- Hardened AI ownership checks so selected IDs are always revalidated against the authenticated user before model calls.

## 0.2.1

- Added an explicit dashboard year selector while keeping the current year as the default view.
- Historical years appear automatically only when the signed-in user has relevant contract/price data for those years.
- Added forecast targets for +1, +2 and +5 years.
- Forecast calculations use known price phases, contract terms and automatic renewal periods instead of copying today's total unchanged.
- Historical/forecast views calculate year totals and average monthly expense, income and delta for the selected year.
- Category breakdowns and the interactive item selector now follow the selected dashboard year.
- Upcoming dates switch from the current 60-day window to contract/cancellation dates inside the selected historical or forecast year.
- The selected year is shown prominently in the dashboard and in the cash-flow chart subtitle.


## 0.2.0

- Added recurring **income** alongside expenses using a backwards-compatible `entry_type` field. Existing entries migrate automatically as expenses.
- Fixed overview selection so cancelled-but-still-running contracts remain in current totals until their effective contract end; only paused/ended entries are excluded.
- Reworked the overview into expense, income and monthly-delta metrics.
- Added an income-vs-expense 12-month chart with an explicit delta line.
- Added separate category breakdowns for expenses and income.
- Added expense/income grouping to the interactive dashboard selector.
- Added type filtering and a type column to the Income & Expenses list.
- Annual/quarterly entries are normalized into monthly equivalents in the recurring cash-flow chart, so yearly subscriptions remain visible every month.
- AI analysis now receives only the current user's selected entries, including explicit income/expense types, separate totals and delta.
- Reworked the AI system prompt for concrete, structured, decision-ready Markdown output without invented market prices.
- Added richer AI result rendering with headings and bullet lists.
- Removed the explanatory user-permission text below the AI analysis button.


## 0.1.9

- Added per-user German/English language packs with a user-level language switch.
- Added application version display below the signed-in user in the sidebar.
- Added personal JSON export/import for expenses, price history, hidden accounts/categories, reminders, theme, language and saved AI-analysis prompt.
- Added administrator full JSON export/import for all users, expenses, catalogs, settings and AI profiles; AI keys are exported in restorable form and the file must be treated as sensitive.
- Added expense cloning from the Costs & Contracts table.
- Removed example placeholders from the new-expense form.
- Renamed notes to “Notes (for AI analysis)” / “Notizen (für KI-Analyse)” and explicitly instructs the AI to use this context when evaluating a cost.
- Fixed dashboard selection so every active expense belonging to the current user is selected after a full refresh.
- AI Analysis now has its own per-analysis cost selector, defaults to all active expenses for the current user and remains strictly user-isolated server-side.
- Added persistent per-user AI prompt storage so it is included in user exports.
- Updated Proxmox management examples to use absolute helper paths under `/usr/local/sbin`.

## 0.1.8

### Fixed
- Fixed Proxmox/LXC backups failing with `Permission denied` when the application image runs as the unprivileged `pengucost` user.
- Backup and restore utility containers now run as root only for filesystem/archive operations; the PenguCost application remains unprivileged.
- Proxmox helper scripts invoke repository scripts through `bash`, so updates no longer depend on Git archive executable bits.
- Installer output now uses absolute `/usr/local/sbin/pengucost-*` helper paths for reliable `pct exec` usage.

## 0.1.7

- Enforced strict per-user ownership for expenses, dashboards, reminders and AI payloads. Administrators no longer see other users' cost data.
- Global accounts and categories are managed by administrators and shared as templates with all users. Non-admin deletion now hides a template only for that user, with a restore option.
- Added admin-managed AI profiles with provider presets for Ollama, OpenAI, Grok/xAI, Google Gemini, IONOS AI Model Hub, Claude/Anthropic and custom OpenAI-compatible endpoints.
- Non-admin users can only select enabled AI profiles for analyses and cannot view or modify base URLs, API keys or model configuration.
- Added native Anthropic Messages API support for Claude profiles while retaining OpenAI-compatible chat-completions for the other providers.
- Made cancellation reminder lead time user-specific.
- Fixed dashboard selection so all active expenses are selected initially and newly created expenses are automatically added without re-selecting previously excluded items.
- Added safe migration of orphaned legacy expenses to the first administrator and migration of the former single AI configuration into a profile.

## 0.1.6

### Fixed
- Added `frontend/src/vite-env.d.ts` with Vite/CSS declarations so `tsc -b` can resolve the global stylesheet side-effect import during Docker builds.
- Updated project version references and installer tag example to 0.1.6.

## 0.1.5

### Fixed
- Replaced the ambiguous ASCII art with a clearly readable `PENGUCOST` installer banner.
- Fixed Proxmox VE 9 / Debian 13 installs where `docker.io` was installed with `--no-install-recommends`, leaving the separately packaged Docker CLI unavailable and causing `docker: command not found` during the image build.
- Docker installation now keeps package recommendations enabled for cross-version Debian compatibility and explicitly verifies the Docker CLI before continuing.
- Added a Docker Compose availability check before the PenguCost source is copied/built.

## 0.1.4

### Changed
- Reworked the Proxmox VE installer to use the guided PenguLab/PenguCoach-style setup flow.
- Added Quick Setup and Advanced Setup before any LXC is created.
- Advanced mode now configures VMID, hostname, CPU, RAM, swap, disk, rootfs/template storage, bridge, DHCP/static IPv4, VLAN, web port and source channel.
- PenguCost source is downloaded and validated before LXC creation, preventing the previous release-bundle 404 from leaving a half-installed container.
- Proxmox deployment now builds the selected source inside the LXC and therefore no longer depends on a GitHub release asset being present.
- Failed installations now offer automatic cleanup of the incomplete LXC.
- Added in-LXC helpers: `pengucost-status`, `pengucost-backup`, `pengucost-restore` and `pengucost-update`.
- Source-based updates create a backup before building/restarting PenguCost.
- Normal runtime remains offline-capable after installation; Internet is only required for installation, updates and optional external AI endpoints.

## 0.1.3
- Added persistent reminder actions: Done, Remind later, and Contract cancelled.
- Added snooze presets for 1/3/7/14/30 days with deadline capping.
- Added two-step confirmation before marking a contract as cancelled.
- Contract cancellation now freezes the current effective term, disables auto-renewal, records the cancellation date, and keeps costs active until term end.
- Added per-reminder event keys so completed reminders can return correctly for later renewal cycles.
- Current dashboard/AI totals now exclude effectively expired non-renewing contracts.
- Added automatic in-place migration from 0.1.2 for cancellation acknowledgement and reminder state storage.

## 0.1.2
- Added configurable colors for all cost categories.
- Category colors are now used in the dashboard donut chart and category badges.
- Added configurable cancellation reminder lead time in Settings.
- Added notification bell with reminder count and a contract reminder center.
- Added separate reminder states for cancellation deadlines, imminent automatic renewals, and already renewed contracts.
- Improved cancellation notice input with common presets plus a custom-day option.
- Added automatic in-place migration from 0.1.1 for the new category color field.

## 0.1.1

- Added effective-dated price history; changing a subscription price no longer rewrites historical periods
- Added support for scheduled future price changes
- Added minimum contract term in months and automatic contract-end calculation
- Added configurable auto-renewal periods in months
- Added effective upcoming contract/cancellation dates for renewed contracts
- Updated annual payment forecast to use the price valid on each payment date
- Added in-place SQLite migration from 0.1.0 and automatic seeding of existing prices into history

## 0.1.0

Initial PenguCost foundation:
- Recurring expense and contract management
- Monthly/yearly normalization
- Contract and cancellation dates
- Account and category assignment
- Interactive dashboard filtering
- Annual payment forecast
- Multi-user local authentication
- Six themes
- Optional OpenAI-compatible AI analysis
- Docker deployment
- Proxmox VE 8/9 installer
- Offline release bundle workflow
- Backup and restore scripts
