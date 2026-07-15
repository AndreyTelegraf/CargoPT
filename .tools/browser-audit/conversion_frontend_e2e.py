from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import Browser, Page, async_playwright


BASE_URL = "https://cargopt.pt/"
OUT = Path(sys.argv[1])

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}


def tracking_snapshot(token: str) -> dict:
    return {
        "job_id": 999999,
        "tracking_token": token,
        "status": "matching",
        "client_confirmation_status": None,
        "carrier_confirmation_status": None,
        "accepted_offers": [],
        "selected_offer_id": None,
        "source_locale": "pt",
        "customer_name": "CargoPT E2E",
        "requested_date": "2026-07-20T12:00:00+00:00",
        "required_loaders": 2,
        "estimated_volume_m3": 5,
        "comment": "Browser E2E sem escrita em produção",
        "addresses": [
            {
                "kind": "pickup",
                "raw_text": "Lisboa",
                "floor": 1,
                "has_elevator": True,
            },
            {
                "kind": "dropoff",
                "raw_text": "Cascais",
                "floor": 2,
                "has_elevator": False,
            },
        ],
        "items": [
            {
                "description": "Sofá e 10 caixas",
                "quantity": None,
            }
        ],
    }


async def fill_step_one(page: Page) -> None:
    await page.locator('[name="pickup"]').fill("Lisboa")
    await page.locator('[name="dropoff"]').fill("Cascais")
    await page.locator('[name="items"]').fill("Sofá e 10 caixas")


async def fill_step_two(page: Page) -> None:
    await page.locator('[name="customer_name"]').fill("CargoPT E2E")
    await page.locator('[name="requested_date"]').fill("20/07/2026")
    await page.locator('[name="client_phone"]').fill("+351910000000")
    await page.locator('[name="pickup_floor"]').fill("1")
    await page.locator('[name="pickup_elevator"]').select_option("true")
    await page.locator('[name="dropoff_floor"]').fill("2")
    await page.locator('[name="dropoff_elevator"]').select_option("false")
    await page.locator('[name="required_loaders"]').select_option("2")
    await page.locator('[name="estimated_volume_m3"]').fill("5")
    await page.locator('[name="comment"]').fill(
        "Browser E2E sem escrita em produção"
    )


async def collect_runtime(page: Page) -> tuple[list[str], list[str], list[dict]]:
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[dict] = []

    page.on(
        "console",
        lambda message: (
            console_errors.append(message.text)
            if message.type == "error"
            else None
        ),
    )
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "requestfailed",
        lambda request: failed_requests.append(
            {
                "url": request.url,
                "failure": request.failure,
            }
        ),
    )

    return console_errors, page_errors, failed_requests


async def validation_scenario(
    browser: Browser,
    viewport_name: str,
    viewport: dict,
) -> dict:
    context = await browser.new_context(
        viewport=viewport,
        locale="pt-PT",
        color_scheme="light",
        reduced_motion="reduce",
        service_workers="block",
    )
    page = await context.new_page()

    console_errors, page_errors, failed_requests = await collect_runtime(page)

    await page.goto(BASE_URL, wait_until="networkidle")

    await page.locator("[data-next]").click()

    first_step_active_after_empty = await page.locator(
        '.form-step[data-step="1"]'
    ).evaluate("element => element.classList.contains('is-active')")

    invalid_step_one = await page.locator(
        '.form-step[data-step="1"] [required]:invalid'
    ).count()

    await fill_step_one(page)
    await page.locator("[data-next]").click()

    second_step_active = await page.locator(
        '.form-step[data-step="2"]'
    ).evaluate("element => element.classList.contains('is-active')")

    await page.locator('button[type="submit"]').click()

    invalid_step_two = await page.locator(
        '.form-step[data-step="2"] [required]:invalid'
    ).count()

    form_message = await page.locator("#formMessage").inner_text()

    await page.screenshot(
        path=str(OUT / f"{viewport_name}-validation.png"),
        full_page=True,
        animations="disabled",
    )

    horizontal_overflow = await page.evaluate(
        """
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth + 1
        """
    )

    result = {
        "scenario": "validation",
        "viewport": viewport_name,
        "firstStepStayedActiveAfterEmpty": first_step_active_after_empty,
        "invalidStepOneCount": invalid_step_one,
        "secondStepActive": second_step_active,
        "invalidStepTwoCount": invalid_step_two,
        "formMessage": form_message,
        "horizontalOverflow": horizontal_overflow,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "failedRequests": failed_requests,
    }

    assert first_step_active_after_empty is True
    assert invalid_step_one >= 3
    assert second_step_active is True
    assert invalid_step_two >= 6
    assert horizontal_overflow is False
    assert not page_errors
    assert not failed_requests

    await context.close()
    return result


