from __future__ import annotations

import ast
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve()
BASE_URL = "https://cargopt.pt"

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}

PAGES = [
    ("pt-landing", "/", "pt-PT"),
    ("en-landing", "/en/", "en"),
    ("ru-landing", "/ru/", "ru"),
    ("pt-carriers", "/transportadores/", "pt-PT"),
]

TRACKING_PAGES = [
    ("pt-tracking", "/track/a11y-active", "pt-PT"),
    ("en-tracking", "/en/track/a11y-active", "en"),
    ("ru-tracking", "/ru/track/a11y-active", "ru"),
]


def load_tracking_snapshot_function():
    source_path = (
        PROJECT_ROOT
        / ".tools/browser-audit/conversion_frontend_e2e.py"
    )

    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))

    target = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "tracking_snapshot"
        ),
        None,
    )

    if target is None:
        raise RuntimeError(
            "tracking_snapshot function was not found in "
            "conversion_frontend_e2e.py"
        )

    module = ast.Module(body=[target], type_ignores=[])
    ast.fix_missing_locations(module)

    namespace: dict[str, Any] = {}

    exec(
        compile(
            module,
            filename=str(source_path),
            mode="exec",
        ),
        namespace,
    )

    return namespace["tracking_snapshot"]


tracking_snapshot = load_tracking_snapshot_function()


async def collect_runtime(page: Page) -> dict[str, list[Any]]:
    runtime: dict[str, list[Any]] = {
        "consoleErrors": [],
        "pageErrors": [],
        "failedRequests": [],
        "writeRequests": [],
    }

    page.on(
        "console",
        lambda message: (
            runtime["consoleErrors"].append(message.text)
            if message.type == "error"
            else None
        ),
    )

    page.on(
        "pageerror",
        lambda error: runtime["pageErrors"].append(str(error)),
    )

    page.on(
        "requestfailed",
        lambda request: runtime["failedRequests"].append(
            {
                "method": request.method,
                "url": request.url,
                "failure": request.failure,
            }
        ),
    )

    page.on(
        "request",
        lambda request: (
            runtime["writeRequests"].append(
                {
                    "method": request.method,
                    "url": request.url,
                }
            )
            if request.method.upper()
            not in {"GET", "HEAD", "OPTIONS"}
            else None
        ),
    )

    return runtime


