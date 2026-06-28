import os
import re
from datetime import datetime

from sqlalchemy.dialects.mysql import LONGTEXT

from splent_framework.db import db

# Trailing WordPress-style size suffix before the extension, e.g.
# "<uuid>-2.jpeg" or "<uuid>-300x200.jpeg". Stripping it gives the base name
# shared by every size variant of the same upload.
_SIZE_SUFFIX_RE = re.compile(r"-\d+(?:x\d+)?$")


post_category = db.Table(
    "post_category",
    db.Column(
        "post_id",
        db.Integer,
        db.ForeignKey("post.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "category_id",
        db.Integer,
        db.ForeignKey("category.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    slug = db.Column(db.String(128), nullable=False, unique=True, index=True)

    def __repr__(self):
        return f"Category<{self.slug}>"


class Post(db.Model):
    """A blog post.

    The public URL is derived from the product's configurable permalink
    structure (default ``/%Y/%m/%d/%postname%``) — see ``build_permalink``.
    """

    __tablename__ = "post"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(512), nullable=False)
    slug = db.Column(db.String(255), nullable=False, unique=True, index=True)
    excerpt = db.Column(db.Text, default="")
    # Rich HTML body (TinyMCE). LONGTEXT on MySQL so long posts are not truncated.
    content = db.Column(db.Text().with_variant(LONGTEXT, "mysql"), default="")
    featured_image = db.Column(db.String(512), default="")  # /static/uploads/<file>
    published_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(db.String(32), default="published")  # published | draft
    comment_status = db.Column(db.String(16), default="open")  # open | closed
    order = db.Column(db.Integer, default=0)

    categories = db.relationship(
        "Category", secondary=post_category, backref="posts", lazy="selectin"
    )

    @property
    def date(self):
        return self.published_at or datetime.utcnow()

    @property
    def show_featured(self):
        """Whether to render the standalone featured image on the detail page.

        WordPress imports often leave the same image inside the post body, where
        ``featured_image`` is just a size variant of it (e.g. featured
        ``<uuid>-2.jpeg`` vs body ``<uuid>.jpeg``). Showing both duplicates the
        image. Return True only when the featured image's size-stripped base name
        is NOT already referenced anywhere in the body — so the standalone image
        is shown only when the body does not already contain it.
        """
        if not self.featured_image:
            return False
        # Compare on the size-stripped base name (no directory, no extension), so
        # every size variant of the same upload is treated as a match.
        stem, _ext = os.path.splitext(os.path.basename(self.featured_image))
        base = _SIZE_SUFFIX_RE.sub("", stem)
        if not base:
            return True
        # Match the base as a whole filename token (optional WP size suffix +
        # extension), anchored to a path/quote boundary, so a short stem like
        # "photo" can't match an unrelated "photographer.jpg" in the body.
        pattern = r"[/\"']" + re.escape(base) + r"(?:-\d+(?:x\d+)?)?\.[A-Za-z0-9]+"
        return re.search(pattern, self.content or "") is None

    def __repr__(self):
        return f"Post<{self.slug}>"
