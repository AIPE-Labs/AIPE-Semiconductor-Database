# Licensing and data rights

Three things are licensed separately.

**Code** (the Python package `aipe-devices`, importers, exporters, services, schemas in `docs/schemas/`, scripts,
examples and tests) is released under the [MIT licence](LICENSE). The wheel contains code only; no dataset is bundled
into it.

**Manufacturer data** keep whatever rights their owners gave. For everything in the table below those rights are
**not established**: no licence, redistribution permission or commercial-use permission is known, so each record's
source metadata carries `license: null`, `redistribution_allowed: null` and `commercial_use_allowed: null`. Nothing is
relicensed. The MIT licence of the code does not extend to these files, public visibility is not a grant of reuse
rights, and normalisation does not change the rights in the underlying data. Until the rights are established, these
files stay in this repository only and are not published as a dataset anywhere else.

**AIPE's own data layer** (the selection and arrangement of the records, the normalisation to domain schema 3.0.0,
quality flags, coverage and migration reports, and the documentation) is offered under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) to the extent that AIPE holds rights in it. This adds no
restriction to the manufacturer data and cannot grant rights that their owners did not give. Attribution: "AIPE
Semiconductor Database, Fulong Li and contributors", with the repository URL and the version or commit used.

The names "AIPE", "AIPE Labs" and "AI for Power Engineering" and their logos are not covered by these licences. Forks
and redistributions are welcome under the terms above, but must not suggest that they are the AIPE project or are
endorsed by it.

| Data | Licence | Notes |
| --- | --- | --- |
| `data/raw/wolfspeed/` (163 Wolfspeed PLECS XML model files and the "PLECS Model User Guide Rev1.pdf", byte-identical, SHA-256 in `data/raw/manifest.json`) | not established | Each XML file carries Wolfspeed's "as is" warranty disclaimer and no licence text. Kept unmodified as the import evidence. |
| `data/canonical/` (163 device records normalised from those files) | not established for the values; CC BY 4.0 for AIPE's own layer | Every record names Wolfspeed as owner and is flagged `manufacturer_model_not_measurement`. |
| `legacy/v1/`, `legacy/v2/` (326 JSON files, earlier conversions of the same Wolfspeed models) | not established | Kept byte-identical as fixtures for the V1/V2 migration tests; not the official corpus. |
| `data/candidates/` (datasheet transcriptions and candidate records for Wolfspeed, Infineon and other manufacturers' parts) | not established | Individual values transcribed with datasheet URL and locator; no datasheet PDF or vendor model file is stored. Unreviewed, never canonical. |
| `data/contributed/<id>/` (community contributions; none yet) | CC BY 4.0 or CC0, as declared in each `contribution.json` | The contributor declares the right to share; attribution text is in the declaration. See [CONTRIBUTING.md](CONTRIBUTING.md). |
| `examples/`, `tests/golden/fixtures/` | MIT | Synthetic or illustrative data written for this repository; not device characterisation. |

Rights holders may request correction or removal of values through an issue on this repository.

## Historical code

The repository once contained a file `transistor.py` that appeared to be substantially inherited from UPB-LEA's
[`transistordatabase`](https://github.com/upb-lea/transistordatabase) and imported that package. It was removed from
the working tree in the 3.0.0 refactor and no implementation from it was copied into `aipe_devices`. It remains in
this repository's git history (commits `9ebd0cf` and `406379f`); the history has not been rewritten. The MIT licence
above is granted by the AIPE contributors for their own work and does not relicense that historical file; its
distribution and attribution questions are not resolved by its removal.

## Rights metadata in records

`AccessMetadata` (on every `Source`) records owner, licence, redistribution permission, commercial-use permission,
visibility and a category (manufacturer, AIPE, partner, licensed, customer). `null` means "not established", never
"allowed". Contributors must supply these fields explicitly. This is metadata, not an authorisation system.

Third-party code dependencies (pydantic MIT; optional scipy and h5py BSD-3-Clause, openpyxl MIT, PyYAML MIT) keep
their licences.
