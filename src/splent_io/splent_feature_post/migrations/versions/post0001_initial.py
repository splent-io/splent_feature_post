"""post feature: post, category and post_category tables.

Revision ID: post0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import LONGTEXT

revision = "post0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "category",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_category_slug"), "category", ["slug"], unique=True)

    op.create_table(
        "post",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("content", LONGTEXT(), nullable=True),
        sa.Column("featured_image", sa.String(length=512), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("comment_status", sa.String(length=16), nullable=True),
        sa.Column("order", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_post_slug"), "post", ["slug"], unique=True)
    op.create_index(op.f("ix_post_published_at"), "post", ["published_at"], unique=False)

    op.create_table(
        "post_category",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id", "category_id"),
    )


def downgrade():
    op.drop_table("post_category")
    op.drop_index(op.f("ix_post_published_at"), table_name="post")
    op.drop_index(op.f("ix_post_slug"), table_name="post")
    op.drop_table("post")
    op.drop_index(op.f("ix_category_slug"), table_name="category")
    op.drop_table("category")
