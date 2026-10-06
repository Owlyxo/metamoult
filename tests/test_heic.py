import pillow_heif
from PIL import Image

from metamoult.cleaner import clean_file
from metamoult.core import Risk, detect_format, scan_file

from conftest import make_heic


def by_field(findings):
    return {f.field: f for f in findings}


def test_heic_is_detected_and_scanned(tmp_path):
    path = make_heic(tmp_path / "pic.heic")
    assert detect_format(path) == "heic"
    found = by_field(scan_file(path))
    assert found["IFD0:Artist"].risk is Risk.HIGH
    assert found["EXIF:BodySerialNumber"].risk is Risk.HIGH
    assert found["GPS:Position"].risk is Risk.HIGH
    assert found["XMP:xmp:CreatorTool"].risk is Risk.MEDIUM


def test_heic_clean_removes_metadata_and_keeps_original(tmp_path):
    path = make_heic(tmp_path / "pic.heic")
    original = path.read_bytes()
    result = clean_file(path)
    assert path.read_bytes() == original
    assert result.output.name == "pic_clean.heic"
    assert not [f for f in result.after if f.risk in (Risk.HIGH, Risk.MEDIUM)]
    assert pillow_heif.open_heif(str(result.output)).size == (64, 48)


def test_heic_without_metadata_is_clean(tmp_path):
    assert scan_file(make_heic(tmp_path / "plain.heic", metadata=False)) == []
