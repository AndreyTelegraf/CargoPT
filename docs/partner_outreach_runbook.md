# CargoPT partner outreach MVP

## Purpose

Send a small number of relevant partnership proposals to Lisbon Metropolitan
Area companies whose customers are likely to need moving or transport help.
The first version is intentionally a reviewed B2B workflow, not a bulk-mail
system.

## Pilot audiences

Use this order:

1. relocation services;
2. real-estate agencies serving international customers;
3. property-management companies;
4. coliving and student housing;
5. interior/renovation firms;
6. cleaning companies focused on move-in or move-out work.

The importer accepts only the 18 municipalities in the Lisbon Metropolitan
Area and one public role mailbox per company domain.

## Non-negotiable safeguards

- `PARTNER_OUTREACH_ENABLED` and `PARTNER_OUTREACH_SEND_ENABLED` default to
  false and are independent of normal customer email notifications.
- Only public role mailboxes on the company's own website domain are accepted.
  Named-person mailboxes and consumer mailbox providers are rejected.
- Every source URL and source-check timestamp are stored.
- Contact-source checks older than 90 days block delivery.
- One initial message per company. The MVP has no automatic follow-up.
- Every draft must be approved by a named reviewer.
- The dispatcher requires a current DGC legal-entity opposition-list snapshot.
- Internal opt-outs suppress both the mailbox and the company domain.
- Sending is limited to Lisbon business days, 09:30-17:30, one message per
  dispatcher run, at least 20 minutes apart, and five per day by default.
- The message identifies CargoPT, states that it is a commercial partnership
  proposal, explains the source of the address, and offers a free reply-based
  opt-out.
- Live mode requires a working `EMAIL_REPLY_TO` mailbox and the full sender
  identity in `PARTNER_OUTREACH_LEGAL_IDENTITY`; both appear in the message or
  its reply path.
- No tracking pixel is included. Links contain only campaign and prospect IDs.

These are technical controls, not a substitute for legal review. Before live
use, obtain the current national legal-entity opposition list from the
Direcao-Geral do Consumidor and confirm the operating procedure with Portuguese
counsel or the responsible compliance adviser.

## Data preparation

Start from `resources/partner_outreach/prospects_sample.csv`. Required fields:

- `company_name`
- `website_url`
- `contact_email`
- `category`
- `municipality`
- `language` (`pt`, `en`, or `ru`)
- `source_url`
- `source_checked_at` (ISO-8601)

`legal_entity_name` and `nif` should be supplied whenever they are publicly
available because they improve DGC suppression matching. `qualification_note`
must briefly explain why the company's customers are likely to need CargoPT.

Validate without writing:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.import_partner_prospects prospects.csv
```

Import only after the review:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.import_partner_prospects prospects.csv --apply
```

## DGC and internal suppressions

Normalize the current DGC list into a CSV with `kind,value,reason`. Prefer NIF;
otherwise use the exact legal-entity name. Validate first, then import with the
date on which the official source was checked:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.import_partner_suppressions dgc.csv \
  --source dgc_legal_entities --checked-at 2026-08-13

PYTHONPATH=. ./.venv/bin/python -m scripts.import_partner_suppressions dgc.csv \
  --source dgc_legal_entities --checked-at 2026-08-13 --apply
```

The dispatcher refuses to send when this snapshot is missing or older than the
configured maximum age (35 days by default).

## Review and approval

List current records:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.manage_partner_outreach list
```

Generate and print drafts for human review:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.manage_partner_outreach draft \
  --prospect-ids 1,2,3
```

Approve selected messages only:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.manage_partner_outreach approve \
  --message-ids 1,3 --actor andrey
```

Record an opt-out immediately:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.manage_partner_outreach suppress \
  --prospect-id 3 --reason "reply opt-out 2026-08-13"
```

## Dispatch

The default command is a dry run and never sends:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.dispatch_partner_outreach
```

Live delivery additionally requires `PARTNER_OUTREACH_SEND_ENABLED=true` and an
explicit `--send` argument:

```bash
PYTHONPATH=. ./.venv/bin/python -m scripts.dispatch_partner_outreach --send
```

For the pilot, install `deploy/systemd/cargopt_partner_outreach.service` and
`deploy/systemd/cargopt_partner_outreach.timer`. The timer checks every 20
minutes on Lisbon business days, while all database and feature-flag guards
remain active. Run five approved companies first, inspect delivery and replies
for three business days, then decide whether to expand to 20.

## Pilot success criteria

- zero messages to personal mailboxes;
- zero sends to DGC or internal suppression entries;
- zero duplicates and no unapproved sends;
- bounce rate below 5 percent;
- at least two positive replies or partner-guide inclusions from the first 20;
- every opt-out recorded on the same business day.
