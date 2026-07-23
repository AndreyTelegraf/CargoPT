from pathlib import Path


def main() -> None:
    js = Path("app/static/assets/js/track.js").read_text(encoding="utf-8")
    css = Path("app/static/assets/css/track.css").read_text(encoding="utf-8")

    assert 'offerAvailableBadge: "Há proposta"' in js
    assert 'offerAvailableBadge: "Offer available"' in js
    assert 'offerAvailableBadge: "Есть предложение"' in js

    assert "const hasAcceptedOffers =" in js
    assert "Number(entry.accepted_offers_count || 0) > 0" in js
    assert 'status.classList.add("track-offer-nav-badge")' in js
    assert "status.textContent = messages.offerAvailableBadge" in js
    assert "status.textContent = messages.openRequest" in js

    assert ".track-offer-nav-badge" in css
    assert "border-radius: var(--radius-pill)" in css

    print("JOB_TRACKING_OTHER_REQUEST_OFFER_BADGE_SMOKE_OK")


if __name__ == "__main__":
    main()