async def dom_audit(page: Page) -> dict[str, Any]:
    return await page.evaluate(
        """
        () => {
          const isVisible = (element) => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();

            return (
              style.display !== "none"
              && style.visibility !== "hidden"
              && Number(style.opacity) !== 0
              && rect.width > 0
              && rect.height > 0
              && !element.hidden
            );
          };

          const textFromIds = (value) => {
            if (!value) return "";

            return value
              .split(/\\s+/)
              .map((id) => document.getElementById(id)?.textContent || "")
              .join(" ")
              .trim();
          };

          const accessibleName = (element) => {
            const ariaLabel = element.getAttribute("aria-label");

            if (ariaLabel?.trim()) return ariaLabel.trim();

            const labelledBy = textFromIds(
              element.getAttribute("aria-labelledby")
            );

            if (labelledBy) return labelledBy;

            if (element.id) {
              const label = document.querySelector(
                `label[for="${CSS.escape(element.id)}"]`
              );

              if (label?.textContent?.trim()) {
                return label.textContent.trim();
              }
            }

            const parentLabel = element.closest("label");

            if (parentLabel?.textContent?.trim()) {
              return parentLabel.textContent.trim();
            }

            const alt = element.getAttribute("alt");

            if (alt?.trim()) return alt.trim();

            const title = element.getAttribute("title");

            if (title?.trim()) return title.trim();

            const text = element.textContent?.trim();

            if (text) return text;

            if (
              element instanceof HTMLInputElement
              && ["button", "submit", "reset"].includes(element.type)
            ) {
              return element.value.trim();
            }

            return "";
          };

          const selectorFor = (element) => {
            if (element.id) return `#${element.id}`;

            const classes = [...element.classList]
              .slice(0, 3)
              .map((value) => `.${CSS.escape(value)}`)
              .join("");

            return `${element.tagName.toLowerCase()}${classes}`;
          };

          const ids = [...document.querySelectorAll("[id]")]
            .map((element) => element.id);

          const duplicateIds = [...new Set(
            ids.filter(
              (value, index) => ids.indexOf(value) !== index
            )
          )];

          const ariaReferenceAttributes = [
            "aria-controls",
            "aria-describedby",
            "aria-labelledby",
            "aria-owns",
          ];

          const brokenAriaReferences = [];

          for (
            const element
            of document.querySelectorAll(
              ariaReferenceAttributes
                .map((name) => `[${name}]`)
                .join(",")
            )
          ) {
            for (const attribute of ariaReferenceAttributes) {
              const value = element.getAttribute(attribute);

              if (!value) continue;

              for (const id of value.split(/\\s+/)) {
                if (!document.getElementById(id)) {
                  brokenAriaReferences.push({
                    selector: selectorFor(element),
                    attribute,
                    target: id,
                  });
                }
              }
            }
          }

          const interactiveSelector = [
            "a[href]",
            "button",
            "input:not([type='hidden'])",
            "select",
            "textarea",
            "[role='button']",
            "[role='link']",
            "[tabindex]",
          ].join(",");

          const unnamedInteractive = [
            ...document.querySelectorAll(interactiveSelector)
          ]
            .filter(isVisible)
            .filter((element) => {
              const tabindex = element.getAttribute("tabindex");

              return (
                !element.disabled
                && tabindex !== "-1"
                && !accessibleName(element)
              );
            })
            .map((element) => ({
              selector: selectorFor(element),
              tag: element.tagName.toLowerCase(),
              role: element.getAttribute("role"),
            }));

          const genericFocusable = [
            ...document.querySelectorAll("[tabindex]")
          ]
            .filter(isVisible)
            .filter((element) => {
              const tabindex = Number(
                element.getAttribute("tabindex")
              );

              return (
                tabindex >= 0
                && !element.matches(
                  "a[href],button,input,select,textarea,"
                  + "[role='button'],[role='link']"
                )
              );
            })
            .map((element) => ({
              selector: selectorFor(element),
              tag: element.tagName.toLowerCase(),
              role: element.getAttribute("role"),
              name: accessibleName(element),
            }));

          return {
            lang: document.documentElement.lang || "",
            title: document.title,
            duplicateIds,
            brokenAriaReferences,
            unnamedInteractive,
            genericFocusable,
            mainCount: document.querySelectorAll("main").length,
            h1Count: document.querySelectorAll("h1").length,
          };
        }
        """
    )


async def ax_tree_audit(
    context: BrowserContext,
    page: Page,
) -> dict[str, Any]:
    session = await context.new_cdp_session(page)

    tree = await session.send(
        "Accessibility.getFullAXTree"
    )

    focusable_nodes = []
    unnamed_focusable_nodes = []
    generic_focusable_nodes = []

    for node in tree.get("nodes", []):
        if node.get("ignored"):
            continue

        role = str(
            (node.get("role") or {}).get("value") or ""
        )

        name = str(
            (node.get("name") or {}).get("value") or ""
        ).strip()

        properties = {
            property_value.get("name"): (
                property_value.get("value") or {}
            ).get("value")
            for property_value in node.get("properties", [])
        }

        if properties.get("focusable") is not True:
            continue

        item = {
            "role": role,
            "name": name,
            "backendDOMNodeId": node.get(
                "backendDOMNodeId"
            ),
        }

        focusable_nodes.append(item)

        if not name:
            unnamed_focusable_nodes.append(item)

        if role in {
            "",
            "none",
            "generic",
            "genericContainer",
        }:
            generic_focusable_nodes.append(item)

    return {
        "nodeCount": len(tree.get("nodes", [])),
        "focusableNodeCount": len(focusable_nodes),
        "unnamedFocusableNodes": unnamed_focusable_nodes,
        "genericFocusableNodes": generic_focusable_nodes,
    }


