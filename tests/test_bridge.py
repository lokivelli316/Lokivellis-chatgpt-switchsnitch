import hashlib,json,unittest
from pathlib import Path

class ContractTests(unittest.TestCase):
    def test_manifest_contract(self):
        m=json.loads(Path("extension/manifest.json").read_text())
        self.assertEqual(m["manifest_version"],3)
        self.assertIn("https://chatgpt.com/*",m["host_permissions"])
        self.assertIn("http://127.0.0.1/*",m["host_permissions"])
    def test_no_prompt_capture(self):
        src=Path("extension/content.js").read_text()
        self.assertNotIn("textarea.value",src); self.assertNotIn("innerHTML",src)
    def test_loopback_only(self):
        src=Path("termux/bridge.py").read_text()
        self.assertIn('("127.0.0.1",p)',src)
    def test_accept_does_not_set_expected(self):
        src=Path("extension/content.js").read_text()
        self.assertNotIn('chrome.storage.local.set({expected:d.target})',src)
    def test_shell_boundary_uses_opaque_id(self):
        src=Path("termux/bridge.py").read_text()
        self.assertIn("RESTORE {mid}",src); self.assertNotIn("RESTORE '{expected}'",src)
    def test_unverified_is_not_restore_capable(self):
        src=Path("termux/bridge.py").read_text()
        self.assertIn('d.get("type")=="OBSERVED_MODEL_UNVERIFIED"',src)
    def test_spec_hash_is_frozen(self):
        lock=json.loads(Path("SPEC_LOCK.json").read_text())
        actual=hashlib.sha256(Path(lock["artifact"]).read_bytes()).hexdigest()
        self.assertEqual(actual,lock["spec_sha256"])
        self.assertEqual(lock["status"],"FROZEN")
    def test_four_gates_exist_and_unverified(self):
        g=json.loads(Path("GATES.json").read_text())
        self.assertEqual(len(g["gates"]),4)
        self.assertTrue(all(x["status"]=="UNVERIFIED" for x in g["gates"]))
        self.assertEqual(g["status"],"HOLD")
    def test_hotkey_contract_documented(self):
        spec=Path("SWITCHSNITCH_SECURITY_STATE_MACHINE_SPEC_v1.0.0.md").read_text()
        self.assertIn("FLAG_NOT_FOCUSABLE",spec)
        self.assertIn("SO_PEERCRED is UNVERIFIED",spec)

if __name__=="__main__":unittest.main()
