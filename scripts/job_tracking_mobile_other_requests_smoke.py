from pathlib import Path


def main() -> None:
    html = Path(
        "app/static/track/index.html"
    ).read_text(encoding="utf-8")

    track_js = Path(
        "app/static/assets/js/track.js"
    ).read_text(encoding="utf-8")

    track_css = Path(
        "app/static/assets/css/track.css"
    ).read_text(encoding="utf-8")

    assert 'id="otherRequestsPanel"' in html
    assert 'id="otherRequestsToggle"' in html
    assert 'class="track-other-requests-toggle"' in html
    assert 'aria-expanded="false"' in html
    assert 'aria-controls="trackPedidosList"' in html

    assert "/assets/css/track.css?v=tracking-header-wrap-v1" in html
    assert "/assets/js/track.js?v=tracking-return-copy-v1" in html

    assert (
        'document.querySelector("#otherRequestsToggle")'
        in track_js
    )
    assert "function setOtherRequestsExpanded(isExpanded)" in track_js
    assert '"is-mobile-expanded"' in track_js
    assert 'setAttribute(\n    "aria-expanded"' in track_js
    assert (
        'otherRequestsToggle.addEventListener("click"'
        in track_js
    )
    assert (
        'otherRequestsLabel: "Outros pedidos ({count})"'
        in track_js
    )
    assert (
        'messages.otherRequestsLabel.replace('
        in track_js
    )
    assert "String(links.length)" in track_js
    assert "setOtherRequestsExpanded(false)" in track_js

    assert ".track-other-requests-toggle" in track_css
    assert "@media (max-width: 720px)" in track_css
    assert (
        ".track-workspace-sidebar .track-sidebar-title"
        in track_css
    )
    assert (
        ".track-workspace-sidebar .track-offer-nav-list"
        in track_css
    )
    assert (
        ".track-workspace-sidebar.is-mobile-expanded"
        in track_css
    )
    assert (
        ".track-other-requests-toggle::after"
        in track_css
    )
    assert "transform: rotate(180deg);" in track_css

    request_order = track_css.index(
        ".track-workspace-shell .tracking-request-card {\n"
        "    order: 1;"
    )
    sidebar_order = track_css.index(
        ".track-workspace-sidebar {\n"
        "    position: static;\n"
        "    order: 2;"
    )

    assert request_order < sidebar_order

    progress_position = html.index('id="trackingProgressHeader"')
    workspace_position = html.index(
        'class="section track-workspace-shell"'
    )

    assert progress_position < workspace_position

    print("job_tracking_mobile_other_requests_ok")


if __name__ == "__main__":
    main()
