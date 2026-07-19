from __future__ import annotations

import asyncio
import json
import sys
import traceback
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Browser, Page, async_playwright


BASE_URL = "https://cargopt.pt"
OUT = Path(sys.argv[1])

VIEWPORTS = {
    "desktop": {
        "width": 1440,
        "height": 1000,
        "expected_spec_columns": 3,
    },
    "mobile": {
        "width": 390,
        "height": 844,
        "expected_spec_columns": 1,
    },
}

LOCALES = {
    "pt": {
        "path": "/track/{token}",
        "browser_locale": "pt-PT",
        "select_text": "Escolher esta oferta",
        "fail_text": "Não chegámos a acordo",
    },
    "en": {
        "path": "/en/track/{token}",
        "browser_locale": "en-GB",
        "select_text": "Choose this offer",
        "fail_text": "No agreement reached",
    },
    "ru": {
        "path": "/ru/track/{token}",
        "browser_locale": "ru-RU",
        "select_text": "Выбрать это предложение",
        "fail_text": "Не удалось договориться",
    },
}

STATES = (
    "offered",
    "assigned_pending_confirmation",
)

OFFER_ID = 77001

OFFER = {
    "offer_id": OFFER_ID,
    "company_name": "CargoPT Offer Card Contract",
    "contact_name": "Marta Silva",
    "phone": "+351910000777",
    "telegram_username": "cargopt_offer_contract",
    "vehicle_type": "Carrinha L4H3",
    "payload_kg": 2400,
    "volume_m3": 24,
    "max_loaders": 4,
    "has_tail_lift": True,
    "has_crane": True,
    "has_mobile_lift": True,
    "carrier_note": (
        "Comentário de contrato com acesso pelo portão lateral."
    ),
    "price_cents": 18750,
}

CURRENT_ASSETS = {
    "/assets/css/components.css": "offer-card-architecture-v1",
    "/assets/js/tracking-workspace.js": "no-offers-visual-state-v2",
    "/assets/js/track.js": "no-offers-visual-state-v2",
}


def build_snapshot(token: str, status: str) -> dict:
    return {
        "job_id": 99977001,
        "status": status,
        "cancelled_from_status": None,
        "tracking_token": token,
        "route_summary": "Lisboa → Cascais",
        "client_confirmation_status": None,
        "carrier_confirmation_status": None,
        "accepted_offers": [OFFER],
    }


async def collect_runtime(
    page: Page,
) -> tuple[list[str], list[str], list[dict]]:
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

    page.on(
        "pageerror",
        lambda error: page_errors.append(str(error)),
    )

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


async def inspect_card(page: Page) -> dict:
    return await page.locator(".tracking-offer-card").evaluate(
        """
        card => {
          const visible = element => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();

            return (
              style.display !== "none"
              && style.visibility !== "hidden"
              && rect.width > 0
              && rect.height > 0
            );
          };

          const specs = [
            ...card.querySelectorAll(
              ".tracking-offer-spec-list "
              + ".tracking-offer-definition"
            )
          ].filter(visible);

          const contacts = [
            ...card.querySelectorAll(
              ".tracking-offer-contact-list "
              + ".tracking-offer-definition"
            )
          ].filter(visible);

          const chips = [
            ...card.querySelectorAll(
              ".tracking-offer-equipment-chip"
            )
          ].filter(visible);

          const specX = [
            ...new Set(
              specs.map(
                element => Math.round(
                  element.getBoundingClientRect().left
                )
              )
            )
          ];

          const clipped = [
            ...card.querySelectorAll(
              ".tracking-offer-company, "
              + ".tracking-offer-vehicle-type, "
              + ".tracking-offer-definition dd, "
              + ".tracking-offer-note, "
              + ".tracking-offer-equipment-chip"
            )
          ]
            .filter(visible)
            .filter(
              element =>
                element.scrollWidth > element.clientWidth + 1
                || element.scrollHeight
                  > element.clientHeight + 1
            )
            .map(element => ({
              className: element.className,
              text: element.textContent.trim(),
              clientWidth: element.clientWidth,
              scrollWidth: element.scrollWidth,
              clientHeight: element.clientHeight,
              scrollHeight: element.scrollHeight,
            }));

          return {
            cardText: card.innerText,
            specCount: specs.length,
            specColumns: specX.length,
            contactCount: contacts.length,
            equipmentChipCount: chips.length,
            equipmentChipTexts: chips.map(
              element => element.innerText.trim()
            ),
            cardHorizontalOverflow:
              card.scrollWidth > card.clientWidth + 1,
            documentHorizontalOverflow:
              document.documentElement.scrollWidth
              > document.documentElement.clientWidth + 1,
            clipped,
          };
        }
        """
    )


