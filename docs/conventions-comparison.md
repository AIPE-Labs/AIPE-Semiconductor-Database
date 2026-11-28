# Conventions compared: this repository, AIPE-Core 0.1.0 and Magnetic Data Schema v0.2

Status: report and proposal. Nothing here changes a schema. Compared on 2026-11-27:
this repository's domain schema 3.0.0 (`src/aipe_devices/domain/`), AIPE-Core `v0.1.0`
(`schemas/common.schema.json`, `evidence.schema.json`, `semiconductor.schema.json`) and
AIPE-Magnetics-Database `v0.3.0` (`schemas/v0.2/`).

## What already agrees

- A quantity is `{value, unit}` with a number and an SI unit string in all three.
- Absolute temperature is kelvin; missing values are absent or `null`, never zero.
- Original files are referenced by URI with a SHA-256.
- Review status starts at `unreviewed` everywhere.
- Core and magnetics share the evidence kinds (`assumption`, `analytical`, `simulation`,
  `measurement`, `source`) and the three review states (`unreviewed`, `reviewed`, `rejected`).

## Differences

| Topic | Semiconductor 3.0.0 | Core 0.1.0 | Magnetics v0.2 | Consequence |
| --- | --- | --- | --- | --- |
| Unit vocabulary | Closed list of 17: adds `C`, `J/K`, `V/s`, `A/s`, `1/s`; lacks `m`, `m^2`, `m^3`, `kg`, `T`, `W/m/K`, `rad` | Closed list of 19: lacks `C`, `J/K`, `V/s`, `A/s`, `1/s` | Any string | Gate charge (C), thermal capacitance (J/K) and dv/dt cannot be written as a Core quantity; a magnetics unit is not checked at all |
| Quantity fields | `value`, `unit` | `value`, `unit` | `value`, `unit`, `original{value,unit}`, `uncertainty` | The as-printed value lives in three places: magnetics on the quantity, semiconductor in `provenance.source_locators`, Core nowhere |
| Uncertainty | On the record: `standard`, `repetitions`, `minimum`, `maximum`, `confidence_interval`, `confidence_level`, `sample_variation` | None | On the quantity: `kind` (standard, expanded, bounds, unknown), `value`, `lower`, `upper`, `coverage_factor`, `basis` | Not convertible without loss: `coverage_factor` has no semiconductor field; `repetitions` and `sample_variation` have no magnetics field |
| Statistic | `typical`, `minimum`, `maximum`, `measured_mean`, `median`, `standard_deviation` on every record | None | None (in notes) | A datasheet "typ." or "max." has no shared spelling |
| Operating condition | One object with electrical fields (`junction_temperature`, `dc_bus_voltage`, `drain_current`, `gate_voltage_on`, `gate_resistance_on` ...) plus named `extensions`; `duty_cycle` in [0, 1] | `operating-point.schema.json` describes a converter operating point, not a test condition | One object with magnetic fields (`frequency`, `flux_density_peak`, `field_dc`, `current_rms` ...); `duty` in (0, 1) exclusive | The two condition objects share only `ambient_temperature` by name; duty is spelled and bounded differently |
| Origin of a value | `provenance.origin` on every scalar and curve: `measured`, `manufacturer_datasheet`, `manufacturer_model`, `digitized`, `interpolated`, `extrapolated`, `fitted`, `physics_derived`, `inferred`, `synthetic` | `evidence.kind` (five kinds) per evidence item | `data_class` per record: `experimental_measurement`, `manufacturer_datasheet`, `manufacturer_tool_export`, `derived_from_measurement`, `fitted_parameters`; plus Core's `evidence.kind` | Three vocabularies for the same question. An agent asking "is this a measurement?" needs a different test in each repository |
| Granularity | Per value (each scalar and curve has its own provenance) | Per evidence item, referenced by `evidence_refs` | Per record, with `source_ref` on some values | Per-value origin cannot be expressed in Core today |
| Source and evidence | `Source{id, kind, name, artifact, url, access}`; kinds `manufacturer`, `laboratory`, `test_partner`, `paper`, `AIPE`, `simulation_model`, `distributor`, `user_upload` | `evidence.source{type, reference, locator}`; types `user_requirement`, `document`, `repository`, `datasheet`, `publication`, `measurement_record`, `synthetic_example` | `Evidence{reference, locator, url, version, sha256, license, accessed_at}` | Source kinds do not map one to one (no Core type for a manufacturer model file or a distributor) |
| Rights | `AccessMetadata{license, redistribution_allowed, commercial_use_allowed, visibility, owner, category}` per source; `null` means not established | None | `license` string required per record and per evidence; `redistribution_permitted` on the dataset record | Core cannot say whether a value may be redistributed; magnetics cannot say "commercial use" or name an owner; semiconductor has no SPDX-style licence check |
| Artifact | `{id, uri, checksum, format, size}` | `{uri, media_type, sha256}` | `{uri, media_type, sha256, size_bytes, role}` | Same content, three sets of field names (`checksum`/`sha256`, `format`/`media_type`, `size`/`size_bytes`) |
| Review and quality | `quality.review_status` is a free string; `flags` free strings | `review_status` enum on evidence | `review_status` enum on evidence; `quality.status` (`raw`, `normalized`, `curated`, `reviewed`, `rejected`); `flags` | The semiconductor field is not validated; a contribution status (submitted, validated, reviewed) has no shared home |
| Lifecycle | `raw`, `normalized`, `validated`, `canonical`, `derived`, `application_view` per value | None | `quality.status` per record | Overlapping but different lists |
| Identifiers | `^[A-Za-z0-9][A-Za-z0-9_.-]*$`, record ids contain `:` | Lower case, `^[a-z][a-z0-9]*(?:[.:-]...)+$` | Free string | Semiconductor ids with upper case or `_` are not valid Core ids; the Core export hashes them for that reason |
| Schema identifiers | Pydantic models; JSON Schemas in `docs/schemas/` have no versioned `$id` | `$id` at `AIPE-Labs/AIPE-Core/v0.1.0` | `$id` still at `FulongLi/AIPE-Magnetics-Database/v0.2.0` | The magnetics `$id`s point at the pre-transfer address |

