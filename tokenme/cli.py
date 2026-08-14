"""tokenme command-line interface.

Subcommands:
  count    <file|->                estimate tokens of a file or stdin
  compare  --raw F --kept F [..]   record + show tokens saved (raw vs kept)
  record   --kind .. [--raw F]     log one tracking event (used by hooks)
  report   [--session ID] [--json] per-session + detailed usage report
  provider-usage FILE             parse provider-reported Codex JSONL usage
  route    --text/--file          select modules and output adapter
  route-feedback                  store route outcome for closed-loop fallback
  sessions                         list tracked sessions
  quality  --diff F | --before A --after B   scan a change for removed safeguards
  audit    [paths ...]             Layer-4 config audit of context/memory files
  checkpoint --goal G [options]    generate a compaction-survival CHECKPOINT block
  selfcheck                        run built-in assertions

All storage is local under ~/.tokenme (override with TOKENME_HOME).
"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__, estimate, quality, tracker, provider, router
from . import layer4


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ── count ────────────────────────────────────────────────────────────────────
def cmd_count(args):
    text = _read(args.file)
    n, method = estimate.count(text, force_heuristic=args.heuristic)
    print(f"{n} tokens ({method})")


# ── compare ──────────────────────────────────────────────────────────────────
def cmd_compare(args):
    raw = _read(args.raw)
    kept = _read(args.kept)
    rn, rm = estimate.count(raw, force_heuristic=args.heuristic)
    kn, km = estimate.count(kept, force_heuristic=args.heuristic)
    saved = rn - kn
    pct = round(100 * saved / rn, 1) if rn else 0.0
    method = "~est" if (estimate.is_estimate(rm) or estimate.is_estimate(km)) else rm
    if not args.no_record:
        tracker.record(kind="tool_call", raw_tokens=rn, kept_tokens=kn,
                       layer=args.layer, label=args.label,
                       session=args.session, method=method, metric=args.metric)
    print(f"raw:   {rn:>8} tokens")
    print(f"kept:  {kn:>8} tokens")
    label = "saved" if saved >= 0 else "added"
    amount = saved if saved >= 0 else -saved
    signed_pct = pct if saved >= 0 else -pct
    print(f"{label + ':':<6} {amount:>8} tokens  ({signed_pct}%, {method})")
    if not args.no_record:
        sid = args.session or tracker.current_session_id()
        note = "  [day-bucket: set TOKENME_SESSION for per-session tracking]" \
               if tracker.is_day_bucket(sid) else ""
        print(f"recorded -> session {sid}{note}")


# ── record ───────────────────────────────────────────────────────────────────
def cmd_record(args):
    raw_text = _read(args.raw) if args.raw else None
    kept_text = _read(args.kept) if args.kept else None
    ev = tracker.record(
        kind=args.kind, raw_text=raw_text, kept_text=kept_text,
        raw_tokens=args.raw_tokens, kept_tokens=args.kept_tokens,
        layer=args.layer, label=args.label, session=args.session,
        metric=args.metric)
    if not args.quiet:
        print(json.dumps(ev, ensure_ascii=False))


# ── report ───────────────────────────────────────────────────────────────────
def _bar(pct: float, width: int = 24) -> str:
    fill = int(round(width * max(0, min(pct, 100)) / 100))
    return "#" * fill + "." * (width - fill)


def cmd_report(args):
    sids = [args.session] if args.session else tracker.list_sessions()
    if not sids:
        print("No sessions tracked yet. Run `tokenme compare ...` or enable hooks.")
        return
    all_events, per = [], []
    for sid in sids:
        ev = tracker.load_session(sid)
        all_events.extend(ev)
        per.append((sid, tracker.aggregate(ev)))
    total = tracker.aggregate(all_events)

    if args.json:
        print(json.dumps({"total": total, "sessions": dict(per)},
                         ensure_ascii=False, indent=2))
        return

    print("=" * 60)
    print("tokenme usage report")
    print("=" * 60)
    for sid, agg in per:
        bucket = "  [day-bucket]" if tracker.is_day_bucket(sid) else ""
        print(f"\nsession: {sid}{bucket}")
        cov = agg.get("coverage_pct", 0.0)
        print(f"  events        : {agg['events']} "
              f"({agg['measured_events']} measured, "
              f"{agg['unknown_raw_events']} unknown raw, {cov}% coverage)")
        print(f"  tokens kept   : {agg['kept_tokens']:,}")
        if agg["mixed_metrics"]:
            print("  net delta      : not combined (multiple metric types)")
        elif agg["raw_tokens_where_known"]:
            pct = agg["saved_pct_where_known"]
            direction = "saved" if agg["saved_tokens"] >= 0 else "added"
            amount = abs(agg["saved_tokens"])
            print(f"  tokens {direction:<5}: {amount:,}  "
                  f"({pct}% net over measured events, {agg['method']})")
            if pct >= 0:
                print(f"  [{_bar(pct)}] {pct}%")
            else:
                print(f"  regression    : {agg['regression_events']} events, "
                      f"{agg['regressed_tokens']:,} tokens added")
        if agg["by_layer"]:
            print("  by layer:")
            for layer in sorted(k for k in agg["by_layer"] if k is not None):
                s = agg["by_layer"][layer]
                lname = {1: "prose", 2: "code", 3: "tool output", 4: "lifecycle"}.get(layer, "?")
                print(f"    L{layer} {lname}: saved {s['saved']:,} tok "
                      f"over {s['events']} events")
        if agg["by_metric"]:
            print("  by metric:")
            for metric, summary in sorted(agg["by_metric"].items()):
                pct = summary["net_saved_pct"]
                delta = summary["net_saved"]
                detail = "unknown raw" if pct is None else f"{delta:+,} tok ({pct:+.1f}%)"
                print(f"    {metric}: {detail}; {summary['measured_events']}/"
                      f"{summary['events']} measured")
        if agg.get("provider_usage"):
            pu = agg["provider_usage"]
            print("  provider telemetry:")
            print(f"    total {pu['total_tokens']:,}; fresh input "
                  f"{pu['fresh_input_tokens']:,}; turns {pu['turns']:,}; "
                  f"output {pu['output_tokens']:,}")
    print("\n" + "-" * 60)
    tcov = total.get("coverage_pct", 0.0)
    if not total["measured_events"]:
        print("TOTAL  net delta: unknown (no raw counterfactuals)")
    elif total["mixed_metrics"]:
        print("TOTAL  net delta: not combined across metric types")
    else:
        print(f"TOTAL  net saved: {total['saved_tokens'] or 0:,}  "
              f"({total['saved_pct_where_known'] or 0.0}%, {total['method']})")
    print(f"       kept:  {total['kept_tokens']:,}")
    print(f"       measurement coverage: {tcov}% of events")
    print("-" * 60)
    print("% saved is over MEASURED events only — see coverage for full picture.")
    if tcov < 50:
        print("Coverage is low. Enable hooks or use `tokenme compare` on tool calls.")


# ── sessions ─────────────────────────────────────────────────────────────────
def cmd_sessions(args):
    for sid in tracker.list_sessions():
        agg = tracker.aggregate(tracker.load_session(sid))
        cov = agg.get("coverage_pct", 0.0)
        bkt = " [day]" if tracker.is_day_bucket(sid) else ""
        if not agg["measured_events"]:
            delta = "unknown raw"
        elif agg["mixed_metrics"]:
            delta = "mixed metrics"
        else:
            delta = f"net {agg['saved_tokens'] or 0:>8,} tok"
        print(f"{sid:40}{bkt}  {agg['events']:>4} ev  "
              f"{cov:>5.1f}% cov  {delta}")


# ── provider usage ────────────────────────────────────────────────────────────
def cmd_provider_usage(args):
    if args.format != "codex-jsonl":
        raise ValueError(f"unsupported provider format: {args.format}")
    usage = provider.parse_codex_jsonl(_read(args.file))
    if args.record:
        tracker.record_provider_usage(
            usage, label=args.label or args.file, session=args.session)
    if args.json:
        print(json.dumps(usage, ensure_ascii=False, indent=2))
        return
    print(f"turns:                  {usage['turns']:,}")
    print(f"input tokens:           {usage['input_tokens']:,}")
    print(f"  cached input:         {usage['cached_input_tokens']:,}")
    print(f"  uncached input:       {usage['uncached_input_tokens']:,}")
    print(f"  cache write input:    {usage['cache_write_input_tokens']:,}")
    print(f"output tokens:          {usage['output_tokens']:,}")
    print(f"  reasoning output:     {usage['reasoning_output_tokens']:,}")
    print(f"fresh input (uncached + write): {usage['fresh_input_tokens']:,}")
    print(f"total (input + output): {usage['total_tokens']:,}")
    if usage.get("ledger"):
        ledger = usage["ledger"]
        print(f"evidence basis:         {ledger['basis']}")
        if ledger.get("unknown"):
            print("unknown fields:          " + ", ".join(ledger["unknown"]))


def cmd_route(args):
    text = _read(args.file) if args.file else args.text
    feedback = router.load_feedback(args.feedback) if args.feedback else None
    if args.adaptive or args.expected_saving is not None:
        result = router.adaptive_route(
            text,
            feedback=feedback,
            expected_saving_tokens=args.expected_saving,
            policy_overhead_tokens=args.policy_overhead,
        )
    else:
        result = router.route_text(text, feedback=feedback)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"layers: {','.join(map(str, result['layers']))}")
    print(f"modules: {', '.join(result['modules'])}")
    print(f"tool adapter: {result['tool_adapter']}")
    print(f"route key: {result['route_key']}")
    print(f"estimated module tokens: {result['estimated_module_tokens']}")
    if result.get("net_benefit"):
        print(f"adaptive action: {result['adaptive_action']} "
              f"(net {result['net_benefit'].get('net_tokens', 'unknown')})")
    if result.get("feedback_action") not in (None, "none"):
        print(f"feedback action: {result['feedback_action']}")


def cmd_route_feedback(args):
    event = router.record_feedback(
        route_key=args.route_key,
        outcome=args.outcome,
        turns=args.turns,
        retries=args.retries,
        quality_ok=args.quality_ok,
        total_tokens=args.total_tokens,
        path=args.path,
        label=args.label,
    )
    if args.json:
        print(json.dumps(event, ensure_ascii=False, indent=2))
    else:
        print(f"recorded route feedback: {event['route_key']} ({event['outcome']})")


# ── quality ──────────────────────────────────────────────────────────────────
def cmd_quality(args):
    if args.diff:
        result = quality.scan_diff(_read(args.diff))
    elif args.before and args.after:
        result = quality.scan_before_after(_read(args.before), _read(args.after))
    else:
        print("error: provide --diff F, or both --before A and --after B",
              file=sys.stderr)
        return 2
    lang = result.get("language")
    lang_note = f" (detected: {lang})" if lang else ""
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    if result["ok"]:
        print(f"quality guard: CLEAN{lang_note}")
        return 0
    print(f"quality guard: {result['risk'].upper()} RISK{lang_note} "
          f"— review before accepting.")
    for name, f in result["findings"].items():
        print(f"\n  [{name}] {f['net_removed']} net removed "
              f"({f['removed']} removed, {f['added_back']} added back)")
        for s in f["samples"]:
            print(f"      - {s}")
    print("\ntokenme iron rule #2: never simplify away validation, error handling,")
    print("security, accessibility, or tests. Restore or confirm intentional.")
    print("Note: this guard is heuristic — verify all findings manually.")
    return 1


# ── audit (Layer 4) ──────────────────────────────────────────────────────────
def cmd_audit(args):
    paths = args.paths or _default_audit_paths()
    if not paths:
        print("No paths to audit. Pass file paths, or set up a default agent config.")
        return
    result = layer4.config_audit(paths)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(layer4.format_audit_report(result))


def _default_audit_paths() -> list[str]:
    """Best-effort list of common agent config locations."""
    import os
    home = os.path.expanduser("~")
    candidates = [
        f"{home}/.claude/CLAUDE.md",
        f"{home}/.claude/memory.md",
        ".kiro/steering",
        "CLAUDE.md",
        ".cursorrules",
        ".github/copilot-instructions.md",
    ]
    from pathlib import Path
    found = []
    for c in candidates:
        p = Path(c)
        if p.is_file():
            found.append(str(p))
        elif p.is_dir():
            found.extend(str(f) for f in p.glob("*.md"))
    return found


# ── checkpoint (Layer 4) ─────────────────────────────────────────────────────
def cmd_checkpoint(args):
    block = layer4.generate_checkpoint(
        goal=args.goal,
        done=args.done or [],
        files=args.files or [],
        decisions=args.decisions or [],
        next_step=args.next_step or "",
    )
    print(block)
    n, m = estimate.count(block)
    print(f"\n(~{n} tokens, {m})")


# ── selfcheck ────────────────────────────────────────────────────────────────
def cmd_selfcheck(args):
    from .selfcheck import run
    return run()


# ── parser ───────────────────────────────────────────────────────────────────
def build_parser():
    p = argparse.ArgumentParser(
        prog="tokenme",
        description="token tracking, savings, quality guard, and Layer-4 tooling")
    p.add_argument("--version", action="version", version=f"tokenme {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("count", help="estimate tokens of a file or stdin")
    c.add_argument("file"); c.add_argument("--heuristic", action="store_true")
    c.set_defaults(func=cmd_count)

    c = sub.add_parser("compare", help="show + record tokens saved (raw vs kept)")
    c.add_argument("--raw", required=True); c.add_argument("--kept", required=True)
    c.add_argument("--layer", type=int); c.add_argument("--label", default="")
    c.add_argument("--metric", choices=tracker.METRIC_TYPES)
    c.add_argument("--session"); c.add_argument("--heuristic", action="store_true")
    c.add_argument("--no-record", action="store_true")
    c.set_defaults(func=cmd_compare)

    c = sub.add_parser("record", help="log one tracking event")
    c.add_argument("--kind", default="tool_call")
    c.add_argument("--raw"); c.add_argument("--kept")
    c.add_argument("--raw-tokens", type=int); c.add_argument("--kept-tokens", type=int)
    c.add_argument("--layer", type=int); c.add_argument("--label", default="")
    c.add_argument("--metric", choices=tracker.METRIC_TYPES)
    c.add_argument("--session"); c.add_argument("--quiet", action="store_true")
    c.set_defaults(func=cmd_record)

    c = sub.add_parser("report", help="per-session usage report")
    c.add_argument("--session"); c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_report)

    c = sub.add_parser("sessions", help="list tracked sessions")
    c.set_defaults(func=cmd_sessions)

    c = sub.add_parser("provider-usage", help="read provider-reported usage")
    c.add_argument("file", help="provider event stream, or - for stdin")
    c.add_argument("--format", choices=("codex-jsonl",), default="codex-jsonl")
    c.add_argument("--json", action="store_true")
    c.add_argument("--record", action="store_true")
    c.add_argument("--session"); c.add_argument("--label", default="")
    c.set_defaults(func=cmd_provider_usage)

    c = sub.add_parser("route", help="select TokenMe modules for a task")
    source = c.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--file")
    c.add_argument("--feedback", help="optional route feedback JSONL")
    c.add_argument("--adaptive", action="store_true",
                   help="include net-benefit simulation and adaptive fallback")
    c.add_argument("--expected-saving", type=int,
                   help="host-observed saving tokens for the simulation")
    c.add_argument("--policy-overhead", type=int,
                   help="host-counted policy overhead tokens")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_route)

    c = sub.add_parser("route-feedback", help="record closed-loop route outcome")
    c.add_argument("--route-key", required=True)
    c.add_argument("--outcome", choices=("success", "retry", "quality-fail", "error"),
                   default="success")
    c.add_argument("--turns", type=int, default=0)
    c.add_argument("--retries", type=int, default=0)
    quality_group = c.add_mutually_exclusive_group()
    quality_group.add_argument("--quality-ok", dest="quality_ok", action="store_true")
    quality_group.add_argument("--quality-fail", dest="quality_ok", action="store_false")
    c.set_defaults(quality_ok=None)
    c.add_argument("--total-tokens", type=int, default=0)
    c.add_argument("--path")
    c.add_argument("--label", default="")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_route_feedback)

    c = sub.add_parser("quality", help="scan a change for removed safeguards")
    c.add_argument("--diff"); c.add_argument("--before"); c.add_argument("--after")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_quality)

    c = sub.add_parser("audit", help="Layer-4 config audit of agent context files")
    c.add_argument("paths", nargs="*", help="files to audit (default: auto-detect)")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_audit)

    c = sub.add_parser("checkpoint", help="generate a compaction-survival CHECKPOINT block")
    c.add_argument("--goal", required=True)
    c.add_argument("--done", nargs="*")
    c.add_argument("--files", nargs="*")
    c.add_argument("--decisions", nargs="*")
    c.add_argument("--next-step", default="")
    c.set_defaults(func=cmd_checkpoint)

    c = sub.add_parser("selfcheck", help="run built-in assertions")
    c.set_defaults(func=cmd_selfcheck)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    rc = args.func(args)
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
