"""Read the simple fields out of an XMP packet (XML metadata)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..core import Finding
from ..risk import make_finding

_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_PREFIXES = {
    "http://purl.org/dc/elements/1.1/": "dc",
    "http://ns.adobe.com/xap/1.0/": "xmp",
    "http://ns.adobe.com/photoshop/1.0/": "photoshop",
    "http://ns.adobe.com/exif/1.0/": "exif",
    "http://ns.adobe.com/exif/1.0/aux/": "aux",
    "http://ns.adobe.com/tiff/1.0/": "tiff",
    "http://ns.adobe.com/pdf/1.3/": "pdf",
    "http://ns.adobe.com/xap/1.0/mm/": "xmpMM",
    "http://ns.adobe.com/xap/1.0/rights/": "xmpRights",
}
_SKIP = {f"{{{_RDF}}}RDF", f"{{{_RDF}}}Description"}
_PADDING = b"\x00 \r\n\t"


def _name(tag: str) -> str:
    """Turn '{namespace}local' into 'prefix:local'."""
    if not tag.startswith("{"):
        return tag
    uri, local = tag[1:].split("}", 1)
    prefix = _PREFIXES.get(uri, uri.rstrip("/").rsplit("/", 1)[-1])
    return f"{prefix}:{local}"


def _text(elem: ET.Element) -> str:
    """Flatten an element: plain text, or the items of an rdf:Seq/Bag/Alt."""
    items = [li.text.strip() for li in elem.iter(f"{{{_RDF}}}li") if li.text and li.text.strip()]
    if items:
        return ", ".join(items)
    return (elem.text or "").strip()


def scan_xmp(packet: bytes) -> list[Finding]:
    """Return findings for the fields of an XMP packet."""
    try:
        root = ET.fromstring(packet.strip(_PADDING))
    except ET.ParseError:
        return [make_finding("XMP:Packet", f"<{len(packet)} bytes, could not be parsed>")]

    findings: list[Finding] = []
    for desc in root.iter(f"{{{_RDF}}}Description"):
        for attr, value in desc.attrib.items():
            if attr.startswith("{" + _RDF) or not value:
                continue
            findings.append(make_finding(f"XMP:{_name(attr)}", value))
        for child in desc:
            if child.tag in _SKIP:
                continue
            value = _text(child)
            if value:
                findings.append(make_finding(f"XMP:{_name(child.tag)}", value))
    return findings
