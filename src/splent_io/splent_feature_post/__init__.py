from flask import abort, render_template

from splent_framework.blueprints.base_blueprint import create_blueprint
from splent_framework.nav.nav_registry import register_nav_item
from splent_framework.services.service_locator import register_service, service_proxy

from splent_io.splent_feature_post.services import PostService

post_bp = create_blueprint(__name__)

# WordPress-style permalink structure. Configurable per product via
# app.config['POST_PERMALINK']. The default matches diversolab.us.es so existing
# links keep working (SEO).
DEFAULT_PERMALINK = "/%Y/%m/%d/%postname%"

# Public index path of the blog. Configurable per product via
# app.config['POST_INDEX_PATH'] so the URL can match the nav label
# (a product calling the entry "News" wants /news).
DEFAULT_INDEX_PATH = "/blog"


def _index_path(app) -> str:
    """Normalized configured index path (leading slash, no trailing slash).

    An empty value falls back to the default rather than "/", which would
    silently register the blog on the site root over the homepage.
    """
    path = app.config.get("POST_INDEX_PATH", "") or DEFAULT_INDEX_PATH
    return "/" + path.strip("/")


def _permalink_to_rule(structure: str) -> str:
    """Turn a permalink structure into a Flask URL rule.

    Date parts use string converters to preserve zero-padding (/2026/06/26/…),
    which matters for SEO. %Y/%year% -> <year>, %m/%monthnum% -> <month>,
    %d/%day% -> <day>, %postname%/%slug% -> <slug>.
    """
    rule = structure
    for token in ("%year%", "%Y"):
        rule = rule.replace(token, "<year>")
    for token in ("%monthnum%", "%m"):
        rule = rule.replace(token, "<month>")
    for token in ("%day%", "%d"):
        rule = rule.replace(token, "<day>")
    for token in ("%postname%", "%slug%"):
        rule = rule.replace(token, "<slug>")
    # Trailing slash so /YYYY/MM/DD/slug/ matches (and /…/slug redirects to it),
    # preserving the canonical WordPress-style permalinks (SEO).
    return rule.rstrip("/") + "/"


def build_permalink(app, post) -> str:
    """Build a post's canonical public URL from the permalink structure."""
    structure = app.config.get("POST_PERMALINK", DEFAULT_PERMALINK)
    d = post.date
    url = structure
    url = url.replace("%year%", str(d.year)).replace("%Y", str(d.year))
    url = url.replace("%monthnum%", f"{d.month:02d}").replace("%m", f"{d.month:02d}")
    url = url.replace("%day%", f"{d.day:02d}").replace("%d", f"{d.day:02d}")
    url = url.replace("%postname%", post.slug).replace("%slug%", post.slug)
    return url.rstrip("/") + "/"


def init_feature(app):
    from splent_framework.assets.asset_registry import register_asset
    from splent_framework.settings.settings_schema import register_settings

    register_service(app, "PostService", PostService)

    # Admin-configurable behaviour (framework renders the panel from this
    # schema). Only request-time values belong here: POST_INDEX_PATH and
    # POST_NAV_LABEL shape routes and nav at init time, so a panel value
    # would claim a change it cannot deliver until restart.
    register_settings(
        "post",
        "Posts",
        [
            {
                "key": "page_size",
                "type": "int",
                "default": "10",
                "label": "Posts per page",
                "help": "How many posts each page of the blog index and of a category archive shows.",
            },
            {
                "key": "home_count",
                "type": "int",
                "default": "3",
                "label": "Posts on the home page",
                "help": "How many recent posts the latest posts section shows. 0 hides the section.",
            },
        ],
        icon="file-text",
    )

    index_path = _index_path(app)

    # Label and URL are product decisions (POST_NAV_LABEL / POST_INDEX_PATH),
    # so the nav entry points at the configured index path.
    register_nav_item(
        key="post",
        label=app.config.get("POST_NAV_LABEL", "Blog"),
        href=index_path,
        order=50,
    )

    # Public blog styles (detail two-column layout + related sidebar). Shipped
    # via the asset registry, not hand-written <link>/<style> tags.
    register_asset(
        "css", "post.assets", order=100, subfolder="css", filename="post.css"
    )

    # Register the public post route from the configurable permalink structure.
    rule = _permalink_to_rule(app.config.get("POST_PERMALINK", DEFAULT_PERMALINK))

    def _post_permalink(**kwargs):
        service = service_proxy("PostService")
        post = service.get_by_slug(kwargs.get("slug"))
        # Drafts and scheduled posts (published with a future date) answer
        # 404 until their time, indistinguishable from a missing post.
        # Admins check them through the login-only preview route instead.
        if not service.is_public(post):
            abort(404)
        return render_template(
            "post/detail.html", post=post, related=service.related(post)
        )

    app.add_url_rule(rule, endpoint="post_permalink", view_func=_post_permalink)

    # Register the public index and category archive from the configurable
    # index path. Endpoint names stay "post.index" / "post.category" so every
    # existing url_for() call (templates, pagination) keeps working.
    from splent_io.splent_feature_post.routes import category, index

    app.add_url_rule(
        index_path, endpoint="post.index", view_func=index, methods=["GET"]
    )
    app.add_url_rule(
        index_path + "/category/<slug>",
        endpoint="post.category",
        view_func=category,
        methods=["GET"],
    )


def inject_context_vars(app):
    # Expose the permalink builder so templates can do {{ post_url(post) }},
    # and the section's product-chosen name so no template says "Blog" to a
    # reader whose site calls it "News".
    def post_url(post):
        return build_permalink(app, post)

    return {
        "post_url": post_url,
        "post_section_label": app.config.get("POST_NAV_LABEL", "") or "Blog",
    }
