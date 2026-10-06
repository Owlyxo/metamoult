"""Scanner for PDF files: the document info dictionary and XMP metadata."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from ..core import Finding, UnsupportedFormatError
from ..risk import make_finding
from . import xmp


def open_pdf(path: Path) -> PdfReader:
    """Open a PDF; password-free encryption is handled, real passwords are not."""
    reader = PdfReader(str(path))
    if reader.is_encrypted and not reader.decrypt(""):
        raise UnsupportedFormatError(f"{path.name}: the PDF is password-protected")
    return reader


def scan_pdf(path: Path) -> list[Finding]:
    reader = open_pdf(path)
    findings: list[Finding] = []

    for key, value in (reader.metadata or {}).items():
        findings.append(make_finding(f"PDF:{str(key).lstrip('/')}", value))

    metadata = reader.trailer["/Root"].get("/Metadata")
    if metadata is not None:
        findings += xmp.scan_xmp(metadata.get_object().get_data())

    ids = reader.trailer.get("/ID")
    if ids:
        value = ", ".join(i.get_object().hex() if isinstance(i.get_object(), bytes)
                          else str(i) for i in ids)
        findings.append(make_finding("PDF:ID", value))
    return findings
