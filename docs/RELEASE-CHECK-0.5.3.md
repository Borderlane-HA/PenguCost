# Release check — PenguCost 0.5.3

Baseline: the previously delivered 0.5.2 Full ZIP.

- 95 backend regression tests passed; TypeScript/Vite production build passed.
- Tests cover German full/partial dates with source-year context, grouped/comma
  decimal amounts, signed expense formats, explicit debit/credit aliases, EUR
  symbols, null optional fields, floating-point noise and relative page indices.
- Source-evidence tests cover numbered multi-line excerpts and normalized quote
  matching. Invented/mismatched dates, amounts, merchants and line/page references
  remain excluded. Diagnostics contain only fixed reason names/counts.
- API tests verify accepted/rejected counts and exclusion of invalid provider
  field contents from user-visible results/diagnostics.
- Browser check through a native Ollama HTTP fixture and generated 15-page German
  PDF: 15/15 pages, 45 confirmed bookings, HUK24/Netflix/Salary each 15 occurrences.
  Netflix imported as a single recurring 15.99 EUR entry through the review form.
- Another fixture returned invalid line references on all 45 bookings. The UI
  displayed the German missing-evidence reason/count and explained that model
  rows failed validation; no false no-readable-transactions warning appeared.
- No browser JavaScript errors; both archive integrity checks passed. Applying
  Git-Changes to 0.5.2 reconstructs the Full ZIP exactly.

No private 15-page bank file or live frozenlab/gemma4-mtp:12b/Ollama inference was
available. The specific cause of the user's 143 previous row rejections cannot
be recovered from the old aggregate-only result. Generated fixtures verify the
new application handling, not live model extraction quality. Docker/Proxmox
were not deployed here. A fresh analysis is needed to apply the new validation.
