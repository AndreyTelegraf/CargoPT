# Meta Operations Console

The console is a human-in-the-loop lead radar for posts and comments that may
contain a request for a carrier. It is dormant until explicitly enabled.

## MVP flow

1. Facebook sends a notification email for a monitored group.
2. The mailbox adapter forwards raw RFC822 or JSON to
   `POST /api/v1/meta-operations/inbound/email`.
3. The endpoint verifies `X-CargoPT-Inbound-Token`, strips attachments, stores
   only useful text and metadata, deduplicates the event, matches the group and
   classifies the request.
4. Target and review events above the configured threshold are sent to the
   configured Telegram recipients.
5. An operator marks the event as target, noise or handled in Telegram or at
   `/meta-operations`.

The system never logs in to Facebook, stores a Facebook password, publishes to
third-party groups or bypasses group rules.

## Configuration

All settings are off or empty by default:

- `META_OPERATIONS_ENABLED`
- `META_OPERATIONS_INBOUND_TOKEN`
- `META_OPERATIONS_ADMIN_USERNAME`
- `META_OPERATIONS_ADMIN_PASSWORD`
- `META_OPERATIONS_TELEGRAM_CHAT_IDS`
- `META_OPERATIONS_ALERT_THRESHOLD`

The inbound token and admin password are random secrets stored only in the
server environment. Telegram recipients are comma-separated numeric chat IDs.

## Group registry

`resources/meta_operations/groups_seed.json` is a normalized snapshot of the
source workbook. Only canonical Facebook group URLs are included. Every new
group starts with `enabled=false`, and repeat imports preserve operator changes.
Rejected invitation, share and missing links are kept for review in
`resources/meta_operations/groups_rejected_report.json`.

Preview the import:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.import_meta_operations_groups
```

Apply after the database migration:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.import_meta_operations_groups --apply
```

## Inbound formats

Raw email uses `Content-Type: message/rfc822` and the
`X-CargoPT-Inbound-Token` header. A JSON adapter may send:

```json
{
  "message_id": "provider-message-id",
  "sender": "notification@facebookmail.com",
  "subject": "New post in a monitored group",
  "text": "Procuro uma transportadora...",
  "source_url": "https://www.facebook.com/groups/.../posts/..."
}
```

## Activation checklist

1. Back up the production database and apply the migration.
2. Import the group seed; verify all groups remain disabled.
3. Add the environment settings and restart API and bot.
4. Enable only the pilot groups confirmed by Olga.
5. Configure mail forwarding and send one synthetic test.
6. Add Olga's Telegram chat ID and perform one alert test with her consent.
7. Measure false positives and notification coverage for seven days.
