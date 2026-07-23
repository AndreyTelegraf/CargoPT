from pathlib import Path


def main() -> None:
    html = Path("app/static/track/index.html").read_text()
    css = Path("app/static/assets/css/track.css").read_text()
    components_css = Path("app/static/assets/css/components.css").read_text()
    workspace_js = Path("app/static/assets/js/tracking-workspace.js").read_text()
    track_js = Path("app/static/assets/js/track.js").read_text()
    landing_js = Path("app/static/assets/js/landing.js").read_text()

    assert 'class="section track-workspace-shell"' in html
    assert 'class="track-workspace-sidebar"' in html
    assert 'id="trackPedidosList"' in html
    assert 'id="trackingPanel"' in html
    assert 'class="tracking-panel tracking-request-card"' in html
    assert 'id="trackingPanelBody"' in html

    assert ".track-workspace-shell" in css
    assert ".track-workspace-sidebar" in css
    assert ".track-workspace-shell .tracking-request-card" in css
    assert ".track-workspace-shell .tracking-panel .tracking-workspace-content" in css

    assert ".tracking-offers" in components_css
    assert ".tracking-offer-card" in components_css
    assert "workspace.className = \"tracking-workspace-content\"" in workspace_js

    normalize_start = track_js.index(
        "function normalizeTrackingLink(entry) {"
    )
    normalize_end = track_js.index(
        "\nfunction getTrackingLinks()",
        normalize_start,
    )
    normalize_body = track_js[
        normalize_start:normalize_end
    ]

    assert "job_id: entry.job_id ?? null" in normalize_body
    assert "entry.tracking_url" in normalize_body
    assert "token: entry.token" in normalize_body
    assert "status_label" not in normalize_body
    assert "status_dot_state" not in normalize_body
    assert "const liveEntriesByToken = new Map();" in track_js
    assert "liveEntriesByToken.set(requestToken, entry);" in track_js
    assert "function getActiveTrackingEntry()" in track_js
    assert "refreshVisibleTrackingEntries({" in track_js
    assert "SAVED_REQUESTS_POLL_INTERVAL_MS = 30000" in track_js
    assert "savedTrackingEntries" not in track_js
    assert "activeTrackingEntry" not in track_js
    assert "loadSavedTrackingEntries(" not in track_js
    assert "status_label: messages.waitingOffers" not in landing_js

    print("job_tracking_request_card_surface_ok")


if __name__ == "__main__":
    main()
