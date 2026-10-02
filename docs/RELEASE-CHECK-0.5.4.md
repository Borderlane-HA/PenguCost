# Release check — PenguCost 0.5.4

Baseline: the previously delivered 0.5.3 Full ZIP.

- 121 backend regression tests passed; TypeScript/Vite production build passed.
- CSV tests cover German bank headers, UTF-8/BOM and Windows-1252, quoted fields,
  export preambles, ISO/German/explicit US dates, signed/unsigned amounts,
  separate debit/credit, duplicate multiplicity, malformed mappings and limits.
- API tests verify no AI calls/profile requirement for CSV, encrypted results,
  original-file non-persistence, no finance entries created on analysis/import,
  one-time dates, ownership isolation and duplicate-import protection.
- Existing-entry updates retain contract fields and notes, require an effective
  date for changed prices and preserve earlier price periods. Concurrent update
  requests produce one successful import and one duplicate conflict without an
  extra entry/price period. Different known contract references are not suggested
  as the same policy.
- Correction tests require explicit original review, verify date/amount/merchant
  against retained text, preserve US-date evidence, refuse missing evidence and
  retain the import marker when a corrected singleton becomes recurring.
  Image transcriptions require original-image review and remain vision results.
- Browser flow: direct Income & Expenses button, local CSV without AI profile,
  German column mapping/preview, rejected currency correction, one-time import
  dated 2026-02-10, and existing Netflix update from 10 to 16.99 EUR with dated
  price history and unchanged contract/note. No browser JavaScript errors.
- Native Ollama HTTP fixture and generated 15-page PDF: 45 deliberately invalid
  source references produce review items; an original booking excerpt is
  recovered, explicitly reviewed and revalidated, yielding one accepted booking
  and 44 remaining rejections. No automatically accepted recovery.
- Browser screenshots checked for Light, Midnight, Nordic, Graphite and Emerald;
  390-pixel mobile viewport has no page-width overflow. English workflow loads.
- Both ZIP integrity checks passed; applying Git-Changes to 0.5.3 exactly
  reconstructs the Full ZIP. No source-file deletion is required.

Live frozenlab/gemma4-mtp:12b inference and the user's private statements were
not available. Generated bank documents/CSV and a native HTTP fixture validate
application handling; they do not prove live model extraction completeness.
Docker/Proxmox were not deployed here. Existing analyses require re-upload to
obtain the newly retained rejection details and singleton lists.
