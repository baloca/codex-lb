## ADDED Requirements

### Requirement: HTTP bridge stream-idle retires poisoned durable continuity

The service MUST retire the timed-out durable HTTP bridge session record and
its aliases when an HTTP bridge Responses request reaches `stream_idle_timeout`
before upstream `response.completed`, before allowing later requests for the
same bridge key to create or reuse durable continuity.

The service MUST preserve the request's `prompt_cache_key` as a cache-affinity
hint. Retiring the durable row MUST NOT globally discard prompt-cache affinity
or require clients to change cache keys. When the timed-out request included
`previous_response_id`, the immediate retry with the same bridge key and same
`previous_response_id` MAY use the existing previous-response recovery rebind
path to create a fresh durable bridge row instead of failing closed solely
because the old durable row was retired.

#### Scenario: SDK retry after stream-idle creates fresh durable row

- **GIVEN** an HTTP `/v1/responses` bridge session is keyed by
  `prompt_cache_key`
- **AND** a follow-up request includes `previous_response_id`
- **AND** the upstream websocket accepts that follow-up but emits no terminal
  frame before `stream_idle_timeout`
- **WHEN** the client immediately retries the same payload with the same
  `prompt_cache_key` and `previous_response_id`
- **THEN** the retry does not reuse the timed-out durable bridge row
- **AND** the retry can create a fresh durable bridge row for the same
  `prompt_cache_key`
- **AND** the forwarded upstream payload still includes the original
  `previous_response_id`

#### Scenario: fresh-context recovery keeps prompt-cache affinity

- **GIVEN** an HTTP `/v1/responses` bridge session is keyed by
  `prompt_cache_key`
- **AND** a follow-up request with `previous_response_id` reached
  `stream_idle_timeout`
- **WHEN** a later recovery request keeps the same `prompt_cache_key` but omits
  `previous_response_id`
- **THEN** the service does not reuse the timed-out durable bridge row
- **AND** the recovery request can create a fresh durable bridge row for the
  same `prompt_cache_key`
- **AND** the forwarded upstream payload does not include
  `previous_response_id`