async def focus_audit(
    page: Page,
    limit: int = 40,
) -> dict[str, Any]:
    await page.evaluate(
        """
        () => {
          window.scrollTo(0, 0);
          document.activeElement?.blur?.();
        }
        """
    )

    entries = []
    seen = set()

    for _ in range(limit):
        await page.keyboard.press("Tab")

        entry = await page.evaluate(
            """
            () => {
              const element = document.activeElement;

              if (!element || element === document.body) {
                return null;
              }

              const style = getComputedStyle(element);

              const selector = element.id
                ? `#${element.id}`
                : `${element.tagName.toLowerCase()}${
                    [...element.classList]
                      .slice(0, 3)
                      .map((value) => `.${value}`)
                      .join("")
                  }`;

              const outlineWidth =
                Number.parseFloat(style.outlineWidth) || 0;

              const hasOutline = (
                style.outlineStyle !== "none"
                && outlineWidth > 0
              );

              const hasShadow = (
                style.boxShadow
                && style.boxShadow !== "none"
              );

              return {
                selector,
                tag: element.tagName.toLowerCase(),
                role: element.getAttribute("role"),
                text: (
                  element.getAttribute("aria-label")
                  || element.textContent
                  || element.value
                  || ""
                ).trim().slice(0, 120),
                outlineStyle: style.outlineStyle,
                outlineWidth: style.outlineWidth,
                boxShadow: style.boxShadow,
                focusIndicatorPresent:
                  Boolean(hasOutline || hasShadow),
              };
            }
            """
        )

        if entry is None:
            continue

        key = (
            entry["selector"],
            entry["text"],
        )

        if key in seen:
            break

        seen.add(key)
        entries.append(entry)

    return {
        "tabStops": entries,
        "tabStopCount": len(entries),
        "withoutVisibleFocusIndicator": [
            entry
            for entry in entries
            if not entry["focusIndicatorPresent"]
        ],
    }


