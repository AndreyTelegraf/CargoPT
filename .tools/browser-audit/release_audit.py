from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Browser, Page, async_playwright


BASE = "https://cargopt.pt"
OUT = Path(sys.argv[1])

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}

SCREENSHOTS_PER_TEMPLATE = 3
NAVIGATION_TIMEOUT_MS = 45_000
POST_LOAD_WAIT_MS = 800

NON_HTML_RESOURCE_SUFFIXES = {
    ".md",
    ".txt",
}


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 CargoPT pre-release browser audit"
            )
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def is_html_page_url(url: str) -> bool:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix not in NON_HTML_RESOURCE_SUFFIXES


def load_sitemap_urls() -> tuple[list[str], list[str]]:
    xml_text = fetch_text(f"{BASE}/sitemap.xml")
    root = ET.fromstring(xml_text)

    html_urls: set[str] = set()
    non_html_resources: set[str] = set()

    for node in root.iter():
        if not node.tag.endswith("loc") or not node.text:
            continue

        url = node.text.strip()

        if not url.startswith(BASE):
            continue

        if is_html_page_url(url):
            html_urls.add(url)
        else:
            non_html_resources.add(url)

    return sorted(html_urls), sorted(non_html_resources)


def classify_template(url: str) -> str:
    path = urlparse(url).path.strip("/")

    if not path:
        return "home-pt"

    if path == "en":
        return "home-en"

    if path == "ru":
        return "home-ru"

    if path in {
        "transportadores",
        "en/carriers",
        "ru/carriers",
    }:
        return "carriers"

    if path in {
        "guias",
        "en/guides",
        "ru/guides",
    }:
        return "guides-index"

    if path.startswith("guias/"):
        parts = path.split("/")
        cluster = parts[1] if len(parts) > 1 else "other"
        return f"guide-{cluster}"

    if re.match(r"^(en/|ru/)?track/", path):
        return "tracking"

    if path.startswith(("en/", "ru/")):
        return "localized-page"

    return "service-landing"


def safe_slug(url: str) -> str:
    path = urlparse(url).path.strip("/") or "home"
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", path).strip("-")

    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]

    return f"{slug[:100]}-{digest}"


async def dismiss_optional_ui(page: Page) -> None:
    selectors = [
        '[aria-label*="cookie" i]',
        '[class*="cookie"] button',
        '[id*="cookie"] button',
        'button:has-text("Aceitar")',
        'button:has-text("Accept")',
        'button:has-text("Принять")',
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector).first

            if await locator.is_visible(timeout=150):
                await locator.click(timeout=500)
        except Exception:
            pass


