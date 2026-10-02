# Release check — PenguCost 0.5.2

Baseline: the previously delivered 0.5.1 Full source ZIP.

- 72 backend regression tests passed.
- Native Ollama HTTP request tests verify `num_ctx`, Automatic `num_predict: -1`,
  manual prediction limits, JSON mode, disabled thinking, text/image mapping,
  proxy-prefix URL conversion and privacy-safe failure diagnostics.
- Extraction tests verify four sequential single-page requests and page progress.
- API tests verify context setting migration preserving finance data and manual
  output limits, settings persistence and export/administrator restore.
- Frontend TypeScript check and Vite production build passed.
- Isolated browser tests verify empty usernames for first-user setup and login,
  context setting persistence, running-to-error and running-to-ready transitions
  without selecting history again. Detail responses were deliberately delayed to
  exercise the former polling race. No browser JavaScript errors were observed.
- Browser upload through the native Ollama HTTP fixture produced HUK24 8×,
  Netflix 4× and Salary 4× from a generated text PDF.
- The delta archive applied to 0.5.1 reconstructs the Full archive exactly, and
  both ZIP integrity checks passed.

The model fixtures validate application behavior and request serialization;
there was no running frozenlab/gemma4-mtp:12b or live Ollama instance. No private
user bank file was available. The reported inference abort for both PDF and PNG
has not been reproduced locally or confirmed fixed. Requested context may still
be subject to server/model/memory limits. Docker/Proxmox deployment was not run.
