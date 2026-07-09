from pathlib import Path


def main() -> None:
    html = Path("app/static/track/index.html").read_text()
    css = Path("app/static/assets/css/track.css").read_text()
    components_css = Path("app/static/assets/css/components.css").read_text()
    workspace_js = Path("app/static/assets/js/tracking-workspace.js").read_text()

    assert 'class="section track-workspace-shell"' in html
    assert 'class="track-workspace-sidebar"' in html
    assert 'id="trackPedidosList"' in html
    assert 'id="trackingPanel"' in html
    assert 'class="tracking-panel tracking-request-card"' in html
    assert 'id="trackingPanelBody"' in html

    assert ".track-workspace-shell" in css
    assert ".track-workspace-sidebar" in css
    assert ".track-workspace-shell .tracking-request-card" in css
    assert ".track-workspace-shell .tracking-panel .hero-workspace" in css

    assert ".tracking-status-summary" in components_css
    assert ".tracking-status-details" in components_css
    assert "card.className = \"hero-workspace\"" in workspace_js

    print("job_tracking_request_card_surface_ok")


if __name__ == "__main__":
    main()
