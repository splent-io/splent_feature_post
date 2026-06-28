import re
from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from splent_io.splent_feature_post import post_bp
from splent_io.splent_feature_post.models import Category, Post
from splent_framework.db import db
from splent_framework.services.service_locator import service_proxy

post_service = service_proxy("PostService")


# =====================================================================
# PUBLIC — the blog index. (Post detail is served by the configurable
# permalink route registered in __init__.py.)
# =====================================================================
@post_bp.route("/blog", methods=["GET"])
def index():
    return render_template("post/list.html", posts=post_service.published())


# =====================================================================
# Helpers
# =====================================================================
def _slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-") or "post"


def _unique_slug(value, exclude_id=None):
    base = _slugify(value)
    slug, i = base, 2
    while True:
        q = Post.query.filter_by(slug=slug)
        if exclude_id:
            q = q.filter(Post.id != exclude_id)
        if not q.first():
            return slug
        slug, i = f"{base}-{i}", i + 1


def _form_to_data(form):
    raw = (form.get("published_at") or "").strip()
    published_at = datetime.utcnow()
    if raw:
        try:
            published_at = datetime.fromisoformat(raw)
        except ValueError:
            pass
    return {
        "title": (form.get("title") or "").strip(),
        "excerpt": (form.get("excerpt") or "").strip(),
        "content": form.get("content") or "",
        "featured_image": (form.get("featured_image") or "").strip(),
        "status": (form.get("status") or "published").strip() or "published",
        "comment_status": (form.get("comment_status") or "open").strip() or "open",
        "published_at": published_at,
    }


def _apply_categories(post, form):
    ids = [int(x) for x in form.getlist("categories") if x]
    post.categories = (
        Category.query.filter(Category.id.in_(ids)).all() if ids else []
    )


def _media_images():
    """Image media items for the reusable media picker (featured image)."""
    try:
        return [m for m in service_proxy("MediaService").list_recent() if m.is_image]
    except Exception:
        return []


# =====================================================================
# ADMIN — posts
# =====================================================================
@post_bp.route("/admin/posts", methods=["GET"])
@login_required
def admin_index():
    posts = Post.query.order_by(Post.published_at.desc()).all()
    return render_template("post/admin/list.html", posts=posts)


@post_bp.route("/admin/posts/new", methods=["GET", "POST"])
@login_required
def admin_new():
    if request.method == "POST":
        data = _form_to_data(request.form)
        if not data["title"]:
            flash("Title is required.", "danger")
            return redirect(url_for("post.admin_new"))
        data["slug"] = _unique_slug(data["title"])
        post = Post(**data)
        _apply_categories(post, request.form)
        db.session.add(post)
        db.session.commit()
        flash(f"Added {post.title}.", "success")
        return redirect(url_for("post.admin_index"))
    return render_template(
        "post/admin/form.html",
        post=None,
        categories=post_service.categories(),
        media=_media_images(),
    )


@post_bp.route("/admin/posts/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def admin_edit(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == "POST":
        data = _form_to_data(request.form)
        if not data["title"]:
            flash("Title is required.", "danger")
            return redirect(url_for("post.admin_edit", post_id=post_id))
        if data["title"] != post.title:
            data["slug"] = _unique_slug(data["title"], exclude_id=post.id)
        for key, value in data.items():
            setattr(post, key, value)
        _apply_categories(post, request.form)
        db.session.commit()
        flash(f"Updated {post.title}.", "success")
        return redirect(url_for("post.admin_index"))
    return render_template(
        "post/admin/form.html",
        post=post,
        categories=post_service.categories(),
        media=_media_images(),
    )


@post_bp.route("/admin/posts/<int:post_id>/delete", methods=["POST"])
@login_required
def admin_delete(post_id):
    post = Post.query.get_or_404(post_id)
    title = post.title
    db.session.delete(post)
    db.session.commit()
    flash(f"Removed {title}.", "success")
    return redirect(url_for("post.admin_index"))
