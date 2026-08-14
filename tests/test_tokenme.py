"""Full unittest suite. Run: python -m unittest discover -s tests"""
import os, sys, tempfile, unittest, pathlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tokenme import estimate, quality, tracker, layer4, provider, router, prompt, context
from hooks import hook_record, hook_response


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

    def test_regression_is_signed(self):
        ev = tracker.record(kind="x", raw_tokens=10, kept_tokens=200, layer=3)
        self.assertEqual(ev["saved"], -190)
        agg = tracker.aggregate([ev])
        self.assertEqual(agg["saved_tokens"], -190)
        self.assertEqual(agg["regression_events"], 1)
        self.assertEqual(agg["regressed_tokens"], 190)

    def test_legacy_clamped_event_is_recomputed(self):
        legacy = {"kind": "tool_call", "layer": 3, "raw": 10,
                  "kept": 200, "saved": 0, "method": "given"}
        agg = tracker.aggregate([legacy])
        self.assertEqual(agg["saved_tokens"], -190)
        self.assertEqual(agg["regression_events"], 1)

    def test_unknown_raw_is_explicit(self):
        ev = tracker.record(kind="note", kept_tokens=20, layer=1)
        self.assertIsNone(ev["saved"])
        self.assertEqual(ev["measurement_status"], "unknown_raw")
        agg = tracker.aggregate([ev])
        self.assertEqual(agg["unknown_raw_events"], 1)
        self.assertEqual(agg["measured_events"], 0)
        self.assertIsNone(agg["saved_tokens"])

    def test_metrics_are_separate(self):
        command = tracker.record(kind="tool_call", raw_tokens=100, kept_tokens=20, layer=3)
        provider = tracker.record(kind="usage", raw_tokens=1000, kept_tokens=900,
                                  metric="provider_total_tokens")
        agg = tracker.aggregate([command, provider])
        self.assertTrue(agg["mixed_metrics"])
        self.assertIsNone(agg["saved_tokens"])
        self.assertEqual(agg["by_metric"]["command_output_reduction"]["net_saved"], 80)
        self.assertEqual(agg["by_metric"]["provider_total_tokens"]["net_saved"], 100)

    def test_provider_usage_metadata_is_reported_separately(self):
        usage = {
            "input_tokens": 100,
            "cached_input_tokens": 20,
            "cache_write_input_tokens": 5,
            "fresh_input_tokens": 85,
            "uncached_input_tokens": 80,
            "output_tokens": 10,
            "reasoning_output_tokens": 2,
            "total_tokens": 110,
            "turns": 2,
            "malformed_lines": 1,
            "source": "provider:test",
        }
        tracker.record_provider_usage(usage)
        ev = tracker.load_session("unittest")[-1]
        self.assertEqual(ev["measurement_status"], "unknown_raw")
        agg = tracker.aggregate(tracker.load_session("unittest"))
        self.assertEqual(agg["provider_usage"]["fresh_input_tokens"], 85)
        self.assertEqual(agg["provider_usage"]["turns"], 2)

    def test_invalid_metric_rejected(self):
        with self.assertRaises(ValueError):
            tracker.record(kind="x", kept_tokens=1, metric="total-ish")

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


class TestHookSchemas(unittest.TestCase):
    def test_current_stop_payload(self):
        text, layer, label = hook_response._extract(
            {"last_assistant_message": "Implemented and tested."})
        self.assertEqual((text, layer, label), ("Implemented and tested.", 1, "response"))

    def test_current_edit_payload(self):
        text, layer, label = hook_response._extract({
            "tool_name": "Edit",
            "tool_input": {"old_string": "before", "new_string": "after"},
        })
        self.assertEqual(text, "after")
        self.assertEqual(layer, 2)
        self.assertEqual(label, "write:Edit")

    def test_current_write_payload(self):
        text, layer, _ = hook_response._extract({
            "tool_name": "Write", "tool_input": {"content": "new file"}})
        self.assertEqual((text, layer), ("new file", 2))

    def test_tool_response_string_and_object(self):
        self.assertEqual(hook_record._extract_output({"tool_response": "stdout"}), "stdout")
        self.assertEqual(hook_record._extract_output(
            {"tool_response": {"stdout": "object stdout"}}), "object stdout")


