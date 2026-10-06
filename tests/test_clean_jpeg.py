from PIL import Image

from metamoult import jpeg
from metamoult.cleaner import clean_file
from metamoult.core import Risk

from conftest import make_jpeg


def test_clean_makes_a_copy_and_keeps_the_original(jpeg_file):
    original = jpeg_file.read_bytes()
    result = clean_file(jpeg_file)
    assert result.output.name == "photo_clean.jpg"
    assert result.output != jpeg_file
    assert jpeg_file.read_bytes() == original  # original untouched


def test_clean_removes_all_high_and_medium_findings(jpeg_file):
    result = clean_file(jpeg_file)
    assert any(f.risk is Risk.HIGH for f in result.before)
    assert not [f for f in result.after if f.risk in (Risk.HIGH, Risk.MEDIUM)]
    assert result.after == []  # orientation is 1 here, so nothing is kept


def test_clean_is_lossless(jpeg_file):
    result = clean_file(jpeg_file)
    _, tail_before = jpeg.parse_jpeg(jpeg_file.read_bytes())
    _, tail_after = jpeg.parse_jpeg(result.output.read_bytes())
    assert tail_before == tail_after  # compressed picture data is byte-identical
    assert Image.open(jpeg_file).tobytes() == Image.open(result.output).tobytes()


def test_clean_keeps_orientation_only(tmp_path):
    path = make_jpeg(tmp_path / "rotated.jpg", orientation=6)
    result = clean_file(path)
    assert [f.field for f in result.after] == ["IFD0:Orientation"]
    assert result.after[0].value == "6"
    assert Image.open(result.output).getexif()[274] == 6


def test_clean_with_out_dir(jpeg_file, tmp_path):
    result = clean_file(jpeg_file, out_dir=tmp_path / "cleaned")
    assert result.output.parent == tmp_path / "cleaned"
    assert result.output.exists()


def test_clean_never_overwrites_an_existing_file(jpeg_file):
    first = clean_file(jpeg_file)
    second = clean_file(jpeg_file)
    assert first.output.name == "photo_clean.jpg"
    assert second.output.name == "photo_clean_2.jpg"
