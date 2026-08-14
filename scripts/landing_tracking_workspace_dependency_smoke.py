from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LANDINGS = (
    ROOT / "app/static/index.html",
    ROOT / "app/static/en/index.html",
    ROOT / "app/static/ru/index.html",
)

TRACK_PAGES = (
    ROOT / "app/static/track/index.html",
    ROOT / "app/static/en/track/index.html",
    ROOT / "app/static/ru/track/index.html",
)

TRACKING_REF = "/assets/js/tracking-workspace.js"
LANDING_REF = (
    "/assets/js/landing.js"
    "?v=location-selector-v1"
)

for path in LANDINGS:
    html = path.read_text(encoding="utf-8")
    assert TRACKING_REF not in html, path
    assert html.count(LANDING_REF) == 1, path

for path in TRACK_PAGES:
    html = path.read_text(encoding="utf-8")
    assert html.count(TRACKING_REF) == 1, path

tracking_js = ROOT / "app/static/assets/js/tracking-workspace.js"
landing_js = ROOT / "app/static/assets/js/landing.js"

assert tracking_js.is_file()
assert landing_js.is_file()
assert "window.CargoPTTrackingWorkspace" in tracking_js.read_text(
    encoding="utf-8"
)

print("LANDING_TRACKING_WORKSPACE_DEPENDENCY_SMOKE_OK")
