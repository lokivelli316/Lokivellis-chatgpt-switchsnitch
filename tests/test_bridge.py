import importlib.util, json, tempfile, unittest
from pathlib import Path

class ContractTests(unittest.TestCase):
    def test_manifest_contract(self):
        m=json.loads(Path("extension/manifest.json").read_text())
        self.assertEqual(m["manifest_version"],3)
        self.assertIn("https://chatgpt.com/*",m["host_permissions"])
    def test_no_prompt_capture(self):
        src=Path("extension/content.js").read_text()
        self.assertNotIn("textarea.value",src)
        self.assertNotIn("innerHTML",src)
    def test_loopback_only(self):
        src=Path("termux/bridge.py").read_text()
        self.assertIn('("127.0.0.1",8765)',src)

if __name__=="__main__": unittest.main()
