# Release check — PenguCost 0.6.1

Baseline: previously delivered 0.6.0 Full ZIP.

- 138 backend regression tests passed; TypeScript/Vite production build passed.
- Compiled review-trigger checks cover descriptive edits (name, provider, URLs,
  notes, reference, tags, holder, account/category, cancellation fields), all cost
  and term triggers, numeric-string normalization and one-time booking dates.
- Browser flow checks provider/URL saving directly without changing price history;
  changed amount and contract end still open the assistant. A historical provider
  correction saves directly and retains both price periods and today's amount.
- No browser page JavaScript errors in that flow.
- Version is 0.6.1 in backend health constant, VERSION and frontend manifests.
- Full and Git-Changes ZIP integrity checked; overlaying Git-Changes onto 0.6.0
  exactly reconstructs the Full ZIP. No file deletion or data migration needed.

Generated local fixtures were used. Docker/Proxmox were not deployed here.
