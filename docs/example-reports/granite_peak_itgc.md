# ITGC testing worksheet: Granite Peak Manufacturing (fictional)

System: ERP (financial system) | Period 2026-01-01 to 2026-09-30 | Generated 2026-10-07 17:24 UTC

- Controls tested: **13 of 13**
- Controls with exceptions: **9** (21 exceptions in total)
- Segregation-of-duties conflicts: **4** across 4 user(s)

## Access to programs and data

| Control | Objective | Population | Exceptions | Result |
|---|---|---|---|---|
| APD-01 | New user access is approved before it is granted. | 4 | 2 | Exceptions noted |
| APD-02 | Access for terminated employees is removed promptly. | 4 | 2 | Exceptions noted |
| APD-03 | User access is reviewed by management every quarter. | 3 | 2 | Exceptions noted |
| APD-04 | Privileged access is restricted to appropriate personnel. | 4 | 2 | Exceptions noted |
| APD-05 | Users do not hold incompatible duties. | 21 | 4 | Exceptions noted |
| APD-06 | Shared and generic accounts are not used. | 21 | 1 | Exceptions noted |

## Program change

| Control | Objective | Population | Exceptions | Result |
|---|---|---|---|---|
| PC-01 | Changes are approved before they are deployed to production. | 24 | 2 | Exceptions noted |
| PC-02 | Changes are tested before deployment. | 26 | 0 | No exceptions |
| PC-03 | Developers cannot deploy their own changes to production. | 26 | 3 | Exceptions noted |
| PC-04 | Approvers are independent of the developer. | 26 | 0 | No exceptions |
| PC-05 | Emergency changes are approved after the fact within the allowed time. | 2 | 0 | No exceptions |

## Computer operations

| Control | Objective | Population | Exceptions | Result |
|---|---|---|---|---|
| CO-01 | Failed backup and batch jobs are followed up. | 6 | 3 | Exceptions noted |
| CO-02 | Backups can be restored. | 1 | 0 | No exceptions |

## Exceptions

- **APD-01** `ssato`: Created 2026-08-20 with no approved access request on file.
- **APD-01** `tyilmaz`: Access granted 2026-05-20, approved later on 2026-05-29.
- **APD-02** `ggrant`: Account still active (terminated 2026-05-08); signed in on 2026-05-19, after termination.
- **APD-02** `owhitaker`: Account disabled 19 days after termination on 2026-08-14 (allowed 3).
- **APD-03** `2026-Q2`: Completed 2026-08-21, 37 days after the 2026-07-15 due date.
- **APD-03** `2026-Q3`: 3 of 5 access issues found in the review were not remediated.
- **APD-04** `fbrennan`: Administrative privileges held by Fatima Brennan in Controller.
- **APD-04** `erpadmin`: Administrative privileges on a generic account.
- **APD-05** `aabbott`: Holds Vendor Maintenance + Payment Approval.
- **APD-05** `eunderhill`: Holds Journal Entry Create + Journal Entry Approve.
- **APD-05** `iquintero`: Holds Create Purchase Order + Receive Goods.
- **APD-05** `kcastro`: Holds User Administration + Payment Approval.
- **APD-06** `erpadmin`: Active generic account not assigned to an individual.
- **PC-01** `CHG-4103`: No approval recorded.
- **PC-01** `CHG-4107`: Deployed 2026-06-05, approved afterward on 2026-06-09.
- **PC-03** `CHG-4105`: Developed and deployed to production by svc_batch.
- **PC-03** `CHG-4112`: Developed and deployed to production by svc_batch.
- **PC-03** `CHG-4120`: Developed and deployed to production by svc_batch.
- **CO-01** `BKP-0702 2026-07-02`: Nightly ERP backup failed with no follow-up ticket.
- **CO-01** `BKP-0703 2026-07-03`: Nightly ERP backup failed with no follow-up ticket.
- **CO-01** `BKP-0910 2026-09-10`: Nightly ERP backup failed with no follow-up ticket.

## Segregation-of-duties conflicts

- **aabbott** (Accounts Payable): Vendor Maintenance + Payment Approval. A user could create a fictitious vendor and approve payments to it.
- **eunderhill** (General Ledger): Journal Entry Create + Journal Entry Approve. A user could record and approve their own journal entries.
- **iquintero** (Purchasing): Create Purchase Order + Receive Goods. A user could order and confirm receipt of goods that never arrived.
- **kcastro** (IT): User Administration + Payment Approval. A user could grant themselves any access and approve payments.

_This worksheet records automated tests of the data supplied. Exceptions are observations for the auditor to evaluate; classifying deficiencies (control deficiency, significant deficiency, or material weakness) requires professional judgment about compensating controls and financial statement impact. The tool does not express an opinion on internal control over financial reporting._
