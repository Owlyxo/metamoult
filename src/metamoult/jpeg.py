"""Minimal JPEG segment reader/writer.

Lets us look at (and remove) metadata segments without decoding or
re-compressing the picture data, so cleaning is lossless.
"""

from __future__ import annotations

from dataclasses import dataclass

EXIF_HEADER = b"Exif\x00\x00"
XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"
XMP_EXT_HEADER = b"http://ns.adobe.com/xmp/extension/\x00"
ICC_HEADER = b"ICC_PROFILE\x00"

APP0, APP1, APP2, APP13, APP14, COM, SOS = 0xE0, 0xE1, 0xE2, 0xED, 0xEE, 0xFE, 0xDA
# Markers that have no length field.
_STANDALONE = {0x01} | set(range(0xD0, 0xD8))


@dataclass
class Segment:
    """One JPEG segment. `data` excludes the marker and length bytes."""

    marker: int
    data: bytes | None  # None for markers without payload


def parse_jpeg(data: bytes) -> tuple[list[Segment], bytes]:
    """Split a JPEG into header segments and the remaining picture data.

    Returns (segments, tail). `tail` starts at the SOS marker and holds the
    compressed image, which is never touched.
    """
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("not a JPEG file")
    segments: list[Segment] = []
    pos = 2
    while pos < len(data):
        if data[pos] != 0xFF:
            raise ValueError("corrupt JPEG: expected a marker")
        while pos < len(data) and data[pos] == 0xFF:  # skip fill bytes
            pos += 1
        marker = data[pos]
        pos += 1
        if marker == SOS or marker == 0xD9:
            return segments, b"\xff" + bytes([marker]) + data[pos:]
        if marker in _STANDALONE:
            segments.append(Segment(marker, None))
            continue
        length = int.from_bytes(data[pos:pos + 2], "big")
        if length < 2 or pos + length > len(data):
            raise ValueError("corrupt JPEG: bad segment length")
        segments.append(Segment(marker, data[pos + 2:pos + length]))
        pos += length
    raise ValueError("corrupt JPEG: no image data")


def build_jpeg(segments: list[Segment], tail: bytes) -> bytes:
    """Reassemble a JPEG from segments and the untouched picture data."""
    out = bytearray(b"\xff\xd8")
    for seg in segments:
        out += b"\xff" + bytes([seg.marker])
        if seg.data is not None:
            out += (len(seg.data) + 2).to_bytes(2, "big") + seg.data
    out += tail
    return bytes(out)


def is_exif(seg: Segment) -> bool:
    return seg.marker == APP1 and seg.data is not None and seg.data.startswith(EXIF_HEADER)


def is_xmp(seg: Segment) -> bool:
    return seg.marker == APP1 and seg.data is not None and seg.data.startswith(
        (XMP_HEADER, XMP_EXT_HEADER)
    )


def is_icc(seg: Segment) -> bool:
    return seg.marker == APP2 and seg.data is not None and seg.data.startswith(ICC_HEADER)


def is_metadata(seg: Segment) -> bool:
    """True for segments that carry metadata and are safe to drop.

    Kept on purpose: JFIF (APP0), ICC colour profile (APP2) and Adobe (APP14),
    because removing them would change how the picture looks.
    """
    if seg.data is None:
        return False
    if seg.marker in (APP0, APP14):
        return False
    if is_icc(seg):
        return False
    return seg.marker == COM or 0xE1 <= seg.marker <= 0xEF
