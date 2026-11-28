# Intended layout of a published dataset

Status: intention only. No dataset is published and no publishing pipeline exists,
because nothing in the repository is redistributable yet: the manufacturer data's rights
are not established ([LICENSING.md](../LICENSING.md)). This note fixes where the first
redistributable data will go, so that the layout does not have to be invented under time
pressure. It follows the AIPE Magnetics Dataset on Hugging Face.

```text
AIPE-Labs/AIPE-Semiconductor-Dataset
  README.md                      dataset card: sources, licences per subtree, limits
  raw/<source-id>/               original files, byte-identical, with LICENSE.md and SHA256SUMS
  normalized/v3/<source-id>/     schema 3.0.0 JSON records, one file per device or package
  tabular/v3/<config>/<source-id>.parquet
                                 flat tables for analysis: one row per value or grid point with
                                 unit, conditions, data_class, source_id, licence, status
  manifests/<source-id>.json     file list with checksums, source version, import commit
```

- `<source-id>` is the contribution id for contributed data
  (`data/contributed/<contribution-id>/` maps to `raw/<contribution-id>/` and
  `normalized/v3/<contribution-id>/`), or a manufacturer id once that manufacturer has
  granted redistribution.
- Each subtree keeps its own licence; nothing is relicensed by being in the dataset.
- Only sources whose rights status is an open licence or an explicit grant are published.
  Records with status `not_established` are never included.
- Proposed `tabular` configs: `scalar_values`, `curve_points`, `thermal_networks`,
  `contributions`.

What exists today that this builds on: `aipe_devices.api.Database` already returns every
value with unit, conditions, data class, source and rights status, and
`contribution_status` for contributed data. The publishing step would be a filter on
rights status followed by a file writer.
