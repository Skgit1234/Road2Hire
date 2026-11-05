from Main import app


def test_resume_routes_are_registered():
    paths = app.openapi()["paths"]

    assert "post" in paths["/resume/upload"]
    assert "get" in paths["/resume/{resume_id}/analysis"]
    assert "get" in paths["/resume/{resume_id}/download"]
    assert "get" in paths["/resumes"]
    assert "delete" in paths["/resumes/{resume_id}"]