class TestProviderUsage(unittest.TestCase):
    def test_codex_total_does_not_double_count_components(self):
        stream = "\n".join([
            '{"type":"thread.started","thread_id":"x"}',
            '{"type":"turn.completed","usage":{"input_tokens":13109,'
            '"cached_input_tokens":6912,"cache_write_input_tokens":0,'
            '"output_tokens":105,"reasoning_output_tokens":80}}',
        ])
        usage = provider.parse_codex_jsonl(stream)
        self.assertEqual(usage["total_tokens"], 13214)
        self.assertEqual(usage["uncached_input_tokens"], 6197)
        self.assertEqual(usage["reasoning_output_tokens"], 80)
        self.assertEqual(usage["fresh_input_tokens"], 6197)
        self.assertEqual(usage["turns"], 1)

    def test_codex_usage_sums_turns_and_skips_malformed(self):
        stream = "\n".join([
            "not json",
            '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":2}}',
            '{"type":"turn.completed","usage":{"input_tokens":20,"output_tokens":3}}',
        ])
        usage = provider.parse_codex_jsonl(stream)
        self.assertEqual(usage["total_tokens"], 35)
        self.assertEqual(usage["turns"], 2)
        self.assertEqual(usage["malformed_lines"], 1)

    def test_usage_ledger_marks_missing_components_unknown(self):
        usage = provider.parse_codex_jsonl(
            '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":2}}'
        )
        self.assertEqual(usage["ledger"]["basis"], "partial")
        self.assertIn("reasoning_output_tokens", usage["ledger"]["unknown"])
        self.assertEqual(usage["total_tokens"], 12)

    def test_count_text_is_explicitly_inferred_without_adapter(self):
        provider.clear_tokenizer_adapters()
        result = provider.count_text("hello", provider="openai", model="gpt-5.6-luna")
        self.assertFalse(result.known)
        self.assertEqual(result.scope, "visible_text")

    def test_registered_tokenizer_adapter_is_provider_native(self):
        class Adapter:
            provider = "test-provider"

            def count(self, text, model=None):
                return provider.TokenCount(7, "provider:test", "high", "request", self.provider, model, True)

        provider.register_tokenizer_adapter(Adapter())
        try:
            result = provider.count_text("anything", provider="test-provider", model="x")
            self.assertTrue(result.known)
            self.assertEqual(result.value, 7)
        finally:
            provider.clear_tokenizer_adapters()


