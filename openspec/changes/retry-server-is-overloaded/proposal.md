# Proposal: Retry the new upstream overload code

## Problem

OpenAI now emits `server_is_overloaded` for transient GPT-5.6 capacity failures.
codex-lb recognizes the older `overloaded_error`, but the new code is absent
from the direct-stream and pre-created WebSocket replay sets. A transient error
therefore reaches the client even when retrying the same request would succeed.

## Change

Treat both overload codes as retryable transient failures. Reuse the existing
bounded same-account retry for direct streams and the existing single replay
before visible output for pre-created WebSocket/HTTP-bridge requests.

## Safety

Do not replay after visible output, do not replay continuations without the
existing retry-safe contract, and do not add model aliases or fallback models.
