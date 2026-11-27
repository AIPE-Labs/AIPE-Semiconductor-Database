"""Read-only query API over a checkout of the data: the one source for the MCP server and the CLI.

Every value returned carries its unit, operating conditions, origin (``data_class``),
source and rights status, so a caller can tell a manufacturer model value from a
datasheet transcription or a measurement, and can tell what it may redistribute.
Nothing here interpolates, fits, estimates or writes.
"""

import json
import os
from functools import cached_property
from itertools import product
from pathlib import Path

from aipe_devices import __version__
from aipe_devices.domain.device import CHARACTERISTICS
from aipe_devices.normalizers.units import normalize
from aipe_devices.services.interpolation import GUARD_TEMPERATURE_K

DATA_ENV = "AIPE_DEVICES_DATA"
MAX_ROWS = 5000

COLLECTIONS = {
    "canonical": (
        "canonical",
        "Official corpus: records normalised from manufacturer model files kept "
        "byte-identical in data/raw/. Model values, not measurements.",
    ),
    "candidate": (
        "candidates/records",
        "Unreviewed datasheet transcriptions. Never canonical evidence.",
    ),
}
RIGHTS_NOTE = (
    "Redistribution and commercial-use rights are not established: the owner has given "
    "no licence. Use the value for your own engineering work and cite the source; do not "
    "republish it as a dataset."
)


