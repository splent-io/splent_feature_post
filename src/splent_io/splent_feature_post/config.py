"""post feature configuration.

POST_PERMALINK controls the public URL structure of posts (WordPress-style).
Default matches diversolab.us.es (/%Y/%m/%d/%postname%) so existing links keep
working. Tokens: %Y/%year%, %m/%monthnum%, %d/%day%, %postname%/%slug%.

POST_INDEX_PATH is the path of the public blog index (default /blog); category
archives hang from it (<path>/category/<slug>). POST_PAGE_SIZE is how many
posts each page of the public blog index (and of a category archive) shows.
POST_NAV_LABEL is the label of the public "Blog" entry in the main navigation;
a product that renames the entry (e.g. "News") sets POST_INDEX_PATH to match.
"""

import os


def inject_config(app):
    app.config.setdefault(
        "POST_PERMALINK", os.getenv("POST_PERMALINK", "/%Y/%m/%d/%postname%")
    )
    app.config.setdefault("POST_INDEX_PATH", os.getenv("POST_INDEX_PATH", "/blog"))
    app.config.setdefault("POST_PAGE_SIZE", int(os.getenv("POST_PAGE_SIZE", "10")))
    app.config.setdefault("POST_NAV_LABEL", os.getenv("POST_NAV_LABEL", "Blog"))
