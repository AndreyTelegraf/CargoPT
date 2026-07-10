from app.api.main import app


def main() -> None:
    paths = app.openapi()["paths"]
    route = "/api/v1/track/{tracking_token}/offers/{offer_id}/select"
    assert route in paths
    assert "post" in paths[route]

    with open("app/api/web_requests.py", encoding="utf-8") as f:
        api = f.read()
    assert "select_accepted_offer_for_client" in api
    assert "ClientOfferSelectionError" in api
    assert "TrackingOfferSelectResponse" in api

    with open("app/static/assets/js/track.js", encoding="utf-8") as f:
        js = f.read()
    with open("app/static/assets/js/tracking-workspace.js", encoding="utf-8") as f:
        workspace_js = f.read()

    assert "selectOffer" in js
    assert "/offers/" in js
    assert "/select" in js
    assert 'entry.tracking_snapshot?.status === "offered"' in workspace_js
    assert '"assigned_pending_confirmation", "assigned"' in workspace_js
    assert '"assigned_pending_confirmation", "assigned", "in_progress"' in js

    with open("app/static/assets/css/track.css", encoding="utf-8") as f:
        css = f.read()
    assert ".track-offer-nav-select" in css

    print("job_tracking_offer_select_ok")


if __name__ == "__main__":
    main()
