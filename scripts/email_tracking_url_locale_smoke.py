from app.services.tracking_url import build_tracking_path
from app.services.tracking_url import build_tracking_url


TOKEN = "test-token"
EXPECTED = {
    "pt": "/track/test-token",
    "pt-PT": "/track/test-token",
    "pt-BR": "/track/test-token",
    "en": "/en/track/test-token",
    "ru": "/ru/track/test-token",
    None: "/track/test-token",
    "de": "/track/test-token",
}


for locale, expected in EXPECTED.items():
    assert build_tracking_path(locale, TOKEN) == expected
    assert build_tracking_url(
        locale,
        TOKEN,
        "https://cargopt.pt/",
    ) == f"https://cargopt.pt{expected}"

print("EMAIL_TRACKING_URL_LOCALE_PARITY_OK")
