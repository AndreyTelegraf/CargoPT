from pathlib import Path

from app.api.main import app


def main() -> None:
    paths = app.openapi()["paths"]
    route = "/api/v1/track/{tracking_token}/assignment/{action}"
    assert route in paths
    assert "post" in paths[route]

    api = Path("app/api/web_requests.py").read_text(encoding="utf-8")
    assert "record_assignment_confirmation" in api
    assert 'actor="client"' in api
    assert "process_assignment_failure_redispatch" in api
    assert "TrackingAssignmentActionResponse" in api

    schemas = Path("app/api/web_request_schemas.py").read_text(encoding="utf-8")
    assert "client_confirmation_status" in schemas
    assert "carrier_confirmation_status" in schemas

    js = Path("app/static/assets/js/track.js").read_text(encoding="utf-8")
    workspace_js = Path("app/static/assets/js/tracking-workspace.js").read_text(encoding="utf-8")
    assert "confirmButton" not in workspace_js
    assert "Não chegámos a acordo com o transportador" in workspace_js
    assert "sendAssignmentAction" in js
    assert "/assignment/" in js
    assert "renderAssignmentActions(entry" in workspace_js

    css = Path("app/static/assets/css/components.css").read_text(encoding="utf-8")
    assert ".tracking-assignment-actions" in css
    assert ".tracking-assignment-fail" in css

    print("JOB_TRACKING_ASSIGNMENT_ACTIONS_SMOKE_OK")


if __name__ == "__main__":
    main()
