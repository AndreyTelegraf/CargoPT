from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"

LANDINGS = {
    "pt": STATIC / "index.html",
    "en": STATIC / "en/index.html",
    "ru": STATIC / "ru/index.html",
}

COOKIE_PAGES = {
    "pt": STATIC / "cookies/index.html",
    "en": STATIC / "en/cookies/index.html",
    "ru": STATIC / "ru/cookies/index.html",
}

PRIVACY_PAGES = {
    "pt": STATIC / "privacy/index.html",
    "en": STATIC / "en/privacy/index.html",
    "ru": STATIC / "ru/privacy/index.html",
}


def require(source: str, expected: str, label: str) -> None:
    if expected not in source:
        raise SystemExit(f"{label} missing: {expected}")


def main() -> None:
    for locale, path in LANDINGS.items():
        source = path.read_text(encoding="utf-8")
        require(source, "/assets/css/meta-consent.css?v=meta-pixel-v1", locale)
        require(source, "/assets/js/meta-consent.js?v=meta-pixel-v1", locale)
        require(source, "data-meta-consent-settings", locale)
        if source.index("/assets/js/meta-consent.js") > source.index("/assets/js/landing.js"):
            raise SystemExit(f"{locale} loads landing.js before consent code")
        if "connect.facebook.net" in source or "facebook.com/tr" in source:
            raise SystemExit(f"{locale} contains unconditional Meta code")

    consent = (STATIC / "assets/js/meta-consent.js").read_text(encoding="utf-8")
    require(consent, 'const META_PIXEL_ID = "2752503925200185"', "consent js")
    require(consent, 'script.src = "https://connect.facebook.net/en_US/fbevents.js"', "consent js")
    require(consent, 'fbq("track", "PageView")', "consent js")
    require(consent, 'window.fbq("track", "Lead")', "consent js")
    require(consent, 'expiresAt.setMonth(expiresAt.getMonth() + 6)', "consent js")
    require(consent, 'consentChoice() !== "granted"', "consent js")
    require(consent, 'document.body.dataset.locale', "consent js")
    require(consent, 'main.before(banner)', "consent js")
    require(consent, "pt:", "consent js")
    require(consent, "en:", "consent js")
    require(consent, "ru:", "consent js")
    if "customer_email" in consent or "client_phone" in consent or "tracking_token" in consent:
        raise SystemExit("consent js references private request fields")
    if "<noscript" in consent or "facebook.com/tr" in consent:
        raise SystemExit("consent js contains a consent-bypassing fallback")
    if consent.count('window.fbq("track", "Lead")') != 1:
        raise SystemExit("Lead must have one guarded dispatch point")

    landing_js = (STATIC / "assets/js/landing.js").read_text(encoding="utf-8")
    response_position = landing_js.index("const body = await response.json()")
    lead_position = landing_js.index("window.CargoPTMeta.trackLeadOnce(body.job_id)")
    redirect_position = landing_js.index("window.location.href = localizedTrackingPath(body.tracking_token)")
    if not response_position < lead_position < redirect_position:
        raise SystemExit("Lead is not tracked after success and before redirect")

    css = (STATIC / "assets/css/meta-consent.css").read_text(encoding="utf-8")
    require(css, "@media (max-width: 700px)", "consent css")
    require(css, "grid-template-columns: 1fr 1fr", "consent css")
    if "position: fixed" in css:
        raise SystemExit("consent bar must not cover the form")

    cookie_markers = {
        "pt": "A escolha é guardada no navegador durante seis meses.",
        "en": "The choice is stored in the browser for six months.",
        "ru": "Выбор сохраняется в браузере на шесть месяцев.",
    }
    privacy_markers = {
        "pt": "eventos PageView e Lead do Meta Pixel",
        "en": "Meta Pixel PageView and Lead events",
        "ru": "событиям PageView и Lead в Meta Pixel",
    }

    for locale, path in COOKIE_PAGES.items():
        source = path.read_text(encoding="utf-8")
        require(source, cookie_markers[locale], f"cookies {locale}")
        require(source, "Meta Platforms Ireland Limited", f"cookies {locale}")

    for locale, path in PRIVACY_PAGES.items():
        source = path.read_text(encoding="utf-8")
        require(source, privacy_markers[locale], f"privacy {locale}")
        require(source, "Meta Platforms Ireland Limited", f"privacy {locale}")

    print("META_PIXEL_CONSENT_SMOKE_OK")


if __name__ == "__main__":
    main()
