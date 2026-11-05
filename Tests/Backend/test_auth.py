from Main import app


def test_auth_routes_are_registered():
    paths = app.openapi()["paths"]
    assert "post" in paths["/auth/register"]
    assert "post" in paths["/auth/login"]
