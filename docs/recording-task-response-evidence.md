# Retained actual task response evidence

The fixed task executor retains an accepted actual TextContextCalls SDK response
before declaring a task result available. This closes the native raw-result join;
answer text alone cannot authenticate usage or the native result digest.

For original task index n (0..63), the sole additional fixed sidecar is
`requests/request-NNNNNN.json`, with ordinal n and at most 65536 canonical ASCII
JSON bytes including LF. Exact fields are `{schema_version:1,
kind:'recording_semantic_response',execution_sha256:H,task_id:ID,input_sha256:H,
scope_index:n+1,operation_instance:H,native_raw_result_sha256:H,sdk_result:object}`.
`sdk_result` is the detached actual accepted TextContextCalls return value, with
its existing exact status/accepted/text/usage/actual_cost/source_record_id/
source_record_sha256/prompt_sha256/provider/model_revision/interpretation/
usage_verified/quality_validated fields and existing SDK bounds. No caller
response or reconstructed model output is accepted. Native raw result digest
is exactly H({text:sdk_result.text,usage:sdk_result.usage}).

The full original runtime join requires exact execution/task/input/scope/native
instance, prompt/provider/revision, source registered snapshot record and native
raw result digest equality. Every accepted SDK response, including a late response
retained in a failed task, has exactly this sidecar; no other request-sidecar row
is admitted in this initial runtime. Failed calls with no accepted SDK response
retain their original native failure and do not manufacture a response. The
sidecar is sealed before the task result and parent validated receipt; its bytes,
parse workspace and copies count against the existing joint task/runtime/parent
artifact reservations and complete lifetime accounting. It does not refresh
snapshot freshness, extend a deadline, add a model call or alter old wire formats.
