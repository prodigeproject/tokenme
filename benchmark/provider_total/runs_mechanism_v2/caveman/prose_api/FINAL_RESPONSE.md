## Contract

The exports interface is exposed as `POST /v1/exports`. Clients submit a JSON filter describing the data to export, and every request must include an `Idempotency-Key` header. The idempotency key is required, not optional guidance, so client libraries and integration documentation should treat omission as a request construction error before traffic reaches the service.

A successful submission returns HTTP `202` and an `export_id`. Here, `202` means processing: the service has accepted the export request, but the export is asynchronous and is not complete when the response arrives. Product flows must therefore avoid presenting acceptance as a finished download. They should retain the returned identifier and use the surrounding export workflow to represent pending work and eventual completion.

Idempotency is tied to both the supplied key and request body. Safe retries should reuse the same key only when resending the same JSON filter. This contract lets callers recover from uncertain network outcomes without intentionally creating duplicate export jobs, while preserving a clear signal when a key is used inconsistently.

## Failure modes

HTTP `400` means the submitted filter is invalid. This is a client-correctable failure: the caller should surface useful validation context, revise the filter, and submit a new valid request rather than retrying unchanged input.

HTTP `409` means an idempotency key was reused with a different body. Blind retry cannot resolve that conflict. The caller must either restore the original body for a true retry or create a distinct request with a new key. Logging should make the key and a non-sensitive request fingerprint available for diagnosis, while avoiding disclosure of filter contents that may contain sensitive selection criteria.

HTTP `429` means the caller must retry after the delay supplied by the service. Retry code should honor that delay instead of using an immediate loop. This response is operationally different from invalid input and key conflict because waiting is part of the documented recovery path.

The main delivery risk is treating asynchronous acceptance as completion. Secondary risks are omitting the required key, generating a new key during an uncertain retry and causing duplicate work, changing the body while retaining a key, or ignoring the supplied retry delay. Monitoring should separate accepted submissions from completed exports and categorize these documented failures so ownership is clear between client validation, integration logic, and service capacity.

## Next action

Assign the client integration owner to add contract tests covering required `Idempotency-Key` handling, asynchronous `202` processing with captured `export_id`, invalid-filter handling, mismatched-body key reuse, and delayed retry behavior, then require those tests to pass before the export workflow ships.
