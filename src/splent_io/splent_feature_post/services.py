from splent_io.splent_feature_post.models import Category, Post
from splent_io.splent_feature_post.repositories import PostRepository
from splent_framework.services.BaseService import BaseService


class PostService(BaseService):
    def __init__(self):
        super().__init__(PostRepository())

    def get_by_slug(self, slug):
        return Post.query.filter_by(slug=slug).first()

    def published(self):
        return (
            Post.query.filter_by(status="published")
            .order_by(Post.published_at.desc())
            .all()
        )

    def categories(self):
        return Category.query.order_by(Category.name.asc()).all()

    def related(self, post, limit=5):
        """Other published posts to surface alongside ``post``.

        Prefers posts that share at least one category with ``post`` (newest
        first), then fills any remaining slots with the most recent published
        posts. The given post is always excluded and no post appears twice.
        Returns a list (possibly empty).
        """
        if post is None:
            return []

        base = Post.query.filter(
            Post.status == "published", Post.id != post.id
        )

        related = []
        seen = {post.id}

        category_ids = [c.id for c in post.categories]
        if category_ids:
            same_category = (
                base.filter(Post.categories.any(Category.id.in_(category_ids)))
                .order_by(Post.published_at.desc())
                .limit(limit)
                .all()
            )
            for p in same_category:
                if p.id not in seen:
                    related.append(p)
                    seen.add(p.id)

        # Fall back to recent posts when there are not enough by category.
        if len(related) < limit:
            recent = (
                base.order_by(Post.published_at.desc())
                .limit(limit + len(seen))
                .all()
            )
            for p in recent:
                if len(related) >= limit:
                    break
                if p.id not in seen:
                    related.append(p)
                    seen.add(p.id)

        return related[:limit]