## What a shared contract in Core would need

Proposed for a Core 0.2 `common` layer. Each item is additive for Core; the two databases
would adopt it in their next schema version, not retroactively.

1. **One unit list.** The union of the two closed lists (Core's 19 plus `C`, `J/K`, `V/s`,
   `A/s`, `1/s`, and the magnetics units actually in use such as `A/m`, `W/m^3`, `J/m^3`,
   `H/m`, `Ohm*m`), published once in Core and validated in all three.
2. **One quantity shape.** `{value, unit}` stays the minimum. Optional `original{value, unit}`
   and `uncertainty` are defined once in Core. For uncertainty, the magnetics form
   (`kind`, `value`, `lower`, `upper`, `coverage_factor`, `basis`) plus `repetitions` covers
   both; the semiconductor `confidence_interval`/`confidence_level` pair maps onto
   `kind: expanded` with bounds.
3. **One `data_class` vocabulary, per value.** A proposed merged list:
   `measured`, `manufacturer_datasheet`, `manufacturer_model`, `digitized`,
   `derived` (with a sub-kind: interpolated, extrapolated, fitted, physics), `synthetic`.
   Magnetics `experimental_measurement` maps to `measured`, `manufacturer_tool_export` to
   `manufacturer_model`, `fitted_parameters` and `derived_from_measurement` to `derived`.
   Core's `evidence.kind` stays as the coarser question "how was this claim established".
4. **One `statistic` enum** (`typical`, `minimum`, `maximum`, `mean`, `median`,
   `standard_deviation`, `unspecified`) next to the quantity.
5. **One rights block.** `{owner, license (SPDX or null), redistribution_allowed,
   commercial_use_allowed, status}` with `status` in `not_established`, `stated_by_owner`,
   `open_licence`. `null` never means allowed. This is what the MCP servers and both
   explorers already need to show.
6. **One artifact shape.** Core's `{uri, media_type, sha256}` plus optional `size_bytes` and
   `role`. The semiconductor `checksum`/`format`/`size` names would be renamed in a 4.0.0.
7. **One review vocabulary.** Core's `unreviewed`, `reviewed`, `rejected` as the enum for
   every `review_status`, and a separate `contribution_status` (`submitted`, `validated`,
   `reviewed`) for contributed data, so that "CI passed" is never read as "a person checked".
8. **Conditions stay domain-specific, with shared rules.** No common list of condition
   fields is proposed: electrical and magnetic test conditions differ by nature. Shared rules
   instead: every condition is a quantity with a unit from the common list; an absent
   condition means "not stated"; temperature names end in `_temperature` and are in K; a
   duty ratio is called `duty_cycle` and is in [0, 1].
9. **Identifier mapping.** Core keeps its lower-case id pattern. Databases publish a stable
   URN per record revision (`urn:aipe:semiconductor:<device_id>:revision:<n>`) for
   `database_ref`, as the Core export here already does.

## Smaller findings

- The magnetics schemas' `$id`s still name `FulongLi/AIPE-Magnetics-Database/v0.2.0`.
  Changing a published `$id` is a schema change; it is listed here, not done.
- This repository's `quality.review_status` is a free string. Restricting it to the Core
  enum would be backward compatible with every record in the tree (all are `unreviewed`).
- Core's `semiconductor.ratings` has three fields (voltage, current, junction temperature)
  with no condition or statistic. The Core export here deliberately does not fill them,
  because a current rating without its case temperature is ambiguous.
