## Decision

Thumbnail generation will use a queue-backed worker. Web request handling will place thumbnail work onto a queue, and a separate worker will perform generation outside the request path. This keeps request latency bounded because the web process does not wait for thumbnail processing to finish. It also gives the work a durable retry path: if processing does not succeed on the first attempt, the queued job can be retried rather than being lost with the request. The architecture therefore separates accepting user work from executing background work, giving each concern a clearer operational boundary.

For engineering management, the key outcome is predictable request handling under thumbnail load. Thumbnail generation can take place asynchronously while the web tier remains focused on serving requests. Queue depth and worker behavior become the primary signals for understanding whether background processing is keeping pace. This decision also creates a natural place to manage failures and backpressure without consuming request workers.

## Trade-off

The explicit trade-off is eventual consistency. After a request is accepted, the UI may not show the generated thumbnail immediately because queue processing happens later. Users can temporarily observe content whose thumbnail is pending. Product behavior must account for that interval with a clear pending or fallback state, then display the thumbnail after processing completes.

This consistency model is accepted in exchange for bounded request latency and durable retries. It shifts complexity away from synchronous request execution and into asynchronous state handling. That means implementation and operations must treat job submission, processing, retry, and completion as distinct states. The UI and API should not imply that thumbnail availability is immediate when only job acceptance is complete.

## Rejected

Polling from the web process was rejected. Polling would tie up request workers while they repeatedly check for completion, reducing the web tier's ability to serve other requests. It would also complicate backpressure because work waiting, completion checks, and request capacity would become coupled inside the same process.

Compared with that choice, a queue-backed worker provides a cleaner boundary between incoming traffic and thumbnail workload. Rejection is based on resource ownership and flow control, not on a claim that polling cannot function. Keeping polling out of the web process avoids making request capacity depend on thumbnail completion timing and preserves the queue as the mechanism for buffering work.

## Next action

Define and review the thumbnail job contract, including its payload, completion state, retry behavior, and the UI's pending-thumbnail state, before implementation begins.