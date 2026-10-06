from metamoult.core import Risk, UnsupportedFormatError, detect_format, scan_file
import pytest

from conftest import make_jpeg


def by_field(findings):
    return {f.field: f for f in findings}


def test_detect_format(jpeg_file):
    assert detect_format(jpeg_file) == "jpeg"


def test_detect_format_rejects_unknown(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello world, not a known format")
    with pytest.raises(UnsupportedFormatError):
        detect_format(f)


def test_high_risk_fields(jpeg_file):
    found = by_field(scan_file(jpeg_file))
    assert found["IFD0:Artist"].risk is Risk.HIGH
    assert found["IFD0:Artist"].value == "Jane Example"
    assert found["EXIF:BodySerialNumber"].risk is Risk.HIGH
    assert found["GPS:Position"].risk is Risk.HIGH


def test_gps_is_shown_as_decimal_text(jpeg_file):
    position = by_field(scan_file(jpeg_file))["GPS:Position"].value
    assert position == "48.858400, -2.294444"


def test_medium_and_low_fields(jpeg_file):
    found = by_field(scan_file(jpeg_file))
    assert found["IFD0:Make"].risk is Risk.MEDIUM
    assert found["IFD0:Model"].risk is Risk.MEDIUM
    assert found["IFD0:Software"].risk is Risk.MEDIUM
    assert found["EXIF:DateTimeOriginal"].risk is Risk.MEDIUM
    assert found["EXIF:ISOSpeedRatings"].risk is Risk.LOW


def test_xmp_and_comment_are_found(jpeg_file):
    found = by_field(scan_file(jpeg_file))
    assert found["XMP:xmp:CreatorTool"].risk is Risk.MEDIUM
    assert found["JPEG:Comment"].value == "shot at Jane's house"


def test_every_finding_has_an_explanation(jpeg_file):
    assert all(f.explanation for f in scan_file(jpeg_file))


def test_results_are_sorted_most_severe_first(jpeg_file):
    ranks = [f.risk.rank for f in scan_file(jpeg_file)]
    assert ranks == sorted(ranks)


def test_clean_jpeg_has_no_findings(tmp_path):
    path = make_jpeg(tmp_path / "plain.jpg", exif=False, comment=False, xmp=False)
    assert scan_file(path) == []
