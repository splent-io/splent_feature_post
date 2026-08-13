"""
Functional tests for WordPress-style status, scheduling and preview.

Scheduling has no cron. A post with status published and a future
published_at is "scheduled": the public queries filter published_at <= now,
so the post appears by itself when its time arrives. The tests exercise the
two sides of that comparison by inserting posts dated in the past and in the
future, which is exactly the before/after of a scheduled post's lifetime.

The preview route is login-only and blind to status and schedule, so drafts
and scheduled posts can be checked before their time. Assertions avoid
translated wording (the product may run in Spanish); they rely on stable
markers such as data-post-state and the post-preview-bar class.
"""

from datetime import datetime, timedelta

from flask import url_for

from splent_framework.db import db
from splent_io.splent_feature_post import build_permalink
from splent_io.splent_feature_post.models import Category, Post


def _index_path(client):
    """The configured public index path, however the product set it."""
    with client.application.test_request_context():
        return url_for("post.index")


def _insert(app, title, slug, status="published", hours=0, content="", category=None):
    """Insert a post whose published_at is ``hours`` from now (may be negative)."""
    with app.app_context():
        post = Post(
            title=title,
            slug=slug,
            status=status,
            content=content,
            published_at=datetime.utcnow() + timedelta(hours=hours),
        )
        if category is not None:
            post.categories = [Category.query.filter_by(slug=category).one()]
        db.session.add(post)
        db.session.commit()
        return post.id


def _permalink(app, post_id):
    with app.app_context():
        return build_permalink(app, db.session.get(Post, post_id))


# ---------------------------------------------------------------------------
# Public visibility of scheduled posts
# ---------------------------------------------------------------------------
def test_scheduled_post_hidden_from_index_until_its_time(test_client):
    app = test_client.application
    _insert(app, "Already live post", "already-live-post", hours=-2)
    _insert(app, "Still scheduled post", "still-scheduled-post", hours=2)

    html = test_client.get(_index_path(test_client)).data.decode()
    assert "Already live post" in html
    assert "Still scheduled post" not in html


def test_scheduled_post_visible_once_its_time_arrived(test_client):
    """A post dated in the past IS the after state of a scheduled post."""
    app = test_client.application
    _insert(app, "Was scheduled now due", "was-scheduled-now-due", hours=-1)

    html = test_client.get(_index_path(test_client)).data.decode()
    assert "Was scheduled now due" in html


def test_scheduled_post_permalink_is_404_until_its_time(test_client):
    app = test_client.application
    future_id = _insert(app, "Future permalink", "future-permalink", hours=2)
    past_id = _insert(app, "Past permalink", "past-permalink", hours=-2)

    assert test_client.get(_permalink(app, future_id)).status_code == 404
    assert test_client.get(_permalink(app, past_id)).status_code == 200


def test_draft_permalink_is_404(test_client):
    app = test_client.application
    draft_id = _insert(app, "Hidden draft", "hidden-draft", status="draft", hours=-2)
    assert test_client.get(_permalink(app, draft_id)).status_code == 404


def test_scheduled_post_hidden_from_category_archive(test_client):
    app = test_client.application
    with app.app_context():
        db.session.add(Category(name="Research", slug="research"))
        db.session.commit()
    _insert(app, "Live in category", "live-in-category", hours=-2, category="research")
    _insert(
        app, "Scheduled in category", "sched-in-category", hours=2, category="research"
    )

    html = test_client.get(
        _index_path(test_client) + "/category/research"
    ).data.decode()
    assert "Live in category" in html
    assert "Scheduled in category" not in html


