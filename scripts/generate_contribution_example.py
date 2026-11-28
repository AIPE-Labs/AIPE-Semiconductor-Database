"""Rebuild ``examples/contribution/example-synthetic-dpt`` (synthetic, not a device characterisation)."""

import hashlib
import json
from pathlib import Path

from aipe_devices.contribution import DECLARATION, SCHEMA, validate_contribution

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "examples/contribution/example-synthetic-dpt"
HOLDER = "Example University Power Electronics Laboratory"
CSV = "time_s,vds_V,id_A\n0,800,0\n1e-8,400,10\n2e-8,5,20\n"


def quantity(value, unit):
    return {"value": value, "unit": unit}


def main():
    (TARGET / "original").mkdir(parents=True, exist_ok=True)
    waveform = TARGET / "original/dpt_run01_25C_800V_20A.csv"
    waveform.write_bytes(CSV.encode())
    checksum = hashlib.sha256(CSV.encode()).hexdigest()
    artifact = {
        "id": "artifact:run01-waveform",
        "uri": "original/dpt_run01_25C_800V_20A.csv",
        "checksum": checksum,
        "format": "text/csv",
        "size": len(CSV.encode()),
    }
    source = {
        "id": "source:example-lab",
        "kind": "laboratory",
        "name": HOLDER,
        "access": {
            "license": "CC-BY-4.0",
            "redistribution_allowed": True,
            "commercial_use_allowed": True,
            "visibility": "public",
            "owner": HOLDER,
            "category": "partner",
        },
    }
    recipe = {"id": "example-energy-integration", "version": "1.0"}
    dependencies = [
        {"id": "waveform:run01", "version": "1", "checksum": checksum},
        {**recipe, "checksum": None},
    ]
    condition = {
        "junction_temperature": quantity(298.15, "K"),
        "dc_bus_voltage": quantity(800.0, "V"),
        "drain_current": quantity(20.0, "A"),
        "gate_voltage_on": quantity(15.0, "V"),
        "gate_voltage_off": quantity(-4.0, "V"),
        "gate_resistance_on": quantity(2.5, "Ohm"),
        "gate_resistance_off": quantity(2.5, "Ohm"),
    }

    def metric(name, value, standard):
        return {
            "id": f"metric:run01-{name.lower()}",
            "name": name,
            "quantity": quantity(value, "J"),
            "provenance": {
                "origin": "synthetic",
                "source_ids": [source["id"]],
                "lifecycle": "derived",
                "dependencies": dependencies,
                "recipe_id": recipe["id"],
                "recipe_version": recipe["version"],
            },
            "condition": condition,
            "statistic": "measured_mean",
            "uncertainty": {"standard": standard, "repetitions": 5},
        }

    manifest = {
        "schema_version": "3.0.0",
        "id": "package:example-synthetic-dpt",
        "request_id": "unsolicited",
        "device_id": "example_sic_1200v",
        "sources": [source],
        "campaigns": [
            {
                "id": "campaign:example-dpt",
                "name": "Synthetic double-pulse example",
                "source": source,
                "test_run_ids": ["run:01"],
            }
        ],
        "runs": [
            {
                "id": "run:01",
                "device_id": "example_sic_1200v",
                "physical_sample_id": "EX-S01",
                "production_lot_id": None,
                "condition": condition,
                "protocol": {"id": "EXAMPLE-DPT", "version": "1.0", "category": "dpt"},
                "instrument_setup": {
                    "instruments": [
                        {
                            "id": "scope",
                            "role": "oscilloscope",
                            "manufacturer": "Example Instruments",
                            "model": "EX-4000",
                            "calibration_reference": "EX-CAL-2026-014",
                        }
                    ],
                    "sampling_rate": quantity(2.5e9, "Hz"),
                    "bandwidth": quantity(1e9, "Hz"),
                    "voltage_probe": {
                        "id": "vprobe",
                        "role": "drain-source voltage",
                        "manufacturer": "Example Instruments",
                        "model": "EX-HV200",
                    },
                    "current_probe": {
                        "id": "iprobe",
                        "role": "drain current",
                        "manufacturer": "Example Instruments",
                        "model": "EX-SHUNT-10m",
                    },
                    "deskew": quantity(1.2e-9, "s"),
                    "load_inductance": quantity(100e-6, "H"),
                    "gate_driver": "Example isolated driver, +15 V / -4 V",
                },
                "waveform_refs": [
                    {
                        "id": "waveform:run01",
                        "test_run_id": "run:01",
                        "artifact": artifact,
                        "stage": "raw",
                        "channels": [
                            {"name": "time_s", "unit": "s", "role": "time"},
                            {"name": "vds_V", "unit": "V", "role": "voltage"},
                            {"name": "id_A", "unit": "A", "role": "current"},
                        ],
                        "provenance": {
                            "origin": "synthetic",
                            "source_ids": [source["id"]],
                            "lifecycle": "derived",
                            "dependencies": [{"id": "example-generator", "version": "1.0"}],
                        },
                    }
                ],
                "processing_recipes": [
                    {
                        **recipe,
                        "algorithm": "Integral of vds*id over the switching event",
                        "integration_start_rule": "10 % of gate voltage",
                        "integration_end_rule": "drain-source voltage below 10 % of bus voltage",
                    }
                ],
                "derived_metrics": [
                    {
                        "id": "metrics:run01",
                        "test_run_id": "run:01",
                        "waveform_ids": ["waveform:run01"],
                        "recipe": {**recipe, "checksum": None},
                        "metrics": [metric("Eon", 3.1e-4, 1.2e-5), metric("Eoff", 9.0e-5, 6e-6)],
                    }
                ],
            }
        ],
        "artifacts": [artifact],
        "external_dependencies": [{"id": "example-generator", "version": "1.0"}],
    }
    contribution = {
        "schema": SCHEMA,
        "id": TARGET.name,
        "title": "Synthetic double-pulse example (format demonstration, not real data)",
        "submitted_on": "2026-11-28",
        "contributor": {
            "name": "A. Example",
            "affiliation": HOLDER,
            "kind": "university",
            "contact": "https://orcid.org/0000-0000-0000-0000",
        },
        "rights": {
            "holder": HOLDER,
            "license": "CC-BY-4.0",
            "declaration": DECLARATION,
            "attribution": f"{HOLDER}, synthetic double-pulse example, 2026",
        },
        "device": {
            "manufacturer": "Example Semiconductor",
            "part_number": "EXAMPLE-SIC-1200",
            "production_lot_id": None,
            "physical_sample_ids": ["EX-S01"],
            "date_code": None,
            "identity_level": "sample",
        },
        "setup": (
            "Double-pulse test on a half-bridge board with a 100 uH air-core load inductor; "
            "drain current through a 10 mOhm coaxial shunt; five repetitions per point. "
            "All numbers in this example are synthetic."
        ),
        "package": "manifest.json",
        "deposit": None,
        "synthetic_example": True,
        "review": None,
    }
    for name, payload in (("manifest.json", manifest), ("contribution.json", contribution)):
        (TARGET / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report = validate_contribution(TARGET, allow_synthetic=True)
    report.raise_for_errors()
    print(f"wrote {TARGET.relative_to(ROOT)}; warnings: {len(report.issues)}")


if __name__ == "__main__":
    main()
