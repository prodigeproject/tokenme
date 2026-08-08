You are one isolated cell in a coding benchmark.

Workspace: C:\Users\Pc\AppData\Local\Temp\tokenme-provider-total-k61o6wqk\baseline\safe_path
Case: safe_path

Only read or modify files inside the workspace. Do not inspect the benchmark
scorer, the repository containing the runner, or any other arm/case. Implement
the ticket below with production-reasonable choices. Run focused checks when
useful. Do not change unrelated files or add dependencies.

Ticket:
Implement safe_upload_path(base_dir, filename) in safe_path/uploads.py. filename is untrusted. A normal filename must resolve inside base_dir; nested paths inside base_dir are allowed; traversal and absolute paths must be rejected.

Before finishing, write the exact user-facing final response you intend to
return into FINAL_RESPONSE.md at the workspace root, then return the same text.
Do not mention benchmark strategy or other arms in that response.
