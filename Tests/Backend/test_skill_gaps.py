from Main import app


def test_skill_gap_routes_are_registered():
    paths = app.openapi()["paths"]
    assert "get" in paths["/skill-gaps/"]
    assert "get" in paths["/skill-gaps/history"]
    assert "get" in paths["/skill-gaps/history/{analysis_id}"]
