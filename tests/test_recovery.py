import importlib.util, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location("bridge_under_test",Path("termux/bridge.py"))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class RetryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  b.ROOT=Path(self.tmp.name);b.TOKEN=b.ROOT/"token";b.RECEIPTS=b.ROOT/"receipts.jsonl"
  b.pending.clear();b.issued.clear();b.suppressions.clear()
  self.event=dict(surface_id="s",chat_id="c",expected_at_event="GPT-5.6 Sol",selected_at_event="GPT-6.2",observed_at_event="UNVERIFIED")
 def tearDown(self): self.tmp.cleanup()
 def test_duplicate_does_not_supersede_pending(self):
  with patch.object(b.threading.Thread,"start"):
   a=b.create_mismatch(self.event);c=b.create_mismatch(self.event)
  self.assertEqual(a["mismatch_id"],c["mismatch_id"])
 def test_failed_notification_can_retry(self):
  with patch.object(b.threading.Thread,"start"):
   a=b.create_mismatch(self.event);a["state"]="NOTIFICATION_FAILED";c=b.create_mismatch(self.event)
  self.assertNotEqual(a["mismatch_id"],c["mismatch_id"])
 def test_terminal_decision_never_issues(self):
  with patch.object(b.threading.Thread,"start"): a=b.create_mismatch(self.event)
  a["state"]="ACCEPTED";a["actionable"]=True;b.issued[a["mismatch_id"]]="RESTORE"
  self.assertEqual(b.issue("s","c","GPT-5.6 Sol")["action"],"NOOP")
 def test_decision_cannot_be_changed_after_issue(self):
  with patch.object(b.threading.Thread,"start"): a=b.create_mismatch(self.event)
  a["state"]="DECISION_PENDING";a["actionable"]=True
  self.assertTrue(b.operator_decision("RESTORE",a["mismatch_id"])["ok"])
  self.assertFalse(b.operator_decision("ACCEPT",a["mismatch_id"])["ok"])
if __name__=="__main__":unittest.main()
