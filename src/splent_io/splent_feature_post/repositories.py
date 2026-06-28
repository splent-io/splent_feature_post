from splent_io.splent_feature_post.models import Post
from splent_framework.repositories.BaseRepository import BaseRepository


class PostRepository(BaseRepository):
    def __init__(self):
        super().__init__(Post)
