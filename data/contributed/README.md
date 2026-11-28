# Contributed data

One directory per accepted contribution, named by its id. Nothing has been contributed yet.

```text
data/contributed/<contribution-id>/
  contribution.json   who contributes, the right to share, the licence, device, setup, review
  manifest.json       measurement package: runs, conditions, instruments, values, file checksums
  original/...        the original files, unmodified
```

Rules, enforced by `aipe-devices validate-contribution data/contributed/*` in CI:

- an open licence (CC BY 4.0 or CC0) and the signed declaration of the right to share;
- every original file listed with its SHA-256, in this directory or in a DOI deposit;
- values are measured, each with its unit and operating conditions; nothing is filled in;
- the directory is not edited after acceptance, except to add a `review`. Corrections are
  a new contribution that names the one it replaces.

How to contribute: [CONTRIBUTING.md](../../CONTRIBUTING.md). A complete format example
with synthetic numbers: [examples/contribution/example-synthetic-dpt](../../examples/contribution/example-synthetic-dpt).
