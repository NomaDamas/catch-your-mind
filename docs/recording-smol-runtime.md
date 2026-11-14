# Recording-owned local Smol lane

`benchmarks.recording_smol_runtime.open_smol_lane` opens the existing
`SmolVLMCalls` / `ProcessProvider` path for an explicitly frozen
`smolvlm_process_v1` adapter and `smolvlm_sentinel_v1` scheduler. It uses the
fixed SmolVLM2-500M model and chronological-image prompt from the SDK. It does
not substitute the custom question used by `recorded_visual_v1` or accept a
text-answer/strong-model role as an equivalent route.

The caller first admits owned runtime inputs and verifies the current Python
installation's dependency inventory. The lane checks the adapter's implementation
hash against `implementation_sha256()`, the exact model/provider/revision,
required dependency versions, the original worker-configuration file hash, and
explicit checkpoint/tokenizer assets. Its initial supported Python asset must
have the exact current `sys.executable` path, bytes and size. A separate
virtual environment is refused even if its interpreter shares an inode; parent
installation evidence does not verify another environment. No environment,
dependency, tokenizer or model installation is performed.

Asset hashing uses bounded, nonblocking, no-follow regular-file descriptors.
The verified checkpoint, tokenizer and interpreter descriptors remain owned until
worker cleanup completes. The current interpreter’s alias is resolved for verification, and the exact
verified canonical target is also used for spawning. Retargeting the alias
after admission cannot select a different executable. A symlink-dependent
virtual environment is refused because canonical execution could select its
base environment; the initial profile supports base environments and current
virtual environments whose executable path is already canonical.
Configuration is detached before asynchronous admission. Cancellation joins the
asset-read thread, or the actual SDK worker's shutdown and reap, before releasing
those descriptors. Missing assets or unsupported dependencies fail explicitly.
The native model still validates its complete graph and tokenizer on startup;
file hashes alone are not trained-model or resource-capacity validation.

The returned owner exposes `.adapter` (actual `SmolVLMCalls`), `.worker` /
`.backend`, `.close()`, and `.entry_for_decision(decision_sha256)`. Entry lookup
uses the recording owner's exact binding/request lookup; it returns no entry
before actual execution and never infers an entry from the latest call.
`prompt_sha256(timestamp_ms)` reports the fixed model prompt identity.
`release_entry` retains no additional wrapper cache and does not delete original
native evidence. Capture/record/pixel validation occurs in the actual SDK call;
this is not the HTTP PNG capture-correlation interface.

Tests use tiny explicitly synthetic asset/installation metadata and an owned
subprocess with a fixture predictor. They cover actual SDK admission, execution,
publication, original native entry lookup, cancellation and process reaping, plus
asset mutation/FIFO/symlink rejection and an actual-spawn alias-retarget
regression. The latter uses non-model assets that the real worker rejects and
checks that an unverified executable marker never runs. They do not establish trained Smol
accuracy, model installation, sustained realtime performance or cost savings.
