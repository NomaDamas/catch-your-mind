# Tennis ball-line task pack

`rfdetr.tennis_image` is a bounded sports task pack for #134. It composes
the existing RF-DETR trajectory providers and finite-image-line rules. It emits
observed ball-centroid endpoint candidates for a caller-selected image line in
a fixed-camera tennis singles view. This is not ball bounce, court in/out,
contact, possession, officiating, score or rule-violation recognition.

```python
worker = await ProcessProvider.open(existing_python, 'rfdetr.tennis_image', {
    'path': '/absolute/local/rf-detr-nano.pth', 'sha256': checkpoint_sha256,
    'reference': {
        'id': 'tennis-camera-view-1', 'source_id': 'cam', 'sensor_id': 'sensor',
        'coordinate_frame': 'camera.normalized', 'calibration_id': None,
        'image_size': [1920, 1080],
        'line': {'start': [.5, .1], 'end': [.5, .9]},
    },
})
```

Use the explicit `SensorStreams` registration/open/submit lifecycle from
[RF-DETR trajectories](rfdetr-trajectories.md), with an appropriate packet/queue
byte budget. The profile opens only the selected existing local worker/model;
discovery imports no optional inference library and installs/downloads nothing.
Python, Context and MCP use registered `sports.tennis.image_line` observations.
Consumer cadence is unchanged. The caller owns original media and retention.

The exact reference/configuration binds the capability version. It fixes source,
sensor, coordinate/calibration identity, image dimensions and one finite
normalized-image line. The first accepted frame also binds subject and stream
epoch. A changed identity, epoch or image size invalidates the reference and
suppresses all subsequent events until explicit reset/reopen. A reset is the
application's decision that the configured fixed view is valid again; it does
not measure camera motion or calibration. Reframing requires a new configured
reference, not automatic reuse of old line coordinates. A same-geometry pan or
cut cannot be detected by this profile: the host must reset/reconfigure or stop
the task. The fixed-camera assumption and model quality always remain unverified.

The default supported population is at most two detected people, one sports
ball and four rackets, within the existing eight-detection cap. Optional exact
`envelope` configuration can set `max_people`1..4, `max_rackets`0..4,
`min_ball_side_pixels`4..128, `max_capture_gap_ms`1..100 and
`max_endpoint_displacement_normalized` greater than0 and at most.1. All five
fields must be supplied together and bind the capability version. This allows
an explicit doubles population or a stricter selected view without unbounded
tracking or silent population selection. Any other
detected category, excess population, incomplete detector snapshot or multiple
balls abstains. This restrictive envelope is suitable for a controlled singles
view; it does not establish ordinary broadcast/full-court support. Detector
thresholds can miss real objects, so a complete detector snapshot is never a
complete physical-scene inventory. People/rackets are population checks, not
verified players or identity.

Only the unique detected `sports ball` track can emit events. Its box must be at
least four source pixels on each side. The previous contributing capture must
be contiguous and within 100 ms, and centroid displacement must be at most .1
normalized-image Euclidean units. These are fixed admission bounds, not measured
accuracy thresholds or a realtime guarantee. IoU association can still create a
new segment inside this envelope; new/ambiguous tracks collect a new pair before
events. Small balls, large displacement, missing/occluded balls, unsupported
population and partial snapshots clear histories and emit explicit abstention.
Nothing is interpolated through an occlusion or a skipped capture. Fast balls
outside this envelope remain unsupported; this pack does not improve the
underlying detector or introduce a new tracker.

The existing [line rule](image-events.md) supplies exact endpoint/event semantics,
deadbands and local indices. Keep the whole immutable output to resolve each
event against its `objects` history and `event_summary` rule. Original timestamps,
evidence hashes, segment IDs and actual velocity intervals remain intact. The
task status is `collecting`, `observed_endpoints` or `abstained`; an empty event
array is not a verified absence of a real event. The task's population/envelope
status is distinct from the original detector completeness flag. Stored outputs
can use existing bounded [cursor replay](observation-pages.md) to retain
intermediate events; retention gaps still count as missing consumer evidence.

## Conditional moving-camera mode

Add `compensation` with exactly `background_roi`, `operating_assumption` and
`anchor` to select the existing compensated provider. `anchor` has exactly
`timestamp_ms`, `capture_sequence` and `evidence_sha256` of the explicitly
selected original anchor capture. The other two fields follow
[conditional compensation](compensated-trajectories.md). The image line is in
that anchor's normalized coordinates. Source/geometry/reference binding and
explicit reopen for rebinding work as documented there. No per-frame line
coordinates or mutable unversioned rule update are accepted.

Capture gap and ball displacement admission use the frozen envelope; displacement
uses estimated anchor projections in this mode. Occlusion, missing/ambiguous
ball and unsupported population clear object association/history while retaining
the camera reference. A returned ball starts a fresh segment and pair. A gap,
cut, failed compensation or horizon invalidates the anchor and abstains until
the host explicitly supplies a newly configured reference. Transform admission
is conditional, not verified camera motion. Parallax, rolling shutter and wrong
accepted fits remain actual-validation limitations, with no blanket broadcast
support claim.

Metric positions are deliberately absent from this ball-line pack. The optional
[projective ground-plane provider](ground-plane.md) maps only explicitly eligible
on-plane points; it never automatically maps ball centroids. Existing
calibrated stereo/`MetricKinematics` supply separate measured-track geometry;
relative image/depth values cannot become court metres. An airborne ball is not
on the court plane, so a court homography is not a valid ball3D speed/height
measurement. Actual metric claims retain #105 acceptance.

## Software validation and remaining evidence

```sh
python3 -m unittest discover -s tests -p test_tennis_image.py -v
python3 -m unittest discover -s tests -p test_anchor_events.py -v
```

Tests cover unequal capture intervals and original evidence indices, ball-only
events, lookalikes/absence/population overflow, small/fast balls, source/epoch/
geometry reference invalidation and explicit reset, sequence/time gaps, offline
discovery and actual owned-child Context/MCP publication and lifecycle cleanup.
Compensated tests run real OpenCV against rendered motion, bind original anchor
evidence, reject mismatches, rebind through explicit frozen reopen, retain
camera state while ball continuity abstains, and bound joint history/event output.
Detector inference is a fixture. No model, dataset or sensor was installed or
run for semantic/accuracy evaluation.

This increment does not complete #134. It supplies a configurable bounded sport
pack, conditional compensated-anchor rule binding/rebinding and explicit
fast-ball/occlusion abstention. Broader support beyond the declared envelope
requires independently supported detector/tracker input; insufficient source
evidence cannot be repaired by interpolating unobserved ball positions.
Actual trained checkpoint acceptance, independently annotated tennis trajectories
and events, missed/abstained-event denominators, pixel/metric calibration truth,
runtime/resources, off-screen consumer tasks and frozen A/B/C quality/cost/latency
remain deferred acceptance under #134/#105/#57/#135. Synthetic geometry and worker
tests cannot close those gates.