def test_home_latest_and_related_exclude_scheduled(test_app, clean_database):
    """service.published() feeds the home hook and related() the sidebar.

    Both must hide scheduled posts, otherwise the home page or a related
    sidebar would leak a post whose permalink still answers 404.
    """
    from splent_io.splent_feature_post.services import PostService

    with test_app.app_context():
        shared = Category(name="Shared", slug="shared")
        db.session.add(shared)
        anchor = Post(
            title="Anchor",
            slug="anchor",
            status="published",
            published_at=datetime.utcnow() - timedelta(hours=3),
            categories=[shared],
        )
        scheduled = Post(
            title="Scheduled sibling",
            slug="scheduled-sibling",
            status="published",
            published_at=datetime.utcnow() + timedelta(hours=3),
            categories=[shared],
        )
        live = Post(
            title="Live sibling",
            slug="live-sibling",
            status="published",
            published_at=datetime.utcnow() - timedelta(hours=1),
            categories=[shared],
        )
        db.session.add_all([anchor, scheduled, live])
        db.session.commit()

        service = PostService()
        published_slugs = {p.slug for p in service.published()}
        assert "live-sibling" in published_slugs
        assert "anchor" in published_slugs
        assert "scheduled-sibling" not in published_slugs

        related_slugs = {p.slug for p in service.related(anchor)}
        assert "live-sibling" in related_slugs
        assert "scheduled-sibling" not in related_slugs


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
def test_preview_requires_login(test_client):
    app = test_client.application
    draft_id = _insert(app, "Draft to preview", "draft-to-preview", status="draft")
    with app.test_request_context():
        preview_url = url_for("post.admin_preview", post_id=draft_id)

    response = test_client.get(preview_url)
    assert response.status_code == 302
    assert "login" in response.headers["Location"]


def test_preview_renders_a_draft_for_logged_in_users(logged_in_client):
    app = logged_in_client.application
    draft_id = _insert(
        app,
        "Draft to preview",
        "draft-to-preview",
        status="draft",
        content="<p>Unreleased draft body</p>",
    )
    with app.test_request_context():
        preview_url = url_for("post.admin_preview", post_id=draft_id)

    response = logged_in_client.get(preview_url)
    assert response.status_code == 200
    html = response.data.decode()
    assert "post-preview-bar" in html
    assert "Draft to preview" in html
    assert "Unreleased draft body" in html


def test_preview_renders_a_scheduled_post_before_its_time(logged_in_client):
    app = logged_in_client.application
    scheduled_id = _insert(app, "Scheduled to preview", "sched-to-preview", hours=6)
    with app.test_request_context():
        preview_url = url_for("post.admin_preview", post_id=scheduled_id)

    # Public permalink still hidden, preview already works.
    assert app.test_client().get(_permalink(app, scheduled_id)).status_code == 404
    response = logged_in_client.get(preview_url)
    assert response.status_code == 200
    assert "post-preview-bar" in response.data.decode()


def test_public_detail_has_no_preview_bar(test_client):
    app = test_client.application
    post_id = _insert(app, "Plain public post", "plain-public-post", hours=-2)
    html = test_client.get(_permalink(app, post_id)).data.decode()
    assert "post-preview-bar" not in html


# ---------------------------------------------------------------------------
# Admin list state labels
# ---------------------------------------------------------------------------
def test_admin_list_labels_draft_scheduled_and_published(logged_in_client):
    app = logged_in_client.application
    _insert(app, "A draft", "a-draft", status="draft")
    scheduled_id = _insert(app, "A scheduled", "a-scheduled", hours=48)
    _insert(app, "A published", "a-published", hours=-48)

    with app.test_request_context():
        list_url = url_for("post.admin_index")
    response = logged_in_client.get(list_url)
    assert response.status_code == 200
    html = response.data.decode()

    assert 'data-post-state="draft"' in html
    assert 'data-post-state="scheduled"' in html
    assert 'data-post-state="published"' in html

    # The scheduled row shows when the post will go live.
    with app.app_context():
        when = db.session.get(Post, scheduled_id).published_at
    assert when.strftime("%Y-%m-%d %H:%M") in html


# ---------------------------------------------------------------------------
# Save and preview from the form
# ---------------------------------------------------------------------------
def test_save_and_preview_saves_then_redirects_to_preview(logged_in_client):
    app = logged_in_client.application
    with app.test_request_context():
        new_url = url_for("post.admin_new")

    response = logged_in_client.post(
        new_url,
        data={
            "title": "Previewed on save",
            "content": "<p>Body</p>",
            "status": "draft",
            "comment_status": "open",
            "action": "preview",
        },
    )
    assert response.status_code == 302

    with app.app_context():
        post = Post.query.filter_by(title="Previewed on save").first()
        assert post is not None
        assert post.status == "draft"
    with app.test_request_context():
        preview_url = url_for("post.admin_preview", post_id=post.id)
    assert response.headers["Location"].endswith(preview_url)
