# Original recording run validation

`validate_recording_run(directory, *, documents, source_bundles,
invocation_ordinal, parent_native_inventory, activation_started_ns)` is a
synchronous, bounded join invoked after the owning parent imports and closes the
original run artifacts. Its `NativeRunInventory` argument must be the actual
parent-issued immutable token. A JSON copy cannot supply that authority.

The validator checks the original execution and declarations, original source
journal and mapping records, native entries and acquired capture timing,
accepted publications, frozen Context and raw SDK responses, original task
receipts, perception opportunities, SDK delivery counters, and actual lifecycle
observations. Actual SDK controller settlements come only from the original
source writer's bounded inventory and its journal/terminal bindings, joined to
original F1 documents and frozen scenarios. Hash integrity does not authenticate
real invoices, remote GPU closure, or model quality.

The returned `ValidatedRecordingRun` has a private issuer and detached read-only
properties: `execution`, `run_inventory`, `task_receipts`, `financial_values`,
`source_coverage`, `task_rows`, `controller_settlements`, and
`controller_settlement_inventory_sha256`. `native_index` is the actual sealed
native reader result; it is `None` for an original missing terminal. The finance
owner adds the original collection execution-inventory digest before issuing
its financial view. It cannot replace the source-owned settlement digest.

Expected failed or incomplete arms retain their original task receipts, known
charges, missing timestamps, and explicit violations. Missing native evidence
never proves zero work. Corrupt originals, changed hashes, cross-task evidence,
unsupported ownership, and unsafe filesystem aliases are rejected. The join
uses at most128MiB of conservatively charged retained working indexes; source
records use compact arrays and source journal events are streamed.

Before activation, `preflight_recording_run_validation(declarations, execution,
publication_rows=...)` returns conservative `peak_workspace_bytes` and
`retained_workspace_bytes` bounds. The coordinator adds its owned input workspace
and all previously retained run bounds; neither per-run admission nor sequential
execution resets the collection total. The issued run exposes actual
`retained_workspace_bytes`. Its `runtime_completeness` is `complete` only when
original source exposure, clock, owned cleanup, and every original task answer
are complete. Unknown external billing remains separate from this structural
state.

No legacy numeric format or acceptance gate is changed. Synthetic F1 evidence
remains synthetic; complete structural runs do not establish real savings or
quality acceptance.
