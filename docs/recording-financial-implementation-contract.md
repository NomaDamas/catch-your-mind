# Recording finance v2 implementation clarifications

This normative implementation amendment accompanies the approved #270/#274
three-document contract. It closes literal path, object and digest-order gaps
found while implementing that contract. It requires independent review before
numeric activation. It does not authorize real financial adapters, lower the
original statistical minimum, change the 20% cost or 10% p95 targets, or make a
structural Q1 run retroactively numeric eligible.

## Exact limits and immutable artifact paths

K2.limits has exactly the nine E2.limits keys, with exactly the same frozen
values: max_groups32, max_arm_runs96, max_original_tasks1000,
max_cost_lines131072, max_cost_pages1024,
max_financial_metadata_bytes67108864, max_source_document_bytes67108864,
max_output_bytes16777216, max_total_bytes4294967296. No stream or writer resets
these collection bounds.

The additional fixed writer filenames are:

- `ledger/lifetime-NNN.json`, `ledger/coverage-NNN.json`,
  `ledger/cost-NNNNNN.json`, `ledger/closure-NNN.json`;
- `ledger/closures.json`, `ledger/financial-inventory.json`,
  `ledger/ledger.json`, `ledger/checkpoint.json`;
- `ledger/validity-NNNNNN.json`, `ledger/late-NNNNNN.json`;
- `financial/evidence/evidence-NNNNNN.json`,
  `financial/finality/finality-NNNNNN.json`,
  `financial/settlements/receipt-NNNNNN.json`.

All ordinals are writer-owned, contiguous within the declared inventory and
never selected by JSON. A standalone evidence file contains exactly the same
FinancialEvidence object as its embedded evidence-page row; operation.evidence
references that standalone immutable file. A finality file contains exactly
SyntheticFinality. A settlement file contains exactly ControllerSettlement.
These retained reference copies consume actual bytes; they are not additional
original invoice lines, claims, or owners.

Ledger2.closure references `ledger/closures.json`, exactly
`{schema_version:1,kind:'recording_financial_closures',closures:list[Ref]}`.
There are exactly all original arm streams, at most96, each one referring to its
single per-stream ClosureEvidence. No failed run may omit its closure row.

FinancialIndex keeps its approved exact wire shape. To permit more than one
lane's cost_line_inventory, filenames use monotonically allocated global file
ordinals per section and page/index category. Each individual chain's
page_ordinal is local0..N-1; its first previous hash is null. Its Ref filenames
are unique and contiguous in their own allocated range, and the local chain
ordinal is not substituted for the global file ordinal. Every nonfinal index
page still contains128 refs. A reader follows exact pinned Ref/hash chains,
checks fixed filename patterns and uniqueness, and does not assume every
independent lane index starts at file000000. Cross-index aliases are rejected.

FinancialEvidence.quantities is exactly the singleton mapping from its original
SyntheticInvoice line.component_id to that line.source_quantity; K2 then verifies
that component's exact conversion/rate. F1 does not split an original line into
multiple components or invent suffix line IDs.

## Acyclic finality

Initial F1 FinancialEvidence.finality_evidence_sha256 is null. This is mandatory,
not unknown finality accepted as complete. The original line is issued and
authoritatively settled before downstream finality exists. SyntheticFinality
then hashes the complete operation rows (including their original evidence and
actual settlement refs) and complete financial lane rows (including exact cost
line inventories). Requiring those earlier evidence rows to hash this later
finality would create a digest cycle.

ClosureEvidence.external_finality_refs and FinancialInventory.finality provide
the mandatory downstream finality join. The finality must cover every original
invoice document/operation/lane, all resource windows and actual operational
closure. The validator rejects a falsely closed inventory, a missing finality,
or an unknown real provider. No evidence file is rewritten to add a backward
pointer after sealing. A future F version may define another acyclic link shape.

## Frozen synthetic charge scenario and actual SDK settlement

The frozen fixture response's `synthetic_receipt_sha256` is the canonical object
digest of this exact SyntheticChargeScenario, never a future invoice file hash:

`{schema_version:1,kind:'synthetic_recording_charge_scenario',evidence_class:'fixture',authority:'gamst.synthetic_invoice_fixture_v1',adapter_id:ID,provider:ID,revision:ID,account_scope:ID,invoice_id:ID,line_id:ID,stream_id:ID,component_id:ID,resource_id:ID,lane_id:ID,operation_key:{invocation_ordinal:N,binding_index:N,call_ordinal:N},source_quantity:Rational,quantity:N,billed_atomic:N,currency:ID,currency_unit:ID,pricing_revision:ID,components:object}`.

