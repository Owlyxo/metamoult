"""Scanner for image files (JPEG, PNG, WebP; HEIC is added separately)."""

from __future__ import annotations

import zlib
from pathlib import Path

from .. import containers, jpeg
from ..core import Finding
from ..risk import make_finding
from . import iptc, xmp
from .exif import scan_exif

IMAGE_FORMATS = {"jpeg", "png", "webp"}

_MAX_TEXT = 1_000_000  # stop decompressing PNG text after 1 MB (guards against zip bombs)


def scan_image(path: Path, fmt: str) -> list[Finding]:
    """Scan an image file of the given format."""
    scanners = {"jpeg": _scan_jpeg, "png": _scan_png, "webp": _scan_webp}
    if fmt not in scanners:
        raise ValueError(f"unsupported image format: {fmt}")
    return scanners[fmt](path)


def with_exif_header(block: bytes) -> bytes:
    """Make sure a raw EXIF block starts with the 'Exif\\0\\0' header."""
    return block if block.startswith(jpeg.EXIF_HEADER) else jpeg.EXIF_HEADER + block


# --- JPEG -----------------------------------------------------------------


def _scan_jpeg(path: Path) -> list[Finding]:
    segments, _tail = jpeg.parse_jpeg(path.read_bytes())
    findings: list[Finding] = []
    for seg in segments:
        if jpeg.is_exif(seg):
            findings += scan_exif(seg.data)
        elif jpeg.is_xmp(seg):
            if seg.data.startswith(jpeg.XMP_HEADER):
                findings += xmp.scan_xmp(seg.data[len(jpeg.XMP_HEADER):])
            else:
                findings.append(make_finding("XMP:Extension", f"<{len(seg.data)} bytes>"))
        elif seg.marker == jpeg.APP13:
            findings += iptc.scan_iptc(seg.data)
        elif seg.marker == jpeg.COM:
            findings.append(make_finding("JPEG:Comment", seg.data.decode("utf-8", "replace")))
        elif jpeg.is_metadata(seg):
            findings.append(
                make_finding(f"JPEG:APP{seg.marker - 0xE0}", f"<{len(seg.data)} bytes>")
            )
    return findings


# --- PNG ------------------------------------------------------------------

PNG_METADATA_CHUNKS = {b"eXIf", b"tEXt", b"zTXt", b"iTXt", b"tIME"}


def _inflate(data: bytes) -> bytes:
    """Decompress zlib data, refusing to expand beyond _MAX_TEXT bytes."""
    return zlib.decompressobj().decompress(data, _MAX_TEXT)


def _png_text(chunk: containers.PngChunk) -> tuple[str, str]:
    """Return (keyword, text) of a tEXt, zTXt or iTXt chunk."""
    body = chunk.body
    keyword, _, rest = body.partition(b"\x00")
    name = keyword.decode("latin-1")
    if chunk.type == b"tEXt":
        return name, rest.decode("latin-1")
    if chunk.type == b"zTXt":
        return name, _inflate(rest[1:]).decode("latin-1")
    compressed, rest = rest[0], rest[2:]  # iTXt: compression flag, then method byte
    _lang, _, rest = rest.partition(b"\x00")
    _translated, _, text = rest.partition(b"\x00")
    return name, (_inflate(text) if compressed else text).decode("utf-8", "replace")


def _decode_raw_profile(text: str) -> bytes:
    """Decode the hex 'Raw profile type ...' text that ImageMagick/ExifTool write."""
    lines = text.strip().split("\n")
    return bytes.fromhex("".join(lines[2:]).replace(" ", ""))


def _scan_png(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for chunk in containers.parse_png(path.read_bytes()):
        if chunk.type == b"eXIf":
            findings += scan_exif(with_exif_header(chunk.body))
        elif chunk.type == b"tIME" and len(chunk.body) == 7:
            year, month, day, hour, minute, second = (
                int.from_bytes(chunk.body[:2], "big"), *chunk.body[2:])
            findings.append(make_finding(
                "PNG:ModifyDate", f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"))
        elif chunk.type in (b"tEXt", b"zTXt", b"iTXt"):
            try:
                keyword, text = _png_text(chunk)
            except (zlib.error, IndexError, ValueError):
                findings.append(make_finding("PNG:Text", "<could not be read>"))
                continue
            if keyword == "XML:com.adobe.xmp":
                findings += xmp.scan_xmp(text.encode("utf-8"))
            elif keyword.lower() == "raw profile type exif":
                findings += scan_exif(with_exif_header(_decode_raw_profile(text)))
            elif keyword.lower() == "raw profile type xmp":
                findings += xmp.scan_xmp(_decode_raw_profile(text))
            else:
                findings.append(make_finding(f"PNG:{keyword}", text))
    return findings


# --- WebP -----------------------------------------------------------------

WEBP_METADATA_CHUNKS = {b"EXIF", b"XMP "}


def _scan_webp(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for chunk in containers.parse_webp(path.read_bytes()):
        if chunk.fourcc == b"EXIF":
            findings += scan_exif(with_exif_header(chunk.body))
        elif chunk.fourcc == b"XMP ":
            findings += xmp.scan_xmp(chunk.body)
    return findings
