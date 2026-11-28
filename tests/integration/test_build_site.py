"""Static Data Explorer build: generated files carry source, rights and review status."""

import importlib.util
import json
import re

import pytest
from conftest import ROOT


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = tmp_path_factory.mktemp("site") / "out"
    assert module.build(out)["devices"] == 182
    return out


def read(site, name):
    return json.loads((site / "data" / name).read_text(encoding="utf-8"))


def test_summary_and_index(site):
    summary = read(site, "summary.json")
    assert summary["measured_records"] == 0 and summary["reviewed_devices"] == 0
    assert summary["collections"]["canonical"]["devices"] == 163
    devices = read(site, "devices.json")
    assert len(devices) == 182
    assert all((site / "data/devices" / f"{d['device_id']}.json").is_file() for d in devices)


def test_every_device_file_states_source_and_rights(site):
    for path in sorted((site / "data/devices").glob("*.json")):
        device = json.loads(path.read_text(encoding="utf-8"))
        assert device["sources"] and device["review_status"] == "unreviewed"
        assert all(s["rights"]["status"] == "not_established" for s in device["sources"])
        assert (ROOT / device["record_path"]).is_file()
        for record in device["records"]:
            assert record["data_class"] in {"manufacturer_model", "manufacturer_datasheet"}
            assert record["sources"]


def test_curve_values_are_copied_unchanged(site):
    device = json.loads((site / "data/devices/wolfspeed_c2m0025120d.json").read_text())
    stored = json.loads((ROOT / "data/canonical/wolfspeed_c2m0025120d.json").read_text())
    curve = next(r for r in device["records"] if r["record_id"].endswith(":Eon:0"))
    assert curve["values"] == stored["switching"]["curves"][0]["values"]
    assert [a["values"] for a in curve["axes"]] == [
        a["values"] for a in stored["switching"]["curves"][0]["axes"]
    ]


def test_frontend_is_self_contained_and_states_the_rights(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    script = (site / "assets/app.js").read_text(encoding="utf-8")
    assert (site / ".nojekyll").is_file() and not (site / "README.md").exists()
    assert "redistribution rights are not established" in html
    assert "Redistribution rights not established" in script
    assert "Not reviewed by a person" in script
    external = set(re.findall(r'(?:src|href)="(https?://[^"/]+)', html))
    assert not [u for u in re.findall(r'<script[^>]+src="([^"]+)"', html) if u.startswith("http")]
    assert external <= {
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com",
        "https://github.com",
        "https://aipel.co.uk",
        "https://aipe-labs.github.io",
    }


def test_contributions_page_data(site, tmp_path):
    assert read(site, "contributions.json") == []
    spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts/build_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.build(tmp_path / "preview", contributed=ROOT / "examples/contribution")
    (item,) = json.loads((tmp_path / "preview/data/contributions.json").read_text())
    assert item["contribution_status"] == "validated" and item["rights"]["license"] == "CC-BY-4.0"
    script = (site / "assets/app.js").read_text(encoding="utf-8")
    assert "No person has confirmed the values" in script


def test_pages_workflow_is_manual_only():
    text = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    trigger = text.split("permissions:")[0]
    assert "workflow_dispatch" in trigger and "push" not in trigger.split("on:")[1]
