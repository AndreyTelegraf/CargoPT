from pathlib import Path


def main() -> None:
    html = Path("app/static/track/index.html").read_text()
    track_js = Path("app/static/assets/js/track.js").read_text()
    workspace_js = Path("app/static/assets/js/tracking-workspace.js").read_text()
    components_css = Path("app/static/assets/css/components.css").read_text()
    landing_css = Path("app/static/assets/css/landing.css").read_text()
    track_css = Path("app/static/assets/css/track.css").read_text()

    assert "id=\"trackingPanelBody\"" in html
    assert "/assets/js/tracking-workspace.js" in html
    assert "/assets/js/track.js" in html
    assert html.count('rel="icon"') == 1
    assert 'type="image/svg+xml"' in html
    assert 'href="/favicon.ico"' not in html

    assert "CargoPTTrackingWorkspace.render" in track_js
    assert "CargoPTTrackingWorkspace.getVisualState" in track_js
    assert "tracking_visual_state" in track_js
    assert 'return "searching";\n}\n\nfunction formatTrackingStatus' in track_js
    assert "const STATUS_CHROME_COLORS = {" in track_js
    assert "function updateStatusChrome(statusDotState)" in track_js
    assert "buildStatusFaviconSvg(color)" in track_js
    assert "updateStatusChrome(entry.status_dot_state);" in track_js
    assert 'meta[name="theme-color"]' in track_js

    assert "function getVisualState(entry)" in workspace_js
    assert "function renderWaitingState(entry, messages)" in workspace_js
    assert "workspace.className = \"tracking-workspace-content\"" in workspace_js
    assert "renderAssignmentActions(entry" in workspace_js

    assert ".tracking-offers" in components_css
    assert ".tracking-offer-card" in components_css
    assert ".tracking-assignment-actions" in components_css
    assert ".track-workspace-shell .tracking-panel .tracking-workspace-content" in track_css

    print("job_tracking_state_cards_ok")


if __name__ == "__main__":
    main()
