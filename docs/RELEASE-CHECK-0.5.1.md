# Release check — PenguCost 0.5.1

Baseline: the previously delivered PenguCost 0.5.0 Full ZIP.

- 61 backend tests passed, including actual serialized HTTP request assertions
  for Ollama Automatic (`max_tokens: -1`), manual 24,000, other-provider
  compatibility, safe response diagnostics, profile export/restore and migration.
- The upgrade converts only the former Ollama 8,000-token default to Automatic,
  once. Custom values and later deliberate manual settings survive restarts.
- Frontend TypeScript check and Vite production build passed.
- Browser check on an isolated test database: an existing 24,000-token profile
  switched to Automatic, saved as zero, reopened correctly, switched back to
  manual 24,000 and saved correctly. Mobile layout had no horizontal overflow
  and the browser reported no JavaScript errors.
- The Git-Changes ZIP applied to 0.5.0 reconstructs the Full ZIP exactly; both
  archive integrity checks passed.

These checks used HTTP/model fixtures, not a running Ollama inference. Ollama
0.34.4 compatibility was checked against the published source mapping
`max_tokens` directly to `num_predict`, and the documented unlimited value -1.
No private bank statement, live frozenlab/gemma4-mtp:12b model, Docker deployment
or Proxmox deployment was available. The user's immediate provider failure has
not been reproduced or confirmed fixed; the new precise error is needed if it
persists. Context size, model template, reasoning and server limits can still
cause failures even with Automatic output.