async def api_error_scenario(
    browser: Browser,
    viewport_name: str,
    viewport: dict,
) -> dict:
    context = await browser.new_context(
        viewport=viewport,
        locale="pt-PT",
        color_scheme="light",
        reduced_motion="reduce",
        service_workers="block",
    )
    page = await context.new_page()

    console_errors, page_errors, failed_requests = await collect_runtime(page)

    captured_payloads: list[dict] = []
    request_count = 0

    async def intercept_request(route, request):
        nonlocal request_count

        request_count += 1
        captured_payloads.append(request.post_data_json)

        await asyncio.sleep(0.4)

        await route.fulfill(
            status=500,
            content_type="application/json",
            body=json.dumps({"detail": "Controlled E2E failure"}),
        )

    await page.route("**/api/v1/requests", intercept_request)

    await page.goto(BASE_URL, wait_until="networkidle")

    await fill_step_one(page)
    await page.locator("[data-next]").click()
    await fill_step_two(page)

    submit = page.locator('button[type="submit"]')

    await submit.dblclick(delay=20)

    await page.wait_for_function(
        """
        () => {
          const message = document.querySelector("#formMessage");
          const button = document.querySelector(
            'button[type="submit"]'
          );

          return Boolean(
            message &&
            message.classList.contains("is-error") &&
            message.textContent.trim().length > 0 &&
            button &&
            button.disabled === false
          );
        }
        """
    )

    button_disabled_after_failure = await submit.is_disabled()
    form_message = await page.locator("#formMessage").inner_text()

    await page.screenshot(
        path=str(OUT / f"{viewport_name}-api-error.png"),
        full_page=True,
        animations="disabled",
    )

    assert request_count == 1, (
        f"duplicate submit reached API: request_count={request_count}"
    )
    assert button_disabled_after_failure is False
    assert captured_payloads

    payload = captured_payloads[0]

    assert payload["source_locale"] == "pt"
    assert payload["customer_name"] == "CargoPT E2E"
    assert payload["client_phone"] == "+351910000000"
    assert payload["preferred_contact"] == "phone"
    assert payload["requested_date"] == "2026-07-20T12:00:00+00:00"
    assert payload["required_loaders"] == 2
    assert payload["estimated_volume_m3"] == 5
    assert payload["addresses"] == [
        {
            "kind": "pickup",
            "raw_text": "Lisboa",
            "floor": 1,
            "has_elevator": True,
        },
        {
            "kind": "dropoff",
            "raw_text": "Cascais",
            "floor": 2,
            "has_elevator": False,
        },
    ]
    assert payload["items"] == [
        {
            "description": "Sofá e 10 caixas",
            "quantity": None,
        }
    ]

    assert form_message
    assert page_errors == []
    assert failed_requests == []

    await context.close()

    return {
        "scenario": "api_error",
        "viewport": viewport_name,
        "requestCount": request_count,
        "payload": payload,
        "buttonDisabledAfterFailure": button_disabled_after_failure,
        "formMessage": form_message,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "failedRequests": failed_requests,
    }


