from flask import request, url_for
from flask_babel import gettext as _

from splent_framework.hooks.template_hooks import register_template_hook


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


register_template_hook("layout.authenticated_sidebar", post_admin_link)
# The public Blog entry is declared via register_nav_item() in __init__.py and
# composed into the main nav by the theme (Menus editor) — no layout.nav hook.
