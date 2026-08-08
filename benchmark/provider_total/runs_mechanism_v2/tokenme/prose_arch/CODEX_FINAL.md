Decision

Adopt a queue-backed worker for thumbnail generation. The web process should enqueue a thumbnail-generation job and complete the request without performing the image work inline. A separate worker should consume that job and produce the thumbnail. This separates request handling from background processing, keeps request latency bounded, and gives thumbnail work a durable execution path. The queue also creates an explicit boundary where work can be buffered and managed when demand exceeds processing capacity. For engineering and product planning, this means the request can succeed before the generated thumbnail is available, and the system must represent that intermediate state clearly.

Trade-off

The principal trade-off is eventual consistency. After an upload or other thumbnail-triggering event completes, the UI may temporarily show a pending state, placeholder, or previously available representation until the worker finishes and the result becomes visible. Consumers must not assume that request completion implies immediate thumbnail availability. That behavior should be explicit in API contracts, interface states, and operational expectations.

In return, request latency stays bounded because the web process is not occupied by thumbnail generation. Retries are durable, so transient processing failures do not require the originating request to remain active. The architecture also provides a natural place to apply backpressure: queued work can wait for worker capacity rather than consuming request workers. Implementation should preserve idempotency so that a retry cannot create conflicting results, and observability should distinguish jobs that are waiting, running, completed, or failed. These are design requirements implied by asynchronous execution, not reasons to hide the consistency delay from users.

Rejected

Polling from the web process was rejected. That approach ties up request workers while they repeatedly check whether thumbnail work has completed, reducing the capacity available for unrelated requests. It also complicates backpressure because waiting request handlers become part of the workload-control problem instead of allowing pending work to remain in a queue designed for that purpose. Polling would couple the lifecycle of background processing to the web tier and weaken the durable retry model. Although polling can appear straightforward at small scale, it does not meet the architecture's goals for bounded request latency, durable execution, and controlled load.

Next action

Define and review the thumbnail job contract, including its idempotency key, payload, pending UI state, retry behavior, and completion signal, before implementing the producer and worker.