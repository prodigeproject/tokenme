# Quality guard — tokens get cheaper, code does not get worse

The single biggest danger of any token optimizer is that it trades correctness for
brevity: a shorter answer that dropped a validation check, a smaller diff that
deleted a test, a terse refactor that removed an auth call. tokenme treats that as
a **bug, not a feature**, and ships an automated guard plus a hard behavioral rule.

## Iron rule #2 (from the skill)

> Never simplify away input validation at trust boundaries, error handling that
> prevents data loss, security, accessibility, or anything explicitly requested.

The guard makes that rule checkable instead of aspirational.

## What the guard scans for

`tokenme quality` inspects a change (a unified diff, or before/after files) and
flags **removed** lines matching protective-code patterns that are **not added
back**:

| Signal | Examples it catches |
|--------|---------------------|
| validation | `validate(`, `assert`, `require`, `sanitize`, schema/zod/pydantic |
| error_handling | `try`/`except`/`catch`/`finally`, `raise`/`throw`, `Result<`, `err != nil` |
| security | `auth`, `authorize`, `csrf`, `escape`, `hash`, `jwt`, `verify`, `permission` |
| accessibility | `aria-*`, `role=`, `alt=`, `tabindex`, `label for=` |
| tests | `def test_`, `it(`, `expect(`, `assertEqual`, `@Test`, `#[test]` |

It is **conservative on purpose**: it warns and reports the exact lines, it does
not block. A removed-then-readded line (refactor/move) is not flagged. False
positives are cheaper than a silent security regression.

## Risk levels

Findings are weighted (security/validation = 3, error_handling/tests = 2,
accessibility = 1) into `clean` / `low` / `medium` / `high`. Exit code is `0` when
clean, `1` when something was flagged — so you can gate CI on it.

## Usage

```bash
# scan a staged change before accepting an AI edit
git diff --cached | tokenme quality --diff -

# compare two versions of a file
tokenme quality --before old.py --after new.py

# machine readable, for CI
git diff origin/main | tokenme quality --diff - --json
```

Example output:

```
quality guard: HIGH RISK - review before accepting.

  [security] 2 net removed (2 removed, 0 added back)
      - if not authorize(user): raise Forbidden()
      - token = verify_jwt(request.headers['Authorization'])

  [tests] 1 net removed (1 removed, 0 added back)
      - def test_rejects_expired_token():

tokenme iron rule #2: never simplify away validation, error handling,
security, accessibility, or tests. Restore these or confirm intentional.
```

## Recommended workflow

1. Let tokenme minimize as usual (Layers 1-2).
2. Before accepting any AI-generated diff, run `git diff | tokenme quality --diff -`.
3. If it flags `medium`/`high`, restore the safeguard or add a `tokenme:` comment
   explaining why removal is intentional.
4. Optionally wire it into a pre-commit hook or CI step (`exit 1` blocks).

## Pre-commit example

```bash
# .git/hooks/pre-commit
git diff --cached -U0 | python -m tokenme quality --diff - || {
  echo "tokenme quality guard flagged removed safeguards. Review above."
  exit 1
}
```

## The point

Saving tokens is only a win if the code is still correct, safe, and accessible.
The guard is how tokenme keeps the promise that its optimization is free of
quality cost — measured, not just asserted.
