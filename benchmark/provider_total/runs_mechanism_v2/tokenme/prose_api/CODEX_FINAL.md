Contract

The export creation contract is `POST /v1/exports`. The caller submits a JSON filter and must include an `Idempotency-Key`; the idempotency key is required, so clients should treat generating and retaining it as part of constructing every request. A successful request returns `202` with an `export_id`. Here, `202` means processing: the service has accepted the export request, but the export is not complete when the response arrives. This asynchronous boundary matters to both product behavior and client implementation. A client should store the returned identifier and present the operation as accepted or in progress rather than reporting that the export has finished. The documented contract does not state how completion is queried or delivered, so no polling URL, callback, completion timing, or terminal status should be assumed.

Failure modes

The API distinguishes malformed input, unsafe idempotency-key reuse, and throttling. A `400` response means the supplied filter is invalid. Clients should treat that as a request correction issue: preserve useful user input, surface an actionable validation message where possible, and avoid automatic retries of the unchanged body.

A `409` response means the same idempotency key was reused with a different body. This protects the meaning of an idempotent request. Clients need to bind each key to the exact request body they originally sent. Retrying the same logical operation should reuse that key only with the same body; a genuinely changed export request should receive a new key. Silently retrying a changed body under an old key risks repeated conflicts and obscures a client-side state error.

A `429` response means the caller must retry after the delay supplied by the service. Retry logic should honor that supplied delay instead of retrying immediately. It should retain the same request body and idempotency key when retrying the same logical export, preventing accidental duplicate submissions while respecting rate limits. User-facing status should distinguish this temporary throttling from an invalid filter and from a key/body conflict.

The main integration risk is therefore not only handling non-success responses; it is also interpreting acceptance as completion. Observability and UI language should reflect the asynchronous lifecycle, correlate logs with `export_id` and the idempotency key, and make each documented failure category identifiable without exposing sensitive filter contents.

Next action

Implement and test one client workflow that sends the JSON filter with a retained `Idempotency-Key`, records the `export_id` on `202`, rejects unchanged retries after `400`, creates a new key for a changed body after `409`, and honors the supplied retry delay after `429`.