# Input reference

An engagement is a folder containing `settings.json` and seven CSV files. Start from `samples/template/`. Column names are not case-sensitive, and dates use the format `YYYY-MM-DD`.

## settings.json

| Field | Example |
|---|---|
| `organization` | `"Granite Peak Manufacturing"` |
| `system` | `"ERP (financial system)"` |
| `period_start`, `period_end` | `"2026-01-01"`, `"2026-09-30"` |
| `termination_removal_days` | `3` |
| `emergency_approval_days` | `2` |
| `privileged_departments` | `["IT"]` |

## users.csv: application user listing

Required: `user`, `employee_id`, `department`, `status` (`active` or `disabled`), `account_type` (`individual`, `service`, or `generic`), `created_date`.
Optional: `name`, `privileged` (`true`/`false`), `disabled_date`, `last_login`, `access_request_id`, `access_request_approved_date`.

## user_roles.csv

`user`, `role`: one row per role assignment. Role names must match the rule set in `src/sox_itgc/data/sod_rules.json`.

## hr_terminations.csv

`employee_id`, `termination_date`, optional `name`: from the HR system for the audit period.

## access_reviews.csv

`quarter` (for example `2026-Q1`), `due_date`, optional `completed_date`, `reviewer`, `exceptions_found`, `exceptions_remediated`.

## changes.csv: production change log

`change_id`, `type` (`standard` or `emergency`), `developer`, `deployed_by`, `deployed_date`, optional `description`, `approver`, `approved_date`, `tested` (`true`/`false`).

## jobs.csv: backup and batch job history

`job_id`, `run_date`, `status` (`success` or `failed`), optional `job_name`, `ticket_id`.

## restore_tests.csv

`test_date`, `result` (`success` or `failed`), optional `system`.

These files contain user and access details. Store them and the worksheets as audit evidence under your organization's retention and confidentiality rules.
