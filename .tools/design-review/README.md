# CargoPT Design Review v1.0

This directory defines the tracked contract for repeatable product and interface reviews of CargoPT. Generated evidence and reports are stored outside Git under `.audit/design-review-v1/<run-id>/`.

## Purpose

Design Review v1.0 combines automated browser evidence with two independent reviewers. It produces normalized, evidence-backed findings that can be deduplicated into an implementation backlog.

## Review categories

- User Flow — P0
- Form UX — P1
- Trust Layer — P2
- Visual Identity — P3
- Design System Consistency
- Accessibility
- Performance
- Mobile UX

P0-P3 are the strategic roadmap priorities. The remaining categories are cross-cutting quality dimensions and use `roadmap_priority: "NONE"` unless a specific finding blocks a roadmap layer.

## Evidence collectors

The initial contract recognizes the existing collectors:

- `release-audit` — broad read-only sitemap and viewport evidence.
- `tracking-status-matrix` — backend/frontend status coverage, action guards and permanent tracking smoke contracts without production access.
- `conversion-frontend-e2e` — production UI scenarios with mocked request submission and zero production writes.
- `fullstack-conversion-e2e` — isolated local API, database, bot and geocoding flow.
- `accessibility` — read-only Chromium checks for the accessibility tree, keyboard operation, focus indicators, ARIA references, reduced motion, contrast and 200% scaling.
- `lighthouse` — read-only Lighthouse performance reports for representative public pages in desktop and mobile modes.

## Safety policy

- Production review is read-only unless a collector explicitly mocks or isolates writes.
- No real customer request may be created by the design-review workflow.
- No real Telegram message may be sent by the design-review workflow.
- Full-stack scenarios must use an isolated temporary database and fake external integrations.
- Existing collector safety guards must not be bypassed by the future runner.
- Every run must preserve prior run output and record commit, environment, timestamps and exit codes.

## Reviewer independence

ChatGPT and Claude review the same evidence independently. Neither reviewer may see the other reviewer’s findings before normalization and deduplication. Findings without concrete evidence must be rejected or marked with low confidence.

## Finding contract

Each source finding must validate against `finding.schema.json`. Evidence should point to a reproducible artifact, URL, selector, viewport, log or screenshot. Recommendations must be specific enough to implement, and acceptance criteria must be testable.

## Planned reports

- `00-executive-summary.md`
- `01-full-audit.md`
- `02-prioritized-backlog.csv`
- `03-findings.json`
- `04-disagreements.md`
- `05-automated-checks.md`
- `06-page-scorecards.md`
- `07-run-manifest.json`

Runner implementation, reviewer prompts, normalization, deduplication and report generation are intentionally outside this contract-only change.
