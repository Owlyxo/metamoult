"""Scanner for Office Open XML files (docx, xlsx, pptx), which are ZIP archives."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from ..core import Finding
from ..risk import make_finding

# Placeholder name that the cleaner writes in place of real author names.
ANON_AUTHOR = "Author"

# Parts whose author names the cleaner replaces: (part-name regex, text regex).
AUTHOR_PARTS = [
    (re.compile(r"word/[^/]+\.xml"), re.compile(r'w:author="([^"]*)"')),
    (re.compile(r"xl/comments[^/]*\.xml"), re.compile(r"<author>([^<]*)</author>")),
    (re.compile(r"ppt/commentAuthors\.xml"), re.compile(r'\bname="([^"]*)"')),
]

_MAX_PART = 50_000_000  # skip absurdly large parts instead of loading them


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _read(archive: zipfile.ZipFile, name: str) -> bytes | None:
    try:
        info = archive.getinfo(name)
    except KeyError:
        return None
    return archive.read(name) if info.file_size <= _MAX_PART else None


def _scan_properties(data: bytes, prefix: str = "Office") -> list[Finding]:
    """Read core.xml / app.xml: every child element becomes one finding."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []
    findings = []
    for child in root:
        value = " ".join(t.strip() for t in child.itertext() if t.strip())
        if value:
            findings.append(make_finding(f"{prefix}:{_local(child.tag)}", value))
    return findings


def _scan_custom(data: bytes) -> list[Finding]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []
    findings = []
    for prop in root:
        value = " ".join(t.strip() for t in prop.itertext() if t.strip())
        findings.append(make_finding(f"Office:custom:{prop.get('name', '?')}", value))
    return findings


def scan_office(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    with zipfile.ZipFile(path) as archive:
        for part, scan in (("docProps/core.xml", _scan_properties),
                           ("docProps/app.xml", _scan_properties),
                           ("docProps/custom.xml", _scan_custom)):
            data = _read(archive, part)
            if data is not None:
                findings += scan(data)

        for name in archive.namelist():
            if name.startswith("docProps/thumbnail"):
                findings.append(make_finding(
                    "Office:Thumbnail", f"<{archive.getinfo(name).file_size} bytes>"))
            for name_pattern, text_pattern in AUTHOR_PARTS:
                if name_pattern.fullmatch(name):
                    data = _read(archive, name)
                    authors = text_pattern.findall(data.decode("utf-8", "replace")) if data else []
                    for author in dict.fromkeys(authors):  # unique, in order
                        if author and author != ANON_AUTHOR:
                            findings.append(make_finding("Office:CommentAuthor", author))
    return findings
