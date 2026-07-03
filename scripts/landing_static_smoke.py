import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.api.main import app


def main() -> None:
    with TestClient(app) as client:
        checks = {
            "/": "Comece com três perguntas simples.",
            "/en/": "Start with three simple questions.",
            "/ru/": "Начните с трёх простых вопросов.",
            "/assets/css/landing.css": "locale-switcher",
            "/assets/js/landing.js": "pageLocale",
            "/robots.txt": "Sitemap: https://cargopt.pt/sitemap.xml",
            "/sitemap.xml": "https://cargopt.pt/humans.txt",
            "/llms.txt": "https://cargopt.pt/aeo.md",
            "/ai.txt": "CargoPT summary for AI assistants",
            "/aeo.md": "CargoPT positions itself as Portugal",
            "/knowledge.md": "Primary keywords",
            "/humans.txt": "CargoPT",
            "/mudancas-lisboa/": "Mudanças em Lisboa",
            "/transporte-moveis-lisboa/": "Transporte de móveis em Lisboa",
            "/mudancas-lisboa-porto/": "Mudanças de Lisboa para o Porto",
            "/mudancas-oeiras/": "Mudanças em Oeiras",
            "/transporte-piano-lisboa/": "Transporte de piano em Lisboa",
            "/": "popular-services",
            "/transportadores/": "href=\"/en/carriers/\"",
            "/en/carriers/": "Receive transport requests in Portugal",
            "/ru/carriers/": "Получайте заявки на перевозки по Португалии",
            "/.well-known/security.txt": "Contact:",
            "/health": "ok",
        }

        for path, expected in checks.items():
            response = client.get(path)
            if response.status_code != 200:
                raise SystemExit(f"{path} failed: {response.status_code} {response.text[:200]}")
            if expected not in response.text:
                raise SystemExit(f"{path} missing expected content: {expected}")

    print("LANDING_STATIC_SMOKE_OK")


if __name__ == "__main__":
    main()
