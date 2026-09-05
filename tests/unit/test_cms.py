"""Tests for v19 CMS."""

from __future__ import annotations

from app.core.cms import (
    PageStatus,
    archive_page,
    create_page,
    get_published_pages,
    preview_page,
    publish_page,
    revert_page,
    search_pages,
    update_page,
)


class TestPageCreation:
    def test_create_basic(self):
        page = create_page("About Us", "<p>We are ACME</p>")
        assert page.title == "About Us"
        assert page.status == PageStatus.DRAFT
        assert page.slug == "about-us"

    def test_create_with_custom_slug(self):
        page = create_page("Test", "Content", slug="custom-slug")
        assert page.slug == "custom-slug"

    def test_create_with_meta(self):
        page = create_page("Test", "Content", meta_description="SEO desc", meta_keywords="oil,gas")
        assert page.meta_description == "SEO desc"
        assert page.meta_keywords == "oil,gas"


class TestPageUpdate:
    def test_update_content(self):
        page = create_page("Test", "Old content")
        page = update_page(page, content="New content", note="Updated")
        assert page.content == "New content"
        assert len(page.versions) == 2

    def test_update_title(self):
        page = create_page("Old Title", "Content")
        page = update_page(page, title="New Title")
        assert page.title == "New Title"

    def test_version_history(self):
        page = create_page("Test", "V1")
        page = update_page(page, content="V2")
        page = update_page(page, content="V3")
        assert len(page.versions) == 3
        assert page.versions[0].version == 1
        assert page.versions[2].version == 3


class TestPagePublish:
    def test_publish_requires_approval(self):
        page = create_page("Test", "Content")
        page = publish_page(page, approved=False)
        assert page.status == PageStatus.REVIEW

    def test_publish_with_approval(self):
        page = create_page("Test", "Content")
        page = publish_page(page, approved=True)
        assert page.status == PageStatus.PUBLISHED
        assert page.published_at is not None

    def test_archive(self):
        page = create_page("Test", "Content")
        page = archive_page(page)
        assert page.status == PageStatus.ARCHIVED


class TestPagePreview:
    def test_preview_html(self):
        page = create_page("Test Page", "<p>Hello</p>")
        html = preview_page(page)
        assert "<!DOCTYPE html>" in html
        assert "Test Page" in html
        assert "<p>Hello</p>" in html


class TestPageRevert:
    def test_revert_to_version(self):
        page = create_page("Test", "V1")
        page = update_page(page, content="V2")
        page = revert_page(page, 1)
        assert page.content == "V1"
        assert len(page.versions) == 3


class TestPageFiltering:
    def test_get_published(self):
        p1 = create_page("Published", "Content")
        p1 = publish_page(p1, approved=True)
        p2 = create_page("Draft", "Content")
        result = get_published_pages([p1, p2])
        assert len(result) == 1

    def test_search_pages(self):
        p1 = create_page("About Oil", "Content about petroleum")
        p2 = create_page("Contact", "Get in touch")
        result = search_pages([p1, p2], "oil")
        assert len(result) == 1
        assert result[0].title == "About Oil"


class TestPageSerialization:
    def test_as_dict(self):
        page = create_page("Test", "Content")
        d = page.as_dict()
        assert "id" in d
        assert "title" in d
        assert "versions" in d
