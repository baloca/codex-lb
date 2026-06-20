## 1. Stream-idle durable bridge retirement

- [x] 1.1 Delete the timed-out durable HTTP bridge session row and aliases after
  an HTTP bridge `stream_idle_timeout`.
- [x] 1.2 Preserve prompt-cache affinity while allowing an immediate
  same-`previous_response_id` retry to create a fresh durable row.
- [x] 1.3 Preserve fresh-context recovery where a retry keeps `prompt_cache_key`
  but omits `previous_response_id`.
- [x] 1.4 Add regression coverage for same-`previous_response_id` SDK retry and
  Eva-style fresh-context recovery after `stream_idle_timeout`.

## 2. Validation

- [x] 2.1 Run focused HTTP bridge regression tests for stream-idle rebind and
  existing previous-response rebind behavior.
- [x] 2.2 Run focused `ruff check`, `ruff format --check`, and `ty check` on the
  changed runtime/test files.
- [x] 2.3 Validate the OpenSpec change with
  `OPENSPEC_TELEMETRY=0 npx -y @fission-ai/openspec@latest validate retire-stream-idle-durable-bridge --strict`.
