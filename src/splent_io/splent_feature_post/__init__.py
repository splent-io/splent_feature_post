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

    register_service(app, "PostService", PostService)

    register_nav_item(key="post", label="Blog", href="/blog", order=50)

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
        if post is None or post.status != "published":
            abort(404)
        return render_template(
            "post/detail.html", post=post, related=service.related(post)
        )

    app.add_url_rule(rule, endpoint="post_permalink", view_func=_post_permalink)


def inject_context_vars(app):
    # Expose the permalink builder so templates can do {{ post_url(post) }}.
    def post_url(post):
        return build_permalink(app, post)

    return {"post_url": post_url}
