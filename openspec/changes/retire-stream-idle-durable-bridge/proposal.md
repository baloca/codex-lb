## Why

Production `/v1/responses` HTTP bridge traffic can hit `stream_idle_timeout`
when the upstream Responses websocket accepts a follow-up request but emits no
frames. After that timeout, an SDK retry that keeps the same
`previous_response_id` and `prompt_cache_key` may recreate a new upstream
websocket while reusing the same durable HTTP bridge row. If that durable row is
the poisoned continuity anchor, the retry can spend another full idle window
instead of recovering or failing quickly.

## What Changes

- Retire the timed-out durable HTTP bridge session record and aliases when an
  HTTP bridge request reaches `stream_idle_timeout`.
- Preserve `prompt_cache_key` affinity while preventing the immediate
  same-`previous_response_id` retry from reusing the same poisoned durable row.
- Allow the immediate same-`previous_response_id` retry to use the existing
  previous-response recovery rebind path and create a fresh durable row.
- Preserve the existing fresh-context recovery path where the client retries
  with the same `prompt_cache_key` and no `previous_response_id`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: HTTP bridge stream-idle recovery must retire the
  poisoned durable bridge row without discarding prompt-cache affinity.

## Impact

- Code: `app/modules/proxy/_service/http_bridge/mixin.py`,
  `app/modules/proxy/_service/http_bridge/streaming.py`,
  `app/modules/proxy/durable_bridge_coordinator.py`,
  `app/modules/proxy/durable_bridge_repository.py`,
  `app/modules/proxy/service.py`
- Tests: `tests/integration/test_http_responses_bridge.py`
- Specs: `openspec/specs/responses-api-compat/spec.md`
