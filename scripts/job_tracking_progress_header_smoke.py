from pathlib import Path


def main() -> None:
    html = Path("app/static/track/index.html").read_text(encoding="utf-8")
    track_js = Path("app/static/assets/js/track.js").read_text(encoding="utf-8")
    progress_js = Path(
        "app/static/assets/js/progress-header.js"
    ).read_text(encoding="utf-8")
    progress_css = Path(
        "app/static/assets/css/progress-header.css"
    ).read_text(encoding="utf-8")

    assert 'id="trackingProgressHeader"' in html
    assert 'class="progress-header-shell"' in html
    assert "/assets/css/progress-header.css?v=progress-v1" in html
    assert "/assets/js/progress-header.js?v=progress-v1" in html
    assert "/assets/js/track.js?v=status-favicon-v10" in html

    for label in (
        "Recebido",
        "À procura",
        "Propostas",
        "Escolha",
        "Confirmado",
    ):
        assert label in progress_js

    assert "function getProgressState(entry)" in progress_js
    assert "assigned_pending_confirmation" in progress_js
    assert "offers_exhausted" in progress_js
    assert "expired_without_response" in progress_js
    assert (
        "progress-header-step progress-header-step-${state}"
        in progress_js
    )
    assert 'return "complete";' in progress_js
    assert 'marker.textContent = "✓"' in progress_js
    assert "window.CargoPTProgressHeader" in progress_js

    assert 'document.querySelector("#trackingProgressHeader")' in track_js
    assert "function renderTrackingProgress(entry)" in track_js
    assert "CargoPTProgressHeader.render(entry" in track_js
    assert "renderTrackingProgress(workspaceEntry)" in track_js

    for selector in (
        ".progress-header-shell",
        ".progress-header-list",
        ".progress-header-step",
        ".progress-header-marker",
        ".progress-header-step-complete",
        ".progress-header-step-current",
        ".progress-header-step-error",
        ".progress-header-step-cancelled",
        ".progress-header-current-label",
    ):
        assert selector in progress_css

    assert "@media (max-width: 720px)" in progress_css
    assert ".progress-header-label" in progress_css
    assert "display: none;" in progress_css

    print("job_tracking_progress_header_ok")


if __name__ == "__main__":
    main()
