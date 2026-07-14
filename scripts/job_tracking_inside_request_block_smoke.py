from pathlib import Path


def main() -> None:
    html = Path("app/static/track/index.html").read_text()
    css = Path("app/static/assets/css/track.css").read_text()
    workspace_js = Path("app/static/assets/js/tracking-workspace.js").read_text()

    assert 'class="tracking-page"' in html
    assert 'class="section track-workspace-shell"' in html
    assert 'class="tracking-panel tracking-request-card"' in html
    assert 'id="trackingPanelBody"' in html
    assert "landing.css" in html
    assert "track.css" in html

    assert ".tracking-request-card" in css
    assert ".track-workspace-shell .tracking-panel .tracking-workspace-content" in css
    assert "container.appendChild(workspace)" in workspace_js
    assert "workspace.className = \"tracking-workspace-content\"" in workspace_js

    print("job_tracking_inside_request_block_ok")


if __name__ == "__main__":
    main()
