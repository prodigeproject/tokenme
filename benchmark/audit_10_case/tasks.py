"""Ten-case paired task pack for the Luna Normal/Caveman/TokenMe audit.

The task definitions are reused from the existing mechanism suite.  Keeping the
selection in a separate module makes the benchmark manifest explicit without
changing TokenMe's product source.
"""
from __future__ import annotations

import sys
from pathlib import Path


PROVIDER_TOTAL = Path(__file__).resolve().parents[1] / "provider_total"
if str(PROVIDER_TOTAL) not in sys.path:
    sys.path.insert(0, str(PROVIDER_TOTAL))

from mechanism_tasks import task_pack as _full_task_pack  # noqa: E402


SELECTED = (
    "prose_release",
    "prose_security",
    "prose_api",
    "prose_arch",
    "rtk_errors",
    "rtk_redact",
    "rtk_routes",
    "pony_strip_version",
    "pony_csv_column",
    "pony_dedupe",
)


def task_pack() -> dict:
    full = _full_task_pack()
    by_id = {task["id"]: task for task in full["tasks"]}
    return {
        "suite": "tokenme-vs-caveman-luna-10-case",
        "description": (
            "Ten identical coding-agent cases: four prose/safety cases, "
            "three command-output cases, and three reuse/anti-overbuilding cases."
        ),
        "tasks": [by_id[task_id] for task_id in SELECTED],
    }
