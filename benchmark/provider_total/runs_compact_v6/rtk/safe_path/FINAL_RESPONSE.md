Implemented `safe_upload_path` in `safe_path/uploads.py`.

It now supports nested relative paths while rejecting absolute paths, drive-qualified paths, `..` traversal, and resolved paths that escape through symlinks. Focused checks and compilation passed.