async def success_tracking_scenario(
    browser: Browser,
    viewport_name: str,
    viewport: dict,
) -> dict:
    context = await browser.new_context(
        viewport=viewport,
        locale="pt-PT",
        color_scheme="light",
        reduced_motion="reduce",
        service_workers="block",
    )
    page = await context.new_page()

    console_errors, page_errors, failed_requests = await collect_runtime(page)

    token = f"frontend-e2e-{viewport_name}"
    captured_payloads: list[dict] = []

    async def intercept_submit(route, request):
        captured_payloads.append(request.post_data_json)

        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "job_id": 999999,
                    "tracking_token": token,
                    "tracking_url": f"/track/{token}",
                    "offers_count": 0,
                }
            ),
        )

    async def intercept_tracking(route, request):
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(tracking_snapshot(token)),
        )

    await page.route("**/api/v1/requests", intercept_submit)
    await page.route(
        f"**/api/v1/track/{token}",
        intercept_tracking,
    )

    await page.goto(BASE_URL, wait_until="networkidle")

    await fill_step_one(page)
    await page.locator("[data-next]").click()
    await fill_step_two(page)

    await page.locator('button[type="submit"]').click()

    await page.wait_for_url(f"**/track/{token}", timeout=15_000)
    await page.wait_for_load_state("networkidle")

    progress_header_visible = await page.locator(
        "#trackingProgressHeader"
    ).is_visible()

    progress_label = await page.locator(
        ".progress-header-current-label"
    ).inner_text()

    stored_links = await page.evaluate(
        """
        JSON.parse(
          localStorage.getItem("cargopt_tracking_links") || "[]"
        )
        """
    )

    stored_draft = await page.evaluate(
        """
        localStorage.getItem("cargopt_landing_request_v2")
        """
    )

    marker_count = await page.locator(
        ".progress-header-marker"
    ).count()

    horizontal_overflow = await page.evaluate(
        """
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth + 1
        """
    )

    await page.screenshot(
        path=str(OUT / f"{viewport_name}-tracking-success.png"),
        full_page=True,
        animations="disabled",
    )

    assert len(captured_payloads) == 1
    assert progress_header_visible is True
    assert progress_label == "À procura"
    assert marker_count == 5
    assert horizontal_overflow is False
    assert stored_draft is None
    assert stored_links
    assert stored_links[0]["token"] == token
    assert stored_links[0]["tracking_url"] == f"/track/{token}"
    assert page_errors == []
    assert failed_requests == []

    await context.close()

    return {
        "scenario": "success_tracking",
        "viewport": viewport_name,
        "requestCount": len(captured_payloads),
        "progressHeaderVisible": progress_header_visible,
        "progressLabel": progress_label,
        "markerCount": marker_count,
        "horizontalOverflow": horizontal_overflow,
        "storedTrackingLinks": stored_links,
        "draftRemoved": stored_draft is None,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "failedRequests": failed_requests,
    }


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        for viewport_name, viewport in VIEWPORTS.items():
            print(f"RUN validation {viewport_name}", flush=True)
            results.append(
                await validation_scenario(
                    browser,
                    viewport_name,
                    viewport,
                )
            )

            print(f"RUN api_error {viewport_name}", flush=True)
            results.append(
                await api_error_scenario(
                    browser,
                    viewport_name,
                    viewport,
                )
            )

            print(f"RUN success_tracking {viewport_name}", flush=True)
            results.append(
                await success_tracking_scenario(
                    browser,
                    viewport_name,
                    viewport,
                )
            )

        await browser.close()

    output = {
        "baseUrl": BASE_URL,
        "productionWrites": 0,
        "realRequestSubmission": False,
        "results": results,
    }

    (OUT / "results.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("SCENARIOS=6")
    print("PRODUCTION_WRITES=0")
    print("REAL_REQUEST_SUBMISSION=false")
    print(f"OUTPUT={OUT}")
    print("CARGOPT_FRONTEND_CONVERSION_E2E_OK")


asyncio.run(main())
