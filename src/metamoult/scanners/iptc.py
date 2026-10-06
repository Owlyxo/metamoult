"""Read IPTC captions/credits from a JPEG APP13 (Photoshop) segment."""

from __future__ import annotations

from ..core import Finding
from ..risk import make_finding

_PHOTOSHOP_HEADER = b"Photoshop 3.0\x00"
_IPTC_RESOURCE_ID = 0x0404

# Record 2 datasets we know by name; others are reported as "Record2:<n>".
_DATASETS = {
    5: "ObjectName", 25: "Keywords", 55: "DateCreated", 60: "TimeCreated",
    80: "By-line", 85: "By-lineTitle", 90: "City", 92: "SubLocation",
    95: "Province", 101: "Country", 105: "Headline", 110: "Credit",
    115: "Source", 116: "Copyright", 120: "Caption", 122: "Writer",
}


def scan_iptc(data: bytes) -> list[Finding]:
    """Return findings for the IPTC fields inside an APP13 segment payload."""
    if not data.startswith(_PHOTOSHOP_HEADER):
        return []
    findings: list[Finding] = []
    pos = len(_PHOTOSHOP_HEADER)
    while pos + 12 <= len(data) and data[pos:pos + 4] == b"8BIM":
        resource_id = int.from_bytes(data[pos + 4:pos + 6], "big")
        name_len = data[pos + 6]
        pos += 7 + name_len
        if (1 + name_len) % 2:  # the name (with its length byte) is padded to even
            pos += 1
        size = int.from_bytes(data[pos:pos + 4], "big")
        pos += 4
        block = data[pos:pos + size]
        pos += size + (size % 2)
        if resource_id == _IPTC_RESOURCE_ID:
            findings.extend(_scan_block(block))
    return findings


def _scan_block(block: bytes) -> list[Finding]:
    findings: list[Finding] = []
    pos = 0
    while pos + 5 <= len(block) and block[pos] == 0x1C:
        record, dataset = block[pos + 1], block[pos + 2]
        length = int.from_bytes(block[pos + 3:pos + 5], "big")
        value = block[pos + 5:pos + 5 + length]
        pos += 5 + length
        if record != 2 or not value:
            continue
        name = _DATASETS.get(dataset, f"Record2:{dataset}")
        findings.append(make_finding(f"IPTC:{name}", value.decode("utf-8", "replace")))
    return findings
