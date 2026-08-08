"""Mechanism-targeted task pack: ten tasks per claimed mechanism."""
from __future__ import annotations

from textwrap import dedent


def _noise(prefix: str, count: int = 80) -> str:
    rows = []
    for i in range(1, count + 1):
        rows.append(
            f"2026-08-07T12:{i % 60:02d}:00Z {prefix} worker={i % 7} "
            f"request=req-{i:04d} route=/api/{i % 9} status={200 + (i % 5)} "
            f"duration_ms={11 + (i * 13) % 997} note=fixture-line-{i}"
        )
    return "\n".join(rows) + "\n"


def _prose_task(task_id: str, source_name: str, facts: list[str], headings: list[str], source: str) -> dict:
    heading_text = ", ".join(f"`{heading}`" for heading in headings)
    fact_text = "; ".join(facts)
    ticket = (
        f"Read {source_name}. Do not modify the fixture. In your final response, write a "
        f"clear 350-500 word report for an engineering manager with exactly these section "
        f"headings: {heading_text}. Include every fact below, without inventing numbers: "
        f"{fact_text}. End with one concrete next action."
    )
    return {
        "id": task_id,
        "stratum": "prose_caveman",
        "mechanism": "caveman",
        "ticket": ticket,
        "files": {source_name: source},
    }


def _rtk_task(task_id: str, function_name: str, doc: str, code: str, input_text: str, expected: str) -> dict:
    ticket = (
        f"Implement `{function_name}` in work.py. {doc} "
        "Use a Bash-style command sequence (or the host's equivalent) to inspect the "
        "workspace before editing: list the tree, search for TODO and the function name, "
        "read the fixture, inspect the diff, and count files/lines. Run a focused "
        "verification command after editing. Use the host's shell syntax where needed; "
        "do not add dependencies or change the public API."
    )
    return {
        "id": task_id,
        "stratum": "bash_rtk",
        "mechanism": "rtk",
        "ticket": ticket,
        "files": {
            "work.py": code,
            "fixtures/input.txt": input_text,
            "fixtures/large.log": _noise(task_id),
            "fixtures/README.md": (
                "This fixture intentionally contains repetitive command output.\n"
                "Inspect it before editing work.py.\n"
            ),
            "commands.sh": (
                "find . -type f\n"
                "grep -R -n TODO .\n"
                f"grep -R -n {function_name} .\n"
                "git diff --stat\n"
                "wc -l fixtures/large.log\n"
            ),
            "TODO.md": "TODO: keep public API stable. TODO: verify malformed input.\n",
        },
        "expected": expected,
    }


def _ponytail_task(task_id: str, function_name: str, doc: str, code: str, fixture: str, expected: str) -> dict:
    ticket = (
        f"Implement `{function_name}` in work.py. {doc} Read the existing helper in "
        "helpers.py first. Keep the requested API and behavior; do not add dependencies, "
        "classes, configuration, or unrelated files. Run one focused check."
    )
    return {
        "id": task_id,
        "stratum": "overbuild_ponytail",
        "mechanism": "ponytail",
        "ticket": ticket,
        "files": {
            "work.py": code,
            # Keep the native/helper answers available in one small module.
            # The task still requires a public work.py API, so an agent must
            # make a thin, readable reuse wrapper rather than inventing a
            # dependency or a new abstraction.
            "helpers.py": """import csv\nimport json\nimport os\nfrom datetime import datetime\nfrom urllib.parse import urlparse\n\n\ndef existing_identity(value):\n    return value\n\ndef existing_strip_v(value):\n    return value.removeprefix(\"v\")\n\ndef existing_parse_bool(value):\n    return json.loads(value)\n\ndef existing_join_path(base, child):\n    return os.path.join(base, child)\n\ndef existing_iso_date(value):\n    return datetime.fromisoformat(value).date().isoformat()\n\ndef existing_clamp(value, low, high):\n    return max(low, min(high, value))\n\ndef existing_first_nonempty(values):\n    return next((value for value in values if value.strip()), None)\n\ndef existing_split_host(value):\n    parsed = urlparse(value)\n    return parsed.hostname\n\ndef existing_env_default(mapping, name, default):\n    return mapping.get(name, default)\n\ndef existing_csv_column(text, column):\n    return [row[column] for row in csv.DictReader(text.splitlines()) if row.get(column)]\n\ndef existing_dedupe(values):\n    return list(dict.fromkeys(values))\n\n""",
            "fixtures/input.txt": fixture,
            "README.md": (
                "The repository intentionally has a small native/helper solution.\n"
                "A dependency or abstraction is not required.\n"
            ),
        },
        "expected": expected,
    }


