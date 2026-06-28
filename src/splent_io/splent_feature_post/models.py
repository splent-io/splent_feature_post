from datetime import datetime

from sqlalchemy.dialects.mysql import LONGTEXT

from splent_framework.db import db


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

    def __repr__(self):
        return f"Post<{self.slug}>"
