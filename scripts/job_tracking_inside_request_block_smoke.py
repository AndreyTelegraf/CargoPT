from pathlib import Path


def main() -> None:
    html = Path("app/static/track/index.html").read_text()
    css = Path("app/static/assets/css/track.css").read_text()

    assert 'class="tracking-page"' in html
    assert 'class="hero section hero-v2 tracking-hero"' in html
    assert 'class="request-form hero-form request-card tracking-request-card"' in html
    assert "timelineList" in html
    assert "stateCard" in html
    assert "offersSection" in html
    assert "class=\"request-card-surface\"" not in html

    assert "landing.css" in html
    assert "request-card-surface-v2" in html

    assert ".tracking-request-card" in css
    assert ".tracking-hero" in css
    print("job_tracking_inside_request_block_ok")


if __name__ == "__main__":
    main()
