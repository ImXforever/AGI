"""Unit tests for app.core.ocr (was 0% covered).

pypdf and pytesseract are optional dependencies and are NOT installed in this
environment, so the ImportError fallbacks are exercised for real. The success
and per-page-failure paths are covered by injecting fake modules into
sys.modules (ocr imports them lazily inside the functions, so this works).
"""

from __future__ import annotations

import sys
import types

import pytest

from app.core import ocr

# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------


def _install_fake_pypdf(monkeypatch, pages):
    """pages: list of str | Exception (raised by extract_text)."""

    class _Page:
        def __init__(self, value):
            self._value = value

        def extract_text(self):
            if isinstance(self._value, Exception):
                raise self._value
            return self._value

    class _PdfReader:
        def __init__(self, stream):
            self.stream = stream
            self.pages = [_Page(p) for p in pages]

    mod = types.ModuleType("pypdf")
    mod.PdfReader = _PdfReader
    monkeypatch.setitem(sys.modules, "pypdf", mod)
    return _PdfReader


def _install_broken_pypdf(monkeypatch, exc):
    class _PdfReader:
        def __init__(self, stream):
            raise exc

    mod = types.ModuleType("pypdf")
    mod.PdfReader = _PdfReader
    monkeypatch.setitem(sys.modules, "pypdf", mod)


def _install_fake_tesseract(monkeypatch, text="hello", *, open_exc=None, ocr_exc=None):
    class _Image:
        width, height = 640, 480

    pil_mod = types.ModuleType("PIL")
    image_ns = types.SimpleNamespace()

    def _open(stream):
        if open_exc:
            raise open_exc
        return _Image()

    image_ns.open = _open
    pil_mod.Image = image_ns

    tess = types.ModuleType("pytesseract")

    def _image_to_string(image, lang="eng"):
        if ocr_exc:
            raise ocr_exc
        _image_to_string.last_lang = lang
        return text

    tess.image_to_string = _image_to_string
    monkeypatch.setitem(sys.modules, "PIL", pil_mod)
    monkeypatch.setitem(sys.modules, "pytesseract", tess)
    return tess


# --------------------------------------------------------------------------
# extract_text_from_pdf
# --------------------------------------------------------------------------


def test_pdf_without_pypdf_installed_returns_empty():
    # pypdf genuinely absent in this environment
    assert "pypdf" not in sys.modules
    assert ocr.extract_text_from_pdf(b"%PDF-1.4 whatever") == ""


def test_pdf_joins_pages_with_newlines(monkeypatch):
    _install_fake_pypdf(monkeypatch, ["page one", "page two"])
    assert ocr.extract_text_from_pdf(b"%PDF-1.4") == "page one\npage two"


def test_pdf_strips_surrounding_whitespace(monkeypatch):
    _install_fake_pypdf(monkeypatch, ["  \n text \n  "])
    assert ocr.extract_text_from_pdf(b"%PDF") == "text"


def test_pdf_treats_none_page_text_as_empty(monkeypatch):
    _install_fake_pypdf(monkeypatch, [None, "real"])
    assert ocr.extract_text_from_pdf(b"%PDF") == "real"


def test_pdf_skips_a_page_that_raises_and_keeps_the_rest(monkeypatch):
    _install_fake_pypdf(monkeypatch, ["good", RuntimeError("bad page"), "also good"])
    assert ocr.extract_text_from_pdf(b"%PDF") == "good\nalso good"


def test_pdf_reader_construction_failure_returns_empty(monkeypatch):
    _install_broken_pypdf(monkeypatch, ValueError("not a pdf"))
    assert ocr.extract_text_from_pdf(b"garbage") == ""


def test_pdf_with_no_pages_returns_empty(monkeypatch):
    _install_fake_pypdf(monkeypatch, [])
    assert ocr.extract_text_from_pdf(b"%PDF") == ""


# --------------------------------------------------------------------------
# extract_text_from_image
# --------------------------------------------------------------------------


def test_image_without_pytesseract_returns_empty():
    assert "pytesseract" not in sys.modules
    assert ocr.extract_text_from_image(b"\x89PNG\r\n\x1a\n") == ""


def test_image_returns_stripped_ocr_text(monkeypatch):
    _install_fake_tesseract(monkeypatch, text="  scanned words \n")
    assert ocr.extract_text_from_image(b"\x89PNG") == "scanned words"


def test_image_default_language_is_arabic_plus_english(monkeypatch):
    tess = _install_fake_tesseract(monkeypatch)
    ocr.extract_text_from_image(b"\x89PNG")
    assert tess.image_to_string.last_lang == "ara+eng"


def test_image_language_override_is_forwarded(monkeypatch):
    tess = _install_fake_tesseract(monkeypatch)
    ocr.extract_text_from_image(b"\x89PNG", lang="fra")
    assert tess.image_to_string.last_lang == "fra"


def test_image_open_failure_returns_empty(monkeypatch):
    _install_fake_tesseract(monkeypatch, open_exc=OSError("cannot identify image"))
    assert ocr.extract_text_from_image(b"nonsense") == ""


def test_image_ocr_engine_failure_returns_empty(monkeypatch):
    _install_fake_tesseract(monkeypatch, ocr_exc=RuntimeError("tesseract missing"))
    assert ocr.extract_text_from_image(b"\x89PNG") == ""


# --------------------------------------------------------------------------
# extract_text dispatch
# --------------------------------------------------------------------------


def test_empty_payload_short_circuits():
    assert ocr.extract_text(b"") == ""


def test_dispatch_by_pdf_extension(monkeypatch):
    _install_fake_pypdf(monkeypatch, ["from pdf"])
    assert ocr.extract_text(b"anything", filename="report.PDF") == "from pdf"


def test_dispatch_by_pdf_magic_bytes_without_filename(monkeypatch):
    _install_fake_pypdf(monkeypatch, ["sniffed"])
    assert ocr.extract_text(b"%PDF-1.7 rest") == "sniffed"


@pytest.mark.parametrize(
    "name", ["scan.png", "photo.JPG", "a.jpeg", "b.tiff", "c.tif", "d.bmp", "e.webp"]
)
def test_dispatch_by_image_extension(monkeypatch, name):
    _install_fake_tesseract(monkeypatch, text="img text")
    assert ocr.extract_text(b"data", filename=name) == "img text"


def test_dispatch_by_png_magic_bytes(monkeypatch):
    _install_fake_tesseract(monkeypatch, text="png text")
    assert ocr.extract_text(b"\x89PNG\r\n\x1a\nrest") == "png text"


def test_dispatch_by_jpeg_magic_bytes(monkeypatch):
    _install_fake_tesseract(monkeypatch, text="jpg text")
    assert ocr.extract_text(b"\xff\xd8\xff\xe0rest") == "jpg text"


def test_unsupported_extension_returns_empty(monkeypatch):
    _install_fake_pypdf(monkeypatch, ["never used"])
    assert ocr.extract_text(b"MZ\x90\x00", filename="setup.exe") == ""


def test_unknown_magic_bytes_without_filename_returns_empty():
    assert ocr.extract_text(b"\x00\x01\x02\x03plain") == ""


def test_extension_wins_over_magic_bytes(monkeypatch):
    """A .png name on PDF bytes must go to the image path, not the PDF path."""
    _install_fake_pypdf(monkeypatch, ["pdf path"])
    _install_fake_tesseract(monkeypatch, text="image path")
    assert ocr.extract_text(b"%PDF-1.4", filename="mislabelled.png") == "image path"
