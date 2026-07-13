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
            ("/", '<span class="field-label">WhatsApp</span>'),
            ("/en/", '<span class="field-label"><span class="field-required" aria-hidden="true">*</span>From</span>'),
            ("/en/", '<span class="field-label">WhatsApp</span>'),
            ("/ru/", '<span class="field-label"><span class="field-required" aria-hidden="true">*</span>Откуда</span>'),
            ("/ru/", '<span class="field-label">WhatsApp</span>'),
            ("/assets/css/components.css", ".request-form .field-required"),
            ("/", "landing.css?v=carousel-motion-v3"),
            ("/en/", "landing.css?v=carousel-motion-v3"),
            ("/ru/", "landing.css?v=carousel-motion-v3"),
            ("/", 'id="openPedidosCta"'),
            ("/en/", 'id="openPedidosCta"'),
            ("/ru/", 'id="openPedidosCta"'),
            ("/", "Meus pedidos (0)"),
            ("/en/", "My requests (0)"),
            ("/ru/", "Мои заявки (0)"),
            ("/assets/js/landing.js", "function renderOpenPedidos()"),
            ("/assets/js/landing.js", "openPedidosCta"),
            ("/assets/js/landing.js", "cta.href = links[0].tracking_url"),
            ("/assets/css/components.css", "open-pedidos-cta"),
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
            ("/en/carriers/", 'class="carrier-join-steps"'),
            ("/ru/carriers/", 'class="carrier-join-steps"'),
            ("/.well-known/security.txt", "Contact:"),
            ("/health", "ok"),
        ]

        for path, expected in checks:
            response = client.get(path)
            if response.status_code != 200:
                raise SystemExit(f"{path} failed: {response.status_code} {response.text[:200]}")
            if expected not in response.text:
                raise SystemExit(f"{path} missing expected content: {expected}")

        carousel_routes = [
            "/",
            "/en/",
            "/ru/",
        ]

        mobile_svg = "/assets/hero/process-cards/card_03_varias_propostas_mobile.svg"

        for route in carousel_routes:
            response = client.get(route)
            if response.status_code != 200:
                raise SystemExit(
                    f"{route} carousel check failed: "
                    f"{response.status_code} {response.text[:200]}"
                )

            html = response.text

            if html.count('class="process-carousel"') != 1:
                raise SystemExit(
                    f"{route} must contain exactly one process carousel"
                )

            carousel_start = html.index('<div class="process-carousel"')
            form_start = html.index('<form id="requestForm"', carousel_start)
            carousel_html = html[carousel_start:form_start]

            if carousel_html.count('<article class="process-card') != 4:
                raise SystemExit(
                    f"{route} process carousel must contain exactly four cards"
                )

            if carousel_html.count(mobile_svg) != 1:
                raise SystemExit(
                    f"{route} process carousel must contain the mobile third-card SVG"
                )

            if "process-carousel-prev" in carousel_html:
                raise SystemExit(
                    f"{route} process carousel must not contain a previous arrow"
                )

            if "process-carousel-next" in carousel_html:
                raise SystemExit(
                    f"{route} process carousel must not contain a next arrow"
                )

        js_response = client.get("/assets/js/landing.js")
        if js_response.status_code != 200:
            raise SystemExit(
                "/assets/js/landing.js carousel check failed: "
                f"{js_response.status_code} {js_response.text[:200]}"
            )

        js = js_response.text

        required_js = [
            'const carousel = document.querySelector(".process-carousel")',
            'function renderCarousel()',
            'function requestCarouselRender()',
            'requestAnimationFrame(renderCarousel)',
            'const proximity = 1 - clamp(Math.abs(normalizedDistance), 0, 1)',
            'card.style.setProperty("--carousel-scale"',
            '"--carousel-rotation",',
            'card.classList.toggle("is-active", distance === 0)',
            'track.addEventListener(',
            '"scroll",',
            'requestCarouselRender,',
            '{ passive: true }',
        ]

        for expected in required_js:
            if expected not in js:
                raise SystemExit(
                    f"/assets/js/landing.js missing carousel behavior: {expected}"
                )

        forbidden_js = [
            "process-carousel-prev",
            "process-carousel-next",
            "prev.disabled",
            "next.disabled",
        ]

        for forbidden in forbidden_js:
            if forbidden in js:
                raise SystemExit(
                    f"/assets/js/landing.js contains stale arrow behavior: {forbidden}"
                )

    print("LANDING_STATIC_SMOKE_OK")


if __name__ == "__main__":
    main()
