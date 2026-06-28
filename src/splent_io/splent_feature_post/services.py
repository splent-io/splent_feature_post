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
