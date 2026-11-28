"""Read-only query API, MCP server and agent-plugin packaging."""

import json
import subprocess
import sys

import pytest
from conftest import ROOT

from aipe_devices.api import Database, QueryError, parse_range

NAME = "aipe-semiconductor-database"
EON = "wolfspeed_c2m0025120d:Eon:0"


@pytest.fixture(scope="module")
def db():
    return Database(ROOT / "data")


def test_summary_states_classes_and_rights(db):
    summary = db.summary()
    assert summary["collections"]["canonical"]["devices"] == 163
    assert set(summary["collections"]["canonical"]["records_by_data_class"]) == {
        "manufacturer_model"
    }
    assert set(summary["collections"]["candidate"]["records_by_data_class"]) == {
        "manufacturer_datasheet"
    }
    assert summary["measured_records"] == 0
    assert "not established" in summary["rights"]


def test_every_value_carries_unit_class_source_and_rights(db):
    for item in db.list_devices(limit=1000):
        device = db.get_device(item["device_id"])
        assert device["sources"]
        for entry in device["records"]:
            record = db.get_values(item["device_id"], entry["record_id"], limit=1)
            assert record["data_class"] != "unknown"
            assert record["review_status"] == "unreviewed"
            assert record["sources"], entry["record_id"]
            assert all(s["rights"]["status"] == "not_established" for s in record["sources"])
            assert all(s["rights"]["note"] for s in record["sources"])
            assert isinstance(record["condition"], dict)
            if record["kind"] == "scalar":
                assert record["unit"] and isinstance(record["value"], float)
            elif record["kind"] == "curve":
                assert all(column["unit"] for column in record["columns"])
            else:
                assert all(
                    e["resistance"]["unit"] == "K/W" and e["capacitance"]["unit"] == "J/K"
                    for e in record["elements"]
                )


def test_lookup_by_part_number_prefers_canonical(db):
    assert db.get_device("c3m0040120k")["device_id"] == "wolfspeed_c3m0040120k"
    assert db.get_device("candidate_wolfspeed_c3m0040120k")["collection"] == "candidate"
    with pytest.raises(QueryError, match="No device"):
        db.get_device("not-a-part")


def test_curve_filter_returns_stored_grid_points_only(db):
    result = db.get_values(
        "C2M0025120D", EON, where={"junction_temperature": "25 degC", "dc_bus_voltage": "800 V"}
    )
    assert [c["name"] for c in result["columns"]] == [
        "junction_temperature",
        "dc_bus_voltage",
        "current",
        "Eon",
    ]
    assert [c["unit"] for c in result["columns"]] == ["K", "V", "A", "J"]
    assert result["rows"][3] == [298.15, 800.0, 25.1, 0.000657]
    assert result["rows_matched"] == 6 and not result["truncated"]
    # 26 degC is not a grid point: nothing is interpolated.
    assert (
        db.get_values("C2M0025120D", EON, where={"junction_temperature": "26 degC"})["rows"] == []
    )


def test_guard_rows_are_excluded_unless_requested(db):
    plain = db.get_values("C2M0025120D", EON, limit=5000)
    full = db.get_values("C2M0025120D", EON, include_guard_rows=True, limit=5000)
    assert plain["guard_rows_excluded"] == 36 and full["guard_rows_excluded"] == 0
    assert full["rows_matched"] == plain["rows_matched"] + 36
    assert all(row[0] < 773.15 for row in plain["rows"])


def test_limit_truncation_is_reported(db):
    result = db.get_values("C2M0025120D", EON, limit=2)
    assert len(result["rows"]) == 2 and result["truncated"] and result["rows_matched"] == 36


@pytest.mark.parametrize("bad", ["25", "25 degC..", "25 V", "x degC", "150 degC..25 degC"])
def test_filter_values_need_valid_units(db, bad):
    with pytest.raises(QueryError):
        db.get_values("C2M0025120D", EON, where={"junction_temperature": bad})


def test_unknown_axis_is_refused(db):
    with pytest.raises(QueryError, match="unknown axis"):
        db.get_values("C2M0025120D", EON, where={"temperature": "25 degC"})


