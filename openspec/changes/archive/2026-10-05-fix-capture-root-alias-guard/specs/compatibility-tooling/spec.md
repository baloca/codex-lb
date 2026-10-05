## ADDED Requirements

### Requirement: Isolated capture storage checks canonical root paths

The isolated Codex body capture utility SHALL refuse destinations under
configured forbidden storage roots after resolving both the destination and
each root. An alias of a forbidden root SHALL enforce the same refusal.

#### Scenario: Temporary storage root is a system alias

- **GIVEN** a configured temporary root resolves through a filesystem symlink
- **WHEN** a capture destination lies under the target of that root
- **THEN** the utility refuses the destination with its storage-policy error
- **AND** no capture process starts
