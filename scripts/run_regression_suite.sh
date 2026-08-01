#!/usr/bin/env bash
set -Eeuo pipefail

STRICT_WARNINGS=0

case "${1:-}" in
  "")
    ;;
  --strict-warnings)
    STRICT_WARNINGS=1
    ;;
  *)
    echo "usage: $0 [--strict-warnings]" >&2
    exit 2
    ;;
esac

ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
  pwd
)"

cd "$ROOT"

export PYTHONPATH="$ROOT"
export PYTHONDONTWRITEBYTECODE=1

if [ "$STRICT_WARNINGS" -eq 1 ]; then
  WARNING_FILTER="error::ResourceWarning,error::DeprecationWarning"
  echo "STRICT_WARNINGS=enabled"
else
  WARNING_FILTER="default"
  echo "STRICT_WARNINGS=disabled"
fi

TMP_ROOT="$(
  mktemp -d /tmp/cargopt_regression_XXXXXXXX
)"

trap 'rm -rf "$TMP_ROOT"' EXIT

TESTS=(
  scripts/bot_bootstrap_smoke.py
  scripts/dispatcher_access_role_smoke.py
  scripts/dispatcher_jobs_admin_smoke.py
  scripts/manual_offer_redispatch_smoke.py
  scripts/dispatcher_leads_admin_smoke.py
  scripts/landing_static_smoke.py
  scripts/landing_custom_validation_smoke.py
  scripts/landing_tracking_workspace_dependency_smoke.py
  scripts/job_tracking_page_static_smoke.py
  scripts/tracking_locale_parity_smoke.py
  scripts/tracking_return_copy_smoke.py
  scripts/job_tracking_workspace_v2_smoke.py
  scripts/job_tracking_progress_header_smoke.py
  scripts/job_tracking_state_cards_smoke.py
  scripts/job_tracking_request_card_surface_smoke.py
  scripts/job_tracking_inside_request_block_smoke.py
  scripts/job_tracking_no_offers_visual_state_smoke.py
  scripts/job_tracking_other_request_offer_badge_smoke.py
  scripts/job_tracking_mobile_other_requests_smoke.py
  scripts/job_tracking_cancelled_stage_smoke.py
  scripts/job_tracking_read_api_smoke.py
  scripts/job_tracking_assignment_actions_smoke.py
  scripts/job_tracking_offer_select_smoke.py
  scripts/job_tracking_token_storage_smoke.py
  scripts/legal_static_smoke.py
  scripts/legal_locale_parity_smoke.py
  scripts/locale_switcher_static_smoke.py
  scripts/guide_locale_contract_smoke.py
  scripts/guides_static_smoke.py
  scripts/guides_article_content_smoke.py
  scripts/guides_multilingual_registry_smoke.py
  scripts/corpus_multilingual_article_contract_smoke.py
  scripts/email_config_smoke.py
  scripts/email_template_locale_smoke.py
  scripts/email_smtp_transport_smoke.py
  scripts/email_notification_outbox_smoke.py
  scripts/email_dispatch_retry_smoke.py
  scripts/email_outbox_migration_smoke.py
  scripts/email_tracking_url_locale_smoke.py
  scripts/email_request_received_smoke.py
  scripts/email_duplicate_guard_smoke.py
  scripts/email_status_events_smoke.py
  scripts/web_request_api_smoke.py
  scripts/web_request_duplicate_guard_smoke.py
  scripts/web_intake_service_smoke.py
  scripts/job_matching_smoke.py
  scripts/job_matching_ignores_weight_volume_smoke.py
  scripts/carrier_search_smoke.py
  scripts/job_offer_smoke.py
  scripts/job_offer_acceptance_smoke.py
  scripts/job_offer_cleanup_smoke.py
  scripts/job_offer_decline_exhaustion_smoke.py
  scripts/job_offer_stale_acceptance_guard_smoke.py
  scripts/client_offer_selection_smoke.py
  scripts/client_offer_dedupe_smoke.py
  scripts/job_assignment_smoke.py
  scripts/job_assignment_confirmation_smoke.py
  scripts/assignment_timeout_smoke.py
  scripts/final_status_action_regression.py
  scripts/carrier_onboarding_service_smoke.py
  scripts/carrier_onboarding_fsm_smoke.py
  scripts/carrier_start_resume_smoke.py
  scripts/carrier_reinvite_reuse_smoke.py
  scripts/carrier_invite_links_smoke.py
  scripts/job_consistency_audit.py
)

RESULTS="$TMP_ROOT/results.tsv"
FAILURES="$TMP_ROOT/failures.log"
LOG_DIR="$TMP_ROOT/logs"

mkdir -p "$LOG_DIR"
: > "$FAILURES"

printf '%s\t%s\t%s\t%s\n' \
  "INDEX" "SCRIPT" "RESULT" "RC" \
  > "$RESULTS"

index=0

for script in "${TESTS[@]}"; do
  index=$((index + 1))

  test -f "$script"

  safe_name="$(
    printf '%s' "$script" |
    tr '/.' '__'
  )"

  log="$LOG_DIR/$(printf '%03d' "$index")_${safe_name}.log"
  isolated_tmp="$TMP_ROOT/tmp_$(printf '%03d' "$index")"

  mkdir -p "$isolated_tmp"

  echo
  echo "===== TEST $index/${#TESTS[@]} ====="
  echo "SCRIPT=$script"

  set +e

  env \
    PYTHONPATH="$ROOT" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONWARNINGS="$WARNING_FILTER" \
    TMPDIR="$isolated_tmp" \
    TEMP="$isolated_tmp" \
    TMP="$isolated_tmp" \
    timeout 180 \
    "$ROOT/.venv/bin/python" "$script" \
    > "$log" 2>&1

  rc=$?

  set -e

  cat "$log"

  if [ "$rc" -eq 0 ]; then
    result="PASS"
  elif [ "$rc" -eq 124 ]; then
    result="TIMEOUT"
  else
    result="FAIL"
  fi

  printf '%s\t%s\t%s\t%s\n' \
    "$index" "$script" "$result" "$rc" \
    >> "$RESULTS"

  if [ "$rc" -ne 0 ]; then
    {
      echo "===== $script ====="
      echo "RC=$rc"
      cat "$log"
      echo
    } >> "$FAILURES"
  fi

  echo "TEST_RESULT=$result"
done

echo
echo "===== REGRESSION SUMMARY ====="

column -t -s $'\t' "$RESULTS"

PASS_COUNT="$(
  awk -F '\t' '
    NR > 1 && $3 == "PASS" {count++}
    END {print count + 0}
  ' "$RESULTS"
)"

FAIL_COUNT="$(
  awk -F '\t' '
    NR > 1 && $3 != "PASS" {count++}
    END {print count + 0}
  ' "$RESULTS"
)"

echo "TEST_COUNT=${#TESTS[@]}"
echo "PASS_COUNT=$PASS_COUNT"
echo "FAIL_COUNT=$FAIL_COUNT"

if [ "$FAIL_COUNT" -ne 0 ]; then
  echo
  echo "===== FAILURES ====="
  cat "$FAILURES"
  exit 1
fi

test "$PASS_COUNT" -eq "${#TESTS[@]}"

echo "CARGOPT_REGRESSION_SUITE_OK"
