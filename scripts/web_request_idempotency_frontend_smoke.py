import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"
JS_PATH = STATIC / "assets/js/landing.js"
ASSET_VERSION = "urgent-policy-v1"


def main() -> None:
    javascript = JS_PATH.read_text(encoding="utf-8")

    required = (
        'const ACTIVE_SUBMISSION_KEY = "cargopt_active_submission_v1"',
        "let activeSubmission = loadActiveSubmission()",
        "function createIdempotencyKey()",
        "window.crypto.randomUUID()",
        "function submissionSignature(serializedPayload)",
        "function idempotencyKeyFor(serializedPayload)",
        "sessionStorage.getItem(ACTIVE_SUBMISSION_KEY)",
        "sessionStorage.setItem(",
        "sessionStorage.removeItem(ACTIVE_SUBMISSION_KEY)",
        "const requestBody = JSON.stringify(buildPayload())",
        "const idempotencyKey = idempotencyKeyFor(requestBody)",
        '"Idempotency-Key": idempotencyKey',
        "body: requestBody",
    )
    for marker in required:
        assert marker in javascript, marker

    assert javascript.index(
        "const idempotencyKey = idempotencyKeyFor(requestBody)"
    ) < javascript.index('fetch("/api/v1/requests"')
    assert javascript.index("saveTrackingLink(trackingEntry)") < javascript.index(
        "clearActiveSubmission()",
        javascript.index("saveTrackingLink(trackingEntry)"),
    )
    assert javascript.index(
        "clearActiveSubmission()",
        javascript.index("saveTrackingLink(trackingEntry)"),
    ) < javascript.index(
        "window.location.href = localizedTrackingPath(body.tracking_token)"
    )

    node_probe = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[2], "utf8");
const start = source.indexOf("function normalizeTrackingLink");
const end = source.indexOf("function formatOpenPedidosLabel", start);
if (start < 0 || end < 0) throw new Error("tracking helper block not found");
const context = {
  TRACKING_LINKS_KEY: "cargopt_tracking_links",
  localeKey: "en",
  localStorage: {
    getItem() { return null; },
    setItem() { throw new Error("simulated localStorage quota denial"); }
  },
  JSON,
  encodeURIComponent
};
vm.runInNewContext(
  source.slice(start, end)
    + "\nsaveTrackingLink({job_id: 501, token: \"tracking-token\"});",
  context,
  {filename: "landing.js"}
);
console.log("TRACKING_STORAGE_FAILURE_ISOLATED_OK");
'''
    probe = subprocess.run(
        ["node", "-", str(JS_PATH)],
        input=node_probe,
        text=True,
        capture_output=True,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr
    assert "TRACKING_STORAGE_FAILURE_ISOLATED_OK" in probe.stdout

    for locale_path in (
        STATIC / "index.html",
        STATIC / "en/index.html",
        STATIC / "ru/index.html",
    ):
        html = locale_path.read_text(encoding="utf-8")
        reference = f"/assets/js/landing.js?v={ASSET_VERSION}"
        assert html.count(reference) == 1, locale_path

    manifest_path = ROOT / "deploy/static_web_idempotency_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "assets/js/landing.js",
        "index.html",
        "en/index.html",
        "ru/index.html",
    }
    static_root = Path(manifest["static_root"])
    actual = {
        Path(value).relative_to(static_root).as_posix()
        for value in manifest["static_files"]
    }
    assert actual == expected

    print("WEB_REQUEST_IDEMPOTENCY_FRONTEND_SMOKE_OK")


if __name__ == "__main__":
    main()
