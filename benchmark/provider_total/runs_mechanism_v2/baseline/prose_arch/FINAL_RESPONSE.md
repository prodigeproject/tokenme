Decision

Adopt a queue-backed worker for thumbnail generation. When an operation requires a thumbnail, the request path should enqueue the work and allow a worker to generate the thumbnail outside the web request lifecycle. This separates thumbnail processing from serving the immediate request and gives the system a clear boundary between accepting work and completing it.

The architecture supports two important operational properties. First, request latency stays bounded because the web process does not wait for thumbnail generation to finish. Second, retries are durable: failed or interrupted thumbnail jobs remain part of the queued workflow instead of depending on the lifetime of a request worker. For an engineering manager, this means the chosen design favors predictable request handling and recoverable background execution over immediate thumbnail availability.

Trade-off

The trade-off is eventual consistency. After the initial request succeeds, the UI may temporarily have no generated thumbnail because the queued worker has not completed the job yet. Product and engineering should therefore treat “request accepted” and “thumbnail available” as separate states rather than implying that both occur together.

This affects the user experience and the system contract. The UI needs to represent pending work clearly, avoid presenting the absence of a thumbnail as a permanent failure, and transition to the completed result when processing finishes. Operationally, the team should also preserve the distinction between a queued job, a retrying job, and a completed job so that eventual consistency remains understandable during support and incident investigation. These consequences are acceptable in exchange for bounded request latency and durable retries, but they should be visible in implementation and product behavior rather than hidden behind an apparently synchronous interaction.

Rejected

Polling from the web process was rejected. That approach would tie up request workers while waiting for thumbnail work to complete, directly coupling background processing time to web-serving capacity. It would also complicate backpressure, because the web tier would be responsible both for serving requests and repeatedly checking unfinished work when downstream processing slows.

Rejecting polling keeps the responsibilities cleaner: the web process accepts the request and submits work, while the queue and worker handle asynchronous execution and retries. This choice reduces contention in the request path and makes load regulation a concern of the background-processing boundary instead of an improvised loop inside web workers.

Next action

Define and implement the queued thumbnail job contract, including its payload, pending and completed states, retry behavior, and the UI response shown while generation is still in progress.