async def contrast_audit(page: Page) -> dict[str, Any]:
    return await page.evaluate(
        """
        () => {
          const parseColor = (value) => {
            const match = value.match(
              /rgba?\\(([^)]+)\\)/
            );

            if (!match) return null;

            const parts = match[1]
              .split(",")
              .map((part) => Number.parseFloat(part.trim()));

            return {
              r: parts[0],
              g: parts[1],
              b: parts[2],
              a: parts.length > 3 ? parts[3] : 1,
            };
          };

          const luminance = ({r, g, b}) => {
            const channels = [r, g, b].map((value) => {
              const normalized = value / 255;

              return normalized <= 0.03928
                ? normalized / 12.92
                : Math.pow(
                    (normalized + 0.055) / 1.055,
                    2.4
                  );
            });

            return (
              channels[0] * 0.2126
              + channels[1] * 0.7152
              + channels[2] * 0.0722
            );
          };

          const ratio = (first, second) => {
            const firstValue = luminance(first);
            const secondValue = luminance(second);

            return (
              (Math.max(firstValue, secondValue) + 0.05)
              / (Math.min(firstValue, secondValue) + 0.05)
            );
          };

          const visible = (element) => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();

            return (
              style.display !== "none"
              && style.visibility !== "hidden"
              && Number(style.opacity) !== 0
              && rect.width > 0
              && rect.height > 0
            );
          };

          const directText = (element) => (
            [...element.childNodes]
              .filter(
                (node) => node.nodeType === Node.TEXT_NODE
              )
              .map((node) => node.textContent || "")
              .join(" ")
              .trim()
          );

          const backgroundFor = (element) => {
            let current = element;

            while (current) {
              const style = getComputedStyle(current);

              if (
                style.backgroundImage
                && style.backgroundImage !== "none"
              ) {
                return null;
              }

              const color = parseColor(
                style.backgroundColor
              );

              if (color && color.a >= 0.99) {
                return color;
              }

              current = current.parentElement;
            }

            return {r: 255, g: 255, b: 255, a: 1};
          };

          const violations = [];
          let checked = 0;
          let skipped = 0;

          for (
            const element
            of document.querySelectorAll(
              "p,a,button,label,legend,h1,h2,h3,"
              + "h4,h5,h6,span,strong,li"
            )
          ) {
            if (!visible(element)) continue;

            if (element.closest('[aria-hidden="true"]')) {
              skipped += 1;
              continue;
            }

            const text = directText(element);

            if (!text) continue;

            const style = getComputedStyle(element);
            const foreground = parseColor(style.color);
            const background = backgroundFor(element);

            if (
              !foreground
              || foreground.a < 0.99
              || !background
            ) {
              skipped += 1;
              continue;
            }

            checked += 1;

            const fontSize = Number.parseFloat(
              style.fontSize
            );

            const fontWeight = Number.parseInt(
              style.fontWeight,
              10
            ) || 400;

            const largeText = (
              fontSize >= 24
              || (fontSize >= 18.66 && fontWeight >= 700)
            );

            const required = largeText ? 3 : 4.5;
            const actual = ratio(
              foreground,
              background
            );

            if (actual + 0.01 < required) {
              violations.push({
                tag: element.tagName.toLowerCase(),
                text: text.slice(0, 120),
                ratio: Number(actual.toFixed(2)),
                required,
                fontSize,
                fontWeight,
                color: style.color,
                background: getComputedStyle(
                  element.parentElement || element
                ).backgroundColor,
              });
            }
          }

          return {
            checked,
            skipped,
            violations: violations.slice(0, 100),
          };
        }
        """
    )


async def motion_audit(page: Page) -> dict[str, Any]:
    return await page.evaluate(
        """
        () => {
          const selectors = [
            ".tracking-status-dot",
            ".process-carousel .process-card",
            ".button",
            ".progress-bar span",
            ".progress-header-marker",
          ];

          const entries = [];

          for (const selector of selectors) {
            for (
              const element
              of document.querySelectorAll(selector)
            ) {
              const style = getComputedStyle(element);
              const rect = element.getBoundingClientRect();

              if (
                style.display === "none"
                || style.visibility === "hidden"
                || rect.width === 0
                || rect.height === 0
              ) {
                continue;
              }

              entries.push({
                selector,
                animationName: style.animationName,
                animationDuration: style.animationDuration,
                animationIterationCount:
                  style.animationIterationCount,
                transitionDuration:
                  style.transitionDuration,
                transitionProperty:
                  style.transitionProperty,
              });
            }
          }

          const activeAnimations = entries.filter(
            (entry) => (
              entry.animationName !== "none"
              && entry.animationDuration !== "0s"
            )
          );

          const activeTransitions = entries.filter(
            (entry) => (
              entry.transitionDuration
              .split(",")
              .some(
                (value) => value.trim() !== "0s"
              )
            )
          );

          return {
            prefersReducedMotion: matchMedia(
              "(prefers-reduced-motion: reduce)"
            ).matches,
            entries,
            activeAnimations,
            activeTransitions,
          };
        }
        """
    )


async def zoom_audit(
    context: BrowserContext,
    page: Page,
) -> dict[str, Any]:
    session = await context.new_cdp_session(page)

    try:
        await session.send(
            "Emulation.setPageScaleFactor",
            {"pageScaleFactor": 2},
        )

        await page.wait_for_timeout(200)

        result = await page.evaluate(
            """
            () => ({
              horizontalOverflow:
                document.documentElement.scrollWidth
                > document.documentElement.clientWidth + 1,
              scrollWidth:
                document.documentElement.scrollWidth,
              clientWidth:
                document.documentElement.clientWidth,
            })
            """
        )

        result["supported"] = True
        return result

    except Exception as error:
        return {
            "supported": False,
            "error": f"{type(error).__name__}: {error}",
        }

    finally:
        try:
            await session.send(
                "Emulation.setPageScaleFactor",
                {"pageScaleFactor": 1},
            )
        except Exception:
            pass


