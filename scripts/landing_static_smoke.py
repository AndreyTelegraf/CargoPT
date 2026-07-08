import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.api.main import app


def main() -> None:
    with TestClient(app) as client:
        checks = [
            ("/", "Comece com três perguntas simples."),
            ("/en/", "Start with three simple questions."),
            ("/ru/", "Начните с трёх простых вопросов."),
            ("/", '<span class="field-label"><span class="field-required" aria-hidden="true">*</span>De onde</span>'),
            ("/", '<span class="field-label">WhatsApp<span class="field-optional">opcional</span></span>'),
            ("/en/", '<span class="field-label"><span class="field-required" aria-hidden="true">*</span>From</span>'),
            ("/en/", '<span class="field-label">WhatsApp<span class="field-optional">optional</span></span>'),
            ("/ru/", '<span class="field-label"><span class="field-required" aria-hidden="true">*</span>Откуда</span>'),
            ("/ru/", '<span class="field-label">WhatsApp<span class="field-optional">необязательно</span></span>'),
            ("/assets/css/components.css", ".request-form .field-required"),
            ("/assets/css/components.css", 'content: "– "'),
            ("/", "landing.css?v=design-unified-v1"),
            ("/en/", "landing.css?v=design-unified-v1"),
            ("/ru/", "landing.css?v=design-unified-v1"),
            ("/assets/css/components.css", ".field-optional"),
            ("/", 'name="customer_name" autocomplete="name" required'),
            ("/", 'name="requested_date" type="text" required list="requestedDateOptions"'),
            ("/", 'placeholder="DD/MM/AAAA, hoje, amanhã"'),
            ("/", 'name="client_phone" autocomplete="tel" placeholder="+351..." required'),
            ("/", 'value="hoje"'),
            ("/", 'value="amanhã"'),
            ("/", 'value="próximos dias"'),
            ("/", 'value="qualquer dia"'),
            ("/", 'name="pickup_floor" type="number" min="-1" max="24" required'),
            ("/", 'name="pickup_elevator" required><option value="">Selecione</option>'),
            ("/", 'name="dropoff_floor" type="number" min="-1" max="24" required'),
            ("/", 'name="dropoff_elevator" required><option value="">Selecione</option>'),
            ("/en/", 'placeholder="DD/MM/YYYY, today, tomorrow"'),
            ("/en/", 'name="client_phone" autocomplete="tel" placeholder="+351..." required'),
            ("/en/", 'value="today"'),
            ("/en/", 'value="tomorrow"'),
            ("/en/", 'value="next few days"'),
            ("/en/", 'value="any day"'),
            ("/ru/", 'placeholder="ДД/ММ/ГГГГ, сегодня, завтра"'),
            ("/ru/", 'name="client_phone" autocomplete="tel" placeholder="+351..." required'),
            ("/ru/", 'value="сегодня"'),
            ("/ru/", 'value="завтра"'),
            ("/ru/", 'value="в ближайшие дни"'),
            ("/ru/", 'value="любой день"'),
            ("/assets/css/components.css", "locale-switcher"),
            ("/assets/js/landing.js", "markFieldInvalid"),
            ("/assets/js/landing.js", "normalizeRequestedDate"),
            ("/favicon.ico", ""),
            ("/site.webmanifest", "CargoPT"),
            ("/assets/brand/cargopt-icon.svg", "<svg"),
            ("/assets/brand/og-image-v1.png", ""),
            ("/assets/brand/apple-touch-icon.png", ""),
            ("/robots.txt", "Sitemap: https://cargopt.pt/sitemap.xml"),
            ("/sitemap.xml", "https://cargopt.pt/humans.txt"),
            ("/llms.txt", "https://cargopt.pt/aeo.md"),
            ("/ai.txt", "CargoPT summary for AI assistants"),
            ("/aeo.md", "CargoPT positions itself as Portugal"),
            ("/knowledge.md", "Primary keywords"),
            ("/humans.txt", "CargoPT"),
            ("/mudancas-lisboa/", "Mudanças em Lisboa"),
            ("/transporte-moveis-lisboa/", "Transporte de móveis em Lisboa"),
            ("/mudancas-lisboa-porto/", "Mudanças de Lisboa para o Porto"),
            ("/mudancas-oeiras/", "Mudanças em Oeiras"),
            ("/transporte-piano-lisboa/", "Transporte de piano em Lisboa"),
            ("/", "og:image"),
            ("/transportadores/", "href=\"/en/carriers/\""),
            ("/en/carriers/", "Receive transport requests in Portugal"),
            ("/ru/carriers/", "Получайте заявки на перевозки по Португалии"),
            ("/.well-known/security.txt", "Contact:"),
            ("/health", "ok"),
        ]

        for path, expected in checks:
            response = client.get(path)
            if response.status_code != 200:
                raise SystemExit(f"{path} failed: {response.status_code} {response.text[:200]}")
            if expected not in response.text:
                raise SystemExit(f"{path} missing expected content: {expected}")

    print("LANDING_STATIC_SMOKE_OK")


if __name__ == "__main__":
    main()
