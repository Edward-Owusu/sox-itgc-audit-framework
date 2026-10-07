import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sox_itgc import load_engagement, parse_engagement, test_controls as run_tests  # noqa: E402
from sox_itgc.cli import main  # noqa: E402
from sox_itgc.engine import EXCEPTIONS, NO_EXCEPTIONS, NOT_TESTED, DataError, _quarters  # noqa: E402
from sox_itgc.reporting import WRITERS  # noqa: E402

S = ROOT / "samples"
SETTINGS = {"organization": "T", "system": "ERP", "period_start": "2026-01-01", "period_end": "2026-06-30"}
BASE = {
    "users": "user,name,employee_id,department,status,account_type,privileged,created_date,disabled_date,last_login,"
             "access_request_id,access_request_approved_date\n"
             "alice,Alice A,E1,Accounts Payable,active,individual,false,2024-01-10,,2026-06-20,AR1,2024-01-08\n"
             "bob,Bob B,E2,IT,active,individual,true,2024-01-10,,2026-06-20,AR2,2024-01-08\n",
    "user_roles": "user,role\nalice,Vendor Maintenance\nbob,User Administration\n",
    "hr_terminations": "employee_id,name,termination_date\n",
    "access_reviews": "quarter,due_date,completed_date,exceptions_found,exceptions_remediated\n"
                      "2026-Q1,2026-04-15,2026-04-10,1,1\n2026-Q2,2026-07-15,2026-07-10,0,0\n",
    "changes": "change_id,type,developer,approver,approved_date,tested,deployed_by,deployed_date\n"
               "C1,standard,dev,ctl,2026-02-01,true,bob,2026-02-03\n",
    "jobs": "job_id,job_name,run_date,status,ticket_id\nJ1,Backup,2026-03-01,success,\n",
    "restore_tests": "test_date,system,result\n2026-05-01,ERP,success\n",
}


def run(**overrides):
    texts = dict(BASE)
    texts.update(overrides)
    return run_tests(parse_engagement(texts, SETTINGS))


def result(r, cid):
    return next(c for c in r.controls if c.id == cid)


class TestParsing(unittest.TestCase):
    def test_rejects_bad_input(self):
        with self.assertRaisesRegex(DataError, "Missing input"):
            parse_engagement({"users": BASE["users"]}, SETTINGS)
        with self.assertRaisesRegex(DataError, "missing required column"):
            run(changes="change_id\nC1\n")
        with self.assertRaisesRegex(DataError, "standard or emergency"):
            run(changes=BASE["changes"].replace("standard", "urgent"))
        with self.assertRaisesRegex(DataError, "2026-03-31"):
            run(jobs="job_id,run_date,status\nJ1,03/01/2026,success\n")

    def test_quarters_in_period(self):
        self.assertEqual(_quarters(*[__import__("datetime").date.fromisoformat(d) for d in ("2026-01-01", "2026-09-30")]),
                         ["2026-Q1", "2026-Q2", "2026-Q3"])


