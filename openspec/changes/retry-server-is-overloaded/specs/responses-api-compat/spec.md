## ADDED Requirements

### Requirement: Upstream overload errors receive bounded safe retry

The Responses proxy MUST classify upstream `overloaded_error` and
`server_is_overloaded` failures as retryable transient errors.

For a direct upstream request, the proxy MUST use the existing bounded
same-account transient retry policy while no downstream output is visible.

For a pre-created WebSocket/HTTP-bridge request, the proxy MUST allow the
existing single transparent replay only when no response was created, no other
request is pending, and no downstream output is visible.

The proxy MUST NOT substitute another model, retry after visible output, or
replay a continuation that fails the existing retry-safety checks.

#### Scenario: New overload code before response creation

- **WHEN** upstream returns `server_is_overloaded` before response creation
- **AND** the request remains safe to replay
- **THEN** the proxy retries through its existing bounded transient mechanism
- **AND** does not surface the first transient failure to the client

#### Scenario: Overload after visible output

- **WHEN** an overload failure occurs after downstream output is visible
- **THEN** the proxy does not replay the request