async def audit_loaded_page(
    context: BrowserContext,
    page: Page,
    *,
    page_id: str,
    viewport_name: str,
    path: str,
    runtime: dict[str, list[Any]],
) -> dict[str, Any]:
    await page.wait_for_timeout(300)

    result = {
        "pageId": page_id,
        "viewport": viewport_name,
        "path": path,
        "url": page.url,
        "dom": await dom_audit(page),
        "axTree": await ax_tree_audit(
            context,
            page,
        ),
        "focus": await focus_audit(page),
        "contrast": await contrast_audit(page),
        "motion": await motion_audit(page),
        "zoom200": await zoom_audit(
            context,
            page,
        ),
        "runtime": runtime,
    }

    await page.screenshot(
        path=str(
            OUT
            / f"{page_id}-{viewport_name}.png"
        ),
        full_page=True,
        animations="disabled",
    )

    return result


async def audit_public_page(
    browser: Browser,
    *,
    page_id: str,
    path: str,
    locale: str,
    viewport_name: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    context = await browser.new_context(
        viewport=viewport,
        locale=locale,
        color_scheme="light",
        reduced_motion="reduce",
        service_workers="block",
    )

    page = await context.new_page()
    runtime = await collect_runtime(page)

    await page.goto(
        f"{BASE_URL}{path}",
        wait_until="networkidle",
    )

    result = await audit_loaded_page(
        context,
        page,
        page_id=page_id,
        viewport_name=viewport_name,
        path=path,
        runtime=runtime,
    )

    await context.close()
    return result


async def tracking_route(route, request):
    parsed = urlparse(request.url)
    token = unquote(
        parsed.path.rstrip("/").split("/")[-1]
    )

    snapshot = tracking_snapshot(token)

    await route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(
            snapshot,
            ensure_ascii=False,
        ),
    )


async def audit_tracking_page(
    browser: Browser,
    *,
    page_id: str,
    path: str,
    locale: str,
    viewport_name: str,
    viewport: dict[str, int],
) -> dict[str, Any]:
    context = await browser.new_context(
        viewport=viewport,
        locale=locale,
        color_scheme="light",
        reduced_motion="reduce",
        service_workers="block",
    )

    await context.add_init_script(
        """
        localStorage.setItem(
          "cargopt_tracking_links",
          JSON.stringify([
            {
              job_id: 900001,
              token: "a11y-active",
              tracking_url: "/track/a11y-active",
              route_summary: "Lisboa → Cascais",
              item_summary: "Caixas e mobiliário"
            },
            {
              job_id: 900002,
              token: "a11y-other",
              tracking_url: "/track/a11y-other",
              route_summary: "Sintra → Lisboa",
              item_summary: "Sofá"
            }
          ])
        );
        """
    )

    await context.route(
        "**/api/v1/track/*",
        tracking_route,
    )

    page = await context.new_page()
    runtime = await collect_runtime(page)

    await page.goto(
        f"{BASE_URL}{path}",
        wait_until="networkidle",
    )

    result = await audit_loaded_page(
        context,
        page,
        page_id=page_id,
        viewport_name=viewport_name,
        path=path,
        runtime=runtime,
    )

    if viewport_name == "mobile":
        toggle = page.locator(
            "#otherRequestsToggle"
        )

        await toggle.focus()
        await page.keyboard.press("Enter")

        result["accordionKeyboard"] = {
            "expandedAfterEnter": (
                await toggle.get_attribute(
                    "aria-expanded"
                )
                == "true"
            ),
            "listVisible": await page.locator(
                "#trackPedidosList"
            ).is_visible(),
        }

        card = page.locator(
            ".track-offer-nav-card"
        ).first

        await card.focus()

        async with page.expect_navigation(
            wait_until="networkidle",
        ):
            await page.keyboard.press(" ")

        result["cardKeyboard"] = {
            "urlAfterSpace": page.url,
            "openedOtherRequest": (
                page.url.endswith(
                    "/track/a11y-other"
                )
            ),
        }

        await page.screenshot(
            path=str(
                OUT
                / f"{page_id}-{viewport_name}"
                "-keyboard.png"
            ),
            full_page=True,
            animations="disabled",
        )

    await context.close()
    return result


