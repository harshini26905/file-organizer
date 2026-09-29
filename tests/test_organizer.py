import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import organizer  # noqa: E402


def touch(p: Path, text="x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_org(self, *args):
        return organizer.main([str(a) for a in args])

    def test_sorts_by_type_case_insensitive(self):
        for n in ["a.JPG", "b.pdf", "c.zip", "d.mp3", "e.mp4", "f.unknown"]:
            touch(self.root / n)
        self.assertEqual(self.run_org(self.root), 0)
        self.assertTrue((self.root / "Images" / "a.JPG").exists())
        self.assertTrue((self.root / "Documents" / "b.pdf").exists())
        self.assertTrue((self.root / "Archives" / "c.zip").exists())
        self.assertTrue((self.root / "Audio" / "d.mp3").exists())
        self.assertTrue((self.root / "Video" / "e.mp4").exists())
        self.assertTrue((self.root / "Others" / "f.unknown").exists())

    def test_never_overwrites_and_numbers_deterministically(self):
        touch(self.root / "Documents" / "r.pdf", "ORIGINAL")
        touch(self.root / "Documents" / "r (1).pdf", "ORIGINAL1")
        touch(self.root / "r.pdf", "NEW")
        self.run_org(self.root)
        self.assertEqual((self.root / "Documents" / "r.pdf").read_text(), "ORIGINAL")
        self.assertEqual((self.root / "Documents" / "r (1).pdf").read_text(), "ORIGINAL1")
        self.assertEqual((self.root / "Documents" / "r (2).pdf").read_text(), "NEW")

    def test_same_name_from_two_sources_in_one_run(self):
        touch(self.root / "a.jpg", "top")
        touch(self.root / "sub" / "a.jpg", "sub")
        self.run_org(self.root, "--recursive")
        got = sorted(p.name for p in (self.root / "Images").iterdir())
        self.assertEqual(got, ["a (1).jpg", "a.jpg"])

    def test_dry_run_changes_nothing_and_matches_live(self):
        touch(self.root / "Documents" / "r.pdf", "ORIGINAL")
        touch(self.root / "r.pdf")
        touch(self.root / "x.png")
        before = sorted(str(p) for p in self.root.rglob("*"))
        cats, fb = organizer.load_categories(None)
        planned = organizer.plan_moves(self.root, self.root, cats, fb)
        self.run_org(self.root, "--dry-run")
        self.assertEqual(before, sorted(str(p) for p in self.root.rglob("*")))
        self.run_org(self.root)
        for m in planned:
            self.assertTrue(m.dst.exists(), m.dst)

    def test_separate_target_directory(self):
        src, tgt = self.root / "src", self.root / "out"
        touch(src / "a.png")
        self.run_org(src, "--target", tgt)
        self.assertTrue((tgt / "Images" / "a.png").exists())
        self.assertFalse((src / "a.png").exists())

    def test_idempotent(self):
        touch(self.root / "a.png")
        self.run_org(self.root)
        self.run_org(self.root, "--recursive")
        self.assertEqual([p.name for p in (self.root / "Images").iterdir()], ["a.png"])

    def test_custom_config_and_log_file(self):
        cfg = self.root / "cfg.json"
        cfg.write_text('{"fallback":"Misc","categories":{"Books":[".epub"]}}')
        src = self.root / "s"
        touch(src / "b.epub")
        touch(src / "c.png")
        logf = self.root / "run.log"
        self.run_org(src, "--config", cfg, "--log", logf)
        self.assertTrue((src / "Books" / "b.epub").exists())
        self.assertTrue((src / "Misc" / "c.png").exists())
        self.assertIn("MOVE", logf.read_text())

    def test_bad_source_returns_error(self):
        self.assertEqual(self.run_org(self.root / "missing"), 2)


if __name__ == "__main__":
    unittest.main()
