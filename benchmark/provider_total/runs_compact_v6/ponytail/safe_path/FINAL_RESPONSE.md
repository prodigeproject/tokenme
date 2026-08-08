Implemented `safe_upload_path` with `pathlib`: normal and nested upload paths resolve inside `base_dir`, while absolute paths, `..` traversal, and resolved escapes are rejected with `ValueError`.

Focused checks passed.
