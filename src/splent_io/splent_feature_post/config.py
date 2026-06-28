"""post feature configuration.

POST_PERMALINK controls the public URL structure of posts (WordPress-style).
Default matches diversolab.us.es (/%Y/%m/%d/%postname%) so existing links keep
working. Tokens: %Y/%year%, %m/%monthnum%, %d/%day%, %postname%/%slug%.
"""

import os


def inject_config(app):
    app.config.setdefault(
        "POST_PERMALINK", os.getenv("POST_PERMALINK", "/%Y/%m/%d/%postname%")
    )
