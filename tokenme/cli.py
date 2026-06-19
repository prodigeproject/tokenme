"""tokenme command-line interface.

Subcommands:
  count    <file|->                estimate tokens of a file or stdin
  compare  --raw F --kept F [..]   record + show tokens saved (raw vs kept)
  record   --kind .. [--raw F]     log one tracking event (used by hooks)
  report   [--session ID] [--json] per-session + detailed usage report
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

from . import __version__, estimate, quality, tracker
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
    saved = max(0, rn - kn)
    pct = round(100 * saved / rn, 1) if rn else 0.0
    method = "~est" if (estimate.is_estimate(rm) or estimate.is_estimate(km)) else rm
    if not args.no_record:
        tracker.record(kind="tool_call", raw_tokens=rn, kept_tokens=kn,
                       layer=args.layer, label=args.label,
                       session=args.session, method=method)
    print(f"raw:   {rn:>8} tokens")
    print(f"kept:  {kn:>8} tokens")
    print(f"saved: {saved:>8} tokens  ({pct}%, {method})")
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
        layer=args.layer, label=args.label, session=args.session)
    if not args.quiet:
        print(json.dumps(ev, ensure_ascii=False))


# ── report ───────────────────────────────────────────────────────────────────
def _bar(pct: float, width: int = 24) -> str:
    fill = int(round(width * min(pct, 100) / 100))
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
              f"({agg['measured_events']} measured, {cov}% coverage)")
        print(f"  tokens kept   : {agg['kept_tokens']:,}")
        if agg["raw_tokens_where_known"]:
            pct = agg["saved_pct_where_known"]
            print(f"  tokens saved  : {agg['saved_tokens']:,}  "
                  f"({pct}% of measured events only, {agg['method']})")
            print(f"  [{_bar(pct)}] {pct}%")
        if agg["by_layer"]:
            print("  by layer:")
            for layer in sorted(k for k in agg["by_layer"] if k is not None):
                s = agg["by_layer"][layer]
                lname = {1: "prose", 2: "code", 3: "tool output", 4: "lifecycle"}.get(layer, "?")
                print(f"    L{layer} {lname}: saved {s['saved']:,} tok "
                      f"over {s['events']} events")
    print("\n" + "-" * 60)
    tcov = total.get("coverage_pct", 0.0)
    print(f"TOTAL  saved: {total['saved_tokens']:,}  "
          f"({total['saved_pct_where_known']}%, {total['method']})")
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
        print(f"{sid:40}{bkt}  {agg['events']:>4} ev  "
              f"{cov:>5.1f}% cov  saved {agg['saved_tokens']:>8,} tok")


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
    c.add_argument("--session"); c.add_argument("--heuristic", action="store_true")
    c.add_argument("--no-record", action="store_true")
    c.set_defaults(func=cmd_compare)

    c = sub.add_parser("record", help="log one tracking event")
    c.add_argument("--kind", default="tool_call")
    c.add_argument("--raw"); c.add_argument("--kept")
    c.add_argument("--raw-tokens", type=int); c.add_argument("--kept-tokens", type=int)
    c.add_argument("--layer", type=int); c.add_argument("--label", default="")
    c.add_argument("--session"); c.add_argument("--quiet", action="store_true")
    c.set_defaults(func=cmd_record)

    c = sub.add_parser("report", help="per-session usage report")
    c.add_argument("--session"); c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_report)

    c = sub.add_parser("sessions", help="list tracked sessions")
    c.set_defaults(func=cmd_sessions)

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