async def inspect_page(page: Page) -> dict:
    return await page.evaluate(
        """
        () => {
          const qs = (selector) => document.querySelector(selector);
          const qsa = (selector) =>
            Array.from(document.querySelectorAll(selector));

          const attr = (selector, name) =>
            qs(selector)?.getAttribute(name) || null;

          const text = (selector) =>
            qs(selector)?.textContent?.replace(/\\s+/g, " ").trim() || null;

          const isVisible = (element) => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();

            return (
              style.display !== "none" &&
              style.visibility !== "hidden" &&
              style.opacity !== "0" &&
              rect.width > 0 &&
              rect.height > 0
            );
          };

          const headings = qsa("h1,h2,h3,h4,h5,h6").map((element) => ({
            level: Number(element.tagName.slice(1)),
            text: element.textContent.replace(/\\s+/g, " ").trim(),
          }));

          const headingSequenceProblems = [];

          for (let index = 1; index < headings.length; index += 1) {
            const previous = headings[index - 1].level;
            const current = headings[index].level;

            if (current > previous + 1) {
              headingSequenceProblems.push({
                previous,
                current,
                text: headings[index].text,
              });
            }
          }

          const visibleInteractive = qsa(
            'a[href], button, input:not([type="hidden"]), select, ' +
            'textarea, [role="button"], summary'
          ).filter(isVisible);

          const TARGET_SIZE_MINIMUM = 24;
          const TARGET_SIZE_ENHANCED = 44;

          const targetDetails = visibleInteractive.map(
            (element) => {
              const rect = element.getBoundingClientRect();
              const style = getComputedStyle(element);

              const elementText = (
                element.textContent ||
                element.getAttribute("aria-label") ||
                element.getAttribute("name") ||
                ""
              ).replace(/\\s+/g, " ").trim();

              const inlineContainer = element.closest(
                "p, dd, dt, figcaption, blockquote, li"
              );

              const containerText = (
                inlineContainer?.textContent || ""
              ).replace(/\\s+/g, " ").trim();

              const inlineException = Boolean(
                element.tagName === "A" &&
                style.display.startsWith("inline") &&
                inlineContainer &&
                containerText.length > elementText.length
              );

              return {
                element,
                rect,
                detail: {
                  tag: element.tagName,
                  text: elementText.slice(0, 80),
                  width: Math.round(rect.width),
                  height: Math.round(rect.height),
                  display: style.display,
                  inlineException,
                },
              };
            }
          );

          const compactTargets = targetDetails
            .filter(
              (target) =>
                target.detail.width < TARGET_SIZE_ENHANCED ||
                target.detail.height < TARGET_SIZE_ENHANCED
            )
            .map((target) => target.detail)
            .slice(0, 50);

          const circleIntersectsRect = (
            centerX,
            centerY,
            radius,
            rect
          ) => {
            const nearestX = Math.max(
              rect.left,
              Math.min(centerX, rect.right)
            );
            const nearestY = Math.max(
              rect.top,
              Math.min(centerY, rect.bottom)
            );

            const deltaX = centerX - nearestX;
            const deltaY = centerY - nearestY;

            return (
              deltaX * deltaX + deltaY * deltaY <=
              radius * radius
            );
          };

          const smallTargets = targetDetails
            .filter(
              (target) =>
                (
                  target.detail.width < TARGET_SIZE_MINIMUM ||
                  target.detail.height < TARGET_SIZE_MINIMUM
                ) &&
                !target.detail.inlineException
            )
            .filter((target) => {
              const centerX =
                target.rect.left + target.rect.width / 2;
              const centerY =
                target.rect.top + target.rect.height / 2;
              const radius = TARGET_SIZE_MINIMUM / 2;

              return targetDetails.some((other) => {
                if (other.element === target.element) {
                  return false;
                }

                if (
                  target.element.contains(other.element) ||
                  other.element.contains(target.element)
                ) {
                  return false;
                }

                if (
                  circleIntersectsRect(
                    centerX,
                    centerY,
                    radius,
                    other.rect
                  )
                ) {
                  return true;
                }

                const otherIsUndersized =
                  other.detail.width < TARGET_SIZE_MINIMUM ||
                  other.detail.height < TARGET_SIZE_MINIMUM;

                if (!otherIsUndersized) {
                  return false;
                }

                const otherCenterX =
                  other.rect.left + other.rect.width / 2;
                const otherCenterY =
                  other.rect.top + other.rect.height / 2;

                const deltaX = centerX - otherCenterX;
                const deltaY = centerY - otherCenterY;

                return (
                  deltaX * deltaX + deltaY * deltaY <=
                  TARGET_SIZE_MINIMUM * TARGET_SIZE_MINIMUM
                );
              });
            })
            .map((target) => ({
              ...target.detail,
              spacingFailure: true,
            }))
            .slice(0, 50);

          const unnamedFields = qsa(
            'input:not([type="hidden"]), select, textarea'
          )
            .filter((element) => {
              if (element.getAttribute("aria-label")) return false;
              if (element.getAttribute("aria-labelledby")) return false;

              if (
                element.id &&
                document.querySelector(`label[for="${element.id}"]`)
              ) {
                return false;
              }

              return !element.closest("label");
            })
            .map((element) => ({
              tag: element.tagName,
              type: element.getAttribute("type"),
              name: element.getAttribute("name"),
              id: element.id || null,
            }));

          const emptyLinks = qsa("a[href]")
            .filter((link) => {
              const label = (
                link.textContent ||
                link.getAttribute("aria-label") ||
                ""
              ).trim();

              return !label;
            })
            .map((link) => link.getAttribute("href"))
            .slice(0, 50);

          const images = qsa("img");

          const imagesWithoutAlt = images
            .filter((image) => !image.hasAttribute("alt"))
            .map((image) => image.getAttribute("src"))
            .slice(0, 50);

          const imagesWithEmptyAlt = images
            .filter((image) => image.getAttribute("alt") === "")
            .map((image) => image.getAttribute("src"))
            .slice(0, 50);

          const canonical = attr('link[rel="canonical"]', "href");

          const hreflang = qsa(
            'link[rel="alternate"][hreflang]'
          ).map((link) => ({
            lang: link.getAttribute("hreflang"),
            href: link.getAttribute("href"),
          }));

          const schemaBlocks = qsa(
            'script[type="application/ld+json"]'
          ).map((script) => {
            try {
              return {
                valid: true,
                value: JSON.parse(script.textContent),
              };
            } catch (error) {
              return {
                valid: false,
                error: String(error),
              };
            }
          });

          const schemaTypes = [];

          const collectSchemaTypes = (value) => {
            if (!value) return;

            if (Array.isArray(value)) {
              value.forEach(collectSchemaTypes);
              return;
            }

            if (typeof value !== "object") return;

            if (value["@type"]) {
              if (Array.isArray(value["@type"])) {
                schemaTypes.push(...value["@type"]);
              } else {
                schemaTypes.push(value["@type"]);
              }
            }

            if (Array.isArray(value["@graph"])) {
              value["@graph"].forEach(collectSchemaTypes);
            }
          };

          schemaBlocks
            .filter((block) => block.valid)
            .forEach((block) => collectSchemaTypes(block.value));

          const internalLinks = qsa("a[href]")
            .map((link) => {
              try {
                return new URL(link.href);
              } catch {
                return null;
              }
            })
            .filter(
              (url) => url && url.origin === window.location.origin
            )
            .map((url) => url.href);

          const ctas = qsa(
            'a.button, button, [role="button"], input[type="submit"]'
          )
            .filter(isVisible)
            .map((element) => ({
              tag: element.tagName,
              text:
                element.textContent?.replace(/\\s+/g, " ").trim()
                || element.getAttribute("value")
                || element.getAttribute("aria-label")
                || "",
              href: element.href || null,
              disabled: Boolean(element.disabled),
            }));

          const navigation = performance.getEntriesByType("navigation")[0];

          return {
            finalUrl: location.href,
            language: document.documentElement.lang || null,
            title: document.title || null,
            titleLength: document.title.length,
            description: attr('meta[name="description"]', "content"),
            descriptionLength:
              attr('meta[name="description"]', "content")?.length || 0,
            robots: attr('meta[name="robots"]', "content"),
            canonical,
            hreflang,
            viewport: {
              width: window.innerWidth,
              height: window.innerHeight,
            },
            document: {
              scrollWidth: document.documentElement.scrollWidth,
              clientWidth: document.documentElement.clientWidth,
              scrollHeight: document.documentElement.scrollHeight,
              clientHeight: document.documentElement.clientHeight,
              horizontalOverflow:
                document.documentElement.scrollWidth >
                document.documentElement.clientWidth + 1,
            },
            h1Count: qsa("h1").length,
            h1: text("h1"),
            headings,
            headingSequenceProblems,
            visibleCtas: ctas,
            visibleCtaCount: ctas.length,
            forms: qsa("form").length,
            visibleInteractiveCount: visibleInteractive.length,
            compactTargets,
            smallTargets,
            unnamedFields,
            emptyLinks,
            imageCount: images.length,
            imagesWithoutAlt,
            imagesWithEmptyAlt,
            internalLinkCount: new Set(internalLinks).size,
            bodyTextLength:
              document.body?.innerText
                ?.replace(/\\s+/g, " ")
                .trim()
                .length || 0,
            schemaTypes: Array.from(new Set(schemaTypes)),
            invalidSchemaBlocks: schemaBlocks.filter(
              (block) => !block.valid
            ),
            timing: navigation
              ? {
                  responseEnd: Math.round(navigation.responseEnd),
                  domContentLoaded: Math.round(
                    navigation.domContentLoadedEventEnd
                  ),
                  load: Math.round(navigation.loadEventEnd),
                  transferSize: navigation.transferSize,
                  encodedBodySize: navigation.encodedBodySize,
                }
              : null,
          };
        }
        """
    )


