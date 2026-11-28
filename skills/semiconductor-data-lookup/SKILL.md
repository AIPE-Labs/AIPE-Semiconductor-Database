---
name: semiconductor-data-lookup
description: Retrieve power semiconductor device data (SiC/Si MOSFET, IGBT, GaN, diode - conduction and switching-loss tables, thermal networks, datasheet ratings) from the AIPE Semiconductor Database with unit, operating conditions, source and rights status for every value - which devices exist, what a part's stored model or datasheet values are, at which conditions, and where each number comes from. Use for data questions only; never estimate, interpolate or recall device values from memory.
---

# Semiconductor data lookup

You have the AIPE Semiconductor Database as MCP tools (`database_summary`, `list_sources`, `list_devices`,
`get_device`, `get_values`, `provenance`). Every number you report must come from those calls.

## Rules

1. **Units always.** Results are SI: temperatures in K, energies in J, resistances in Ohm. Give filter values
   with units (`"25 degC"`, `"400 V..800 V"`); bare numbers are refused. Convert for the user only when asked
   and say that you converted.
2. **Keep data classes apart.** Each value has a `data_class`: `manufacturer_model` (a table from the
   manufacturer's simulation model), `manufacturer_datasheet` (a transcribed datasheet value) or `measured`
   (a laboratory measurement). Never present a model or datasheet value as a measurement. Today the database
   holds no measured record.
3. **State the conditions, and only the stated ones.** A value is meaningful only at its conditions (junction
   temperature, bus voltage, current, gate resistance, gate voltage). If `condition` does not list one, the
   source did not state it: say so, do not assume a typical value.
4. **Say what may be redistributed.** Each source has `rights.status`. `not_established` means the owner has
   given no licence: the value can be used for engineering work and cited, but must not be republished as a
   dataset. This is the status of all manufacturer data today.
5. **Review status.** `review_status: unreviewed` means no person has checked the record. Repeat it, and repeat
   quality flags such as `manufacturer_model_not_measurement`, `candidate_not_canonical` and `absent:...`.
6. **Collections.** `canonical` records come from manufacturer model files archived in the repository.
   `candidate` records are unreviewed datasheet transcriptions; never treat them as canonical evidence.
7. **No modelling.** `get_values` returns stored grid points. Do not interpolate between them, extrapolate
   beyond them or compute losses. Model tables contain guard points outside the operating range; rows at or
   above 773.15 K are left out unless you ask for them. A missing value stays missing.

## Typical workflow

1. `list_devices(query="C3M0040120K")` to find the record ids of a part; a part can have a canonical record
   and a candidate record.
2. `get_device("wolfspeed_c3m0040120k")` for its records: single values with conditions, curves with axes.
3. `get_values(device, record_id, where={"junction_temperature": "25 degC..150 degC", "dc_bus_voltage": "800 V"})`.
4. `provenance(device, record_id)` before quoting a number in a report: source file and checksum or datasheet
   locator, data class, review status and rights.

## Setup

The data are not bundled into the Python package, because the manufacturer data's redistribution rights are
not established. Clone https://github.com/AIPE-Labs/AIPE-Semiconductor-Database and run
`pip install -e '.[mcp]'` in the clone, or set `AIPE_DEVICES_DATA` to the clone's `data/` directory.
