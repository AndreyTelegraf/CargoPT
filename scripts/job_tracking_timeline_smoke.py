from pathlib import Path


def main() -> None:
    html = Path("app/static/track/index.html").read_text()
    js = Path("app/static/assets/js/track.js").read_text()
    css = Path("app/static/assets/css/track.css").read_text()

    assert 'id="timelineList"' in html
    assert "TIMELINE_STEPS" in js
    assert "ACTIVE_STEP_BY_STATUS" in js
    assert "renderTimeline(job)" in js

    for label in (
        "Pedido recebido",
        "À procura",
        "Propostas",
        "Escolhido",
        "Confirmado",
        "Concluído",
    ):
        assert label in js

    assert ".timeline-card" in css
    assert ".timeline-list" in css
    assert ".timeline-item" in css
    assert ".timeline-marker" in css
    assert ".is-current" in css
    assert ".is-complete" in css

    print("job_tracking_timeline_ok")


if __name__ == "__main__":
    main()
