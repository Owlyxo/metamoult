"""Risk rating: decides how sensitive a metadata field is and explains why."""

from __future__ import annotations

import re

from .core import Finding, Risk

# Rules are checked top to bottom; the first match wins.
# Each rule: (regex on the lower-case field name, risk, explanation for laypeople).
_RULES: list[tuple[str, Risk, str]] = [
    # Harmless fields that would otherwise match a broader rule below.
    (r"orientation$", Risk.LOW,
     "A rotation hint so the picture displays upright. Harmless; kept on purpose."),
    (r"creatortool|pdf:creator$|pdf:producer$|office:application$",
     Risk.MEDIUM, "This reveals which program created or edited the file."),
    # --- HIGH ---
    (r"gps|:position$", Risk.HIGH,
     "This reveals where the file was created (GPS location)."),
    (r"serial", Risk.HIGH,
     "A serial number can link this file to your specific device."),
    (r"owner", Risk.HIGH, "This contains the name of the device or file owner."),
    (r"(^|:)(artist|author|creator|by-line|byline|copyright|rights|writer|credit)$",
     Risk.HIGH, "This contains the name of a person (author, creator or rights holder)."),
    (r"lastmodifiedby|lastsavedby|office:company|office:manager", Risk.HIGH,
     "This contains a person's or organisation's name."),
    # --- MEDIUM ---
    (r"(^|:)(make|model|lensmake|lensmodel|lens|hostcomputer|devicemanufacturer)$",
     Risk.MEDIUM, "This reveals which device or lens was used."),
    (r"date|created|creation|modified|lastprinted", Risk.MEDIUM,
     "This reveals when the file was created or changed."),
    (r"software|application|producer", Risk.MEDIUM,
     "This reveals which program created or edited the file."),
    (r"thumbnail", Risk.MEDIUM,
     "An embedded preview image; it can still show the original, uncropped picture."),
    (r"makernote", Risk.MEDIUM,
     "A manufacturer-specific data block; it may contain serial numbers and settings."),
    (r"city|province|state|country|sublocation|location", Risk.MEDIUM,
     "This names a place connected to the file."),
    (r"comment|description|caption|headline|title|subject|keywords|objectname",
     Risk.MEDIUM, "Free text written by a person; it may contain names or places."),
]
_COMPILED = [(re.compile(pattern), risk, text) for pattern, risk, text in _RULES]
_DEFAULT = (Risk.LOW, "A technical detail; usually harmless.")


def classify(field: str) -> tuple[Risk, str]:
    """Return (risk, explanation) for a field name such as 'EXIF:Make'."""
    name = field.lower()
    for pattern, risk, text in _COMPILED:
        if pattern.search(name):
            return risk, text
    return _DEFAULT


def make_finding(field: str, value: object) -> Finding:
    """Build a Finding, rating the field automatically."""
    risk, explanation = classify(field)
    return Finding(field=field, value=str(value), risk=risk, explanation=explanation)
