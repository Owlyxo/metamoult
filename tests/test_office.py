import zipfile

import pytest

from metamoult.cleaner import clean_file
from metamoult.core import Risk, detect_format, scan_file

from conftest import make_office

KINDS = ["docx", "xlsx", "pptx"]


def by_field(findings):
    return {f.field: f for f in findings}


@pytest.mark.parametrize("kind", KINDS)
def test_office_properties_are_found(tmp_path, kind):
    path = make_office(tmp_path / f"file.{kind}")
    assert detect_format(path) == kind
    found = by_field(scan_file(path))
    assert found["Office:creator"].risk is Risk.HIGH
    assert found["Office:creator"].value == "Jane Example"
    assert found["Office:lastModifiedBy"].risk is Risk.HIGH
    assert found["Office:Company"].risk is Risk.HIGH
    assert found["Office:Application"].risk is Risk.MEDIUM
    assert found["Office:created"].risk is Risk.MEDIUM
    assert found["Office:AppVersion"].risk is Risk.LOW
    assert found["Office:custom:ProjectCode"].risk is Risk.MEDIUM
    assert found["Office:Thumbnail"].risk is Risk.MEDIUM


@pytest.mark.parametrize("kind", KINDS)
def test_office_author_in_comments_or_revisions_is_found(tmp_path, kind):
    found = by_field(scan_file(make_office(tmp_path / f"file.{kind}")))
    assert found["Office:CommentAuthor"].value == "Jane Example"
    assert found["Office:CommentAuthor"].risk is Risk.HIGH


@pytest.mark.parametrize("kind", KINDS)
def test_office_clean_removes_everything_sensitive(tmp_path, kind):
    path = make_office(tmp_path / f"file.{kind}")
    original = path.read_bytes()
    result = clean_file(path)
    assert path.read_bytes() == original
    assert result.output.name == f"file_clean.{kind}"
    assert any(f.risk is Risk.HIGH for f in result.before)
    assert result.after == []
    with zipfile.ZipFile(result.output) as zf:
        assert zf.testzip() is None
        assert "docProps/thumbnail.jpeg" not in zf.namelist()
        assert all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in zf.infolist())
        assert b"Jane" not in b"".join(zf.read(n) for n in zf.namelist())
        assert b"thumbnail" not in zf.read("_rels/.rels")


def test_docx_main_content_is_preserved(tmp_path):
    result = clean_file(make_office(tmp_path / "file.docx"))
    with zipfile.ZipFile(result.output) as zf:
        assert b"<w:t>Hello</w:t>" in zf.read("word/document.xml")


@pytest.mark.parametrize("kind", KINDS)
def test_office_without_metadata_is_clean(tmp_path, kind):
    assert scan_file(make_office(tmp_path / f"plain.{kind}", metadata=False)) == []
