"""Contribution window: acceptance rules, status, API and generated lists."""

import json
import shutil
import subprocess
import sys

import pytest
from conftest import ROOT

from aipe_devices.api import Database, QueryError
from aipe_devices.contribution import (
    DECLARATION,
    contribution_status,
    load_contribution,
    validate_contribution,
)

EXAMPLE = ROOT / "examples/contribution/example-synthetic-dpt"


@pytest.fixture
def package(tmp_path):
    target = tmp_path / EXAMPLE.name
    shutil.copytree(EXAMPLE, target)
    return target


def edit(package, name, change):
    path = package / name
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def codes(package, **kwargs):
    kwargs.setdefault("allow_synthetic", True)
    return {
        i.code for i in validate_contribution(package, **kwargs).issues if i.severity == "error"
    }


def test_example_is_valid_only_as_an_example(package):
    assert codes(package) == set()
    assert codes(package, allow_synthetic=False) == {"synthetic"}


def test_example_is_reproducible():
    before = {p: p.read_bytes() for p in EXAMPLE.rglob("*") if p.is_file()}
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate_contribution_example.py")], check=True
    )
    assert before == {p: p.read_bytes() for p in EXAMPLE.rglob("*") if p.is_file()}


def test_no_licence_no_merge(package):
    edit(package, "contribution.json", lambda c: c["rights"].update(license="proprietary"))
    assert codes(package) == {"schema"}


def test_declaration_must_be_made_verbatim(package):
    edit(package, "contribution.json", lambda c: c["rights"].update(declaration="ok"))
    assert codes(package) == {"schema"}
    assert DECLARATION.startswith("I have the right to share")


def test_cc_by_needs_attribution(package):
    edit(package, "contribution.json", lambda c: c["rights"].update(attribution=None))
    assert codes(package) == {"schema"}


def test_cc0_is_allowed(package):
    edit(package, "contribution.json", lambda c: c["rights"].update(license="CC0-1.0"))
    edit(
        package,
        "manifest.json",
        lambda m: [s["access"].update(license="CC0-1.0") for s in m["sources"]],
    )
    assert codes(package) == set()


def test_source_rights_must_match_the_declaration(package):
    edit(
        package,
        "manifest.json",
        lambda m: m["sources"][0]["access"].update(redistribution_allowed=None),
    )
    assert codes(package) == {"licence"}


def test_changed_original_file_is_detected(package):
    path = next((package / "original").iterdir())
    path.write_bytes(path.read_bytes() + b"0,0,0\n")
    assert codes(package) == {"artifact_integrity"}


def test_unlisted_file_is_refused(package):
    (package / "original/notes.txt").write_text("not in the manifest", encoding="utf-8")
    assert codes(package) == {"unlisted_file"}


def test_original_files_are_required(package):
    def strip(manifest):
        manifest["artifacts"] = []

    edit(package, "manifest.json", strip)
    assert "originals" in codes(package)


def test_large_file_belongs_in_a_deposit(package):
    (package / "original/big.bin").write_bytes(b"\0" * (5 * 1024 * 1024 + 1))
    assert "size" in codes(package)


def test_deposit_must_be_a_doi(package):
    deposit = {
        "doi_url": "https://drive.example.com/file",
        "retrieved_on": "2026-11-28",
        "files": [{"name": "a.csv", "sha256": "0" * 64, "size": 1}],
    }
    edit(package, "contribution.json", lambda c: c.update(deposit=deposit))
    assert codes(package) == {"schema"}
    deposit["doi_url"] = "https://doi.org/10.5281/zenodo.1234567"
    edit(package, "contribution.json", lambda c: c.update(deposit=deposit))
    assert codes(package) == set()


def test_instruments_and_conditions_are_required(package):
    def strip(manifest):
        run = manifest["runs"][0]
        run["instrument_setup"]["instruments"] = []
        run["condition"] = {}

    edit(package, "manifest.json", strip)
    assert codes(package) == {"instruments", "conditions"}


def test_real_contribution_must_be_measured(package):
    edit(package, "contribution.json", lambda c: c.update(synthetic_example=False))
    assert codes(package, allow_synthetic=False) == {"origin"}


def test_identity_level_must_be_backed(package):
    edit(package, "contribution.json", lambda c: c["device"].update(physical_sample_ids=[]))
    assert codes(package) == {"schema"}
    edit(
        package,
        "contribution.json",
        lambda c: c["device"].update(identity_level="part", physical_sample_ids=[]),
    )
    assert codes(package) == set()


def test_missing_uncertainty_is_a_warning_not_a_guess(package):
    def strip(manifest):
        for metric in manifest["runs"][0]["derived_metrics"][0]["metrics"]:
            metric["uncertainty"] = None

    edit(package, "manifest.json", strip)
    report = validate_contribution(package, allow_synthetic=True)
    assert report.valid and {i.code for i in report.issues} == {"uncertainty"}


def test_status_is_reviewed_only_with_a_named_reviewer(package):
    contribution, _ = load_contribution(package)
    assert contribution_status(contribution, accepted=False) == "submitted"
    assert contribution_status(contribution, accepted=True) == "validated"
    review = {"reviewer": "F. Li", "reviewed_on": "2026-12-01", "scope": "Plausibility of Eon"}
    edit(package, "contribution.json", lambda c: c.update(review=review))
    contribution, _ = load_contribution(package)
    assert contribution_status(contribution, accepted=True) == "reviewed"
    assert contribution_status(contribution, accepted=False) == "submitted"


def test_api_serves_contributions_as_their_own_class(package):
    db = Database(ROOT / "data", contributed=package.parent)
    (header,) = db.list_contributions()
    assert header["collection"] == "contributed"
    assert header["contribution_status"] == "validated" and header["review"] is None
    assert header["rights"]["status"] == "open_licence"
    assert header["rights"]["license"] == "CC-BY-4.0" and header["rights"]["attribution"]
    detail = db.get_contribution(header["contribution_id"])
    eon = next(v for v in detail["values"] if v["name"] == "Eon")
    assert eon["unit"] == "J" and eon["condition"]["dc_bus_voltage"]["value"] == 800.0
    assert eon["uncertainty"]["standard"] == 1.2e-05 and eon["physical_sample_id"] == "EX-S01"
    assert eon["instruments"] and detail["files"][0]["sha256"]
    assert db.summary()["contributed"]["by_status"]["validated"] == 1
    assert db.list_contributions(status="reviewed") == []
    with pytest.raises(QueryError):
        db.get_contribution("missing")


def test_invalid_contribution_is_served_as_submitted(package):
    path = next((package / "original").iterdir())
    path.write_bytes(b"tampered")
    db = Database(ROOT / "data", contributed=package.parent)
    assert db.list_contributions()[0]["contribution_status"] == "submitted"
    assert db.get_contribution(package.name)["validation_issues"]


def test_repository_has_no_unvalidated_contribution():
    directories = [p for p in (ROOT / "data/contributed").iterdir() if p.is_dir()]
    for directory in directories:
        validate_contribution(directory).raise_for_errors()
    assert Database(ROOT / "data").summary()["contributed"]["contributions"] == len(directories)


def test_wanted_list_is_current():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/generate_wanted.py"), "--check"])
    assert proc.returncode == 0


def test_issue_form_carries_the_declaration_and_licences():
    form = (ROOT / ".github/ISSUE_TEMPLATE/contribute-data.yml").read_text(encoding="utf-8")
    assert DECLARATION in form and "CC-BY-4.0" in form and "CC0-1.0" in form
    assert "https://doi.org/" in form
