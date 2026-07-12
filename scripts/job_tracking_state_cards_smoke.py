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

    assert "CargoPTTrackingWorkspace.render" in track_js
    assert "CargoPTTrackingWorkspace.getVisualState" in track_js
    assert "tracking_visual_state" in track_js

    assert "function getVisualState(entry)" in workspace_js
    assert "tracking-status-summary" in workspace_js
    assert "tracking-status-dot-${entry.status_dot_state" in workspace_js
    assert "renderAssignmentActions(entry" in workspace_js

    assert ".tracking-status-summary" in components_css
    assert ".tracking-status-dot" in components_css
    assert ".tracking-assignment-actions" in components_css
    assert ".track-workspace-shell .tracking-panel .hero-workspace" in track_css

    print("job_tracking_state_cards_ok")


if __name__ == "__main__":
    main()