async def validation_keyboard_scenario(
    browser: Browser,
) -> dict[str, Any]:
    context = await browser.new_context(
        viewport=VIEWPORTS["mobile"],
        locale="pt-PT",
        color_scheme="light",
        reduced_motion="reduce",
        service_workers="block",
    )

    page = await context.new_page()
    runtime = await collect_runtime(page)

    await page.goto(
        f"{BASE_URL}/",
        wait_until="networkidle",
    )

    next_button = page.locator("[data-next]")

    await next_button.focus()
    await page.keyboard.press("Enter")

    await page.locator(
        ".field-validation-message"
    ).first.wait_for()

    result = await page.evaluate(
        """
        () => {
          const active = document.activeElement;
          const describedBy = active?.getAttribute(
            "aria-describedby"
          );

          const description = describedBy
            ? document.getElementById(describedBy)
            : null;

          return {
            activeElementName:
              active?.getAttribute("name") || null,
            activeElementId: active?.id || null,
            activeAriaInvalid:
              active?.getAttribute("aria-invalid"),
            activeAriaDescribedBy: describedBy,
            descriptionExists: Boolean(description),
            descriptionRole:
              description?.getAttribute("role") || null,
            descriptionText:
              description?.textContent?.trim() || "",
            firstStepActive:
              document.querySelector(
                '.form-step[data-step="1"]'
              )?.classList.contains("is-active")
              || false,
          };
        }
        """
    )

    result["runtime"] = runtime

    await page.screenshot(
        path=str(
            OUT
            / "validation-keyboard-mobile.png"
        ),
        full_page=True,
        animations="disabled",
    )

    await context.close()
    return result


