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


def make_png(path, *, metadata: bool = True, size=(32, 24)):
    """Write a small PNG with invented text, EXIF, XMP and a modification time."""
    import struct
    import zlib

    from PIL.PngImagePlugin import PngInfo

    from metamoult import containers

    img = Image.effect_noise(size, 60).convert("RGB")
    info = PngInfo()
    kwargs = {}
    if metadata:
        info.add_text("Author", "Jane Example")
        info.add_text("Comment", "taken at Jane's house")
        info.add_text("Creation Time", "2020-01-02T03:04:05")
        info.add_itxt("XML:com.adobe.xmp", XMP_PACKET.decode(), zip=True)
        kwargs = {"pnginfo": info, "exif": fake_exif()}
    buf = io.BytesIO()
    img.save(buf, "PNG", **kwargs)
    chunks = containers.parse_png(buf.getvalue())
    if metadata:  # Pillow does not write tIME, so add one by hand
        body = struct.pack(">HBBBBB", 2020, 1, 2, 3, 4, 5)
        raw = struct.pack(">I", 7) + b"tIME" + body + struct.pack(">I", zlib.crc32(b"tIME" + body))
        chunks.insert(1, containers.PngChunk(b"tIME", body, raw))
    path.write_bytes(containers.build_png(chunks))
    return path


def make_webp(path, *, metadata: bool = True, size=(32, 24)):
    """Write a small lossless WebP with invented EXIF and XMP."""
    img = Image.effect_noise(size, 60).convert("RGB")
    kwargs = {"exif": fake_exif(), "xmp": XMP_PACKET} if metadata else {}
    img.save(path, "WEBP", lossless=True, **kwargs)
    return path


def make_heic(path, *, metadata: bool = True, size=(64, 48)):
    """Write a small HEIC with invented EXIF and XMP."""
    import pillow_heif

    img = Image.effect_noise(size, 60).convert("RGB")
    kwargs = {"exif": fake_exif(), "xmp": XMP_PACKET} if metadata else {}
    pillow_heif.from_pillow(img).save(str(path), quality=90, **kwargs)
    return path


def make_pdf(path, *, metadata: bool = True):
    """Write a one-page PDF with invented info-dictionary and XMP metadata."""
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject

    writer = PdfWriter()
    writer.add_blank_page(200, 200)
    if metadata:
        writer.add_metadata({
            "/Author": "Jane Example",
            "/Creator": "FakeEditor",
            "/Title": "Jane's tax return",
            "/CreationDate": "D:20200102030405+01'00'",
        })
        stream = DecodedStreamObject()
        stream.set_data(XMP_PACKET)
        stream.update({NameObject("/Type"): NameObject("/Metadata"),
                       NameObject("/Subtype"): NameObject("/XML")})
        writer._root_object[NameObject("/Metadata")] = writer._add_object(stream)
    else:
        writer.metadata = None
    with open(path, "wb") as fh:
        writer.write(fh)
    return path


_CORE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    '<dc:title>Jane budget</dc:title><dc:creator>Jane Example</dc:creator>'
    '<cp:lastModifiedBy>John Sample</cp:lastModifiedBy>'
    '<dcterms:created xsi:type="dcterms:W3CDTF">2020-01-02T03:04:05Z</dcterms:created>'
    '</cp:coreProperties>'
)
_APP = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
    '<Application>FakeOffice</Application><AppVersion>16.0</AppVersion>'
    '<Company>Example Corp</Company><Pages>3</Pages></Properties>'
)
_CUSTOM = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
    '<property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="ProjectCode">'
    '<vt:lpwstr>X-42</vt:lpwstr></property></Properties>'
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="MAIN"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail" Target="docProps/thumbnail.jpeg"/>'
    '</Relationships>'
)
_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="jpeg" ContentType="image/jpeg"/></Types>'
)
_OFFICE_MAIN = {
    "docx": ("word/document.xml",
             '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
             '<w:body><w:p><w:ins w:id="1" w:author="Jane Example" w:date="2020-01-02T03:04:05Z">'
             '<w:r><w:t>Hello</w:t></w:r></w:ins></w:p></w:body></w:document>'),
    "xlsx": ("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>'),
    "pptx": ("ppt/presentation.xml", '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>'),
}


def make_office(path, *, metadata: bool = True):
    """Write a minimal docx/xlsx/pptx (chosen by file extension) with invented metadata."""
    import zipfile

    kind = path.suffix[1:]
    main_name, main_xml = _OFFICE_MAIN[kind]
    if not metadata:
        main_xml = main_xml.replace(' w:author="Jane Example"', "")
    parts = {
        "[Content_Types].xml": _CONTENT_TYPES,
        "_rels/.rels": _RELS.replace("MAIN", main_name),
        main_name: main_xml,
    }
    if metadata:
        parts["docProps/core.xml"] = _CORE
        parts["docProps/app.xml"] = _APP
        parts["docProps/custom.xml"] = _CUSTOM
        parts["docProps/thumbnail.jpeg"] = "fake preview image bytes"
        if kind == "xlsx":
            parts["xl/comments1.xml"] = "<comments><authors><author>Jane Example</author></authors></comments>"
        if kind == "pptx":
            parts["ppt/commentAuthors.xml"] = '<p:cmAuthorLst xmlns:p="x"><p:cmAuthor id="0" name="Jane Example" initials="JE"/></p:cmAuthorLst>'
    else:
        parts["_rels/.rels"] = parts["_rels/.rels"].split("<Relationship Id=\"rId2\"")[0] + "</Relationships>"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, text in parts.items():
            zf.writestr(zipfile.ZipInfo(name, date_time=(2020, 1, 2, 3, 4, 5)), text)
    return path
