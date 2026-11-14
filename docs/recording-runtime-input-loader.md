# Owned recording runtime metadata loader

`OwnedRuntimeInputs.open(root, expected_execution_sha256=...,
invocation_ordinal=...)` reads only the fixed input inventory from the approved
runtime input-root contract. It activates no providers, imports no caller code,
loads no model/checkpoint, and supplies no financial finality.

The loader uses one owned read/parse thread. It walks every absolute directory
component without following symlinks, requires a private mode0700 root, bounds
all fixed metadata sizes before JSON conversion, and retains a128-times-byte
parse-workspace quota until close (maximum256MiB). This quota is implementation
ownership, not global joint-memory certification: parent preflight must charge
the maximum before opening and combine the held workspace with other owned
memory. Actual payload reads/hashes, dependency/asset byte certification,
native/source/artifact admission, and provider activation remain separate.

The immutable issuer-guarded `.receipt` exposes detached documents, all original
source bundles, and selected native declarations; `.identities` names exact
execution/U/C/Q/I/L/assets/input-index object hashes. The receipt becomes unusable
on close. Copies returned by its methods belong to the trusted caller and must
remain in the caller's own admitted ownership. `duplicate_payload_root(id)`
returns a caller-owned non-inheritable duplicate FD, never a borrowed FD to close.
The complete original payload path inventory and regular-file sizes are checked;
OwnedCaptureSource independently checks actual original bytes before replay.

Before activation, call `.validate_native_paths(paths)` with the exact original
native bootstrap paths. It checks both fixed absolute names and retained file
identity/original bytes, rejecting copied-file and hard-link aliases. This
synchronous bounded check belongs to startup; a caller performing it in an owned
thread must join that thread before closing the input owner. The loader's own
open/close path joins its read thread despite repeated cancellation.

U1 rejects every prospective numeric input. U2 requires exact K2/G/E2/F input
files and the separately validated Q2/I3 entrypoint; prior structural inputs are
never upgraded. The F fixed-path addition must receive the pending independent
contract approval before runtime activation. Every invocation and every original
recording remains present, including20-recording synthetic feasibility fixtures;
these fixtures establish structural admission, not real recording independence,
model quality, monetary acceptance, or cost/latency savings.
