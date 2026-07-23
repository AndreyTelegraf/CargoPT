from pathlib import Path


def main() -> None:
    html = Path(
        "app/static/track/index.html"
    ).read_text(encoding="utf-8")

    track_js = Path(
        "app/static/assets/js/track.js"
    ).read_text(encoding="utf-8")

    workspace_js = Path(
        "app/static/assets/js/tracking-workspace.js"
    ).read_text(encoding="utf-8")

    progress_js = Path(
        "app/static/assets/js/progress-header.js"
    ).read_text(encoding="utf-8")

    track_css = Path(
        "app/static/assets/css/track.css"
    ).read_text(encoding="utf-8")

    assert 'id="otherRequestsPanel"' in html
    assert 'aria-label="Outros pedidos"' in html
    assert (
        '<h2 class="track-sidebar-title">'
        "Outros pedidos</h2>"
        in html
    )
    assert "Pedidos em aberto" not in html
    assert "Os seus pedidos" not in html
    assert "track-new-request" not in html

    assert "/assets/css/track.css?v=tracking-header-wrap-v1" in html
    assert "/assets/js/progress-header.js?v=progress-stage-v5" in html
    assert "/assets/js/tracking-workspace.js?v=no-offers-visual-state-v2" in html
    assert "/assets/js/track.js?v=tracking-return-copy-v1" in html

    assert (
        'document.querySelector("#otherRequestsPanel")'
        in track_js
    )
    assert (
        'document.querySelector(".track-workspace-shell")'
        in track_js
    )
    assert "function getOtherTrackingLinks()" in track_js
    assert "entry.token !== token" in track_js
    assert (
        "otherRequestsPanel.hidden = !hasOtherRequests"
        in track_js
    )
    assert '"has-no-other-requests"' in track_js
    assert "track-offer-nav-empty" not in track_js

    for copy in (
        "Ainda não recebemos propostas.",
        "Estamos à procura de transportadores.",
        "Isto normalmente demora apenas alguns minutos.",
    ):
        assert copy in track_js

    assert (
        'workspace.className = "tracking-workspace-content"'
        in workspace_js
    )
    assert (
        "function renderWaitingState(entry, messages)"
        in workspace_js
    )
    assert (
        "function renderOffers(entry, options, messages)"
        in workspace_js
    )
    assert (
        "if (offers.length > 0 && !options.hideOffers)"
        in workspace_js
    )
    assert "renderWaitingState(entry, messages)" in workspace_js

    assert (
        'if (snapshot.status === "no_carriers_found") '
        'return "searching";'
        in track_js
    )
    assert (
        '["no_carriers_found", "offers_exhausted", '
        '"expired_without_response"]'
        in track_js
    )
    assert (
        'if (snapshot.status === "no_carriers_found") '
        'return "searching";'
        in workspace_js
    )
    assert (
        'status === "no_carriers_found"'
        in workspace_js
    )
    assert (
        '|| status === "no_carriers_found"'
        in progress_js
    )

    manual_review_group = (
        '["ready_for_matching", "matching", "offered", '
        '"manual_review_required"]'
    )

    assert track_js.count(manual_review_group) == 3
    assert workspace_js.count(manual_review_group) == 1
    assert '"manual_review_required"' in progress_js

    get_visual_state_marker = (
        "function getVisualState(entry) {"
    )
    assert get_visual_state_marker in workspace_js

    get_visual_state_body = (
        workspace_js
        .split(get_visual_state_marker, 1)[1]
        .split("\n  function ", 1)[0]
    )

    assert get_visual_state_body.rstrip().endswith(
        'return "searching";\n  }'
    )
    assert not get_visual_state_body.rstrip().endswith(
        'return "completed";\n  }'
    )

    assert 'card.className = "hero-workspace"' not in workspace_js
    assert "tracking-status-title" not in workspace_js
    assert "tracking-status-summary" not in workspace_js
    assert "tracking-success-actions" not in workspace_js

    assert (
        "grid-template-columns: "
        "minmax(220px, 1fr) minmax(0, 3fr);"
        in track_css
    )
    assert (
        ".track-workspace-shell.has-no-other-requests"
        in track_css
    )
    assert ".track-workspace-sidebar[hidden]" in track_css
    assert (
        ".track-workspace-sidebar[hidden] "
        "+ .tracking-request-card"
        in track_css
    )
    assert (
        ".track-workspace-shell .tracking-panel "
        ".tracking-workspace-content"
        in track_css
    )
    assert ".tracking-waiting-state" in track_css
    assert ".tracking-waiting-title" in track_css
    assert ".tracking-waiting-text" in track_css
    assert ".tracking-waiting-note" in track_css

    assert ".track-offer-nav-empty" not in track_css
    assert ".track-new-request" not in track_css
    assert ".tracking-success-actions" not in track_css
    assert ".hero-workspace" not in track_css

    print("job_tracking_workspace_v2_ok")


if __name__ == "__main__":
    main()
