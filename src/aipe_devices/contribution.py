"""Community data contributions: the declaration, its validation and its review status.

A contribution is a directory::

    <contribution-id>/
      contribution.json   who contributes, the right to share, the licence, device, setup
      manifest.json       a MeasurementPackage (the existing measurement package format)
      ...                 the original files, each listed with its SHA-256 in the manifest

This module adds only the declaration and the acceptance rules; values, conditions,
instruments and lineage stay in the measurement package. Nothing is estimated or filled.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator

from aipe_devices.domain.base import Model
from aipe_devices.measurement.submission_validator import MeasurementPackage, validate_submission
from aipe_devices.schema.enums import Origin
from aipe_devices.schema.validation import ValidationIssue, ValidationReport

SCHEMA = "aipe-contribution/0.1"
LICENCES = {
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
}
DECLARATION = (
    "I have the right to share these data and I release them under the licence named in "
    "this contribution."
)
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_PACKAGE_BYTES = 20 * 1024 * 1024
DOI_URL = re.compile(r"^https://doi\.org/10\.\d{4,9}/\S+$")
STATUSES = ("submitted", "validated", "reviewed")


class Contributor(Model):
    name: str = Field(min_length=1)
    affiliation: str | None = None
    kind: Literal["university", "manufacturer", "company", "laboratory", "individual"]
    contact: str | None = Field(
        default=None, description="Public contact: ORCID, GitHub handle or e-mail"
    )


class Rights(Model):
    holder: str = Field(min_length=1)
    license: Literal["CC-BY-4.0", "CC0-1.0"]
    declaration: str
    attribution: str | None = None

    @model_validator(mode="after")
    def declared(self):
        if self.declaration.strip() != DECLARATION:
            raise ValueError(f"declaration must read exactly: {DECLARATION}")
        if self.license == "CC-BY-4.0" and not (self.attribution or "").strip():
            raise ValueError("CC-BY-4.0 needs the attribution text to be used")
        return self


class ContributedDevice(Model):
    """Identity down to the level it is known; unknown levels stay null."""

    manufacturer: str = Field(min_length=1)
    part_number: str = Field(min_length=1)
    production_lot_id: str | None = None
    physical_sample_ids: tuple[str, ...] = ()
    date_code: str | None = None
    identity_level: Literal["part", "lot", "sample"]

    @model_validator(mode="after")
    def level_matches(self):
        if self.identity_level == "sample" and not self.physical_sample_ids:
            raise ValueError("identity_level 'sample' needs physical_sample_ids")
        if self.identity_level == "lot" and not self.production_lot_id:
            raise ValueError("identity_level 'lot' needs production_lot_id")
        return self


class DepositFile(Model):
    name: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(ge=0)


class Deposit(Model):
    """A DOI-registered archive (for example Zenodo) holding the original files."""

    doi_url: str
    retrieved_on: date
    files: tuple[DepositFile, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def is_doi(self):
        if not DOI_URL.match(self.doi_url):
            raise ValueError("doi_url must be a https://doi.org/10.... address")
        return self


class Review(Model):
    reviewer: str = Field(min_length=1)
    reviewed_on: date
    scope: str = Field(min_length=1, description="What the reviewer checked")
    notes: str | None = None


class Contribution(Model):
    schema_: Literal["aipe-contribution/0.1"] = Field(alias="schema")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    title: str = Field(min_length=1)
    submitted_on: date
    contributor: Contributor
    rights: Rights
    device: ContributedDevice
    setup: str = Field(min_length=20, description="Test setup and method in plain words")
    package: str = "manifest.json"
    deposit: Deposit | None = None
    synthetic_example: bool = False
    review: Review | None = None


def contribution_status(contribution: Contribution, *, accepted: bool) -> str:
    """``submitted`` until CI has validated it on the default branch; ``reviewed`` only with a named reviewer."""
    if contribution.review is not None and accepted:
        return "reviewed"
    return "validated" if accepted else "submitted"


def load_contribution(directory: str | Path) -> tuple[Contribution, MeasurementPackage]:
    directory = Path(directory)
    contribution = Contribution.model_validate(
        json.loads((directory / "contribution.json").read_bytes())
    )
    package = MeasurementPackage.model_validate(
        json.loads((directory / contribution.package).read_bytes())
    )
    return contribution, package


def _values(package: MeasurementPackage):
    for run in package.runs:
        for record in run.results:
            yield run, record
        for group in run.derived_metrics:
            for record in group.metrics:
                yield run, record


def validate_contribution(
    directory: str | Path, *, allow_synthetic: bool = False
) -> ValidationReport:
    """Acceptance rules for one contribution directory. Errors block a merge.

    ``allow_synthetic`` is for the format examples under ``examples/``; a synthetic
    package is never accepted as contributed data.
    """
    directory = Path(directory)
    issues: list[ValidationIssue] = []

    def issue(code, path, message, severity="error"):
        issues.append(ValidationIssue(code=code, path=path, message=message, severity=severity))

    try:
        contribution, package = load_contribution(directory)
    except (ValidationError, ValueError, OSError) as exc:
        issue("schema", str(directory), str(exc))
        return ValidationReport(issues=tuple(issues))

    if contribution.synthetic_example and not allow_synthetic:
        issue("synthetic", "contribution.json", "a synthetic example is not contributed data")
    if contribution.id != directory.name:
        issue("id", "contribution.json", "id must equal the directory name")
    issues.extend(validate_submission(package, root=directory).issues)

    # Rights: every source carries the declared licence and allows redistribution.
    for source in package.sources:
        access = source.access
        if access.license != contribution.rights.license:
            issue("licence", source.id, f"source licence must be {contribution.rights.license}")
        if access.redistribution_allowed is not True or access.commercial_use_allowed is not True:
            issue(
                "licence",
                source.id,
                "redistribution_allowed and commercial_use_allowed must be true under "
                "CC BY 4.0 / CC0",
            )
        if (access.owner or "").strip() != contribution.rights.holder.strip():
            issue("licence", source.id, "source owner must equal rights.holder")

    # Original files are archived at acceptance: in the package or in a DOI deposit.
    listed = {Path(a.uri).as_posix() for a in package.artifacts}
    if not package.artifacts and contribution.deposit is None:
        issue("originals", "manifest.json", "no original file is archived (artifacts or deposit)")
    reserved = {"contribution.json", contribution.package}
    total = 0
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        relative = path.relative_to(directory).as_posix()
        size = path.stat().st_size
        total += size
        if size > MAX_FILE_BYTES:
            issue(
                "size",
                relative,
                f"larger than {MAX_FILE_BYTES // 2**20} MB: keep it in the DOI deposit and "
                "list it under deposit.files",
            )
        if relative not in reserved and relative not in listed:
            issue("unlisted_file", relative, "file is not listed in the manifest artifacts")
    if total > MAX_PACKAGE_BYTES:
        issue("size", str(directory), f"package exceeds {MAX_PACKAGE_BYTES // 2**20} MB")

    # Device identity and per-value completeness.
    samples = set(contribution.device.physical_sample_ids)
    for run in package.runs:
        if run.physical_sample_id and samples and run.physical_sample_id not in samples:
            issue("sample", run.id, "run sample is not listed in device.physical_sample_ids")
        if not run.instrument_setup.instruments:
            issue("instruments", run.id, "the instruments used are not listed")
        if not any(
            getattr(run.condition, name) is not None
            for name in type(run.condition).model_fields
            if name not in {"gate_state", "extensions"}
        ):
            issue("conditions", run.id, "the operating condition of the run is empty")
    count = 0
    for run, record in _values(package):
        count += 1
        origin = record.provenance.origin
        if contribution.synthetic_example:
            if origin != Origin.SYNTHETIC:
                issue("origin", record.id, "a synthetic example may only hold synthetic values")
        elif origin != Origin.MEASURED:
            issue("origin", record.id, f"contributed values must be 'measured', not '{origin}'")
        if record.uncertainty is None:
            issue("uncertainty", record.id, "no uncertainty is stated", "warning")
    if count == 0:
        issue("values", "manifest.json", "the package holds no value")
    return ValidationReport(issues=tuple(issues))
