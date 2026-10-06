import pytest
from PIL import Image

from metamoult.cleaner import clean_file
from metamoult.core import Risk, detect_format, scan_file

from conftest import make_png, make_webp


def by_field(findings):
    return {f.field: f for f in findings}


@pytest.fixture(params=["png", "webp"])
def image_file(request, tmp_path):
    maker = {"png": make_png, "webp": make_webp}[request.param]
    return maker(tmp_path / f"pic.{request.param}")


def test_format_is_detected(image_file):
    assert detect_format(image_file) == image_file.suffix[1:]


def test_exif_fields_are_found(image_file):
    found = by_field(scan_file(image_file))
    assert found["IFD0:Artist"].risk is Risk.HIGH
    assert found["EXIF:BodySerialNumber"].risk is Risk.HIGH
    assert found["GPS:Position"].risk is Risk.HIGH
    assert found["IFD0:Make"].risk is Risk.MEDIUM


def test_xmp_is_found(image_file):
    assert by_field(scan_file(image_file))["XMP:xmp:CreatorTool"].risk is Risk.MEDIUM


def test_clean_removes_everything_sensitive(image_file):
    result = clean_file(image_file)
    assert any(f.risk is Risk.HIGH for f in result.before)
    assert not [f for f in result.after if f.risk in (Risk.HIGH, Risk.MEDIUM)]
    assert result.output.name == f"pic_clean.{image_file.suffix[1:]}"


def test_clean_keeps_pixels_and_original(image_file):
    original = image_file.read_bytes()
    result = clean_file(image_file)
    assert image_file.read_bytes() == original
    assert Image.open(image_file).tobytes() == Image.open(result.output).tobytes()


def test_png_text_and_time_are_found(tmp_path):
    found = by_field(scan_file(make_png(tmp_path / "t.png")))
    assert found["PNG:Author"].risk is Risk.HIGH
    assert found["PNG:Author"].value == "Jane Example"
    assert found["PNG:Comment"].risk is Risk.MEDIUM
    assert found["PNG:Creation Time"].risk is Risk.MEDIUM
    assert found["PNG:ModifyDate"].value == "2020-01-02 03:04:05"


def test_png_and_webp_without_metadata_are_clean(tmp_path):
    assert scan_file(make_png(tmp_path / "a.png", metadata=False)) == []
    assert scan_file(make_webp(tmp_path / "a.webp", metadata=False)) == []
