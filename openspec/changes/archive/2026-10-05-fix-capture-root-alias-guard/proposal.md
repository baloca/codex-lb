## Why

On macOS `/tmp` resolves to `/private/tmp`. The isolated Codex body capture
guard resolves its destination but compares it to unresolved forbidden roots,
so its existing temporary-storage refusal fails for this equivalent path.

## What Changes

- Resolve forbidden roots before comparing them with the resolved destination.
- Cover a symlinked root with a host-independent regression.
- Preserve the existing storage policy and production proxy behavior.

## Capabilities

### Modified Capabilities

- `compatibility-tooling`: refuse temporary capture storage through equivalent root aliases.

## Impact

Only the isolated capture utility and its tests change. No live capture is run.
