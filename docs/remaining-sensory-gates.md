# Remaining sensory delivery gates — 2026-11-14 audit

The approved scope remains all24 families in [the acceptance map](perception-acceptance.md),
plus the cross-cutting streaming, API/MCP, profiling and measured efficiency gates.
Recent text/visual client execution and cost instrumentation do not complete the
sensory provider inventory. This document records newly isolated gaps, not an
exhaustive replacement of the acceptance map or a reduced MVP.

## Merged recording and transport evidence software

The following software milestones were merged on 2026-11-14. They do not
replace the 24-family sensory acceptance map or establish measured savings.

- [PR #279](https://github.com/NomaDamas/Gamst/pull/279): explicit
  [Responses transport](openai-responses-evidence.md) connects actual SDK
  callback entry to the physical request and separately retained original
  response evidence. Cancellation and missing billing remain unknown costs.
- [PR #280](https://github.com/NomaDamas/Gamst/pull/280): original collector
  native3 records are joined to transport evidence and
  [original account aggregates](original-billing-aggregates.md). Aggregate
  amounts are not allocated into invented per-request invoices.
- [PR #281](https://github.com/NomaDamas/Gamst/pull/281):
  [recording-wide native4 operations](recording-native-scopes.md) retain
  immutable task/source/provider ownership, actual SDK entry and worker
  lifecycle evidence, bounded journals and verifiable failed prefixes.
- [PR #282](https://github.com/NomaDamas/Gamst/pull/282): the
  [native4 structural crosscheck](transport-native-crosscheck.md) includes
  the whole selected lane, separate dispatch/entry/send counters, immutable
  output and an offline CLI. Output inside original evidence roots is refused.

Each PR passed independent exact-head review, its final full suite and CI.
The software prerequisites #269, #275 and #276 are closed. The persistent
A/B/C execution composition [#270](https://github.com/NomaDamas/Gamst/issues/270)
and full-lifetime matched-source evaluation
[#274](https://github.com/NomaDamas/Gamst/issues/274) remain in development.
These six work items are one implementation batch, not a denominator for overall
project completion.

Original request-receipt financial integration
[#257](https://github.com/NomaDamas/Gamst/issues/257) and its source-acceptance
contract [#277](https://github.com/NomaDamas/Gamst/issues/277) remain open.
#257 was reopened after the acceptance audit found that its remaining receipt
requirements were not satisfied. Synthetic original-byte/HTTP fixtures prove
software behavior; they do not prove vendor authenticity, account isolation,
invoice completeness, model quality, whole-system savings or latency improvement.

## Required software paths still missing actual acceptance

- **Mapping, family6:** [#186](https://github.com/NomaDamas/Gamst/issues/186),
  child of [#22](https://github.com/NomaDamas/Gamst/issues/22). Depth and optical
  flow do not supply the required ORB-SLAM3 camera-frame mapping path. Add a
  concrete isolated native bridge, bounded map sessions, tracked/lost state,
  transform direction, reset/loop-closure provenance and calibrated replay.
  Monocular scale is not meters. The inspected official
  [System API](https://github.com/UZ-SLAMLab/ORB_SLAM3/blob/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/include/System.h)
  provides C++ tracking/reset/shutdown methods; no official Python binding is
  assumed. The [native ABI software slice](orbslam-native.md) calls this API but
  now has an [owned Context provider](orbslam-context.md); software tests use a
  test-double header, not actual SLAM inference.
  Native build, vocabulary/settings and reference-motion evidence remain
  unverified. Source/build and license handling must be explicit.
- **Cross-modal source separation, family13:**
  [#187](https://github.com/NomaDamas/Gamst/issues/187), child of
  [#29](https://github.com/NomaDamas/Gamst/issues/29). The
  [official SAM-Audio repository](https://github.com/facebookresearch/sam-audio)
  publishes inference code and model/example links. Integrate concrete local
  inference with bounded audio and prompt provenance; independently verify each
  prompt mode. Whole-window processing does not establish native causal streaming.
  Preserve ambient input and validate source separation against clean references.
- **Tactile contact/slip, family17:**
  Software acquisition scope: [bounded tactile capture/replay](tactile-capture.md) (#224). It reports input provenance/window readiness only; Sparsh/task-head inference (#225) and actual tactile validation (#226) remain separate requirements.
  [#188](https://github.com/NomaDamas/Gamst/issues/188), child of
  [#33](https://github.com/NomaDamas/Gamst/issues/33). IMU support does not complete
  the required DIGIT/GelSight capture plus Sparsh/task-head path. The
  [official Sparsh repository](https://github.com/facebookresearch/sparsh) is
  archived/read-only as observed in this audit. Pin the runtime and actual
  task-trained head; representations alone do not measure contact, slip or force.
  Sensor calibration, reference data and live validation are still required.
- **Through-wall pose/action, family16:**
  [#189](https://github.com/NomaDamas/Gamst/issues/189), child of
  [#32](https://github.com/NomaDamas/Gamst/issues/32). The
  [RF-Pose research page](https://rfpose.csail.mit.edu/) describes radio-based
  pose with cross-modal training; it does not establish a downloadable compatible
  runtime or compatibility with arbitrary Wi-Fi RSSI. Identify reproducible
  code/checkpoints, radio preprocessing and actual hardware before claiming
  integration. CSI motion/TI track parsing are separate capabilities, not proof
  of occluded human pose/action inference.

Physical concepts remain a separate required gap under
[#105](https://github.com/NomaDamas/Gamst/issues/105) and family22: calibrated
track/depth geometry plus an executable physical-concept model path and evidence.
Image trajectories alone do not establish world motion, contact, force or mass.
Existing per-family model/device acceptance issues remain required even where
software adapters already exist.

## Issue-state reconciliation

The audit found #57, #133, #135, #154 and #161 closed while their written scope
and implementation comments still required additional software or actual evidence.
They were reopened with explanatory comments. This does not reverse completed PRs
or assert why the issues had been closed. Completion must be demonstrated by the
written requirements and evidence, not inferred from GitHub status alone.

- [#57](https://github.com/NomaDamas/Gamst/issues/57) and
  [#135](https://github.com/NomaDamas/Gamst/issues/135): real frozen matched
  A/B/C quality, whole cost and task-answer-ready latency remain unverified.
- [#133](https://github.com/NomaDamas/Gamst/issues/133) and
  [#154](https://github.com/NomaDamas/Gamst/issues/154): explicit text/local-small/
  external-visual execution exists; full written integration/evidence scope is
  not proven complete.
- [#161](https://github.com/NomaDamas/Gamst/issues/161): explicit client attempts
  now bind actual controller evidence; whole-pipeline coverage, local-worker/
  perception instrumentation and actual evaluated runs still require work.

No model weights were installed by this audit. Hardware purchases are not
implied by implementation authorization. Software work can continue while missing
assets are tracked; fixtures, generated graphs or packet parsers cannot close the
actual-model/device gates. Halo demos remain deferred.
