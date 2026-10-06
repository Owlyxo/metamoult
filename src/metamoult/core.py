"""Core data model and format detection for metamoult."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Risk(Enum):
    """How much a metadata field can reveal about you."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        """Sort key: lower is more severe."""
        return {"high": 0, "medium": 1, "low": 2}[self.value]


@dataclass(frozen=True)
class Finding:
    """One piece of metadata found in a file."""

    field: str
    value: str
    risk: Risk
    explanation: str


class UnsupportedFormatError(Exception):
    """Raised when a file is not in a format metamoult can handle."""


_HEIF_BRANDS = {b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx", b"mif1", b"msf1"}
_OFFICE_EXTENSIONS = {".docx": "docx", ".xlsx": "xlsx", ".pptx": "pptx"}


def detect_format(path: str | Path) -> str:
    """Return the format name of a file, judged by content (not just by name).

    Possible results: jpeg, png, webp, heic, pdf, docx, xlsx, pptx.
    """
    path = Path(path)
    with open(path, "rb") as fh:
        head = fh.read(16)

    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[4:8] == b"ftyp" and head[8:12] in _HEIF_BRANDS:
        return "heic"
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"PK") and path.suffix.lower() in _OFFICE_EXTENSIONS:
        return _OFFICE_EXTENSIONS[path.suffix.lower()]
    raise UnsupportedFormatError(f"{path.name}: unsupported or unrecognised file format")


def scan_file(path: str | Path) -> list[Finding]:
    """Scan a file and return its findings, most severe first."""
    # Imported here so that core stays free of import cycles.
    from .scanners import image

    path = Path(path)
    fmt = detect_format(path)
    if fmt in image.IMAGE_FORMATS:
        findings = image.scan_image(path, fmt)
    else:
        raise UnsupportedFormatError(f"{path.name}: {fmt} is not supported yet")
    return sorted(findings, key=lambda f: f.risk.rank)