def test_parse_range_converts_to_si():
    assert parse_range("25 degC..150 degC", "K") == (298.15, 423.15)
    assert parse_range("1.2 kV", "V") == (1200.0, 1200.0)


def test_datasheet_value_keeps_condition_and_locator(db):
    device = db.get_device("candidate_infineon_imza120r040m2h")
    rds = next(r for r in device["records"] if r["name"] == "rds_on")
    assert rds["data_class"] == "manufacturer_datasheet" and rds["unit"] == "Ohm"
    assert rds["condition"]["junction_temperature"]["unit"] == "K"
    provenance = db.provenance(device["device_id"], rds["record_id"])
    assert provenance["source_locators"] and provenance["sources"][0]["url"].startswith("https://")
    assert "candidate_not_canonical" in provenance["quality_flags"]


def test_canonical_provenance_names_the_archived_file(db):
    source = db.provenance("C2M0025120D")["sources"][0]
    path = ROOT / "data/raw" / source["file"].removeprefix("raw:")
    assert path.is_file() and len(source["sha256"]) == 64


def test_missing_data_directory_explains_the_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPE_DEVICES_DATA", str(tmp_path))
    with pytest.raises(QueryError, match="pip install -e"):
        Database()


def test_mcp_self_test_lists_read_only_tools():
    pytest.importorskip("mcp")
    proc = subprocess.run(
        [sys.executable, "-m", "aipe_devices.mcp.server", "--self-test"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["writes_files"] is False
    assert report["tools"] == [
        "database_summary",
        "list_sources",
        "list_devices",
        "get_device",
        "get_values",
        "provenance",
    ]


def test_mcp_tools_answer_and_refuse_unknown_arguments():
    pytest.importorskip("mcp")
    import anyio
    from mcp.client import Client

    from aipe_devices.mcp.server import build_server

    async def scenario():
        async with Client(build_server(Database(ROOT / "data"))) as client:
            tools = (await client.list_tools()).tools
            assert all(t.annotations.read_only_hint for t in tools)
            good = await client.call_tool(
                "get_values",
                {"device": "C2M0025120D", "record_id": EON, "where": {"dc_bus_voltage": "800 V"}},
            )
            payload = json.loads(good.content[0].text)
            assert payload["data_class"] == "manufacturer_model"
            assert payload["sources"][0]["rights"]["status"] == "not_established"
            typo = await client.call_tool(
                "get_device",
                {"device": "C2M0025120D", "devcie": "x"},
            )
            assert typo.is_error is True and "unknown argument" in typo.content[0].text
            bare = await client.call_tool(
                "get_values",
                {"device": "C2M0025120D", "record_id": EON, "where": {"dc_bus_voltage": "800"}},
            )
            assert bare.is_error and "needs a value and a unit" in bare.content[0].text

    anyio.run(scenario)


@pytest.mark.parametrize(
    "manifest",
    [
        f"plugins/claude/{NAME}/.claude-plugin/plugin.json",
        f"plugins/codex/{NAME}/.codex-plugin/plugin.json",
    ],
)
def test_plugin_manifests(manifest):
    from aipe_devices import __version__

    path = ROOT / manifest
    plugin = json.loads(path.read_text(encoding="utf-8"))
    assert plugin["name"] == NAME and plugin["license"] == "MIT"
    assert plugin["version"] == __version__
    assert plugin["repository"] == "https://github.com/AIPE-Labs/AIPE-Semiconductor-Database"
    mcp = json.loads((path.parent.parent / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp["mcpServers"][NAME]["args"] == ["-m", "aipe_devices.mcp.server"]
    assert (path.parent.parent / "skills/semiconductor-data-lookup/SKILL.md").is_file()
    for market, source in (
        (".claude-plugin/marketplace.json", f"./plugins/claude/{NAME}"),
        (".agents/plugins/marketplace.json", f"./plugins/codex/{NAME}"),
    ):
        entry = json.loads((ROOT / market).read_text(encoding="utf-8"))["plugins"][0]
        assert entry["source"] == source and entry["version"] == __version__


def test_plugin_skills_in_sync():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/sync_plugin_skills.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout
