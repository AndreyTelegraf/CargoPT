from pathlib import Path


def main() -> None:
    html = Path("app/static/track/index.html").read_text()
    css = Path("app/static/assets/css/track.css").read_text()

    assert "request-card-surface" in html
    assert html.index("request-card-surface") < html.index("timelineList")
    assert html.index("timelineList") < html.index("stateCard")
    assert html.index("stateCard") < html.index("offersSection")

    assert ".request-card-surface" in css
    assert "Tracking card as request-card product surface" in css
    assert ".request-card-surface .timeline-card" in css
    assert ".request-card-surface .state-card" in css
    assert ".request-card-surface .offers-section" in css

    print("job_tracking_request_card_surface_ok")


if __name__ == "__main__":
    main()
