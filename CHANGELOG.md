# Changelog

## 3.2.0 — Graduation: licence, agent and people entry points, contribution window (2026-11-28)

No change to the domain schema (3.0.0) or to any data file. Nothing in the existing Python API is removed.

- MIT `LICENSE` for the code, declared in `pyproject.toml` and `aipe.yaml`; `LICENSING.md` rewritten (code MIT,
  manufacturer data rights not established and not relicensed, AIPE's own data layer CC BY 4.0). Repository and
  AIPE-Core schema addresses point at `AIPE-Labs`; CI checks all Core projections against AIPE-Core `v0.1.0`.
- Entry point for agents: `aipe_devices.api.Database` (read-only queries) and a local stdio MCP server
  (`aipe-devices-mcp`, extra `mcp`) with the tools `database_summary`, `list_sources`, `list_devices`,
  `get_device`, `get_values` and `provenance`. Every value carries unit, stated conditions, data class, source and
  rights status. Claude Code and Codex plugins with the `semiconductor-data-lookup` skill.

- Entry point for people: a static, read-only Data Explorer (`site/`, `scripts/build_site.py`) with an overview, a
  device list, device pages with charts of the stored grid points, and a sources-and-rights page. Every device page
  states the source of the data and that its redistribution rights are not established. The GitHub Pages workflow
  is manual only.

- Contribution window: `aipe_devices.contribution` (declaration model, acceptance rules, status), CLI
  `aipe-devices validate-contribution`, `data/contributed/`, a synthetic format example, issue forms for data
  contributions and for rights holders, `CONTRIBUTING.md`, `docs/wanted-measurements.md` (generated) and
  `docs/dataset-layout.md` (intention only; nothing is published). Contributed data are served by the API, the MCP
  tools `list_contributions` / `get_contribution` and the explorer with their status: submitted, validated, reviewed.
- `docs/conventions-comparison.md`: conventions compared with AIPE-Core 0.1.0 and the magnetics schema v0.2.

## 3.1.0 — DAB loss evaluation, screening and measurement requests

- Python 3.10 support: `StrEnum` backport in `schema/enums.py`, `requires-python >= 3.10`,
  CI matrix 3.10/3.11/3.12. Package version 3.1.0; domain schema stays 3.0.0.
- `services/interpolation`: `NDInterpolator`/`PreparedTensor` multilinear evaluation of
  N-D curves with `EnvelopePolicy` (guard rows >= 773.15 K dropped, extrapolation only
  with `allow_extrapolation=True`, flagged and recorded as `extrapolated` origin).
- `services/loss/dab.py`: `DABLossEvaluator` implementing `LossEvaluator` for a DAB
  switch position from summary metrics or sampled waveforms (HDF5 loader), with
  conduction (forward/reverse, gate-aware third-quadrant policy), turn-off, ZVS-aware
  turn-on, PLECS gate-resistance formula scaling through a restricted grammar
  (`plecs_formula.py`), `physics_derived` records with tensor lineage and a `coverage` list.
- `services/thermal`: Zth(t) step response, exact Cauer -> Foster conversion, junction
  temperature with user-supplied case-to-sink resistance, electro-thermal fixed point.
- `importers/datasheet`: transcription importer (`aipe-datasheet-transcription/0.1`) that
  builds unreviewed candidate records with datasheet URL evidence, `absent` flags and
  canonical-record links; `data/candidates/` with the 2026-10-21 SiC DAB shortlist
  (17 devices + 2 TI reference-design parts) and generated records.
- `services/selection/dab.py`: evidence-tiered DAB screening (derating, current margin,
  losses at Tj, junction-temperature headroom, confidence score; tiers never interleave).
- `services/measurement_requests.py`: prioritised draft `MeasurementRequest`s from
  coverage gaps (static I-V, Rds(on) vs Tj, DPT, reverse conduction, Coss/Eoss, Zth,
  package thermal) with questions, uncertainty targets and benefit x uncertainty scores.
- CLI: `dab-losses`, `dab-screen`, `measurement-requests`, `import-candidates`;
  `examples/dab/` holds outputs generated from the nominal run summary.
- Unit registry: uH/nH/mH, uC, A/us, A/ns, V/us, V/ns, kV, kW/mW, degC/W.
- `aipe.yaml`: capabilities `semiconductor-loss-evaluation`, `semiconductor-dab-screening`,
  `semiconductor-measurement-requests`, `candidate-device-import`.

## 3.0.0 — Foundation refactor

- Added versioned canonical models, SI units, conditions, provenance, lineage and quality.
- Added JSON repository, artifact storage, PLECS importer/exporter, JSON/MATLAB exports,
  and explicit V1/V2 migrations.
- Preserved 164 raw files and 326 legacy JSON files. Rebuilt 163 devices, including
  90 four-dimensional switching tables lost by old converters.
- Added DPT campaign/run/instrument/protocol/recipe/metric metadata, measurement
  schemas, examples and validation; module, reliability and market extensions.
- Added coverage, invalidation, bounded interpolation, thermal resistance, tests and CI.

### Breaking changes

Old root scripts and the monolithic `Transistor` API are retired. V3 does not import
`transistordatabase`. `DUTs/` moved to `data/raw/wolfspeed/`; `standard_database*`
moved to `legacy/v1/` and `legacy/v2/`. `data/canonical/` is the sole official corpus.
The V3 CLI replaces preprocessing/router scripts. PDF/HTML reports and legacy plots
are retired without a V3 replacement in this phase. New services do not implement
all historical working-point, fitting or lifetime methods.

Energy is J, resistance Ohm, absolute temperature K; `C` means electrical charge.
No source temperature/voltage points are removed and no unknown ratings/gate voltages
are synthesized. V2 rating/static assumptions remain derived/inferred records.
