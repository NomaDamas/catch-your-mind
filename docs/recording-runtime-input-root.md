# Fixed runtime input root for recording ABC

This amendment defines the missing owned input transport for #270. It requires
independent review before runtime activation. Native channel bootstrap2 and the
coordinator bootstrap1 keep their exact approved JSON keys and versions.

The only child command is the parent-owned interpreter running the built-in
`-m benchmarks.recording_arm --runtime-inputs ABSOLUTE_ROOT`. The argument names
a private input directory created and owned by this invocation's parent, not a
module, executable, command, endpoint, or import path. The parent supplies no
other application command, shell expansion, dynamic entrypoint, or model/import
selection environment configuration. The only transport environment additions
are the already frozen native/coordinator FD keys; approved explicitly named
credential forwarding remains governed by its frozen adapter policy. No search
path, executable selection, or implicit endpoint/model environment is added. The root remains owned and open until the child and all owned
read threads are joined and the process reaped. A child never removes inputs.
Only the creating parent may remove its own generated directory afterward.

The parent creates the private root with mode0700 and retains its owned FD.
The child walks ABSOLUTE_ROOT component by component from an owned `/` FD,
opening EVERY directory with O_DIRECTORY|O_NOFOLLOW|O_NONBLOCK. A single
O_NOFOLLOW open of the full absolute string is insufficient because it could
follow an ancestor symlink. All retained FDs are non-inheritable except the
explicit already approved transport descriptors. Every descendant
path is walked relative to that owned FD, with nofollow/nonblocking directory
opens for intermediate components and nofollow/nonblocking regular-file checks
for files. No symlinks, devices, sockets, FIFOs, empty components, dot/dotdot,
absolute descendants, or path rebasing are accepted. Directory and file identity
are retained through each read. Close owned FDs and join actual reads on every
failure or repeated cancellation before reporting resource closure.

The exact metadata inventory is:

- `runtime/source-bundles.json`, `runtime/policy.json`, `runtime/latency.json`,
  `runtime/assets.json`, `runtime/plan.json`, `runtime/collection.json`,
  `runtime/scopes.json`, `runtime/instrumentation.json`;
- `recordings/NN/manifest.json`, `recordings/NN/tasks.json`,
  `recordings/NN/profiles.json` for the original C2 recording ordinal NN (00..31);
- `invocations/NN/execution.json` for the original C2 invocation ordinal NN
  (00..95), with no relabeling, omitted invocation, or additional row;
- optional `runtime/accounting.json`, `runtime/opportunities.json`,
  `runtime/exposure.json` exactly when U2 requires K2/G/E2. U1 rejects these;
- `configurations/NNN.json`, `responses/NNN.json`, and `budgets/NNN.json` are
  separately admitted fixed-index metadata assets only when referenced by the
  exact asset inventory or U policy. Each is parsed by its exact approved
  configuration/response/budget grammar; no arbitrary JSON executable options.

Every JSON metadata file has exactly canonical ASCII JSON bytes plus one LF,
using the same canonical serializer as C2, with no duplicate keys or trailing
bytes. `Ref` means the approved exact `{path,file_sha256,bytes}`. Each path is
one of the fixed paths above, and its byte hash/size refer to original bytes,
not merely a parsed canonical object. The reader checks regular-file sizes and
reserves the entire joint metadata byte budget BEFORE parsing any document.
The metadata file-byte bound does not assert an equivalent Python heap bound.
Before parsing, reserve additional owned parse workspace of128 times the total
metadata file bytes, covering lexical inspection, decoded trees, canonical
copies and frozen receipt storage, with an independent256MiB workspace cap.
Perform bounded lexical tree/depth/node checks before JSON conversion. This
joint reservation may refuse a bundle below the file-byte ceiling and remains
held until the last owned metadata/receipt consumer closes.
All distinct input metadata, including all original bundles and execution
rows, jointly fit16MiB. Individual files fit 16MiB; source-bundles.json,
execution.json, policy.json, latency.json, scopes.json and instrumentation.json
additionally fit their existing approved tighter grammar limits (64KiB for
source-bundles.json and execution.json). Assets inventory fits1MiB; each config
and budget fits64KiB; fixture response inventory fits1MiB. These are joint
admission restrictions: the standalone source64MiB manifest ceiling does not
promise it fits this runtime. Source payload and checkpoint byte reads are
streamed under their separate approved joint preflight budgets, never parsed
as JSON or included as metadata merely to bypass these checks.

The source-bundles index has exact keys:
`{schema_version:1,kind:'recording_runtime_input_sources',collection_sha256:H,
runtime_policy_sha256:H,recordings:list}`. A row has exactly
`{recording_id:ID,recording_index:N,manifest:Ref,tasks:Ref,profiles:Ref}`.
There are exactly 1..32 rows, one in original C2 recording order. Paths are
exactly the three `recordings/NN/` names above for that ordinal. Ref sizes and
file hashes must equal canonical(original bound document)+LF. Thus index
identity is exactly derived from C2/U and those already bound originals, with
no unbound row, task alias, alternate filename, or caller-selected file.

Before any provider/client activation, parent and child independently verify:

1. The coordinator bootstrap execution hash equals the exact selected
   execution declaration, its invocation ordinal selects the original C2 row,
   and all U/C/Q/I/asset hashes agree with that declaration. The native bootstrap
   paths must resolve to the SAME owned original metadata documents for its
   selected recording; different bytes or path aliases reject.
2. U's hash equals coordinator bootstrap and C2.runtime_policy_sha256. U binds
   exact P/L and every original manifest/tasks/profiles document. C2 binds the
   same original recording IDs/order, source/tasks/profile hashes and original
   task IDs. Every P task belongs to exactly one original recording and keeps
   its identical input across ABC. No task is substituted for a recording.
3. The input index equals the unique derived inventory above, every file SHA,
   length, canonical representation and original semantic SHA agrees, and all
   source/profile/task validations run before creating a runtime admission
   receipt. Full collection source/native/artifact preflight is mandatory at
   parent; child validates all owned originals available through this root.
4. Each source payload path remains relative to that original recording's
   separately owned `recordings/NN/payload/` directory. Original manifest paths
   and hashes are unchanged. Task input is portable JSON question data only;
   it cannot name host paths, loaders, code, or files. Explicit authorized
   checkpoint/Python assets remain pinned read-only files and use the existing
   reviewed asset/dependency validation, not this root as an import mechanism.

Input admission produces an issuer-guarded immutable receipt containing exact
U/C/Q/I/L/assets and input-index identities plus detached frozen declarations.
It is process-local and cannot be supplied by JSON or inherited as authority.
Public legacy native entrypoints remain strict Q1/I2/legacy profiles. NEW
runtime entrypoints revalidate the complete owned inputs and use private shared
native machinery with their issued receipt; no public validator callback or
boolean bypass permits an arbitrary profile or protocol version. U1 is always
structural-only. Prospective U2/Q2/I3 requires independently validated E2/K2/G
and never makes prior Q1 runs numerically eligible.