class QueryError(ValueError):
    """Invalid query; ``code`` is a stable machine-readable prefix."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def default_data_root() -> Path:
    """``$AIPE_DEVICES_DATA`` or the ``data/`` directory of the checkout this package runs from.

    The wheel bundles no dataset (the manufacturer data's redistribution rights are not
    established), so a plain ``pip install`` has nothing to serve until this is set.
    """
    env = os.environ.get(DATA_ENV)
    root = Path(env) if env else Path(__file__).resolve().parents[2] / "data"
    if not (root / "canonical").is_dir():
        raise QueryError(
            "data_not_found",
            f"No data directory at {root}. Clone "
            "https://github.com/AIPE-Labs/AIPE-Semiconductor-Database and install it with "
            f"`pip install -e '.[mcp]'`, or set {DATA_ENV} to the checkout's data/ directory.",
        )
    return root


def parse_range(text: str, unit: str) -> tuple[float, float]:
    """``'25 degC'`` or ``'400 V..800 V'`` -> inclusive SI bounds in ``unit``. Bare numbers are refused."""

    def one(part: str) -> float:
        pieces = part.split()
        if len(pieces) != 2:
            raise QueryError(
                "invalid_input", f"'{part.strip()}' needs a value and a unit, e.g. '25 degC'"
            )
        try:
            quantity = normalize(float(pieces[0]), pieces[1])
        except ValueError:
            raise QueryError("invalid_input", f"'{pieces[0]}' is not a number") from None
        if quantity.unit != unit:
            raise QueryError(
                "invalid_input", f"unit '{pieces[1]}' does not convert to the axis unit {unit}"
            )
        return quantity.value

    low, separator, high = text.partition("..")
    bounds = (one(low), one(high) if separator else one(low))
    if bounds[0] > bounds[1]:
        raise QueryError("invalid_input", f"range '{text}' is reversed")
    return bounds


def _condition(condition: dict) -> dict:
    """Stated conditions only; a missing key means the source did not state it."""
    out = {
        key: value
        for key, value in condition.items()
        if isinstance(value, dict) and value.get("value") is not None
    }
    if condition.get("gate_state", "unknown") != "unknown":
        out["gate_state"] = condition["gate_state"]
    for extension in condition.get("extensions", ()):
        out[extension["name"]] = extension["quantity"]
    return out


def _rights(access: dict) -> dict:
    established = (
        access.get("license") is not None or access.get("redistribution_allowed") is not None
    )
    return {
        "status": "stated_by_owner" if established else "not_established",
        "owner": access.get("owner"),
        "license": access.get("license"),
        "redistribution_allowed": access.get("redistribution_allowed"),
        "commercial_use_allowed": access.get("commercial_use_allowed"),
        "note": None if established else RIGHTS_NOTE,
    }


def _source(source: dict) -> dict:
    artifact = source.get("artifact") or {}
    return {
        "id": source["id"],
        "kind": source["kind"],
        "name": source["name"],
        "url": source.get("url"),
        "file": artifact.get("uri"),
        "sha256": artifact.get("checksum"),
        "rights": _rights(source.get("access", {})),
    }


class Database:
    """In-memory index of the JSON records under one data root. Read-only."""

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root is not None else default_data_root()

    @cached_property
    def _devices(self) -> dict[str, tuple[str, dict]]:
        devices = {}
        for collection, (folder, _) in COLLECTIONS.items():
            for path in sorted((self.root / folder).glob("*.json")):
                if path.name.endswith(".dossier.json") or path.name == "index.json":
                    continue
                devices[path.stem] = (collection, json.loads(path.read_text(encoding="utf-8")))
        return devices

    # -- lookup ---------------------------------------------------------------------------

    def _get(self, device: str) -> tuple[str, dict]:
        if device in self._devices:
            return self._devices[device]
        key = device.casefold()
        matches = [
            item
            for item in self._devices.values()
            if key
            in {
                item[1]["device_id"].casefold(),
                item[1]["identity"]["part_number"].casefold(),
                *(alias.casefold() for alias in item[1]["identity"].get("aliases", ())),
            }
        ]
        canonical = [item for item in matches if item[0] == "canonical"]
        if len(canonical) == 1 or len(matches) == 1:
            return (canonical or matches)[0]
        if matches:
            ids = ", ".join(item[1]["device_id"] for item in matches)
            raise QueryError("ambiguous", f"'{device}' matches several records: {ids}")
        raise QueryError(
            "not_found", f"No device '{device}'. Use list_devices to see what is available."
        )

    @staticmethod
    def _records(device: dict):
        """(group, kind, record) for every value-bearing record of a device."""
        for record in device.get("ratings", ()):
            yield "ratings", "scalar", record
        for record in device.get("package", {}).get("parasitics", ()):
            yield "package", "scalar", record
        for group in CHARACTERISTICS:
            for record in device[group].get("scalars", ()):
                yield group, "scalar", record
            for record in device[group].get("curves", ()):
                yield group, "curve", record
        for record in device.get("thermal", ()):
            yield "thermal", "thermal_network", record

    def _describe(self, collection: str, device: dict, group: str, kind: str, record: dict) -> dict:
        sources = {source["id"]: source for source in device["provenance"]}
        provenance = record["provenance"]
        quality = record.get("quality") or device["quality"]
        out = {
            "device_id": device["device_id"],
            "record_id": record["id"],
            "group": group,
            "kind": kind,
            "name": record.get("name", f"{record.get('topology', '')} thermal network"),
            "data_class": provenance["origin"],
            "collection": collection,
            "review_status": quality.get("review_status", "unreviewed"),
            "quality_flags": [*device["quality"]["flags"], *quality.get("flags", ())]
            if quality is not device["quality"]
            else list(device["quality"]["flags"]),
            "statistic": record.get("statistic", "unspecified"),
            "uncertainty": record.get("uncertainty"),
            "condition": _condition(record.get("condition", {})),
            "sources": [_source(sources[i]) for i in provenance["source_ids"] if i in sources],
            "source_locators": provenance.get("source_locators", []),
        }
        if kind == "scalar":
            out["value"] = record["quantity"]["value"]
            out["unit"] = record["quantity"]["unit"]
        elif kind == "curve":
            out["unit"] = record["unit"]
            out["axes"] = [
                {
                    "name": axis["name"],
                    "unit": axis["unit"],
                    "min": min(axis["values"]),
                    "max": max(axis["values"]),
                    "points": len(axis["values"]),
                    "values": axis["values"],
                }
                for axis in record["axes"]
            ]
        else:
            out["topology"] = record["topology"]
            out["from_node"] = record.get("from_node", "junction")
            out["to_node"] = record.get("to_node", "case")
            out["elements"] = [
                {
                    "resistance": element["resistance"],
                    "capacitance": element["capacitance"],
                }
                for element in record["elements"]
            ]
        return out

    # -- queries --------------------------------------------------------------------------

    def summary(self) -> dict:
        collections = {}
        for name, (_, description) in COLLECTIONS.items():
            items = [device for collection, device in self._devices.values() if collection == name]
            classes: dict[str, int] = {}
            for device in items:
                for _, _, record in self._records(device):
                    origin = record["provenance"]["origin"]
                    classes[origin] = classes.get(origin, 0) + 1
            collections[name] = {
                "description": description,
                "devices": len(items),
                "manufacturers": sorted({d["identity"]["manufacturer"] for d in items}),
                "records_by_data_class": classes,
            }
        return {
            "database": "AIPE Semiconductor Database",
            "package_version": __version__,
            "domain_schema": "3.0.0",
            "collections": collections,
            "measured_records": sum(
                c["records_by_data_class"].get("measured", 0) for c in collections.values()
            ),
            "rights": (
                "Code is MIT. " + RIGHTS_NOTE + " This applies to every record whose rights "
                "status is 'not_established'. See LICENSING.md."
            ),
            "limitations": [
                "No record is a measurement unless its data_class is 'measured'.",
                "No record has been reviewed by a person unless review_status says so.",
                "Values are returned as stored; nothing is interpolated or extrapolated.",
            ],
        }

    def list_sources(self) -> list[dict]:
        grouped: dict[tuple, dict] = {}
        for collection, device in self._devices.values():
            for source in device["provenance"]:
                rights = _rights(source.get("access", {}))
                key = (collection, source["kind"], rights["owner"], rights["status"])
                entry = grouped.setdefault(
                    key,
                    {
                        "collection": collection,
                        "kind": source["kind"],
                        "owner": rights["owner"],
                        "rights": rights,
                        "devices": 0,
                        "original_files_archived": 0,
                    },
                )
                entry["devices"] += 1
                entry["original_files_archived"] += bool(source.get("artifact"))
        return sorted(grouped.values(), key=lambda e: (e["collection"], e["kind"], str(e["owner"])))

    def list_devices(
        self,
        query: str | None = None,
        manufacturer: str | None = None,
        technology: str | None = None,
        integration: str | None = None,
        collection: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        if collection is not None and collection not in COLLECTIONS:
            raise QueryError("invalid_input", f"collection must be one of {sorted(COLLECTIONS)}")
        out = []
        for name, device in self._devices.values():
            identity, classification = device["identity"], device["classification"]
            text = " ".join(
                [device["device_id"], identity["manufacturer"], identity["part_number"]]
            ).casefold()
            if (
                (collection and name != collection)
                or (query and query.casefold() not in text)
                or (manufacturer and manufacturer.casefold() != identity["manufacturer"].casefold())
                or (technology and technology.casefold() != classification["technology"].casefold())
                or (integration and integration != classification["integration"])
            ):
                continue
            classes = sorted({r["provenance"]["origin"] for _, _, r in self._records(device)})
            out.append(
                {
                    "device_id": device["device_id"],
                    "manufacturer": identity["manufacturer"],
                    "part_number": identity["part_number"],
                    "technology": classification["technology"],
                    "integration": classification["integration"],
                    "collection": name,
                    "data_classes": classes,
                    "review_status": device["quality"]["review_status"],
                }
            )
        return out[: max(1, min(limit, 1000))]

    def get_device(self, device: str) -> dict:
        collection, data = self._get(device)
        keep = ("record_id", "group", "kind", "name", "unit", "data_class", "value", "condition")
        records = []
        for group, kind, record in self._records(data):
            described = self._describe(collection, data, group, kind, record)
            entry = {key: described[key] for key in keep if key in described}
            if kind == "curve":
                entry["axes"] = [
                    {k: axis[k] for k in ("name", "unit", "min", "max", "points")}
                    for axis in described["axes"]
                ]
            records.append(entry)
        present = {record["group"] for record in records}
        return {
            "device_id": data["device_id"],
            "revision": data["revision"],
            "collection": collection,
            "collection_meaning": COLLECTIONS[collection][1],
            "identity": data["identity"],
            "classification": data["classification"],
            "review_status": data["quality"]["review_status"],
            "quality_flags": data["quality"]["flags"],
            "sources": [_source(source) for source in data["provenance"]],
            "records": records,
            "groups_without_data": [
                g for g in ("ratings", *CHARACTERISTICS, "thermal") if g not in present
            ],
        }

    def export_device(self, device: str) -> dict:
        """``get_device`` plus every record in full (curve grids included), for static publication."""
        collection, data = self._get(device)
        out = self.get_device(data["device_id"])
        out["records"] = []
        for group, kind, record in self._records(data):
            described = self._describe(collection, data, group, kind, record)
            if kind == "curve":
                described["values"] = record["values"]
            out["records"].append(described)
        return out

    def _record(self, device: str, record_id: str) -> tuple[str, dict, str, str, dict]:
        collection, data = self._get(device)
        for group, kind, record in self._records(data):
            if record["id"] == record_id:
                return collection, data, group, kind, record
        raise QueryError(
            "not_found",
            f"No record '{record_id}' in {data['device_id']}. get_device lists the record ids.",
        )

    def get_values(
        self,
        device: str,
        record_id: str,
        where: dict[str, str] | None = None,
        include_guard_rows: bool = False,
        limit: int = 200,
    ) -> dict:
        collection, data, group, kind, record = self._record(device, record_id)
        out = self._describe(collection, data, group, kind, record)
        if kind != "curve":
            if where:
                raise QueryError(
                    "invalid_input", "'where' applies to curves; this record is a single value"
                )
            return out
        axes = record["axes"]
        names = [axis["name"] for axis in axes]
        unknown = sorted(set(where or {}) - set(names))
        if unknown:
            raise QueryError(
                "invalid_input", f"unknown axis {unknown}; this record's axes are {names}"
            )
        bounds = {
            axis["name"]: parse_range(where[axis["name"]], axis["unit"])
            for axis in axes
            if where and axis["name"] in where
        }
        rows, guard, matched = [], 0, 0
        limit = max(1, min(limit, MAX_ROWS))
        for point, value in zip(product(*(axis["values"] for axis in axes)), record["values"]):
            coordinates = dict(zip(names, point))
            if any(not low <= coordinates[n] <= high for n, (low, high) in bounds.items()):
                continue
            if (
                not include_guard_rows
                and coordinates.get("junction_temperature", 0) >= GUARD_TEMPERATURE_K
            ):
                guard += 1
                continue
            matched += 1
            if len(rows) < limit:
                rows.append([*point, value])
        for axis in out["axes"]:
            del axis["values"]
        out["columns"] = [
            *({"name": axis["name"], "unit": axis["unit"]} for axis in axes),
            {"name": record["name"], "unit": record["unit"]},
        ]
        out["rows"] = rows
        out["rows_matched"] = matched
        out["truncated"] = matched > len(rows)
        out["guard_rows_excluded"] = guard
        out["notes"] = [
            "Rows are the stored grid points; nothing is interpolated.",
            "Simulation model tables contain guard points outside the device's operating "
            "range (zero rows at negative voltage or current, junction temperatures at or "
            f"above {GUARD_TEMPERATURE_K} K). The temperature guard rows are left out unless "
            "include_guard_rows is true.",
        ]
        return out

    def provenance(self, device: str, record_id: str | None = None) -> dict:
        if record_id is None:
            collection, data = self._get(device)
            return {
                "device_id": data["device_id"],
                "revision": data["revision"],
                "collection": collection,
                "collection_meaning": COLLECTIONS[collection][1],
                "review_status": data["quality"]["review_status"],
                "quality_flags": data["quality"]["flags"],
                "sources": [_source(source) for source in data["provenance"]],
                "models": [
                    {"id": m["id"], "format": m["format"], "data_class": m["provenance"]["origin"]}
                    for m in data.get("models", ())
                ],
            }
        collection, data, group, kind, record = self._record(device, record_id)
        described = self._describe(collection, data, group, kind, record)
        keep = (
            "device_id",
            "record_id",
            "group",
            "name",
            "data_class",
            "collection",
            "review_status",
            "quality_flags",
            "statistic",
            "uncertainty",
            "condition",
            "sources",
            "source_locators",
        )
        out = {key: described[key] for key in keep}
        provenance = record["provenance"]
        out["lifecycle"] = provenance["lifecycle"]
        out["freshness"] = provenance["freshness"]
        out["dependencies"] = provenance["dependencies"]
        out["recipe"] = (
            {"id": provenance["recipe_id"], "version": provenance["recipe_version"]}
            if provenance.get("recipe_id")
            else None
        )
        return out
