Decision

Adopt a queue-backed worker for thumbnail generation. The web process should accept the request, validate and record the work, enqueue a thumbnail-generation job, and return without performing the image work inline. A worker can then consume the job, generate the thumbnail, and persist the resulting status and asset reference for the UI to read. This boundary keeps request latency bounded because thumbnail processing does not occupy the request path. It also gives the system a clear place to apply durable retries when processing fails temporarily.

The queue should be treated as the handoff between request handling and background execution. Application state should make job progress explicit enough for the UI and operators to distinguish work that is queued, in progress, complete, or failed, without making the web process responsible for repeatedly performing the work. This is the selected architecture for the thumbnail workflow.

Trade-off

The principal trade-off is eventual consistency. A successful request means the work has been accepted, not that the thumbnail is immediately available. For a period after submission, the UI may display an existing image, a pending state, or no thumbnail while the worker completes processing and the stored result becomes visible.

That behavior needs to be reflected in the product contract and error handling. The UI should communicate progress honestly and tolerate completion occurring after the initiating request has ended. Consumers must not assume that enqueueing and thumbnail availability happen atomically. In exchange, request latency stays bounded, failures can be retried durably, and background capacity can absorb work independently of request workers. Operationally, the team should also make stalled or repeatedly failing jobs observable so eventual consistency does not become an indefinite, unexplained pending state.

Rejected

Polling from the web process was rejected. That design would keep request workers involved while waiting for or checking on thumbnail work, tying up capacity that should remain available for incoming requests. It would also complicate backpressure: the web tier would become responsible both for serving traffic and for regulating repeated checks against work whose completion rate may vary.

Polling therefore weakens the separation between synchronous request handling and asynchronous processing. It does not provide the same clean, durable handoff for retries, and it makes load behavior harder to control when thumbnail generation slows or accumulates. The queue-backed worker is the better fit because it places work admission, processing, and retry behavior at an explicit asynchronous boundary.

Next action

Implement a thin vertical slice that records a thumbnail job, enqueues it, processes it in the worker with durable retry behavior, and exposes its pending, completed, or failed state to the UI.