class TestControls(unittest.TestCase):
    def test_clean_baseline(self):
        r = run()
        self.assertFalse(any(c.result == EXCEPTIONS for c in r.controls))
        self.assertEqual(result(r, "PC-05").result, NOT_TESTED)  # no emergency changes
        self.assertEqual(result(r, "APD-03").result, NO_EXCEPTIONS)

    def test_terminated_user_still_active_and_used(self):
        r = run(hr_terminations="employee_id,name,termination_date\nE1,Alice A,2026-03-01\n")
        ex = result(r, "APD-02").exceptions
        self.assertEqual(len(ex), 1)
        self.assertIn("still active", ex[0].detail)
        self.assertIn("after termination", ex[0].detail)

    def test_late_removal(self):
        users = BASE["users"].replace("E1,Accounts Payable,active,individual,false,2024-01-10,,2026-06-20",
                                      "E1,Accounts Payable,disabled,individual,false,2024-01-10,2026-03-20,2026-02-27")
        r = run(users=users, hr_terminations="employee_id,termination_date\nE1,2026-03-01\n")
        self.assertIn("19 days", result(r, "APD-02").exceptions[0].detail)

    def test_new_user_without_approval(self):
        users = BASE["users"] + "carl,Carl C,E3,Finance,active,individual,false,2026-02-10,,2026-06-01,,\n"
        self.assertEqual([x.item for x in result(run(users=users), "APD-01").exceptions], ["carl"])

    def test_access_review_late_and_unremediated(self):
        r = run(access_reviews="quarter,due_date,completed_date,exceptions_found,exceptions_remediated\n"
                               "2026-Q1,2026-04-15,2026-05-20,3,1\n")
        items = [x.item for x in result(r, "APD-03").exceptions]
        self.assertEqual(items.count("2026-Q1"), 2)
        self.assertIn("2026-Q2", items)  # missing review

    def test_privileged_and_generic_accounts(self):
        users = BASE["users"] + "admin,,,IT,active,generic,true,2021-01-01,,2026-06-01,,\n"
        users = users.replace("Accounts Payable,active,individual,false", "Accounts Payable,active,individual,true")
        r = run(users=users)
        self.assertEqual(sorted(x.item for x in result(r, "APD-04").exceptions), ["admin", "alice"])
        self.assertEqual([x.item for x in result(r, "APD-06").exceptions], ["admin"])

    def test_segregation_of_duties(self):
        r = run(user_roles=BASE["user_roles"] + "alice,Payment Approval\n")
        self.assertEqual([x["user"] for x in r.sod_conflicts], ["alice"])
        self.assertEqual(r.sod_matrix["Vendor Maintenance"]["Payment Approval"], ["alice"])
        self.assertEqual(r.sod_matrix["Payment Approval"]["Vendor Maintenance"], ["alice"])

    def test_change_management(self):
        changes = ("change_id,type,developer,approver,approved_date,tested,deployed_by,deployed_date\n"
                   "C1,standard,dev,ctl,2026-02-05,true,bob,2026-02-03\n"   # approved after deploy
                   "C2,standard,dev,dev,2026-02-01,false,dev,2026-02-03\n"  # self-approved, untested, self-deployed
                   "C3,emergency,dev,ctl,2026-03-10,true,bob,2026-03-01\n")  # late emergency approval
        r = run(changes=changes)
        self.assertEqual([x.item for x in result(r, "PC-01").exceptions], ["C1"])
        self.assertEqual([x.item for x in result(r, "PC-02").exceptions], ["C2"])
        self.assertEqual([x.item for x in result(r, "PC-03").exceptions], ["C2"])
        self.assertEqual([x.item for x in result(r, "PC-04").exceptions], ["C2"])
        self.assertEqual([x.item for x in result(r, "PC-05").exceptions], ["C3"])

    def test_operations(self):
        r = run(jobs="job_id,job_name,run_date,status,ticket_id\nJ1,Backup,2026-03-01,failed,\nJ2,Backup,2026-03-02,failed,INC1\n",
                restore_tests="test_date,system,result\n2025-12-01,ERP,success\n")
        self.assertEqual(len(result(r, "CO-01").exceptions), 1)
        self.assertEqual(result(r, "CO-02").result, EXCEPTIONS)


class TestSamplesAndOutput(unittest.TestCase):
    def test_samples(self):
        weak = run_tests(load_engagement(S / "granite_peak"))
        strong = run_tests(load_engagement(S / "bluewater"))
        self.assertGreaterEqual(weak.counts()["with_exceptions"], 5)
        self.assertGreaterEqual(weak.counts()["sod_conflicts"], 1)
        self.assertEqual(strong.counts()["exceptions"], 0)

    def test_writers_and_escaping(self):
        r = run_tests(parse_engagement(BASE, dict(SETTINGS, organization="<script>x</script>")))
        for fmt, w in WRITERS.items():
            self.assertTrue(w(r).strip(), fmt)
        self.assertNotIn("<script>x</script>", WRITERS["html"](r))
        json.loads(WRITERS["json"](r))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main([str(S / "granite_peak"), "--out", tmp, "--fail-on-deficiency"]), 2)
            self.assertEqual(main([str(S / "bluewater"), "--out", tmp, "--fail-on-deficiency"]), 0)
            self.assertEqual(main([str(Path(tmp) / "missing"), "--out", tmp]), 1)


if __name__ == "__main__":
    unittest.main()
