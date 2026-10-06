import pytest
from pypdf import PdfReader

from metamoult.cleaner import clean_file
from metamoult.core import Risk, detect_format, scan_file

from conftest import make_pdf


def by_field(findings):
    return {f.field: f for f in findings}


def test_pdf_info_and_xmp_are_found(tmp_path):
    path = make_pdf(tmp_path / "doc.pdf")
    assert detect_format(path) == "pdf"
    found = by_field(scan_file(path))
    assert found["PDF:Author"].risk is Risk.HIGH
    assert found["PDF:Author"].value == "Jane Example"
    assert found["PDF:Creator"].risk is Risk.MEDIUM  # the program, not a person
    assert found["PDF:Title"].risk is Risk.MEDIUM
    assert found["PDF:CreationDate"].risk is Risk.MEDIUM
    assert found["XMP:xmp:CreatorTool"].risk is Risk.MEDIUM


def test_pdf_clean_removes_everything(tmp_path):
    path = make_pdf(tmp_path / "doc.pdf")
    original = path.read_bytes()
    result = clean_file(path)
    assert path.read_bytes() == original
    assert result.output.name == "doc_clean.pdf"
    assert any(f.risk is Risk.HIGH for f in result.before)
    assert result.after == []
    assert len(PdfReader(str(result.output)).pages) == 1
    assert b"Jane Example" not in result.output.read_bytes()


def test_pdf_without_metadata_is_clean(tmp_path):
    assert scan_file(make_pdf(tmp_path / "plain.pdf", metadata=False)) == []
