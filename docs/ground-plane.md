# Explicit projective ground-plane points

`geometry.ground_plane` supplies the projective/homography software path for
caller-declared points on a calibrated plane. This is separate from airborne
ball trajectories. It uses no model or optional numerical package and never
fits a calibration automatically. The caller supplies a verified application
calibration if it wants measured claims; the SDK keeps calibration truth false.

```python
worker = await ProcessProvider.open(existing_python, 'geometry.ground_plane', {
    'id': 'court-calibration-1', 'reference_id': 'camera-view-1',
    'source_id': 'cam', 'sensor_id': 'plane-points',
    'input_frame': 'camera.normalized', 'output_frame': 'court.xy',
    'image_size': [1920, 1080], 'valid_roi': [.1, .1, .9, .9],
    'image_to_plane': [[10, 0, 0], [0, 20, 0], [.5, 0, 1]],
})
```

The example matrix is illustrative, not a real court calibration. All exact
configuration fields bind the capability version. The matrix maps normalized
input coordinates `[x,y,1]` to homogeneous plane metres; divide its first two
outputs by the third. The configured `valid_roi` limits where that calibration
is applicable. A singular matrix, nonfinite/bounded coefficient violation or
projective horizon through that ROI is rejected before runtime startup.

Submit a video `InputFrame` with structured data, original capture timestamp,
and `SensorMetadata` matching configured source/sensor/input-frame/calibration
ID and an explicit stream epoch (assigned by `SensorStreams` when managed):

```python
data = {
    'reference_id': 'camera-view-1', 'image_size': [1920, 1080],
    'points': [
        {'id': 'known-ground-contact', 'xy': [.5, .5], 'on_plane': True},
        {'id': 'airborne-ball', 'xy': [.5, .5], 'on_plane': False},
    ],
}
```

At most eight unique points are accepted. Every point must explicitly declare
`on_plane`; unknown/off-plane points return null metric coordinates and
`off_plane_or_unknown`. Out-of-region or out-of-extent projections also abstain.
Even `on_plane=True` remains an unverified caller assertion, not evidence of
ground contact. In particular, a foot bounding-box bottom or ball centroid
cannot establish plane eligibility automatically. The provider reports original
capture identity and hashes the supplied structured points, not camera pixels.

Changed reference ID, image dimensions, source, frame or calibration requires
explicit reconfiguration/reopen and rejects the old configuration. Moving-camera
inputs must first be correctly expressed in the same calibrated anchor frame;
the provider does not silently apply a static homography to a new camera view.
The image dimensions and reference ID are assertions the integrator must match
to original evidence. No camera pose, elevation, airborne 3D velocity, force or
measured calibration accuracy is inferred. Existing `MetricKinematics` is the
separate path for actual calibrated metric3D tracks and capture-time motion.

Register the worker's capability and factory in `SensorStreams` using the same
Python/Context/MCP lifecycle as other providers. Discovery starts no devices or
workers. A real dependency-free child/stream/MCP test verifies this path:

```sh
python3 -m unittest discover -s tests -p test_ground_plane.py -v
```

Tests check projective division, source/reference/calibration rejection, bounded
points, matrix degeneracy/horizons, off-plane and region abstention, retained
output copies and owned worker cleanup. They do not validate real court
calibration or physical point eligibility. #105/#134 retain reference-device,
annotation, actual accuracy/runtime and matched consumer acceptance.
