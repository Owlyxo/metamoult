import pytest

from metamoult.cli import main

from conftest import make_jpeg, make_pdf


def test_scan_prints_findings_and_explanations(jpeg_file, capsys):
    assert main(["scan", str(jpeg_file)]) == 0
    out = capsys.readouterr().out
    assert "HIGH" in out and "MEDIUM" in out
    assert "GPS:Position" in out and "48.858400" in out
    assert "reveals where the file was created" in out
    assert "\033[" not in out  # no colours when output is not a terminal


def test_scan_several_files_and_wildcards(tmp_path, capsys):
    make_jpeg(tmp_path / "a.jpg")
    make_pdf(tmp_path / "b.pdf")
    assert main(["scan", str(tmp_path / "*")]) == 0
    out = capsys.readouterr().out
    assert "a.jpg" in out and "b.pdf" in out


def test_clean_writes_copy_and_shows_rescan(jpeg_file, capsys):
    assert main(["clean", str(jpeg_file)]) == 0
    out = capsys.readouterr().out
    assert "photo_clean.jpg" in out
    assert "Re-scan of the copy: no metadata found" in out
    assert (jpeg_file.parent / "photo_clean.jpg").exists()


def test_clean_with_out_folder(jpeg_file, tmp_path, capsys):
    target = tmp_path / "out"
    assert main(["clean", str(jpeg_file), "--out", str(target)]) == 0
    assert (target / "photo_clean.jpg").exists()


def test_unsupported_file_gives_error_and_exit_code_1(tmp_path, capsys):
    bad = tmp_path / "note.txt"
    bad.write_text("just text, no metadata format")
    good = make_jpeg(tmp_path / "ok.jpg")
    assert main(["scan", str(bad), str(good)]) == 1  # keeps going after the error
    captured = capsys.readouterr()
    assert "note.txt" in captured.err
    assert "ok.jpg" in captured.out


def test_missing_file_is_reported(tmp_path, capsys):
    assert main(["scan", str(tmp_path / "nope.jpg")]) == 1
    assert "nope.jpg" in capsys.readouterr().err


def test_no_command_is_an_error():
    with pytest.raises(SystemExit):
        main([])
