from splent_framework.fixtures.fixtures import *  # noqa: F401,F403

import pytest

from splent_framework.db import db


@pytest.fixture(scope="function")
def logged_in_client(test_client):
    """A test client authenticated as a fresh editor user.

    The post admin screens are login_required. The active product always
    ships auth (the admin panel is mandatory), so the user is created
    directly, the way the sibling features' test suites do.
    """
    from splent_io.splent_feature_auth.models import User

    email = "post-editor@example.com"
    with test_client.application.app_context():
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email=email, active=True)
            user.set_password("1234")
            db.session.add(user)
            db.session.commit()

    test_client.post(
        "/login",
        data={"email": email, "password": "1234"},
        follow_redirects=True,
    )
    return test_client
