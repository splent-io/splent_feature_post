from flask import render_template, request, url_for
from flask_babel import gettext as _
from markupsafe import Markup

from splent_framework.hooks.template_hooks import register_template_hook
from splent_framework.services.service_locator import service_proxy


def post_admin_link():
    """Sidebar entry for the Posts management screen (the WP-plugin pattern)."""
    active = (
        "active"
        if request.endpoint and request.endpoint.startswith("post.admin")
        else ""
    )
    return (
        f'<li class="sidebar-item {active}">'
        f'<a class="sidebar-link" href="{url_for("post.admin_index")}">'
        '<i class="align-middle" data-feather="file-text"></i> '
        f'<span class="align-middle">{_("Posts")}</span>'
        "</a>"
        "</li>"
    )


def latest_posts_section():
    """Home "Latest posts" section (home.section hook).

    Surfaces the most recent published posts on the public home page. Returns
    an empty string when there are no published posts, so the slot collapses
    cleanly rather than rendering an empty heading.
    """
    posts = service_proxy("PostService").published()[:3]
    if not posts:
        return ""
    return Markup(render_template("post/home_latest.html", posts=posts))


register_template_hook("layout.authenticated_sidebar", post_admin_link)
register_template_hook("home.section", latest_posts_section, order=20)
# The public Blog entry is declared via register_nav_item() in __init__.py and
# composed into the main nav by the theme (Menus editor) — no layout.nav hook.
