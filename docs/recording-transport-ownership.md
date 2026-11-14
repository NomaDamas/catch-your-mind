# Recording completion transport ownership amendment

This finite #270 interface uses actual SDK `BoundCompletion`/`PreparedCall` and
actual observer-issued `NativeEntryBinding`. It cannot create entry evidence
from JSON, certify remote GPU execution, infer money or close an external server.
It supplements the approved HTTP visual amendment with concrete preactivation
ownership and resource contracts; it does not authorize a new model or installer.

## Installed dependencies

`verify_dependencies(expected, allowed_roots=..., metadata_roots=...)` performs
synchronous bounded owned file I/O without importing selected package code.
`expected` is the frozen ordered assets `dependencies` list, each exact
`{distribution,version,installation_sha256}`. Each installation hash is SHA256
of canonical sorted-key ASCII JSON without LF for exact descriptor
`{distribution,version,files:[{path,bytes,sha256}]}`. Rows sort lexically by exact
RECORD path string. The issued immutable `VerifiedDependencyInventory.sha256`
is SHA256 of the complete ordered expected list. Raw JSON cannot issue it.

Both root arguments are explicit nonempty tuples of absolute directories;
metadata roots must lie within authorized installation roots. No importlib
metadata discovery/version/files, ZIP, egg or custom provider reader is used.
Lazy owned directory scanning admits <=32768 directory entries jointly across
selected dependencies. Only one matching canonical-name regular `*.dist-info`
directory is supported. Every path component opens through owned descriptors
with `O_NOFOLLOW`; final file opens `O_NONBLOCK|O_NOFOLLOW` and must be regular.
A RECORD path such as `../../../bin/httpx` requires an explicitly authorized
containing installation root. Device/inode/size/mtime/ctime compare before and
after reads; growth, truncation, missing files and symlinks refuse admission.

Before parsing, owned reads admit METADATA <=1 MiB, RECORD <=8 MiB. These
bootstrap reads count against the joint 2 GiB actual-read limit across selected
distributions. METADATA has <=8192 physical lines of <=8192 bytes and unique
ASCII Name/Version headers. RECORD has <=32768 physical rows, <=12288 bytes/row,
exact CSV path/hash/size columns and <=4096 UTF-8 bytes/path. Descriptor files
include METADATA and RECORD, whose final actual SHA must match bootstrap bytes.
Unique inventoried files jointly total <=32768. File contents stream through
64 KiB chunks rather than retaining the full 2 GiB.

Exact repeated RECORD path strings select one actual file. RECORD's asserted
hash/size columns are untrusted; the actual file bytes and complete RECORD are
hashed. This supports installed NumPy wheels repeating a pycache path with
different assertions. Different spellings aliasing one actual lexical path
refuse; canonical-name aliases cannot declare a dependency twice. No installed
metadata is rewritten. Missing metadata/listing remains a refusal.

The coordinator jointly reserves `VERIFICATION_WORKSPACE_BYTES` (192 MiB), owns
one verification worker at a time and joins it before activation, including
rejection and descriptor encoding paths. Callers retaining multiple descriptor
outputs separately admit them. The receipt identifies selected installed files
at preflight, not continued immutability of a writable install or authenticity
of imported code/transitive closure. Parent preflight must declare all selected
dependencies. No model, package or code is installed or implicitly selected.

HTTP requires declared httpx/httpcore/h11/anyio/certifi/idna/sniffio and matches
imported httpx version to its receipt. Visual HTTP also requires declared numpy
and opencv-python. Their actual selected files remain in the full inventory.

## Owned lanes and finite HTTP

One client per lane opens before activation. Typed `TransportCapacity` and shared
`TransportMemoryBudget` reserve workspace until owned lane close, with no hidden
queue and at most one prepared call. The conservative workspace formula is
request*8 + wire*3 + PNG*2 + decoded*3 + response*32 +16 MiB parser/object/correlation overhead
+64 KiB receive chunk +32 KiB heads; wire=min(16 MiB,request*2+1024). It covers
canonical encoding, parsed strings, image URL/base64, decode/inflate/copies and
malformed/rejected HTTP/JSON objects and retained <=16384 instance/prompt hashes,
<=256 entry objects and <=256 capture correlations. Interpreter/library resident state remains
in separate collection preflight. Independent maxima may fail joint admission.

