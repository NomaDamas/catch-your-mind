# #270 local HTTP visual request mapping — proposed exact amendment

This amendment changes only `local_chat_completions_v1`'s wire-message mapping.
The upstream adapter enum/configuration, one-shot entry/admission, no retries,
strict response grammar, explicit local endpoint and unknown financial status
remain unchanged. It requires independent approval before implementation.

Actual `VisualContextCalls` produces a completed SDK request with exactly one
top-level `images` entry, separate from its two text `messages`. Sending those
text messages unchanged would omit the captured image. No model may be described
as having received pixels when this happens.

The built-in transport accepts the actual completed SDK Text/Visual request,
not caller-generated image instructions. Text requests have no `images` key:
copy their SDK messages unchanged. Visual requests have exactly one image and
exactly the image entry keys `mime_type`, `data_base64`, `sha256`,
`source_frame_sha256`, `capture_ms`, `shape`. Require `mime_type='image/png'`,
strict canonical ASCII base64 with no whitespace and at most8MiB decoded bytes,
lowercase64hex digests, original integer capture_ms0..2**53-1 and plain shape `[H,W,3]`
with H32..1080, W32..1920. The SHA256 of the actual decoded PNG must match
`sha256`; its PNG signature/IHDR dimensions must equal W/H. Decode the bounded
lossless PNG using already-installed OpenCV into a plain uint8 HWC BGR array;
its exact shape must match and existing `smolvlm_frame_sha256(decoded_pixels)`
must equal `source_frame_sha256`. The runtime join must further bind that digest
and capture_ms to the actual owned original CapturePacket/SDK frame record.
Lowercase digest syntax alone never proves this relation. The additional
decoded-array bytes and any decoder thread are explicitly reserved and owned;
join the thread despite repeated cancellation before releasing its reservation.
No model/decoder install is implicit. The SDK already owns encoding from the
actual validated frame; these checks do not independently
authenticate physical pixels or server model execution.

For the single final SDK user message only, replace its nonempty string content
with exactly this ordered array:

```json
[
  {"type":"text","text":"<original SDK user content, byte-for-byte>"},
  {"type":"image_url","image_url":{"url":"data:image/png;base64,<actual SDK data_base64>","detail":"auto"}}
]
```

All message roles, order, system content and other fields remain unchanged.
Require exactly the SDK's two messages, system then user, each exactly
`role,content`; reject unsupported/multiple images, malformed images, arbitrary
preexisting multipart content or another image transport. No extra prompt,
image selection, inference attempt, tool call or source retimestamp is added.
The actual wire body remains exactly `model,messages,temperature,stream`, with
the frozen model_id, temperature0 and streamfalse. Canonical wire bytes have no
LF and are bounded to16MiB including base64 and encoding overhead, separately
reserved from the SDK request/PNG buffers.

Preserve the actual complete SDK request's prompt_sha256 unchanged. Separately
hash the actual mapped canonical HTTP wire body into wire_request_sha256.
Transport provenance binds both and the actual one-shot callback entry; neither
hash substitutes for the other. Provider request ID extraction remains ONLY
the optional validated response body.id, with no header fallback.

Focused acceptance must invoke the actual `VisualContextCalls` encoder and
actual async HTTP transport against an owned local server. Verify exactly one
POST, unchanged original text/system, one matching original PNG/image digest,
different correct SDK/wire hashes, accepted strict response, and cancellation
cleanup. Text calls must remain unchanged. A valid64hex but wrong source digest
and valid different PNG pixels must each reject, as must wrong image/hash/shape or malformed
response must be entered failures with retained unknown cost; no salvage/retry.
