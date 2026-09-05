"""OCR — PDF text extraction (pypdf) and optional image OCR (pytesseract)."""

from __future__ import annotations

import io
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
        text = pytesseract.image_to_string(image, lang=lang).strip()
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


def extract_text(data: bytes, *, filename: str = "") -> str:
    """Unified entry point: dispatch to the appropriate extractor.

    Determines format from the filename extension or falls back to
    content sniffing.  Returns extracted text or empty string.
    """
    if not data:
        return ""

    name = Path(filename).suffix.lower() if filename else ""

    if name == ".pdf" or (not name and data[:4] == b"%PDF"):
        return extract_text_from_pdf(data)

    if name in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"):
        return extract_text_from_image(data)

    if not name:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return extract_text_from_image(data)
        if data[:3] == b"\xff\xd8\xff":
            return extract_text_from_image(data)

    log.info(
        "ocr_unsupported_format",
        extra={"action": "extract_text", "filename": filename, "header": data[:4].hex()},
    )
    return ""
