Implemented `safe_upload_path` in `safe_path/uploads.py`.

It allows relative nested paths inside `base_dir`, rejects absolute/rooted paths and parent traversal, and verifies the resolved destination remains inside the base directory (including protection against symlink escapes). Focused checks passed.