The public httpcore network-backend wrapper buffers raw heads BEFORE h11 sees
them: <=16 KiB total, <=128 fields, one final HTTP/1.0 or HTTP/1.1 response,
exactly one decimal Content-Length within frozen response bound, no
Transfer-Encoding/interim1xx. Pre-admission reads are <=remaining head bound+1;
body reads <=64 KiB. Oversized complete heads fail before parser field-list
allocation. One connection/request closes after use; the lane client persists.
TLS uses explicit verified certifi CA bytes, without SSL_CERT_FILE/SSL_CERT_DIR
or proxy discovery. No HTTP2, redirects, retries, chunked bodies or automatic
content decompression is supported. These finite restrictions can refuse a
local server. Endpoint/model/provider/revision come only from the frozen adapter.
A named credential environment variable is read only inside actual entry and
never included in artifacts. There is no automatic endpoint or model discovery.

Strict UTF-8 JSON raw responses are <=1 MiB. A linear lexical preflight bounds
depth12 and <=8192 tokens including object keys, with bounded string lexemes,
before json.loads. Duplicate keys, nonfinite numbers and strict typed SDK tree
violations still reject afterward. Body `id` alone supplies printable provider
request ID; there is no header fallback. Transport rows retain separate actual
SDK prompt SHA and exact canonical wire SHA. Partial/rejected incomplete bodies
have no complete-body SHA. Each admitted HTTP entry emits one bounded row,
including failed/cancelled work; fixtures fabricate no HTTP rows.

The trusted concrete `TransportOutcomeSink` constructor must reserve its fixed
maximum-row artifact capacity before lane activation. Its synchronous `record`
only consumes that reservation. A generic Python subclass does not certify
storage ownership; runtime allowlisting and full collection preflight do.
Sink exceptions remain failures rather than discarded entered work.

## Capture identity, entries and cleanup

`register_capture(decision_sha, actual_capture_packet)` derives original BGR
pixel digest, SDK capture time and capture locator from immutable owned payload.
Before native decoding, PNG must match actual SDK grammar: IHDR/IDAT/IEND only,
<=2048 chunks with valid CRC, noninterlaced8-bit truecolor; bounded zlib inflation
must equal H*(W*3+1). Ancillary compressed profiles/APNG are refused. An owned
OpenCV decode thread then checks lossless BGR digest against SDK source digest
AND original owned packet/capture time. Cancellation joins that thread before
releasing workspace. The complete native/source inventory separately validates
original manifest/capture provenance. Only the actual SDK's system/user strings
and image are mapped to the frozen wire form, without an added attempt.

Prepared calls accept one actual binding and validate frozen owner/context,
binding index, provider/revision and actual SDK prompt digest. Actual bindings
are retained immutably under original decision SHA only after entry.
`entry_for_decision` returns that exact object; <=256 entries are retained.
The trusted coordinator calls `release_entry` only after reserving immutable
case/publication/financial exports. Release never resets actual-entered ordinal
or permits reusing an entry instance. `release_capture` retires correlation for
an unentered request whose dispatch was refused. Close scrubs retained maps.

A fixture requires exact frozen `(invocation,lane,actual-entered ordinal)` rows,
without wildcard/generated fallback. Optional explicit
`FixtureReceiptRouter.settle(actual_binding,scenario_sha,call_ordinal=...)` runs
once after actual row selection, before response/decoder delay. Later failure
or cancellation does not erase a recorded charge. Unknown fixture rows remain
unknown; no router means nonnull scenario references reject. Synthetic routing
never authorizes real monetary settlement.

Close joins prepared work, owned decoder, HTTP response and client despite
repeated cancellation, then releases the joint workspace reservation. It never
closes or certifies an external server/GPU; unknown liabilities remain explicit.
