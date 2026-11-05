# Telegram delivery reliability

## Transaction boundary

Offer distribution, expiry, declines, assignment failure/timeout, client offer
selection, assignment requests/final notifications, dispatcher retry/send and
carrier approval redispatch enqueue through the existing
`telegram_notification_outbox`. Business services do not send these messages.
Their caller commits business changes and notifications together; the existing
systemd Telegram dispatcher performs delivery after commit.

`send_job_offers_to_carriers` is a compatibility entry point whose return value
is now **queued count**, not confirmed delivery count. Dispatcher UI reflects
this distinction. Initial intake already used this outbox and remains compatible.

SQLite enqueue uses `INSERT ... ON CONFLICT DO NOTHING`, backed by the existing
unique dedupe-key index. A nested SQLite SAVEPOINT before a real outer BEGIN can
commit on release, so it is deliberately avoided for this operation. No schema
migration or historical-data rewrite is needed.

## Business rules

The common distribution guard runs before MATCHING, candidate selection and
offer creation. A passed requested time returns `requested_date_passed`.
Without accepted offers it moves the actively processed request to manual review;
accepted offers/history are preserved. Jobs are not bulk-scanned or relabelled.
Dispatcher retry and single-carrier send also reject a past requested time and
require the actual date to be updated through the existing request-update flow.
There is no implicit bypass or 72-hour ban. `None` dates retain their contract.

Use `app.domain.requested_date`: naive values mean UTC, as in intake, SQLite
loading and Telegram date handling. Web and Telegram local input is converted to
UTC. The comparison is strict `<`; an exactly equal instant is not in the past.

The sender also checks that a carrier offer is still pending, not expired, the
job is offered and its requested date has not passed. Obsolete queued offers
become terminal failed with `offer_no_longer_actionable`; job history is not
rewritten by the sender. `accepted` remains a carrier response, not automatic
client assignment; multiple accepted offers are allowed until client selection.

## Ownership and retries

Claim is a conditional atomic UPDATE with RETURNING. It checks pending/retry
status, attempt limit and due time, and increments attempts in the same write.
The claim commits before any external operation. Progress and final updates
check SENDING plus the claimed attempt number, preventing a stale worker from
finishing another attempt. Each step renews the sending lease.

States are pending, sending, retry, sent, failed and **uncertain**. Forbidden and
BadRequest errors are permanent. Malformed local payloads fail permanently.
Other errors have bounded retries (default five attempts), exponential backoff
and Telegram `retry_after` as a minimum when provided. One failed recipient or
persistence error does not stop the rest of a dispatch batch. Error text saved
to the DB is the exception class; diagnostic stacks contain frame locations,
not exception message bodies or recipient identifiers.

A sending claim interrupted past the stale threshold (default 300 seconds)
becomes uncertain. It is **not automatically sent again**. This trades automatic
redelivery of a possibly unsent message for avoiding an automatic duplicate after
an ambiguous crash. Failed and uncertain records require operational review;
never reset all of them to pending.

Useful read-only checks:

```sql
SELECT notification_type, delivery_status, count(*)
FROM telegram_notification_outbox GROUP BY 1, 2;

SELECT id, job_id, offer_id, delivery_status, attempt_count,
       last_attempt_at, next_attempt_at, last_error
FROM telegram_notification_outbox
WHERE delivery_status IN ('retry', 'failed', 'uncertain') ORDER BY id;
```

Success/failure logs include notification/job/offer/carrier identifiers and
attempt number, without chat identifiers, payload text, tokens or file IDs.
Scheduler completion events are logged even for zero work.

## Media and long text

The sender persists an immutable operation plan and a completed-step cursor in
the existing `payload_json` before delivery. Every successful media/text step is
checkpointed before proceeding. A known later failure resumes at the unfinished
step, preserving already delivered media. The final keyboard message is saved as
`carrier_message_id`; HTML and recipient locale are retained.

Single photo/video uses a caption when it fits. Longer descriptions use separate
text messages; albums are delivered in batches of up to ten with a single-item
tail preserved. Text is split at conservative UTF-16 limits (4096 for messages,
1024 for captions), counting decoded entities and balancing HTML tags across
chunks. Acceptance/decline buttons attach to the final text or single caption.
See the primary [Telegram Bot API reference](https://core.telegram.org/bots/api)
for message/caption limits, HTML and retry parameters.

## Remaining delivery uncertainty

Telegram sends and SQLite commits are not a shared transaction. A crash after
Telegram accepts a step but before its checkpoint leaves the outcome unknown;
the record is quarantined instead of blindly replayed. A network/response
timeout can also occur after Telegram accepted a request. Bounded network-error
retries may therefore still duplicate that individual ambiguous operation.
This implementation does not claim universal exactly-once delivery.

If the final keyboard message reached Telegram but persistence failed, its
reference can be missing in `job_offer`; reconcile the uncertain record before
any deliberate resend. Do not change the business dedupe key to force retries.

## Verification and rollout

Run `bash scripts/run_regression_suite.sh`. The suite supplies a temporary audit
schema and dummy bot token; live DB audit tools use a read-only connection and
can receive `CARGOPT_AUDIT_DB_PATH`. Regressions never require a real recipient.
The new regressions cover dates and every existing caller, transaction rollback,
client selection, permanent/temporary failures, concurrent claims/dispatchers,
restart, DB failures after send, media limits and partial progress.

Deploy only a tested commit after checking clean tracked files, live schema and
queue state. Pause the Telegram timer and allow a running dispatch to drain;
stop bot/API writers, create an online SQLite backup, verify integrity and a
restore into a separate temporary DB, then fast-forward code and restart the
services/timer. No migrations are part of this release.

For a rollback, pause delivery and business writers first. Keep the live DB and
all queue evidence. Audit pending/retry/sending/uncertain records and completed
multipart steps before selecting a compatible code version. Restoring an older
DB would lose newer business activity and cannot unsend Telegram messages; it is
not a generic rollback. Verify any proposed restore separately before using it.