It has the approved F1 identifiers, bounds, conversion and exact one-original-line
policy. Components are a nonempty exact subset of
input/output/cache_read/cache_write/media/text_consumer/local_compute/other,
each0..10**18, and sum exactly billed_atomic. Unit/pricing revision must match
the actual controller's frozen CallBudget. All fixture names remain explicitly
synthetic. Scenario IDs cannot create new real invoice authority.

The runtime registers `(request_id,request_decision_sha256)` on its known
RecordingSettlementRecorder before execute, while the original pending request
exists. PreparedCall.invoke receives the actual SDK-issued NativeEntryBinding;
`bind_entry(binding)` resolves that exact decision hash to the original request,
verifies actual dispatched decision/provider/model/prompt/role, and captures the
immutable original instance/invocation/binding and per-binding actual-entry rank.
It never uses ambient currenttask, timing association or model-echoed IDs.

`generate_synthetic_receipt(request_id,scenario,expected_scenario_sha256=...,
adapter_inventory=exact_F_bytes,expected_adapter_inventory_sha256=...)` generates
the downstream original synthetic invoice with actual current service-event
monotonic time and exact frozen scenario identity/quantities. It issues a private
FrozenRecordingReceipt only after strict source bytes, adapter grammar, original
line, claim, actual owner and charge have been validated. The runtime persists
those exact original source/evidence bytes and invokes the same actual
controller.settle transition. Known charge before a failed result is retained;
late receipts can use the opaque binding retained after sensory deletion.

CallController.settle's optional recording_receipt must be that SDK-issued object
owned by its bound recorder. It validates before the budget transition and
records the actual settled budget result under the controller lock before
retiring a finished request or deleting detached financial lookup. Overruns
remain actual policy failures, never clamped. Ordinary settle behavior is
unchanged. Issuance, declared269 attachments and model usage alone do not settle
a request. No receipt token can be replayed or rebound.

The recorder exposes the exact ControllerSettlement and actual transition hash.
The original synthetic invoice and financial evidence are bounded retained
artifacts; their generated bytes count toward the financial/global budgets.
Financial hash integrity does not authenticate a real external receipt.

## Typed runtime-to-financial join

The complete runtime validator issues frozen `FinancialRunView` through its
internal issuer. This is not a JSON deserializer or a generic success attestation.
Its exact fields are:

`execution_sha256:H,run_inventory_sha256:H,invocation_ordinal:0..95,stream_id:ID,recording_id:ID,arm:ABC,source_manifest_sha256:H,source_coverage_sha256:H,source_comparable:bool,task_row_inventory_sha256:H,clock_domain:ID,clock_consistent:bool,activation_started_ns:N,child_spawn_started_ns:N|null,playback_anchor_ns:N|null,source_finished_ns:N|null,child_cleanup_finished_ns:N|null,process_reaped_ns:N|null,parent_resources_closed_ns:N|null,operational_closed:bool,external_work_closed:bool,worker_inventory_sha256:H,native_terminal_sha256:H|null,controller_settlement_inventory_sha256:H,semantic_unknown_instances:tuple[H],violations:tuple[enum]`.

Only activation_started_ns is mandatory among lifecycle times; every unknown
actual milestone remains null. A failed run still gets its typed view after
complete verification of the durable known prefix and explicit unknowns; it
cannot get source_comparable/operational_closed merely from child termination.
source_coverage_sha256 is the canonical coverage object's digest; the retaining
Ref's file_sha256 separately hashes exact bytes plus LF. native_terminal_sha256 is the original native terminal.json file SHA256 over its exact canonical bytes INCLUDING the terminal LF, never the digest of the parsed object. The typed index's terminal/context and original invocation must all match even when no operation entered.

Violation enum is exactly source_incomplete,clock_discontinuity,
operational_incomplete,external_work_unknown,reservation_overrun,
missing_native_prefix,unsupported_entry_coverage; unique, at most one of each.
semantic_unknown_instances is a unique bounded inventory of the native
historical unknowns, not an instruction to clear current liability. A later
authoritative recorded settlement may resolve one financial operation without
rewriting that immutable native history.

The financial reader consumes only the typed #269 ValidatedRecordingIndex and
public iter_canonical_inventory. Every actual entered operation remains once,
including failed, cancelled and discarded work. Released/no-entry reservations
do not consume call ordinal. The same-host parent lifetime and all complete
actual costs remain separate from original exposure D.

## Numeric output and current validity

Only prospective U2/C2/Q2/I3 can enter the numeric reader. Q1/nullR is immutable
structural history. Financial synthetic completion can produce fixture-only
mathematical eligibility. All measurement/authentic receipt/isolation/actual
model/worker backend truth flags remain false absent a separate recognized audit.

The quality/latency helper preserves original task order, original paired
bootstrap seed/repetitions, critical facts, nonnegative quality difference and
p95 ratio upper<=9/10. It consumes actual parent receipt latency/failure floors
and external original assessment, independently of cost. It never supplies
invented usage0 or resourcecost to a legacy priced comparator.

