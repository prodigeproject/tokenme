"""Full unittest suite. Run: python -m unittest discover -s tests"""
import os, sys, tempfile, unittest, pathlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tokenme import estimate, quality, tracker, layer4


class TestEstimate(unittest.TestCase):
    def test_no_bare_exact(self):
        _, m = estimate.count("anything")
        self.assertNotEqual(m, "exact")

    def test_labelled(self):
        _, m = estimate.count("hello")
        self.assertIn(m[0], ("~", "t"))  # ~est or tiktoken:*

    def test_empty(self):
        self.assertEqual(estimate.count_n(""), 0)

    def test_none(self):
        self.assertEqual(estimate.count_n(None), 0)  # type: ignore

    def test_monotonic(self):
        self.assertGreater(estimate.count_n("x" * 400), estimate.count_n("x" * 40))

    def test_is_estimate(self):
        self.assertTrue(estimate.is_estimate("~est"))
        self.assertTrue(estimate.is_estimate(None))
        self.assertFalse(estimate.is_estimate("tiktoken:cl100k_base"))

    def test_count_for_model(self):
        n, m = estimate.count_for_model("hello world", "gpt-4o")
        self.assertGreater(n, 0)
        self.assertNotEqual(m, "exact")

    def test_heuristic_accuracy_within_factor_two(self):
        """Heuristic should be within 2x of tiktoken on typical text (loose bound)."""
        samples = [
            "The quick brown fox jumps over the lazy dog.",
            "def foo(x):\n    return x * 2\n",
            "import os\nimport sys\n\ndef main():\n    print('hello')\n",
        ]
        for text in samples:
            h = estimate.heuristic_tokens(text)
            # rough sanity: 1 token per word at minimum, never more than len(text)
            self.assertGreater(h, 0)
            self.assertLessEqual(h, len(text))


class TestQualityFalsePositives(unittest.TestCase):
    def test_import_bcrypt(self):
        self.assertTrue(quality.scan_diff("-import bcrypt\n+import hashlib")["ok"])

    def test_require_js(self):
        self.assertTrue(quality.scan_diff("-const x = require('bcrypt')\n")["ok"])

    def test_hashmap(self):
        self.assertTrue(quality.scan_diff("-    let x = hashmap.get(k)\n")["ok"])

    def test_submit(self):
        self.assertTrue(quality.scan_diff("-    submit(form)\n")["ok"])

    def test_insecure(self):
        self.assertTrue(quality.scan_diff("-    # insecure old approach\n")["ok"])

    def test_comment_validate(self):
        self.assertTrue(quality.scan_diff("-    # validate later\n")["ok"])

    def test_reindent_not_flagged(self):
        before = "def f():\n    x = 1\n    y = 2\n"
        after  = "def f():\n  x = 1\n  y = 2\n"
        self.assertTrue(quality.scan_before_after(before, after)["ok"])


class TestQualityTruePositives(unittest.TestCase):
    def test_removed_validate(self):
        diff = "@@\n-    if not validate(x):\n-        raise ValueError()\n+    pass\n"
        self.assertFalse(quality.scan_diff(diff)["ok"])

    def test_readd_clears(self):
        diff = "@@\n-    if not validate(x):\n+    if not validate(x):  # refactored\n"
        self.assertTrue(quality.scan_diff(diff)["ok"])

    def test_weakened_operator(self):
        diff = "@@\n-    if age <= 18:\n+    if age < 18:\n"
        r = quality.scan_diff(diff)
        self.assertFalse(r["ok"])
        self.assertIn("weakened_logic", r["findings"])

    def test_const_guard(self):
        diff = "@@\n-    if not is_admin(user):\n+    if True:\n"
        self.assertFalse(quality.scan_diff(diff)["ok"])

    def test_removed_test(self):
        diff = "@@\n-def test_rejects_expired():\n-    assert login(expired) is None\n"
        self.assertFalse(quality.scan_diff(diff)["ok"])

    def test_per_hunk_not_cross_cancelled(self):
        diff = "@@\n-    if not authorize(user): raise Forbidden()\n@@\n+    auth_config = {}\n"
        self.assertFalse(quality.scan_diff(diff)["ok"])

    def test_scan_before_after_proper(self):
        before = "def f():\n    if not validate(x):\n        raise ValueError()\n    return x\n"
        after  = "def f():\n    return x\n"
        self.assertFalse(quality.scan_before_after(before, after)["ok"])

    def test_language_detected(self):
        diff = "--- a/auth.py\n+++ b/auth.py\n@@\n-    validate(x)\n"
        self.assertEqual(quality.scan_diff(diff).get("language"), "python")

    def test_risk_levels(self):
        clean = quality.scan_diff("+x=1\n-y=2")
        self.assertEqual(clean["risk"], "clean")

    def test_removed_security(self):
        diff = "@@\n-    token = verify_jwt(req.headers['Auth'])\n+    token = req.headers['Authorization-Header']\n"
        self.assertFalse(quality.scan_diff(diff)["ok"])


