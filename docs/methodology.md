# Methodology

## Purpose

Section 404 of the Sarbanes-Oxley Act requires public companies to assess internal control over financial reporting (ICFR), and many require their auditors to attest to it. Automated financial controls and reports are only reliable if the IT general controls (ITGCs) over the systems that run them operate effectively. This tool performs the data-driven portion of a typical ITGC test of a financial application, covering every item in the population rather than a sample, and records the results in a worksheet an auditor can review.

## Control domains

The 13 controls follow the domains commonly used in ITGC testing under COSO 2013 (Principle 11, general controls over technology) and PCAOB AS 2201:

| Ref | Domain | Control | Test |
|---|---|---|---|
| APD-01 | Access to programs and data | New access approved before it is granted | Every account created in the period has an approved request dated on or before creation |
| APD-02 | | Leavers removed promptly | Every HR termination in the period is matched to accounts; flags accounts still active, disabled late, or used after termination |
| APD-03 | | Quarterly user access reviews | A review exists for every quarter ending in the period, was completed by its due date, and all issues found were remediated |
| APD-04 | | Privileged access restricted | Every active account with administrative privileges belongs to a named person in an authorized department |
| APD-05 | | Segregation of duties | No active user holds an incompatible pair of roles from the rule set |
| APD-06 | | No shared or generic accounts | No active account is generic |
| PC-01 | Program change | Changes approved before deployment | Every standard change has an approval dated on or before deployment |
| PC-02 | | Changes tested | Every change has evidence of testing |
| PC-03 | | Developers cannot deploy their own changes | Developer differs from the person who deployed |
| PC-04 | | Independent approval | Developer differs from the approver |
| PC-05 | | Emergency changes approved after the fact | Retroactive approval within the allowed number of days |
| CO-01 | Computer operations | Failed jobs followed up | Every failed backup or batch job in the period has a ticket |
| CO-02 | | Backups can be restored | At least one successful restore test of the financial system in the period |

Each control lists related NIST SP 800-53 Rev. 5 controls (for example AC-2, AC-5, AC-6, PS-4, CM-3, CM-5, CP-4, CP-9) for organizations that cross-walk ITGCs to a security framework.

## Results

For each control the worksheet records the population, the number of exceptions, the exception rate, and a result:

- **No exceptions:** every item in the population met the test.
- **Exceptions noted:** at least one item did not; each is listed with the reason.
- **No population:** nothing in the period was subject to the test (for example, no emergency changes).

Because the tool tests the full population, any exception is reported. Whether exceptions amount to a control deficiency, significant deficiency, or material weakness depends on compensating controls and potential financial statement impact, which require the auditor's judgment. The tool does not make that classification.

## Segregation of duties

The rule set in `src/sox_itgc/data/sod_rules.json` lists incompatible role pairs, each with the risk it creates (for example, maintaining vendors and approving payments). The matrix shows every role against every other: red cells give the number of active users holding an incompatible pair, green cells are incompatible pairs with no conflicts, and grey cells are compatible. Rename roles in the rule set to match your application.

## Parameters

Each engagement folder's `settings.json` sets the organization, system, audit period, the days allowed to remove leavers (default 3), the days allowed for emergency change approval (default 2), and the departments allowed to hold administrative privileges (default IT).

## Limitations

- Results depend on the completeness and accuracy of the exports. Auditors should obtain evidence that the populations are complete (for example, by tracing a few items from the system to the export).
- Design effectiveness, walkthroughs, and the review of evidence such as approval emails or test scripts remain manual steps.
- The tool does not express an opinion on ICFR.
