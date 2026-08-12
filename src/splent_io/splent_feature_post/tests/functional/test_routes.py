"""
Functional tests for splent_feature_post.

Functional tests use Flask's test client to exercise full HTTP
request/response cycles (GET, POST, redirects, rendered HTML).
"""

from datetime import datetime, timedelta

from splent_framework.db import db
from splent_io.splent_feature_post.models import Category, Post


def _create_published_posts(app, count, category_slug=None):
    """Insert ``count`` published posts, oldest first (post-00 is the oldest).

    Distinctive zero-padded titles so page assertions cannot collide on
    substrings (e.g. "Post 1" inside "Post 10"). When ``category_slug`` is
    given, every post is attached to that (existing) category.
    """
    with app.app_context():
        category = (
            Category.query.filter_by(slug=category_slug).one()
            if category_slug
            else None
        )
        for i in range(count):
            post = Post(
                title=f"Pagination post {i:02d}",
                slug=f"pagination-post-{i:02d}",
                status="published",
                published_at=datetime(2026, 1, 1) + timedelta(days=i),
            )
            if category is not None:
                post.categories = [category]
            db.session.add(post)
        db.session.commit()


def test_index_is_reachable(test_client):
    """Verify the public blog index exists and renders."""
    response = test_client.get("/blog")
    assert response.status_code == 200


def test_index_first_page_holds_page_size_posts(test_client):
    """Page 1 shows the newest POST_PAGE_SIZE posts; the oldest waits on page 2."""
    app = test_client.application
    page_size = app.config["POST_PAGE_SIZE"]
    _create_published_posts(app, page_size + 1)

    response = test_client.get("/blog")
    assert response.status_code == 200
    html = response.data.decode()
    # Newest first, so the extra (oldest) post is pushed off page 1.
    assert f"Pagination post {page_size:02d}" in html
    assert "Pagination post 00" not in html
    # The pager is rendered and points at page 2.
    assert "/blog?page=2" in html


def test_index_second_page_holds_the_overflow(test_client):
    """Page 2 shows the post that did not fit on page 1, and only that one."""
    app = test_client.application
    page_size = app.config["POST_PAGE_SIZE"]
    _create_published_posts(app, page_size + 1)

    response = test_client.get("/blog?page=2")
    assert response.status_code == 200
    html = response.data.decode()
    assert "Pagination post 00" in html
    assert "Pagination post 01" not in html


def test_index_hides_pager_when_everything_fits(test_client):
    """A single page of posts renders no pager."""
    app = test_client.application
    _create_published_posts(app, 1)

    response = test_client.get("/blog")
    assert response.status_code == 200
    assert "/blog?page=2" not in response.data.decode()


def test_category_archive_filters_by_category(test_client):
    """/blog/category/<slug> lists only that category's published posts."""
    app = test_client.application
    with app.app_context():
        research = Category(name="Research", slug="research")
        db.session.add(research)
        db.session.add(
            Post(
                title="In the category",
                slug="in-the-category",
                status="published",
                categories=[research],
            )
        )
        db.session.add(
            Post(
                title="Out of the category",
                slug="out-of-the-category",
                status="published",
            )
        )
        db.session.commit()

    response = test_client.get("/blog/category/research")
    assert response.status_code == 200
    html = response.data.decode()
    # Category name is the page heading.
    assert "Research" in html
    assert "In the category" in html
    assert "Out of the category" not in html


def test_category_archive_paginates(test_client):
    """A category archive paginates within the category only."""
    app = test_client.application
    page_size = app.config["POST_PAGE_SIZE"]
    with app.app_context():
        db.session.add(Category(name="News", slug="news"))
        db.session.commit()
    _create_published_posts(app, page_size + 1, category_slug="news")

    response = test_client.get("/blog/category/news?page=2")
    assert response.status_code == 200
    html = response.data.decode()
    assert "Pagination post 00" in html
    assert "Pagination post 01" not in html


def test_category_archive_unknown_slug_is_404(test_client):
    """An unknown category slug returns 404."""
    response = test_client.get("/blog/category/does-not-exist")
    assert response.status_code == 404
