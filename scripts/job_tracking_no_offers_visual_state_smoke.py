from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"

track_js = (
    STATIC / "assets/js/track.js"
).read_text(encoding="utf-8")

workspace_js = (
    STATIC / "assets/js/tracking-workspace.js"
).read_text(encoding="utf-8")

progress_js = (
    STATIC / "assets/js/progress-header.js"
).read_text(encoding="utf-8")

terminal_mapping = (
    'if (["offers_exhausted", '
    '"expired_without_response"].includes(snapshot.status)) '
)

assert terminal_mapping + 'return "error";' in track_js
assert terminal_mapping + 'return "error";' in workspace_js

assert terminal_mapping + 'return "cancelled";' not in track_js
assert terminal_mapping + 'return "cancelled";' not in workspace_js

assert (
    'if (snapshot.status === "cancelled") '
    'return "cancelled";'
) in track_js

assert (
    'if (snapshot.status === "cancelled") '
    'return "cancelled";'
) in workspace_js

assert 'error: "#D92D20"' in track_js
assert 'tone: "error"' in progress_js
assert 'title: messages.statusNoOffers' in workspace_js
assert 'text: messages.noOffersText' in workspace_js

for relative in (
    "track/index.html",
    "en/track/index.html",
    "ru/track/index.html",
):
    html = (STATIC / relative).read_text(encoding="utf-8")

    assert (
        "/assets/js/tracking-workspace.js"
        "?v=short-lead-filter-v1"
    ) in html

    assert (
        "/assets/js/track.js"
        "?v=short-lead-filter-v1"
    ) in html

print("TRACKING_NO_OFFERS_VISUAL_STATE_ERROR_OK")
print("TRACKING_CANCELLED_VISUAL_STATE_PRESERVED_OK")
print("TRACKING_NO_OFFERS_COPY_PRESERVED_OK")
print("TRACKING_NO_OFFERS_ASSET_VERSION_PARITY_OK")
