# Contributing

AIPE is an open-source community. This file is mostly about contributing **data**; code
contributions are ordinary pull requests (run `ruff check`, `ruff format --check` and
`pytest -q` first).

## Contributing device data

Universities, companies, test laboratories, individuals and device manufacturers are all
welcome to contribute data they have measured, or, for a manufacturer, their own data. The
terms are the same for everyone.

### What you must state

1. **Who you are**: name, organisation, and whether you contribute as a university,
   manufacturer, company, laboratory or individual.
2. **That you have the right to share the data.** The declaration reads: "I have the right
   to share these data and I release them under the licence named in this contribution."
3. **The licence**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) by default
   (users must credit you; you say how), or
   [CC0](https://creativecommons.org/publicdomain/zero/1.0/). No licence, no merge.
4. **The device**, down to the level you know it: manufacturer and part number always;
   lot, date code and sample identifiers where known. Unknown stays unknown.
5. **The test setup and instruments**: method, fixture, oscilloscope and probes with model
   names, how derived quantities such as switching energies were calculated.
6. **The operating conditions of every value**: temperature, voltage, current, gate
   voltages and resistances, as applicable.
7. **Uncertainty**, where you know it: repetitions, standard deviation or an estimate.
8. **The original files**, unmodified.

Missing values are left missing. Nobody estimates, interpolates or fills them in.

### Two ways in

**A. An issue form, no git needed.** Upload your files to an archive that gives them a DOI
([Zenodo](https://zenodo.org/) is free and lets you choose the licence), then open
[Contribute measured device data](https://github.com/AIPE-Labs/AIPE-Semiconductor-Database/issues/new?template=contribute-data.yml)
and fill in the form. A maintainer builds the data package from your deposit and asks you
to confirm it in the issue before it is merged.

Why a DOI and not an ordinary link: a DOI deposit is permanent and versioned, the files
cannot silently change or vanish, and the archive already records the licence you chose.
Links to personal pages or cloud drives are not accepted.

**B. A pull request with a data package.** Add one directory under `data/contributed/`:

```text
data/contributed/<contribution-id>/
  contribution.json   the declaration (items 1 to 5 above)
  manifest.json       measurement package: runs, conditions, instruments, values, checksums
  original/...        your original files
```

Start from [examples/contribution/example-synthetic-dpt](examples/contribution/example-synthetic-dpt)
(synthetic numbers, real format; `scripts/generate_contribution_example.py` builds it) and
check your package before you push:

```sh
python -m pip install -e .
aipe-devices validate-contribution data/contributed/<contribution-id>
```

`manifest.json` is the measurement package format of this repository
([docs/measurement.md](docs/measurement.md)); use `"request_id": "unsolicited"` when
nobody asked for the measurement. Files larger than 5 MB stay in a DOI deposit and are
listed with their SHA-256 under `deposit.files` in `contribution.json`.

### What happens to a contribution

| Status | Meaning | Who sets it |
| --- | --- | --- |
| submitted | Received, not yet passing the automatic checks | the open issue or pull request |
| validated | Format, licence, declaration, conditions and file checksums pass. No person has confirmed the values | CI, when the package is merged |
| reviewed | A named maintainer has looked at it; the review says what was checked | a maintainer, by adding `review` to `contribution.json` |

The status is shown to people in the Data Explorer and to AI agents through the MCP
server. Contributed data are a class of their own: they are never merged into the
manufacturer records, and nothing is presented as reviewed before a person has looked at
it. "Reviewed" means a plausibility and completeness check by a maintainer, not a
repetition of your measurement.

Original files are archived at the moment a contribution is accepted: in the package
directory, or as a DOI deposit whose file checksums are recorded.

### Which measurements are most wanted

See [docs/wanted-measurements.md](docs/wanted-measurements.md). In short: the database has
no laboratory measurement at all yet, so any measurement of a listed device is new.

### Manufacturers: rights for data already here

Manufacturer model files in this repository are marked "rights not established". A rights
holder can state the terms, or ask for correction or removal, with the form
[Grant or clarify rights](https://github.com/AIPE-Labs/AIPE-Semiconductor-Database/issues/new?template=grant-rights.yml).

## For maintainers: turning an issue into a package

1. Check the form: DOI link, licence, both boxes ticked. Ask in the issue for anything
   missing; do not guess.
2. Download the deposit. Record every file's SHA-256 and size. Files up to 5 MB go into
   `original/`; larger ones are listed under `deposit.files`.
3. Write `contribution.json` from the form and `manifest.json` from the files. Convert
   units to SI with the unit registry; keep the as-submitted value in `source_locators`
   when it was converted. Transcribe only what the contributor gave.
4. Run `aipe-devices validate-contribution`, open a pull request that links the issue,
   and ask the contributor to confirm the package there.
5. Merge when CI is green and the contributor has confirmed. The contribution is then
   "validated". Add `review` only after a person has actually checked it.
