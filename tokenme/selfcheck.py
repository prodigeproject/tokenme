"""Built-in assertions. Run: python -m tokenme selfcheck"""
from __future__ import annotations

import os
import tempfile

from . import estimate, quality, tracker, layer4


def run() -> int:
    failures: list[str] = []

    def check(name: str, cond: bool, detail: object = ""):
        if not cond:
            failures.append(f"{name}{': ' + str(detail) if detail else ''}")

    # ── estimate ──────────────────────────────────────────────────────────────
    n, method = estimate.count("hello world this is a test")
    check("estimate>0", n > 0)
    check("estimate-no-bare-exact", method != "exact", method)
    check("estimate-labelled", method in ("~est",) or method.startswith("tiktoken:"), method)
    check("estimate-monotonic", estimate.count_n("a" * 400) > estimate.count_n("a" * 40))
    check("estimate-empty", estimate.count_n("") == 0)
    check("estimate-none", estimate.count_n(None) == 0)  # type: ignore
    check("is_estimate-~est", estimate.is_estimate("~est"))
    check("is_estimate-None", estimate.is_estimate(None))
    check("is_estimate-tiktoken-false", not estimate.is_estimate("tiktoken:cl100k_base"))
    check("count_for_model-gpt4o-tuple", len(estimate.count_for_model("hi", "gpt-4o")) == 2)

    # ── quality false-positives ───────────────────────────────────────────────
    check("qfp-import-bcrypt", quality.scan_diff("-import bcrypt\n+import hashlib")["ok"])
    check("qfp-require-js", quality.scan_diff("-const x = require('bcrypt')\n+const x = require('argon2')")["ok"])
    check("qfp-hashmap", quality.scan_diff("-    let x = hashmap.get(k)\n")["ok"])
    check("qfp-submit", quality.scan_diff("-    submit(form)\n")["ok"])
    check("qfp-insecure", quality.scan_diff("-    # insecure because old\n")["ok"])
    check("qfp-comment-validate", quality.scan_diff("-    # validate later\n")["ok"])

    # ── quality true-positives ────────────────────────────────────────────────
    vdiff = "@@\n-    if not validate(x):\n-        raise ValueError('bad')\n+    pass\n"
    rv = quality.scan_diff(vdiff)
    check("qtp-validate-flagged", not rv["ok"], rv)
    check("qtp-readd-clears",
          quality.scan_diff("@@\n-    if not validate(x):\n+    if not validate(x):  # moved\n")["ok"])
    wdiff = "@@\n-    if age <= 18:\n+    if age < 18:\n"
    rw = quality.scan_diff(wdiff)
    check("qtp-weak-op-flagged", not rw["ok"], rw)
    check("qtp-weak-op-in-findings", "weakened_logic" in rw["findings"])
    cdiff = "@@\n-    if not is_admin(user):\n+    if True:\n"
    rc = quality.scan_diff(cdiff)
    check("qtp-const-guard", not rc["ok"], rc)
    cross = "@@\n-    if not authorize(user): raise Forbidden()\n@@\n+    auth_config = {}\n"
    check("qtp-per-hunk-not-cancelled", not quality.scan_diff(cross)["ok"])
    check("qtp-risk-key", "risk" in rv)
    check("qtp-language-key", "language" in rv)

    # ── scan_before_after (proper difflib, #4) ────────────────────────────────
    before = "def foo():\n    if not validate(x):\n        raise ValueError()\n    return x\n"
    after  = "def foo():\n    return x\n"
    rba = quality.scan_before_after(before, after)
    check("sba-validate-flagged", not rba["ok"], rba)
    # reindent should NOT flag (same content, different whitespace)
    b2 = "def f():\n    x = 1\n    y = 2\n"
    a2 = "def f():\n  x = 1\n  y = 2\n"
    check("sba-reindent-clean", quality.scan_before_after(b2, a2)["ok"])

    # ── tracker ───────────────────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as d:
        os.environ["TOKENME_HOME"] = d
        os.environ["TOKENME_SESSION"] = "selftest"
        ev1 = tracker.record(kind="tool_call", raw_tokens=1000, kept_tokens=200, layer=3)
        check("tracker-method-given", ev1["method"] == "given", ev1["method"])
        check("tracker-saved-800", ev1["saved"] == 800)
        ev2 = tracker.record(kind="note", kept_text="hello world", layer=1)
        check("tracker-text-not-given", ev2["method"] != "given", ev2["method"])
        tracker.record(kind="note", kept_tokens=50, layer=1)
        evs = tracker.load_session("selftest")
        agg = tracker.aggregate(evs)
        check("tracker-saved-total", agg["saved_tokens"] == 800)
        check("tracker-coverage-gt0", 0 < agg["coverage_pct"] <= 100)
        check("tracker-by-layer-3", 3 in agg["by_layer"])
        check("tracker-no-negative-clamp",
              tracker.record(kind="x", raw_tokens=10, kept_tokens=100, layer=3)["saved"] == 0)
        check("is_day_bucket-true", tracker.is_day_bucket("day-20260619"))
        check("is_day_bucket-false", not tracker.is_day_bucket("selftest"))
        os.environ.pop("TOKENME_HOME", None)
        os.environ.pop("TOKENME_SESSION", None)

    # ── layer4 ────────────────────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as d:
        import pathlib
        big = pathlib.Path(d) / "big.md"
        big.write_text("# Rules\n" + ("Always respond formally.\n" * 300), encoding="utf-8")
        result = layer4.config_audit([str(big)])
        check("l4-oversized-flagged", any(f["issue"] in ("oversized", "large") for f in result["findings"]), result)
        check("l4-not-found", layer4.config_audit(["/nonexistent/path.md"])["findings"][0]["issue"] == "not_found")

    ckpt = layer4.generate_checkpoint(
        goal="Build the auth module",
        done=["Schema defined", "Routes added"],
        files=["src/auth.py", "tests/test_auth.py"],
        decisions=["Use JWT", "Refresh token = 7 days"],
        next_step="Write unit tests",
    )
    check("l4-checkpoint-has-goal", "Goal:" in ckpt)
    check("l4-checkpoint-has-next", "Next step:" in ckpt)
    parsed = layer4.parse_checkpoint(ckpt)
    check("l4-parse-goal", parsed is not None and "auth" in parsed["goal"].lower(), parsed)
    check("l4-parse-next", parsed is not None and "unit" in parsed["next_step"].lower(), parsed)
    # parse finds LAST checkpoint in a longer text
    text = "some earlier text\n" + ckpt + "\nmore text\n" + \
           layer4.generate_checkpoint("Goal 2", [], [], [], "step 2")
    parsed2 = layer4.parse_checkpoint(text)
    check("l4-parse-last-checkpoint", parsed2 is not None and parsed2["goal"] == "Goal 2", parsed2)

    if failures:
        print("SELFCHECK FAILED:")
        for f in failures:
            print("  FAIL:", f)
        return 1

    import inspect, re as _re
    n_checks = len(_re.findall(r'\bcheck\(', inspect.getsource(run)))
    print(f"selfcheck: all {n_checks} assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
