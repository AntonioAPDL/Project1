#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


SOFTWARE_MANIFEST_REL = "artifacts/software_availability/software_availability_manifest.json"
SOFTWARE_CONTRACT_REL = "repro/run/REVISION_SOFTWARE_REPRODUCIBILITY_CONTRACT_20260615.md"
ARTICLE_SOFTWARE_DOC_REL = "docs/software_availability_contract.md"
CRAN_EXDQLM_URL = "https://CRAN.R-project.org/package=exdqlm"
CRAN_EXDQLM_DOI_URL = "https://doi.org/10.32614/CRAN.package.exdqlm"
PROJECT1_URL = "https://github.com/AntonioAPDL/Project1"

PENDING_ARCHIVE_STATUS = "pending_final_release"
FINAL_ARCHIVE_STATUS = "archived_final_release"
PENDING_VALUE = "pending"
DOI_RE = re.compile(r"^(?:https://doi\.org/)?10\.\d{4,9}/\S+$")


@dataclass(frozen=True)
class ArchiveStatusCheck:
    ok: bool
    mode: str
    detail: str
    doi: str

    @property
    def is_pending(self) -> bool:
        return self.mode == "pending"

    @property
    def is_final(self) -> bool:
        return self.mode == "final"


def _clean(value: Any) -> str:
    return str(value or "").strip()


def check_archive_status(archive: dict[str, Any]) -> ArchiveStatusCheck:
    status = _clean(archive.get("workflow_archive_status"))
    doi = _clean(archive.get("workflow_archive_doi"))
    service = _clean(archive.get("workflow_archive_service"))
    release_tag = _clean(archive.get("workflow_archive_release_tag"))

    if (
        status == PENDING_ARCHIVE_STATUS
        and doi == PENDING_VALUE
        and service == PENDING_VALUE
        and release_tag == PENDING_VALUE
    ):
        return ArchiveStatusCheck(True, "pending", "workflow archive DOI is pending final release", doi)

    final_fields = [status == FINAL_ARCHIVE_STATUS, bool(DOI_RE.match(doi)), service not in {"", PENDING_VALUE}, release_tag not in {"", PENDING_VALUE}]
    if all(final_fields):
        return ArchiveStatusCheck(True, "final", f"workflow archive DOI recorded: {doi}", doi)

    detail = (
        "archive status must be either fully pending "
        f"({PENDING_ARCHIVE_STATUS}/pending fields) or fully final "
        f"({FINAL_ARCHIVE_STATUS}/valid DOI/service/tag); "
        f"got status={status!r}, doi={doi!r}, service={service!r}, release_tag={release_tag!r}"
    )
    return ArchiveStatusCheck(False, "invalid", detail, doi)
