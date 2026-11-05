from Main import app


def test_existing_profile_routes_are_registered():
    paths = app.openapi()["paths"]
    assert "get" in paths["/profile"]
    assert "patch" in paths["/profile"]