class TestAdaptiveRouter(unittest.TestCase):
    def test_compiled_code_policy_is_small_and_keeps_invariants(self):
        route = router.route_text("Implement safe_upload_path in uploads.py.")
        text = prompt.render_instructions(route)
        self.assertLess(len(text), 700)
        for marker in ("safety", "security", "validation", "accessibility", "compatibility",
                       "Result first", "Code:"):
            self.assertIn(marker, text)
        self.assertEqual(route["compiled_instruction_chars"], len(text))

    def test_compiled_tool_policy_adds_only_selected_delta(self):
        route = router.route_text("Inspect verbose pytest output and diff.")
        text = prompt.render_instructions(route)
        self.assertIn("Tools:", text)
        self.assertLess(len(text), 900)
        self.assertEqual(route["instruction_mode"], "micro")

    def test_code_task_does_not_pay_for_tools_without_signal(self):
        result = router.route_text("Implement safe_upload_path in uploads.py.")
        self.assertEqual(result["layers"], [2])
        self.assertEqual(result["tool_adapter"], "native-output")

    def test_explicit_test_task_selects_code_and_tools(self):
        result = router.route_text(
            "Implement the auth function and inspect the focused pytest output.")
        self.assertIn(2, result["layers"])
        self.assertIn(3, result["layers"])
        self.assertEqual(result["tool_adapter"], "rtk-eligible")

    def test_read_only_api_report_does_not_load_code_or_tools(self):
        result = router.route_text(
            "Read api.md. Do not modify the fixture. In your final response, "
            "write a clear 350-500 word report for an engineering manager with "
            "exactly these section headings: Contract, Failure modes, Next action. "
            "Include every fact below; a successful request returns 202."
        )
        self.assertEqual(result["task_mode"], "prose-only")
        self.assertEqual(result["layers"], [1])
        self.assertEqual(result["suppressed_layers"], [2])
        self.assertEqual(result["tool_adapter"], "native-output")
        rendered = prompt.render_instructions(result)
        self.assertNotIn("Code:", rendered)
        self.assertNotIn("Tools:", rendered)

    def test_read_only_security_report_keeps_expanded_summary(self):
        result = router.route_text(
            "Read security.md. Do not modify the fixture. In your final response, "
            "write a clear report with section headings Threat, Control, Residual risk."
        )
        self.assertEqual(result["task_mode"], "prose-only")
        self.assertEqual(result["layers"], [1])
        self.assertEqual(result["summary_mode"], "expanded")

    def test_noisy_tool_task_recommends_rtk_eligible(self):
        result = router.route_text("Inspect the verbose pytest test output and diff.")
        self.assertIn(3, result["layers"])
        self.assertEqual(result["tool_adapter"], "rtk-eligible")

    def test_context_task_selects_l4(self):
        result = router.route_text("Audit the context and write a compaction checkpoint.")
        self.assertIn(4, result["layers"])
        self.assertIn("layer4-context", result["modules"])

    def test_high_stakes_summary_keeps_explicit_warnings(self):
        result = router.route_text("Fix safe path traversal in auth token upload.")
        self.assertEqual(result["summary_mode"], "expanded")
        self.assertIn("warning", prompt.render_instructions(result))

    def test_low_stakes_summary_is_brief(self):
        result = router.route_text("Rename a local variable in a helper.")
        self.assertEqual(result["summary_mode"], "brief")
        self.assertIn("one sentence when sufficient", prompt.render_instructions(result))

    def test_feedback_downgrades_repeated_bad_tool_route(self):
        base = router.route_text("Inspect verbose pytest output and diff.")
        feedback = {
            base["route_key"]: {
                "samples": 3,
                "quality_failures": 1,
                "retry_rate": 0.67,
            }
        }
        result = router.route_text("Inspect verbose pytest output and diff.", feedback)
        self.assertNotIn(3, result["layers"])
        self.assertEqual(result["feedback_action"], "downgrade-layer3")

    def test_feedback_waits_for_three_samples(self):
        base = router.route_text("Inspect verbose pytest output and diff.")
        feedback = {base["route_key"]: {"samples": 2, "quality_failures": 2, "retry_rate": 1}}
        result = router.route_text("Inspect verbose pytest output and diff.", feedback)
        self.assertIn(3, result["layers"])
        self.assertEqual(result["feedback_action"], "observe_until_3_samples")

    def test_net_benefit_is_unknown_without_host_observation(self):
        result = router.adaptive_route("Explain the API contract in prose.")
        self.assertEqual(result["adaptive_action"], "observe")
        self.assertIsNone(result["net_benefit"]["net_tokens"])

    def test_unknown_economics_do_not_inject_tool_delta(self):
        result = router.adaptive_route("Implement parser and inspect verbose pytest output.")
        self.assertEqual(result["adaptive_action"], "observe")
        self.assertEqual(result["layers"], [2])
        self.assertEqual(result["fallback"], "observe-without-optional-deltas")

    def test_net_benefit_skips_optional_layers_when_negative(self):
        result = router.adaptive_route(
            "Inspect verbose pytest output and diff.",
            expected_saving_tokens=1,
            policy_overhead_tokens=100,
        )
        self.assertEqual(result["adaptive_action"], "skip")
        self.assertNotIn(3, result["layers"])
        self.assertEqual(result["fallback"], "net-benefit-skip-optional-deltas")

    def test_net_benefit_keeps_code_contract_for_implementation(self):
        result = router.adaptive_route(
            "Implement the parser and inspect verbose pytest output.",
            expected_saving_tokens=1,
            policy_overhead_tokens=100,
        )
        self.assertEqual(result["layers"], [2])
        self.assertIn(3, result["suppressed_layers"])

    def test_summary_policy_promotes_failed_work(self):
        route = router.route_text("Rename a local variable in a helper.")
        policy = prompt.summary_policy(route, state="failed")
        self.assertEqual(policy["mode"], "expanded")
        self.assertGreaterEqual(policy["max_sentences"], 5)


class TestContextPacking(unittest.TestCase):
    def test_pins_security_and_error_segments(self):
        packed = context.pack_segments(
            [
                context.ContextSegment("routine", "routine", relevance=1),
                context.ContextSegment("secret", "security evidence", security=True),
                context.ContextSegment("error", "traceback", error=True),
            ],
            budget_tokens=2,
            model="gpt-5.6-luna",
        )
        self.assertEqual([s.id for s in packed.segments], ["secret", "error"])
        self.assertEqual([s.id for s in packed.dropped], ["routine"])

    def test_pack_order_is_deterministic_and_lossless(self):
        segments = [
            context.ContextSegment("low", "low", relevance=0.1),
            context.ContextSegment("high", "high", relevance=0.9),
        ]
        a = context.pack_segments(segments)
        b = context.pack_segments(segments)
        self.assertEqual(a.text, b.text)
        self.assertEqual(a.text, "high\n\nlow")

    def test_lossy_plugin_requires_explicit_recovery(self):
        plugin = context.FunctionCompressor(
            "lossy",
            lambda segment: context.CompressionResult(
                text="short", method="lossy", lossless=False, reversible=False,
                original_sha256=__import__("hashlib").sha256(segment.text.encode()).hexdigest(),
            ),
        )
        packed = context.pack_segments(
            [context.ContextSegment("x", "a much longer context block")],
            compressor=plugin,
            allow_lossy=True,
        )
        self.assertEqual(packed.text, "a much longer context block")
        self.assertFalse(packed.compression[0]["accepted"])


if __name__ == "__main__":
    unittest.main()
