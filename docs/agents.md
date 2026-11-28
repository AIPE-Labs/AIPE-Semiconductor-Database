# Entry point for agents

Agents read the database through a local, read-only MCP server. It serves the same JSON records that are in
`data/`; it does not calculate, interpolate or write.

## Setup

The Python package contains code only. The data stay in the repository because the manufacturer data's
redistribution rights are not established ([LICENSING.md](../LICENSING.md)), so the server reads a clone:

```sh
git clone https://github.com/AIPE-Labs/AIPE-Semiconductor-Database.git
cd AIPE-Semiconductor-Database
python -m pip install -e '.[mcp]'
aipe-devices-mcp --self-test      # lists the tools and exits
```

With another install layout, set `AIPE_DEVICES_DATA` to the clone's `data/` directory.

| Host | Commands |
| --- | --- |
| Claude Code | `claude plugin marketplace add AIPE-Labs/AIPE-Semiconductor-Database` then `claude plugin install aipe-semiconductor-database@aipe-semiconductor-database` |
| Codex | `codex plugin marketplace add AIPE-Labs/AIPE-Semiconductor-Database` then `codex plugin add aipe-semiconductor-database@aipe-semiconductor-database` |
| Any MCP client | run `aipe-devices-mcp` (stdio), or `python -m aipe_devices.mcp.server` |

The plugins start `python -m aipe_devices.mcp.server` and add the skill
[`semiconductor-data-lookup`](../skills/semiconductor-data-lookup/SKILL.md). `skills/` is the source; the copies
under `plugins/` are kept identical by `python scripts/sync_plugin_skills.py` (CI runs `--check`).

## Tools

| Tool | Returns |
| --- | --- |
| `database_summary` | Devices and records per collection and data class, number of measured records, rights statement |
| `list_sources` | Data owners per collection, their rights status, whether original files are archived |
| `list_devices` | Devices filtered by `query`, `manufacturer`, `technology`, `integration`, `collection` |
| `get_device` | Identity, sources, review status, every record (values with conditions, curves with axes), groups without data |
| `get_values` | Stored values of one record; for a curve, grid points filtered with `where` |
| `provenance` | Source file and SHA-256 or datasheet locator, data class, lifecycle, review status, flags, rights |

Filter values need a unit: `where={"junction_temperature": "25 degC..150 degC", "dc_bus_voltage": "800 V"}`.
Bare numbers, unknown axes and misspelled tool arguments are refused.

## What every value carries

| Field | Meaning |
| --- | --- |
| `unit` / `columns[].unit` | SI unit (K, V, A, J, Ohm, F, C, K/W, J/K ...) |
| `condition` | Operating conditions the source stated. A condition that is not listed was not stated |
| `data_class` | `manufacturer_model`, `manufacturer_datasheet`, `measured`, or a derived class such as `fitted` |
| `collection` | `canonical` (from archived manufacturer model files) or `candidate` (unreviewed datasheet transcription) |
| `review_status` | `unreviewed` until a person has checked the record |
| `quality_flags` | For example `manufacturer_model_not_measurement`, `candidate_not_canonical`, `absent:...` |
| `sources[]` | Name, kind, URL or archived file with SHA-256 |
| `sources[].rights` | `status` (`not_established` or `stated_by_owner`), owner, licence, redistribution and commercial-use permission |
| `uncertainty`, `statistic` | Present where the source gives them; otherwise `null` / `unspecified` |

Model tables from simulation files contain guard points outside the operating range. `get_values` leaves out
rows at or above 773.15 K (the threshold used by the interpolation service) and reports how many in
`guard_rows_excluded`; `include_guard_rows=true` returns them.

## Python

The same queries are available without MCP:

```python
from aipe_devices.api import Database

db = Database()                      # or Database("path/to/data")
db.list_devices(query="C3M0040120K")
db.get_values("C2M0025120D", "wolfspeed_c2m0025120d:Eon:0",
              where={"junction_temperature": "25 degC", "dc_bus_voltage": "800 V"})
```
