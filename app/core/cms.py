"""Simple CMS for website pages (v19).

Create, edit, preview, and publish website pages with version control.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.cms")


class PageStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclass
class PageVersion:
    version: int
    content: str
    edited_by: str
    edited_at: float
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "content": self.content,
            "edited_by": self.edited_by,
            "edited_at": self.edited_at,
            "note": self.note,
        }


@dataclass
class Page:
    id: str
    title: str
    slug: str
    content: str
    status: PageStatus
    created_by: str
    created_at: float
    updated_at: float
    published_at: float | None
    versions: list[PageVersion] = field(default_factory=list)
    meta_description: str = ""
    meta_keywords: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "content": self.content,
            "status": self.status.value,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "published_at": self.published_at,
            "versions": [v.as_dict() for v in self.versions[-5:]],
            "meta_description": self.meta_description,
            "meta_keywords": self.meta_keywords,
        }

    def to_html(self) -> str:
        return (
            f"<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
            f"<meta charset='UTF-8'>\n"
            f"<meta name='description' content='{self.meta_description}'>\n"
            f"<title>{self.title}</title>\n"
            f"</head>\n<body>\n"
            f"<h1>{self.title}</h1>\n"
            f"{self.content}\n"
            f"</body>\n</html>"
        )


def _gen_id() -> str:
    return hashlib.sha256(os.urandom(32)).hexdigest()[:12]


def _slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = " ".join(slug.split())
    slug = slug.replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    return slug[:80]


def create_page(
    title: str,
    content: str,
    *,
    slug: str = "",
    created_by: str = "admin",
    meta_description: str = "",
    meta_keywords: str = "",
) -> Page:
    """Create a new CMS page."""
    now = time.time()
    return Page(
        id=_gen_id(),
        title=title,
        slug=slug or _slugify(title),
        content=content,
        status=PageStatus.DRAFT,
        created_by=created_by,
        created_at=now,
        updated_at=now,
        published_at=None,
        versions=[
            PageVersion(
                version=1,
                content=content,
                edited_by=created_by,
                edited_at=now,
                note="Initial creation",
            )
        ],
        meta_description=meta_description,
        meta_keywords=meta_keywords,
    )


def update_page(
    page: Page,
    *,
    title: str | None = None,
    content: str | None = None,
    meta_description: str | None = None,
    meta_keywords: str | None = None,
    edited_by: str = "admin",
    note: str = "",
) -> Page:
    """Update a page and create a version snapshot."""
    now = time.time()
    if title is not None:
        page.title = title
    if content is not None:
        page.content = content
    if meta_description is not None:
        page.meta_description = meta_description
    if meta_keywords is not None:
        page.meta_keywords = meta_keywords
    page.updated_at = now
    next_version = (page.versions[-1].version + 1) if page.versions else 1
    page.versions.append(
        PageVersion(
            version=next_version,
            content=page.content,
            edited_by=edited_by,
            edited_at=now,
            note=note or f"Update v{next_version}",
        )
    )
    return page


def publish_page(page: Page, *, approved: bool = False) -> Page:
    """Publish a page (requires approval for sensitive changes)."""
    if not approved:
        page.status = PageStatus.REVIEW
        return page
    page.status = PageStatus.PUBLISHED
    page.published_at = time.time()
    return page


def archive_page(page: Page) -> Page:
    """Archive a page."""
    page.status = PageStatus.ARCHIVED
    return page


def preview_page(page: Page) -> str:
    """Get HTML preview of a page."""
    return page.to_html()


def revert_page(page: Page, version: int) -> Page:
    """Revert a page to a specific version."""
    for v in page.versions:
        if v.version == version:
            page.content = v.content
            page.updated_at = time.time()
            next_v = (page.versions[-1].version + 1) if page.versions else 1
            page.versions.append(
                PageVersion(
                    version=next_v,
                    content=v.content,
                    edited_by="system",
                    edited_at=time.time(),
                    note=f"Reverted to v{version}",
                )
            )
            return page
    raise ValueError(f"Version {version} not found")


def get_published_pages(pages: list[Page]) -> list[Page]:
    """Filter published pages."""
    return [p for p in pages if p.status == PageStatus.PUBLISHED]


def search_pages(pages: list[Page], query: str) -> list[Page]:
    """Search pages by title or content."""
    q = query.lower()
    return [p for p in pages if q in p.title.lower() or q in p.content.lower()]
