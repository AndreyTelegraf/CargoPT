from pathlib import Path

from app.api.main import app


def main() -> None:
    static_dir = Path("app/static")
    assert (static_dir / "track" / "index.html").is_file()
    assert (static_dir / "assets" / "js" / "track.js").is_file()
    assert (static_dir / "assets" / "css" / "track.css").is_file()

    html = (static_dir / "track" / "index.html").read_text()
    js = (static_dir / "assets" / "js" / "track.js").read_text()
    css = (static_dir / "assets" / "css" / "track.css").read_text()
    main_source = Path("app/api/main.py").read_text()

    assert "/assets/js/track.js" in html
    assert "/assets/css/track.css" in html
    assert "/api/v1/track/" in js
    assert "window.setInterval" in js
    assert "accepted_offers" in js
    assert "track/{tracking_token}" in main_source

    paths = app.openapi()["paths"]
    assert "/api/v1/track/{tracking_token}" in paths

    route_paths = {
        getattr(route, "path", "")
        for route in app.routes
        if hasattr(route, "path")
    }
    assert "/track/{tracking_token}" in route_paths

    print("job_tracking_page_static_ok")


if __name__ == "__main__":
    main()
