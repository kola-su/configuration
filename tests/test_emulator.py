import os
import unittest
from pathlib import Path

import emulator

ROOT = Path(__file__).resolve().parents[1]


class ShellTest(unittest.TestCase):
    def test_quotes_and_env(self):
        shell = emulator.Shell()
        os.environ["EMUL_DEMO"] = "a b"
        args = shell.parse('ls "$EMUL_DEMO"')
        self.assertEqual(args, ["ls", "a b"])
        args = shell.parse("ls '$EMUL_DEMO'")
        self.assertEqual(args, ["ls", "$EMUL_DEMO"])

    def test_commands_on_deep_vfs(self):
        root, note = emulator.load_vfs(ROOT / "vfs" / "deep.json")
        self.assertIn("узлов=", note)
        shell = emulator.Shell(root)
        self.assertIn("home", shell.execute("ls"))
        self.assertNotIn(".hidden", shell.execute("ls"))
        self.assertIn(".hidden", shell.execute("ls -a"))
        self.assertEqual(shell.execute("cd /home/user"), "")
        self.assertTrue(shell.prompt().endswith(":/home/user$ "))
        self.assertIn("projects", shell.execute("tree -L 1"))
        self.assertRegex(shell.execute("date +%Y"), r"^\d{4}$")
        before = (ROOT / "vfs" / "deep.json").read_bytes()
        self.assertEqual(shell.execute("touch /tmp/a.txt"), "")
        self.assertEqual(shell.execute("cp -r /home /tmp/home_copy"), "")
        self.assertIn("photo.bin", shell.execute("ls /tmp/home_copy/user"))
        self.assertEqual((ROOT / "vfs" / "deep.json").read_bytes(), before)

    def test_errors(self):
        shell = emulator.Shell()
        self.assertIn("неизвестная команда", shell.execute("foo"))
        self.assertIn("незакрытые кавычки", shell.execute('ls "abc'))
        self.assertIn("не принимает", shell.execute("exit 1"))
        self.assertTrue(shell.running)
        shell.execute("exit")
        self.assertFalse(shell.running)


if __name__ == "__main__":
    unittest.main()
