# Verification

- Original code: all six new WebSocket route reproductions fail, surfacing the first capacity terminal.
- Patched code: 1,581 direct WebSocket/service tests and 45 accepted/sequenced HTTP bridge tests pass.
- Ruff check and formatting pass for the changed Python files.
- The change passes strict OpenSpec validation. Full strict spec validation has existing failures; the owning spec has exactly the same 95 existing validation findings before and after the initial documentation update.
- Deployed only the two Python runtime files after verifying original SHA-256 checksums and creating rollback copies. No dependency, schema, configuration, credential or model changes.
- Readiness and database checks pass after restart. No automatic service restarts; memory is within the existing limit.
- Live production verification: two gpt-6.1-sol WebSocket turns, including an anchored follow-up, complete with one created event per turn and strictly increasing numeric sequences. Existing direct-TLS checks pass: authentication, models, cached route policy, generation and WebSocket upgrade.
- Live overload was not artificially induced. Recovery is verified deterministically at the actual WebSocket route with controlled upstream fixtures.

The proxy retries only output-free capacity terminals, once. Repeated capacity failure or a failure after model output can still reach the client. Upstream model availability remains external to this deployment.