async def audit_one(
    browser: Browser,
    url: str,
    viewport_name: str,
    viewport: dict,
    screenshot_path: Path | None,
) -> dict:
    context = await browser.new_context(
        viewport=viewport,
        locale="pt-PT",
        color_scheme="light",
        reduced_motion="reduce",
        service_workers="block",
    )

    page = await context.new_page()

    console_errors: list[str] = []
    page_errors: list[str] = []
    request_failures: list[dict] = []
    http_errors: list[dict] = []

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
        lambda request: request_failures.append(
            {
                "url": request.url,
                "resourceType": request.resource_type,
                "failure": request.failure,
            }
        ),
    )

    page.on(
        "response",
        lambda response: (
            http_errors.append(
                {
                    "url": response.url,
                    "status": response.status,
                    "resourceType": response.request.resource_type,
                }
            )
            if response.status >= 400
            else None
        ),
    )

    started = time.monotonic()
    status = None
    navigation_error = None

    try:
        response = await page.goto(
            url,
            wait_until="networkidle",
            timeout=NAVIGATION_TIMEOUT_MS,
        )

        status = response.status if response else None

    except Exception as error:
        navigation_error = repr(error)

        try:
            await page.wait_for_load_state(
                "domcontentloaded",
                timeout=5_000,
            )
        except Exception:
            pass

    await page.wait_for_timeout(POST_LOAD_WAIT_MS)
    await dismiss_optional_ui(page)

    try:
        details = await inspect_page(page)
    except Exception as error:
        details = {
            "inspectionError": repr(error),
            "finalUrl": page.url,
        }

    screenshot_error = None

    if screenshot_path is not None:
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            await page.screenshot(
                path=str(screenshot_path),
                full_page=True,
                animations="disabled",
            )
        except Exception as error:
            screenshot_error = repr(error)

    elapsed_ms = round((time.monotonic() - started) * 1000)

    await context.close()

    return {
        "requestedUrl": url,
        "template": classify_template(url),
        "viewportName": viewport_name,
        "httpStatus": status,
        "navigationError": navigation_error,
        "wallTimeMs": elapsed_ms,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "requestFailures": request_failures,
        "httpErrors": http_errors,
        "screenshot": (
            str(screenshot_path.relative_to(OUT))
            if screenshot_path is not None
            else None
        ),
        "screenshotError": screenshot_error,
        **details,
    }


