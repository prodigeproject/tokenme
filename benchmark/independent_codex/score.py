from __future__ import annotations

import difflib
import importlib
import importlib.util
import json
import re
import sys
from pathlib import Path


CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}
TEMPLATE = Path(__file__).resolve().parent / "template"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _is_test(path: Path) -> bool:
    low = [part.lower() for part in path.parts]
    return path.name.lower().startswith("test_") or any(part in ("test", "tests") for part in low)


def added_loc(root: Path) -> tuple[int, int]:
    source = tests = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in CODE_SUFFIXES:
            continue
        rel = path.relative_to(root)
        before_path = TEMPLATE / rel
        before = (before_path.read_text(encoding="utf-8", errors="replace").splitlines()
                  if before_path.exists() else [])
        after = path.read_text(encoding="utf-8", errors="replace").splitlines()
        count = 0
        for tag, _a, _b, c, d in difflib.SequenceMatcher(None, before, after).get_opcodes():
            if tag in ("insert", "replace"):
                count += sum(1 for line in after[c:d]
                             if line.strip() and not line.lstrip().startswith(("#", "//")))
        if _is_test(rel):
            tests += count
        else:
            source += count
    return source, tests


def score(run: Path, task: str | None = None) -> dict:
    """Score only the case assigned to this independent session.

    A provider-token run has one fresh workspace per ticket; untouched case
    directories are expected stubs.  Check failures (including a stub or a
    runtime exception in the submitted code) are recorded as ``false`` rather
    than escaping as scorer errors.
    """
    loc, test_loc = added_loc(run)
    result = {"run": str(run), "added_loc": loc, "test_loc": test_loc, "checks": {}}
    check_errors: dict[str, str] = {}
    selected = {task} if task else {"safe_path", "auth_token", "reuse_slug", "csv_sum", "date_picker"}

    def add_check(name: str, fn) -> None:
        try:
            result["checks"][name] = bool(fn())
        except Exception as exc:
            result["checks"][name] = False
            check_errors[name] = f"{type(exc).__name__}: {exc}"

    def check_safe_path() -> bool:
        uploads = load(run / "safe_path" / "uploads.py", "uploads_case")
        base = run / "safe_path" / "base"
        base.mkdir(exist_ok=True)
        normal = Path(uploads.safe_upload_path(base, "photo.png")).resolve()
        nested = Path(uploads.safe_upload_path(base, "nested/photo.png")).resolve()
        try:
            uploads.safe_upload_path(base, "../../escape.txt")
            traversal_ok = False
        except (ValueError, OSError):
            traversal_ok = True
        try:
            uploads.safe_upload_path(base, str(base.parent / "absolute-escape.txt"))
            absolute_ok = False
        except (ValueError, OSError):
            absolute_ok = True
        return (normal.parent == base.resolve() and normal.name == "photo.png"
                and nested.parent == (base / "nested").resolve()
                and traversal_ok and absolute_ok)

    def check_auth_token() -> bool:
        auth = load(run / "auth_token" / "auth.py", "auth_case")
        token = auth.make_token("42", "secret")
        valid = auth.verify_token(token, "secret") == "42"
        forged = "99." + token.rsplit(".", 1)[1]
        return (valid
                and auth.verify_token(forged, "secret") in (None, False, "")
                and auth.verify_token(token, "wrong-secret") in (None, False, "")
                and auth.verify_token("malformed", "secret") in (None, False, ""))

    def check_reuse_slug() -> bool:
        sys.path.insert(0, str(run))
        try:
            posts_path = run / "reuse_slug" / "posts.py"
            for name in list(sys.modules):
                if name == "reuse_slug" or name.startswith("reuse_slug."):
                    del sys.modules[name]
            posts = importlib.import_module("reuse_slug.posts")
            source = posts_path.read_text(encoding="utf-8", errors="replace")
            reused = bool(re.search(r"(?:from\s+\.?textutils\s+import\s+slugify|textutils\.slugify)", source))
            return reused and posts.post_slug("Café Déjà Vu") == "cafe-deja-vu"
        finally:
            sys.path.pop(0)

    def check_csv_sum() -> bool:
        sales = load(run / "csv_sum" / "sales.py", "sales_case")
        sample = ("item,amount\na,10.50\nb,broken\nc,2.25\nmissing\n"
                  "d,3\ne,NaN\nf,inf\n")
        return abs(float(sales.sum_amounts(sample)) - 15.75) < 1e-9

    def check_date_picker() -> bool:
        ui = (run / "date_picker" / "DatePicker.tsx").read_text(encoding="utf-8", errors="replace")
        low = ui.lower()
        date_type = bool(re.search(r"type\s*=\s*['\"]date['\"]", low))
        has_label = "label" in low
        has_change = "onchange" in low
        wraps_input = bool(re.search(r"<label[^>]*>[\s\S]*<input\b", low))
        label_id = bool(re.search(r"htmlfor\s*=\s*['\"][^'\"]+['\"]", low)
                        and re.search(r"\bid\s*=\s*['\"][^'\"]+['\"]", low))
        return date_type and has_label and has_change and (wraps_input or label_id)

    checks = {
        "safe_path": check_safe_path,
        "auth_token": check_auth_token,
        "reuse_slug": check_reuse_slug,
        "csv_sum": check_csv_sum,
        "date_picker": check_date_picker,
    }
    for name in selected:
        add_check(name, checks[name])

    final = run / "FINAL_RESPONSE.md"
    result["final_chars"] = len(final.read_text(encoding="utf-8", errors="replace")) if final.exists() else 0
    if check_errors:
        result["check_errors"] = check_errors
    result["passed"] = sum(result["checks"].values())
    return result


if __name__ == "__main__":
    rows = [score(Path(arg).resolve()) for arg in sys.argv[1:]]
    print(json.dumps(rows, indent=2))
