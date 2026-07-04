from app.api.main import app


def main() -> None:
    paths = app.openapi()["paths"]
    route = "/api/v1/track/{tracking_token}/assignment/{action}"
    assert route in paths
    assert "post" in paths[route]

    api = open("app/api/web_requests.py", encoding="utf-8").read()
    assert "record_assignment_confirmation" in api
    assert 'actor="client"' in api
    assert "process_assignment_failure_redispatch" in api
    assert "TrackingAssignmentActionResponse" in api

    schemas = open("app/api/web_request_schemas.py", encoding="utf-8").read()
    assert "client_confirmation_status" in schemas
    assert "carrier_confirmation_status" in schemas

    js = open("app/static/assets/js/track.js", encoding="utf-8").read()
    assert "Negócio confirmado" in js
    assert "Não chegámos a acordo" in js
    assert "sendAssignmentAction" in js
    assert "/assignment/" in js
    assert "renderAssignmentActions(job)" in js

    css = open("app/static/assets/css/track.css", encoding="utf-8").read()
    assert ".assignment-actions" in css
    assert ".assignment-button" in css

    print("job_tracking_assignment_actions_ok")


if __name__ == "__main__":
    main()