def issue_categories(result: dict) -> list[str]:
    categories: list[str] = []

    if result.get("httpStatus") != 200:
        categories.append("http_failure")

    if result.get("navigationError"):
        categories.append("navigation_error")

    if result.get("consoleErrors") or result.get("pageErrors"):
        categories.append("runtime_error")

    if result.get("requestFailures") or result.get("httpErrors"):
        categories.append("resource_failure")

    document = result.get("document") or {}

    if document.get("horizontalOverflow"):
        categories.append("horizontal_overflow")

    if result.get("h1Count") != 1:
        categories.append("h1_invalid")

    if not result.get("title"):
        categories.append("title_missing")

    if not result.get("description"):
        categories.append("description_missing")

    if not result.get("canonical"):
        categories.append("canonical_missing")

    if not result.get("language"):
        categories.append("language_missing")

    if result.get("invalidSchemaBlocks"):
        categories.append("schema_invalid")

    if result.get("unnamedFields"):
        categories.append("field_name_missing")

    if result.get("imagesWithoutAlt"):
        categories.append("image_alt_missing")

    if (
        result.get("viewportName") == "mobile"
        and result.get("smallTargets")
    ):
        categories.append("small_touch_targets")

    if result.get("headingSequenceProblems"):
        categories.append("heading_sequence")

    if result.get("emptyLinks"):
        categories.append("empty_links")

    return categories


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    screenshots_root = OUT / "screenshots"
    screenshots_root.mkdir(parents=True, exist_ok=True)

    urls, non_html_resources = load_sitemap_urls()

    (OUT / "urls.txt").write_text(
        "\n".join(urls) + "\n",
        encoding="utf-8",
    )

    (OUT / "non-html-resources.txt").write_text(
        (
            "\n".join(non_html_resources) + "\n"
            if non_html_resources
            else ""
        ),
        encoding="utf-8",
    )

    template_screenshot_counts: dict[tuple[str, str], int] = defaultdict(int)
    results: list[dict] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        total = len(urls) * len(VIEWPORTS)
        audit_index = 0

        for url_index, url in enumerate(urls, start=1):
            template = classify_template(url)

            for viewport_name, viewport in VIEWPORTS.items():
                audit_index += 1

                print(
                    f"[{audit_index:03d}/{total}] "
                    f"{viewport_name:<7} {url}",
                    flush=True,
                )

                screenshot_key = (template, viewport_name)
                screenshot_path = None

                if (
                    template_screenshot_counts[screenshot_key]
                    < SCREENSHOTS_PER_TEMPLATE
                ):
                    template_screenshot_counts[screenshot_key] += 1

                    screenshot_path = (
                        screenshots_root
                        / viewport_name
                        / template
                        / f"{safe_slug(url)}.png"
                    )

                result = await audit_one(
                    browser,
                    url,
                    viewport_name,
                    viewport,
                    screenshot_path,
                )

                result["issues"] = issue_categories(result)
                results.append(result)

        await browser.close()

    issue_counts = Counter(
        issue
        for result in results
        for issue in result["issues"]
    )

    urls_with_issues = [
        {
            "url": result["requestedUrl"],
            "viewport": result["viewportName"],
            "template": result["template"],
            "issues": result["issues"],
        }
        for result in results
        if result["issues"]
    ]

    templates = defaultdict(
        lambda: {
            "urls": set(),
            "audits": 0,
            "screenshots": [],
            "issues": Counter(),
        }
    )

    for result in results:
        template = result["template"]
        templates[template]["urls"].add(result["requestedUrl"])
        templates[template]["audits"] += 1

        if result.get("screenshot"):
            templates[template]["screenshots"].append(
                result["screenshot"]
            )

        templates[template]["issues"].update(result["issues"])

    template_summary = {
        template: {
            "urlCount": len(data["urls"]),
            "auditCount": data["audits"],
            "screenshots": data["screenshots"],
            "issueCounts": dict(data["issues"]),
        }
        for template, data in sorted(templates.items())
    }

    summary = {
        "baseUrl": BASE,
        "urlCount": len(urls),
        "nonHtmlResourceCount": len(non_html_resources),
        "nonHtmlResources": non_html_resources,
        "auditCount": len(results),
        "desktopAuditCount": sum(
            result["viewportName"] == "desktop"
            for result in results
        ),
        "mobileAuditCount": sum(
            result["viewportName"] == "mobile"
            for result in results
        ),
        "issueCounts": dict(issue_counts),
        "auditsWithIssues": len(urls_with_issues),
        "auditsWithoutIssues": len(results) - len(urls_with_issues),
        "templates": template_summary,
        "urlsWithIssues": urls_with_issues,
    }

    (OUT / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"URL_COUNT={summary['urlCount']}")
    print(
        "NON_HTML_RESOURCE_COUNT="
        f"{summary['nonHtmlResourceCount']}"
    )
    print(f"AUDIT_COUNT={summary['auditCount']}")
    print(f"AUDITS_WITH_ISSUES={summary['auditsWithIssues']}")
    print(f"AUDITS_WITHOUT_ISSUES={summary['auditsWithoutIssues']}")

    for issue, count in sorted(issue_counts.items()):
        print(f"ISSUE_{issue.upper()}={count}")

    print(f"OUTPUT={OUT}")


asyncio.run(main())
