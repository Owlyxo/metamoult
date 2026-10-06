"""Turn a raw EXIF block into findings (works for JPEG, PNG, WebP and HEIC)."""

from __future__ import annotations

import piexif

from ..core import Finding
from ..risk import make_finding

_GROUPS = {"0th": "IFD0", "Exif": "EXIF", "GPS": "GPS", "Interop": "Interop", "1st": "IFD1"}
# Pointers and offsets that only describe the file layout.
_STRUCTURAL = {"ExifTag", "GPSTag", "InteroperabilityTag", "JPEGInterchangeFormat",
               "JPEGInterchangeFormatLength"}
# GPS tags that are folded into one combined "GPS:Position" finding.
_POSITION_TAGS = {"GPSLatitude", "GPSLatitudeRef", "GPSLongitude", "GPSLongitudeRef"}
_BULKY = {"MakerNote", "PrintImageMatching", "XPKeywords"}


def _rational(r: tuple[int, int]) -> float:
    return r[0] / r[1] if r[1] else 0.0


def _to_degrees(dms, ref: bytes) -> float:
    degrees = sum(_rational(part) / 60 ** i for i, part in enumerate(dms))
    return -degrees if ref in (b"S", b"W") else degrees


def _format(name: str, value: object) -> str:
    if isinstance(value, bytes):
        if name in _BULKY or len(value) > 64:
            return f"<{len(value)} bytes>"
        if name == "UserComment":  # 8-byte character-set prefix
            value = value[8:]
        return value.rstrip(b"\x00").decode("utf-8", "replace")
    if isinstance(value, tuple):
        if len(value) == 2 and all(isinstance(v, int) for v in value):
            return str(round(_rational(value), 6))  # a single rational number
        return ", ".join(_format(name, v) for v in value)
    return str(value)


def _position(gps: dict) -> str | None:
    """Combine latitude and longitude into 'lat, lon' (plain text, no network)."""
    try:
        lat = _to_degrees(gps[piexif.GPSIFD.GPSLatitude], gps[piexif.GPSIFD.GPSLatitudeRef])
        lon = _to_degrees(gps[piexif.GPSIFD.GPSLongitude], gps[piexif.GPSIFD.GPSLongitudeRef])
    except (KeyError, TypeError, ZeroDivisionError):
        return None
    return f"{lat:.6f}, {lon:.6f}"


def scan_exif(exif_bytes: bytes) -> list[Finding]:
    """Return findings for an EXIF block (bytes starting with 'Exif\\0\\0' or 'II'/'MM')."""
    try:
        tags = piexif.load(exif_bytes)
    except Exception:  # piexif raises various errors on damaged data
        return [make_finding("EXIF:Block", "<present, but could not be read>")]

    findings: list[Finding] = []
    for ifd, group in _GROUPS.items():
        for tag, value in tags.get(ifd, {}).items():
            name = piexif.TAGS[ifd].get(tag, {}).get("name", f"Tag{tag}")
            if name in _STRUCTURAL or (ifd == "GPS" and name in _POSITION_TAGS):
                continue
            findings.append(make_finding(f"{group}:{name}", _format(name, value)))

    position = _position(tags.get("GPS", {}))
    if position:
        findings.append(make_finding("GPS:Position", position))
    if tags.get("thumbnail"):
        findings.append(make_finding("EXIF:Thumbnail", f"<{len(tags['thumbnail'])} bytes>"))
    return findings
