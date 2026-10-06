import tkinter as tk

import pytest

from conftest import make_jpeg


@pytest.fixture
def app():
    from metamoult.gui import App
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    root.withdraw()
    yield App(root)
    root.destroy()


def test_files_are_listed_with_traffic_light_rows(app, tmp_path):
    app.add_files([str(make_jpeg(tmp_path / "a.jpg"))])
    rows = [app.tree.item(i) for i in app.tree.get_children()]
    assert rows and rows[0]["values"][0] == "HIGH"
    assert "High" not in rows[0]["tags"] and "high" in rows[0]["tags"]
    assert str(app.save_button["state"]) == "normal"


def test_unsupported_file_shows_an_error_instead_of_crashing(app, tmp_path):
    bad = tmp_path / "x.txt"
    bad.write_text("not a supported format")
    app.add_files([str(bad)])
    assert "unsupported" in app.summary["text"]
    assert str(app.save_button["state"]) == "disabled"


def test_save_cleaned_copy_adds_it_to_the_list(app, tmp_path):
    photo = make_jpeg(tmp_path / "a.jpg")
    app.add_files([str(photo)])
    app.save_cleaned()
    assert (tmp_path / "a_clean.jpg").exists()
    assert "no metadata found" in app.status["text"]
    assert app.listbox.size() == 2
    assert not app.tree.get_children()  # the cleaned copy shows no findings
