#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

export PYTHONPATH="$ROOT"
export PYTHONDONTWRITEBYTECODE=1
export BOT_TOKEN="${BOT_TOKEN:-123456:TESTTOKEN}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///data/cargopt_dev.db}"

"$PYTHON_BIN" -m compileall -q app scripts

TESTS=(
  scripts/backup_sqlite_smoke.py
  scripts/rate_limit_smoke.py
  scripts/web_request_contact_rate_limit_smoke.py
  scripts/stale_draft_archive_smoke.py
  scripts/requested_date_validation_smoke.py
  scripts/job_requested_datetime_handler_smoke.py
  scripts/request_draft_service_smoke.py
  scripts/carrier_approval_targeted_redispatch_smoke.py
  scripts/manual_offer_redispatch_smoke.py
  scripts/job_control_routing_smoke.py
  scripts/job_completion_smoke.py
  scripts/job_lifecycle_notifications_smoke.py
  scripts/email_template_locale_smoke.py
  scripts/email_status_events_smoke.py
  scripts/web_request_duplicate_guard_smoke.py
  scripts/web_intake_service_smoke.py
  scripts/job_tracking_workspace_v2_smoke.py
)

for test_script in "${TESTS[@]}"; do
  echo "RUN=$test_script"
  "$PYTHON_BIN" "$test_script"
done

echo "CARGOPT_CRITICAL_SUITE_OK"