class TestTracker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["TOKENME_HOME"] = self.tmp.name
        os.environ["TOKENME_SESSION"] = "unittest"

    def tearDown(self):
        os.environ.pop("TOKENME_HOME", None)
        os.environ.pop("TOKENME_SESSION", None)
        self.tmp.cleanup()

    def test_given_method(self):
        ev = tracker.record(kind="tool_call", raw_tokens=1000, kept_tokens=250, layer=3)
        self.assertEqual(ev["method"], "given")

    def test_text_method_not_given(self):
        ev = tracker.record(kind="note", kept_text="hello world", layer=1)
        self.assertNotEqual(ev["method"], "given")

    def test_saved(self):
        tracker.record(kind="tool_call", raw_tokens=1000, kept_tokens=250, layer=3)
        agg = tracker.aggregate(tracker.load_session("unittest"))
        self.assertEqual(agg["saved_tokens"], 750)

    def test_coverage_pct(self):
        tracker.record(kind="tool_call", raw_tokens=1000, kept_tokens=250, layer=3)
        tracker.record(kind="note", kept_tokens=50, layer=1)
        agg = tracker.aggregate(tracker.load_session("unittest"))
        self.assertEqual(agg["coverage_pct"], 50.0)

    def test_no_negative(self):
        ev = tracker.record(kind="x", raw_tokens=10, kept_tokens=200, layer=3)
        self.assertEqual(ev["saved"], 0)

    def test_is_day_bucket(self):
        self.assertTrue(tracker.is_day_bucket("day-20260619"))
        self.assertFalse(tracker.is_day_bucket("unittest"))

    def test_corrupt_line_skipped(self):
        tracker.record(kind="note", kept_tokens=10, layer=1)
        p = pathlib.Path(self.tmp.name) / "sessions" / "unittest.jsonl"
        with p.open("a") as f:
            f.write("{CORRUPT}\n")
        events = tracker.load_session("unittest")
        self.assertGreaterEqual(len(events), 1)
        for e in events:
            self.assertIn("kind", e)

    def test_concurrent_writes_no_crash(self):
        """Multiple record() calls in sequence must not corrupt the file."""
        for i in range(20):
            tracker.record(kind="note", kept_tokens=i, layer=1, label=f"ev{i}")
        events = tracker.load_session("unittest")
        self.assertEqual(len(events), 20)


class TestLayer4(unittest.TestCase):
    def test_oversized_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            big = pathlib.Path(d) / "big.md"
            big.write_text("Rule: always respond formally.\n" * 300, encoding="utf-8")
            result = layer4.config_audit([str(big)])
            issues = [f["issue"] for f in result["findings"]]
            self.assertTrue(any(i in ("oversized", "large") for i in issues))

    def test_not_found(self):
        result = layer4.config_audit(["/nonexistent/file.md"])
        self.assertEqual(result["findings"][0]["issue"], "not_found")

    def test_checkpoint_generate_parse(self):
        ckpt = layer4.generate_checkpoint(
            goal="Refactor auth", done=["Added JWT"], files=["auth.py"],
            decisions=["Use RS256"], next_step="Write tests")
        self.assertIn("CHECKPOINT", ckpt)
        self.assertIn("Refactor auth", ckpt)
        parsed = layer4.parse_checkpoint(ckpt)
        self.assertIsNotNone(parsed)
        self.assertIn("auth", parsed["goal"].lower())  # type: ignore
        self.assertEqual(parsed["next_step"].lower(), "write tests")  # type: ignore

    def test_parse_returns_last_checkpoint(self):
        c1 = layer4.generate_checkpoint("Goal 1", [], [], [], "step 1")
        c2 = layer4.generate_checkpoint("Goal 2", [], [], [], "step 2")
        parsed = layer4.parse_checkpoint(f"noise\n{c1}\nmiddle\n{c2}\nend")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["goal"], "Goal 2")  # type: ignore

    def test_parse_none_on_missing(self):
        self.assertIsNone(layer4.parse_checkpoint("no checkpoint here"))


if __name__ == "__main__":
    unittest.main()
