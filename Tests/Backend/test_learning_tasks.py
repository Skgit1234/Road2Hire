from Main import app


def test_learning_task_progress_route_is_registered():
    paths = app.openapi()["paths"]
    assert "patch" in paths["/tasks/{task_id}"]
