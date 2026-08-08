Contract

The export operation is exposed as `POST /v1/exports`. A caller submits a JSON filter describing the data to export and must include an `Idempotency-Key`; the idempotency key is required, not optional. When the service accepts a valid request, it returns HTTP `202` together with an `export_id`. Here, `202` means processing: the export has been accepted for asynchronous work rather than completed within the request. Consumers therefore should not interpret the initial response as proof that an output file already exists. The returned identifier is the durable reference the client can retain for the accepted export operation.

Idempotency is part of the public contract and should be treated as a correctness requirement. A client may reuse a key only when repeating the same request body, such as after losing the original response. The combination of an explicit key, the submitted JSON filter, and the returned export identifier gives callers a clear way to distinguish request acceptance from eventual completion. It also prevents an uncertain network outcome from becoming an excuse to create another logically distinct export.

Failure modes

The documented failures are specific enough to drive client behavior. HTTP `400` means the supplied filter is invalid. The caller should correct the request rather than blindly retry it. HTTP `409` means an idempotency key was reused with a different body. That response protects the original meaning of the key; the client must either send the original body again or use a new key for a genuinely different export request.

HTTP `429` means the caller should retry after the delay supplied by the service. Clients need to honor that server-provided delay instead of inventing an immediate retry loop. They should also preserve the same idempotency key and body when retrying the same logical request, so a throttled or ambiguous attempt cannot accidentally create duplicate work.

The main integration risk is collapsing acceptance and completion into one state. A `202` response confirms asynchronous processing was accepted, but it does not confirm that processing succeeded. Another risk is regenerating idempotency keys on transport retries, which would defeat the protection the endpoint requires. Finally, treating all non-success responses alike would cause bad filters or key conflicts to be retried when they instead require a request correction.

Next action

Add one client contract test that posts a JSON filter with an `Idempotency-Key` and asserts that a `202` response is recorded as processing with its returned `export_id`.