def task_pack() -> dict:
    prose = [
        _prose_task("prose_release", "release.md",
                    ["version 2.4.0 ships bulk export", "p95 latency fell from 820 ms to 610 ms", "rollback is safe before migration step 3"],
                    ["Highlights", "Risks", "Next action"],
                    "Release 2.4.0 adds bulk export for CSV and JSON. Benchmark p95 fell from 820 ms to 610 ms after query batching. The migration has two additive steps; rollback is safe before step 3 but not after the destructive index swap. Support must update the runbook.\n"),
        _prose_task("prose_incident", "incident.md",
                    ["queue backlog peaked at 18,400", "root cause was a missing retry bound", "mitigation was rate limiting"],
                    ["Impact", "Root cause", "Mitigation", "Next action"],
                    "Incident INC-184: queue backlog peaked at 18,400 jobs for 27 minutes. A worker retry loop had no bound after a 502 response. Rate limiting and a worker restart restored throughput. No data loss was observed; delayed notifications were delivered.\n"),
        _prose_task("prose_review", "review.md",
                    ["finding is P1", "query performs N+1 reads", "add a composite index"],
                    ["Finding", "Evidence", "Recommendation"],
                    "Review target: billing/history.py. The endpoint loads one invoice, then performs one line-item query per row. A tenant with 400 invoices creates 401 reads. The query filters by tenant_id and created_at. A composite index on those columns is available in the database engine.\n"),
        _prose_task("prose_migration", "migration.md",
                    ["old column remains readable for one release", "backfill is resumable", "rollback stops before drop"],
                    ["Before", "After", "Rollback", "Next action"],
                    "Migration M-17 renames account.handle to account.slug. The old column remains readable for one release. Backfill records a cursor and can resume after interruption. Rollback is supported until the drop-column step; after that, restore from backup is required.\n"),
        _prose_task("prose_support", "support.md",
                    ["HTTP 429 means rate limit", "Retry-After is authoritative", "credentials need not be rotated"],
                    ["Answer", "Evidence", "Limit", "Next action"],
                    "Customer reports HTTP 429 from the upload API. The response includes Retry-After: 30, which is authoritative. The request was authenticated and no credential exposure appears in logs. Clients should back off and retry; rotating credentials will not fix a rate limit.\n"),
        _prose_task("prose_api", "api.md",
                    ["endpoint is POST /v1/exports", "idempotency key is required", "202 means processing"],
                    ["Contract", "Failure modes", "Next action"],
                    "Exports API: POST /v1/exports accepts a JSON filter and requires Idempotency-Key. A successful request returns 202 with export_id because processing is asynchronous. 400 means invalid filter, 409 means key reuse with a different body, and 429 means retry after the supplied delay.\n"),
        _prose_task("prose_change", "changes.md",
                    ["added WebAuthn login", "changed default page size to 50", "the old token endpoint is breaking"],
                    ["Added", "Changed", "Breaking", "Next action"],
                    "This release adds WebAuthn login and audit events. Default list page size changes from 20 to 50. The legacy /token endpoint is removed; clients must use /oauth/token. The change is breaking for integrations that still call the legacy path.\n"),
        _prose_task("prose_security", "security.md",
                    ["threat is path traversal", "control is canonicalization plus containment", "residual risk is symlink replacement"],
                    ["Threat", "Control", "Residual risk", "Next action"],
                    "Upload accepts an untrusted filename. The threat is path traversal through ../ or an absolute path. Control: canonicalize the candidate and require it to remain under the upload root. A race remains if an attacker replaces a directory with a symlink between validation and open; use a no-follow open primitive where available.\n"),
        _prose_task("prose_perf", "perf.md",
                    ["baseline is 1,240 ms", "bottleneck is JSON serialization", "experiment batches 100 records"],
                    ["Baseline", "Bottleneck", "Experiment", "Next action"],
                    "The report endpoint baseline is 1,240 ms at p95 for 10,000 records. CPU profiling attributes 61% of time to JSON serialization, not the database query. The proposed experiment batches 100 records per serializer call and compares p95 plus memory.\n"),
        _prose_task("prose_arch", "architecture.md",
                    ["decision is a queue-backed worker", "trade-off is eventual consistency", "rejected choice was polling"],
                    ["Decision", "Trade-off", "Rejected", "Next action"],
                    "For thumbnail generation, choose a queue-backed worker. Trade-off: the UI is eventually consistent, but request latency stays bounded and retries are durable. Polling from the web process was rejected because it ties up request workers and complicates backpressure.\n"),
    ]

    rtk_specs = [
        ("rtk_errors", "filter_error_lines", "Return newline-separated lines containing the exact word ERROR, preserving order.", "def filter_error_lines(text):\n    raise NotImplementedError\n", "INFO boot\nERROR disk full\nWARN retry\nERROR timeout\n", "ERROR disk full\nERROR timeout"),
        ("rtk_status", "count_status", "Return a dict with integer keys counting each status token after `status=`.", "def count_status(text):\n    raise NotImplementedError\n", "status=200\nstatus=500\nstatus=200\n", "{200: 2, 500: 1}"),
        ("rtk_ids", "extract_ids", "Return sorted unique integer request IDs from `ID=<number>` markers.", "def extract_ids(text):\n    raise NotImplementedError\n", "ID=9 ID=2\nID=9\n", "[2, 9]"),
        ("rtk_duration", "average_duration_ms", "Return the arithmetic mean of numeric `duration_ms=` values, or 0.0 when absent.", "def average_duration_ms(text):\n    raise NotImplementedError\n", "duration_ms=10\nduration_ms=30\nnoise\n", "20.0"),
        ("rtk_paths", "normalize_paths", "Return input lines with backslashes changed to forward slashes; preserve line order.", "def normalize_paths(text):\n    raise NotImplementedError\n", "C:\\repo\\a.py\nD:\\tmp\\b.py\n", "C:/repo/a.py\nD:/tmp/b.py"),
        ("rtk_recent", "recent_lines", "Return the last `limit` non-empty lines, preserving order and defaulting to 2.", "def recent_lines(text, limit=2):\n    raise NotImplementedError\n", "one\ntwo\nthree\n\n", "['two', 'three']"),
        ("rtk_redact", "redact_tokens", "Replace each `token=<value>` value with `[REDACTED]` without changing other text.", "def redact_tokens(text):\n    raise NotImplementedError\n", "user=ana token=abc123\nstatus=ok\n", "user=ana token=[REDACTED]\nstatus=ok"),
        ("rtk_kv", "parse_kv", "Return a dict for non-empty `key=value` lines; ignore malformed lines.", "def parse_kv(text):\n    raise NotImplementedError\n", "mode=fast\ninvalid\ncount=3\n", "{'mode': 'fast', 'count': '3'}"),
        ("rtk_failed", "failed_commands", "Return command names from lines formatted `cmd=<name> exit=<nonzero>`.", "def failed_commands(text):\n    raise NotImplementedError\n", "cmd=build exit=0\ncmd=test exit=1\n", "['test']"),
        ("rtk_routes", "top_routes", "Return route counts sorted by descending count then route name.", "def top_routes(text):\n    raise NotImplementedError\n", "route=/a\nroute=/b\nroute=/a\n", "[('/a', 2), ('/b', 1)]"),
    ]
    rtk = [_rtk_task(*spec) for spec in rtk_specs]

    pony_specs = [
        ("pony_strip_version", "strip_version", "Remove one leading `v` from a version string; leave other values unchanged.", "def strip_version(value):\n    raise NotImplementedError\n", "v1.2.3", "1.2.3"),
        ("pony_json_bool", "parse_enabled", "Parse the JSON boolean in the fixture and return a Python bool.", "def parse_enabled(text):\n    raise NotImplementedError\n", "true", "True"),
        ("pony_join_path", "join_path", "Join base and child using the standard path API and return a string.", "def join_path(base, child):\n    raise NotImplementedError\n", "base=/srv\nchild=app.log", "/srv\\app.log"),
        ("pony_iso_date", "iso_date", "Return the YYYY-MM-DD date portion of an ISO timestamp.", "def iso_date(value):\n    raise NotImplementedError\n", "2026-08-07T12:34:56+00:00", "2026-08-07"),
        ("pony_clamp", "clamp", "Clamp integer value to inclusive low/high bounds.", "def clamp(value, low, high):\n    raise NotImplementedError\n", "-4,0,10", "0"),
        ("pony_first_nonempty", "first_nonempty", "Return the first non-whitespace string, or None.", "def first_nonempty(values):\n    raise NotImplementedError\n", "['', '  ', 'ready']", "ready"),
        ("pony_host", "split_host", "Return the hostname from a URL, or None when absent.", "def split_host(url):\n    raise NotImplementedError\n", "https://example.com/a", "example.com"),
        ("pony_env_default", "env_default", "Return mapping[name] when present, otherwise the supplied default.", "def env_default(mapping, name, default):\n    raise NotImplementedError\n", "MODE=prod", "prod"),
        ("pony_csv_column", "csv_column", "Return non-empty values from the named CSV column in order.", "def csv_column(text, column):\n    raise NotImplementedError\n", "name,score\na,1\nb,\nc,3\n", "['1', '3']"),
        ("pony_dedupe", "dedupe_preserve", "Return unique values in first-seen order.", "def dedupe_preserve(values):\n    raise NotImplementedError\n", "['a', 'b', 'a', 'c']", "['a', 'b', 'c']"),
    ]
    pony = [_ponytail_task(*spec) for spec in pony_specs]
    return {
        "suite": "tokenme-mechanism-v2-compiled-policy-30-pairs",
        "description": (
            "Thirty identical tasks per arm: ten prose-heavy, ten command-output-heavy, "
            "and ten native-helper/over-building tasks."
        ),
        "tasks": prose + rtk + pony,
    }


TASKS = task_pack()