The cost statistic uses ALL original recording groups and complete lifetime
money exactly once; canonicalA is counted once. A missing quantity is unknown,
not0. Current export requires mandatory sealed genesis, the complete immutable
validity chain and an explicitly externally reviewed checkpoint digest. A late
validated original charge invalidates future exports without rewriting prior
ledger/report bytes. Neither a timeout nor a zero-notice file proves finality.

## Actual worker inventory and lifecycle lanes

FinancialRunView.worker_inventory_sha256 is the canonical object digest of the
complete actual public #269 worker_interval rows for that invocation, sorted by
(work_ordinal,worker_ordinal), with every field retained. Empty digest([]) is
valid only when the actual inventory has no owned worker interval; it does not
prove absence of external resources or costs. The full inventory hash is checked
against the actual typed native reader before any financial completion.

K2 observed_lifecycle.lifecycle_binding_id resolves uniquely to the frozen C2
arm provider_bindings binding_id and its exact binding_index. That lane's
work_inventory_sha256 hashes the complete actual worker_interval subset with
matching binding, in the same order and exact row grammar. A whole_lifetime
lane instead carries the full run.worker_inventory_sha256. Neither hash is the
resource_intervals Ref file hash. Every selected interval must remain within
the declared resource window and its entire attributable work must be covered
by the same lane's original cost lines or explicit incomplete counters. An
unknown ended_ns, absent declared binding or clock mismatch remains incomplete.
Overlapping actual lifecycle work is not silently summed into invented elapsed
time; the original isolated lane meter covers its full observed resource window.

## Failed arm without a committed native terminal

The original native terminal hash is null only when the actual child/native
protocol did not produce a validated terminal. Such a view must include
missing_native_prefix and must have source_comparable, operational_closed and
external_work_closed all false. Its aligned native index input is exactly null;
no caller-supplied prefix or fabricated empty ValidatedRecordingIndex is accepted.
The parent retains its actual unvalidated prefix/counters separately. Its worker
inventory digest cannot certify complete work and is never treated as digest([])
proof that no work entered. Every frozen failed arm remains in the original
stream/closure inventories, and its full cost stays unknown regardless of any
known received money.

Supported original synthetic invoices/evidence for that arm remain retained and
counted once in known money. An operation key that cannot resolve because that
arm has no valid native terminal may retain its original opaque owner_instance
only as an unverified-prefix charge; it cannot create a verified financial
operation row, settled controller claim or finality/completion. Unknown-prefix
charges do not authorize successful closure or make missing native operations
zero. For an arm with a valid terminal, the unchanged strict bijective actual
entry join is mandatory and a missing operation key is rejected.

## Retained join memory and orphan inventories

The reader's financial/native retained join index has one collection-wide
128 MiB cap. It conservatively charges actual retained Python object sizes,
including each row/reference/container allowance before insertion; shared
references may be charged more than once. One bounded decoded page remains
working memory. Source-document and metadata byte caps remain independently
mandatory and shared ArtifactBudget charges every written byte. Exceeding the
index cap refuses that joint combination; it does not drop entries, restart a
per-arm budget or advertise every independent maximum as jointly supported.
Cross-index page/chain aliases and every retained original financial file
omitted from the declared inventories are rejected.

## Actual controller settlement inventory

FinancialRunView.controller_settlement_inventory_sha256 is the canonical object
digest of all actual SDK-issued RecordingSettlementRecorder.receipts() snapshots
for that invocation, sorted by the exact ControllerSettlement key instance.
The concrete FinancialFixtureReceiptRouter exports the actual object inventory
and digest; the runtime joins its retained sidecar/provenance before issuing the
view. The financial reader requires the exact complete matching settlement
inventory for every valid-native run. A JSON attachment alone cannot supply
this typed authority. Empty digest([]) means actually no authoritative receipt;
it does not clear any native historical unknown or real external liability.

The recorder belongs to one invocation, although several predeclared bindings
may use the same controller within that invocation. Router contexts, binding
ownership, scenario bytes and adapter inventory freeze before activation. The
router calls actual settle before the fixture response delay/decoder; generated
source/evidence files and authoritative settlement files all consume shared
artifact bytes. Any later file failure retains the actual charge and fails the
run, without an optimistic published receipt.

For a known fixture receipt after earlier unknown entries, bind_entry may accept
the actual owned FixtureCompletion call_ordinal explicitly. This ordinal is
monotonic, at least the next known binding ordinal and no greater than the
actual native global entry_ordinal. It is never model-reported or inferred by
clock. The reader independently reconstructs its exact per-binding rank from
the complete native sequence and rejects any mismatch. Ordinary bind_entry
without that argument preserves contiguous observed binding behavior.
