Contract

The Exports API exposes POST /v1/exports. A caller submits a JSON filter describing the export it wants, and an idempotency key is required in the Idempotency-Key header. The service uses that key to distinguish a safe repeat of the same logical request from an incompatible attempt to reuse the key. Clients should therefore generate and retain a key for each intended export operation, keep the request body stable when retrying that operation, and avoid assigning the same key to a different export.

A successfully accepted request returns 202 together with an export_id. The 202 response means processing, not completion: export creation is asynchronous, so receiving it confirms that the service has accepted the work rather than that an export artifact is already ready. Callers should persist the export_id and present the request as pending until the surrounding product flow has evidence of completion. They should not interpret acceptance as permission to download or consume a finished result immediately.

Failure modes

The contract identifies three client-visible failures. A 400 response means the supplied filter is invalid. This should be treated as a request-correction problem: automatic repetition of the unchanged body will not make the filter valid, and the caller should surface useful validation feedback before another submission.

A 409 response means an idempotency key was reused with a different body. This protects the identity of the original operation and indicates a caller-side consistency defect or an incorrect retry implementation. The client should not silently overwrite its stored request, reinterpret the conflict as success, or retry the changed body with the conflicted key. Logging should associate the key, request identity, and response while avoiding exposure of sensitive filter content.

A 429 response means the caller must retry after the supplied delay. Retry behavior should honor that server-provided delay rather than choosing an earlier attempt, and it should preserve both the idempotency key and the exact JSON body so the retry continues to represent the same export operation. User interfaces should keep the operation in a waiting state and avoid presenting throttling as permanent rejection.

Across all paths, observability should distinguish invalid input, conflicting key reuse, throttling, and accepted asynchronous work. Tests should verify the required header, stable retry payloads, export_id capture, and the fact that 202 means processing. This separation will help support teams identify whether remediation belongs in validation, request identity handling, retry scheduling, or downstream completion tracking.

Next action

Add a contract test suite for POST /v1/exports that covers the required Idempotency-Key header, 202 processing behavior with export_id persistence, invalid-filter handling, mismatched-body key reuse, and delayed throttling retries.