"""Scanner for image files (JPEG so far)."""

from __future__ import annotations

from pathlib import Path

from .. import jpeg
from ..core import Finding
from ..risk import make_finding
from . import iptc, xmp
from .exif import scan_exif

IMAGE_FORMATS = {"jpeg"}


def scan_image(path: Path, fmt: str) -> list[Finding]:
    """Scan an image file of the given format."""
    if fmt == "jpeg":
        return _scan_jpeg(path)
    raise ValueError(f"unsupported image format: {fmt}")


def _scan_jpeg(path: Path) -> list[Finding]:
    segments, _tail = jpeg.parse_jpeg(path.read_bytes())
    findings: list[Finding] = []
    for seg in segments:
        if jpeg.is_exif(seg):
            findings += scan_exif(seg.data)
        elif jpeg.is_xmp(seg):
            findings += xmp.scan_xmp(seg.data[len(jpeg.XMP_HEADER):]) \
                if seg.data.startswith(jpeg.XMP_HEADER) else \
                [make_finding("XMP:Extension", f"<{len(seg.data)} bytes>")]
        elif seg.marker == jpeg.APP13:
            findings += iptc.scan_iptc(seg.data)
        elif seg.marker == jpeg.COM:
            findings.append(make_finding("JPEG:Comment", seg.data.decode("utf-8", "replace")))
        elif jpeg.is_metadata(seg):
            findings.append(
                make_finding(f"JPEG:APP{seg.marker - 0xE0}", f"<{len(seg.data)} bytes>")
            )
    return findings
