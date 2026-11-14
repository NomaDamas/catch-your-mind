# Owned runtime synthetic charge inputs

This narrowly extends the approved synthetic F1 runtime input boundary. It
does not introduce real settlement, new models, another numerical gate, or
retroactive eligibility for structural U1 recordings.

U2 inputs additionally contain the fixed file `runtime/charge-scenarios.json`.
It is canonical ASCII JSON with exactly one terminal LF, at most 65536 bytes,
and exact fields `{schema_version:1,kind:'recording_synthetic_charge_scenarios',
scenarios:list[SyntheticChargeScenario]}`. The list contains at most256 bodies,
including bodies for all original invocations. U1 rejects this file. The complete
file and its bounded parse workspace count against existing original-input,
retained metadata and collection artifact limits. The independent response-row
limit stays unchanged; jointly unsupported combinations are refused before
activation. This is not a full-hour capacity promise.

Each body uses the already approved shared SDK SyntheticChargeScenario grammar.
Its canonical object digest must equal a non-null synthetic_receipt_sha256 in
the original frozen fixture response inventories referenced by U2 adapters.
The two complete hash sets must be equal; duplicates, extras and omissions
are rejected. A body also resolves its exact original invocation, semantic
lane, C binding index and call ordinal, applicable K stream/component/resource
lane, original F1 adapter/provider/revision, and original monetary currency,
unit and price revision. It cannot target a real completion adapter or use an
event scenario to settle an interval meter. The inventory's hash binding is
acyclic: frozen response rows contain scenario hashes, not future invoices.

The exported preactivation parser is
`validate_runtime_charge_scenarios(value, *, runtime_policy, collection,
responses, accounting_policy, financial_adapter_inventory)`. `responses` is
the complete original list of fixture response documents. The return value is
a tuple of detached canonical scenario bytes ordered by digest. Parsing never
constructs a model, controller, invoice or settlement.

`open_fixture_receipts(documents, execution, controllers, semantic_bindings,
native_context, root, artifact_budget, *, retain_financial_documents)` consumes
the original owned input receipt's detached documents and original execution.
`controllers` maps original controller IDs to their actual SDK instances;
`semantic_bindings` maps every original semantic lane ID to its actual C binding
index. The helper creates one SDK recorder per actual controller, so small and
strong lanes sharing a controller also share the same immutable recorder.
The already-created owned output root uses the actual shared ArtifactBudget.
Explicit financial retention is required. No endpoint, environment variable,
model loader or arbitrary callback is activated by this helper.

The returned owner exposes its actual router, actual recorder map, retained
original references and detached actual SDK settlements. Runtime request
registration occurs before SDK execution; the router produces an original F1
invoice only after the actual SDK entry callback and settles through the SDK
before response waits. Unknown fixture rows remain unknown. Owner.close only
closes its file owner after the runtime joins callbacks/controllers; it does
not assert that native work, source coverage or financial resources are closed.

Parent finance finalization consumes only the new typed full runtime join.
Execution inventory and actual original controller-settlement inventory hashes
are added to its immutable financial values; process status or caller-provided
attachments cannot issue a successful FinancialRunView. Every missing terminal,
failed arm and known original charge remains in the required collection.


The initial execution inventory is sealed before assessment, with assessments=[]
and every original execution/run Ref in frozen invocation order. Assessments
refer to this immutable inventory digest. Later assessment references belong to
separate reconciliation/result artifacts; the sealed inventory is never rewritten
or projected. `finalize_financial_runs(validated_runs, execution_inventory, *,
documents)` accepts only all original typed runtime joins and checks those exact
original execution/run file hashes and declaration identities before issuing the
financial views. `reconcile_runtime_finance` feeds those views, actual validated
native indices and parent receipts into the existing strict lifetime and paired
quality evaluators. Original financial artifacts and externally reviewed ledger,
assessment and current validity checkpoint remain explicit inputs; completing a
process cannot generate external financial finality or scoring review.
