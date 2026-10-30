# Retry sequenced output-free capacity failures

## Why
Native Codex WebSocket responses carry sequence numbers on their lifecycle prelude. The blanket sequence guard surfaces a transient capacity rejection even when the accepted response produced no model output. On the deployed instance, output-free overloads therefore bypass the existing one-shot accepted-response replay.

## What Changes
Permit the existing one-shot capacity-terminal replay after a sequenced, output-free prelude. Suppress both repeated lifecycle prelude events before applying the sequence regression check; preserve original numeric values and fail closed if a replacement event does not advance. Transport-close, quota, output, ownership, admission and settlement rules stay in force.

## Impact
Owning capability: responses-api-compat. No schema or setting change.