async def run_scenario(
    browser: Browser,
    locale_name: str,
    locale_config: dict,
    viewport_name: str,
    viewport_config: dict,
    initial_status: str,
) -> dict:
    scenario = (
        f"{locale_name}-"
        f"{viewport_name}-"
        f"{initial_status}"
    )

    token = f"offer-card-{scenario}"

    context = await browser.new_context(
        viewport={
            "width": viewport_config["width"],
            "height": viewport_config["height"],
        },
        locale=locale_config["browser_locale"],
        color_scheme="light",
        reduced_motion="reduce",
        service_workers="block",
    )

    page = await context.new_page()
    page.set_default_timeout(20_000)

    (
        console_errors,
        page_errors,
        failed_requests,
    ) = await collect_runtime(page)

    current_status = initial_status
    api_calls: list[dict] = []
    responses: list[dict] = []

    page.on(
        "response",
        lambda response: responses.append(
            {
                "url": response.url,
                "status": response.status,
            }
        ),
    )

    async def intercept_tracking(route, request):
        nonlocal current_status

        path = urlparse(request.url).path
        method = request.method

        api_calls.append(
            {
                "method": method,
                "path": path,
            }
        )

        base_path = f"/api/v1/track/{token}"
        select_path = (
            f"{base_path}/offers/{OFFER_ID}/select"
        )
        fail_path = f"{base_path}/assignment/fail"

        if method == "GET" and path == base_path:
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    build_snapshot(token, current_status)
                ),
            )
            return

        if method == "POST" and path == select_path:
            current_status = "assigned_pending_confirmation"

            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "job_id": 99977001,
                        "status": current_status,
                        "selected_offer_id": OFFER_ID,
                    }
                ),
            )
            return

        if method == "POST" and path == fail_path:
            current_status = "offered"

            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "job_id": 99977001,
                        "status": current_status,
                        "client_confirmation_status": None,
                        "carrier_confirmation_status": None,
                    }
                ),
            )
            return

        await route.abort("blockedbyclient")

    await page.route(
        "**/api/v1/track/**",
        intercept_tracking,
    )

    result = {
        "scenario": scenario,
        "locale": locale_name,
        "viewport": viewport_name,
        "initialStatus": initial_status,
        "status": "failed",
        "issues": [],
    }

    try:
        page_path = locale_config["path"].format(
            token=token
        )

        await page.goto(
            f"{BASE_URL}{page_path}",
            wait_until="networkidle",
        )

        card = page.locator(".tracking-offer-card")
        await card.wait_for(state="visible")

        body_locale = await page.locator(
            "body"
        ).get_attribute("data-locale")

        initial_metrics = await inspect_card(page)

        select_button = page.locator(
            ".tracking-select-button:not("
            ".tracking-assignment-fail)"
        )

        fail_button = page.locator(
            ".tracking-assignment-fail"
        )

        select_count = await select_button.count()
        fail_count = await fail_button.count()

        if initial_status == "offered":
            action_button = select_button
            expected_button_text = (
                locale_config["select_text"]
            )
            expected_post_suffix = (
                f"/offers/{OFFER_ID}/select"
            )
            expected_initial_contacts = 0
            expected_final_contacts = 3
            expected_final_button = fail_button
        else:
            action_button = fail_button
            expected_button_text = (
                locale_config["fail_text"]
            )
            expected_post_suffix = "/assignment/fail"
            expected_initial_contacts = 3
            expected_final_contacts = 0
            expected_final_button = select_button

        await action_button.wait_for(state="visible")

        actual_button_text = (
            await action_button.inner_text()
        ).strip()

        keyboard_focus_reached = False

        for _ in range(80):
            await page.keyboard.press("Tab")

            keyboard_focus_reached = (
                await action_button.evaluate(
                    "element => document.activeElement === element"
                )
            )

            if keyboard_focus_reached:
                break

        async with page.expect_request(
            lambda request: (
                request.method == "POST"
                and urlparse(
                    request.url
                ).path.endswith(expected_post_suffix)
            )
        ) as callback_info:
            await page.keyboard.press("Enter")

        callback_request = await callback_info.value

        await expected_final_button.wait_for(
            state="visible"
        )

        await page.wait_for_timeout(250)

        final_metrics = await inspect_card(page)

        screenshot_path = OUT / f"{scenario}.png"

        await page.screenshot(
            path=str(screenshot_path),
            full_page=True,
            animations="disabled",
        )

        loaded_assets = {}

        for path, version in CURRENT_ASSETS.items():
            suffix = f"{path}?v={version}"

            loaded_assets[suffix] = any(
                response["status"] == 200
                and response["url"].endswith(suffix)
                for response in responses
            )

        initial_text = initial_metrics["cardText"]

        checks = {
            "bodyLocale":
                body_locale == locale_name,
            "oneOfferCard":
                await card.count() == 1,
            "companyVisible":
                OFFER["company_name"] in initial_text,
            "priceVisible":
                "187" in initial_text
                and "€" in initial_text,
            "vehicleVisible":
                OFFER["vehicle_type"] in initial_text,
            "payloadVisible":
                "2400 kg" in initial_text,
            "volumeVisible":
                "24 m³" in initial_text,
            "loadersVisible":
                "4" in initial_text,
            "carrierNoteVisible":
                OFFER["carrier_note"] in initial_text,
            "threeSpecifications":
                initial_metrics["specCount"] == 3,
            "responsiveSpecifications":
                initial_metrics["specColumns"]
                == viewport_config[
                    "expected_spec_columns"
                ],
            "threeEquipmentChips":
                initial_metrics[
                    "equipmentChipCount"
                ] == 3,
            "initialContactVisibility":
                initial_metrics["contactCount"]
                == expected_initial_contacts,
            "initialSelectButton":
                (
                    select_count == 1
                    and fail_count == 0
                    if initial_status == "offered"
                    else True
                ),
            "initialFailButton":
                (
                    fail_count == 1
                    and select_count == 0
                    if initial_status
                    == "assigned_pending_confirmation"
                    else True
                ),
            "localizedButtonText":
                actual_button_text
                == expected_button_text,
            "keyboardFocus":
                keyboard_focus_reached,
            "callbackMethod":
                callback_request.method == "POST",
            "callbackPath":
                urlparse(
                    callback_request.url
                ).path.endswith(
                    expected_post_suffix
                ),
            "finalContactVisibility":
                final_metrics["contactCount"]
                == expected_final_contacts,
            "initialCardNoOverflow":
                not initial_metrics[
                    "cardHorizontalOverflow"
                ],
            "finalCardNoOverflow":
                not final_metrics[
                    "cardHorizontalOverflow"
                ],
            "initialDocumentNoOverflow":
                not initial_metrics[
                    "documentHorizontalOverflow"
                ],
            "finalDocumentNoOverflow":
                not final_metrics[
                    "documentHorizontalOverflow"
                ],
            "initialNoClippedContent":
                initial_metrics["clipped"] == [],
            "finalNoClippedContent":
                final_metrics["clipped"] == [],
            "currentAssetsLoaded":
                all(loaded_assets.values()),
            "noConsoleErrors":
                console_errors == [],
            "noPageErrors":
                page_errors == [],
            "noFailedRequests":
                failed_requests == [],
            "screenshotWritten":
                screenshot_path.is_file(),
        }

        issues = [
            name
            for name, passed in checks.items()
            if not passed
        ]

        result.update(
            {
                "status": (
                    "passed"
                    if not issues
                    else "failed"
                ),
                "issues": issues,
                "checks": checks,
                "initialMetrics": initial_metrics,
                "finalMetrics": final_metrics,
                "selectButtonCount": select_count,
                "failButtonCount": fail_count,
                "buttonText": actual_button_text,
                "callback": {
                    "method": callback_request.method,
                    "path": urlparse(
                        callback_request.url
                    ).path,
                },
                "apiCalls": api_calls,
                "loadedAssets": loaded_assets,
                "consoleErrors": console_errors,
                "pageErrors": page_errors,
                "failedRequests": failed_requests,
                "screenshot": str(screenshot_path),
            }
        )

    except Exception as error:
        result["issues"].append(
            f"{type(error).__name__}: {error}"
        )

        result["traceback"] = traceback.format_exc()
        result["apiCalls"] = api_calls
        result["consoleErrors"] = console_errors
        result["pageErrors"] = page_errors
        result["failedRequests"] = failed_requests

        failure_path = OUT / (
            f"{scenario}-failure.png"
        )

        try:
            await page.screenshot(
                path=str(failure_path),
                full_page=True,
                animations="disabled",
            )

            result["failureScreenshot"] = str(
                failure_path
            )
        except Exception as screenshot_error:
            result["screenshotError"] = str(
                screenshot_error
            )

    finally:
        await context.close()

    return result


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

        try:
            for locale_name, locale_config in (
                LOCALES.items()
            ):
                for viewport_name, viewport_config in (
                    VIEWPORTS.items()
                ):
                    for initial_status in STATES:
                        scenario = (
                            f"{locale_name}-"
                            f"{viewport_name}-"
                            f"{initial_status}"
                        )

                        print(
                            f"RUN {scenario}",
                            flush=True,
                        )

                        result = await run_scenario(
                            browser,
                            locale_name,
                            locale_config,
                            viewport_name,
                            viewport_config,
                            initial_status,
                        )

                        results.append(result)

                        print(
                            "RESULT "
                            f"{scenario} "
                            f"{result['status']} "
                            f"{result['issues']}",
                            flush=True,
                        )
        finally:
            await browser.close()

    passed = sum(
        result["status"] == "passed"
        for result in results
    )

    failed = len(results) - passed

    output = {
        "baseUrl": BASE_URL,
        "productionWrites": 0,
        "realProductionApiUsed": False,
        "scenarioCount": len(results),
        "passedCount": passed,
        "failedCount": failed,
        "matrix": {
            "locales": list(LOCALES),
            "viewports": list(VIEWPORTS),
            "states": list(STATES),
        },
        "results": results,
    }

    (OUT / "results.json").write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(f"SCENARIOS={len(results)}")
    print(f"PASSED={passed}")
    print(f"FAILED={failed}")
    print("PRODUCTION_WRITES=0")
    print("REAL_PRODUCTION_API_USED=false")
    print(f"OUTPUT={OUT}")

    if failed:
        raise SystemExit(1)

    print("OFFER_CARD_CONTRACT_OK")


if __name__ == "__main__":
    asyncio.run(main())
