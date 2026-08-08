Decision

Adopt a queue-backed worker for thumbnail generation. The web process should accept the triggering request, place the thumbnail job on the queue, and return without performing or supervising the generation work itself. A worker can then consume the job independently. This separates user-facing request handling from background image processing and gives the system a clear boundary between accepting work and completing it.

This decision keeps request latency bounded because the web request is not held open while a thumbnail is generated. It also makes retries durable: queued work can remain available for another processing attempt instead of relying on the lifetime of a particular web request or process. For engineering management, the central outcome is a more reliable background-processing path without expanding the web tier's responsibilities.

Trade-off

The explicit trade-off is eventual consistency. A thumbnail may not be available immediately after the action that requests it, so the UI can temporarily show a pending, placeholder, or prior state while the queued job completes. Product behavior and operational expectations should acknowledge that short-lived gap rather than imply synchronous completion.

That delay is accepted in exchange for bounded request latency and durable retries. The queue also creates a natural place for work to wait when generation capacity is busy. The implementation should keep the user-visible state simple and honest: accepted means the job has been queued, while completed means the worker has successfully produced the thumbnail. This distinction prevents the UI from reporting success prematurely and gives support and operations a shared model for interpreting intermediate states.

Rejected

Polling from the web process was rejected. It would tie up request workers while they repeatedly check for completion, reducing the capacity available for ordinary user traffic. It would also complicate backpressure because waiting and checking would occur in the same tier responsible for serving requests, rather than allowing queued demand to be absorbed and processed according to worker capacity.

Polling does not improve the core outcome enough to justify those costs. It couples thumbnail progress to request-process resources, makes failure and retry behavior harder to reason about, and weakens the clean separation established by a queue-backed worker. No additional orchestration mechanism is warranted until observed requirements show that the queue and worker model is insufficient.

Next action

Implement one end-to-end thumbnail job through the queue-backed worker, including an honest pending UI state and a durable retry path, then verify that the originating web request returns without waiting for thumbnail completion.