def build_findings(
    page_results: list[dict[str, Any]],
    validation_result: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []

    for result in page_results:
        key = (
            f"{result['pageId']}:"
            f"{result['viewport']}"
        )

        dom = result["dom"]
        ax_tree = result["axTree"]
        focus = result["focus"]
        contrast = result["contrast"]
        motion = result["motion"]
        zoom = result["zoom200"]
        runtime = result["runtime"]

        checks = [
            (
                "duplicate_ids",
                dom["duplicateIds"],
                "serious",
            ),
            (
                "broken_aria_references",
                dom["brokenAriaReferences"],
                "serious",
            ),
            (
                "unnamed_interactive",
                dom["unnamedInteractive"],
                "serious",
            ),
            (
                "generic_focusable_dom",
                dom["genericFocusable"],
                "moderate",
            ),
            (
                "unnamed_focusable_ax",
                ax_tree["unnamedFocusableNodes"],
                "serious",
            ),
            (
                "generic_focusable_ax",
                ax_tree["genericFocusableNodes"],
                "moderate",
            ),
            (
                "missing_focus_indicator",
                focus[
                    "withoutVisibleFocusIndicator"
                ],
                "serious",
            ),
            (
                "contrast",
                contrast["violations"],
                "serious",
            ),
            (
                "reduced_motion_animations",
                motion["activeAnimations"],
                "moderate",
            ),
            (
                "reduced_motion_transitions",
                motion["activeTransitions"],
                "minor",
            ),
            (
                "write_requests",
                runtime["writeRequests"],
                "critical",
            ),
            (
                "page_errors",
                runtime["pageErrors"],
                "serious",
            ),
        ]

        if (
            zoom.get("supported")
            and zoom.get("horizontalOverflow")
        ):
            checks.append(
                (
                    "zoom_200_horizontal_overflow",
                    [zoom],
                    "serious",
                )
            )

        for finding_type, evidence, severity in checks:
            if not evidence:
                continue

            findings.append(
                {
                    "id": (
                        f"a11y:{key}:{finding_type}"
                    ),
                    "pageId": result["pageId"],
                    "viewport": result["viewport"],
                    "type": finding_type,
                    "severity": severity,
                    "evidence": evidence,
                }
            )

    if (
        validation_result.get("activeAriaInvalid")
        != "true"
        or not validation_result.get(
            "descriptionExists"
        )
        or validation_result.get("descriptionRole")
        != "alert"
        or not validation_result.get(
            "firstStepActive"
        )
    ):
        findings.append(
            {
                "id": (
                    "a11y:validation:"
                    "keyboard_error_contract"
                ),
                "pageId": "pt-landing",
                "viewport": "mobile",
                "type": (
                    "keyboard_error_contract"
                ),
                "severity": "serious",
                "evidence": validation_result,
            }
        )

    return findings


async def main() -> None:
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    page_results = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        for viewport_name, viewport in VIEWPORTS.items():
            for page_id, path, locale in PAGES:
                print(
                    f"RUN {page_id} {viewport_name}",
                    flush=True,
                )

                page_results.append(
                    await audit_public_page(
                        browser,
                        page_id=page_id,
                        path=path,
                        locale=locale,
                        viewport_name=viewport_name,
                        viewport=viewport,
                    )
                )

            for page_id, path, locale in TRACKING_PAGES:
                print(
                    f"RUN {page_id} {viewport_name}",
                    flush=True,
                )

                page_results.append(
                    await audit_tracking_page(
                        browser,
                        page_id=page_id,
                        path=path,
                        locale=locale,
                        viewport_name=viewport_name,
                        viewport=viewport,
                    )
                )

        validation_result = (
            await validation_keyboard_scenario(
                browser
            )
        )

        await browser.close()

    findings = build_findings(
        page_results,
        validation_result,
    )

    write_requests = [
        request
        for result in page_results
        for request in result["runtime"][
            "writeRequests"
        ]
    ]

    write_requests.extend(
        validation_result["runtime"][
            "writeRequests"
        ]
    )

    output = {
        "collector": "accessibility",
        "baseUrl": BASE_URL,
        "browser": "chromium",
        "productionWrites": len(write_requests),
        "realRequestSubmission": False,
        "usedMockedTrackingApi": True,
        "pageResults": page_results,
        "validationKeyboard": validation_result,
        "findings": findings,
        "summary": {
            "pageScenarioCount": len(
                page_results
            ),
            "findingCount": len(findings),
            "criticalCount": sum(
                finding["severity"] == "critical"
                for finding in findings
            ),
            "seriousCount": sum(
                finding["severity"] == "serious"
                for finding in findings
            ),
            "moderateCount": sum(
                finding["severity"] == "moderate"
                for finding in findings
            ),
            "minorCount": sum(
                finding["severity"] == "minor"
                for finding in findings
            ),
        },
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

    (OUT / "findings.json").write_text(
        json.dumps(
            findings,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if write_requests:
        raise RuntimeError(
            "accessibility collector attempted "
            f"{len(write_requests)} write request(s)"
        )

    print()
    print(
        "PAGE_SCENARIOS="
        f"{len(page_results)}"
    )
    print(
        "FINDINGS="
        f"{len(findings)}"
    )
    print("PRODUCTION_WRITES=0")
    print("REAL_REQUEST_SUBMISSION=false")
    print("MOCKED_TRACKING_API=true")
    print(f"OUTPUT={OUT}")
    print("ACCESSIBILITY_COLLECTOR_EXECUTION_OK")


asyncio.run(main())
