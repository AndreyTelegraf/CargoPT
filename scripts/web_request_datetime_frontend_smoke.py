import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "app/static/assets/js/landing.js"


NODE_PROBE = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[2], "utf8");
const start = source.indexOf("function isValidCalendarDate");
const end = source.indexOf("function renderRequestLeadTimeNotice", start);
if (start < 0 || end < 0) throw new Error("requested date helper block not found");
const context = {Date, Intl, Object};
vm.runInNewContext(source.slice(start, end), context, {filename: "landing.js"});
const explicit = context.normalizeRequestedDate("01/12/2026");
if (explicit !== "2026-12-01") {
  throw new Error(`calendar date shifted in ${process.env.TZ}: ${explicit}`);
}
if (context.normalizeRequestedDate("2026-12-01") !== "2026-12-01") {
  throw new Error(`ISO calendar date shifted in ${process.env.TZ}`);
}
if (context.normalizeRequestedDate("any day") !== null) {
  throw new Error("flexible requested date must remain unset");
}
const fixedNow = new Date("2026-12-01T12:00:00Z");
if (context.hasShortLeadRequestedDate("2026-12-04", "11:59", fixedNow) !== true) {
  throw new Error(`sub-72-hour request not detected in ${process.env.TZ}`);
}
if (context.hasShortLeadRequestedDate("2026-12-04", "12:00", fixedNow) !== false) {
  throw new Error(`exact 72-hour request misclassified in ${process.env.TZ}`);
}
// Non-quarter-hour minutes must keep their exact Portugal local time.
for (const [date, time, expected, urgent] of [
  ["2026-12-02", "10:10", "2026-12-02T10:10:00.000Z", true],
  ["2026-12-10", "14:20", "2026-12-10T14:20:00.000Z", false],
  ["2026-12-10", "09:07", "2026-12-10T09:07:00.000Z", false],
  ["2027-07-10", "14:10", "2027-07-10T13:10:00.000Z", false]
]) {
  const instant = context.portugalLocalDateTimeToInstant(date, time);
  if (!instant || instant.toISOString() !== expected) {
    throw new Error(`Portugal local minute changed: ${date} ${time}`);
  }
  if (context.hasShortLeadRequestedDate(date, time, fixedNow) !== urgent) {
    throw new Error(`Wrong lead-time notice: ${date} ${time}`);
  }
}
console.log(`WEB_REQUEST_DATETIME_FRONTEND_OK ${process.env.TZ}`);
'''


def main() -> None:
    for timezone in ("Pacific/Kiritimati", "America/Adak"):
        environment = dict(os.environ)
        environment["TZ"] = timezone
        probe = subprocess.run(
            ["node", "-", str(JS_PATH)],
            input=NODE_PROBE,
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        assert probe.returncode == 0, probe.stderr
        assert f"WEB_REQUEST_DATETIME_FRONTEND_OK {timezone}" in probe.stdout

    print("WEB_REQUEST_DATETIME_FRONTEND_SMOKE_OK")


if __name__ == "__main__":
    main()
