# Project review — PenguCost 0.5.0

Reviewed against the supplied full source package **0.4.11**, which is the release
baseline. The GitHub link could not be retrieved in this environment; no newer
remote changes were assumed or overwritten. This is a source review and tested
release update, not an exhaustive security audit.

## Implemented in this release

| Area | Finding / previous behavior | Change |
| --- | --- | --- |
| AI model limits | Fixed extraction limits can exceed some models' output capacity | Per-profile statement output limit, default 8,000 tokens, persisted and exported |
| AI inputs | Only existing finance entries could be analyzed | PDF/JPG/PNG statement assistant with evidence, recurrence detection and reviewed import |
| AI jobs | Running jobs could stay running permanently after a restart | Mark interrupted chats and statement jobs as errors with a retry/upload instruction |
| Document processing | No bounded document pipeline | Byte/type checks, page/pixel/text/transaction limits, two-page calls and complete JSON validation |
| Privacy | New statement data requires separate protection | Ephemeral raw uploads, encrypted results, user-scoped routes and no-store API responses |
| Imports | Repeated clicks/concurrent saves could create duplicate suggestions | Unique candidate/job guard and entry creation in a single transaction |
| Finance inputs | Invalid interval/status, nonfinite amounts, empty names and unsafe link schemes were accepted | Server validation, canonical preset intervals and safe HTTP(S) links |
| Current reporting | Future-start entries could enter backend dashboard / AI current totals | Respect start date in effective activity checks |
| Annual normalization | Preset intervals could be overridden by the default `interval_months=1` | Normalize monthly/quarterly/half-yearly/yearly periods consistently |
| Entry editor | Failed saves produced no useful inline error | Display server validation/save errors inside the form |
| Local dates | Editor default date used UTC | Use local calendar date for form defaults and statement drafts |
| API helper | Multipart bodies received the JSON content type; validation arrays rendered poorly | Let the browser set multipart boundaries and render field error messages |
| Graphite theme | Primary white text could blend into pale primary buttons | Dedicated primary button text token |
| Restore | Live files deleted before archive validation; filenames interpolated into shell | Validate archive, SQLite and keys before stopping/replacing; safe mounts, staged replacement and rollback on replacement failure |
| Backup | Output filenames were shell-interpolated and backup permissions not explicit | Pass name via environment and create private backup archives |
| Full JSON restore | Old sessions could remain valid for restored user IDs; statement/audit rows were not cleared | Increment restored session versions and clear the relevant owned tables |
| User JSON import | Invalid entry rows could reach ORM creation | Validate financial entries before commit; failed imports preserve old data |
| Deletion | Some reminder/history rows could remain orphaned | Clean those rows in individual and bulk deletion and user import |
| Authentication | Corrupt imported password hashes could raise server errors | Fail authentication cleanly |
| Static serving | File resolution lacked a final root containment check | Require static files to resolve inside the static root |
| Builds | Frontend dependencies were all `latest` without a lockfile | Pin installed versions, include package-lock.json and use npm ci in Docker |
| CI | Only container build and health smoke test | Add backend regression tests on Python 3.13 |

## Useful next improvements

1. **Bank-specific import reliability:** add optional CSV/CAMT/MT940 import and
   merchant alias editing. Deterministic structured imports complement AI scans
   and avoid OCR errors and inconsistent merchant names.
2. **Explicit price-change proposals:** let users confirm effective price dates
   from statement evidence and import several price periods. Current release
   deliberately proposes only the latest amount with a new start date today.
3. **AI capability settings:** optional profile-level image/context limits and a connection test, so local models can advertise their capabilities.
4. **Currencies:** define one base currency or separate totals by currency.
   Existing generic entry routes allow non-EUR amounts but reporting does not
   convert them. The new statement importer requires manual EUR conversion.
5. **Jobs and persistence:** a dedicated durable queue would allow more workers,
   richer cancellation and configurable result retention. Current background
   work is intended for the shipped single-worker Uvicorn deployment.
6. **Maintainability:** split the growing API/App files into finance, catalogs,
   authentication, AI and transfer modules; adopt FastAPI lifespan hooks and
   timezone-aware timestamps without changing existing stored date semantics.
7. **Bundle size:** split charts and AI/editor screens into lazy chunks. The build
   remains successful but reports a large JavaScript chunk.
8. **Internet-facing hardening:** add authentication throttling, explicit secure
   cookie/proxy settings and documented origin/CSRF handling before broad public
   exposure. The documented LAN/VPN deployment remains the supported baseline.
9. **Restore durability:** replacement failures are rolled back; a power loss
   between multiple file renames still needs operational recovery from the
   retained backup. A filesystem snapshot/atomic directory design can strengthen
   that guarantee.
10. **Export coverage:** include schema-versioned, validated historical price and
    audit data and optional encrypted statement results in portable exports.
    Current volume backups retain all database state; JSON exports omit statement
    results intentionally and do not provide a full audit-history transport.

## Validation

- Backend regression tests exercise statement extraction validation, counts,
  duplicate/overlap handling, policy/account/currency/direction separation,
  month-end/leap-year intervals, variable amounts and one-time occurrences.
- API tests exercise upload consent/types, disabled profiles, user isolation,
  account permissions, encrypted results, progress, interruption recovery,
  reviewed import, concurrent/idempotent import and deletion without loss of
  imported entries.
- Finance/auth tests exercise historical prices, start dates, validation,
  import rollback, session invalidation, corrupt hash handling and an upgrade
  migration preserving existing profiles/entries.
- Restore tests exercise archive traversal/unexpected members, invalid databases
  and keys, validation before mutation and rollback on a simulated replacement
  failure. Test filesystem ownership changes are mocked; actual Docker uid/gid
  application requires deployment validation.
- **48 backend tests passed** in the local Python 3.12 runtime; CI runs the same suite on Python 3.13.
- Browser end-to-end test with a synthetic text PDF and local provider stub: HUK24 8×, Netflix 4× and Salary 4×; reviewed Netflix import persisted correctly with no browser errors.
- Sequential browser review imported HUK24 as expense and Salary as income; all three imported flags persisted after reopening. English labels loaded correctly.
- Screenshots inspected for Light, Graphite and the mobile layout; Midnight, Nordic and Emerald were also rendered. Mobile document width matched the 390 px viewport without horizontal overflow.
- TypeScript checking and Vite production build.
- Python compilation and shell syntax checks.

No live provider credentials, real statements or personal finance data were
used for these tests. Real-world extraction quality depends on the model and
bank statement layout. The full Docker image build and Proxmox install/restore
were not run here because Docker/Proxmox are not available in this environment.
