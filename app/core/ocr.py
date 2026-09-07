"""OCR — PDF text extraction (pypdf) and optional image OCR (pytesseract)."""

from __future__ import annotations

import html
import io
import re
import zipfile
from pathlib import Path

from app.logging_setup import get_logger

log = get_logger("app.core.ocr")


def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a PDF using pypdf.

    Falls back to empty string if pypdf is not installed or the file
    is not a valid PDF.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        log.warning("pypdf_not_installed", extra={"action": "extract_text_from_pdf"})
        return ""

    try:
        reader = PdfReader(io.BytesIO(data))
        pages: list[str] = []
        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
                pages.append(text)
            except Exception as exc:
                log.warning(
                    "pdf_page_extract_failed",
                    extra={"action": "extract_text_from_pdf", "page": page_num, "error": str(exc)},
                )
                continue

        full_text = "\n".join(pages).strip()
        log.info(
            "pdf_extracted",
            extra={
                "action": "extract_text_from_pdf",
                "pages": len(reader.pages),
                "chars": len(full_text),
            },
        )
        return full_text
    except Exception as exc:
        log.error(
            "pdf_extract_failed", extra={"action": "extract_text_from_pdf", "error": str(exc)}
        )
        return ""


def extract_text_from_image(data: bytes, *, lang: str = "ara+eng") -> str:
    """Extract text from an image using pytesseract.

    Falls back to empty string if pytesseract or Pillow is not installed.
    """
    try:
        import pytesseract  # type: ignore[import-untyped]
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        log.warning("pytesseract_not_installed", extra={"action": "extract_text_from_image"})
        return ""

    try:
        image = Image.open(io.BytesIO(data))
        try:
            text = pytesseract.image_to_string(image, lang=lang).strip()
        except Exception:
            # 1.6.0: the Arabic language pack may be missing on the host —
            # fall back to English instead of losing the whole image.
            if lang == "eng":
                raise
            text = pytesseract.image_to_string(image, lang="eng").strip()
        log.info(
            "image_ocr_extracted",
            extra={
                "action": "extract_text_from_image",
                "width": image.width,
                "height": image.height,
                "chars": len(text),
            },
        )
        return text
    except Exception as exc:
        log.error(
            "image_ocr_failed", extra={"action": "extract_text_from_image", "error": str(exc)}
        )
        return ""


_TEXT_SUFFIXES = (
    ".txt",
    ".csv",
    ".json",
    ".md",
    ".xml",
    ".tsv",
    ".log",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
)
_XML_TAG = re.compile(r"<[^>]+>")
MAX_TEXT_FILE_CHARS = 60_000


def extract_text_from_plain(data: bytes) -> str:
    """Decode a text-like file (utf-8 with BOM / utf-16 / latin-1 fallback)."""
    for enc in ("utf-8-sig", "utf-16"):
        try:
            text = data.decode(enc)
            break
        except (UnicodeDecodeError, ValueError):
            continue
    else:
        text = data.decode("latin-1", errors="replace")
    text = text.replace("\x00", "")
    return text[:MAX_TEXT_FILE_CHARS].strip()


def extract_text_from_docx(data: bytes) -> str:
    """Paragraph text from a .docx without python-docx (zip + XML)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError, ValueError) as exc:
        log.warning(
            "docx_extract_failed", extra={"action": "extract_text_from_docx", "error": str(exc)}
        )
        return ""
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    text = html.unescape(_XML_TAG.sub("", xml))
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())[
        :MAX_TEXT_FILE_CHARS
    ]


def extract_text_from_xlsx(data: bytes) -> str:
    """Cell text from a .xlsx without openpyxl: shared strings + inline values."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            shared: list[str] = []
            if "xl/sharedStrings.xml" in names:
                sst = zf.read("xl/sharedStrings.xml").decode("utf-8", errors="replace")
                shared = [
                    html.unescape(_XML_TAG.sub("", si))
                    for si in re.findall(r"<si>(.*?)</si>", sst, flags=re.S)
                ]
            lines: list[str] = []
            for sheet in sorted(n for n in names if n.startswith("xl/worksheets/sheet")):
                xml = zf.read(sheet).decode("utf-8", errors="replace")
                for row in re.findall(r"<row[^>]*>(.*?)</row>", xml, flags=re.S):
                    cells: list[str] = []
                    for attrs, value in re.findall(r"<c([^>]*)>(.*?)</c>", row, flags=re.S):
                        v = re.search(r"<v>(.*?)</v>", value, flags=re.S)
                        if v is None:
                            t = re.search(r"<t[^>]*>(.*?)</t>", value, flags=re.S)
                            cells.append(html.unescape(t.group(1)) if t else "")
                            continue
                        raw = v.group(1)
                        if 't="s"' in attrs:
                            try:
                                cells.append(shared[int(raw)])
                            except (ValueError, IndexError):
                                cells.append(raw)
                        else:
                            cells.append(raw)
                    if any(cells):
                        lines.append(" | ".join(c.strip() for c in cells))
                if lines:
                    lines.append("")
            return "\n".join(lines).strip()[:MAX_TEXT_FILE_CHARS]
    except (zipfile.BadZipFile, KeyError, ValueError) as exc:
        log.warning(
            "xlsx_extract_failed", extra={"action": "extract_text_from_xlsx", "error": str(exc)}
        )
        return ""


def extract_text(data: bytes, *, filename: str = "") -> str:
    """Unified entry point: dispatch to the appropriate extractor.

    Determines format from the filename extension or falls back to
    content sniffing.  Returns extracted text or empty string.

    1.6.0: plain text / CSV / JSON / Markdown / XML, DOCX and XLSX are read
    too — the simulator and the channels accepted them but the bot only ever
    saw the file *name*.
    """
    if not data:
        return ""

    name = Path(filename).suffix.lower() if filename else ""

    if name == ".pdf" or (not name and data[:4] == b"%PDF"):
        return extract_text_from_pdf(data)

    if name in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"):
        return extract_text_from_image(data)

    if name == ".docx":
        return extract_text_from_docx(data)
    if name in (".xlsx", ".xlsm"):
        return extract_text_from_xlsx(data)
    if name in _TEXT_SUFFIXES:
        return extract_text_from_plain(data)

    if not name:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return extract_text_from_image(data)
        if data[:3] == b"\xff\xd8\xff":
            return extract_text_from_image(data)
        if data[:2] == b"PK":
            docx = extract_text_from_docx(data)
            return docx or extract_text_from_xlsx(data)
        if data[:1] in (b"{", b"[") or all(32 <= b < 127 or b in (9, 10, 13) for b in data[:512]):
            return extract_text_from_plain(data)

    log.info(
        "ocr_unsupported_format",
        extra={"action": "extract_text", "filename": filename, "header": data[:4].hex()},
    )
    return ""
