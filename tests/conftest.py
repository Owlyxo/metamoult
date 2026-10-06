"""Shared test helpers. All test files are generated here with invented data."""

from __future__ import annotations

import io

import piexif
import pytest
from PIL import Image

from metamoult import jpeg

XMP_PACKET = (
    b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
    b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    b'<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/" '
    b'xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmp:CreatorTool="FakeEditor 9.0">'
    b'</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
)


def fake_exif(orientation: int = 1) -> bytes:
    """EXIF block with invented camera, owner, serial and GPS data."""
    return piexif.dump({
        "0th": {
            piexif.ImageIFD.Make: b"FakeCam",
            piexif.ImageIFD.Model: b"FC-1000",
            piexif.ImageIFD.Software: b"FakeEditor 9.0",
            piexif.ImageIFD.Artist: b"Jane Example",
            piexif.ImageIFD.Orientation: orientation,
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: b"2020:01:02 03:04:05",
            piexif.ExifIFD.BodySerialNumber: b"SN123456",
            piexif.ExifIFD.ISOSpeedRatings: 200,
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N",
            piexif.GPSIFD.GPSLatitude: ((48, 1), (51, 1), (3024, 100)),
            piexif.GPSIFD.GPSLongitudeRef: b"W",
            piexif.GPSIFD.GPSLongitude: ((2, 1), (17, 1), (4000, 100)),
        },
    })


def make_jpeg(path, *, exif: bool = True, orientation: int = 1, comment: bool = True,
              xmp: bool = True, size=(64, 48)):
    """Write a small JPEG with invented metadata and return the path."""
    buf = io.BytesIO()
    Image.effect_noise(size, 60).convert("RGB").save(buf, "JPEG", quality=90)
    segments, tail = jpeg.parse_jpeg(buf.getvalue())
    extra = []
    if exif:
        extra.append(jpeg.Segment(jpeg.APP1, fake_exif(orientation)))
    if xmp:
        extra.append(jpeg.Segment(jpeg.APP1, jpeg.XMP_HEADER + XMP_PACKET))
    if comment:
        extra.append(jpeg.Segment(jpeg.COM, b"shot at Jane's house"))
    # Insert after the leading JFIF segment so the order stays valid.
    segments[1:1] = extra
    path.write_bytes(jpeg.build_jpeg(segments, tail))
    return path


@pytest.fixture
def jpeg_file(tmp_path):
    return make_jpeg(tmp_path / "photo.jpg")
